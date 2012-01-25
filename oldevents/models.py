from django.db import models
from django.contrib.auth.models import User
from pytz import timezone
from onlyinpgh.settings import TIME_ZONE

# the following a step towawrds a more appropriate model for the new Django version of the site. the current one
# needs to follow the current conventions, so individuals and organizations aren't related
# READ ALL COMMENTS WHEN WRITING FOR DJANGO BACKEND -- I PUT SOME USEFUL STUFF IN THERE
#
# Should there be some more logic for string-based fields that shouldn't be blank? blank=True does it on the validation side, but is that just in the admin panel?
#

'''
class Identity(models.Model):
	# each identity has a many-to-many relationship with Django auth.User accounts
	# only used for Django-friendly user authentication -- no profile info used here at all
	user = models.ManyToManyField(User,blank=True)
	dtcreated = models.DateTimeField('dt created',auto_now_add=True)
	display_name = models.CharField(max_length=200)	# often set by "subclass"
	email = models.EmailField()

class Individual(Identity):
	first_name = models.CharField(max_length=40)
	last_name = models.CharField(max_length=4)

# this wasn't made with much thought, feel free to start from scratch
class Organization(Identity):
	url = models.URLField(max_length=300,blank=True)
	description = models.TextField()
	location = models.ForeignKey(Location,blank=True,null=True)
	image_url = models.URLField(max_length=300,blank=True)
	fan_count = models.IntegerField()
'''

UTC = timezone('UTC')
LOCAL = timezone(TIME_ZONE)
def utctolocal(dt):
	return LOCAL.normalize(UTC.localize(dt).astimezone(LOCAL))

# work in progress
class Neighborhood(models.Model):
	name = models.CharField(max_length=200)
	description = models.TextField(blank=True)
	# probably more info in here, but we don't need this now
	def __unicode__(self):
		return self.name

# is this a static location or an "establishment"? hm.
# probably get rid of name and description
class Location(models.Model):
	name = models.CharField(max_length=200,blank=True)		# should mandate that either name or address is given
	dtcreated = models.DateTimeField('dt created',auto_now_add=True)
	# all the following fields can be blank, but shouldn't be. higher level validation should ensure this
	description = models.TextField(blank=True)
	# !! add a 2-char country code?
	country = models.CharField(max_length=2,blank=True)
	# !! change to 2 digit state code? If not because of internationalization concerns, at least mandate US states are 2 letter in higher level logic
	state = models.CharField(max_length=200,blank=True)

	town = models.CharField(max_length=50,blank=True)
	neighborhood = models.ForeignKey(Neighborhood,blank=True,null=True)
	
	postcode = models.CharField(max_length=10,blank=True)
	address = models.CharField('street address',max_length=200,blank=True)	# should mandate that either name or address is given
	# should always be between -90,90
	latitude = models.DecimalField(max_digits=9,decimal_places=6,blank=True,null=True)	
	# should always be between -180,180
	longitude = models.DecimalField(max_digits=9,decimal_places=6,blank=True,null=True)	

	'''
	Returns the most salient human-readable identifier for the address 
	(either it's name if provided, or its street address)
	'''
	primary_identifier = property(lambda self:self.name if self.name != '' else self.address)
	
	def __unicode__(self):
		return self.name

# Organization is a direct copy of the useful parts of wp_em_events
class Organization(models.Model):
	# when reindexing all the ids, remove this and let django use a regular default IntegerField
	id = models.BigIntegerField(primary_key=True)
	name = models.CharField(max_length=200)
	url = models.URLField(blank=True)
	location = models.ForeignKey(Location,blank=True,null=True)
	image_url = models.URLField(max_length=400,blank=True)
	fan_count = models.IntegerField(default=0)
	type = models.CharField(max_length=200)

	def __unicode__(self):
		return self.name

class Event(models.Model):
	name = models.CharField(max_length=200)
	description = models.TextField()

	dtcreated = models.DateTimeField('created datetime',auto_now_add=True)
	dtmodified = models.DateTimeField('modified datetime',auto_now=True)
	
	# all times are assumed to be UTC within models unless explicitly converted. 
	# cliff's notes on converting a Model's UTC dt:
	# >>> from pytz import timezone
	# >>> utc = timezone('utc'); est = timezone('US/Eastern')
	# >>> utc_dt = utc.localize(dt)							% change the tz-agnostic datetime into a utc datetime
	# >>> est_dt = est.normalize(utc_dt.astimezone(est))	% convert into the EST timezone
	# Note that just setting tzinfo to localize and using datetime.astimezone to convert isn't enough. the pytz 
	# 	normalize/localize methods are needed to ensure Daylight savings special cases are handled
	dtstart = models.DateTimeField('start datetime (UTC)')
	# dtend is the non-inclusive end date/time, meaning an event with dtend at 11pm actually only takes up time till 10:59pm
	# for all day events, this should be set to the next date (time irrelevant)
	# in a recurring event, dtend specifies FIRST occurrance end time, not end time of whole range
	dtend = models.DateTimeField('end datetime (UTC)')	
	allday = models.BooleanField('all day?',default=False)

	image_url = models.URLField(max_length=400,blank=True)
	url =  models.URLField(blank=True)
	location = models.ForeignKey(Location,blank=True,null=True)
	parent_event = models.ForeignKey('self',default=None,blank=True,null=True)

	@property
	def dtstart_local(self):
		return utctolocal(self.dtstart).replace(tzinfo=None)

	@property
	def dtend_local(self):
		return utctolocal(self.dtend).replace(tzinfo=None)

	def __unicode__(self):
		return self.name

class Role(models.Model):
	event = models.ForeignKey(Event)
	role_name = models.CharField(max_length=50)	# e.g. submitter, administrator, host, etc.
	organization = models.ForeignKey(Organization)

	def __unicode__(self):
		return self.role_name + ': ' + unicode(self.organization)
	#class Meta:
	#	unique_together = ('event','role_name','organization')

class Meta(models.Model):
	event = models.ForeignKey(Event)
	meta_key = models.CharField(max_length=200)
	meta_value = models.TextField()

	def __unicode__(self):
		return self.meta_key + ': ' + self.meta_value
	#class Meta:
	#	unique_together = ('event','meta_key','meta_value')

class Attendee(models.Model):
	individual = models.IntegerField()	# should be a foreign key to an Individual object, but just using WP ids for now
	event = models.ForeignKey(Event)
	#class Meta:
	#	unique_together = ('individual','event')

	# maybe want some kind of field for "commitment level" or something?