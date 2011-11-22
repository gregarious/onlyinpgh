from django.db import models

from onlyinpgh.tagging.models import Tag

class Article(models.Model):
    title = models.CharField(max_length=50)
    short_description = models.TextField()

    source_name = models.CharField(max_length=100)
    source_url = models.URLField(max_length=400)
    dt_published = models.DateTimeField('datetime of source publication (UTC)')

    tags = models.ManyToManyField(Tag,blank=True,null=True)