# Generated manually for explicit primary key naming
# Renames id -> problem_group_id and id -> problem_id

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("problems", "0002_answer"),
    ]

    operations = [
        # Rename ProblemGroup.id -> ProblemGroup.problem_group_id
        migrations.RenameField(
            model_name="problemgroup",
            old_name="id",
            new_name="problem_group_id",
        ),
        # Rename Problem.id -> Problem.problem_id
        migrations.RenameField(
            model_name="problem",
            old_name="id",
            new_name="problem_id",
        ),
    ]
