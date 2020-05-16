# Generated by Django 3.0.6 on 2020-05-16 00:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('swickapp', '0016_auto_20200515_1957'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='chef',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='chef', to='swickapp.Server'),
        ),
        migrations.AlterField(
            model_name='order',
            name='customer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='swickapp.Customer'),
        ),
        migrations.AlterField(
            model_name='order',
            name='server',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='server', to='swickapp.Server'),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='meal',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='swickapp.Meal'),
        ),
        migrations.AlterField(
            model_name='server',
            name='restaurant',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='swickapp.Restaurant'),
        ),
    ]
