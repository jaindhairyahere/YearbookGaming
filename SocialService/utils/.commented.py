################################################### PUbnub Event Reciever ########################
from chat_moderator.serializers import ContentSerializer, Content
from django.conf import settings
from utils.choices import ModerationStates
from utils.pubnub import send_pubnub_message
from utils.functions import get_pubnub_service
from django.dispatch import Signal, receiver
from django.db.models.signals import pre_save
# from app_admin.models import ModerationTicket

# Get the PubNub Instance from settings
pubnub_service = get_pubnub_service()


@receiver(pre_save, sender=Content)
def content_changed_or_created(sender, instance, **kwargs):
    """Function which initiates different actions based on how the 
    "content" instance will be changed depending on the "pre_save" signal.
    The following actions are issued by this signal function: 
        1. If Old object is Under Review, and New Object is Rejected => Send Feedback to Sender
        2. If Old object is [Under Review, Marked Spam, Rejected] and New object is Approved => Forward the message
        3. If Old Object is Approved and [New Object is Marked Spam, Under Review, Rejected]  => Send Feedback to sender

    Args:
        sender (django.db.models.Model): A django Model (Content Class in this case)
        instance (Content): The modified instance, before saving
    """
    # Boolean marking unexpected_behaviour
    unexpected_behaviour = True
    try:
        # Fetch the old object from the database. Raise error if previous object doesn't exist
        old_obj = sender.objects.select_for_update().get(pk=instance.id)
    except sender.DoesNotExist:
        # Object is new. Should go Under Moderation
        instance.status = ModerationStates.UNDER_REVIEW    
        mt, _ = ModerationTicket.objects.get_or_create(content=instance)
        if _:
            rebalance()
    else:
        if old_obj.is_under_review and instance.is_rejected:
            # Send Feed Back to Sender
            # print("Send Feed Back to Sender")
            unexpected_behaviour = send_pubnub_message(pubnub_service, instance, "backward", "Content Rejected by Moderators")
        elif not old_obj.is_approved and not old_obj.is_deleted and instance.is_approved:
            # Send Message Forward to Reciever
            # print("Send Message Forward to Reciever")
            unexpected_behaviour = send_pubnub_message(pubnub_service, instance, "forward", f"Message from {instance.sender_uuid}")
        elif old_obj.is_approved and not instance.is_approved and not instance.is_deleted:
            # Reciever reports the message and Send Feed Back to Sender
            # print("Reciever reports the message and Send Feed Back to Sender")
            unexpected_behaviour = send_pubnub_message(pubnub_service, instance, "backward", "Message reported by reciever")
            generate_moderation_ticket(instance)
            
        else:
            # print("Doing just nothing")
            unexpected_behaviour = True
        unexpected_behaviour = not unexpected_behaviour
        
    if unexpected_behaviour:
        # Report to admin about unexpected behaviour
        pass
            
##################################### Pika Asynchronous Publilsher ##############################3
# -*- coding: utf-8 -*-
# pylint: disable=C0111,C0103,R0205

import asyncio
import functools
import logging
import json
import pika
from pika.exchange_type import ExchangeType

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
# LOGGER = logging.get# LOGGER(__name__)


