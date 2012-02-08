from django.db import models
from django.contrib.contenttypes import generic

from onlyinpgh.identity.models import Organization
from onlyinpgh.tagging.models import TaggedItem

class Offer(models.Model):
    description = models.TextField()
    point_value = models.PositiveIntegerField()
    sponsor = models.ForeignKey(Organization)
    tags = generic.GenericRelation(TaggedItem)
