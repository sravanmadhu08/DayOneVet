from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_userprofile"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="theme_mode",
            field=models.CharField(
                choices=[("light", "Light"), ("dark", "Dark")],
                default="light",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="theme_scheme",
            field=models.CharField(
                choices=[
                    ("classic", "Classic"),
                    ("forest", "Forest"),
                    ("ocean", "Ocean"),
                    ("plum", "Plum"),
                    ("contrast", "High contrast"),
                ],
                default="classic",
                max_length=30,
            ),
        ),
    ]
