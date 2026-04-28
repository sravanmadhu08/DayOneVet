from django.db import migrations, models


def move_forest_profiles_to_classic(apps, schema_editor):
    UserProfile = apps.get_model("core", "UserProfile")
    UserProfile.objects.filter(theme_scheme="forest").update(theme_scheme="classic")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_add_general_system_choice"),
    ]

    operations = [
        migrations.RunPython(move_forest_profiles_to_classic, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="userprofile",
            name="theme_scheme",
            field=models.CharField(
                choices=[
                    ("classic", "Classic"),
                    ("ocean", "Ocean"),
                    ("plum", "Plum"),
                    ("contrast", "High contrast"),
                ],
                default="classic",
                max_length=24,
            ),
        ),
    ]
