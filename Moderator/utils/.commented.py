############################# REBALANCING FUNCTION from app_admin.tasks.py ###############################3
@shared_task(name="tasks.rebalance", serializer="pickle")
def rebalance(*args, **kwargs):
    # from app_admin.celery import rebalance
    # rebalance(self)
    """Simple round robin / random allocation algo <=> Policy Less Distribution
    """
    # Step 1: Get all the available users, sort by their response time
    available_moderators = YearbookGamingModerator.objects.filter(is_mod_available=True).order_by('average_response_time')
    if not available_moderators.exists():
        print("No One is Online")
        # Some action when no one is online
        return
    
    # Step 2: Get all the under_reveiw Contents
    contents = Content.objects.filter(status = ModerationStates.UNDER_REVIEW).order_by('-time', 'updated_on')
    
    # Step 3: Get the required time (current - timedelta of 10 mins)
    last_updated_time = timezone.now() - timezone.timedelta(minutes=10)
    
    # Step 3: Get all the moderation tickets that either are associated with the\
        # available moderators\
        # under_review content\
        # updated_on < last_updated_time\
        # unassigned tickets (when content is just created)
        # moderator free for 10 mins
    mod_onl_q = Q(moderator__in = available_moderators)
    cont_in_q = Q(content__in = contents)
    timedel_q = Q(updated_on__lt = last_updated_time)
    unassig_q = Q(moderator = None)
    mod_upd_q = Q(moderator__updated_on__lt = last_updated_time)
    
    tickets = ModerationTicket.objects.filter(
        mod_onl_q | cont_in_q | timedel_q | unassig_q | mod_upd_q
    ).distinct()
    
    
    # Req 2: Moderator if free for more than 10 mins should be allocated more contents
    # moderator_free_tickets = tickets.filter(Q(moderator_updated_on__lt = (current_time-timedelta)))
    
    # Step 3: Define Allotment Conditions
    
    # Condition 1: Num Available Moderators >= Num contents (Rarely Possible) => Allot line by line
    if available_moderators.count() >= tickets.count():
        for ticket in tickets:
            if ticket.moderator is not None:
                ticket.is_expired = True
        for ti in range(tickets.count()):
            tickets[ti].is_expired = True
            old_moderator = tickets[ti].moderator
            if old_moderator is not None:
                num_tickets_old_moderator = ModerationTicket.objects.filter(moderator = old_moderator).count()
                old_moderator.average_response_time = (old_moderator.average_response_time*num_tickets_old_moderator + 6e5)/(num_tickets_old_moderator+1)
                content = tickets[ti].content
                moderator = available_moderators[ti]
                new_ticket, created = ModerationTicket.objects.get_or_create(moderator = moderator, content = content)
                if not created:
                    new_ticket.is_expired = False
                    new_ticket.save()
            else:
                moderator = YearbookGamingModerator.get_moderator()
                tickets[ti].moderator = moderator
                tickets[ti].save()
         
    # Condition 2: Num contents = K * Num Available Modetators + R, where K>1
    else:
        K = tickets.count() // available_moderators.count()
        R = tickets.count() % available_moderators.count()
        start = 0
        for moderator_index in range(available_moderators.count()):
            moderator = available_moderators[moderator_index]
            for ti in range(K):            
                old_moderator = tickets[start+ti].moderator
                if old_moderator is not None:
                    num_tickets_old_moderator = ModerationTicket.objects.filter(moderator = old_moderator).count()
                    old_moderator.average_response_time = (old_moderator.average_response_time*num_tickets_old_moderator + 6e5)/(num_tickets_old_moderator+1)
                    content = tickets[ti].content
                    new_ticket, created = ModerationTicket.objects.get_or_create(moderator = moderator, content = content)
                    if not created:
                        new_ticket.is_expired = False
                        new_ticket.save()
                else:                    
                    moderator = YearbookGamingModerator.get_moderator()
                    tickets[ti].moderator = moderator
                    tickets[ti].save()
            start += K
        for ti in range(R):
            tickets[start+ti].is_expired = True
            old_moderator = tickets[start+ti].moderator
            num_tickets_old_moderator = ModerationTicket.objects.filter(moderator = old_moderator).count()
            if old_moderator is not None:
                old_moderator.average_response_time = (old_moderator.average_response_time*num_tickets_old_moderator + 6e5)/(num_tickets_old_moderator+1)
                content = tickets[start+ti].content
                moderator = available_moderators[ti]
                new_ticket, created = ModerationTicket.objects.get_or_create(moderator = moderator, content = content)
                if not created:
                    new_ticket.is_expired = False
                    new_ticket.save()
            else: 
                moderator = YearbookGamingModerator.get_moderator()
                tickets[ti].moderator = moderator
                tickets[ti].save()
    return Response(data={"status": "Success", "message": "Rebalancing Done"})


