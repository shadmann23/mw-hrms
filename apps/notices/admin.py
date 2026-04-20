from django.contrib import admin
from apps.notices.models import Notice

@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ['title', 'priority', 'visibility', 'publish_date', 'is_active', 'views_count']
    list_filter = ['priority', 'visibility', 'is_active']
    search_fields = ['title', 'content']
    date_hierarchy = 'publish_date'
