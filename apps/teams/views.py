"""teams/views.py"""
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404, render
from django.views.generic import ListView, DetailView
from django.views import View

from apps.teams.models import Team, TeamMembership
from apps.employees.models import Employee, Department
from apps.accounts.decorators import AdminRequiredMixin

User = get_user_model()


class TeamListView(LoginRequiredMixin, ListView):
    model = Team
    template_name = 'teams/list.html'
    context_object_name = 'teams'

    def get_queryset(self):
        user = self.request.user
        if user.is_admin:
            return Team.objects.filter(is_active=True).select_related('supervisor', 'department')
        elif user.is_supervisor:
            # Show teams this user supervises
            return Team.objects.filter(supervisor=user, is_active=True).select_related('department')
        else:
            # Show teams the user is a member of
            return Team.objects.filter(
                memberships__member=user, memberships__is_active=True, is_active=True
            ).select_related('supervisor', 'department').distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_admin:
            ctx['can_create'] = True
            ctx['departments'] = Department.objects.filter(is_active=True)
            ctx['all_users'] = User.objects.filter(is_active=True).select_related('role')
        return ctx


class TeamDetailView(LoginRequiredMixin, DetailView):
    model = Team
    template_name = 'teams/detail.html'
    context_object_name = 'team'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['members'] = self.object.memberships.filter(is_active=True).select_related('member', 'member__employee_profile')
        ctx['can_manage'] = self.request.user.is_admin or self.request.user == self.object.supervisor
        # Available users to add (not already members)
        if ctx['can_manage']:
            existing_ids = self.object.memberships.filter(is_active=True).values_list('member_id', flat=True)
            ctx['available_users'] = User.objects.filter(is_active=True).exclude(pk__in=existing_ids).order_by('first_name')
        return ctx


class TeamCreateView(AdminRequiredMixin, View):
    def post(self, request):
        name = request.POST.get('name', '').strip()
        dept_id = request.POST.get('department')
        supervisor_id = request.POST.get('supervisor')
        description = request.POST.get('description', '')

        if not name or not dept_id:
            messages.error(request, "Team name and department are required.")
            return redirect('teams:list')

        try:
            dept = Department.objects.get(pk=dept_id)
            supervisor = User.objects.get(pk=supervisor_id) if supervisor_id else None
            team = Team.objects.create(
                name=name, department=dept, supervisor=supervisor, description=description
            )
            messages.success(request, f"Team '{team.name}' created.")
        except Exception as e:
            messages.error(request, f"Error creating team: {e}")
        return redirect('teams:list')


class TeamAddMemberView(LoginRequiredMixin, View):
    def post(self, request, pk):
        team = get_object_or_404(Team, pk=pk)
        if not (request.user.is_admin or request.user == team.supervisor):
            messages.error(request, "Access denied.")
            return redirect('teams:detail', pk=pk)

        user_id = request.POST.get('member')
        try:
            member = User.objects.get(pk=user_id)
            obj, created = TeamMembership.objects.get_or_create(
                team=team, member=member,
                defaults={'is_active': True}
            )
            if not created:
                obj.is_active = True
                obj.save(update_fields=['is_active'])
            messages.success(request, f"{member.get_full_name()} added to {team.name}.")
        except User.DoesNotExist:
            messages.error(request, "User not found.")
        return redirect('teams:detail', pk=pk)


class TeamRemoveMemberView(LoginRequiredMixin, View):
    def post(self, request, pk, member_pk):
        team = get_object_or_404(Team, pk=pk)
        if not (request.user.is_admin or request.user == team.supervisor):
            messages.error(request, "Access denied.")
            return redirect('teams:detail', pk=pk)

        TeamMembership.objects.filter(team=team, member_id=member_pk).update(is_active=False)
        messages.success(request, "Member removed from team.")
        return redirect('teams:detail', pk=pk)