########################## Incoming Request Middleware from app_admin.middleware.py #######################3
from app_admin.models import YearbookGamingModerator

class UserLoginEventMiddleware:
    """Middleware class which marks a user logged-in whenever there is a
    request from the user's client. Upon verifying the user as a moderator, 
    this middleware triggers the `user_request_incoming` signal, which then
    does some preprocessing on the backend.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        # if not request.user.is_anonymous:
        #     is_moderator = request.user.role.role_id != 3
        #     if is_moderator:            
        #         # Set the moderator to be active. Fires `user_is_active` signal
        #         YearbookGamingModerator.set_active(user_id=request.user.id)
        
        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response

########################################### PUBNUB #########################################
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
        direction (str, optional): Direction of message flow. Defaults to 'forward'. 
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

############################################### PERMISSIONS #########################################3
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

################################################ Generate Permissions ########################################
import Moderator.settings as settings
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

################################################## Permission Migrations #######################################3
# Generated by Django 3.2.11 on 2022-05-13 09:51

from django.db import migrations
from app_admin.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from utils.perm import GroupPermissions
from django.apps.registry import apps

def initialize_data(apps):
    # We can't import the model directly as it may be a newer
    # version than this migration expects. We use the historical version.
    Role = apps.get_model('app_admin', 'Role')
    print(Role)
    groups = ["SUPERUSER", "ADMIN_MODERATOR", "SIMPLE_MODERATOR"]
    id = 0
    # Iterate over all groups and create the permissions and add them to groups
    for group_name in groups:
        id += 1
        print(group_name)
        try:
            group, _ = Group.objects.get_or_create(name=group_name)
        except:
            continue
        for permission in getattr(GroupPermissions, group_name):
            app_name, model_name, perm = permission.split('.')
            permission_codename = f"{model_name}.{perm}"
            try:
                model = apps.get_model(app_name.lower(), model_name)
            except:
                continue
            permission_name = permission
            content_type = ContentType.objects.get_for_model(model)
            permission_object, created = Permission.objects.get_or_create(codename=permission_codename,
                                                                    name=permission_name,
                                                                    content_type=content_type)    
            group.permissions.add(permission_object)
        role = Role.objects.create(role_id=id, group=group)

initialize_data(apps)

######################################### Basic Commandline Consumer Script ######################################
#!/usr/bin/env python
import pika

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

channel.exchange_declare(exchange='message', exchange_type='topic')

result = channel.queue_declare(queue='text', exclusive=False)
queue_name = result.method.queue

channel.queue_bind(exchange='message', queue=queue_name)

print(' [*] Waiting for logs. To exit press CTRL+C')
messages = 0

def callback(ch, method, properties, body):
    global messages 
    messages += 1
    print(" [x] %r" % body)
    if messages==2:
        ch.connection.close()
        
channel.basic_qos(prefetch_count=2)
q = channel.basic_consume(
    queue=queue_name, on_message_callback=callback, auto_ack=False)

try:
    channel.start_consuming()
except KeyboardInterrupt:
    channel.connection.close()
    
###################################### Advanced Asynchronous Consumer ##################################
# -*- coding: utf-8 -*-
# pylint: disable=C0111,C0103,R0205

import functools
import logging
import time
import pika
from pika.exchange_type import ExchangeType

# LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
#               '-35s %(lineno) -5d: %(message)s')
# # LOGGER = logging.get# LOGGER(__name__)


class TicketConsumer(object):
    """This is an example consumer that will handle unexpected interactions
    with RabbitMQ such as channel and connection closures.
    If RabbitMQ closes the connection, this class will stop and indicate
    that reconnection is necessary. You should look at the output, as
    there are limited reasons why the connection may be closed, which
    usually are tied to permission related issues or socket timeouts.
    If the channel is closed, it will indicate a problem with one of the
    commands that were issued and that should surface in the output as well.
    """
    EXCHANGE = 'message'
    EXCHANGE_TYPE = ExchangeType.topic
    QUEUE = 'text'
    ROUTING_KEY = 'example.text'
    DEFAULT_CONNECTION = 'BlockingConnection'
    
    def __init__(self, host, scheme="amqp", port=5672, url = None):
        """Create a new instance of the consumer class, passing in the AMQP
        URL used to connect to RabbitMQ.
        :param str amqp_url: The AMQP url to connect with
        """
        self.should_reconnect = False
        self.was_consuming = False

        self._scheme = scheme
        self._port = port
        self._connection = None
        self._channel = None
        self._closing = False
        self._consumer_tag = None
        self._url = url or f"{scheme}://{host}:{port}"
        self._host = host
        self._consuming = False
        # In production, experiment with higher prefetch values
        # for higher consumer throughput
        self._prefetch_count = 1

    def connect(self):
        """This method connects to RabbitMQ, returning the connection handle.
        When the connection is established, the on_connection_open method
        will be invoked by pika.
        :rtype: pika.SelectConnection
        """
        # LOGGER.info('Connecting to %s', self._url)    
        # parameters = pika.ConnectionParameters(host=self._host)
        parameters = pika.URLParameters(self._url)
        connection = getattr(pika, self.DEFAULT_CONNECTION)
        self._connection = connection(
            parameters=parameters
        )
        self.on_connection_open(connection)

    def close_connection(self):
        self._consuming = False
        if self._connection.is_closing or self._connection.is_closed:
            # LOGGER.info('Connection is closing or already closed')
            pass
        else:
            # LOGGER.info('Closing connection')
            self._connection.close()

    def on_connection_open(self, _unused_connection):
        """This method is called by pika once the connection to RabbitMQ has
        been established. It passes the handle to the connection object in
        case we need it, but in this case, we'll just mark it unused.
        :param pika.SelectConnection _unused_connection: The connection
        """
        # LOGGER.info('Connection opened')
        self.open_channel()

    def on_connection_open_error(self, _unused_connection, err):
        """This method is called by pika if the connection to RabbitMQ
        can't be established.
        :param pika.SelectConnection _unused_connection: The connection
        :param Exception err: The error
        """
        # LOGGER.error('Connection open failed: %s', err)
        self.reconnect()

    def on_connection_closed(self, _unused_connection, reason):
        """This method is invoked by pika when the connection to RabbitMQ is
        closed unexpectedly. Since it is unexpected, we will reconnect to
        RabbitMQ if it disconnects.
        :param pika.connection.Connection connection: The closed connection obj
        :param Exception reason: exception representing reason for loss of
            connection.
        """
        self._channel = None
        if self._closing:
            self._connection.ioloop.stop()
        else:
            # LOGGER.warning('Connection closed, reconnect necessary: %s', reason)
            self.reconnect()

    def reconnect(self):
        """Will be invoked if the connection can't be opened or is
        closed. Indicates that a reconnect is necessary then stops the
        ioloop.
        """
        self.should_reconnect = True
        self.stop()

    def open_channel(self):
        """Open a new channel with RabbitMQ by issuing the Channel.Open RPC
        command. When RabbitMQ responds that the channel is open, the
        on_channel_open callback will be invoked by pika.
        """
        # LOGGER.info('Creating a new channel')
        self._connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel):
        """This method is invoked by pika when the channel has been opened.
        The channel object is passed in so we can make use of it.
        Since the channel is now open, we'll declare the exchange to use.
        :param pika.channel.Channel channel: The channel object
        """
        # LOGGER.info('Channel opened')
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
        :param pika.channel.Channel: The closed channel
        :param Exception reason: why the channel was closed
        """
        # LOGGER.warning('Channel %i was closed: %s', channel, reason)
        self.close_connection()

    def setup_exchange(self, exchange_name):
        """Setup the exchange on RabbitMQ by invoking the Exchange.Declare RPC
        command. When it is complete, the on_exchange_declareok method will
        be invoked by pika.
        :param str|unicode exchange_name: The name of the exchange to declare
        """
        # LOGGER.info('Declaring exchange: %s', exchange_name)
        # Note: using functools.partial is not required, it is demonstrating
        # how arbitrary data can be passed to the callback when it is called
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
        cb = functools.partial(self.on_queue_declareok, userdata=queue_name)
        self._channel.queue_declare(queue=queue_name, callback=cb)

    def on_queue_declareok(self, _unused_frame, userdata):
        """Method invoked by pika when the Queue.Declare RPC call made in
        setup_queue has completed. In this method we will bind the queue
        and exchange together with the routing key by issuing the Queue.Bind
        RPC command. When this command is complete, the on_bindok method will
        be invoked by pika.
        :param pika.frame.Method _unused_frame: The Queue.DeclareOk frame
        :param str|unicode userdata: Extra user data (queue name)
        """
        queue_name = userdata
        # LOGGER.info('Binding %s to %s with %s', self.EXCHANGE, queue_name,
                    # self.ROUTING_KEY)
        cb = functools.partial(self.on_bindok, userdata=queue_name)
        self._channel.queue_bind(
            queue_name,
            self.EXCHANGE,
            routing_key=self.ROUTING_KEY,
            callback=cb)

    def on_bindok(self, _unused_frame, userdata):
        """Invoked by pika when the Queue.Bind method has completed. At this
        point we will set the prefetch count for the channel.
        :param pika.frame.Method _unused_frame: The Queue.BindOk response frame
        :param str|unicode userdata: Extra user data (queue name)
        """
        # LOGGER.info('Queue bound: %s', userdata)
        self.set_qos()

    def set_qos(self):
        """This method sets up the consumer prefetch to only be delivered
        one message at a time. The consumer must acknowledge this message
        before RabbitMQ will deliver another one. You should experiment
        with different prefetch values to achieve desired performance.
        """
        self._channel.basic_qos(
            prefetch_count=self._prefetch_count, callback=self.on_basic_qos_ok)

    def on_basic_qos_ok(self, _unused_frame):
        """Invoked by pika when the Basic.QoS method has completed. At this
        point we will start consuming messages by calling start_consuming
        which will invoke the needed RPC commands to start the process.
        :param pika.frame.Method _unused_frame: The Basic.QosOk response frame
        """
        # LOGGER.info('QOS set to: %d', self._prefetch_count)
        self.start_consuming()

    def start_consuming(self):
        """This method sets up the consumer by first calling
        add_on_cancel_callback so that the object is notified if RabbitMQ
        cancels the consumer. It then issues the Basic.Consume RPC command
        which returns the consumer tag that is used to uniquely identify the
        consumer with RabbitMQ. We keep the value to use it when we want to
        cancel consuming. The on_message method is passed in as a callback pika
        will invoke when a message is fully received.
        """
        # LOGGER.info('Issuing consumer related RPC commands')
        self.add_on_cancel_callback()
        self._consumer_tag = self._channel.basic_consume(
            self.QUEUE, self.on_message)
        self.was_consuming = True
        self._consuming = True

    def add_on_cancel_callback(self):
        """Add a callback that will be invoked if RabbitMQ cancels the consumer
        for some reason. If RabbitMQ does cancel the consumer,
        on_consumer_cancelled will be invoked by pika.
        """
        # LOGGER.info('Adding consumer cancellation callback')
        self._channel.add_on_cancel_callback(self.on_consumer_cancelled)

    def on_consumer_cancelled(self, method_frame):
        """Invoked by pika when RabbitMQ sends a Basic.Cancel for a consumer
        receiving messages.
        :param pika.frame.Method method_frame: The Basic.Cancel frame
        """
        # LOGGER.info('Consumer was cancelled remotely, shutting down: %r',
                    # method_frame)
        if self._channel:
            self._channel.close()

    def on_message(self, _unused_channel, basic_deliver, properties, body):
        """Invoked by pika when a message is delivered from RabbitMQ. The
        channel is passed for your convenience. The basic_deliver object that
        is passed in carries the exchange, routing key, delivery tag and
        a redelivered flag for the message. The properties passed in is an
        instance of BasicProperties with the message properties and the body
        is the message that was sent.
        :param pika.channel.Channel _unused_channel: The channel object
        :param pika.Spec.Basic.Deliver: basic_deliver method
        :param pika.Spec.BasicProperties: properties
        :param bytes body: The message body
        """
        # LOGGER.info('Received message # %s from %s: %s',
                    # basic_deliver.delivery_tag, properties.app_id, body)
        self.acknowledge_message(basic_deliver.delivery_tag)

    def acknowledge_message(self, delivery_tag):
        """Acknowledge the message delivery from RabbitMQ by sending a
        Basic.Ack RPC method for the delivery tag.
        :param int delivery_tag: The delivery tag from the Basic.Deliver frame
        """
        # LOGGER.info('Acknowledging message %s', delivery_tag)
        self._channel.basic_ack(delivery_tag)

    def stop_consuming(self):
        """Tell RabbitMQ that you would like to stop consuming by sending the
        Basic.Cancel RPC command.
        """
        if self._channel:
            # LOGGER.info('Sending a Basic.Cancel RPC command to RabbitMQ')
            cb = functools.partial(
                self.on_cancelok, userdata=self._consumer_tag)
            self._channel.basic_cancel(self._consumer_tag, cb)

    def on_cancelok(self, _unused_frame, userdata):
        """This method is invoked by pika when RabbitMQ acknowledges the
        cancellation of a consumer. At this point we will close the channel.
        This will invoke the on_channel_closed method once the channel has been
        closed, which will in-turn close the connection.
        :param pika.frame.Method _unused_frame: The Basic.CancelOk frame
        :param str|unicode userdata: Extra user data (consumer tag)
        """
        self._consuming = False
        # LOGGER.info(
            # 'RabbitMQ acknowledged the cancellation of the consumer: %s',
            # userdata)
        self.close_channel()

    def close_channel(self):
        """Call to close the channel with RabbitMQ cleanly by issuing the
        Channel.Close RPC command.
        """
        # LOGGER.info('Closing the channel')
        self._channel.close()

    def run(self):
        """Run the example consumer by connecting to RabbitMQ and then
        starting the IOLoop to block and allow the SelectConnection to operate.
        """
        self._connection = self.connect()
        self._connection.ioloop.start()

    def stop(self):
        """Cleanly shutdown the connection to RabbitMQ by stopping the consumer
        with RabbitMQ. When RabbitMQ confirms the cancellation, on_cancelok
        will be invoked by pika, which will then closing the channel and
        connection. The IOLoop is started again because this method is invoked
        when CTRL-C is pressed raising a KeyboardInterrupt exception. This
        exception stops the IOLoop which needs to be running for pika to
        communicate with RabbitMQ. All of the commands issued prior to starting
        the IOLoop will be buffered but not processed.
        """
        if not self._closing:
            self._closing = True
            # LOGGER.info('Stopping')
            if self._consuming:
                self.stop_consuming()
                self._connection.ioloop.start()
            else:
                self._connection.ioloop.stop()
            # LOGGER.info('Stopped')

    def get_one_message(self):
        method_frame, header_frame, body = self._channel.basic_get(queue = self._queue_name, auto_ack=False)      
        try:
            if method_frame is not None: 
                assert(method_frame.NAME == 'Basic.GetEmpty')
                return ''
        except:
            if method_frame is not None:          
                self._channel.basic_ack(delivery_tag=method_frame.delivery_tag)
                return body.decode()
        finally:
            pass
        
    def dequeue_messages(self, count):
        bodies = []
        for c in range(count):
            bodies.append(self.get_one_message())
        return bodies
        

