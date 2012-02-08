from django.db import models
from django.contrib.contenttypes import generic

from django.core.validators import MinValueValidator, MaxValueValidator, MinLengthValidator
from django.core.exceptions import ValidationError

from math import sqrt, pow

from onlyinpgh.identity.models import Organization
from onlyinpgh.tagging.models import TaggedItem

# TODO: largely a placeholder, flesh out more later
class Neighborhood(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    def __unicode__(self):
        return self.name

def _calc_distance(p0,p1):
    return sqrt(pow(p1[0]-p0[0],2),
                pow(p1[1]-p0[1],2))

class CloseLocationManager(models.Manager):
    def get_close(self,**kwargs):
        '''
        Runs a get query that allows some leeway on exact matching of 
        the geocoding data. Assuming any results are close (within some
        error tolerance), the closest one to the input will be returned.

        In addition to normal arguments, a dict of options with the
        keyword name '_close_options' can be passed in with the following
        keys:
        - lat_error (+/- bounds put on latitude [default: .001])
        - lng_error (+/- bounds put on longitude [default: .001])
        - assert_single_match (raise an error if more than one result 
            matches the full query with bounding criteria [default: False])
        '''
        assert kwargs, 'get_close() only support keyword arguments'

        close_options = kwargs.pop('_close_options',{})
        lat_error = close_options.get('lat_error',1e-3)
        lng_error = close_options.get('lng_error',1e-3)
        assert_single_match = close_options.get('assert_single_match',False)

        # remove the equality constraints and add a pair of bounding ones
        lat = kwargs.get('latitude')
        if lat is not None:
            kwargs.pop('latitude')
            kwargs['latitude__lt'] = lat + lat_error
            kwargs['latitude__gt'] = lat - lat_error
        lng = kwargs.get('longitude')
        if lng is not None:
            kwargs['longitude__lt'] = lng + lng_error
            kwargs['longitude__gt'] = lng - lng_error
        
        # if we can only have one match (or no geocoding in query anyway), just run regular get
        if assert_single_match or (lng is None and lat is None):
            return self.get(**kwargs)
        
        # otherwise, we need to run filter with the relaxed constraints and then find the closest result among them
        results = self.filter(**kwargs)
        if len(results) == 0:
            raise Location.DoesNotExist("Location matching 'close query' does not exist")
        elif len(results) == 1:
            return results[0]
        else:
            calc_distance = lambda p0,p1: sqrt(pow(float(p1[0])-float(p0[0]),2) +
                                                pow(float(p1[1])-float(p0[1]),2))
            if lat is None: lat = 0
            if lng is None: lng = 0
            anchor = (lat,lng)
            best, best_dist = None, float('inf')
            for r in results:
                point = (r.latitude or 0, r.longitude or 0)
                dist = calc_distance(anchor,point)
                if dist < best_dist:
                    best, best_dist = r, dist
            return best
    
    def get_close_or_create(self,**kwargs):
        '''
        Runs get_or_create query with some leeway on matching geocoding
        criteria for the get attempt.

        Note: be careful on using this function with address-less
        locations that just feature geocoding. Doing so will encourage all
        address-less locations to converge to focus points (the first 
        one created).

        Accepts same _close_options as get_close() -- see that method's 
        docstring for more details.

        Note, this involves one extra query than a normal get_or_create
        when the get_close fails because I didn't want to muck around 
        in duplicating the intricaies of Django's own get_or_create.
        '''
        try:
            return self.get_close(**kwargs), False
        except Location.DoesNotExist:
            kwargs.pop('_close_options', {})
            return self.get_or_create(**kwargs)
        

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

    objects = models.Manager()
    close_manager = CloseLocationManager()
    
    def save(self,*args,**kwargs):
        self.full_clean()        # run field validators
        # ensure country and state are saved in db in uppercase
        if self.country:
            self.country = self.country.upper()
        if self.state:
            self.state = self.state.upper()
        # TODO: normalize?
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
    
    @property
    def full_string(self):
        s = ''
        if self.address:
            s += '%s, ' % self.address
        if self.town:
            s += '%s, ' % self.town
        
        if self.state and self.postcode:
            s += '%s %s, ' % (self.state, self.postcode)
        elif self.state:
            s += '%s, ' % self.state
        elif self.postcode:
            s += '%s, ' % self.postcode
        
        if self.latitude or self.longitude:
            s += '(%s,%s)' % ('%.3f'%self.latitude if self.latitude else '-',
                              '%.3f'%self.longitude if self.latitude else '-')

        return s.rstrip(', ')

class Place(models.Model):
    '''
    Handles information about places.
    '''
    class Meta:
        ordering = ['name']

    dtcreated = models.DateTimeField('dt created',auto_now_add=True)
    
    name = models.CharField(max_length=200,blank=True)
    description = models.TextField(blank=True)
    location = models.ForeignKey(Location,blank=True,null=True)

    owner = models.ForeignKey(Organization,blank=True,null=True)
    tags = generic.GenericRelation(TaggedItem)

    def __unicode__(self):
        s = self.name
        if self.location:
            s += u'. Loc: ' + self.location.address + u', ' + self.location.town  + u', ' + self.location.state + u', ' + self.location.postcode  
        assert type(s==unicode)
        return s

class Meta(models.Model):
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
