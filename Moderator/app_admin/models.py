# Library Imports
from django.conf import settings
from django.contrib.auth.models import Group as BaseGroup, Permission as BasePermission, PermissionsMixin
from django.contrib.contenttypes.models import  ContentType
from django.db import models
from django.db.models.query import Q
from unicodedata import normalize

# Library Import
from utils.models import TimeStampedModel
from utils.functions import checkList, returnList, getUpper, getLower

class Permission(BasePermission):
    """Proxy Model for `Permission` - Overloaded with multiple class methods"""
    class Meta:
        app_label = 'app_admin'
        proxy = True
    
    @classmethod
    def get_permission_objects(cls, app_labels="*", model_names="*", field_names="*", actions="*"):
        """Function that returns all the permissions corrosponding to given parameters

        Args:
            app_labels (str, List[str], Optional): _description_. Defaults to all apps.
            model_names (str, List[str], Optional): _description_. Defaults to all models of app_labels.
            field_names (str, List[str], Optional): _description_. Defaults to all field of models.
            actions (str, List[str], Optional): _description_. Defaults to all actions.

        Returns:
            list[Permission]: list of all the permission objects
        """
        # So we break this into two parts. First parse the parameters in a good format. This involves
        # adding support for all kinds of parameters, list, string, tuple, or a `*`.  If we have 
        # multiple apps, then no sense to specify multiple models; Similar logic for (models, fields)
        # Second, This will be followed by loooping through them and getting the permissions
        
        # Parse the field names and actions. Convert them to list of lower class strings
        field_names = checkList(returnList(getLower(field_names)))
        actions = checkList(returnList(getLower(actions)))
        
        # Parse the app labels and model names. Their case **SHOULD NOT** be forcefully changed
        app_labels = checkList(returnList(app_labels))
        model_names = checkList(returnList(model_names))
        
        # Deal with the `*`
        if "*" in app_labels:
            app_labels = getLower(settings.PROJECT_APPS)
        if "*" in app_labels or len(app_labels)>1:
            model_names = ["*",]
        if "*" in model_names or len(model_names)>1:
            field_names = ["*",]
            
        # Create List to store processed data
        returned_permissions = []
                
        # Iterate over Parameters
        for app_label in app_labels:
            for model_name in model_names:
                # Get the content type given then app_label and model_name
                app_query = Q() if app_label=="*" else Q(app_label=app_label)
                model_query = Q() if model_name=="*" else Q(model = model_name)
                contenttype = ContentType.objects.filter(Q(app_query & model_query)).first()
                if contenttype is not None:
                    # If we have a content-type, try to fetch the field and action permissions
                    for field_name in field_names:
                        for action in actions:
                            field_query = Q() if field_name=="*" else Q(codename__contains = field_name)
                            action_query = Q() if action=="*" else Q(codename__contains = action)
                            # Get the related permissions
                            query_results = Permission.objects\
                                .filter(content_type=contenttype)\
                                .filter(Q(field_query&action_query))
                            # Extend the permissions
                            returned_permissions.extend(query_results)
        
        return returned_permissions
    
    @classmethod
    def format(cls):
        """A permission is stored as (content_type, name, codename). This method
        returns the format of the codename"""
        return "{model}|{action}|{field}"
    
    @classmethod       
    def get_all_permission_objects(cls):
        """Returns list of permissions subject to query on app_label, model_name, field_name and action."""
        return cls.get_permission_objects(app_labels="*", model_names="*", field_names="*", actions="*")
        
        
class Group(BaseGroup):
    """
    Groups are a generic way of categorizing users to apply permissions, or
    some other label, to those users. A user can belong to any number of
    groups.

    A user in a group automatically has all the permissions granted to that
    group. For example, if the group 'Site editors' has the permission
    can_edit_home_page, any user in that group will have that permission.

    This class extends the django provided `Group` model, to incorporate the custom
    permissions model that we've created above
    
    Defined Fields:
    
    Inherited Fields:
        name (str): Name of the group as a string
        permissions (Permission): List of permissions that are attached to this group
    
    Reverse Fields:
        role (app_admin.Role): Role object corrorsponding to this group object (One-to-One Relation) 
    """
    def __init__(self, *args, **kwargs):
        # Initialize the group model as before
        super(BaseGroup, self).__init__(*args, **kwargs)
        # A new permissions field that shares a many-to-many relationship
        # with `app_admin.Permission` and not `django.contrib.auth.models.Permission`
        permissions = models.ManyToManyField(
            "app_admin.Permission",
            verbose_name='permissions',
            blank=True,
            help_text='Permissions linked with this group'
        )
        # Set this new permissions field to contribute to original permissions field
        # This way django will use the same table in the database
        permissions.contribute_to_class(BaseGroup, 'permissions')
    class Meta:
        app_label = 'app_admin'
        proxy = True
   
        