class TicketPublisher(object):
    """This is an example publisher that will handle unexpected interactions
    with RabbitMQ such as channel and connection closures.
    If RabbitMQ closes the connection, it will reopen it. You should
    look at the output, as there are limited reasons why the connection may
    be closed, which usually are tied to permission related issues or
    socket timeouts.
    It uses delivery confirmations and illustrates one way to keep track of
    messages that have been sent and if they've been confirmed by RabbitMQ.
    """
    EXCHANGE = 'message'
    EXCHANGE_TYPE = ExchangeType.fanout
    PUBLISH_INTERVAL = 99999
    QUEUE = 'text_1'
    ROUTING_KEY = 'example.text'
    
    def __init__(self, amqp_url):
        """Setup the example publisher object, passing in the URL we will use
        to connect to RabbitMQ.
        :param str amqp_url: The URL for connecting to RabbitMQ
        """
        self._connection = None
        self._channel = None

        self._deliveries = None
        self._acked = None
        self._nacked = None
        self._message_number = None

        self._stopping = False
        self._url = amqp_url

    def connect(self):
        """This method connects to RabbitMQ, returning the connection handle.
        When the connection is established, the on_connection_open method
        will be invoked by pika.
        :rtype: pika.SelectConnection
        """
        # LOGGER.info('Connecting to %s', self._url)
        print('Connecting to %s', self._url)
        return pika.SelectConnection(
            pika.URLParameters(self._url),
            on_open_callback=self.on_connection_open,
            on_open_error_callback=self.on_connection_open_error,
            on_close_callback=self.on_connection_closed)

    def on_connection_open(self, _unused_connection):
        """This method is called by pika once the connection to RabbitMQ has
        been established. It passes the handle to the connection object in
        case we need it, but in this case, we'll just mark it unused.
        :param pika.SelectConnection _unused_connection: The connection
        """
        # LOGGER.info('Connection opened')
        print("Connected async")
        self.open_channel()

    def on_connection_open_error(self, _unused_connection, err):
        """This method is called by pika if the connection to RabbitMQ
        can't be established.
        :param pika.SelectConnection _unused_connection: The connection
        :param Exception err: The error
        """
        # LOGGER.error('Connection open failed, reopening in 5 seconds: %s', err)
        print('Connection open failed, reopening in 5 seconds: %s', err)
        self._connection.ioloop.call_later(5, self._connection.ioloop.stop)

    def on_connection_closed(self, _unused_connection, reason):
        """This method is invoked by pika when the connection to RabbitMQ is
        closed unexpectedly. Since it is unexpected, we will reconnect to
        RabbitMQ if it disconnects.
        :param pika.connection.Connection connection: The closed connection obj
        :param Exception reason: exception representing reason for loss of
            connection.
        """
        self._channel = None
        if self._stopping:
            print("Channel Closed. Not reopening. ", reason)
            self._connection.ioloop.stop()
        else:
            # LOGGER.warning('Connection closed, reopening in 5 seconds: %s',
                        #    reason)
            print('Connection closed, reopening in 5 seconds: %s', reason)
            self._connection.ioloop.call_later(5, self._connection.ioloop.stop)

    def open_channel(self):
        """This method will open a new channel with RabbitMQ by issuing the
        Channel.Open RPC command. When RabbitMQ confirms the channel is open
        by sending the Channel.OpenOK RPC reply, the on_channel_open method
        will be invoked.
        """
        # LOGGER.info('Creating a new channel')
        print("Creating new channel")
        self._connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel):
        """This method is invoked by pika when the channel has been opened.
        The channel object is passed in so we can make use of it.
        Since the channel is now open, we'll declare the exchange to use.
        :param pika.channel.Channel channel: The channel object
        """
        # LOGGER.info('Channel opened')
        print("Channel Opened")
        self._channel = channel
        self.add_on_channel_close_callback()
        self.setup_exchange(self.EXCHANGE)

    def add_on_channel_close_callback(self):
        """This method tells pika to call the on_channel_closed method if
        RabbitMQ unexpectedly closes the channel.
        """
        # LOGGER.info('Adding channel close callback')
        self._channel.add_on_close_callback(self.on_channel_closed)

    def on_channel_closed(self, channel, reason):
        """Invoked by pika when RabbitMQ unexpectedly closes the channel.
        Channels are usually closed if you attempt to do something that
        violates the protocol, such as re-declare an exchange or queue with
        different parameters. In this case, we'll close the connection
        to shutdown the object.
        :param pika.channel.Channel channel: The closed channel
        :param Exception reason: why the channel was closed
        """
        # LOGGER.warning('Channel %i was closed: %s', channel, reason)
        print('Channel %i was closed: %s', channel, reason)
        self._channel = None
        if not self._stopping:
            self._connection.close()

    def setup_exchange(self, exchange_name):
        """Setup the exchange on RabbitMQ by invoking the Exchange.Declare RPC
        command. When it is complete, the on_exchange_declareok method will
        be invoked by pika.
        :param str|unicode exchange_name: The name of the exchange to declare
        """
        # LOGGER.info('Declaring exchange %s', exchange_name)
        # Note: using functools.partial is not required, it is demonstrating
        # how arbitrary data can be passed to the callback when it is called
        print('Declaring exchange %s', exchange_name)
        cb = functools.partial(
            self.on_exchange_declareok, userdata=exchange_name)
        self._channel.exchange_declare(
            exchange=exchange_name,
            exchange_type=self.EXCHANGE_TYPE,
            callback=cb)

    def on_exchange_declareok(self, _unused_frame, userdata):
        """Invoked by pika when RabbitMQ has finished the Exchange.Declare RPC
        command.
        :param pika.Frame.Method unused_frame: Exchange.DeclareOk response frame
        :param str|unicode userdata: Extra user data (exchange name)
        """
        # LOGGER.info('Exchange declared: %s', userdata)
        self.setup_queue(self.QUEUE)

    def setup_queue(self, queue_name):
        """Setup the queue on RabbitMQ by invoking the Queue.Declare RPC
        command. When it is complete, the on_queue_declareok method will
        be invoked by pika.
        :param str|unicode queue_name: The name of the queue to declare.
        """
        # LOGGER.info('Declaring queue %s', queue_name)
        self._channel.queue_declare(
            queue=queue_name, callback=self.on_queue_declareok)

    def on_queue_declareok(self, _unused_frame):
        """Method invoked by pika when the Queue.Declare RPC call made in
        setup_queue has completed. In this method we will bind the queue
        and exchange together with the routing key by issuing the Queue.Bind
        RPC command. When this command is complete, the on_bindok method will
        be invoked by pika.
        :param pika.frame.Method method_frame: The Queue.DeclareOk frame
        """
        # LOGGER.info('Binding %s to %s with %s', self.EXCHANGE, self.QUEUE,
                    # self.ROUTING_KEY)
        self._channel.queue_bind(
            self.QUEUE,
            self.EXCHANGE,
            routing_key=self.ROUTING_KEY,
            callback=self.on_bindok)

    def on_bindok(self, _unused_frame):
        """This method is invoked by pika when it receives the Queue.BindOk
        response from RabbitMQ. Since we know we're now setup and bound, it's
        time to start publishing."""
        # LOGGER.info('Queue bound')
        self.start_publishing()

    def start_publishing(self):
        """This method will enable delivery confirmations and schedule the
        first message to be sent to RabbitMQ
        """
        # LOGGER.info('Issuing consumer related RPC commands')
        self.enable_delivery_confirmations()
        self.schedule_next_message()

    def enable_delivery_confirmations(self):
        """Send the Confirm.Select RPC method to RabbitMQ to enable delivery
        confirmations on the channel. The only way to turn this off is to close
        the channel and create a new one.
        When the message is confirmed from RabbitMQ, the
        on_delivery_confirmation method will be invoked passing in a Basic.Ack
        or Basic.Nack method from RabbitMQ that will indicate which messages it
        is confirming or rejecting.
        """
        # LOGGER.info('Issuing Confirm.Select RPC command')
        self._channel.confirm_delivery(self.on_delivery_confirmation)

    def on_delivery_confirmation(self, method_frame):
        """Invoked by pika when RabbitMQ responds to a Basic.Publish RPC
        command, passing in either a Basic.Ack or Basic.Nack frame with
        the delivery tag of the message that was published. The delivery tag
        is an integer counter indicating the message number that was sent
        on the channel via Basic.Publish. Here we're just doing house keeping
        to keep track of stats and remove message numbers that we expect
        a delivery confirmation of from the list used to keep track of messages
        that are pending confirmation.
        :param pika.frame.Method method_frame: Basic.Ack or Basic.Nack frame
        """
        confirmation_type = method_frame.method.NAME.split('.')[1].lower()
        # LOGGER.info('Received %s for delivery tag: %i', confirmation_type,
                    # method_frame.method.delivery_tag)
        if confirmation_type == 'ack':
            self._acked += 1
        elif confirmation_type == 'nack':
            self._nacked += 1
        self._deliveries.remove(method_frame.method.delivery_tag)
        # LOGGER.info(
            # 'Published %i messages, %i have yet to be confirmed, '
            # '%i were acked and %i were nacked', self._message_number,
            # len(self._deliveries), self._acked, self._nacked)

    def schedule_next_message(self):
        """If we are not closing our connection to RabbitMQ, schedule another
        message to be delivered in PUBLISH_INTERVAL seconds.
        """
        # LOGGER.info('Scheduling next message for %0.1f seconds',
                    # self.PUBLISH_INTERVAL)
        self._connection.ioloop.call_later(self.PUBLISH_INTERVAL,
                                           self.publish_message)

    def publish_message(self, message):
        """If the class is not stopping, publish a message to RabbitMQ,
        appending a list of deliveries with the message number that was sent.
        This list will be used to check for delivery confirmations in the
        on_delivery_confirmations method.
        Once the message has been sent, schedule another message to be sent.
        The main reason I put scheduling in was just so you can get a good idea
        of how the process is flowing by slowing down and speeding up the
        delivery intervals by changing the PUBLISH_INTERVAL constant in the
        class.
        """
        if self._channel is None or not self._channel.is_open:
            print("Channel is None")
            return

        hdrs = {}
        properties = pika.BasicProperties(
            app_id='example-publisher',
            content_type='application/json',
            headers=hdrs)


        self._channel.basic_publish(self.EXCHANGE, self.ROUTING_KEY,
                                    json.dumps(message, ensure_ascii=False),
                                    properties)
        self._message_number += 1
        self._deliveries.append(self._message_number)
        # LOGGER.info('Published message # %i', self._message_number)

    async def run(self):
        """Run the example code by connecting and then starting the IOLoop.
        """
        while not self._stopping:
            self._connection = None
            self._deliveries = []
            self._acked = 0
            self._nacked = 0
            self._message_number = 0

            try:
                self._connection = self.connect()
                self._connection.ioloop.start()
            except KeyboardInterrupt:
                self.stop()
                if (self._connection is not None and
                        not self._connection.is_closed):
                    # Finish closing
                    self._connection.ioloop.start()


    def stop(self):
        """Stop the example by closing the channel and connection. We
        set a flag here so that we stop scheduling new messages to be
        published. The IOLoop is started because this method is
        invoked by the Try/Catch below when KeyboardInterrupt is caught.
        Starting the IOLoop again will allow the publisher to cleanly
        disconnect from RabbitMQ.
        """
        # LOGGER.info('Stopping')
        self._stopping = True
        self.close_channel()
        self.close_connection()

    def close_channel(self):
        """Invoke this command to close the channel with RabbitMQ by sending
        the Channel.Close RPC command.
        """
        if self._channel is not None:
            # LOGGER.info('Closing the channel')
            self._channel.close()

    def close_connection(self):
        """This method closes the connection to RabbitMQ."""
        if self._connection is not None:
            # LOGGER.info('Closing connection')
            self._connection.close()
            
