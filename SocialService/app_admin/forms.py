from django import forms
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError

class TokenAuthenticationForm(forms.Form):
    """
    Base class for authenticating users. Extend this to get a form that accepts
    YearbookGaming_id/token logins.
    """
    YearbookGaming_id = forms.IntegerField(widget=forms.TextInput(attrs={'autofocus': True}), required=False)
    token = forms.CharField(max_length=100)

    error_messages = {
        'invalid_login': 
            "Please enter a correct %(YearbookGaming_id)s and token. Note that both "
            "fields may be case-sensitive."
        ,
        'inactive': "This account is inactive.",
    }

    def __init__(self, request=None, *args, **kwargs):
        """
        The 'request' parameter is set for custom auth use by subclasses.
        The form data comes in via the standard 'data' kwarg.
        """
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)
        
        
    def clean(self):
        """Cleans the form to validate the fields. Attempts to authenticate the user
        using user-provided credentials. Also checks if the user is allowed to login

        Raises: `Validation Error` if the user can't log in

        Returns: None
        """
        YearbookGaming_id = self.cleaned_data.get('YearbookGaming_id', None)
        token = self.cleaned_data.get('token', None)

        if token is not None:
            self.user_cache = authenticate(self.request, token=token, YearbookGaming_id = YearbookGaming_id)
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data

    def confirm_login_allowed(self, user):
        """
        Controls whether the given User may log in. This is a policy setting,
        independent of end-user authentication. This default behavior is to
        allow login by active users, and reject login by inactive users.

        If the given user cannot log in, this method should raise a
        ``ValidationError``.

        If the given user may log in, this method should return None.
        """
        if not user.is_active:
            raise ValidationError(
                self.error_messages['inactive'],
                code='inactive',
            )

    def get_user(self):
        return self.user_cache

    def get_invalid_login_error(self):
        return ValidationError(
            self.error_messages['invalid_login'],
            code='invalid_login',
            params={'username': self.username_field.verbose_name},
        )

