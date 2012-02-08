from django.db import models
from django.contrib.contenttypes import generic

from onlyinpgh.tagging.models import TaggedItem

class Article(models.Model):
    class Meta:
        ordering = ['title']

    title = models.CharField(max_length=50)
    short_description = models.TextField()
    source_url = models.URLField(max_length=400)

    source_name = models.CharField(max_length=100)
    dt_published = models.DateTimeField('datetime of source publication (UTC)')

    tags = generic.GenericRelation(TaggedItem)