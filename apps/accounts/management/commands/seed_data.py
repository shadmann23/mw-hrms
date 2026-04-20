"""seed_data.py — Seed initial HRMS data"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed initial HRMS data'

    def handle(self, *args, **options):
        with transaction.atomic():
            self._create_roles()
            self._create_departments()
            self._create_leave_types()
            self._create_support_categories()
            self._create_shift_templates()
            self._create_users()
            self._create_teams()
        self.stdout.write(self.style.SUCCESS('\n✓ Seed data created successfully.\n'))
        self.stdout.write('Demo credentials:')
        self.stdout.write('  admin      / admin123')
        self.stdout.write('  supervisor / super123')
        self.stdout.write('  employee   / emp123\n')

    def _create_roles(self):
        from apps.accounts.models import Role
        for name, desc in [
            ('admin', 'Full HR system access'),
            ('supervisor', 'Team management and approvals'),
            ('employee', 'Standard employee access'),
        ]:
            Role.objects.get_or_create(name=name, defaults={'description': desc})
        self.stdout.write('  ✓ Roles')

    def _create_departments(self):
        from apps.employees.models import Department, Position
        for code, name in [('ENG','Engineering'),('HR','Human Resources'),('FIN','Finance'),('MKT','Marketing'),('OPS','Operations')]:
            dept, _ = Department.objects.get_or_create(code=code, defaults={'name': name})
            Position.objects.get_or_create(title='Manager', department=dept, defaults={'level': 3})
            Position.objects.get_or_create(title='Staff', department=dept, defaults={'level': 1})
        self.stdout.write('  ✓ Departments & Positions')

    def _create_leave_types(self):
        from apps.leaves.models import LeaveType
        for code, name, days, doc, paid in [
            ('AL','Annual Leave',21,False,True),('SL','Sick Leave',14,True,True),
            ('ML','Maternity Leave',90,True,True),('PL','Paternity Leave',7,True,True),
            ('UL','Unpaid Leave',30,False,False),('EL','Emergency Leave',3,False,True),
        ]:
            LeaveType.objects.get_or_create(code=code, defaults={'name':name,'max_days_per_year':days,'requires_documentation':doc,'is_paid':paid})
        self.stdout.write('  ✓ Leave Types')

    def _create_support_categories(self):
        from apps.support.models import SupportCategory
        for name, icon in [('IT & Technical','monitor'),('HR Policy','book'),('Payroll & Benefits','dollar-sign'),('Facilities','home'),('General Inquiry','help-circle')]:
            SupportCategory.objects.get_or_create(name=name, defaults={'icon': icon})
        self.stdout.write('  ✓ Support Categories')

    def _create_shift_templates(self):
        from apps.shifts.models import ShiftTemplate
        for name, start, end, color in [
            ('Morning','07:00','15:00','#3B82F6'),('Day','09:00','17:00','#10B981'),
            ('Afternoon','13:00','21:00','#F59E0B'),('Night','21:00','05:00','#8B5CF6'),
        ]:
            ShiftTemplate.objects.get_or_create(name=name, defaults={'start_time':start,'end_time':end,'color':color})
        self.stdout.write('  ✓ Shift Templates')

    def _create_users(self):
        from apps.accounts.models import Role
        from apps.employees.models import Employee, Department, Position

        hr = Department.objects.get(code='HR')
        eng = Department.objects.get(code='ENG')
        admin_role = Role.objects.get(name='admin')
        sup_role = Role.objects.get(name='supervisor')
        emp_role = Role.objects.get(name='employee')
        hr_manager = Position.objects.get(title='Manager', department=hr)
        eng_manager = Position.objects.get(title='Manager', department=eng)
        eng_staff = Position.objects.get(title='Staff', department=eng)

        admin_user, created = User.objects.get_or_create(username='admin', defaults={
            'email':'admin@peopleos.local','first_name':'Alex','last_name':'Carter',
            'role':admin_role,'is_staff':True,'is_active':True,
        })
        if created:
            admin_user.set_password('admin123'); admin_user.save()
            Employee.objects.get_or_create(user=admin_user, defaults={
                'employee_id':'EMP-001','department':hr,'position':hr_manager,'hire_date':'2020-01-01','employment_type':'full_time',
            })

        sup_user, created = User.objects.get_or_create(username='supervisor', defaults={
            'email':'supervisor@peopleos.local','first_name':'Sam','last_name':'Rivera',
            'role':sup_role,'is_active':True,
        })
        if created:
            sup_user.set_password('super123'); sup_user.save()
            Employee.objects.get_or_create(user=sup_user, defaults={
                'employee_id':'EMP-002','department':eng,'position':eng_manager,'hire_date':'2021-03-15','employment_type':'full_time',
            })

        emp_user, created = User.objects.get_or_create(username='employee', defaults={
            'email':'employee@peopleos.local','first_name':'Jordan','last_name':'Lee',
            'role':emp_role,'is_active':True,
        })
        if created:
            emp_user.set_password('emp123'); emp_user.save()
            Employee.objects.get_or_create(user=emp_user, defaults={
                'employee_id':'EMP-003','department':eng,'position':eng_staff,
                'supervisor':sup_user,'hire_date':'2022-06-01','employment_type':'full_time',
            })

        self.stdout.write('  ✓ Demo Users')

    def _create_teams(self):
        from apps.teams.models import Team, TeamMembership
        from apps.employees.models import Department

        eng = Department.objects.get(code='ENG')
        try:
            sup_user = User.objects.get(username='supervisor')
            emp_user = User.objects.get(username='employee')
        except User.DoesNotExist:
            return

        team, _ = Team.objects.get_or_create(
            name='Engineering Team',
            defaults={'department': eng, 'supervisor': sup_user, 'description': 'Core engineering team', 'is_active': True}
        )
        TeamMembership.objects.get_or_create(team=team, member=emp_user, defaults={'is_active': True})
        TeamMembership.objects.get_or_create(team=team, member=sup_user, defaults={'is_active': True})
        self.stdout.write('  ✓ Teams')
