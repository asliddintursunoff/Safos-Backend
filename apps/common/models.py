from django.contrib.gis.db import models
from uuid import uuid4

class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    class Meta:
        abstract = True