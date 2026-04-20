"""notifications/context_processors.py"""
from apps.notifications.models import Notification


def unread_notifications(request):
    if request.user.is_authenticated:
        qs = Notification.objects.filter(recipient=request.user, is_read=False).order_by('-created_at')
        count = qs.count()
        unread = qs[:10]
        return {
            'unread_notifications': unread,
            'unread_count': count,
        }
    return {'unread_notifications': [], 'unread_count': 0}
