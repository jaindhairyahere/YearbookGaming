# Library Imports
from django.db.models.query import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

# Project Imports
from app_admin.permissions import HasGroupPermission, LoggedInPermission
from utils.choices import ModerationStatesChoices
from user_client.signals import ticket_patched
from user_client.models import(
    FeedbackTags, YearbookModerator, 
    ModerationTicket, TicketBoard,
    UploadObject, Content
)
from user_client.rest_apis import SocialService
from user_client.serializers import (
    MediaSerializer, YearbookModeratorSerializer, 
    ModerationTicketSerializer, ContentSerializer
)
from user_client.tasks import Queue, dequeue_from_broker, enqueue_ticket
from utils.views import APIView


class ProfileView(APIView):
    """Class based View for moderators and admins to view different profiles
    An admin can view all the profiles of all moderators and of other admins
    but a simple moderator can, however, view only its own profile.
    
    Supported Methods:
        get: Get the profile of the moderator with id=pk, or 
            if pk is None, then get all profiles
        
    URLs: 
        - "/moderators/"
        - "/moderators/<int:pk>"
    """
    permission_classes = [LoggedInPermission, HasGroupPermission]
    required_groups = {
        "GET": ["ADMIN_MODERATOR", "SELF"]
    }
    pk_class = YearbookModerator

    def get(self, request, pk=None):
        """Get the profile of a single moderator with id=pk OR if pk is None, 
        get profiles of all the moderators. In case of an admin moderator, 
        both pk=<some_id> and pk=None will work. But for a simple moderator, 
        only pk=request.user.moderator.id works # ["SELF"] group [QUERY OPTIMIZED]

        Args:
            request (Request): the drf wrapped wsgi request
                query_params : {}
                
            pk (int (YearbookModerator), optional): 
                Id of the Yearbook moderator whoose profile we want to see. Defaults to None. 
                If pk is none, then user should be an admin_moderator for the view to be
                called; otherwise DRF returns a Forbidden 403 response. 
                Example {url}/{pk}/
        
        URLS:
            - GET /moderators/
            - GET /moderators/<int:pk>
        """
        # starttime = timezone.now()
        if pk is None:
            moderators = YearbookModerator.objects.all().select_related('user', 'user__board').prefetch_related('user__tickets')
            message = "Fetched list of all moderators"
        else:
            moderators = YearbookModerator.objects.filter(id=pk).select_related('user', 'user__board').prefetch_related('user__tickets')
            message = "Fetched the requested moderator"
            
        serializer = YearbookModeratorSerializer(
            moderators, partial=True, 
            context={"purpose": "download", "exclude": [("user", ["role","groups", "user_permissions"]), ("tickets", ["user"])]}, 
            many=True)
        response = Response(
            data={
                "status": "success",
                "message": message,
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )
        # endtime = timezone.now()
        # print((endtime-starttime).microseconds)
        return response

class TicketFeedAPI(APIView):
    """Class based View for moderators and admins to fetch new tickets
    in their ticket feed.
    
    Supported Methods:
        get: Get new tickets in the ticket-feed
        
    URLs: 
        - "/ticket_feed/"
    """
    permission_classes = [LoggedInPermission]
    
    def get(self, request):
        """ Get some new tickets in the ticket-feed. Requires user to be Logged In. Fetches 
        the tickets first from the global ticket queue `Queue` and the remaining from the 
        Message Queue instance, and then assigns those tickets to the current user [QUERY OPTIMIZED]
        
        Args:
            request (Request): the drf wrapped wsgi request
                query_params: {
                    "num_tickets" (integer): The number of tickets to return. Defaults to 1.
                }
        
        URLs:
            - GET /ticket_feed/?num_tickets=3
        """
        # starttime = timezone.now()
        # Get the user, and current time
        user = request.user
        current_time = timezone.now()
        
        # Get the number of tickets the user demands
        num_tickets = int(request.query_params.get('num_tickets', 1))
        
        # Set up the variables
        tickets = [] # Stores the tickets (used in bulk update and then sliced to do a bulk create)
        boards = [] # Stores the boards (used in bulk update)
        all_medias = [] # Stores the medias (used in bulk create)
        tickets_created = False # Stores if tickets were created (to get the correct response code)
        tkt_position = 0 # Stores the number of tickets fetched from Queue (used to slice tickets)
        
        # Fetch from escalation queue until not empty
        while not Queue.empty() and num_tickets:
            # Get the ticket using id, if it is valid, add it to tickets else continue
            ticket = ModerationTicket.objects.filter(id=Queue.get()).first()
            if ticket is not None: 
                # Update the ticket assignee      
                ticket.user = user
                # Update the ticket pulled_on time
                ticket.pulled_on = current_time
                # Set the ticket's completed_on time to be None
                if ticket.completed_on is not None:
                    ticket.completed_on = None
                # Add it to `tickets` list, and decrement the num_tickets
                # ticket.save() #### Saving will be done later in a bulk update step
                tickets.append(ticket)
                num_tickets -= 1
                tkt_position += 1
                
        # Do a bulk update now
        ModerationTicket.objects.bulk_update(tickets, ["user", "pulled_on", "completed_on"])
        
        # If user requested more tickets than were in the Queue, pull from RabbitMQ Broker
        if num_tickets:
            # Get the tickets from social service as an python dictionary
            social_tickets = dequeue_from_broker(num_tickets)
            # Create an ticket object for each ticket
            for tkt in social_tickets:
                if tkt is not None:
                    # Get the content (and media) from the ticket
                    content_dict = tkt.get('content')
                    medias = content_dict.get('medias')
                    
                    # Create a content object (medias is a read_only field in the serializer)
                    # If not success, skip this this ticket
                    content_serializer = ContentSerializer(data=content_dict, context={'purpose': 'internal'})
                    if content_serializer.is_valid(): content = content_serializer.save()
                    else: continue
                    
                    # Create medias for this object
                    media_count = 0
                    for media in medias:
                        # Send the media json into the serializer. Save the new media. 
                        # Attach the content previously created to this media. 
                        # Increment the media_count which we'll use later to check if 
                        # this ticket could be sent to the moderator
                        serializer = MediaSerializer(data=media)
                        if serializer.is_valid():
                            media = serializer.validated_data
                            media.content = content
                            media = serializer.save()
                            all_medias.append(media)
                            media_count += 1
                    
                    # If saved medias are not equal, some error with media creation. Skip this ticket
                    if len(medias) != media_count: continue
                    
                    # Create a new ticket for this content, assign it's pulled time to be now
                    # and user to be the current user. Then push it in the `tickets` list
                    ticket = ModerationTicket(
                        user=user, content=content, pulled_on=current_time
                    )
                    boards.append(user.board)
                    boards[-1].total = boards[-1].total + 1
                    
                    tickets.append(ticket)
                    tickets_created = True
        
        # Do the bulk create and bulk updates
        ModerationTicket.objects.bulk_create(tickets[tkt_position:])
        # UploadObject.objects.bulk_create(all_medias)
        TicketBoard.objects.bulk_update(boards, ["total"])
        
        # Serialize the tickets 
        ##### TODO - A better idea might be to serialize the ticket as soon as we create them, so that we can take advantage of the cache
        serializer = ModerationTicketSerializer(tickets, context={"purpose": "download", "request": request}, many=True)
        
        response = Response(
            data={
                "status": "success",
                "message": "Tickets assigned & returned successfully" if len(tickets) else "No tickets to assign",
                "tickets": serializer.data
            },
            status=status.HTTP_201_CREATED if tickets_created else status.HTTP_200_OK
        )
        # endtime = timezone.now()
        # print((endtime-starttime).microseconds)
        return response

class TicketViewAPI(APIView):
    """Class based View for moderators and admins to Get/Modify a ticket
    by ticket ID
    
    Supported Methods:
        get: Get a ticket by its ID
        patch: Modify a ticket (maybe mark its status) by its ID
        
    URLs: 
        - "tickets/id/pk"
    """
    permission_classes = [LoggedInPermission, HasGroupPermission]
    required_groups = {
         'GET': ["ADMIN_MODERATOR", "SELF"],
         'PATCH': ["ADMIN_MODERATOR", "SELF"]
    }
    pk_class = ModerationTicket
    
    def get(self, request, pk):
        """Get a ticket with id=pk 
        
        In case of an admin moderator, any pk=<some_id> will work. But for a simple 
        moderator, only pk=request.user.moderator.id works # ["SELF"] group [QUERY OPTIMIZED]

        Args:
            request (Request): the drf wrapped wsgi request
                query_params: {}
                
            pk (int (ModerationTicket)): 
                Id of the ticket we want to see. Example: /{url}/{pk}/
        
        URLs:
            - GET /tickets/id/
            - GET /tickets/id/pk
        """
        starttime = timezone.now()
        ticket = ModerationTicket.objects.filter(pk=pk).select_related('content').prefetch_related('content__medias').first()
        serializer = ModerationTicketSerializer(ticket, context={"purpose": "download", "request": request})
        response =  Response(
            data={
                "status": "success",
                "message": "Ticket fetched successfully",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )
        endtime = timezone.now()
        print((endtime-starttime).microseconds)
        return response
    
    def patch(self, request, pk):
        """
        Change the moderation status of a ticket, by its pk
        In case of an admin moderator, any pk=<some_id> will work. But for a 
        simple moderator, only the user should have the ownership of that ticket.
        Also, tickets once marked completed can't be modified. To modify them,
        client needs to issue an escalate request (using this same view)
        
        Args:
            request (Request): the drf wrapped wsgi request
                data = {
                    'escalate' (boolean, Optional): If you want to escalate the ticket to another moderator
                    'content':{
                        'id' (integer): Id of the content object
                        'status' (integer): # Options are ModerationStates.choices
                    }
                }
            pk (int (ModerationTicket)): 
                Id of the ticket we want to update. Example /{url}/{pk}/
        
        URLs:
            - PATCH /tickets/id/pk
        """
        # Get the user and the request body
        user = request.user
        data = request.data
    
        # Get the ticket object
        ticket, _ = ModerationTicket.objects.get_or_create(id=pk)
        
        # Check if the ticket is completed and it's something other than an escalation request
        if ticket.completed_on is not None and not data.get('escalate', False):
            return Response(
                data={
                    "status": "failure",
                    "message": "Ticket has already been completed" 
                    "You can only escalate it now"
                },
                status=status.HTTP_200_OK
            )

        # Get the patch data from the request
        ticket_status = content_status = data.get('content').get('status')
        
        # Complete the ticket and save
        ticket.status = ticket_status
        ticket.completed_on = timezone.now()
        ticket.save()
        
        # Add feedback tags to the content
        contents = []
        feedback_tags_ids = data.get('content').get('feedback_tags_ids', [])
        feedbacks = FeedbackTags.objects.filter(id__in=feedback_tags_ids)
        if feedbacks:
            ticket.content.feedbacks.add(feedbacks)
            contents.append(ticket.content)
        Content.objects.bulk_update(contents, ["feedbacks"])
        
        # Check for escalation request. Puts the ticket into global ticket `Queue`
        if data.get('escalate', False):
            # Dont call SocialService REST API | Copy the ticket and push into escalation queue
            copy_ticket = ModerationTicket.objects.create(content = ticket.content)
            enqueue_ticket(copy_ticket)
            # Send the ticket patch signal
            ticket_patched.send_robust(sender=ModerationTicket, ticket=ticket, 
                                       status="ESCALATED")
            return Response(
                data={
                    "status": "success", 
                    "message": "Successfully escalated the Ticket"
                },
                status=status.HTTP_201_CREATED
            )
        
        # Patch Request to SocialService to update the content's status
        response = SocialService.update_moderation_status(request, ticket.content, content_status)
        if response.get('status')=='failure':
            return Response(
                data={
                    "status": "failure",
                    "message": "Couldn't update moderation status"
                },
                status=status.HTTP_502_BAD_GATEWAY
            )
        else:
            # Send the ticket patch signal
            ticket_patched.send_robust(sender=ModerationTicket, ticket=ticket, 
                                       status=ModerationStatesChoices._value2member_map_[content_status].name)
            return Response(
                data={
                    "status": "success",
                    "message": "Updated moderation status successfully"
                },
                status=status.HTTP_200_OK
            )

class TicketHistoryAPI(APIView):
    """Class based View for moderators and admins to get tickets by
    moderator's ID
    
    Supported Methods:
        get: Get a ticket by its ID
        
    URLs: 
        - "/tickets/moderator/<int:pk>"
        - "/tickets/
    """
    permission_classes = [LoggedInPermission, HasGroupPermission]
    required_groups = {
         'GET': ["ADMIN_MODERATOR", "SELF"],
         'PATCH': ["ADMIN_MODERATOR", "SELF"]
    }
    pk_class = YearbookModerator
    queryset = ModerationTicket.objects.all().select_related('content').prefetch_related('content__medias')
    
    def get(self, request, pk=None):
        """
        Get the tickets of a moderator by moderator's ID or PK
        In case of an admin moderator, any pk=int/None will work. In case of None,
        returns tickets of all moderators. But for a simple moderator, only that 
        particular moderator's ID will work. This view also allows the client to pass
        filters like created_date, end_date, completed_on to filter the tickets
        
        Args:
            request (Request): the drf wrapped wsgi request
                query_params: {
                    // Format for dates : '%c'- Example: 16-05-2022 21:30:00
                    created_start (string): Get tickets only after this date
                    created_end (string): Get tickets only before this date
                    completed_on (string): Get the completed time (unmodifiable)
                }
            pk (int (YearbookModerator), Optional): 
                Id of the moderator, whoose tickets we want to get. Defaults to None
        
        URLs:
            - GET /tickets/moderator/pk
            - GET /tickets/?created_start=&created_end=&completed_on=    
        """
        # Get the user
        user =  request.user
        current_time = timezone.now()
        
        # Get the Base Queryset (All for Admins, and User for SimpleModerator)
        queryset = self.queryset
        if pk is not None:
            queryset = self.queryset.filter(user__id=pk)
        
        # Define a datetime parser format
        format = "%d-%m-%Y %H:%M:%S" # 16-05-2022 21:30:00
        
        # Get time filters
        created_start = timezone.datetime.strptime(
            request.query_params.get(
                "created_start", timezone.datetime(2000, 1, 1).strftime(format)
            ),
            format)
        created_end = timezone.datetime.strptime(
            request.query_params.get(
                "created_end", current_time.strftime(format)
            ),
            format)
        if request.query_params.get('completed_before', None) or \
                request.query_params.get('is_completed', 'true')=='true':
            completed_before = request.query_params.get("completed_before", None)
            if not completed_before:
                completed_before = current_time.strftime(format)
                
            completed_before = timezone.datetime.strptime(completed_before, format)
            completed_query = Q(completed_on__lt=completed_before)
        else:
            completed_query = Q(completed_on = None)
        
        # Make queries
        query = Q(created_on__lt=created_end, created_on__gt=created_start) & completed_query
        
        # Filter the objects, and pass into serializer
        tickets = queryset.filter(query)
            
        serializer = ModerationTicketSerializer(tickets, context={"purpose": "download", "exclude": ["user"]}, many=True)
        return Response(
            data={
                "status": "success",
                "message": "Tickets fetched successfully" if len(tickets) else "No tickets found",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )