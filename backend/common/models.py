"""Modèles abstraits partagés par toutes les applications."""

import uuid

from django.db import models


class BaseModel(models.Model):
    """Identifiant UUID non énumérable et horodatage automatique."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
