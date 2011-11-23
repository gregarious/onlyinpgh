from django.db import models
from onlyinpgh.places.models import Place
from onlyinpgh.events.models import Event
from onlyinpgh.identity.models import Identity

# TODO: probably do some generic model type stuff here
class PlaceCheckin(models.Model):
    place = models.ForeignKey(Place)
    identity = models.ForeignKey(Identity)
    
    def __unicode__(self):
        return u'%s@%s' % (unicode(identity),unicode(place))

class EventCheckin(models.Model):
    event = models.ForeignKey(Event)
    identity = models.ForeignKey(Identity)

    def __unicode__(self):
        return u'%s@%s' % (unicode(identity),unicode(place))