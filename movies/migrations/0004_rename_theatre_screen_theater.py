# Generated by Django 3.2.19 on 2025-02-11 06:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('movies', '0003_show'),
    ]

    operations = [
        migrations.RenameField(
            model_name='screen',
            old_name='theatre',
            new_name='theater',
        ),
    ]