class Role(TimeStampedModel):
    """Model for storing Users. This is also the AUTH_USER_MODEL used in the service
    
    Defined Fields:
        role_id: ID of the `Role` that is stored in the Auth Service Database
        group: One-on-one mapping to `Group` table
        
    Reverse Fields:
        YearbookGaming_users: The Ojects of `YearbookGamingModerator` associated with this instance of `YearbookGamingUser`
    
    Inherited Fields:
        created_on (TimeStampedModel): Time when an instance is created on the server side
        updated_on (TimeStampedModel): Time when an instance is updated on the server side
        deleted_on (TimeStampedModel): Time when an instance is deleted on the server side
    """
    role_id = models.PositiveSmallIntegerField(
        default=0,
        help_text='ID of the `Role` that is stored in the Auth Service Database'
    )
    group = models.OneToOneField(
        Group, on_delete=models.CASCADE,
        help_text='The group to which this user belongs to')


class YearbookGamingUserManager(models.Manager):
    """Model Manager for the `YearbookGamingUser` model.
    
    Methods in this are straight copy-pasted from django.contrib.auth.models.AbstractBaseUserManager

    For more information, check: 
        https://docs.djangoproject.com/en/4.0/topics/migrations/#model-managers
    """
    use_in_migrations = True
    
    def get_by_natural_key(self, username):
        """Gets an instance by it's natural_key i.e. username
        The `YearbookGamingUser` has ensured that the username is unique"""
        return self.get(**{self.model.USERNAME_FIELD: username})
    
    def _create_user(self, username, **extra_fields):
        """
        Create and save a user with the given username, YearbookGaming_id, role
        """
        YearbookGaming_id = extra_fields.pop('YearbookGaming_id', None)
        role = extra_fields.pop('role', None)
        role = Role.objects.get(role_id=role)
        if not YearbookGaming_id:
            raise ValueError('The given YearbookGaming_id must be set')
        # Lookup the real model class from the global app registry so this
        # manager method can be used in migrations. This is fine because
        # managers are by definition working on the real model.
        user = self.model(YearbookGaming_id=YearbookGaming_id, role=role, username=username)
        user.save(using=self._db)
        return user
    
    def create_user(self, username, **extra_fields):
        """Creates a simple no-staff, and no-superuser user .
        Ensures that the `is_staff` and `is_superuser` to be False,
        and then creates the new `YearbookGamingUser` instance

        Returns:
            YearbookGamingUser: a newly created YearbookGamingUser instance
        """
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(username, **extra_fields)

    def create_superuser(self, username, **extra_fields):
        """Function run when `createsuperuser` command is used.
        Ensures that the `is_staff` and `is_superuser` to be True,
        and then creates the new `YearbookGamingUser` instance

        Returns:
            YearbookGamingUser: a newly created YearbookGamingUser instance
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(username, **extra_fields)


class YearbookGamingUser(TimeStampedModel, PermissionsMixin):
    """Model for storing Users. This is also the AUTH_USER_MODEL used in the service
    
    Defined Fields:
        YearbookGaming_id: ID of the `YearbookGamingUser` that is stored in the Auth Service Database
        username: Username of the `YearbookGamingUser` that is stored in the Auth Service Database
        email: Email of the `YearbookGamingUser` that is stored in the Auth Service Database
        role: Role of the `YearbookGamingUser` that is stored in the Auth Service Database. 
            Foreign key to `Role` model
        is_staff: Whether this User can access the admin portal
        is_active: Whether this User is allowed to Login
    
    Reverse Fields:
        moderator: The Object of `YearbookGamingModerator` associated with this instance of `YearbookGamingUser`
        tickets: A list of `ModerationTicket`s associated with this user instance 
        board: The object of `TicketBoard` associated with this user instance 
    
    Inherited Fields:
        created_on (TimeStampedModel): Time when an instance is created on the server side
        updated_on (TimeStampedModel): Time when an instance is updated on the server side
        deleted_on (TimeStampedModel): Time when an instance is deleted on the server side
    
    Property Methods:
        is_anonymous : If the user could be identified
        is_authenticated: If the user is authenticated or not
    
    Static Methods:
        normalize_username: Helper method that does the NFK Normalization of the username
        
    For more information on the fields, check: 
        https://docs.djangoproject.com/en/4.0/topics/auth/customizing/
    """
    YearbookGaming_id = models.PositiveIntegerField(
        default=1, unique=True,
        help_text=
            'Designated the user\'s YearbookGaming_id. This is supplied by the Auth-Service'
        )
    username = models.CharField(
        max_length=100,
        unique=True,
        help_text=
            'Designated the user\'s username. This is supplied by the Auth-Service'
    )
    email = models.EmailField(
        default="default@YearbookGamingtoys.com",
        help_text= 'Designated the user\'s email. This is supplied by the Auth-Service'
    )
    role = models.ForeignKey(
        "app_admin.Role", on_delete=models.CASCADE,
        related_name="YearbookGaming_users", 
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
    
    objects = YearbookGamingUserManager()
    USERNAME_FIELD = 'YearbookGaming_id'
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

    def set_active(self):
        """Sets the moderator associated with this user to be active"""
        self.moderator.set_active()
        
    def set_inactive(self):
        """Sets the moderator associated with this user to be in-active"""
        self.moderator.set_inactive()

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