# Generated manually on 2025-12-29
# Remove unused fields from ProblemGroup model: app_scale, mode, created_by_user

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("problems", "0004_alter_problem_problem_id_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Remove app_scale field
        migrations.RemoveField(
            model_name="problemgroup",
            name="app_scale",
        ),
        # Remove mode field
        migrations.RemoveField(
            model_name="problemgroup",
            name="mode",
        ),
        # Remove created_by_user foreign key
        migrations.RemoveField(
            model_name="problemgroup",
            name="created_by_user",
        ),
    ]