######################################### Generated Permissions ########################################
import re
from django.conf import settings
from django.db import models
from .functions import getUpper, checkList, returnList
from django.contrib.auth.models import Permission

APP_NAMES = settings.INSTALLED_APPS

class Groups(models.TextChoices):
    SUPERUSER = "SUPERUSER", "Super User"
    ADMIN_MODERATOR = "ADMIN_MODERATOR", "Moderator Admin"
    SIMPLE_MODERATOR = "SIMPLE_MODERATOR", "Moderator"    

class Permissions: 
    CHAT_MODERATOR_TIMESTAMPEDMODEL_CREATE__CREATED_ON = "CHAT_MODERATOR.TIMESTAMPEDMODEL.CREATE__CREATED_ON"
    CHAT_MODERATOR_TIMESTAMPEDMODEL_RETRIEVE__CREATED_ON = "CHAT_MODERATOR.TIMESTAMPEDMODEL.RETRIEVE__CREATED_ON"
    CHAT_MODERATOR_TIMESTAMPEDMODEL_UPDATE__CREATED_ON = "CHAT_MODERATOR.TIMESTAMPEDMODEL.UPDATE__CREATED_ON"
    CHAT_MODERATOR_TIMESTAMPEDMODEL_DELETE__CREATED_ON = "CHAT_MODERATOR.TIMESTAMPEDMODEL.DELETE__CREATED_ON"
    CHAT_MODERATOR_TIMESTAMPEDMODEL_CREATE__UPDATED_ON = "CHAT_MODERATOR.TIMESTAMPEDMODEL.CREATE__UPDATED_ON"
    CHAT_MODERATOR_TIMESTAMPEDMODEL_RETRIEVE__UPDATED_ON = "CHAT_MODERATOR.TIMESTAMPEDMODEL.RETRIEVE__UPDATED_ON"
    CHAT_MODERATOR_TIMESTAMPEDMODEL_UPDATE__UPDATED_ON = "CHAT_MODERATOR.TIMESTAMPEDMODEL.UPDATE__UPDATED_ON"
    CHAT_MODERATOR_TIMESTAMPEDMODEL_DELETE__UPDATED_ON = "CHAT_MODERATOR.TIMESTAMPEDMODEL.DELETE__UPDATED_ON"
    CHAT_MODERATOR_MODERATIONBASE_CREATE__STATUS = "CHAT_MODERATOR.MODERATIONBASE.CREATE__STATUS"
    CHAT_MODERATOR_MODERATIONBASE_RETRIEVE__STATUS = "CHAT_MODERATOR.MODERATIONBASE.RETRIEVE__STATUS"
    CHAT_MODERATOR_MODERATIONBASE_UPDATE__STATUS = "CHAT_MODERATOR.MODERATIONBASE.UPDATE__STATUS"
    CHAT_MODERATOR_MODERATIONBASE_DELETE__STATUS = "CHAT_MODERATOR.MODERATIONBASE.DELETE__STATUS"
    CHAT_MODERATOR_CHANNEL_CREATE__CONTENT = "CHAT_MODERATOR.CHANNEL.CREATE__CONTENT"
    CHAT_MODERATOR_CHANNEL_RETRIEVE__CONTENT = "CHAT_MODERATOR.CHANNEL.RETRIEVE__CONTENT"
    CHAT_MODERATOR_CHANNEL_UPDATE__CONTENT = "CHAT_MODERATOR.CHANNEL.UPDATE__CONTENT"
    CHAT_MODERATOR_CHANNEL_DELETE__CONTENT = "CHAT_MODERATOR.CHANNEL.DELETE__CONTENT"
    CHAT_MODERATOR_CHANNEL_CREATE__NAME = "CHAT_MODERATOR.CHANNEL.CREATE__NAME"
    CHAT_MODERATOR_CHANNEL_RETRIEVE__NAME = "CHAT_MODERATOR.CHANNEL.RETRIEVE__NAME"
    CHAT_MODERATOR_CHANNEL_UPDATE__NAME = "CHAT_MODERATOR.CHANNEL.UPDATE__NAME"
    CHAT_MODERATOR_CHANNEL_DELETE__NAME = "CHAT_MODERATOR.CHANNEL.DELETE__NAME"
    CHAT_MODERATOR_CHANNEL_CREATE__USER_IDS = "CHAT_MODERATOR.CHANNEL.CREATE__USER_IDS"
    CHAT_MODERATOR_CHANNEL_RETRIEVE__USER_IDS = "CHAT_MODERATOR.CHANNEL.RETRIEVE__USER_IDS"
    CHAT_MODERATOR_CHANNEL_UPDATE__USER_IDS = "CHAT_MODERATOR.CHANNEL.UPDATE__USER_IDS"
    CHAT_MODERATOR_CHANNEL_DELETE__USER_IDS = "CHAT_MODERATOR.CHANNEL.DELETE__USER_IDS"
    CHAT_MODERATOR_CHANNEL_CREATE__IS_UNDER_MODERATION = "CHAT_MODERATOR.CHANNEL.CREATE__IS_UNDER_MODERATION"
    CHAT_MODERATOR_CHANNEL_RETRIEVE__IS_UNDER_MODERATION = "CHAT_MODERATOR.CHANNEL.RETRIEVE__IS_UNDER_MODERATION"
    CHAT_MODERATOR_CHANNEL_UPDATE__IS_UNDER_MODERATION = "CHAT_MODERATOR.CHANNEL.UPDATE__IS_UNDER_MODERATION"
    CHAT_MODERATOR_CHANNEL_DELETE__IS_UNDER_MODERATION = "CHAT_MODERATOR.CHANNEL.DELETE__IS_UNDER_MODERATION"
    CHAT_MODERATOR_CONTENT_CREATE__REJECTEDCATEGORY = "CHAT_MODERATOR.CONTENT.CREATE__REJECTEDCATEGORY"
    CHAT_MODERATOR_CONTENT_RETRIEVE__REJECTEDCATEGORY = "CHAT_MODERATOR.CONTENT.RETRIEVE__REJECTEDCATEGORY"
    CHAT_MODERATOR_CONTENT_UPDATE__REJECTEDCATEGORY = "CHAT_MODERATOR.CONTENT.UPDATE__REJECTEDCATEGORY"
    CHAT_MODERATOR_CONTENT_DELETE__REJECTEDCATEGORY = "CHAT_MODERATOR.CONTENT.DELETE__REJECTEDCATEGORY"
    CHAT_MODERATOR_CONTENT_CREATE__ID = "CHAT_MODERATOR.CONTENT.CREATE__ID"
    CHAT_MODERATOR_CONTENT_RETRIEVE__ID = "CHAT_MODERATOR.CONTENT.RETRIEVE__ID"
    CHAT_MODERATOR_CONTENT_UPDATE__ID = "CHAT_MODERATOR.CONTENT.UPDATE__ID"
    CHAT_MODERATOR_CONTENT_DELETE__ID = "CHAT_MODERATOR.CONTENT.DELETE__ID"
    CHAT_MODERATOR_CONTENT_CREATE__CREATED_ON = "CHAT_MODERATOR.CONTENT.CREATE__CREATED_ON"
    CHAT_MODERATOR_CONTENT_RETRIEVE__CREATED_ON = "CHAT_MODERATOR.CONTENT.RETRIEVE__CREATED_ON"
    CHAT_MODERATOR_CONTENT_UPDATE__CREATED_ON = "CHAT_MODERATOR.CONTENT.UPDATE__CREATED_ON"
    CHAT_MODERATOR_CONTENT_DELETE__CREATED_ON = "CHAT_MODERATOR.CONTENT.DELETE__CREATED_ON"
    CHAT_MODERATOR_CONTENT_CREATE__UPDATED_ON = "CHAT_MODERATOR.CONTENT.CREATE__UPDATED_ON"
    CHAT_MODERATOR_CONTENT_RETRIEVE__UPDATED_ON = "CHAT_MODERATOR.CONTENT.RETRIEVE__UPDATED_ON"
    CHAT_MODERATOR_CONTENT_UPDATE__UPDATED_ON = "CHAT_MODERATOR.CONTENT.UPDATE__UPDATED_ON"
    CHAT_MODERATOR_CONTENT_DELETE__UPDATED_ON = "CHAT_MODERATOR.CONTENT.DELETE__UPDATED_ON"
    CHAT_MODERATOR_CONTENT_CREATE__STATUS = "CHAT_MODERATOR.CONTENT.CREATE__STATUS"
    CHAT_MODERATOR_CONTENT_RETRIEVE__STATUS = "CHAT_MODERATOR.CONTENT.RETRIEVE__STATUS"
    CHAT_MODERATOR_CONTENT_UPDATE__STATUS = "CHAT_MODERATOR.CONTENT.UPDATE__STATUS"
    CHAT_MODERATOR_CONTENT_DELETE__STATUS = "CHAT_MODERATOR.CONTENT.DELETE__STATUS"
    CHAT_MODERATOR_CONTENT_CREATE__CLIENT_CONTENT_ID = "CHAT_MODERATOR.CONTENT.CREATE__CLIENT_CONTENT_ID"
    CHAT_MODERATOR_CONTENT_RETRIEVE__CLIENT_CONTENT_ID = "CHAT_MODERATOR.CONTENT.RETRIEVE__CLIENT_CONTENT_ID"
    CHAT_MODERATOR_CONTENT_UPDATE__CLIENT_CONTENT_ID = "CHAT_MODERATOR.CONTENT.UPDATE__CLIENT_CONTENT_ID"
    CHAT_MODERATOR_CONTENT_DELETE__CLIENT_CONTENT_ID = "CHAT_MODERATOR.CONTENT.DELETE__CLIENT_CONTENT_ID"
    CHAT_MODERATOR_CONTENT_CREATE__SENDER_UUID = "CHAT_MODERATOR.CONTENT.CREATE__SENDER_UUID"
    CHAT_MODERATOR_CONTENT_RETRIEVE__SENDER_UUID = "CHAT_MODERATOR.CONTENT.RETRIEVE__SENDER_UUID"
    CHAT_MODERATOR_CONTENT_UPDATE__SENDER_UUID = "CHAT_MODERATOR.CONTENT.UPDATE__SENDER_UUID"
    CHAT_MODERATOR_CONTENT_DELETE__SENDER_UUID = "CHAT_MODERATOR.CONTENT.DELETE__SENDER_UUID"
    CHAT_MODERATOR_CONTENT_CREATE__CONTENT_TYPE = "CHAT_MODERATOR.CONTENT.CREATE__CONTENT_TYPE"
    CHAT_MODERATOR_CONTENT_RETRIEVE__CONTENT_TYPE = "CHAT_MODERATOR.CONTENT.RETRIEVE__CONTENT_TYPE"
    CHAT_MODERATOR_CONTENT_UPDATE__CONTENT_TYPE = "CHAT_MODERATOR.CONTENT.UPDATE__CONTENT_TYPE"
    CHAT_MODERATOR_CONTENT_DELETE__CONTENT_TYPE = "CHAT_MODERATOR.CONTENT.DELETE__CONTENT_TYPE"
    CHAT_MODERATOR_CONTENT_CREATE__CONTENT = "CHAT_MODERATOR.CONTENT.CREATE__CONTENT"
    CHAT_MODERATOR_CONTENT_RETRIEVE__CONTENT = "CHAT_MODERATOR.CONTENT.RETRIEVE__CONTENT"
    CHAT_MODERATOR_CONTENT_UPDATE__CONTENT = "CHAT_MODERATOR.CONTENT.UPDATE__CONTENT"
    CHAT_MODERATOR_CONTENT_DELETE__CONTENT = "CHAT_MODERATOR.CONTENT.DELETE__CONTENT"
    CHAT_MODERATOR_CONTENT_CREATE__CHANNEL = "CHAT_MODERATOR.CONTENT.CREATE__CHANNEL"
    CHAT_MODERATOR_CONTENT_RETRIEVE__CHANNEL = "CHAT_MODERATOR.CONTENT.RETRIEVE__CHANNEL"
    CHAT_MODERATOR_CONTENT_UPDATE__CHANNEL = "CHAT_MODERATOR.CONTENT.UPDATE__CHANNEL"
    CHAT_MODERATOR_CONTENT_DELETE__CHANNEL = "CHAT_MODERATOR.CONTENT.DELETE__CHANNEL"
    CHAT_MODERATOR_CONTENT_CREATE__FEEDBACK = "CHAT_MODERATOR.CONTENT.CREATE__FEEDBACK"
    CHAT_MODERATOR_CONTENT_RETRIEVE__FEEDBACK = "CHAT_MODERATOR.CONTENT.RETRIEVE__FEEDBACK"
    CHAT_MODERATOR_CONTENT_UPDATE__FEEDBACK = "CHAT_MODERATOR.CONTENT.UPDATE__FEEDBACK"
    CHAT_MODERATOR_CONTENT_DELETE__FEEDBACK = "CHAT_MODERATOR.CONTENT.DELETE__FEEDBACK"
    CHAT_MODERATOR_REJECTEDCATEGORY_CREATE__ID = "CHAT_MODERATOR.REJECTEDCATEGORY.CREATE__ID"
    CHAT_MODERATOR_REJECTEDCATEGORY_RETRIEVE__ID = "CHAT_MODERATOR.REJECTEDCATEGORY.RETRIEVE__ID"
    CHAT_MODERATOR_REJECTEDCATEGORY_UPDATE__ID = "CHAT_MODERATOR.REJECTEDCATEGORY.UPDATE__ID"
    CHAT_MODERATOR_REJECTEDCATEGORY_DELETE__ID = "CHAT_MODERATOR.REJECTEDCATEGORY.DELETE__ID"
    CHAT_MODERATOR_REJECTEDCATEGORY_CREATE__NAME = "CHAT_MODERATOR.REJECTEDCATEGORY.CREATE__NAME"
    CHAT_MODERATOR_REJECTEDCATEGORY_RETRIEVE__NAME = "CHAT_MODERATOR.REJECTEDCATEGORY.RETRIEVE__NAME"
    CHAT_MODERATOR_REJECTEDCATEGORY_UPDATE__NAME = "CHAT_MODERATOR.REJECTEDCATEGORY.UPDATE__NAME"
    CHAT_MODERATOR_REJECTEDCATEGORY_DELETE__NAME = "CHAT_MODERATOR.REJECTEDCATEGORY.DELETE__NAME"
    CHAT_MODERATOR_REJECTEDCATEGORY_CREATE__REF_CONTENT = "CHAT_MODERATOR.REJECTEDCATEGORY.CREATE__REF_CONTENT"
    CHAT_MODERATOR_REJECTEDCATEGORY_RETRIEVE__REF_CONTENT = "CHAT_MODERATOR.REJECTEDCATEGORY.RETRIEVE__REF_CONTENT"
    CHAT_MODERATOR_REJECTEDCATEGORY_UPDATE__REF_CONTENT = "CHAT_MODERATOR.REJECTEDCATEGORY.UPDATE__REF_CONTENT"
    CHAT_MODERATOR_REJECTEDCATEGORY_DELETE__REF_CONTENT = "CHAT_MODERATOR.REJECTEDCATEGORY.DELETE__REF_CONTENT"
    APP_ADMIN_MODERATINGUSER_CREATE__ID = "APP_ADMIN.MODERATINGUSER.CREATE__ID"
    APP_ADMIN_MODERATINGUSER_RETRIEVE__ID = "APP_ADMIN.MODERATINGUSER.RETRIEVE__ID"
    APP_ADMIN_MODERATINGUSER_UPDATE__ID = "APP_ADMIN.MODERATINGUSER.UPDATE__ID"
    APP_ADMIN_MODERATINGUSER_DELETE__ID = "APP_ADMIN.MODERATINGUSER.DELETE__ID"
    APP_ADMIN_MODERATINGUSER_CREATE__REF_USER_ID = "APP_ADMIN.MODERATINGUSER.CREATE__REF_USER_ID"
    APP_ADMIN_MODERATINGUSER_RETRIEVE__REF_USER_ID = "APP_ADMIN.MODERATINGUSER.RETRIEVE__REF_USER_ID"
    APP_ADMIN_MODERATINGUSER_UPDATE__REF_USER_ID = "APP_ADMIN.MODERATINGUSER.UPDATE__REF_USER_ID"
    APP_ADMIN_MODERATINGUSER_DELETE__REF_USER_ID = "APP_ADMIN.MODERATINGUSER.DELETE__REF_USER_ID"
    APP_ADMIN_MODERATINGUSER_CREATE__ROLE = "APP_ADMIN.MODERATINGUSER.CREATE__ROLE"
    APP_ADMIN_MODERATINGUSER_RETRIEVE__ROLE = "APP_ADMIN.MODERATINGUSER.RETRIEVE__ROLE"
    APP_ADMIN_MODERATINGUSER_UPDATE__ROLE = "APP_ADMIN.MODERATINGUSER.UPDATE__ROLE"
    APP_ADMIN_MODERATINGUSER_DELETE__ROLE = "APP_ADMIN.MODERATINGUSER.DELETE__ROLE"
    APP_ADMIN_MODERATINGUSER_CREATE__TOKEN = "APP_ADMIN.MODERATINGUSER.CREATE__TOKEN"
    APP_ADMIN_MODERATINGUSER_RETRIEVE__TOKEN = "APP_ADMIN.MODERATINGUSER.RETRIEVE__TOKEN"
    APP_ADMIN_MODERATINGUSER_UPDATE__TOKEN = "APP_ADMIN.MODERATINGUSER.UPDATE__TOKEN"
    APP_ADMIN_MODERATINGUSER_DELETE__TOKEN = "APP_ADMIN.MODERATINGUSER.DELETE__TOKEN"
 
    @staticmethod
    def get_pattern(app_name, model_name, field_name, perm_type):
        getReg = lambda s: "[A-Z]+" if s=="*" else s
        app_name = getReg(app_name)
        model_name = getReg(model_name)
        field_name = getReg(field_name)
        perm_type = getReg(perm_type)
        return re.compile(f"{app_name}_{model_name}_{perm_type}__{field_name}")

    @classmethod
    def get_permissions(cls, app_names="*", model_names="*", field_names="*", permissions="*"):
        # Parse the parameters
        field_names = checkList(returnList(getUpper(field_names)))
        app_names = checkList(returnList(getUpper(app_names)))
        model_names = checkList(returnList(getUpper(model_names)))
        permissions = checkList(returnList(getUpper(permissions)))
        
        if "*" in app_names:
            app_names = getUpper(APP_NAMES)
        
        # If we have multiple apps, then no sense to specify multiple models; Similar logic for (models, fields)
        if "*" in app_names or len(app_names)>1:
            model_names = ["*",]
        if "*" in model_names or len(model_names)>1:
            field_names = ["*",]
            
        # Create List to store processed data
        returned_permissions = []
        
        # Iterate over Parameters
        for app in app_names:
            for model in model_names:
                for field in field_names:
                    for perm in permissions:
                        pat = cls.get_pattern(app, model, field, perm)
                        attrs = list(filter(pat.match, cls.__dict__.keys()))
                        for attr in attrs:
                            returned_permissions.append(getattr(cls, attr))
        # print(returned_permissions)
        return returned_permissions
    
    @classmethod
    def get_all_permissions(cls):
        return cls.get_permissions("*", "*", "*", "*")
    
    @classmethod
    def get_group_names_with_permission(cls, permission):
        pass


