from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('employees', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='avatar',
            field=models.ImageField(blank=True, null=True, upload_to='employee_avatars/'),
        ),
        migrations.CreateModel(
            name='EmployeeDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('document_type', models.CharField(
                    choices=[
                        ('contract', 'Employment Contract'),
                        ('id', 'ID / Passport'),
                        ('certificate', 'Certificate / Degree'),
                        ('nda', 'NDA / Agreement'),
                        ('payslip', 'Payslip'),
                        ('warning', 'Warning Letter'),
                        ('other', 'Other'),
                    ],
                    default='other',
                    max_length=30,
                )),
                ('file', models.FileField(upload_to='employee_documents/%Y/%m/')),
                ('notes', models.TextField(blank=True)),
                ('uploaded_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('employee', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='documents',
                    to='employees.employee',
                )),
                ('uploaded_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='uploaded_documents',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'employee_documents',
                'ordering': ['-uploaded_at'],
            },
        ),
    ]
