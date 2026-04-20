from django.contrib import admin
from apps.teams.models import Team, TeamMembership

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'department', 'supervisor', 'member_count', 'is_active']

@admin.register(TeamMembership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ['team', 'member', 'is_active', 'joined_at']
