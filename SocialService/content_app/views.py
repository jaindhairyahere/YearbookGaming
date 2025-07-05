# Library Imports
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import APIView
from rest_framework.response import Response

# Project Imports
from content_app.models import Content, ContentTypeChoices, UploadObject
from content_app.serializers import ContentSerializer
from content_app.signals import content_send_to_moderation as content_save
from utils.functions import get_encrypted_s3_key


class ContentAPI(APIView):
    def get(self, request):
        """View to handle get requests. Gets content by content-id
        
        Args:
            request (Request):- Contains 'content-id' in query_params
        URLs:
            GET {{base_app_url}}/content/?content-id=2
        """
        # Get the user
        user = request.user

        # Get the content_id and fetch the content from the database
        content_id = request.query_params.get('content_id')
        content = Content.objects.filter(id=content_id).first()
        if content is None:
            # Object with `content_id` not found; Throw failure response
            return Response(
                data={
                    "status": "failure",
                    "message": "Requested entity not found"
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get the medias associated using reverse lookup
        medias = content.medias

        # Serialize the content and store the data
        serialized_content = ContentSerializer(content, context={'purpose': 'download'}).data
        
            
        return Response(
            data={
                "status": "success",
                "message": "Presigned URL generated successfully",
                "data": serialized_content
            }
        )
        
    def post(self, request):
        """View to handle post requests. Creates new contents based on a post dictionary
        
        Args:
            request:- Contains a json in request body
                {
                    "content_type": string, // This is among (COMMENT, POST, HISTORY, CHAT), Default is POST
                    "text": string, // Text part of the Content, Default is empty string
                    "parent_id": int, // Id of the parent, if exists. Default is null
                    "medias":[
                        {
                            // Now this is a single media object
                            "s3_object_key": string, // Object key, generated at client end, // REQUIRED
                                                    // gets encrypted here. ("my_example_object_key")
                            "extension": string, // Extension of the file ("mp4") // REQUIRED
                            "meta": {
                                // Meta data about the file
                                "size": int, // Size in KBs (8000)
                                "resolution": string, // Resolution as a string ("1200*1150")
                                "time": int, // Time required to see that file in milliseconds (60000)
                                "file_type": "video", // Type of the content this file has. [document, video, image, audio, gif, etc...]
                            } // meta dict is OPTIONAL, Default is empty json {}
                        } 
                    ] // A list of all medias associated with this content. Default is empty list
                }
        URLs:
            POST {{base_app_url}}/content/
        """
        # Get the user
        user = request.user
        
        # Get the content type (chat, chat history, post, comment)
        content_type = getattr(ContentTypeChoices, request.data.get('content_type'), ContentTypeChoices.POST)
        
        # Get the text data from the chat post
        text = request.data.get('text', '')
        
        # Get the id of the parent content, and find the parent
        parent_id = request.data.get('parent_id', None)
        parent = None
        if parent_id is not None:
            parent = Content.objects.filter(id=parent_id).first()
            if parent is None:
                # No parent with id `parent_id` found
                return Response(
                    data={
                        "status": "failure",
                        "message": f"No parent exists with the given parent id {parent_id}",
                    }
                )
                
        # Try to create the content instance
        try:
            content = Content.objects.create(
                user=user,
                content_type=content_type,
                text=text,
                parent=parent
            )
        except Exception as e:
            # Can't create the content instance
            return Response(
                data={
                    "status": "failure",
                    "message": "Couldn't create the new object"
                },
                status=status.HTTP_304_NOT_MODIFIED
            )

        # Create the media files if any
        medias = request.data.get('medias', [])
        for media in medias:
            if media is None: continue
            
            # Encrypt the passed object key and create the presigned url for this media
            upload_object = None
            s3_object_key = get_encrypted_s3_key(media['s3_object_key'])
        
            # Register an object against the s3_object_key
            upload_object, created = UploadObject.objects.get_or_create(s3_object_key=s3_object_key)
            
            if not created:
                # Object key should be unique, return failure
                return Response(
                    data={
                        "status": "failure",
                        "message": "Object key should be unique"
                    }
                )
            
            # Set the attributes of the uploaded_object, and save it
            upload_object.extension = media.get('extension')
            upload_object.time = media.get('time')
            upload_object.meta = media.get('meta')
            upload_object.content = content
            upload_object.save()

        # Save the content model and Send the signal
        content.save()
        content_save.send_robust(sender=Content, instance=content)
        
        # Get the created responses
        serialized_content = ContentSerializer(content, context={'purpose':'upload'}).data
        
        # Return the response
        return Response(
            data={
                "status": "success",
                "message": "New Object created successfully",
                "data": serialized_content
            },
            status=status.HTTP_201_CREATED
        )
        
    def patch(self, request):
        """View to handle post requests. Updates the existing contents text based on a post dictionary.
        Deleted the media if any specified
        
        Args:
            request:- Contains a json in request body
                {
                    "content_id": string, // ID that uniquely identifies the content
                    "text": string, // Text part of the Content, Default is empty string
                    "medias":[
                        {
                            "operation": string, // Operation to do with media // REQUIRED
                            // Now this is a single media object
                            "s3_object_key": string, // Object key, generated at client end, // REQUIRED
                                                    // gets encrypted here. ("my_example_object_key")
                            "extension": string, // Extension of the file ("mp4") // REQUIRED
                            "meta": {
                                // Meta data about the file
                                "size": int, // Size in KBs (8000)
                                "resolution": string, // Resolution as a string ("1200*1150")
                                "time": int, // Time required to see that file in milliseconds (60000)
                                "file_type": "video", // Type of the content this file has. [document, video, image, audio, gif, etc...]
                            } // meta dict is OPTIONAL, Default is empty json {}
                        }
                    ] // A list of all medias associated with this content. Default is empty list
                }
        URLs:
            PATCH {{base_app_url}}/content/
        """
        # Get the user
        user = request.user
        
        # Get the content-id and fetch the content object
        content_id = request.data.get('content-id')
        content = Content.objects.filter(id=content_id).first()
        if content is None:
            return Response(
                data={
                    "status": "failure",
                    "message": "Requested entity not found"
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Change the text
        text = request.body.get('text', None)
        if text is not None:
            content.text = text
        
        # Get current time
        delete_time = timezone.now()
        errors = []
        for media in request.body.get('medias', []):
            s3_object_key = media['s3_object_key']
            if media["operation"] == "delete":    
                media_object = UploadObject.objects.filter(s3_object_key=s3_object_key).first()
                if media_object is None:
                    errors.append(media)
                else:
                    media_object.deleted_on = delete_time
                    media_object.save()
            else:
                # Encrypt the passed object key and create the presigned url for this media
                upload_object = None
                s3_object_key = get_encrypted_s3_key(media['s3_object_key'])
            
                # Register an object against the s3_object_key
                upload_object, created = UploadObject.objects.get_or_create(s3_object_key=s3_object_key)
                
                if not created:
                    # Object key should be unique, return failure
                    return Response(
                        data={
                            "status": "failure",
                            "message": "Object key should be unique"
                        }
                    )
                
                # Set the attributes of the uploaded_object, and save it
                upload_object.extension = media.get('extension')
                upload_object.time = media.get('time')
                upload_object.meta = media.get('meta')
                upload_object.content = content
                upload_object.save()

        # Save the content and Sent the signal
        content.save()
        content_save.send_robust(sender=Content, instance=content)
        
        # Serialize the content
        serializer = ContentSerializer(content)
        if errors:
            return Response(
                data={
                    "status": "failure",
                    "message": "Some medias were not operated on successfully. Content-text updated successfully"
                }
            )
        return Response(
            data={
                "status": "success",
                "message": "Content-text updated successfully. Requested medias deleted/created successfully",
                "data": serializer.data
            }
        )
                
    def delete(self, request):
        """View to handle delete requests. Deletes the entire content tree
        
        Args:
            request:- Contains a json in request body
                {
                    "content_id": string, //Required
                }
        URLs:
            DELETE {{base_app_url}}/content/
        """
        # Get the user
        user = request.user
        
        # Get the content id and fetch the content object
        content_id = request.data.get('content_id', None)
        content = Content.objects.filter(id=content_id).first()
        if content is None:
            return Response(
                data={
                    "status": "failure",
                    "message": "Requested entity not found"
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if the current user is either the creator of the content, else is creator of any of the content's parent
        content_alias = content
        is_content_admin = False
        while content_alias is not None:
            if user == content_alias.user:
                is_content_admin = True
                break
            content_alias = content_alias.parent
        
        # If the current user is somehow the content admin, try to delete the content, recursively!!
        delete_time = timezone.now()
        
        def recursive_delete(root, delete_time):
            """Function to recursively go through content graph (DFS) 
            and soft delete the objects"""
            if root is None: return
            
            root.deleted_on = delete_time
            root.save()
            for media in root.medias:
                media.deleted_on = delete_time
                media.save()
            for child in content.children:
                recursive_delete(child, delete_time)
        
        if is_content_admin:
            recursive_delete(content)
        
        return Response(
                data={
                    "status": "success",
                    "message": "Content and all of its sub contents deleted successfully"
                },
                status=status.HTTP_200_OK
            )