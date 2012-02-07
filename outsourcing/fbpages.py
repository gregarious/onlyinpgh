'''
Module containing code for managing Facebook pages, including Organization
or Place insertion, updating, etc.
'''

from django.db import transaction

from onlyinpgh.outsourcing.apitools import facebook, facebook_client
from onlyinpgh.identity.models import Organization
from onlyinpgh.places.models import Location, Place, Meta as PlaceMeta
from onlyinpgh.outsourcing.models import FacebookOrgRecord, ExternalPlaceSource

from onlyinpgh.outsourcing.places import resolve_place, resolve_location

from onlyinpgh import utils

import logging, copy, re
outsourcing_log = logging.getLogger('onlyinpgh.outsourcing')

# reverse the US_STATE_MAP for eaach lookup of full names to abbreviations
from onlyinpgh.places import US_STATE_MAP
state_name_to_abbrev = {name:code for code,name in US_STATE_MAP}

def get_full_place_pages(pids):
    '''
    Returns a list of full page information dicts, one per page id.

    Bad requests will return caught exception objects.
    '''
    page_details = []
    cmds = []
    def _add_batch(batch):
        responses = facebook_client.run_batch_request(batch)
        for resp,batch_req in zip(responses,batch):
            try:
                resp = facebook_client.postprocess_response(batch_req.to_GET_format(),resp)
            except facebook.FacebookAPIError as e:
                resp = e
            page_details.append(resp)

    for pid in pids:
        cmds.append(facebook.BatchCommand(str(pid),{'metadata':1}))
        if len(cmds) == 50:
            _add_batch(cmds)
            cmds = []
    if len(cmds) > 0:
        _add_batch(cmds)

    return page_details 

def gather_fb_place_pages(center,radius,query=None,limit=4000,batch_requests=True):
    '''
    Returns a list of Facebook place page info stubs represneting all places 
    found in the given area. Object fields can be found at 
    https://developers.facebook.com/docs/reference/api/page/

    center should be a tuple of (latitude,logitude) values, and radius is 
    in meters (i think?)

    If query is omitted, a "blank query" will be run by running the same 
    center and radius query 26 separate times, once per letter of the 
    alphabet as the actual query argument. 

    If batch_request is True (default), these requests will be batched, 
    otherwise they'll be run once at a time. Commands with a large number
    of results may fail if batched.

    No error handling right now -- if any of the search requests fail the whole 
    thing is coming down.
    '''
    search_opts = dict(type='place',
                        center='%f,%f' % center,
                        distance=radius,
                        limit=limit)
    
    # no query given, run one for each letter of the alphabet
    if query is None:
        batch_commands, pages_unfilitered = [], []
        letters = [chr(o) for o in range(ord('a'),ord('z')+1)]

        if batch_requests:
            for letter in letters:
                opts = copy.copy(search_opts)
                opts['q']=letter
                batch_commands.append(facebook.BatchCommand('search',options=opts))
            for response in facebook_client.run_batch_request(batch_commands):
                pages_unfilitered.extend(response['data'])
        else:
            for letter in letters:
                pages_unfilitered.extend(facebook_client.graph_api_collection_request('search',q=letter,**search_opts))
                  
        # need to go through the 26 separate page sets to filter out dups
        ids_seen = set()    # cache the ids in the list for a quick duplicate check
        pages = []
        for page in pages_unfilitered:
            if page['id'] not in ids_seen:
                ids_seen.add(page['id'])
                pages.append(page)
        return pages
    else:
        return facebook_client.graph_api_collection_request('search',q=query,**search_opts)

