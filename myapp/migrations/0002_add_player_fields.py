from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('myapp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='player',
            name='device_order',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='player',
            name='has_viewed_role',
            field=models.BooleanField(default=False),
        ),
    ] 