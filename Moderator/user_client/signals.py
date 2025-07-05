from django.dispatch import Signal

user_request_incoming = Signal()
user_logout = Signal()
user_is_active = Signal()
ticket_patched = Signal()