@transaction.commit_on_success
def store_fbpage_organization(page_info):
    '''
    Takes a dict of properties retreived from a Facebook Graph API call for
    a page and stores an Organization from the information. The following 
    fields in the dict are used:
    - id        (required)
    - type      (required with value 'page' or a TypeError will be thrown)
    - name      (required)
    - website
    - picture

    If a FacebookOrgRecord already exists for the given Facebook id, the 
    already linked organization is returned. An INFO message is logged to 
    note the attempt to store an existing page as an Organization.
    '''
    pid = page_info.get('id')
    if pid is None:
        raise TypeError("Cannot store object without 'event' type.")

    try:
        organization = FacebookOrgRecord.objects.get(fb_id=pid).organization
        outsourcing_log.info('Existing fb page Organization found for fbid %s' % unicode(pid))
        return organization
    except FacebookOrgRecord.DoesNotExist:
        pass

    if page_info.get('type') != 'page':
        raise TypeError("Cannot store object without 'page' type as a Place.")

    pname = page_info['name'].strip()

    try:
        # url field can be pretty free-formed and list multiple urls. 
        # we take the first one (identified by whitespace parsing)
        url = page_info.get('website','').split()[0].strip()
    except IndexError:
        # otherwise, go with the fb link (and manually create it if even that fails)
        url = page_info.get('link','http://www.facebook.com/%s'%pid)
    
    # ensure URL starts with protocol (PHP site didn't handle these URLs well)
    url_p = re.compile(utils.url_pattern)
    if not url_p.match(url):
        url = 'http://'+url
        if not url_p.match(url):    # if that didn't work, blank out the url
            url = ''

    organization, created = Organization.objects.get_or_create(name=pname[:200],
                                                                avatar=page_info.get('picture','')[:400],
                                                                url=url[:400])

    if not created:
        outsourcing_log.info('An organization matching fbid %s already existed with '\
                             'no FacebookOrgRecord. The record was created.' % unicode(pid))
    
    record = FacebookOrgRecord.objects.create(fb_id=pid,organization=organization)
    outsourcing_log.info(u'Stored new Organization for fbid %s: "%s"' % (pid,unicode(organization)))

    if len(pname) == 0:
        logging.warning('Facebook page with no name was stored as Organization')

    return organization


def fbloc_to_loc(fbloc):
    '''
    Converts a dict of fields composing a Facebook location to a Location.
    '''
    state = fbloc.get('state','').strip()
    # State entry is often full state name
    if len(state) != 2 and state != '':
        state = state_name_to_abbrev.get(state,'')

    return Location(address=fbloc.get('street','').strip(),
                    town=fbloc.get('city','').strip(),
                    state=state,
                    postcode=fbloc.get('postcode','').strip(),
                    latitude=fbloc.get('latitude'),
                    longitude=fbloc.get('longitude'))

def _store_fbpage_placemeta(page_info,place):
    '''
    Helper function to be used in conjuction with store_fbpage_place.
    '''
    # first the easy ones: phone, hours, picture
    image_url = page_info.get('picture')
    if image_url:
        PlaceMeta.objects.get_or_create(place=place,meta_key='image_url',meta_value=image_url)
    phone = page_info.get('phone')
    if phone:
        PlaceMeta.objects.get_or_create(place=place,meta_key='phone',meta_value=phone)
    hours = page_info.get('hours')
    if hours:
        PlaceMeta.objects.get_or_create(place=place,meta_key='hours',meta_value=hours)

    try:
        # url field can be pretty free-formed and list multiple urls. 
        # we take the first one (identified by whitespace parsing)
        url = page_info.get('website','').split()[0].strip()[:400]
    except IndexError:
        # otherwise, go with the fb link (and manually create it if even that fails)
        url = page_info.get('link','http://www.facebook.com/%s'%page_info['id'])
    if url:
        PlaceMeta.objects.get_or_create(place=place,meta_key='url',meta_value=url)

