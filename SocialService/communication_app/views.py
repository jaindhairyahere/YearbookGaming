# Library Imports
from django.db.models.query import Q
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import APIView, api_view

# Project Imports
from app_admin.models import YearbookUser
from app_admin.serializers import YearbookPlayerSerializer
from app_admin.permissions import LoggedInPermission, HasGroupPermission
from communication_app.models import Channel, Subscription, GameRequest
from communication_app.serializers import SubscriptionSerializer, ChannelSerializer, GameRequestSerializer
from utils.functions import get_channel_name
from utils.choices import FriendPolicyChoices, RequestTypeChoices, ChatTypeChoices
"""
1. Channel
2. Subscription

SubscriptionView = user + channel

Get - get list of subscriptions- User.subscriptions.channels
    - check subscription - channel in User.subscriptions
Post - create subscription - User subscribes a channel
Delete - delete a subscription - Used un-subscribes a channel


Put, Patch not allowed
"""
class SubscriptionView(APIView):
    """Class Based View to handle Subscription Model like list all subscriptions 
    of a user, or confirm subscription of user to a channel, or subscribe a user 
    to a channel by creating a new subscription, or unsubscribe a user
    
    Supported Methods:
        get: Get all subscriptions, or pending subscriptions of a user or check 
            if user is subscribed to a particular channel
        post: Create new subscription for a user
        delete: Unsubscribe a channel for the user
        
    URLs: 
        - "subscriptions/"
    """
    permission_classes = [LoggedInPermission]
    
    def get(self, request):
        # Get the user
        user = request.user
        # Get the query type
        query_type = request.query_params.get('query_type', 'list')
        
        # Get all subscriptions
        if query_type=='list':        
            subscriptions = user.subscriptions
        # Get the subscription with the requested channel_id   
        elif query_type=='check':
            channel_id = request.query_params.get('channel_id', None)
            subscriptions = user.subscriptions.filter(channel__id=channel_id)
        
        # Serialize the subscriptions and return
        serializer = SubscriptionSerializer(subscriptions, many=True)        
        return Response(
            data={
                "status": "success",
                "message": "Fetched subscriptions successfully",
                "data": serializer.data
            }
        )
    
    def post(self, request):
        """Subscribe to a channel"""
        # Get the user and the channel_id
        user = request.user
        channel_id = request.data.get('channel_id')
        
        # Get the channel
        channel = Channel.objects.filter(id=channel_id).first()
        if channel is None:
            # channel not found
            return Response(
                data={
                    "status": "failure", 
                    "message": "The channel you are trying to subscribe to, doesn't exist"
                }, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if not already subscribed
        subscription, already_subscribed = Subscription.objects.get_or_create(channel=channel, user=user)
        if already_subscribed:
            # channel was already subscribed
            return Response(
                data={
                    "status": "success", 
                    "message": "[WARNING] The channel you are trying to subscribe to, is already subscribed"
                }, 
                status=status.HTTP_202_ACCEPTED
            )
        else:
            # subscription created
            return Response(
                data={
                    "status": "success", 
                    "message": f"Successfully subscribed to channel {channel.name}"
                }, 
                status=status.HTTP_201_CREATED
            )
        
    def delete(self, request):
        """Un-Subscribe to a channel"""
        # Get the user and the channel_id
        user = request.user
        channel_id = request.data.get('channel_id')
        
        # Get the channel
        channel = Channel.objects.filter(id=channel_id).first()
        if channel is None:
            # channel not found
            return Response(
                data={
                    "status": "failure", 
                    "message": "The channel you are trying to subscribe to, doesn't exist"
                }, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if not already subscribed
        subscription = Subscription.objects.filter(channel=channel, user=user).first()
        if not subscription:
            # channel was already un-subscribed
            return Response(
                data={
                    "status": "success", 
                    "message": "[WARNING] The channel you are trying to subscribe to, is already un-subscribed"
                }, 
                status=status.HTTP_202_ACCEPTED
            )
        else:
            # Un-subscribe
            subscription.deleted_on = timezone.now()
            subscription.save()
            return Response(
                data={
                    "status": "success", 
                    "message": f"Successfully Un-subscribed from channel {channel.name}"
                }, 
                status=status.HTTP_201_CREATED
            )
        
class ChannelView(APIView):
    permission_classes = [LoggedInPermission]
    
    def get(self, request):
        """Get a channel, by its id or name"""
        # Get the user,
        user = request.user
        
        # Get the channel name or id from request
        channel_identity = request.query_params.get("channel_id", None) or \
                    request.query_params.get("channel_name", None)
        if isinstance(channel_identity, int):
            key = 'id'
        elif isinstance(channel_identity, str):
            key = 'name'
        
        # Get the channels user has subscribed to
        channel = Channel.objects.filter(**{key: channel_identity}).first()
        if channel:
            # Check if this user has subscribed to this channel
            if not Subscription.objects.filter(user=user, channel=channel).exists():
                return Response(
                    data={
                        "status": "failure",
                        "message": f"User can't get this channel information",
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            serializer = ChannelSerializer(channel)
            return Response(
                data={
                    "status": "success",
                    "message": f"Fetched subscribed channes successfully",
                    "data": serializer.data
                },
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                    data={
                        "status": "failure",
                        "message": f"Requested channel not found",
                    },
                    status=status.HTTP_404_NOT_FOUND
                )
        
    def post(self, request):
        """Create a new channel with a `purpose` and a `nickname`.
        With this API, client will be able to create a new channel and recieves the channel name
        in the response. Now client can send and receive messages to/from the channel
        """
        # Get the user
        user = request.user
        
        nickname = request.data.get('nickname')
        purpose = request.data.get('purpose')
        
        name, nickname = get_channel_name(user, user, purpose=ChatTypeChoices.GROUP, nickname=nickname)
        
        channel, created = Channel.objects.get_or_create(name=name)
        if not created:
            return Response(data={
                "status": "success",
                "message": f"A player can't create two {purpose} with same nicknames"
            },
            status=status.HTTP_202_ACCEPTED)
            
        channel.admins.add(user)
        channel.save()
        if not created:
            # A player can't create two groups with same nicknames
            return Response(data={
                "status": "success",
                "message": f"A player can't create two {purpose} with same nicknames"
            },
            status=status.HTTP_202_ACCEPTED)
        serializer = ChannelSerializer(channel)
        
        
        if request.data.get('invitees'):
            pass
        
        return Response(
            data={
                "status": "success",
                "message": f"{purpose.capitalize()} created Successfully!",
                "channel": serializer.data
            },
            status=status.HTTP_201_CREATED)
        
class RequestView(APIView):
    permission_classes = [LoggedInPermission]
    
    def get(self, request):
        """Get pending/un-accepted requests for the current user"""
        # Get the user
        user = request.user
        
        # Get the request_type
        request_type = request.query_params.get('request_type', 'All').upper()
        
        # Get the side
        side = request.query_params.get('side', 'receiver')
        
        # Get the requestes based on request type
        side_q = Q(**{side: user})
        print(side_q)
        type_q = Q() if request_type=="ALL" else Q(type=getattr(RequestTypeChoices, request_type))
        accp_q = Q(is_accepted=False)
        requests = GameRequest.objects.filter(side_q & type_q & accp_q)
        
        # Serialize the requests
        serializer = GameRequestSerializer(requests, many=True)
        return Response(
            data={
                "status": "success",
                "message": f"Fetched all {request_type.lower().replace('_', ' ')} successfully",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )
    
    def post(self, request):
        """Send Friend request to another user"""
        # Get the user
        user = request.user
        # Get the friend's id, and fetch the Player from it
        friend_id = request.data.get('friend_user_id')
        assert(friend_id!=user.id)
        friend = YearbookUser.objects.filter(id=friend_id).first()
        if friend is None:
            # Requested friend doesn't exist
            return Response(
                data={
                    "status": "failure",
                    "message": "The requested friend doesn't exist"
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if you can send the request to this friend
        if friend.player.policy is not None and friend.player.policy.friend_policy == FriendPolicyChoices.FORBID_REQUESTS:
            # Requested friend doesn't want to allow any kind of friend requests
            return Response(
                data={
                    "status": "failure",
                    "message": "The requested friend is private and doesn't allow friend requests"
                },
                status=status.HTTP_204_NO_CONTENT
            )
        # Get the purpose
        purpose = request.data.get('purpose', ChatTypeChoices.ONE_ON_ONE)
        
        # Create the name
        name, nickname = get_channel_name(user, friend, purpose)
        
        channel, created = Channel.objects.get_or_create(name=name)
        channel.nickname = nickname
        channel.admins.add(user)
        channel.save()
        
        
        # Create a GameRequest Object
        game_request, created = GameRequest.objects.get_or_create(sender=user, receiver=friend, type=RequestTypeChoices.FRIEND_REQUEST, channel=channel)
        
        _ = Subscription.objects.get_or_create(channel=channel, user=user)
            
        
        if not created:
            # A request is already created
            return Response(
                data={
                    "status": "success",
                    "message": "[WARNING] You've already sent the friend request once"
                },
                status=status.HTTP_202_ACCEPTED
            )
        
        serializer = GameRequestSerializer(game_request)
        
        # GameRequest created        
        return Response(
            data={
                "status": "success",
                "message": "Friend Request sent",
                "data": serializer.data
            },
            status=status.HTTP_201_CREATED
        )

    def patch(self, request):
        """Accept friend request from another user"""
        # Get the user
        user = request.user
        # Get the friend-request
        request_id = request.data.get('request_id')
        game_request = GameRequest.objects.filter(id=request_id).first()
        if game_request is None:
            # Either game request doesn't exist or can't be accessed by this user
            return Response(
                data={
                    "status": "failure",
                    "message": "Game request doesn't exist",
                },
                status=status.HTTP_404_NOT_FOUND
            )
        elif  game_request.receiver != user:
            # Game request can't be accessed by this user
            return Response(
                data={
                    "status": "failure",
                    "message": "Game request can't be accessed by this user"
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        # Accept the request and save it
        game_request.is_accepted = True
        game_request.save()
        
        # Add each other to friend's list
        game_request.sender.player.friends.add(game_request.receiver.player)
        game_request.receiver.player.friends.add(game_request.sender.player)
        game_request.sender.player.save()
        game_request.receiver.player.save()
        
        # Get the channel
        channel = game_request.channel
        if channel is not None:
            if channel.nickname.split("=")[1] == ChatTypeChoices.ONE_ON_ONE:
                channel.admins.add(user)
            channel.save()
        
        # Create a subscription for that channel
        _ = Subscription.objects.get_or_create(channel=channel, user=user)
        
        # serializer the game request
        serializer = GameRequestSerializer(game_request)
        
        # Return success resposne
        return Response(
                data={
                    "status": "success",
                    "message": "Game request accepted successfully",
                    "data": serializer.data
                },
                status=status.HTTP_200_OK
            )
        
class FriendsListView(APIView):
    permission_classes = [LoggedInPermission]
    
    def get(self, request):
        """Get all the friends of the current user"""
        user = request.user
        serializer = YearbookPlayerSerializer(user.player.friends, many=True)
        return Response(
            data={
                "status": "success",
                "message": "Fetched friends successfully",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )
        
    def get(self, request):
        """Get all the subscriptions, with their involved users, the current user has subscribed to
        With this API, client will be able to map the groups to the users that have subscribed
        to this group. Now client can send the message to the channel.
        """
        # Get the user
        user = request.user
        
        if request.query_params.get('channel_id', None):
            channels = Channel.objects.filter(id=request.query_params.get('channel_id'))
        
        # Get the channels has subscribed to
        channels = [channel[0] for channel in user.subscriptions.values_list('channels')]
        
        # Get all the subscriptions where the channel is in user subscribed channels 
        # but subscribed user is not `request.user`
        subscriptions = Subscription.objects.filter(Q(channel__in=channels) & ~Q(user=request.user))
        # Serialize the subscriptions and return the response
        serializer = SubscriptionSerializer(subscriptions, many=True)
        return Response(
            data={
                "status": "success",
                "message": "Fetched subscriptions successfully",
                "data": serializer.data
            }
        )
