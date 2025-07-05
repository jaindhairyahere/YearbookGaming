from django.dispatch import receiver
from user_client.signals import user_request_incoming, user_logout, user_is_active, ticket_patched
from user_client.tasks import logout_event, moderator_activity, ticket_patch
from django.db.models.signals import post_save

@receiver(user_logout)
def event_logout_reciever(signal, sender, moderator_id, *args, **kwargs):
    """Reciever function that gets called when `user_logout` signal
    is emmitted i.e. on a GET request to /api/v1/auth/logout. Calls
    the celery task `tasks.logout_event` which then handles the tickets
    assigned to the logout-ing user

    Args:
        signal (Signal): the signal which has called this reciever
        sender (Any): the sender of the signal
        moderator_id (int): the id (pk) of the YearbookGamingModerator instance
    """
    logout_event.delay(moderator_id, *args, **kwargs)
    
@receiver(user_is_active)
def event_activity_reciever(signal, sender, moderator_id, *args, **kwargs):
    """Reciever function that gets called when `user_is_active` signal
    is emmitted i.e. on any request made by the user to the server. Calls
    the celery task `tasks.moderator_activity` which sets the moderator to
    be active (a database commit), but on a celery worker

    Args:
        signal (Signal): the signal which has called this reciever
        sender (Any): the sender of the signal
        moderator_id (int): the id (pk) of the YearbookGamingModerator instance
    """
    moderator_activity.delay(moderator_id, *args, **kwargs)
    
@receiver(ticket_patched)
def ticket_patched(signal, sender, ticket, status, *args, **kwargs):
    """Reciever function that gets called when `ticket_patched` signal
    is emmitted i.e. on a ticket patch request by the moderator. Calls
    the celery task `tasks.ticket_patch` which update the moderator's 
    performance statistics with respect to the status

    Args:
        signal (Signal): the signal which has called this reciever
        sender (Any): the sender of the signal
        ticket (ModerationTicket): the ModerationTicket instance
        status (int): the new status of the ticket.content
    """
    ticket_patch.delay(ticket.id, status, *args, **kwargs)