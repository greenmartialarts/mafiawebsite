# Generated by Django 5.1.3 on 2024-11-27 18:27

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Player',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('session_key', models.CharField(max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('device_order', models.IntegerField(default=0)),
                ('has_viewed_role', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='BugReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('steps_to_reproduce', models.TextField(blank=True)),
                ('priority', models.CharField(choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High'), ('CRITICAL', 'Critical')], default='MEDIUM', max_length=10)),
                ('status', models.CharField(choices=[('NEW', 'New'), ('IN_PROGRESS', 'In Progress'), ('RESOLVED', 'Resolved'), ('CLOSED', 'Closed')], default='NEW', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('admin_notes', models.TextField(blank=True)),
                ('reporter', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reported_bugs', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Room',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('room_name', models.CharField(max_length=100)),
                ('room_code', models.CharField(max_length=6, unique=True)),
                ('mafia_count', models.IntegerField(default=1)),
                ('doctor_count', models.IntegerField(default=1)),
                ('cop_count', models.IntegerField(default=1)),
                ('special_role_assigned', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('players_ready', models.IntegerField(default=0)),
                ('all_ready_at', models.DateTimeField(blank=True, null=True)),
                ('password', models.CharField(blank=True, max_length=128, null=True)),
                ('banned_users', models.ManyToManyField(blank=True, related_name='banned_from_rooms', to=settings.AUTH_USER_MODEL)),
                ('host', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='hosted_rooms', to=settings.AUTH_USER_MODEL)),
                ('players', models.ManyToManyField(related_name='joined_rooms', to=settings.AUTH_USER_MODEL)),
                ('temp_players', models.ManyToManyField(related_name='joined_rooms', to='myapp.player')),
            ],
        ),
        migrations.CreateModel(
            name='RoleAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('MAFIA', 'Mafia'), ('DOCTOR', 'Doctor'), ('COP', 'Cop'), ('VILLAGER', 'Villager')], max_length=10)),
                ('assigned_at', models.DateTimeField(auto_now_add=True)),
                ('temp_player', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='myapp.player')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('room', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='myapp.room')),
            ],
            options={
                'unique_together': {('temp_player', 'room'), ('user', 'room')},
            },
        ),
    ]