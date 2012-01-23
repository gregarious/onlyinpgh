'''
Models mostly needed for bookkeeping reasons to relate external
references to our objects.
'''

from django.db import models
from onlyinpgh.identity.models import Organization
from onlyinpgh.places.models import Place
from onlyinpgh.events.models import Event, Role

import pytz

## custom ExternalPlaceSource managers to make it simpler to query a particular service's ids
class FBPlaceManager(models.Manager):
    def get_query_set(self):
        return super(FBPlaceManager, self).get_query_set().filter(service='fb')

class FactualPlaceManager(models.Manager):
    def get_query_set(self):
        return super(FactualPlaceManager, self).get_query_set().filter(service='fact')

class ExternalPlaceSource(models.Model):
    '''
    Model used to relate external API IDs to unique objects in our
    database (e.g. Factual GUIDs an onlyinpgh.places.models.Place)
    '''
    class Meta:
        unique_together = (('service','uid'),)

    service_choices = [('fb',   'Facebook Object ID'),
                       ('fact', 'Factual GUID')]

    service = models.CharField(max_length=8,choices=service_choices)
    uid = models.CharField('string representation of UID',max_length=36)
    place = models.OneToOneField(Place)

    last_checked = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()
    facebook = FBPlaceManager()
    factual = FactualPlaceManager()
    def __unicode__(self):
        return '%s:%s -> %s' % (self.service,self.uid,self.place)

class FacebookPage(models.Model):
    '''
    Simple model to store all FB ids encountered.
    '''
    fb_id = models.BigIntegerField(primary_key=True)
    ignore = models.BooleanField('always ignore this page',default=False)    
    pageinfo_json = models.TextField(blank=True)

class FacebookEventRecord(models.Model):
    '''
    Model that records links between Facebook events and internal Events.
    '''
    fb_id = models.BigIntegerField(primary_key=True)
    event = models.ForeignKey(Event)

    time_added = models.DateTimeField('time added in our records',auto_now_add=True)
    last_checked = models.DateTimeField('time last checked for updated',auto_now_add=True)
    
    last_updated = models.DateTimeField('time Facebook record was last updated')
    ignore = models.BooleanField('always ignore this event',default=False)    

class FacebookOrgRecord(models.Model):
    '''
    Model that records links between Facebook identities and internal 
    Organizations.
    '''
    fb_id = models.BigIntegerField(primary_key=True)
    time_added = models.DateTimeField(auto_now_add=True)
    last_checked = models.DateTimeField(auto_now_add=True)

    organization = models.ForeignKey(Organization,related_name="%(app_label)s_%(class)s_related")
    ignore = models.BooleanField('always ignore this page',default=False)

class ICalendarFeed(models.Model):
    url = models.URLField(max_length=300)
    owner = models.ForeignKey(Organization,null=True,blank=True)
    name = models.CharField(max_length=100,blank=True)
    event_role_type = models.CharField(max_length=50,choices=Role.ROLE_TYPES)

    def __unicode__(self):
        return self.name

class VEventRecord(models.Model):
    feed = models.ForeignKey(ICalendarFeed)
    uid = models.CharField(max_length=255)
    dtmodified = models.DateTimeField('last modification date in entry (in UTC)')
    event = models.ForeignKey(Event)

    def __unicode__(self):
        return self.uid

