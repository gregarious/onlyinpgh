from django.db import models

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

# TOOD: some sort of easy tag creation funcion? maybe part of a mgr?

class Tag(models.Model):
    name = models.SlugField()

class TaggedItem(models.Model):
    tag = models.ForeignKey(Tag)
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    def __unicode__(self):
        return self.tag