from onlyinpgh.outsourcing.models import ICalendarFeed, VEventRecord
from onlyinpgh.places.models import Location, Place
from onlyinpgh.events.models import Event, Role

from onlyinpgh.outsourcing.places import smart_text_resolve
from onlyinpgh.utils.time import localtoutc
import icalendar, urllib, pytz

class EventImportReport(object):
	def __init__(self,event_instance,notices=[]):
		self.event_instance = event_instance
		self.notices = notices

    # base class to be used to classify all notices
	class EventImportNotice(object):
		def __init__(self):
			pass

	class UnknownTimezone(EventImportNotice):
		def __init__(self,tzid):
			self.tzid = tzid
			super(EventImportReport.UnknownTimezone,self).__init__()

	class UnavailableTimezone(EventImportNotice):
		pass

	class EventExists(EventImportNotice):
		pass

	class LocationResolveStatus(EventImportNotice):
		def __init__(self,location_str,status):
			self.location_str = location_str
			self.status = status
			super(EventImportReport.LocationResolveStatus,self).__init__()

	class FailedLocationResolve(EventImportNotice):
		def __init__(self,location_str):
			self.location_str = location_str
			super(EventImportReport.FailedLocationResolve,self).__init__()

class FeedImporter(object):
	def __init__(self,feed_inst):
		'''initialize from an ICalendarFeed instance'''
		self.feed_instance = feed_inst
	
	@classmethod
	def from_url(cls,url,organization=None):
		'''initialize from a url and Organization instance'''
		feed_instance = ICalendarFeed.objects.create(
							url=url,
							owner=organization)
		return cls(feed_instance)
	
	def _resolve_location_string(self,location_str):
		if location_str:
			# TODO: could do some geocoding filtering here
			try:
				result = smart_text_resolve(location_str)
			except Exception as e:
				print 'location resolve error!',e
				return None, None

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
		after the start_filter)
		'''
		def _process_time(component):
			'''
			Returns a UTC-based timezone-naive datetime for the time present
			in the given component. The component must have a dt element and 
			an optional TZID parameter.

			Helper assumes the existance of a 'notices' list, a 'uid' string
			and a 'default_tz_str' string (which may be empty or None).
			'''
			# pull the datetime first -- if its UTC, we'll know immediately
			if component.dt.tzinfo:
				return component.dt.replace(tzinfo=None)

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
				notices = []
				uid = entry['uid']
				# grab the start time

				# ignore entry if it starts before the filter
				dtstart = _process_time(entry['dtstart'])
				if start_filter is not None and dtstart < start_filter:
					continue
				
				# see if we've already processed this record. if so, we're done
				try:
					record = VEventRecord.objects.get(feed=self.feed_instance,uid=entry['uid'])
					reports.append( EventImportReport(record.event,[EventImportReport.EventExists()]) )
					continue
				except VEventRecord.DoesNotExist:
					pass
				
				#### Location Processing ####
				location_str = entry.get('location','').encode('utf8')
				loc_key = location_str.strip().lower()

				# if the place isn't cached, we need to resolve and cache it
				place = place_cache.get(loc_key)
				if place is None:
					place, status = self._resolve_location_string(location_str)
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

				event = Event.objects.create(name=entry.get('summary','').encode('utf8'),
											 dtstart=dtstart,
											 dtend=_process_time(entry['dtend']),
											 description=entry.get('description','').encode('utf8'),
											 place=place,
				        					 dtmodified=dtmodified)
				if owner:
					Role.objects.create(role_name='host',
										organization=owner,
										event=event)


				VEventRecord.objects.create(event=event,
											uid=uid,
											dtmodified=dtmodified,
											feed=self.feed_instance)	            
				reports.append( EventImportReport(event,notices) )
			except KeyError as e:
				reports.append( EventImportReport(None,[e]) )
		return reports