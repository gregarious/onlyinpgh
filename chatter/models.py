from django.db import models
from onlyinpgh.identity.models import Identity
from onlyinpgh.tagging.models import Tag

class Post(models.Model):
    # might turn earch post type into an implementation of a Post ABC, we'll see
    POST_TYPES = (
        ('photo','Photo'),
        ('conversation','Conversation'),
        ('question','Question'),
    )

    dt = models.DateTimeField('post datetime (UTC)')
    post_type = models.CharField('type (e.g. photo, question, etc.)',
                                    max_length=30,choices=POST_TYPES)
    author = models.ForeignKey(Identity)
    
    content = models.TextField()
    # TODO: probably turn this into an ImageField -- just simple url for now
    image_url = models.URLField(max_length=400,blank=True)

    tags = models.ManyToManyField(Tag,blank=True,null=True)

    def __unicode__(self):
        return u'#%s type:%s' % (unicode(self.id),self.post_type)

class Comment(models.Model):
    post = models.ForeignKey(Post)
    dt = models.DateTimeField('post datetime (UTC)')

    identity = models.ForeignKey(Identity)
    content = models.TextField()

    def __unicode__(self):
        return u'#%s post:%s' % (unicode(self.id),unicode(self.post))

# TODO: ChatterPost manager that returnes "newest", "hottest", etc.