"""teams/models.py — Team & Hierarchy Management"""
from django.db import models
from django.conf import settings


class Team(models.Model):
    name = models.CharField(max_length=100)
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='led_teams'
    )
    department = models.ForeignKey(
        'employees.Department', on_delete=models.CASCADE, related_name='teams'
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'teams'
        ordering = ['department', 'name']
        unique_together = [('name', 'department')]

    def __str__(self):
        return f"{self.name} ({self.department.code})"

    @property
    def member_count(self):
        return self.memberships.filter(is_active=True).count()


class TeamMembership(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='memberships')
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='team_memberships'
    )
    is_active = models.BooleanField(default=True)
    joined_at = models.DateField(auto_now_add=True)

    class Meta:
        db_table = 'team_memberships'
        unique_together = [('team', 'member')]
        ordering = ['team', 'joined_at']

    def __str__(self):
        return f"{self.member} in {self.team}"