class GroupPermissions:
    BASE_MODERATOR = []
    SIMPLE_MODERATOR = list(BASE_MODERATOR + [
        *Permissions.get_permissions('chat_moderator', 'rejectedcategory'),
        *Permissions.get_permissions('chat_moderator', 'content', ['id', 'content', 'content_type'], ['retrieve']),
        *Permissions.get_permissions('chat_moderator', 'content', ['feedback', 'status'], "*"),
    ])
    ADMIN_MODERATOR = list(SIMPLE_MODERATOR + [
        *Permissions.get_permissions('chat_moderator', 'channel'),
        *Permissions.get_permissions('chat_moderator', 'content'),
        *Permissions.get_permissions('chat_moderator', 'rejectedcategory'),
        *Permissions.get_permissions('app_admin', 'moderatinguser'),
    ])
    SUPERUSER = Permissions.get_all_permissions()

    @staticmethod
    def SM(cls):
        return cls.SIMPLE_MODERATOR
    
    @staticmethod
    def AM(cls):
        return cls.ADMIN_MODERATOR
    
    @staticmethod
    def SU(cls):
        return cls.SUPER_USER

################################## Permission Generator ################################3
import SocialService.settings as settings
from django.db import models
from pprint import pprint
from app_admin.models import Permission
from django.contrib.contenttypes.models import ContentType

