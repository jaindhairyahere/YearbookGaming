# Library Imports
from django.conf import settings
from pika import URLParameters, BlockingConnection
from pika.exceptions import *
import logging

# Project Imports
from utils.defaults import MessageQueue

logging.getLogger('pika').setLevel(logging.ERROR)
class TicketConsumer:
    """Consumer Class that fetches the messages from the Message Queue
    
    This is an example consumer that will handle unexpected interactions
    with RabbitMQ such as channel and connection closures.
    If RabbitMQ closes the connection, this class will stop and indicate
    that reconnection is necessary. You should look at the output, as
    there are limited reasons why the connection may be closed, which
    usually are tied to permission related issues or socket timeouts.
    If the channel is closed, it will indicate a problem with one of the
    commands that were issued and that should surface in the output as well.
    """
    DEFAULT_QUEUE_NAME = getattr(settings, "DEFAULT_QUEUE_NAME", None) or MessageQueue.DEFAULT_QUEUE_NAME
    DEFAULT_EXCHANGE_NAME = getattr(settings, "DEFAULT_EXCHANGE_NAME", None) or MessageQueue.DEFAULT_EXCHANGE_NAME
    DEFAULT_EXCHANGE_TYPE = getattr(settings, "DEFAULT_EXCHANGE_TYPE", None) or MessageQueue.DEFAULT_EXCHANGE_TYPE
    DEFAULT_RECONNECTION_THRESHOLD = getattr(settings, "DEFAULT_RECONNECTION_THRESHOLD", None) or MessageQueue.DEFAULT_RECONNECTION_THRESHOLD
    DEFAULT_ROUTING_KEY = getattr(settings, "DEFAULT_ROUTING_KEY", None) or MessageQueue.DEFAULT_ROUTING_KEY
    
    def __init__(self, amqp_url, **kwargs):
        """Consumer Constructor

        Args:
            amqp_url (str): URL to the message queue service 
                Example: {amqp}://{username}:{password}@{host}:{port}/{virtual_host}
                
            kwargs: Optional Parameters. If they are not passed, then their default values are used
                    either from the `django.conf:settings` or from `utils.defaults`
                queue_name: The queue name to be used
                exchange_name: The exchange name to be used
                exchange_type: The exchange type to be used
                routing_key: The routing key to be used
        """
        self._host = amqp_url
        self._connection = None
        self._channel = None
        self._counter = 0
        self._queue = None
        self._queue_name = kwargs.pop("queue_name", None) or self.DEFAULT_QUEUE_NAME
        self._exchange_name = kwargs.pop("exchange_name", None) or self.DEFAULT_EXCHANGE_NAME
        self._exchange_type = kwargs.pop("exchange_type", None) or self.DEFAULT_EXCHANGE_TYPE
        self._routing_key = kwargs.pop("routing_key", None) or self.DEFAULT_ROUTING_KEY
    
    def close(self):
        """Closes the existing connections (if any) of the consumer isntance"""
        # Check if connection exists and is not closed; Close it in that case
        if self._connection is not None and not self._connection.is_closed:
            self._connection.close()
        # Again try to close the connection | Sanity check
        try:
            self._connection.close()
        except Exception as e:
            pass
        # Return if the connection is closed or just None
        return self._connection is None or self._connection.is_closed
    
    def connect(self):
        """Connects the consumer instance to the Message Queue by creating a new connection
        and destrocying/closing the older/existing connections"""
        # Create the parameters
        parameters = URLParameters(self._host)
        # Close any previous connections
        if not self.close():
            raise Exception("Couldn't close the connection")
        
        # Create a new Blocking Connection using the parameters
        self._connection = BlockingConnection(parameters)
        # Set up a new channel in the connection
        self._channel = self._connection.channel()
        # Set up an exchange to transfer messages
        self.setup_exchange()
    
    @property
    def queue(self):
        """Getter for ``self._queue``"""
        return self._queue
    
    def setup_exchange(self):
        """Sets up the exchange by delaring the exchange and the queue"""
        # Declare the exchange
        self._channel.exchange_declare(exchange=self._exchange_name, exchange_type=self._exchange_type)
        # Declare the queue
        self.queue_declare()
    
    def queue_declare(self):
        """Declares the queue"""
        # Declare the queue
        result = self._channel.queue_declare(queue=self._queue_name)
        # Store the resulting (returned) queue name in the consumer
        self._queue = result.method.queue
        # Bind the queue with the exchange and routing key
        self._channel.queue_bind(self._queue_name, self._exchange_name, self._routing_key)
    
    def reconnect(self):
        """Attempts to reconnect the consumer with the AMQP Message Queue

        Returns:
            bool: If reconnection was attempted successfully
        """
        # Reconnection is attempted if reconnection_counter is less than the threshold
        if self._counter<self.DEFAULT_RECONNECTION_THRESHOLD:
            # Try to connect
            self.connect()
            # Increment the reconnection counter
            self._counter += 1
            # Return True indicating successful reconnection attempt
            return True
        else:
            # Return False, indicating reconnection wasn't attempted
            return False
        
    def get_one_message(self):
        """Get/Dequeue a single message from the Message Queue

        Returns:
            dict: Message Object as a JSoN formatted string
        """
        # Get the message
        try:
            # Try to get a message
            method_frame, header_frame, body = self._channel.basic_get(queue = self.queue, auto_ack=False)      
        except (StreamLostError, AMQPChannelError, ConnectionClosed, ChannelClosed, ConnectionResetError):
            # Try reconnecting if not able to get a message. 
            # Return None if not able to reconnect
            if not self.reconnect():
                return None
            # If reconnection was succesful, try to get the message once again
            return self.get_one_message()    
        
        # Set the reconnection counter back to zero. This line signifies that
        # reconnection counter will be treated per message, i.e. Consumer tries
        # to reconnect THRESHOLD number of times just to get a single message.
        # If this is removed, then reconnection counter will serve as a global
        # counter, which will denote the total reconnection attempts made in the
        # process lifecycle, and that will require THRESHOLD to be very big number.
        self._counter = 0
        
        # If no message frame is returned, return empty message (None)
        if method_frame is None:
            return None
        if method_frame.NAME == 'Basic.GetEmpty':
            # If the queue was empty, return empty string
            return None
        else:
            # Decode the message consumed from the queue from byte string to python string
            self._channel.basic_ack(delivery_tag=method_frame.delivery_tag)
            return body.decode()
        
    def dequeue_messages(self, count=0):
        """Dequeue messages from the messages queue

        Args:
            count (int): Number of messages to be dequeued. Defaults to 0

        Returns:
            list(json_str): List of messages as a JSoN formatted string
        """
        # Store the messages
        bodies = []
        # Get a single message and append it to message list    
        for _ in range(count):
            message = self.get_one_message()
            bodies.append(message)
        # Return the messages
        return bodies
        