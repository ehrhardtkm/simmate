# Generated by Django 3.1.1 on 2021-01-15 03:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Pathway',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('element', models.CharField(max_length=2)),
                ('dpf_index', models.IntegerField()),
                ('distance', models.FloatField()),
                ('isite', models.CharField(max_length=100)),
                ('msite', models.CharField(max_length=100)),
                ('esite', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='Structure',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pretty_formula', models.CharField(max_length=25)),
                ('nsites', models.IntegerField()),
                ('density', models.FloatField()),
                ('structure', models.TextField()),
                ('material_id', models.CharField(max_length=12)),
                ('final_energy', models.FloatField(blank=True, null=True)),
                ('final_energy_per_atom', models.FloatField(blank=True, null=True)),
                ('formation_energy_per_atom', models.FloatField(blank=True, null=True)),
                ('e_above_hull', models.FloatField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='DimensionalityLarsen',
            fields=[
                ('status', models.CharField(choices=[('S', 'Scheduled'), ('C', 'Completed'), ('F', 'Failed')], default='S', max_length=1)),
                ('pathway', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='diffusion.pathway')),
                ('dimensionality', models.IntegerField()),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='RelativeDistanceVsDmin',
            fields=[
                ('status', models.CharField(choices=[('S', 'Scheduled'), ('C', 'Completed'), ('F', 'Failed')], default='S', max_length=1)),
                ('pathway', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='diffusion.pathway')),
                ('distance_rel_min', models.FloatField(blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='pathway',
            name='structure',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pathways', to='diffusion.structure'),
        ),
    ]
