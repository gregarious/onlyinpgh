from django.db import models

from onlyinpgh.places.models import Place
from onlyinpgh.tagging.models import Tag
from onlyinpgh.identity.models import Identity, Organization

# Create your models here.
class Event(models.Model):
    class Meta:
        ordering = ['name']

    name = models.CharField(max_length=200)
    description = models.TextField()

    dtcreated = models.DateTimeField('created datetime (UTC)',auto_now_add=True)
    dtmodified = models.DateTimeField('modified datetime (UTC)',auto_now=True)
    
    # all times are assumed to be UTC within models unless explicitly converted. 
    # cliff's notes on converting a Model's UTC dt:
    # >>> from pytz import timezone
    # >>> utc = timezone('utc'); est = timezone('US/Eastern')
    # >>> utc_dt = utc.localize(dt)                         % change the tz-agnostic datetime into a utc datetime
    # >>> est_dt = est.normalize(utc_dt.astimezone(est))    % convert into the EST timezone
    # Note that just setting tzinfo to localize and using datetime.astimezone to convert isn't enough. the pytz 
    #   normalize/localize methods are needed to ensure Daylight savings special cases are handled
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

    tags = models.ManyToManyField(Tag,blank=True,null=True)

    # TODO: change these to template filters
    @property
    def dtstart_local(self):
        return utctolocal(self.dtstart).replace(tzinfo=None)

    @property
    def dtend_local(self):
        return utctolocal(self.dtend).replace(tzinfo=None)

    def __unicode__(self):
        return self.name

class Role(models.Model):
    ROLE_TYPES = (
        ('host','Host'),
        ('creator','Creator'),
    )

    role_name = models.CharField(max_length=50,choices=ROLE_TYPES)
    event = models.ForeignKey(Event)
    identity = models.ForeignKey(Identity)

    def __unicode__(self):
        return self.role_name + u':' + unicode(self.identity) + u'(%s)' % self.role_name

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

class ICalendarFeed(models.Model):
    timezone_choices = zip(pytz.all_timezones(),pytz.all_timezones())

    url = models.URLField(max_length=300)
    owner = models.ForeignKey(Organization,null=True,blank=True)
    xcal_name = models.CharField(max_length=100)

    default_timezone = models.CharField('fallback timezone for DATETIMEs in feed when none specified',
                                        max_length=50,choices=timezone_choices,default='US/Eastern')

class VEventRecord(models.Model):
    feed = models.ForeignKey('source iCalendar feed',ICalendarFeed)
    uid = models.CharField(max_length=255)
    time_last_modified = models.DateTimeField('last modification date in entry (in UTC)')
    event = models.ForeignKey(Event,null=True,blank=True)

### Bottom two models used for caching Facebook pages/events for future lookup
class FacebookEventRecord(models.Model):
    fb_id = models.BigIntegerField(primary_key=True)
    event_id = models.ForeignKey(Event,null=True,blank=True)

    time_last_updated = models.DateTimeField('time Facebook record was last updated')
    time_added = models.DateTimeField('time added in our records',auto_now_add=True)
    time_checked = models.DateTimeField('time last checked for updated',auto_now_add=True)

class FacebookPageRecord(models.Model):
    fb_id = models.BigIntegerField(primary_key=True)
    dt_added = models.DateTimeField(auto_now_add=True)
    dt_checked = models.DateTimeField(null=True)

    org_id = models.ForeignKey(Organization,null=True,blank=True)
    place_id = models.ForeignKey(Place,null=True,blank=True)
