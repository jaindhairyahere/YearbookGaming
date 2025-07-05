from rest_framework.decorators import APIView, api_view
from rest_framework.response import Response
from rest_framework import status
from app_admin.models import YearbookGamingUser
from content_app.models import Content
from communication_app.models import Channel, Subscription
from django.middleware.http import ConditionalGetMiddleware

@api_view(["POST"])
def report_user(request, user_id):
    # Get the reporting user and the user to be reported
    reporting_user = request.user
    reported_user = YearbookGamingUser.objects.filter(id=user_id).first()
    if reported_user is None:
        # reported user not found
        return Response(
            data={
                "status": "failure", 
                "message": "The user you are trying to report doesn't exist"
            }, 
            status=status.HTTP_404_NOT_FOUND
        )
        
    # CODE TO HANDLE LAST N MESSAGES AND CREATE A ReportingTicket
    # history_content = Content.objects.create(
    #     user=reporting_user, 
    #     content_type=ContentTypeChoices.HISTORY,
    #     content={},
    # )
    # ReportingTicket.objects.create(content=) 
    
    # PUSH THE TICKET TO THE QUEUE
    
    # Now block the user
    reporting_user.player.blocked_users.add(reported_user.player)
    reporting_user.player.save()

    # Get the channels of this blocking user
    channels = set(reporting_user.subscriptions.values("channel__name")).intersection(set(reported_user.subscriptions.values("channel")))
    
    # Return the response
    return Response(
        data={
            "status": "success",
            "message": f"User Blocked Successfully"
        },
        status=status.HTTP_200_OK)

@api_view(["GET"])
def block_user(request, user_id):
    # Get the reporting user and the user to be reported
    reporting_user = request.user
    reported_user = YearbookGamingUser.objects.get(id=user_id)
    if reported_user is None:
        # reported user not found
        return Response(
            data={
                "status": "failure", 
                "message": "The user you are trying to report doesn't exist"
            }, 
            status=status.HTTP_404_NOT_FOUND
        )
        
    # Now block the user
    reporting_user.player.blocked_users.add(reported_user.player)
    reporting_user.player.save()
    
    # Return the response
    return Response(
        data={
            "status": "success",
            "message": f"User Blocked Successfully"
        },
        status=status.HTTP_200_OK)

@api_view(["PATCH", "GET"])
def update_moderation_status(request):
    role_id = request.data.get('user').get('role').get('role_id')
    if role_id !=3:
        content_id = request.data.get('content').get('id')
        content = Content.objects.filter(id=content_id).first()
        if content is None:
            return Response(
                data={
                    "status": "failure",
                    "message": "Requested content doesn't exist"
                },
                status=status.HTTP_204_NO_CONTENT
            )
        new_status = request.data.get('content').get('status')
        content.status = new_status
        content.save()
        return Response(
            data={
                "status": "success",
                "message": "Status Updated Successfully"
            },
            status=status.HTTP_200_OK
        )
    return Response(
        data={
            "status": "failure",
            "message": "User not allowed to modify content status"
        },
        status=status.HTTP_401_UNAUTHORIZED
    )