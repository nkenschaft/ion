# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-03-30 19:54
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('printing', '0004_auto_20151218_1346')]

    operations = [migrations.AlterField(
        model_name='printjob',
        name='file',
        field=models.FileField(upload_to='printing/'),
    )]
