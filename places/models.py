from django.db import models

# TODO: largely a placeholder, flesh out more later
class Neighborhood(models.Model):
	name = models.CharField(max_length=100)
	description = models.TextField(blank=True)

	def __unicode__(self):
		return self.name

class Location(models.Model):
	'''
	Handles specific information about where a physical place is located.
	
	A location must include either a longitude/latitude pair or street address.
	'''
	# 2-char country code (see http://en.wikipedia.org/wiki/ISO_3166-1)
	country = models.CharField(max_length=2,blank=True)

	# if US state, this field should either contain 2 letters or be blank
	state = models.CharField(max_length=30,blank=True)

	town = models.CharField(max_length=60,blank=True)
	neighborhood = models.ForeignKey(Neighborhood,blank=True,null=True)
	
	postcode = models.CharField(max_length=10,blank=True)
	address = models.TextField('street address',blank=True)

	# should always be between -90,90
	latitude = models.DecimalField(max_digits=9,decimal_places=6,blank=True,null=True)	
	# should always be between -180,180
	longitude = models.DecimalField(max_digits=9,decimal_places=6,blank=True,null=True)	

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

	def __unicode__(self):
		return u'%s (%.3f,%.3f)' % (self.address,self.latitude,self.longitude)

class Place(models.Model):
	'''
	Handles information about places.
	'''
	dtcreated = models.DateTimeField('dt created',auto_now_add=True)
	
	name = models.CharField(max_length=200)
	description = models.TextField(blank=True)
	url = models.URLField(max_length=400,blank=True)
	location = models.ForeignKey(Location,blank=True,null=True)

	def __unicode__(self):
		return self.name

class PlaceMeta(models.Model):
	'''
	Handles meta information (tags, external API ids, etc.) for a Place.
	'''
	place = models.ForeignKey(Place)
	meta_key = models.CharField(max_length=100)
	# blank values allowed (boolean meta attributes)
	meta_value = models.TextField(blank=True)

class LocationMeta(models.Model):
	'''
	Handles meta information (tags, external API ids, etc.) for a Place.
	'''
	location = models.ForeignKey(Location)
	meta_key = models.CharField(max_length=100)
	# blank values allowed (boolean meta attributes)
	meta_value = models.TextField(blank=True)