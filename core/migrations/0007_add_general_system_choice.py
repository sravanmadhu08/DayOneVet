from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_add_general_species_choice"),
    ]

    operations = [
        migrations.AlterField(
            model_name="flashcard",
            name="system",
            field=models.CharField(
                blank=True,
                choices=[
                    ("general", "General"),
                    ("respiratory", "Respiratory"),
                    ("neurology", "Neurology"),
                    ("cardiology", "Cardiology"),
                    ("gastrointestinal", "Gastrointestinal"),
                    ("musculoskeletal", "Musculoskeletal"),
                    ("reproductive", "Reproductive"),
                    ("urinary", "Urinary"),
                    ("dermatology", "Dermatology"),
                    ("ophthalmology", "Ophthalmology"),
                    ("endocrine", "Endocrine"),
                    ("infectious_disease", "Infectious disease"),
                    ("pharmacology", "Pharmacology"),
                    ("surgery", "Surgery"),
                    ("anaesthesia", "Anaesthesia"),
                    ("emergency_critical_care", "Emergency and critical care"),
                    ("public_health", "Public health"),
                ],
                max_length=60,
            ),
        ),
        migrations.AlterField(
            model_name="question",
            name="system",
            field=models.CharField(
                choices=[
                    ("general", "General"),
                    ("respiratory", "Respiratory"),
                    ("neurology", "Neurology"),
                    ("cardiology", "Cardiology"),
                    ("gastrointestinal", "Gastrointestinal"),
                    ("musculoskeletal", "Musculoskeletal"),
                    ("reproductive", "Reproductive"),
                    ("urinary", "Urinary"),
                    ("dermatology", "Dermatology"),
                    ("ophthalmology", "Ophthalmology"),
                    ("endocrine", "Endocrine"),
                    ("infectious_disease", "Infectious disease"),
                    ("pharmacology", "Pharmacology"),
                    ("surgery", "Surgery"),
                    ("anaesthesia", "Anaesthesia"),
                    ("emergency_critical_care", "Emergency and critical care"),
                    ("public_health", "Public health"),
                ],
                max_length=60,
            ),
        ),
        migrations.AlterField(
            model_name="studyresource",
            name="system",
            field=models.CharField(
                blank=True,
                choices=[
                    ("general", "General"),
                    ("respiratory", "Respiratory"),
                    ("neurology", "Neurology"),
                    ("cardiology", "Cardiology"),
                    ("gastrointestinal", "Gastrointestinal"),
                    ("musculoskeletal", "Musculoskeletal"),
                    ("reproductive", "Reproductive"),
                    ("urinary", "Urinary"),
                    ("dermatology", "Dermatology"),
                    ("ophthalmology", "Ophthalmology"),
                    ("endocrine", "Endocrine"),
                    ("infectious_disease", "Infectious disease"),
                    ("pharmacology", "Pharmacology"),
                    ("surgery", "Surgery"),
                    ("anaesthesia", "Anaesthesia"),
                    ("emergency_critical_care", "Emergency and critical care"),
                    ("public_health", "Public health"),
                ],
                max_length=60,
            ),
        ),
    ]