class ReconnectingTicketConsumer(object):
    """This is an example consumer that will reconnect if the nested
    ExampleConsumer indicates that a reconnect is necessary.
    """

    def __init__(self, amqp_url):
        self._reconnect_delay = 0
        self._amqp_url = amqp_url
        self._consumer = TicketConsumer(self._amqp_url)

    def run(self):
        while True:
            try:
                self._consumer.run()
            except KeyboardInterrupt:
                self._consumer.stop()
                break
            self._maybe_reconnect()

    def _maybe_reconnect(self):
        if self._consumer.should_reconnect:
            self._consumer.stop()
            reconnect_delay = self._get_reconnect_delay()
            # LOGGER.info('Reconnecting after %d seconds', reconnect_delay)
            time.sleep(reconnect_delay)
            self._consumer = TicketConsumer(self._amqp_url)

    def _get_reconnect_delay(self):
        if self._consumer.was_consuming:
            self._reconnect_delay = 0
        else:
            self._reconnect_delay += 1
        if self._reconnect_delay > 30:
            self._reconnect_delay = 30
        return self._reconnect_delay
    
########################################### Celery Consumer Reconnect ###########################
@app.task(name="tasks.setup_connection", serializer="json")
def refresh_connection(*args, **kwargs):
    success = False, False
    if consumer is not None:
        if consumer._connection is not None and consumer._connection.is_closed:
            consumer.connect()
            success = True, True
        else:
            print("Connection is None? ", consumer._connection is None)
            print("Connection is Closed? ", consumer._connection.is_closed)
            success = True, False
    return success

