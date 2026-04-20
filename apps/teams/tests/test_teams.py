"""
apps/teams/tests/test_teams.py
Tests for: Team, TeamMembership models and views
"""
import pytest
from django.urls import reverse
from apps.teams.models import Team, TeamMembership


# ═══════════════════════════════════════════════
#  TEAM MODEL TESTS
# ═══════════════════════════════════════════════

class TestTeamModel:

    def make_team(self, db, supervisor_user, department, **kwargs):
        defaults = {
            'name': 'Alpha Team',
            'supervisor': supervisor_user,
            'department': department,
            'is_active': True,
        }
        defaults.update(kwargs)
        return Team.objects.create(**defaults)

    def test_team_created(self, db, supervisor_user, department):
        team = self.make_team(db, supervisor_user, department)
        assert team.pk is not None
        assert team.is_active is True

    def test_team_str(self, db, supervisor_user, department):
        team = self.make_team(db, supervisor_user, department)
        assert 'Alpha Team' in str(team)
        assert department.code in str(team)

    def test_team_unique_per_department(self, db, supervisor_user, department):
        from django.db import IntegrityError
        self.make_team(db, supervisor_user, department)
        with pytest.raises(IntegrityError):
            Team.objects.create(
                name='Alpha Team',
                supervisor=supervisor_user,
                department=department,
            )

    def test_same_team_name_different_dept(self, db, supervisor_user, department):
        from apps.employees.models import Department
        other_dept = Department.objects.create(name='Finance', code='FIN')
        team1 = self.make_team(db, supervisor_user, department)
        team2 = Team.objects.create(
            name='Alpha Team',
            supervisor=supervisor_user,
            department=other_dept,
        )
        assert team1.pk != team2.pk

    def test_team_member_count_zero(self, db, supervisor_user, department):
        team = self.make_team(db, supervisor_user, department)
        assert team.member_count == 0

    def test_team_member_count_with_members(self, db, supervisor_user, employee_user, department):
        team = self.make_team(db, supervisor_user, department)
        TeamMembership.objects.create(team=team, member=employee_user, is_active=True)
        assert team.member_count == 1

    def test_inactive_members_not_counted(self, db, supervisor_user, employee_user, department):
        team = self.make_team(db, supervisor_user, department)
        TeamMembership.objects.create(team=team, member=employee_user, is_active=False)
        assert team.member_count == 0


# ═══════════════════════════════════════════════
#  TEAM MEMBERSHIP MODEL TESTS
# ═══════════════════════════════════════════════

class TestTeamMembershipModel:

    def test_membership_created(self, db, supervisor_user, employee_user, department):
        team = Team.objects.create(
            name='Beta Team', supervisor=supervisor_user, department=department
        )
        membership = TeamMembership.objects.create(team=team, member=employee_user)
        assert membership.pk is not None
        assert membership.is_active is True

    def test_membership_str(self, db, supervisor_user, employee_user, department):
        team = Team.objects.create(
            name='Gamma Team', supervisor=supervisor_user, department=department
        )
        membership = TeamMembership.objects.create(team=team, member=employee_user)
        assert str(employee_user) in str(membership)
        assert 'Gamma Team' in str(membership)

    def test_unique_membership_per_team(self, db, supervisor_user, employee_user, department):
        from django.db import IntegrityError
        team = Team.objects.create(
            name='Delta Team', supervisor=supervisor_user, department=department
        )
        TeamMembership.objects.create(team=team, member=employee_user)
        with pytest.raises(IntegrityError):
            TeamMembership.objects.create(team=team, member=employee_user)

    def test_same_user_multiple_teams(self, db, supervisor_user, employee_user, department):
        team1 = Team.objects.create(name='Team 1', supervisor=supervisor_user, department=department)
        team2 = Team.objects.create(name='Team 2', supervisor=supervisor_user, department=department)
        m1 = TeamMembership.objects.create(team=team1, member=employee_user)
        m2 = TeamMembership.objects.create(team=team2, member=employee_user)
        assert m1.pk != m2.pk


# ═══════════════════════════════════════════════
#  TEAM VIEWS TESTS
# ═══════════════════════════════════════════════

class TestTeamViews:

    def test_team_list_requires_login(self, client):
        response = client.get(reverse('teams:list'))
        assert response.status_code == 302
        assert 'login' in response['Location']

    def test_team_list_loads_for_admin(self, admin_client):
        response = admin_client.get(reverse('teams:list'))
        assert response.status_code == 200

    def test_team_list_loads_for_supervisor(self, supervisor_client):
        response = supervisor_client.get(reverse('teams:list'))
        assert response.status_code == 200

    def test_team_detail_accessible_by_admin(self, admin_client, supervisor_user, department, db):
        team = Team.objects.create(
            name='Test Team', supervisor=supervisor_user, department=department
        )
        response = admin_client.get(reverse('teams:detail', kwargs={'pk': team.pk}))
        assert response.status_code == 200

    def test_nonexistent_team_returns_404(self, admin_client):
        response = admin_client.get(reverse('teams:detail', kwargs={'pk': 99999}))
        assert response.status_code == 404
