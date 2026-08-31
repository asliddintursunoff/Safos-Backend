from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, blank=True, default=timezone.now, null=True
            ),
            preserve_default=False,
        ),
    ]
