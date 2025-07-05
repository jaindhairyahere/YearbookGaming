from django.db import models

class ModerationStatesChoices(models.IntegerChoices):
    APPROVED = 1, "Approved"
    REJECTED = 2, "Rejected"
    UNDER_REVIEW = 3, "Under review"
    MARKED_SPAM = 4, "Marked Spam"
    ESCALATED = 5, "Escalated"
    
class ContentTypeChoices(models.IntegerChoices):
    CHAT = 1, "Chat"
    HISTORY = 2, "Chat History"
    POST = 3, "Feed Post"
    COMMENT = 4, "Comment"
    
class RequestTypeChoices(models.IntegerChoices):
    FRIEND_REQUEST = 1, "Friend Request"
    MESSAGE_REQUEST = 2, "Message Request"
    
class ChatTypeChoices(models.IntegerChoices):
    ONE_ON_ONE = 1, "One on one chat"
    GROUP = 2, "Group Chat"
    COMMUNITY = 3, "Community Chat"

class PresenceStatesChoices(models.IntegerChoices):
    LOGGED_IN = 1, "Logged In"
    LOGGED_OFF = 2, "Logged Off"
    
class FriendPolicyChoices(models.IntegerChoices):
    ALLOW_REQUESTS = 1, "Other players can send friend requests"
    FORBID_REQUESTS = -1, "Other players can send friend requests"
    
class ChatPolicyChoices(models.IntegerChoices):
    FORBID_MESSAGES = 0, "No one can send messages"
    ALLOW_FRIENDS = 1, "Friends can send messages"
    ANONYMOUS = 2, "Anyone can send messages"
    
class ReactionChoices(models.IntegerChoices):
    LIKE = 1, "LIKE",
    LOVE = 2, "LOVE",
    LAUGH = 3, "LAUGH",
    HUG = 4, "HUG",
    WOW = 5, "WOW",
    SAD = 6, "SAD",
    ANGRY = 7, "ANGRY",
    CRY = 8, "CRY",
    SMIRK = 9, "SMIRK",
    PLEAD = 10, "PLEAD",
    SWAG = 11, "SWAG",
    SHIT = 12, "SHIT"

class GroupPermissions:
    ADMIN_MODERATOR = [("*", "*", "*", "*"),]
    SIMPLE_MODERATOR = [("user_client", ["Content", "UploadObject"], "*", "*")]