actions = ['create',  'retrieve', 'update', 'delete']
app_names = settings.INSTALLED_APPS[-1*(settings.NUM_APPS):]


def get_app_models(app_name):
    exec(f"import {app_name}.models as app_name_models")
    app_models = []
    app_name_models_local = locals()["app_name_models"]
    for content in app_name_models_local.__dir__():
        cmd = f"modelClass = app_name_models_local.{content}"
        exec(cmd)
        modelClass_local = locals()["modelClass"]
        try:
            if issubclass(modelClass_local, models.Model):
                app_models.append(modelClass_local)
        except:
            pass
    return app_models
            
def field_names(app_model):
    return [f.name for f in app_model._meta.get_fields()]


def write_permissions(verbose=False):
    permission_class = None
    if verbose:
        permission_class = """
class Permissions:
"""
    permission_list = []
    for app_name in app_names:
        for app_model in get_app_models(app_name):
            model_name = str(app_model._meta.verbose_name)
            try:   
                content_type, _ = ContentType.objects.get_or_create(app_label=app_name.lower(), model=model_name)
                if content_type.app_label == '' or content_type.model is None or content_type.model == '':
                    raise Exception ("Custom exception")
            except Exception as e:
                print(app_model, e)
                continue
            
            for field_name in field_names(app_model):
                for action in actions:
                    try:
                        name = f"Can {action} {model_name.lower().capitalize()}'s {field_name}"
                        codename = f"{action}.{model_name.lower().capitalize()}.{field_name}"
                        permission_list.append(Permission.objects.get_or_create(content_type=content_type, codename=codename, name=name)[0])
                    except:
                        pass
                    if verbose:
                        permission_base = f"\"{app_name.upper()}.{model_name.upper()}.{action.upper()}__{field_name.upper()}\""
                        permission_head = f"{app_name.upper()}_{model_name.upper()}_{action.upper()}__{field_name.upper()}"
                        permission_list.append(permission_base)
                        permission_class += f"""\t{permission_head} = {permission_base}\n"""
    return permission_class, permission_list

