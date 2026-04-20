from django.contrib import admin
from apps.support.models import SupportCategory, SupportTicket, TicketResponse

@admin.register(SupportCategory)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon']

@admin.register(SupportTicket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_number', 'requester', 'subject', 'priority', 'status', 'created_at']
    list_filter = ['status', 'priority', 'category']
    search_fields = ['ticket_number', 'subject', 'requester__username']

@admin.register(TicketResponse)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'responder', 'is_internal', 'created_at']
