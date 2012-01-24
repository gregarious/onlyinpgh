from django.db import models

from onlyinpgh.identity.models import Organization
from onlyinpgh.tagging.models import Tag

class Offer(models.Model):
    description = models.TextField()
    point_value = models.PositiveIntegerField()
    sponsor = models.ForeignKey(Organization)
    tags = models.ManyToManyField(Tag,blank=True,null=True)