# Generated by Django 3.0.7 on 2020-11-23 22:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('swickapp', '0011_auto_20201021_0921'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customer',
            name='stripe_cust_id',
            field=models.CharField(max_length=255),
        ),
    ]
