# Generated by Django 4.2.2 on 2023-07-21 16:22

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="FingerprintPool",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, db_index=True, null=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, db_index=True, null=True),
                ),
                ("source", models.JSONField(blank=True, null=True)),
                ("method", models.JSONField(blank=True, null=True)),
                ("init_kwargs", models.JSONField(blank=True, null=True)),
                (
                    "database_table",
                    models.CharField(blank=True, max_length=50, null=True),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Spacegroup",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, db_index=True, null=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, db_index=True, null=True),
                ),
                ("number", models.IntegerField(primary_key=True, serialize=False)),
                ("symbol", models.CharField(max_length=15)),
                ("crystal_system", models.CharField(max_length=15)),
                ("point_group", models.CharField(max_length=15)),
            ],
        ),
        migrations.CreateModel(
            name="Fingerprint",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, db_index=True, null=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, db_index=True, null=True),
                ),
                ("database_id", models.IntegerField(blank=True, null=True)),
                ("fingerprint", models.JSONField(blank=True, null=True)),
                (
                    "pool",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fingerprints",
                        to="core_components.fingerprintpool",
                    ),
                ),
            ],
        ),
    ]