########################################### User Client tasks.py functions ######################################

@app.task(name="tasks.create_enqueue_task", serializer="pickle")
def create_enqueue_ticket(content_id, *args, **kwargs):
    """Creates a new ticket for the `Content` object with id=content_id
    and enqueues it in the global ticket queue

    Args:
        content_id (int): ID or Primary key of the `Content` object
    """
    content = Content.objects.get(id=content_id)
    # Create the ticket for the content_id
    ticket = ModerationTicket.objects.create(content=content)
    enqueue_ticket(ticket)

######################## META Data View #######################
class MetaInfo(APIView):
    """Get the internal API information. Only for Development purposes
    """
    def get(self, request):
        query = request.GET.get('query')
        if query == 'group_names':
            serializer = GroupSerializer(Group.objects.all(), partial=True, many=True)
            return Response(
                data={
                    "status": "success",
                    "message": "Fetched group names successfully",
                    "data": serializer.data
                },
                status=status.HTTP_200_OK)
        elif query == "permissions":
            serializer = PermissionSerializer(Permission.objects.all(), partial=True, many=True)
            return Response(
                data={
                    "status": "success",
                    "message": "Fetched permission names successfully",
                    "data": serializer.data
                },
                status=status.HTTP_200_OK)
            
        return Response(
                data={
                    "status": "failure",
                    "message": "Invalid request",
                },
                status=status.HTTP_400_BAD_REQUEST)
        
