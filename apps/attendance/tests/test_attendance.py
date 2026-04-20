"""
apps/attendance/tests/test_attendance.py
Tests for: AttendanceRecord model, check-in/out logic, views
"""
import pytest
from django.urls import reverse
from django.utils import timezone
from datetime import date, datetime, timedelta
from apps.attendance.models import AttendanceRecord


# ═══════════════════════════════════════════════
#  ATTENDANCE MODEL TESTS
# ═══════════════════════════════════════════════

class TestAttendanceRecordModel:

    def test_create_attendance_record(self, db, employee_user):
        record = AttendanceRecord.objects.create(
            employee=employee_user,
            date=date.today(),
            status='present',
        )
        assert record.pk is not None
        assert str(employee_user.username) in str(record)

    def test_attendance_str(self, db, employee_user):
        record = AttendanceRecord.objects.create(
            employee=employee_user,
            date=date.today(),
            status='present',
        )
        assert str(record) != ''

    def test_unique_per_employee_per_day(self, db, employee_user):
        from django.db import IntegrityError
        today = date.today()
        AttendanceRecord.objects.create(employee=employee_user, date=today)
        with pytest.raises(IntegrityError):
            AttendanceRecord.objects.create(employee=employee_user, date=today)

    def test_working_hours_calculated_on_save(self, db, employee_user):
        check_in = timezone.make_aware(datetime(2024, 6, 1, 8, 0))
        check_out = timezone.make_aware(datetime(2024, 6, 1, 17, 0))
        record = AttendanceRecord.objects.create(
            employee=employee_user,
            date=date(2024, 6, 1),
            check_in=check_in,
            check_out=check_out,
        )
        assert float(record.working_hours) == 9.0

    def test_status_set_to_present_on_full_day(self, db, employee_user):
        check_in = timezone.make_aware(datetime(2024, 6, 1, 8, 30))
        check_out = timezone.make_aware(datetime(2024, 6, 1, 17, 0))
        record = AttendanceRecord.objects.create(
            employee=employee_user,
            date=date(2024, 6, 1),
            check_in=check_in,
            check_out=check_out,
        )
        assert record.status == 'present'

    def test_status_set_to_late_if_checkin_after_9_15(self, db, employee_user):
        check_in = timezone.make_aware(datetime(2024, 6, 1, 9, 30))
        check_out = timezone.make_aware(datetime(2024, 6, 1, 17, 0))
        record = AttendanceRecord.objects.create(
            employee=employee_user,
            date=date(2024, 6, 1),
            check_in=check_in,
            check_out=check_out,
        )
        assert record.status == 'late'

    def test_status_set_to_half_day_if_under_4_hours(self, db, employee_user):
        check_in = timezone.make_aware(datetime(2024, 6, 1, 9, 0))
        check_out = timezone.make_aware(datetime(2024, 6, 1, 12, 0))
        record = AttendanceRecord.objects.create(
            employee=employee_user,
            date=date(2024, 6, 1),
            check_in=check_in,
            check_out=check_out,
        )
        assert record.status == 'half_day'

    def test_is_checked_in_property(self, db, employee_user):
        check_in = timezone.now()
        record = AttendanceRecord.objects.create(
            employee=employee_user,
            date=date.today(),
            check_in=check_in,
        )
        assert record.is_checked_in is True
        assert record.is_complete is False

    def test_is_complete_property(self, db, employee_user):
        check_in = timezone.make_aware(datetime(2024, 6, 1, 8, 0))
        check_out = timezone.make_aware(datetime(2024, 6, 1, 17, 0))
        record = AttendanceRecord.objects.create(
            employee=employee_user,
            date=date(2024, 6, 1),
            check_in=check_in,
            check_out=check_out,
        )
        assert record.is_complete is True
        assert record.is_checked_in is False

    def test_record_without_checkout_has_no_working_hours(self, db, employee_user):
        record = AttendanceRecord.objects.create(
            employee=employee_user,
            date=date.today(),
            check_in=timezone.now(),
        )
        assert record.working_hours is None

    def test_attendance_status_choices(self, db, employee_user):
        valid_statuses = ['present', 'absent', 'late', 'half_day', 'on_leave']
        for status in valid_statuses:
            day = date.today() - timedelta(days=valid_statuses.index(status) + 1)
            record = AttendanceRecord.objects.create(
                employee=employee_user,
                date=day,
                status=status,
            )
            assert record.status == status


# ═══════════════════════════════════════════════
#  ATTENDANCE VIEWS TESTS
# ═══════════════════════════════════════════════

class TestAttendanceViews:

    def test_checkin_requires_login(self, client):
        response = client.post(reverse('attendance:checkin'))
        assert response.status_code == 302
        assert 'login' in response['Location']

    def test_employee_can_checkin(self, employee_client, employee_user):
        # Make sure no existing record for today
        AttendanceRecord.objects.filter(employee=employee_user, date=date.today()).delete()
        response = employee_client.post(reverse('attendance:checkin'))
        assert response.status_code in [200, 302]
        assert AttendanceRecord.objects.filter(employee=employee_user, date=date.today()).exists()

    def test_cannot_checkin_twice_same_day(self, employee_client, employee_user):
        AttendanceRecord.objects.filter(employee=employee_user, date=date.today()).delete()
        # First check-in
        employee_client.post(reverse('attendance:checkin'))
        # Second check-in should not create a new record
        employee_client.post(reverse('attendance:checkin'))
        count = AttendanceRecord.objects.filter(employee=employee_user, date=date.today()).count()
        assert count == 1

    def test_employee_can_checkout(self, employee_client, employee_user):
        AttendanceRecord.objects.filter(employee=employee_user, date=date.today()).delete()
        AttendanceRecord.objects.create(
            employee=employee_user,
            date=date.today(),
            check_in=timezone.now(),
        )
        response = employee_client.post(reverse('attendance:checkout'))
        assert response.status_code in [200, 302]
        record = AttendanceRecord.objects.get(employee=employee_user, date=date.today())
        assert record.check_out is not None

    def test_history_page_requires_login(self, client):
        response = client.get(reverse('attendance:history'))
        assert response.status_code == 302

    def test_history_page_loads_for_employee(self, employee_client):
        response = employee_client.get(reverse('attendance:history'))
        assert response.status_code == 200

    def test_admin_report_requires_admin(self, employee_client):
        response = employee_client.get(reverse('attendance:admin_report'))
        assert response.status_code in [302, 403]

    def test_admin_report_accessible_by_admin(self, admin_client):
        response = admin_client.get(reverse('attendance:admin_report'))
        assert response.status_code == 200