def write_permissions():
    permission_list = []
    for app_name in app_names:
        for app_model in get_app_models(app_name):
            try:
                content_type, _ = ContentType.objects.get_or_create(app_label=app_name.lower(), model=app_model)
            except Exception as e:
                print(app_model, ":", e, ".....Next model.....")
                continue
            for field_name in field_names(app_model):
                for action in actions:
                    try:
                        name = f"Can {action} {app_model.__name__.lower().capitalize()}'s {field_name}"
                        codename = f"{action}.{app_model.__name__.lower().capitalize()}.{field_name}"
                        permission_list.append(Permission.objects.create(content_type=content_type, codename=codename, name=name))
                    except:
                        pass
            print(app_model, "Finished")
    return permission_list

####################################### Pubnub ###############################################
from unicodedata import name
from venv import create
from pubnub.exceptions import PubNubException
from pubnub.callbacks import SubscribeCallback
from pubnub.pubnub import PNStatusCategory

from datetime import datetime
from requests import request

from uritemplate import partial
from chat_moderator.models import Content
from chat_moderator.serializers import ContentSerializer
from chat_moderator.models import Channel

def my_publish_callback(envelope, status, *args, **kwargs):
    # Check whether request successfully completed or not
    try:
        if not status.is_error():
            pass  # Message successfully published to specified channel.
        else:
            pass
            # Handle message publish error. Check 'category' property to find out possible issue
            # because of which request did fail.
            # Request can be resent using: [status retry];
    except Exception as e:
        print(e)
      
            
