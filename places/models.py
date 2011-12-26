from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, MinLengthValidator
from django.core.exceptions import ValidationError

from onlyinpgh.tagging.models import Tag
from onlyinpgh.identity.models import Organization

# TODO: largely a placeholder, flesh out more later
class Neighborhood(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    def __unicode__(self):
        return self.name

class Location(models.Model):
    '''
    Handles specific information about where a physical place is located. Should
    rarely be exposed without a Place wrapping it on the front end.
    '''
    class Meta:
        ordering = ['address','latitude']

    # TODO: probably take out defaults for town and state, definitely country
    # 2-char country code (see http://en.wikipedia.org/wiki/ISO_3166-1)
    country = models.CharField(max_length=2,blank=True,
                                validators=[MinLengthValidator(2)],
                                default='US')

    # should only include 2-letter codes (US states and CA provinces obey this)
    state = models.CharField(max_length=2,blank=True,
                                validators=[MinLengthValidator(2)])

    town = models.CharField(max_length=60,blank=True)
    neighborhood = models.ForeignKey(Neighborhood,blank=True,null=True)
    
    postcode = models.CharField(max_length=10,blank=True)
    address = models.TextField('street address (or premise)',blank=True)

    # should always be between -90,90
    latitude = models.DecimalField(    max_digits=9,decimal_places=6,
                                    blank=True,null=True,
                                    validators=[MinValueValidator(-90),
                                                MaxValueValidator(90)])
    # should always be between -180,180
    longitude = models.DecimalField(max_digits=9,decimal_places=6,
                                    blank=True,null=True,
                                    validators=[MinValueValidator(-180),
                                                MaxValueValidator(180)])

    def _normalize_address(self):
        '''
        Replaces the current contents of the address field with a normalized
        version of it (e.g. '201 S. Bouquet Street' -> '201 S Bouquet St').

        Currently uses Google Geocoding API's formatted_address field in 
        development, though this should change.
        '''
        # TODO: revisit address normalization api
        pass
    
    def _complete_missing_fields(self):
        '''
        Refers to an authoritative source to complete missing fields. 
        
        Currently uses Google Geocoding API, but will hopefully move to 
        Factual Resolve API.
        '''
        # TODO: revisit missing location info api
        pass

    def save(self,*args,**kwargs):
        self.full_clean()        # run field validators
        # ensure country and state are saved in db in uppercase
        if self.country:
            self.country = self.country.upper()
        if self.state:
            self.state = self.state.upper()
        return super(Location,self).save(*args,**kwargs)

    def clean(self,*args,**kwargs):
        # ensure latitude and longitude exist in pairs
        if self.latitude is not None and self.longitude is None or \
            self.longitude is not None and self.latitude is None:
            raise ValidationError('If geocoding information is available, buth longitude and latitude must be specified')
        return super(Location,self).clean(*args,**kwargs)

    def __unicode__(self):
        addr_s = self.address if self.address else ''
        lat_s = '%.3f' % self.latitude if self.latitude is not None else '-'
        lon_s = '%.3f' % self.longitude if self.longitude is not None else '-'
        return u'%s (%s,%s)' % (addr_s,lat_s,lon_s)

class Place(models.Model):
    '''
    Handles information about places.
    '''
    class Meta:
        unique_together = ('name','location')
        ordering = ['name']

    dtcreated = models.DateTimeField('dt created',auto_now_add=True)
    
    name = models.CharField(max_length=200,blank=True)
    description = models.TextField(blank=True)
    location = models.ForeignKey(Location,blank=True,null=True)

    owner = models.ForeignKey(Organization,blank=True,null=True)
    tags = models.ManyToManyField(Tag,blank=True,null=True)

    def __unicode__(self):
        s = self.name
        if self.location:
            s += '. Loc: ' + self.location.address + ', ' + self.location.town  + ', ' + self.location.state + ', ' + self.location.postcode  
        return unicode(s)

class PlaceMeta(models.Model):
    '''
    Handles meta information for a Place.
    '''
    key_choices = ( ('url','Website'),
                    ('phone','Phone number'),
                    ('hours','Hours'),
                    ('image_url','Image URL')
                  )

    place = models.ForeignKey(Place)
    meta_key = models.CharField(max_length=20,choices=key_choices)
    meta_value = models.TextField(blank=True)   # blank values allowed (boolean meta attributes)

    def __unicode__(self):
        if len(self.meta_value) < 20:
            val = self.meta_value
        else:
            val = self.meta_value[:16] + '...'
        return u'%s: %s' % (self.meta_key,val)

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

class FacebookPageRecord(models.Model):
    fb_id = models.BigIntegerField(primary_key=True)
    time_added = models.DateTimeField(auto_now_add=True)
    last_checked = models.DateTimeField(auto_now_add=True)
    place = models.ForeignKey(Place,null=True,blank=True,related_name="%(app_label)s_%(class)s_related")

class LocationLookupNotice(models.Model):
    '''
    Records information about a questionable lookup result from an external API
    '''
    # this should be in sync with external.API_NOTICE_TYPES 
    NOTICE_TYPES = (
        ('PartialMatch',            'Partial Match'),
        ('MultipleResults',         'Multiple Results Returned'),
        ('NoStreetAddress',         'No Street Address'),
        ('NonConcreteAddress',      'Non-concrete Address'),
        ('PreprocessingOccurred',   'Request Preprocessing Occured'),
        ('LookupFailure',           'API Lookup Failure')
    )
    SERVICE_TYPES = (
        ('GoogleGeocode','Google Geocoding API'),
    )

    dtlookup = models.DateTimeField('tiemstamp of lookup (in UTC)')
    service = models.CharField(max_length=50, choices=SERVICE_TYPES)

    notice_type = models.CharField(max_length=50, choices=NOTICE_TYPES)
    raw_request = models.TextField()
    cleaned_request = models.TextField()
    api_call = models.TextField()
    response_json = models.TextField() # does not include any post-processing

    # Location entry lookup resulted in (if applicable)
    location = models.ForeignKey(Location,null=True,blank=True,default=None)

    def __unicode__(self):
        loc_label = unicode(self.location) if self.location else u'[no location]'
        return u'%s: %s' % (loc_label,self.notice_type)
