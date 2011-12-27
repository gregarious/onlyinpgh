'''
Models mostly needed for bookkeeping reasons to relate external
references to our objects.
'''

from django.db import models
from onlyinpgh.identity.models import Organization
from onlyinpgh.places.models import Place
from onlyinpgh.events.models import Event

class FacebookOrgRecord(models.Model):
    '''
    Model that records links between Facebook identities and 
    internal Organizations.
    '''
    page_fbid = models.BigIntegerField(primary_key=True)
    time_added = models.DateTimeField(auto_now_add=True)
    last_checked = models.DateTimeField(auto_now_add=True)

    organization = models.ForeignKey(Organization,related_name="%(app_label)s_%(class)s_related")
    ignore = models.BooleanField('always ignore this page',default=False)

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

    def __unicode__(self):
        return '%s:%s -> %s' % (self.service,self.uid,self.place)

