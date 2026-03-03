from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mih', '0006_remove_patientnonclinicalinfos_accept_tcl_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='image',
            name='content_type',
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.AddField(
            model_name='image',
            name='object_name',
            field=models.CharField(blank=True, db_index=True, max_length=512, null=True),
        ),
        migrations.RemoveField(
            model_name='image',
            name='file',
        ),
    ]