# TODO: need to test what happens when _store_fbpage_placemeta returns -- does it commit its part? it shouldn't.
@transaction.commit_on_success
def store_fbpage_place(page_info,create_owner=True):
    '''
    Takes a dict of properties retreived from a Facebook Graph API call for
    a page and stores a Place from the information. The following 
    fields in the dict are used:
    - id          (required)
    - type        (required with value 'page' or a TypeError will be thrown)
    - location    (required or TypeError will be thrown)
    - description
    - url
    - phone
    - hours
    - picture

    No new Place will be returned if either an identical one already
    exists in the db, or an ExternalPlaceSource already exists for 
    the given Facebook id. An INFO message is logged to note the attempt 
    to store an existing page as a Place.

    If create_owner is True a new Organization will be created from the same
    page information if one does not already exist.
    '''
    pid = page_info['id']
    
    try:
        place = ExternalPlaceSource.objects.get(service='fb',uid=pid).place
        outsourcing_log.info('Existing fb page Place found for fbid %s' % unicode(pid))
        return place
    except ExternalPlaceSource.DoesNotExist:
        pass

    if page_info.get('type') != 'page':
        raise TypeError("Cannot store object without 'page' type as a Place.")
    elif 'location' not in page_info:
        raise TypeError("Cannot store object without location key as a Place.")
    
    pname = page_info['name'].strip()

    ### Figure out the new Place's location field
    fbloc = page_info['location']
    if 'id' in fbloc:
        # TODO: need to ensure fbloc_to_loc can handle ids in location if this ever happens
        outsourcing_log.info('Facebook page %s has id in location (%s)' % (pid,fbloc['id']))
    location = fbloc_to_loc(fbloc)

    # if there's no address or geocoding, we'll need to talk to outside services
    if not location.address:
        seed_place = Place(name=pname,location=location)
        resolved_place = resolve_place(seed_place)
        if resolved_place:
            location = resolved_place.location
    
    # really want geolocation, go to Google Geocoding for it if we need it
    if location.longitude is None or location.latitude is None:
        seed_loc = copy.deepcopy(location)
        resolved_location = resolve_location(seed_loc,allow_numberless=False)
        if resolved_location: 
            location = resolved_location

    # if there's no specific address information, make the error radius around the
    # lat/lng super tight. Don't want to create whirlpools. 
    cl_opts = dict(lat_error=1e-5,lng_error=1e-5) if not location.address else {}
    
    location, created = Location.close_manager.get_close_or_create(
                    address=location.address,
                    postcode=location.postcode,
                    town=location.town,
                    state=location.state,
                    country=location.country,
                    neighborhood=location.neighborhood,
                    latitude=location.latitude,
                    longitude=location.longitude,
                    _close_options=cl_opts)
    if created:
        outsourcing_log.debug('Saved new location "%s"' % location.full_string)
    else:
        outsourcing_log.debug('Retrieved existing location "%s"' % location.full_string)

    try:
        owner = FacebookOrgRecord.objects.get(fb_id=pid).organization
    except FacebookOrgRecord.DoesNotExist:
        if create_owner:
            outsourcing_log.info('Creating new Organization as byproduct of creating Place from Facebook page %s' % unicode(pid))
            owner = store_fbpage_organization(page_info)
        else:
            owner = None

    place, created = Place.objects.get_or_create(name=pname[:200],
                        description=page_info.get('description','').strip(),
                        location=location,
                        owner=owner)

    # add place meta info that exists      
    _store_fbpage_placemeta(page_info,place)

    # create a new link to an external id
    ExternalPlaceSource.objects.create(service='fb',uid=pid,
                                        place=place)
    return place

class PageImportReport(object):
    # notices can be expected to be among the following:
    #   - TypeError (when page is not a valid page for the model type being created)
    #   - FacebookAPIError (for successful responses with unexpected content)
    #   - IOError (if problem getting response from server)
    #   - PageImportReport.RelatedObjectCreationError (e.g. if Org couldn't be created inside Place creation)
    #   - PageImportReport.ModelInstanceExists (if PageImportManager attempts to create an object already being managed)
    def __init__(self,page_id,model_instance,notices=[]):
        self.page_id = page_id
        self.model_instance = model_instance
        self.notices = notices

    class RelatedObjectCreationError(Exception):
        def __init__(self,related_object,error):
            '''
            Related object is any string, error is Exception that occurred
            while object creation was being attempted.
            '''
            self.related_object = related_object
            self.error = error
            super(PageImportReport.RelatedObjectCreationError,self).__init__()

        def __str__(self):
            return 'RelatedObjectCreationError: %s failed with error: "%s"' % \
                    (unicode(self.related_object),unicode(self.error))

    class ModelInstanceExists(Exception):
        def __init__(self,fbid,model_type):
            self.model_type = model_type
            self.fbid = fbid
            super(PageImportReport.ModelInstanceExists,self).__init__()
        
        def __str__(self):
            return 'ModelInstanceExists: %s for Facebook page id %s' % \
                    (unicode(self.model_type),unicode(self.fbid))

