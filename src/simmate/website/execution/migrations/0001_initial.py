# Generated by Django 3.1.1 on 2021-01-15 03:21

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='WorkItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fxn', models.BinaryField()),
                ('args', models.BinaryField(default=b'\x80\x04]\x94.')),
                ('kwargs', models.BinaryField(default=b'\x80\x04}\x94.')),
                ('result', models.BinaryField(blank=True, null=True)),
                ('status', models.CharField(choices=[('P', 'Pending'), ('R', 'Running'), ('C', 'Cancelled'), ('F', 'Finished')], default='P', max_length=1)),
            ],
        ),
    ]
