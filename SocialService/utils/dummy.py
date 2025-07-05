def get_dummy_data(token: str):
    """Generate dummy login information given a login token

    #### TODO - Remove dependency on this function 
    
    Args:
        token (str): the auth-token

    Returns:
        dict: A sample response from login service
    """
    tokens = token.split('_')
    if token.endswith("admin_moderator"):
        Yearbook_id=2
        role_id=2
        group_name="ADMIN_MODERATOR"
    elif token.endswith("simple_moderator"):
        Yearbook_id=1
        role_id=1
        group_name="SIMPLE_MODERATOR"
    elif token.endswith("wrong_token"):
        return{
            "success": False
        }
    else:
        Yearbook_id = int(tokens[-1])
        if tokens[-2]=='client':
            role_id = 3
            group_name = "CLIENT_USER"
        elif 'simple_moderator' in token:
            role_id = 1
            group_name = "SIMPLE_MODERATOR"
        elif 'admin_moderator' in token:
            role_id = 2
            group_name = "ADMIN_MODERATOR"
    return {
        "Yearbook_id": Yearbook_id,
        "role_id": role_id,
        "group_name": group_name,
        "username": f"nick_{Yearbook_id}_{tokens[0]}",
        "email": f"nick_{Yearbook_id}_{tokens[0]}@Yearbooktoys.com",
        "success": True
    }