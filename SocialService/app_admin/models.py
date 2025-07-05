from celery import shared_task
from django.conf import settings
from django.contrib.auth.models import Group as BaseGroup, Permission as BasePermission, PermissionsMixin
from django.db import models
from django.db.models.query import Q
from unicodedata import normalize
from django.core.exceptions import ObjectDoesNotExist
from utils.models import TimeStampedModel
from utils.functions import checkList, returnList, getUpper
from utils.choices import ChatPolicyChoices, FriendPolicyChoices

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
    
class Group(BaseGroup):
    def __init__(self, *args, **kwargs):
        super(BaseGroup, self).__init__(*args, **kwargs)
        permissions = models.ManyToManyField(
            Permission,
            verbose_name='permissions',
            blank=True,
        )
        permissions.contribute_to_class(BaseGroup, 'permissions')

class Role(TimeStampedModel):
    """My thought is to use roles for showing different HTML pages to users like 
    based on the user category and use group for permission purposes"""
    role_id = models.PositiveSmallIntegerField(default=0)
    group = models.OneToOneField(Group, on_delete=models.CASCADE)

class YearbookUserManager(models.Manager):
    use_in_migrations = True
    def get_by_natural_key(self, username):
        return self.get(**{self.model.USERNAME_FIELD: username})
    
    def get(self, *args, **kwargs):
        try:
            return super().get(*args, **kwargs)
        except ObjectDoesNotExist:
            return None
        
    
    def _create_user(self, username, **extra_fields):
        """
        Create and save a user with the given Yearbook_id, role
        """
        Yearbook_id = extra_fields.pop('Yearbook_id', None)
        role = extra_fields.pop('role', None)
        role = Role.objects.get(role_id=role)
        if not Yearbook_id:
            raise ValueError('The given Yearbook_id must be set')
        # Lookup the real model class from the global app registry so this
        # manager method can be used in migrations. This is fine because
        # managers are by definition working on the real model.
        user = self.model(Yearbook_id=Yearbook_id, role=role)
        user.save(using=self._db)
        return user
    
    def create_user(self, username, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(username, **extra_fields)

    def create_superuser(self, username, **extra_fields):

        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(username, **extra_fields)


class YearbookUser(TimeStampedModel, PermissionsMixin):
    """Model for storing Users. This is also the AUTH_USER_MODEL used in the service
    
    Defined Fields:
        Yearbook_id: ID of the `YearbookUser` that is stored in the Auth Service Database
        username: Username of the `YearbookUser` that is stored in the Auth Service Database
        email: Email of the `YearbookUser` that is stored in the Auth Service Database
        role: Role of the `YearbookUser` that is stored in the Auth Service Database. 
            Foreign key to `Role` model
        is_staff: Whether this User can access the admin portal
        is_active: Whether this User is allowed to Login
    
    Reverse Fields:
        moderator: The Object of `YearbookModerator` associated with this instance of `YearbookUser`
    
    Inherited Fields:
        created_on (TimeStampedModel): Time when an instance is created on the server side
        updated_on (TimeStampedModel): Time when an instance is updated on the server side
        deleted_on (TimeStampedModel): Time when an instance is deleted on the server side
    
    Property Methods:
        is_anonymous : If the user could be identified
        is_authenticated: If the user is authenticated or not
    
    For more information on the fields, check: 
        https://docs.djangoproject.com/en/4.0/topics/auth/customizing/
    """
    Yearbook_id = models.PositiveIntegerField(
        default=1, unique=True,
        help_text=
            'Designated the user\'s Yearbook_id. This is supplied by the Auth-Service'
        )
    username = models.CharField(
        max_length=100,
        unique=True,
        help_text=
            'Designated the user\'s username. This is supplied by the Auth-Service'
    )
    email = models.EmailField(
        default="default@Yearbooktoys.com",
        help_text= 'Designated the user\'s email. This is supplied by the Auth-Service'
    )
    role = models.ForeignKey(
        "app_admin.Role", on_delete=models.CASCADE,
        related_name="Yearbook_users", 
        help_text=
            'Designates the Role this user has using a foreign key to the Role table'
            'This is usually supplied by the Auth-Service'
    )
    is_staff = models.BooleanField(
        'staff',
        default=True,
        help_text=
            'Designates whether this user should be treated as staff. '
            'Only staff can access the admin portal.'
        ,
    )
    is_active = models.BooleanField(
        'active',
        default=True,
        help_text=
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ,
    )
    
    objects = YearbookUserManager()
    USERNAME_FIELD = 'Yearbook_id'
    REQUIRED_FIELDS = ['role', 'username'] # Required to create a user using `createsuperuser` 

    @staticmethod
    def normalize_username(username):
        """Applies NFKC Unicode normalization to usernames so that visually identical 
        characters with different Unicode code points are considered identical. Refer to
        `django.contrib.auth.models.AbstractBaseUser.normalize_username` for more details.
        
        Args:
            username (str): username of the user

        Returns:
            str: Normalized Username of the user
        """
        return normalize('NFKC', username) if isinstance(username, str) else username

    @property
    def is_anonymous(self):
        """
        Always return False. This is a way of comparing User objects to
        anonymous users.
        
        Returns:
            bool: Any object of this class is not anonymous (it is identified)
        """
        return False
    
    @property
    def is_authenticated(self):
        """
        Always return True. This is a way to tell if the user has been
        authenticated in templates.
        
        Returns:
            bool: Any object of this class is always authenticated
        """
        return True

    def get_full_name(self):
        """
        This method is required by Django for things like handling emails.
        Typically this would be the user's first and last name. Since we do
        not store the user's real name, we return their username instead.
        """
        return self.username

    def get_short_name(self):
        """
        This method is required by Django for things like handling emails.
        Typically, this would be the user's first name. Since we do not store
        the user's real name, we return their username instead.
        """
        return self.username

class Policy(TimeStampedModel):
    chat_policy = models.IntegerField(default=ChatPolicyChoices.ALLOW_FRIENDS, choices=ChatPolicyChoices.choices)
    friend_policy = models.IntegerField(default=FriendPolicyChoices.ALLOW_REQUESTS, choices=FriendPolicyChoices.choices)

class YearbookPlayer(TimeStampedModel):
    user = models.OneToOneField(YearbookUser, on_delete=models.CASCADE, related_name="player")
    friends = models.ManyToManyField("self")
    policy = models.ForeignKey(Policy, on_delete=models.CASCADE)
    blocked_users = models.ManyToManyField("self")