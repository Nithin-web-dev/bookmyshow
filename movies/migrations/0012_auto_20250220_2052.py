# Generated by Django 3.2.19 on 2025-02-20 15:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('movies', '0011_auto_20250220_2035'),
    ]

    operations = [
        migrations.AlterField(
            model_name='movie',
            name='name',
            field=models.CharField(max_length=255, unique=True),
        ),
        migrations.AlterUniqueTogether(
            name='seat',
            unique_together={('theater', 'seat_number')},
        ),
        migrations.AlterUniqueTogether(
            name='show',
            unique_together={('movie', 'theater', 'date', 'time')},
        ),
        migrations.AlterUniqueTogether(
            name='theater',
            unique_together={('name', 'movie', 'time')},
        ),
    ]
