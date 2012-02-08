from django.db import models
from django.contrib.contenttypes import generic

import pytz

from onlyinpgh.places.models import Place
from onlyinpgh.identity.models import Identity, Organization
from onlyinpgh.tagging.models import TaggedItem

from onlyinpgh.utils.time import utctolocal
from onlyinpgh.settings import TIME_ZONE

# Create your models here.
class Event(models.Model):
    class Meta:
        ordering = ['name']

    name = models.CharField(max_length=200)
    description = models.TextField()

    dtcreated = models.DateTimeField('created datetime (UTC)',auto_now_add=True)
    dtmodified = models.DateTimeField('modified datetime (UTC)',auto_now=True)
    
    # all times are assumed to be UTC within models unless explicitly converted. 
    dtstart = models.DateTimeField('start datetime (UTC)')
    # dtend is the non-inclusive end date/time, meaning an event with dtend at 11pm actually only takes up time till 10:59pm
    # for all day events, this should be set to the next date (time irrelevant)
    # in a recurring event, dtend specifies FIRST occurrance end time, not end time of whole range
    dtend = models.DateTimeField('end datetime (UTC)')  
    allday = models.BooleanField('all day?',default=False)

    # recurrance rules (simple text, same format as iCalendar spec)
    rrule = models.TextField(blank=True)
    rdate = models.TextField(blank=True)
    exrule = models.TextField(blank=True)
    exdate = models.TextField(blank=True)

    # might turn this into a locally-hosted image instead of relying on hotlinking, we'll see
    image_url = models.URLField(max_length=400,blank=True)

    url =  models.URLField(blank=True)
    place = models.ForeignKey(Place,blank=True,null=True)
    parent_event = models.ForeignKey('self',default=None,blank=True,null=True)

    # make the event "invisible", meaning it won't be displayable, searchable, etc.
    invisible = models.BooleanField(default=False)

    tags = generic.GenericRelation(TaggedItem)

    # TODO: change these to template filters
    @property
    def dtstart_local(self):
        return utctolocal(self.dtstart,TIME_ZONE,return_naive=True)

    @property
    def dtend_local(self):
        return utctolocal(self.dtend,TIME_ZONE,return_naive=True)

    def __unicode__(self):
        return self.name

## custom Role managers to make it simpler to query a particular type of Role
class HostRoleManager(models.Manager):
    def get_query_set(self):
        return super(HostRoleManager, self).get_query_set().filter(role_type='host')

class ReferrerRoleManager(models.Manager):
    def get_query_set(self):
        return super(HostRoleManager, self).get_query_set().filter(role_type='referrer')

class Role(models.Model):
    ROLE_TYPES = (
        ('host','Host'),
        ('referer','Referer'),
    )

    role_type = models.CharField(max_length=50,choices=ROLE_TYPES)
    event = models.ForeignKey(Event)
    organization = models.ForeignKey(Organization)

    objects = models.Manager()
    hosts = HostRoleManager()
    referrers = ReferrerRoleManager()

    def __unicode__(self):
        return self.role_type + u':' + unicode(self.organization) + u'(%s)' % self.role_type

class Meta(models.Model):
    event = models.ForeignKey(Event)
    meta_key = models.CharField(max_length=200)
    meta_value = models.TextField()

    def __unicode__(self):
        return self.meta_key + ':' + self.meta_value

class Attendee(models.Model):
    identity = models.ForeignKey(Identity)
    event = models.ForeignKey(Event)
    # maybe some commitment level or something?

    def __unicode__(self):
        return unicode(self.individual) + u'@' + unicode(self.event)
