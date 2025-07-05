# Library Imports
from celery import current_app as app
from django.conf import settings
from django.db.models.query import Q
from django.utils import timezone
import json
import logging
from queue import Queue

# Project Imports
from user_client.models import YearbookGamingModerator, ModerationTicket, TicketBoard
from utils.consumer import TicketConsumer

# Setup Logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create a global ticket queue, which stores the escalated tickets
# Whenever a new ticket is requested by the client, the deque operation
# is done firstly on this Queue, then on the RabbitMQ queue. This queue
# is stored globally because it is treated as a priority, and is expected 
# to contain very few tickets. If this gets crashed then we could replace 
# it by a Redis Cache (more RAM), or by another self-service to self-service
# RabbitMQ queue, which will then be treated as a priority queue
Queue = Queue(int(settings.MAX_QUEUE_SIZE))

# Initializing the ticket consumer using the RabbitMQ URL and setting up
# the connection using AMQP protocol
consumer = TicketConsumer(settings.MESSAGE_QUEUE_URL)
consumer.connect()

def handle_tickets(expire_time=None, moderator=None, tickets=None, complete=True, requeue=True, board=None,
                   callbacks={}, update_moderator_stats=True, is_mod_available=False, moderator_abandoned=False):
    """Handles the tickets by completing them or setting them to get re-processed or both.
    Case when both complete=True and requeue=True is also referred as a ticket expiry event
    
    Args:
        expire_time (DateTime, Optional): expire date-time will be passed here. Default is the 
                                        current time fetched using `timezone.now()`
        moderator (YearbookGamingModerator, Optional): the moderator instance. Defaults to None
        tickets (QuerySet[ModerationTicket], Optional): tickets to be handled. Defaults to tickets 
            that were assigned to this moderator, that have been pulled but not completed yet
        complete (bool, Optional): Should the tickets be set to completed. Defaults to True.
        requeue (bool, Optional): Should the ticket's content be processed again. Defaults to True.
        board (TicketBoard, Optional): the board of the current user/moderator
        callbacks (dict[str, List[Callable]]): Functions to be executed after complete or requeue or both.
                Defaults to empty dict. Example: {"complete": [...], "requeue": [...], "general": [...]}
        update_moderator_status (bool, Optional): Should the moderator's performance statistics be updated. 
                                                Defaults to True
        is_mod_availabls (bool, Optional): Is the moderator available after handling the tickets. This will 
            naturally be False, except in rare cases (not thought of yet). Defaults to False.
        moderator_abandoned (bool, Optional): Is the handling done because moderator has abandoned his seat.
            In this case, abandoned posts will also be updated for the moderator. Defaults to False.
    """
    # Directly return if nothing to do with the tickets
    if not complete and not requeue:
        return
    # Both moderator and tickets can't be set None at the same time
    if not moderator and not tickets:
        return
    
    # Set the expire_time to be current time, if not provided
    expire_time = expire_time or timezone.now()
    
    # Use the tickets that were provided in the function call; If nothing was passed,
    # fetch the tickets that were assigned to this moderator, that have been pulled
    # but not completed yet. This doesn't take into account when the tickets were pulled
    # (completed_on=None => uncompleted tickets) & (pulled_on!=None => pulled tickets)
    tickets = tickets or moderator.user.tickets.filter(completed_on=None).exclude(pulled_on=None)

    # So, if a moderator has abandoned, then we increment it's `times_abandoned` by 1, but it's 
    # `posts_abandoned` can be any Natural Number. In this case, we need to track if we have 
    # incremented the `times_abandoned` of that moderator already, and we do this by using a 
    # set. We push the moderator in the set if we have incremented its `times_abandoned` 
    # attribute and if we haven't, then we increment `times_abandoned` and push it in the set.
    abandoned_moderators = set()
    
    # Complete these tickets and requeue them
    for ticket in tickets:
        # If moderator stats have to be updated
        if update_moderator_stats:
            # Get the moderator from the function parameters or the ticket
            moderator = moderator or ticket.moderator
            # Get the moderator's board
            board = board or moderator.user.board
            # Logout the moderator i.e set it unavailable and update it's login-logout time stats
            moderator.is_mod_available = is_mod_available            
            moderator.last_logout = expire_time
            # If moderator has abandoned
            if moderator_abandoned:
                # Increment the abandoned post count
                board.posts_abandoned += 1
                # Increment the abandoned times count by 1 (in all the iterations combined). 
                if moderator not in abandoned_moderators:
                    abandoned_moderators.add(moderator)
                    board.times_abandoned += 1  
            # Save the moderator
            moderator.save()
            board.save()            
            
        # If `complete` == True, update the `completed_on` attribute of the ticket and save it
        if complete:
            # Complete and save the ticket
            ticket.completed_on = expire_time
            ticket.save()
            # Run post complete call-back
            for cb in callbacks.get("complete", []):
                cb(ticket)
        # If `requeue` == True, Create a new copy of the ticket and enqueue it in the ticket `Queue` 
        if requeue:
            # Requeue the ticket
            ticket_copy = ModerationTicket.objects.create(content=ticket.content)
            enqueue_ticket(ticket_copy)
            # Run post requeue call-back
            for cb in callbacks.get("requeue", []):
                cb(ticket)
        # Run the general callbacks
        for cb in callbacks.get("general", []):
            cb(ticket)
    logger.info(f"Handled {tickets.count()} tickets")