class MySubscribeCallback(SubscribeCallback):
    def presence(self, pubnub, presence):
        pass  # handle incoming presence data

    def status(self, pubnub, status):
        if status.category == PNStatusCategory.PNUnexpectedDisconnectCategory:
            pass  # This event happens when radio / connectivity is lost

        elif status.category == PNStatusCategory.PNConnectedCategory:
            # Connect event. You can do stuff like publish, and know you'll get it.
            # Or just use the connected event to confirm you are subscribed for
            # UI / internal notifications, etc
            pubnub.publish().channel('my_channel').message('Hello world!').pn_async(my_publish_callback)
        elif status.category == PNStatusCategory.PNReconnectedCategory:
            pass
            # Happens as part of our regular operation. This event happens when
            # radio / connectivity is lost, then regained.
        elif status.category == PNStatusCategory.PNDecryptionErrorCategory:
            pass
            # Handle message decryption error. Probably client configured to
            # encrypt messages and on live data feed it received plain text.

    def message(self, pubnub, message):
        # Handle new message stored in message.message
        if not Channel.objects.filter(name=message.message['channel']).exists():
            channel = Channel(name=message.message['channel'])
            channel.user_ids = [message.message['sender_uuid'],]
            channel.save()
        serializer = ContentSerializer(data=message.message, partial=True, context={"request": None})
        if serializer.is_valid():
            try:
                serializer.save()    
                print(f"Content Registered: \n\t{serializer.data}")
            except Exception as e:
                print(f"Encountered Exception: {e}")
        # Moderate Success
        return serializer

