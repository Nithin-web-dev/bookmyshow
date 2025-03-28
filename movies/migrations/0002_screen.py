# Generated by Django 3.2.19 on 2025-02-09 13:15

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('movies', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Screen',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('theatre', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='screens', to='movies.theater')),
            ],
        ),
    ]
