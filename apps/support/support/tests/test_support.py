"""
apps/support/tests/test_support.py
Tests for: SupportCategory, SupportTicket, TicketResponse models and views
"""
import pytest
from django.urls import reverse
from django.utils import timezone
from apps.support.models import SupportCategory, SupportTicket, TicketResponse


# ═══════════════════════════════════════════════
#  SUPPORT CATEGORY MODEL TESTS
# ═══════════════════════════════════════════════

class TestSupportCategoryModel:

    def test_category_str(self, support_category):
        assert str(support_category) == 'IT Support'

    def test_category_name_unique(self, db, support_category):
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            SupportCategory.objects.create(name='IT Support')

    def test_multiple_categories(self, db, support_category):
        SupportCategory.objects.create(name='HR Queries')
        SupportCategory.objects.create(name='Payroll')
        assert SupportCategory.objects.count() >= 3


# ═══════════════════════════════════════════════
#  SUPPORT TICKET MODEL TESTS
# ═══════════════════════════════════════════════

class TestSupportTicketModel:

    def make_ticket(self, employee_user, support_category, **kwargs):
        defaults = {
            'requester': employee_user,
            'category': support_category,
            'subject': 'Cannot login to system',
            'description': 'I am unable to login since this morning.',
            'priority': 'medium',
        }
        defaults.update(kwargs)
        return SupportTicket.objects.create(**defaults)

    def test_ticket_created(self, db, employee_user, support_category):
        ticket = self.make_ticket(employee_user, support_category)
        assert ticket.pk is not None
        assert ticket.status == 'open'

    def test_ticket_number_auto_generated(self, db, employee_user, support_category):
        ticket = self.make_ticket(employee_user, support_category)
        assert ticket.ticket_number.startswith('TKT-')
        assert len(ticket.ticket_number) == 12  # TKT- + 8 digits

    def test_ticket_number_unique(self, db, employee_user, support_category):
        ticket1 = self.make_ticket(employee_user, support_category, subject='Issue 1')
        ticket2 = self.make_ticket(employee_user, support_category, subject='Issue 2')
        assert ticket1.ticket_number != ticket2.ticket_number

    def test_ticket_str(self, db, employee_user, support_category):
        ticket = self.make_ticket(employee_user, support_category)
        assert ticket.ticket_number in str(ticket)
        assert 'Cannot login' in str(ticket)

    def test_resolved_at_set_when_status_resolved(self, db, employee_user, support_category):
        ticket = self.make_ticket(employee_user, support_category)
        assert ticket.resolved_at is None
        ticket.status = 'resolved'
        ticket.save()
        assert ticket.resolved_at is not None

    def test_default_status_is_open(self, db, employee_user, support_category):
        ticket = self.make_ticket(employee_user, support_category)
        assert ticket.status == 'open'

    def test_priority_choices(self, db, employee_user, support_category):
        for priority in ['low', 'medium', 'high', 'critical']:
            ticket = self.make_ticket(employee_user, support_category,
                                       priority=priority, subject=f'{priority} issue')
            assert ticket.priority == priority

    def test_ticket_ordering(self, db, employee_user, support_category):
        t1 = self.make_ticket(employee_user, support_category, subject='Old ticket')
        t2 = self.make_ticket(employee_user, support_category, subject='New ticket')
        tickets = list(SupportTicket.objects.filter(requester=employee_user))
        # Most recent first
        assert tickets[0].pk == t2.pk


# ═══════════════════════════════════════════════
#  TICKET RESPONSE MODEL TESTS
# ═══════════════════════════════════════════════

class TestTicketResponseModel:

    def test_response_created(self, db, employee_user, admin_user, support_category):
        ticket = SupportTicket.objects.create(
            requester=employee_user,
            category=support_category,
            subject='Help needed',
            description='Please help.',
        )
        response = TicketResponse.objects.create(
            ticket=ticket,
            responder=admin_user,
            message='We will look into this.',
        )
        assert response.pk is not None
        assert response.is_internal is False

    def test_internal_response(self, db, employee_user, admin_user, support_category):
        ticket = SupportTicket.objects.create(
            requester=employee_user,
            category=support_category,
            subject='Internal test',
            description='Test.',
        )
        response = TicketResponse.objects.create(
            ticket=ticket,
            responder=admin_user,
            message='Internal note only.',
            is_internal=True,
        )
        assert response.is_internal is True

    def test_response_str(self, db, employee_user, admin_user, support_category):
        ticket = SupportTicket.objects.create(
            requester=employee_user,
            category=support_category,
            subject='Str test',
            description='Test.',
        )
        response = TicketResponse.objects.create(
            ticket=ticket,
            responder=admin_user,
            message='Reply here.',
        )
        assert str(admin_user) in str(response)
        assert ticket.ticket_number in str(response)


# ═══════════════════════════════════════════════
#  SUPPORT VIEWS TESTS
# ═══════════════════════════════════════════════

class TestSupportViews:

    def test_ticket_list_requires_login(self, client):
        response = client.get(reverse('support:list'))
        assert response.status_code == 302
        assert 'login' in response['Location']

    def test_ticket_list_loads_for_employee(self, employee_client):
        response = employee_client.get(reverse('support:list'))
        assert response.status_code == 200

    def test_ticket_create_page_loads(self, employee_client):
        response = employee_client.get(reverse('support:create'))
        assert response.status_code == 200

    def test_employee_can_create_ticket(self, employee_client, employee_user, support_category):
        response = employee_client.post(reverse('support:create'), {
            'category': support_category.pk,
            'subject': 'My laptop is broken',
            'description': 'My laptop stopped working after update.',
            'priority': 'high',
        })
        assert response.status_code in [200, 302]
        assert SupportTicket.objects.filter(
            requester=employee_user, subject='My laptop is broken'
        ).exists()

    def test_ticket_detail_accessible_by_requester(self, employee_client, employee_user, support_category):
        ticket = SupportTicket.objects.create(
            requester=employee_user,
            category=support_category,
            subject='My ticket',
            description='Some issue.',
        )
        response = employee_client.get(reverse('support:detail', kwargs={'pk': ticket.pk}))
        assert response.status_code == 200

    def test_ticket_detail_contains_subject(self, employee_client, employee_user, support_category):
        ticket = SupportTicket.objects.create(
            requester=employee_user,
            category=support_category,
            subject='Unique subject XYZ',
            description='Some issue.',
        )
        response = employee_client.get(reverse('support:detail', kwargs={'pk': ticket.pk}))
        assert b'Unique subject XYZ' in response.content

    def test_nonexistent_ticket_returns_404(self, employee_client):
        response = employee_client.get(reverse('support:detail', kwargs={'pk': 99999}))
        assert response.status_code == 404
