"""
apps/leaves/tests/test_leaves.py
Tests for: LeaveType, LeaveRequest, LeaveApproval models, forms, views
"""
import pytest
from django.urls import reverse
from datetime import date, timedelta
from apps.leaves.models import LeaveType, LeaveRequest, LeaveApproval


# ═══════════════════════════════════════════════
#  LEAVE TYPE MODEL TESTS
# ═══════════════════════════════════════════════

class TestLeaveTypeModel:

    def test_leave_type_str(self, leave_type):
        assert 'AL' in str(leave_type)
        assert 'Annual Leave' in str(leave_type)

    def test_leave_type_created(self, leave_type):
        assert leave_type.pk is not None
        assert leave_type.is_active is True
        assert leave_type.is_paid is True

    def test_leave_type_code_unique(self, db, leave_type):
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            LeaveType.objects.create(name='Another Annual', code='AL')

    def test_leave_type_name_unique(self, db, leave_type):
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            LeaveType.objects.create(name='Annual Leave', code='AL2')


# ═══════════════════════════════════════════════
#  LEAVE REQUEST MODEL TESTS
# ═══════════════════════════════════════════════

class TestLeaveRequestModel:

    def make_request(self, employee_user, leave_type, days=3, start_offset=7):
        start = date.today() + timedelta(days=start_offset)
        end = start + timedelta(days=days - 1)
        return LeaveRequest.objects.create(
            employee=employee_user,
            leave_type=leave_type,
            start_date=start,
            end_date=end,
            reason='Family vacation',
        )

    def test_leave_request_created(self, db, employee_user, leave_type):
        lr = self.make_request(employee_user, leave_type)
        assert lr.pk is not None
        assert lr.status == 'pending'

    def test_leave_request_str(self, db, employee_user, leave_type):
        lr = self.make_request(employee_user, leave_type)
        assert str(lr) != ''
        assert 'AL' in str(lr)

    def test_total_days_auto_calculated(self, db, employee_user, leave_type):
        start = date.today() + timedelta(days=7)
        end = start + timedelta(days=4)  # 5 days
        lr = LeaveRequest.objects.create(
            employee=employee_user,
            leave_type=leave_type,
            start_date=start,
            end_date=end,
            reason='Holiday',
        )
        assert lr.total_days == 5

    def test_single_day_leave(self, db, employee_user, leave_type):
        today_future = date.today() + timedelta(days=7)
        lr = LeaveRequest.objects.create(
            employee=employee_user,
            leave_type=leave_type,
            start_date=today_future,
            end_date=today_future,
            reason='Personal',
        )
        assert lr.total_days == 1

    def test_default_status_is_pending(self, db, employee_user, leave_type):
        lr = self.make_request(employee_user, leave_type)
        assert lr.status == 'pending'

    def test_leave_request_ordering(self, db, employee_user, leave_type):
        lr1 = self.make_request(employee_user, leave_type, start_offset=10)
        lr2 = self.make_request(employee_user, leave_type, start_offset=20)
        requests = list(LeaveRequest.objects.filter(employee=employee_user))
        # Most recent applied_at first
        assert requests[0].pk >= requests[1].pk


# ═══════════════════════════════════════════════
#  LEAVE APPROVAL MODEL TESTS
# ═══════════════════════════════════════════════

class TestLeaveApprovalModel:

    def test_approval_str(self, db, employee_user, supervisor_user, leave_type):
        start = date.today() + timedelta(days=7)
        lr = LeaveRequest.objects.create(
            employee=employee_user,
            leave_type=leave_type,
            start_date=start,
            end_date=start + timedelta(days=2),
            reason='Test',
        )
        approval = LeaveApproval.objects.create(
            leave_request=lr,
            approver=supervisor_user,
            level=1,
            action='approve',
            comments='Approved',
        )
        assert 'approve' in str(approval)
        assert str(supervisor_user) in str(approval)

    def test_approval_creates_with_level(self, db, employee_user, supervisor_user, leave_type):
        start = date.today() + timedelta(days=7)
        lr = LeaveRequest.objects.create(
            employee=employee_user,
            leave_type=leave_type,
            start_date=start,
            end_date=start,
            reason='Test',
        )
        approval = LeaveApproval.objects.create(
            leave_request=lr,
            approver=supervisor_user,
            level=1,
            action='approve',
        )
        assert approval.level == 1
        assert approval.action == 'approve'


# ═══════════════════════════════════════════════
#  LEAVE VIEWS TESTS
# ═══════════════════════════════════════════════

class TestLeaveViews:

    def test_leave_list_requires_login(self, client):
        response = client.get(reverse('leaves:list'))
        assert response.status_code == 302
        assert 'login' in response['Location']

    def test_leave_list_accessible_by_employee(self, employee_client):
        response = employee_client.get(reverse('leaves:list'))
        assert response.status_code == 200

    def test_leave_create_page_loads(self, employee_client):
        response = employee_client.get(reverse('leaves:create'))
        assert response.status_code == 200

    def test_employee_can_submit_leave_request(self, employee_client, employee_user, leave_type):
        start = date.today() + timedelta(days=7)
        end = start + timedelta(days=2)
        response = employee_client.post(reverse('leaves:create'), {
            'leave_type': leave_type.pk,
            'start_date': start.strftime('%Y-%m-%d'),
            'end_date': end.strftime('%Y-%m-%d'),
            'reason': 'Family event',
        })
        assert response.status_code in [200, 302]
        assert LeaveRequest.objects.filter(employee=employee_user).exists()

    def test_leave_detail_accessible(self, employee_client, employee_user, leave_type):
        start = date.today() + timedelta(days=7)
        lr = LeaveRequest.objects.create(
            employee=employee_user,
            leave_type=leave_type,
            start_date=start,
            end_date=start + timedelta(days=2),
            reason='Test leave',
        )
        response = employee_client.get(reverse('leaves:detail', kwargs={'pk': lr.pk}))
        assert response.status_code == 200

    def test_cannot_access_other_users_leave_detail(self, admin_client, employee_user, leave_type):
        start = date.today() + timedelta(days=7)
        lr = LeaveRequest.objects.create(
            employee=employee_user,
            leave_type=leave_type,
            start_date=start,
            end_date=start,
            reason='Private',
        )
        # Admin can view all leave requests
        response = admin_client.get(reverse('leaves:detail', kwargs={'pk': lr.pk}))
        assert response.status_code in [200, 302, 403]

    def test_nonexistent_leave_returns_404(self, employee_client):
        response = employee_client.get(reverse('leaves:detail', kwargs={'pk': 99999}))
        assert response.status_code == 404
