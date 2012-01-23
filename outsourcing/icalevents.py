from onlyinpgh.outsourcing.models import ICalendarFeed, VEventRecord
from onlyinpgh.places.models import Location, Place
from onlyinpgh.events.models import Event, Role

from onlyinpgh.outsourcing.places import smart_text_resolve
from onlyinpgh.utils.time import localtoutc
import icalendar, urllib, pytz, datetime, logging

logger = logging.getLogger('onlyinpgh.outsourcing')

class EventImportReport(object):
	def __init__(self,vevent_record,notices=[]):
		self.vevent_record = vevent_record
		self.notices = notices

    # base class to be used to classify all notices
	class EventImportNotice(object):
		def __init__(self):
			pass

	class UnknownTimezone(EventImportNotice):
		def __init__(self,tzid):
			self.tzid = tzid
			super(EventImportReport.UnknownTimezone,self).__init__()
		def __unicode__(self):
			return u'EventImportNotice: UnknownTimezone: %s' % unicode(self.tzid)

	class UnavailableTimezone(EventImportNotice):
		def __unicode__(self):
			return u'EventImportNotice: UnavailableTimezone'

	class RecordExists(EventImportNotice):
		def __unicode__(self):
			return u'EventImportNotice: RecordExists'		

	class RequiredFieldMissing(EventImportNotice):
		def __init__(self,field):
			self.field = field
			super(EventImportReport.RequiredFieldMissing,self).__init__()
		def __unicode__(self):
			return u'EventImportNotice: RecordExists'		

	class LocationResolveStatus(EventImportNotice):
		def __init__(self,location_str,status):
			self.location_str = location_str
			self.status = status
			super(EventImportReport.LocationResolveStatus,self).__init__()
		def __unicode__(self):
			return u'EventImportNotice: LocationResolveStatus: "%s" resolved with parse status %s' % (self.location_str,self.status)

	class FailedLocationResolve(EventImportNotice):
		def __init__(self,location_str):
			self.location_str = location_str
			super(EventImportReport.FailedLocationResolve,self).__init__()
		def __unicode__(self):
			return u'EventImportNotice: FailedLocationResolve: "%s"' % self.location_str

