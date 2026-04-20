"""
apps/notices/tests/test_notices.py
Tests for: Notice model, views
"""
import pytest
from django.urls import reverse
from django.utils import timezone
from datetime import date, timedelta
from apps.notices.models import Notice


# ═══════════════════════════════════════════════
#  NOTICE MODEL TESTS
# ═══════════════════════════════════════════════

class TestNoticeModel:

    def make_notice(self, db, admin_user, **kwargs):
        defaults = {
            'title': 'Test Notice',
            'content': 'This is a test notice content.',
            'priority': 'normal',
            'visibility': 'all',
            'is_active': True,
            'publish_date': date.today(),
            'created_by': admin_user,
        }
        defaults.update(kwargs)
        return Notice.objects.create(**defaults)

    def test_notice_str(self, db, admin_user):
        notice = self.make_notice(db, admin_user)
        assert 'Test Notice' in str(notice)
        assert 'NORMAL' in str(notice)

    def test_notice_created(self, db, admin_user):
        notice = self.make_notice(db, admin_user)
        assert notice.pk is not None
        assert notice.views_count == 0

    def test_notice_is_visible_when_active_and_published(self, db, admin_user):
        notice = self.make_notice(db, admin_user, publish_date=date.today(), is_active=True)
        assert notice.is_visible is True

    def test_notice_not_visible_when_inactive(self, db, admin_user):
        notice = self.make_notice(db, admin_user, is_active=False)
        assert notice.is_visible is False

    def test_notice_not_visible_when_future_publish(self, db, admin_user):
        future = date.today() + timedelta(days=5)
        notice = self.make_notice(db, admin_user, publish_date=future)
        assert notice.is_visible is False

    def test_notice_is_expired(self, db, admin_user):
        past = date.today() - timedelta(days=1)
        notice = self.make_notice(db, admin_user, expiry_date=past)
        assert notice.is_expired is True

    def test_notice_not_expired_without_expiry(self, db, admin_user):
        notice = self.make_notice(db, admin_user)
        assert notice.is_expired is False

    def test_notice_not_expired_future_expiry(self, db, admin_user):
        future = date.today() + timedelta(days=10)
        notice = self.make_notice(db, admin_user, expiry_date=future)
        assert notice.is_expired is False

    def test_notice_priority_choices(self, db, admin_user):
        for priority in ['low', 'normal', 'high', 'urgent']:
            notice = self.make_notice(db, admin_user, priority=priority, title=f'{priority} notice')
            assert notice.priority == priority

    def test_notice_visibility_choices(self, db, admin_user):
        for vis in ['all', 'admin', 'supervisors', 'employees']:
            notice = self.make_notice(db, admin_user, visibility=vis, title=f'{vis} notice')
            assert notice.visibility == vis


# ═══════════════════════════════════════════════
#  NOTICE VIEWS TESTS
# ═══════════════════════════════════════════════

class TestNoticeViews:

    def test_notice_list_requires_login(self, client):
        response = client.get(reverse('notices:list'))
        assert response.status_code == 302
        assert 'login' in response['Location']

    def test_notice_list_loads_for_employee(self, employee_client):
        response = employee_client.get(reverse('notices:list'))
        assert response.status_code == 200

    def test_notice_create_blocked_for_employee(self, employee_client):
        response = employee_client.get(reverse('notices:create'))
        assert response.status_code in [302, 403]

    def test_notice_create_accessible_by_admin(self, admin_client):
        response = admin_client.get(reverse('notices:create'))
        assert response.status_code == 200

    def test_admin_can_create_notice(self, admin_client, admin_user):
        response = admin_client.post(reverse('notices:create'), {
            'title': 'New Company Policy',
            'content': 'Please read the updated policy document.',
            'priority': 'high',
            'visibility': 'all',
            'publish_date': date.today().strftime('%Y-%m-%d'),
            'is_active': True,
        })
        assert response.status_code in [200, 302]
        assert Notice.objects.filter(title='New Company Policy').exists()

    def test_notice_detail_loads(self, admin_client, admin_user, db):
        notice = Notice.objects.create(
            title='Detail Test',
            content='Content here.',
            created_by=admin_user,
            publish_date=date.today(),
        )
        response = admin_client.get(reverse('notices:detail', kwargs={'pk': notice.pk}))
        assert response.status_code == 200

    def test_nonexistent_notice_returns_404(self, employee_client):
        response = employee_client.get(reverse('notices:detail', kwargs={'pk': 99999}))
        assert response.status_code == 404
