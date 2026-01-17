from django.dispatch import Signal

# args: user, username, request, event
honeyword_detected = Signal()
