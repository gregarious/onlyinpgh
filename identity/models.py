from django.db import models
from django.contrib.auth.models import User

class Identity(models.Model):
    class Meta:
        verbose_name_plural = 'identities'
    dt_created = models.DateTimeField(auto_now_add=True)

    # account is not required to have an identity on the site
    account = models.ManyToManyField(User,null=True,blank=True)
    avatar = models.ImageField(upload_to='avatars',blank=True,null=True)

    display_name = models.CharField(max_length=30)
    
    def __unicode__(self):
        return self.display_name

class Organization(models.Model):
    dt_created = models.DateTimeField(auto_now_add=True)
    identity = models.ForeignKey(Identity,unique=True)
    
    def __unicode__(self):
        return unicode(self.identity)

class Individual(models.Model):
    dt_created = models.DateTimeField(auto_now_add=True)
    identity = models.ForeignKey(Identity,unique=True)

    def __unicode__(self):
        return unicode(self.identity)