from django.conf import settings
from botocore.exceptions import ClientError
import random
import datetime
import jwt, hashlib, json

def convert_perm_avcd_to_crud(perm, return_tuple=True):
    """ Converts a model based permission of AVCD type (source: django ModelAdmin) 
    to a CRUD permission. This is done by simply substituting AVCD by CRUD in the 
    permission string. Returns a tuple containing the app label, permission type,
    model name and the modified permission string
    
    Args:
        perm (str): String denoting a permission - {app_label}.{perm_type}_{model}
        return_tuple (bool): Boolean denoting if a tuple should be returned
         
    Returns:
        tuple: app_label, perm_type, model_name, perm => If return_tuple is True
        str: The modified permission string => If return_tuple is False
    """
    # Split the permission to get various components
    perm_split = perm.split('.')
    perm_1_split = perm_split[1].split('_')
    # Get and switch the permission type (ACVD to CRUD)
    perm_type = perm_1_split[0]
    perm_type = 'create' if perm_type=='add' else perm_type
    perm_type = 'retrieve' if perm_type=='view' else perm_type
    perm_type = 'update' if perm_type=='change' else perm_type    
    # Create the new permission string
    perm = f"{perm_split[0]}.{perm_type}_{perm_1_split[1]}"
    # Return the calculated values
    if return_tuple:
        return perm_split[0], perm_type, perm_1_split[1], perm
    else:
        return perm
    
def convert_perm_crud_to_avcd(perm, return_tuple=False):
    """ Converts a model based permission of CRUD type (source: Permission.codename)
    to a AVCD permission (possible destination - django ModelAdmin). This is done by 
    simply substituting CRUD by AVCD in the permission string. Returns a 4-element tuple
    containing the app label, permission type, model name and the modified permission string
    
    Args:
        perm (str): String denoting a permission - {perm_type}.{model_name}.{field_name}
        return_tuple (bool): Boolean denoting if a tuple should be returned
         
    Returns:
        tuple: model_name, perm_type, field_name, perm => If return_tuple is True
        str: The modified permission string => If return_tuple is False
    """
    # Split the permission to get various components
    perm_split = perm.split('.')
    # Get and switch the permission type (ACVD to CRUD)
    perm_type = perm_split[0]
    perm_type = 'add' if perm_type=='change' else perm_type
    perm_type = 'view' if perm_type=='retrieve' else perm_type
    perm_type = 'change' if perm_type=='update' else perm_type
    if return_tuple:
        return perm_split[1], perm_type, perm_split[2], perm
    else:
        return perm

def getUpper(param): 
    # Function to Convert every parameter to uppercase, if list convert all elements to uppercase
    return param.upper() if isinstance(param, str) else [f.upper() for f in param]

def getLower(param): 
    # Function to Convert every parameter to uppercase, if list convert all elements to uppercase
    return param.lower() if isinstance(param, str) else [f.lower() for f in param]

def checkList(list): 
    # Function to Check List for *, if yes then remove other elements
    return ["*"] if "*" in list else list        
        
def returnList(object):
    # Function to If parameter is a single string, convert it to list
    return [object,] if isinstance(object, str) else object

def get_set_user(request, user):
    """Sets the user attribute of the request, and return it

    Args:
        request (HttpRequest): a wsgi request
        user (YearbookGamingUser): the user to be assigned

    Returns:
        YearbookGamingUser: the user instance
    """
    if not hasattr(request, '_cached_user'):
        request._cached_user = user
    return request._cached_user

def get_set_token(request, token):
    """Sets the token attribute of the request, and return it

    Args:
        request (HttpRequest): a wsgi request
        token (str): the jwt token assigned to user

    Returns:
        str: the token
    """
    if not hasattr(request, '_token'):
        request._token = token
    return request._token

def generate_access_token(user, intent="access"):
    """Generate JWT Access token for the given user and with a given intent

    Args:
        user (YearbookGamingUser): the user object
        intent (str, Optional): Intent of the token. For login, it should be access.
            For logout, it should by anything random (eg - "logout"). Defaults to "access".

    Returns:
        str: The jwt token
    """
    # Get the current time
    current_time = datetime.datetime.now()
    # Create the payload
    payload = {
            'token_type': intent,
            'jti': user.id if user else -1,
            'user_id': user.id if user else -1,
            'exp': current_time + datetime.timedelta(minutes=settings.JWT_EXPIRE_TIME),
            'iat': current_time
        }
    # Generate the token and return it
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

def  get_encrypted_s3_key(s3_object_key):
    """Generate encrypted object key for the given s3_object_key
    
    Args:
        s3_object_key (str): The object key of the s3 object
        
    Returns:
        str: The encrypted key
    """
    # Get the current time as string
    curr_time = datetime.datetime.strftime(datetime.datetime.now(),"%d%m%Y:%H%M%S%f")
    payload = json.dumps({
        "s3_key": s3_object_key,
        "time": curr_time
    }).encode()
    return hashlib.sha512(payload).hexdigest()

def create_presigned_url_upload(s3_object_key):
    """Generate a presigned URL to share an S3 object
    
    :param bucket_name: string
    :param object_name: string
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Presigned URL as string. If error, returns None.
    """
    # Generate a presigned URL for the S3 object
    bucket_name = settings.BUCKET_NAME
    expiration = settings.PRESIGNED_EXPIRATION_TIME
    
    # Generate the random unique object_key
    object_key = get_encrypted_s3_key(s3_object_key)
    
    # Try to create a pre-signed url
    try:
        response = settings.S3_CLIENT.generate_presigned_post(bucket_name, object_key, ExpiresIn=expiration)
    except ClientError as e:
        return {
            "status": "failure",
            "message": "Can't generate the presigned url"
        }
           
    return {
        "status": "success",
        "message": "Pre-signed Url Generated Successfully",
        "data": response
    }
    
    
def create_presigned_url_download(object_key):
    """Generate a presigned URL to share an S3 object

    :param bucket_name: string
    :param object_name: string
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Presigned URL as string. If error, returns None.
    """

    # Generate a presigned URL for the S3 object
    bucket_name = settings.BUCKET_NAME
    expiration = settings.PRESIGNED_EXPIRATION_TIME
    
    try:
        response = settings.S3_CLIENT.generate_presigned_url(
            ClientMethod='get_object', 
            Params={'Bucket': bucket_name, 'Key': object_key},
            ExpiresIn=expiration
        )
    except ClientError as e:
        return {
            "status": "failure",
            "message": "Can't generate the presigned url"
        }
    # The response contains the presigned URL
    return {
        "status": "success",
        "message": "Presigned url generated successfully",
        "data": response
    }