def dequeue_from_broker(num_tickets):
    """Function that dequeues a selected number of tickets 
    from the Message Queue and loads the JSoN formatted strings
    into python dictionary. Dequeues `None` when no tickets left
    in the Broker Queue instance

    Args:
        num_tickets (int): Number to tickets to dequeue

    Returns:
        List[Dict]: List of tickets as a python dictionary objects
    """
    messages = consumer.dequeue_messages(count=num_tickets)
    return [json.loads(message) if message is not None else None for message in messages]

def enqueue_ticket(ticket):
    """Function that enqueues a ticket into the global ticket queue
    
    Args:
        ticket (Any): A serialized ticket instance or a ticket instance
    """
    if isinstance(ticket, ModerationTicket):
        Queue.put(ticket.id)
    elif isinstance(ticket, dict) and 'id' in ticket:
        Queue.put(ticket.get('id'))

@app.task(name="tasks.moderator_activity", serializer="json")
def moderator_activity(moderator_id, shared=False, *args, **kwargs):
    """Celery task that is associated with every request. On every request by
    a user, this task sets the `user.moderator` to be active. This task is run
    when the signal `user_is_active` is emitted

    Args:
        moderator_id (int (YearbookGamingModerator)): ID or PK of a `YearbookGamingModerator` instance
        shared (bool, Optional): Should the `model.save()` by run asynchronously with 
                                respect to the worker. Defaults to False.
    """
    moderator = YearbookGamingModerator.objects.get(id=moderator_id)
    if not moderator.is_mod_available:
        moderator.set_active(shared=shared)

@app.task(name="tasks.logout_event", serializer="json")
def logout_event(moderator_id, expire_tickets=True, shared=False, *args, **kwargs):
    """Celery task that is associated with every logout event. On every logout event,
    this task sets the `user.moderator` to be in-active. Optionally, this task will 
    also re-queue the moderator's tickets. This task is run when
    the signal `user_logout` is emitted.

    Args:
        moderator_id (int (YearbookGamingModerator)): ID or PK of a `YearbookGamingModerator` instance
        expire_tickets (bool, Optional): Does the task also need to expire the tickets, 
                            i.e. complete them and then requeue them. Defaults to True.
        shared (bool, Optional): Should the `model.save()` by run asynchronously with 
                                respect to the worker. Defaults to False.
    """
    # Get the current time
    current_time = timezone.now()
    # Get the moderator and its board
    moderator = YearbookGamingModerator.objects.get(id=moderator_id)
    board = moderator.user.board
    board.total_logged_in_time += (current_time-moderator.last_logout).seconds//60
    board.save()
    # Expire the tickets if asked to do so
    if expire_tickets:
        handle_tickets(current_time, moderator=moderator, moderator_abandoned=False, board=board)
    
@app.task(name="tasks.periodic_check_expired", serializer="json")
def periodic_check_expired(*args, **kwargs):
    """Periodically checks all the tickets that have not been modified in the last few minutes"""
    # Get the current time
    current_time = timezone.now()

    # Get all the moderation tickets that either are associated with the internet 
    # connection cut moderators or online/too much waiting logout or browser close
    pulled_before = current_time - timezone.timedelta(seconds=settings.MODERATOR_LOGOUT_TIME)
    
    # Get the tickets to expire - pulled tickets (i.e user is not None) which have been
    # pulled before `pulled_before` time and are not completed yet
    tickets = ModerationTicket.objects\
                .exclude(pulled_on=None)\
                .exclude(user=None)\
                .filter(Q(pulled_on__lt=pulled_before, completed_on=None))\
                .distinct()
    
    # Mark these tickets to be completed and create copies and push back to queue
    # Also In the same iteration, mark the user to be logout   
    handle_tickets(current_time, tickets=tickets, moderator_abandoned=True)
    logger.info("Periodic ticket expire task done")

@app.task(name="tasks.setup_connection", serializer="json")
def refresh_connection(*args, **kwargs):
    """Periodically reconnects the consumer instance so as to avoid connection reset error"""
    consumer.connect()

def update_board(board, status, ticket, current_time):
    if status=="ESCALATED":
        board.escalated += 1
    elif status=="REJECTED":
        board.rejected += 1
    elif status=="APPROVED":
        board.approved += 1
    content_time = 0
    medias = ticket.content.medias
    for media in medias.all():
        content_time += media.meta.get('time', 10000)//1000
    board.average_response_time = ((board.average_response_time*board.total)+max(content_time, (current_time-ticket.pulled_on).seconds-content_time))//(board.total+1)
    board.total += 1
    board.save()
    
@app.task(name="tasks.ticket_patch", serializer="json")
def ticket_patch(ticket_id, status, *args, **kwargs):
    ticket = ModerationTicket.objects.get(id=ticket_id)
    current_time = timezone.now()
    board = ticket.user.board
    update_board(board, status, ticket, current_time)