def send_pubnub_message(pubnub_service, content, direction="forward", server_feedback=None):
    """Sends the content object to the specified channel

    Args:
        content (Content) : An object of class Content
        direction (str, optional): Direction of message flow. Defaults to "forward". 
            Forward direction means send the message to the reciever
            Backward direction means send the message back to the sender
        server_feedback (str, optional): Send an optional feedback from the server side. 
            This could help client in putting things in places. Defaults to None.

    Returns:
        Boolean: True if message is sent successfully, else False
    """
    # The default and most-basic payload (Will be used on client side to uniquely identify a message) 
    payload = {
        "sender_uuid": str(content.sender_uuid),
        "channel": str(content.channel),
        "client_content_id": content.client_content_id,
        "meta": {
            "dispached_on": datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
            "feedback": server_feedback
        }
    }
    
    # Channel where message is to be sent
    channel =  f"channel__{content.sender_uuid}"
    
    # Augment default payload with content information before sending it to reciever
    update_payload = {}
    if direction=="forward":
        update_payload = {
            "content": str(content.content),
            "content_type": str(content.content_type),
            "status": content.status,
            "feedback": content.feedback,
        }
        channel = content.channel
        
    # Update the payload
    payload.update(update_payload)
    
    try:
        # Try to send the payload
        envelope = pubnub_service.publish().\
                        channel(payload["channel"]).\
                        message(payload).\
                        should_store(True).sync()
        # print("publish timetoken: %d" % envelope.result.timetoken)
        # print("SENT MESSAGE : ", payload)
        return True
    except PubNubException as e:
        # Log Exception if message not sent successfully
        # print("Pubnub Exception: ", e)
        return False

