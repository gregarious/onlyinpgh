from django.db import models
from django.contrib.auth.models import User

class Identity(models.Model):
    # account is not required to have an identity on the site
    account = models.ManyToManyField(User,null=True,blank=True)
    avatar = models.ImageField(upload_to='avatars')

    display_name = models.CharField(max_length=30)
    
    def __unicode__(self):
        return self.display_name

class Organization(models.Model):
    identity = models.ForeignKey(Identity,unique=True,blank=True,null=True)

class Individual(models.Model):
    identity = models.ForeignKey(Identity,unique=True)