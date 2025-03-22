# Generated by Django 3.2.19 on 2025-02-11 08:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('movies', '0007_remove_show_theater'),
    ]

    operations = [
        migrations.AddField(
            model_name='show',
            name='theater',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='movies.theater'),
        ),
    ]
