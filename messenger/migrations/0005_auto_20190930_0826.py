# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2019-09-30 08:26
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('messenger', '0004_auto_20190925_0729'),
    ]

    operations = [
        migrations.AlterField(
            model_name='messageattachment',
            name='deleted_time',
            field=models.DateTimeField(blank=True, editable=False, null=True, verbose_name='deleted time'),
        ),
        migrations.AlterField(
            model_name='messagebody',
            name='deleted_time',
            field=models.DateTimeField(blank=True, editable=False, null=True, verbose_name='deleted time'),
        ),
    ]