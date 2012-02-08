from django.db import models
from django.contrib.contenttypes import generic

from onlyinpgh.identity.models import Identity
from onlyinpgh.tagging.models import TaggedItem

from datetime import datetime

class Post(models.Model):
    class Meta:
        ordering = ['title']

    # might turn earch post type into an implementation of a Post ABC, we'll see
    POST_TYPES = (
        ('photo','Photo'),
        ('conversation','Conversation'),
        ('question','Question'),
    )
    dt = models.DateTimeField('post datetime (UTC)',default=datetime.utcnow())

    post_type = models.CharField('type (e.g. photo, question, etc.)',
                                    max_length=30,choices=POST_TYPES)

    title = models.CharField(max_length=40,blank=True)
    author = models.ForeignKey(Identity)
    
    content = models.TextField()
    # TODO: probably turn this into an ImageField -- just simple url for now
    image_url = models.URLField(max_length=400,blank=True)

    tags = generic.GenericRelation(TaggedItem)

    def __unicode__(self):
        return u'#%s type:%s' % (unicode(self.id),self.post_type)

class Comment(models.Model):
    post = models.ForeignKey(Post)
    dt = models.DateTimeField('comment datetime (UTC)',default=datetime.utcnow())

    commenter = models.ForeignKey(Identity)
    content = models.TextField()

    def __unicode__(self):
        return u'#%s post:%s' % (unicode(self.id),unicode(self.post))

# TODO: ChatterPost manager that returnes "newest", "hottest", etc.