class FeedImporter(object):
	def __init__(self,feed_inst):
		'''initialize from an ICalendarFeed instance'''
		self.feed_instance = feed_inst
	
	@classmethod
	def from_url(cls,url,organization=None):
		'''initialize from a url and Organization instance'''

		f = urllib.urlopen(url)
		ical = icalendar.Calendar.from_string(f.read())
		f.close()
		cal_name = ical.get('X-WR-CALNAME',url)

		feed, created = ICalendarFeed.objects.get_or_create(
							url=url,name=cal_name)
		
		if organization:
			# if we need to set the owner, but found an existing feed whose owner is different, fail
			if not created and feed.owner is not None and feed.owner != organization:
				raise Exception('Feed already exists under different owner. Cannot create new one.')
			feed.owner = organization	
			feed.save()

		return cls(feed)
	
	def _resolve_location_string(self,location_str):
		if location_str:
			# TODO: could do some geocoding filtering here
			result = smart_text_resolve(location_str)

			if result.place is not None:
				place = result.place
			elif result.location is not None:
				place = Place(name=location_str,location=result.location)
			else:
				return None, None
		else:
			return None, None

		# neither the location nor place are in the DB yet. do this now
		l = place.location
		if l:
			place.location, _ = Location.close_manager.get_close_or_create(
									address=l.address,
									postcode=l.postcode,
									town=l.town,
									state=l.state,
									country=l.country,
									neighborhood=l.neighborhood,
									latitude=l.latitude,
									longitude=l.longitude)
		place, _ = Place.objects.get_or_create(name=place.name,location=place.location)
		return place, result.parse_status


	def import_new(self,start_filter=None):
		'''
		Import any events in the feed not already tracked by a 
		VEventRecord. If provided, will ignore any events taking place
		before start_filter.

		Function is a generator object that will yield a collection of
		EventImportNotice objects, one per entry considered (that begins
		after the start_filter). If the event was not created successfully,
		the VEventRecord in the returned notice will not be savable to the 
		db.
		'''
		def _process_time(component):
			'''
			Returns a UTC-based timezone-naive datetime for the time present
			in the given component. The component must have a dt element and 
			an optional TZID parameter.

			Helper assumes the existance of a 'notices' list, a 'uid' string
			and a 'default_tz_str' string (which may be empty or None).
			'''
			dt = component.dt
			try:
				# pull the datetime first -- if its UTC, we'll know immediately
				if dt.tzinfo:
					return component.dt.replace(tzinfo=None)
			except AttributeError:
				# if no timezone, it must be a regular date object. give it a time of midnight
				return datetime.datetime.combine(dt,datetime.time())

			# otherwise, we need to find a timezone
			tz_str = component.params.get('TZID',default_tz_str)
			# if couldn't find one, return the bare dt with a notice
			if not tz_str:
				notices.append(EventImportReport.UnavailableTimezone())
				return component.dt
			
			# we have a timezone string, try converting to UTC now. if the string is invalid, return a notice
			try:
				return localtoutc(component.dt,tz_str,return_naive=True)
			except pytz.exceptions.UnknownTimeZoneError:
				notices.append(EventImportReport.UnknownTimezone(tz_str))
				return component.dt

		place_cache = {}	# cached dict of location strings to resolved places
		owner = self.feed_instance.owner

		f = urllib.urlopen(self.feed_instance.url)
		ical = icalendar.Calendar.from_string(f.read())
		f.close()

		default_tz_str = ical.get('X-WR-TIMEZONE')
		
		reports = []
		for entry in ical.walk('vevent'):
			try:
				notices, uid = [], None
				uid = unicode(entry['uid'])
				# grab the start time

				# ignore entry if it starts before the filter
				dtstart = _process_time(entry['dtstart'])
				if start_filter is not None and dtstart < start_filter:
					continue
				
				# see if we've already processed this record. if so, we're done
				try:
					record = VEventRecord.objects.get(feed=self.feed_instance,uid=uid)
					notices.append(EventImportReport.RecordExists())
					yield EventImportReport(record,notices)
					continue
				except VEventRecord.DoesNotExist:
					pass
				
				#### Location Processing ####
				location_str = entry.get('location','').strip()
				loc_key = location_str.strip().lower()

				# if the place isn't cached, we need to resolve and cache it				
				if loc_key in place_cache:
					place = place_cache[loc_key]
				else:
					try:
						place, status = self._resolve_location_string(location_str)
					except IOError:
						place, status = None, 'IOERROR'

					if status:
						notices.append(EventImportReport.LocationResolveStatus(location_str,status))
					# cache the results of the resolve process
					place_cache[loc_key] = place

				# if the location string is non-empty but the place is, we need a notice
				if location_str and place is None:
					notices.append(EventImportReport.FailedLocationResolve(location_str))
					
				#### Other field processing and Event creation ####
				dtmodified = entry.get('LAST-MODIFIED')
				if dtmodified:
					dtmodified = _process_time(dtmodified)

				name = entry.get('summary','').strip()
				event = Event.objects.create(name=name,
											 dtstart=dtstart,
											 dtend=_process_time(entry['dtend']),
											 description=entry.get('description','').strip(),
											 place=place,
				        					 dtmodified=dtmodified)
				if owner:
					Role.objects.create(role_type='host',
										organization=owner,
										event=event)

				record = VEventRecord.objects.create(event=event,
														uid=uid,
														dtmodified=dtmodified,
														feed=self.feed_instance)
				yield EventImportReport(record,notices)
			except KeyError as e:
				notices.append(EventImportNotice.RequiredFieldMissing(e.message))
				yield EventImportReport(VEventRecord(uid=uid),notices)
			except Exception as e:
				logger.error('iCalendar UID. %s' % unicode(e))
				yield None