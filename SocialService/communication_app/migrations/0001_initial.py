# Generated by Django 3.2.11 on 2022-06-07 02:16

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Channel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(auto_now_add=True, db_column='created_on')),
                ('updated_on', models.DateTimeField(auto_now=True, db_column='updated_on')),
                ('deleted_on', models.DateTimeField(db_column='deleted_on', default=None, null=True)),
                ('name', models.CharField(max_length=1000, unique=True)),
                ('is_under_moderation', models.BooleanField(default=True)),
                ('nickname', models.CharField(default='a new channel for chat', max_length=100, null=True)),
                ('admins', models.ManyToManyField(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-updated_on', '-created_on'),
                'get_latest_by': 'updated_on',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(auto_now_add=True, db_column='created_on')),
                ('updated_on', models.DateTimeField(auto_now=True, db_column='updated_on')),
                ('deleted_on', models.DateTimeField(db_column='deleted_on', default=None, null=True)),
                ('channel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subscriptions', to='communication_app.channel')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subscriptions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-updated_on', '-created_on'),
                'get_latest_by': 'updated_on',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='GameRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(auto_now_add=True, db_column='created_on')),
                ('updated_on', models.DateTimeField(auto_now=True, db_column='updated_on')),
                ('deleted_on', models.DateTimeField(db_column='deleted_on', default=None, null=True)),
                ('is_accepted', models.BooleanField(default=False)),
                ('type', models.IntegerField(choices=[(1, 'Friend Request'), (2, 'Message Request')], default=1)),
                ('channel', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='communication_app.channel')),
                ('receiver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='requests_received', to=settings.AUTH_USER_MODEL)),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='requests_sent', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-updated_on', '-created_on'),
                'get_latest_by': 'updated_on',
                'abstract': False,
            },
        ),
    ]