####################################### App Admin Permissions model ##################################3
class Permission(BasePermission):
    class Meta:
        app_label = 'app_admin'
        proxy = True
    
    @classmethod       
    def get_permissions(cls, app_names="*", model_names="*", field_names="*", permissions="*"):
        # Parse the parameters
        field_names = checkList(returnList(getUpper(field_names)))
        app_names = checkList(returnList(getUpper(app_names)))
        model_names = checkList(returnList(getUpper(model_names)))
        permissions = checkList(returnList(getUpper(permissions)))
        
        if "*" in app_names:
            app_names = getUpper(settings.INSTALLED_APPS[-1*settings.NUM_APPS:])
        
        # If we have multiple apps, then no sense to specify multiple models; Similar logic for (models, fields)
        if "*" in app_names or len(app_names)>1:
            model_names = ["*",]
        if "*" in model_names or len(model_names)>1:
            field_names = ["*",]
            
        # Create List to store processed data
        returned_permissions = []
        
        # print(app_names, model_names, field_names, permissions)
        
        # Iterate over Parameters
        for app in app_names:
            for model in model_names:
                for field in field_names:
                    for perm in permissions:
                        app_query = Q() if app=="*" else Q(content_type__app_label=app.lower())
                        model_query = Q() if model=="*" else Q(content_type__model = model)
                        field_query = Q() if field=="*" else Q(codename__endswith = field)
                        perm_query = Q() if perm=="*" else Q(codename__startswith = perm)
                
                        final_query = Q(app_query & model_query & field_query & perm_query)
                        # print(final_query, "\n")
                        query_results = Permission.objects.filter(final_query)
                        returned_permissions.extend(query_results)
                        
        # print(returned_permissions)
        return returned_permissions
    
    @classmethod       
    def get_all_permissions(cls):
        return cls.get_permissions()
