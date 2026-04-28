from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_userprofile_theme_preferences"),
    ]

    operations = [
        migrations.AlterField(
            model_name="flashcard",
            name="species",
            field=models.CharField(
                blank=True,
                choices=[
                    ("general", "General"),
                    ("dog", "Dog"),
                    ("cat", "Cat"),
                    ("horse", "Horse"),
                    ("cow", "Cow"),
                    ("sheep", "Sheep"),
                    ("goat", "Goat"),
                    ("pig", "Pig"),
                    ("poultry", "Poultry"),
                    ("exotic", "Exotic"),
                    ("wildlife", "Wildlife"),
                ],
                max_length=40,
            ),
        ),
        migrations.AlterField(
            model_name="question",
            name="species",
            field=models.CharField(
                choices=[
                    ("general", "General"),
                    ("dog", "Dog"),
                    ("cat", "Cat"),
                    ("horse", "Horse"),
                    ("cow", "Cow"),
                    ("sheep", "Sheep"),
                    ("goat", "Goat"),
                    ("pig", "Pig"),
                    ("poultry", "Poultry"),
                    ("exotic", "Exotic"),
                    ("wildlife", "Wildlife"),
                ],
                max_length=40,
            ),
        ),
        migrations.AlterField(
            model_name="studyresource",
            name="species",
            field=models.CharField(
                blank=True,
                choices=[
                    ("general", "General"),
                    ("dog", "Dog"),
                    ("cat", "Cat"),
                    ("horse", "Horse"),
                    ("cow", "Cow"),
                    ("sheep", "Sheep"),
                    ("goat", "Goat"),
                    ("pig", "Pig"),
                    ("poultry", "Poultry"),
                    ("exotic", "Exotic"),
                    ("wildlife", "Wildlife"),
                ],
                max_length=40,
            ),
        ),
    ]