class PageImportManager(object):
    '''
    Class to manage the building and storage of Place and Organization
    model instances from Facebook pages.
    '''
    def __init__(self):
        # each page ids requested will ultimately be put in one (and only one) of these buckets:
        self._cached_page_infos = {}    # page_id:{page_info}
        self._unavailable_pages = {}     # page_id:error

    def pull_page_info(self,page_ids,use_cache=True):
        '''
        Returns a list of page info dicts pulled from the live FB service.

        If use_cache is True, any available cached page information stored 
        in this manager will be used.
        '''
        # if we can use the cache, pull any cached ids from the API request
        if use_cache:
            ids_to_pull = set(page_ids) - set(self._cached_page_infos.keys())
        else:
            ids_to_pull = page_ids
        
        try:
            page_infos = get_full_place_pages(ids_to_pull)
        except IOError as e:
            outsourcing_log.error('IOError on batch page info pull: %s' % unicode(e))
            # spread the IOError to all requests
            page_infos = [e]*len(ids_to_pull)

        # update the cached items
        for pid,info in zip(ids_to_pull,page_infos):
            # each "info" is either a successful page info response, or 
            #  an Exception. put them into the correct bnuckets
            if isinstance(info,Exception):
                self._unavailable_pages[pid] = info
            else:
                self._cached_page_infos[pid] = info

        # return the responses in the same order as the requests
        return [self._cached_page_infos.get(pid,self._unavailable_pages.get(pid))
                    for pid in page_ids]

    def _store_org(self,info):
        '''
        Does actual storage of a new page-backed organization. Does the 
        packaging into PageImportReports.
        '''
        pid = info['id']
        # first off -- if org is already stored, we're done -- no overwriting as of now
        try:
            FacebookOrgRecord.objects.get(fb_id=pid)
            return PageImportReport(pid,None,
                        notices=[PageImportReport.ModelInstanceExists(pid,'Organization')])
        except FacebookOrgRecord.DoesNotExist:
            pass

        # try to store, and catch TypeErrors from info not being a 'page'
        try:
            org = store_fbpage_organization(info)
            return PageImportReport(pid,org)
        except TypeError as e:
            return PageImportReport(pid,None,notices=[e])

    def import_org(self,page_id,use_cache=True):
        '''
        Inserts Organizations for a page_id from Facebook. Returns a 
        PageImportReport.

        If a batch of orgs are being imported, building up the cache
        first with a pull_page_info call is recommended.

        Will skip over any Organizations already tracked by 
        aFacebookOrgRecord instance and return a result with a 
        ModelInstanceExists set as the error.
        '''
        page_info = self.pull_page_info([page_id],use_cache)[0]
        if not isinstance(page_info,Exception):
            return self._store_org(page_info)
        else:
            return PageImportReport(page_id,None,[page_info])

    def _store_place(self,info,import_owners=True):
        '''
        Does actual storage of a new page-backed Place. Does the packaging
        into PageImportReports
        '''
        pid = info['id']
        # first off -- if place is already stored, we're done -- no overwriting as of now
        try:
            ExternalPlaceSource.facebook.get(uid=pid)
            return PageImportReport(pid,None,
                        notices=[PageImportReport.ModelInstanceExists(pid,'Place')])
        except ExternalPlaceSource.DoesNotExist:
            pass

        # try to store, and catch TypeErrors from info not being a 'page' or not having a location
        try:
            place = store_fbpage_place(info,import_owners)
            return PageImportReport(pid,place)
        except TypeError as e:
            return PageImportReport(pid,None,notices=[e])

    def import_place(self,page_id,use_cache=True,import_owners=True):
        '''
        Inserts Place corresponding to a page_id from Facebook. Returns a
        PageImportReport.

        Will skip over creating a Place already tracked by a 
        FacebookOrgRecord instance and return a result with a
        ModelInstanceExists set as the error.

        If import_owners is True, an Organization owning the Place that 
        does not already exist will be imported as well.
        '''
        page_info = self.pull_page_info([page_id],use_cache)[0]
        
        if not isinstance(page_info,Exception):
            return self._store_place(page_info,import_owners)
        else:
            return PageImportReport(page_id,None,[page_info])

def import_org(page_id):
    '''
    Quick import of an Organization given an fb page id. Returns a 
    PageImportReport.
    '''
    return PageImportManager().import_org(page_id)

def import_place(page_id,import_owner=True):
    '''
    Quick import of a Place given an fb page id. Returns a PageImportReport.
    '''
    return PageImportManager().import_place(page_id,import_owners=import_owner)
