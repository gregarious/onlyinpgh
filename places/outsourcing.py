'''
Module containing utilities that use external APIs to perform 
places-related tasks.
'''

from copy import deepcopy
from itertools import chain
import re, time, json, datetime

from django.db.models import Q

from onlyinpgh.apitools import google
from onlyinpgh.apitools import factual
from onlyinpgh.apitools import facebook
from onlyinpgh.places import US_STATE_MAP

from onlyinpgh.places.models import Location, Place, PlaceMeta, ExternalPlaceSource, FacebookPageRecord
from onlyinpgh.identity.models import Organization

import logging
dbglog = logging.getLogger('onlyinpgh.debugging')

def _resolve_result_to_place(result):
    resolved_loc = Location(
            country='US',           
            address=result.get('address',''),
            town=result.get('locality',''),
            state=result.get('region',''),
            postcode=result.get('postcode',''),
            latitude=result.get('latitude'),
            longitude=result.get('longitude'))
    
    # TODO: make place meta key to url here
    return Place(name=result.get('name'),
                    location=resolved_loc)


def _geocode_result_to_location(result):
    coords = result.get_geocoding()
    return Location(
        address = result.get_street_address(),
        postcode = result.get_postalcode(),
        town = result.get_town(),
        state = result.get_state(),
        country = result.get_country(),
        latitude = coords[0],
        longitude = coords[1]
    )

def resolve_place(partial_place=None,partial_location=None):
    '''
    Resolves a partial Place or Location object into a complete Place 
    using the Factual Resolve API. Returns None if resolution was not 
    possible.
    '''
    if partial_place:
        loc = partial_place.location
        pl_name = partial_place.name
    else:
        loc = partial_location
        pl_name = None

    if loc is None:
        resp = factual.oip_client.resolve(name=pl_name)
    else:
        resp = factual.oip_client.resolve(
            name=pl_name,
            address=loc.address,
            town=loc.town,
            state=loc.state,
            postcode=loc.postcode,
            latitude=loc.latitude,
            longitude=loc.longitude)

    result = resp.get_resolved_result()
    if result:
        return _resolve_result_to_place(result)
    else:
        return None

def resolve_location(partial_location,allow_numberless=True):
    '''
    Resolves a partial Location object into a complete one using the Google
    Geocoding API. Useful for fleshing out non-named locations not in Factual's
    Places database.

    Also useful for normalizing street addresses contained in Location objects.

    Returns None if resolution was not possible.
    '''
    LAT_BUFFER, LONG_BUFFER = 0.005, 0.005

    # need to combine most Location fields into a string
    state = partial_location.state
    if partial_location.postcode:
        state += ' ' + partial_location.postcode
    nbrhd = partial_location.neighborhood.name if partial_location.neighborhood else ''
    fields = [partial_location.address, nbrhd, partial_location.town, state]
    address_text = ', '.join( [field for field in fields if field != '' ])
    
    biasing_args = {}
    # use the location's lat/long to create a bounding window biaser
    if partial_location.latitude is not None and partial_location.longitude is not None:
        biasing_args['bounds'] = \
            ((partial_location.latitude-LAT_BUFFER, partial_location.longitude-LONG_BUFFER),
             (partial_location.latitude+LAT_BUFFER, partial_location.longitude+LONG_BUFFER))

    # use country as a region biaser
    if partial_location.country:
        biasing_args['region'] = partial_location.country

    # Run the geocoding
    time.sleep(.5)   # TODO: remove
    response = google.GoogleGeocodingClient.run_geocode_request(address_text,**biasing_args)
    result = response.best_result(wrapped=True)
    # TODO: add ambiguous result handling
    if not result or not result.is_address_concrete(allow_numberless):
        return None

    # convert geocoding result to Location
    return _geocode_result_to_location(result)

def text_to_location(address_text,seed_location=None,allow_numberless=True):
    '''
    Attempts to resolve a raw text string into a Location using the Google
    Geocoding API.

    If Location object is provided as seed_location Location, the completed
    fields from it are used as hints to help resolving. These hints are more
    forgiving than those used in the Resolve API. Note that the Location's 
    address field will have no bearing on the results.

    If allow_numberless is False, the resolved location must be one more 
    specific that a neighborhood.

    Returns None if resolution was not possible.
    '''
    # if given a seed location, this is implemented by copying over the 
    # seed location and inserting the given raw text into the Location's 
    # field
    if seed_location:
        location = deepcopy(seed_location)
    else:
        location = Location()
    location.address = address_text

    return resolve_location(location,allow_numberless)

city_pattern = re.compile( 
            r'((new\s+)?[\w-]+)' +  # city part (doesn't support multi-word cities other that ones starting with )
            r'\W+' +                # space between city and state/zip
            r'(' +                  # OR group for matching state or zip code
                r'([A-Z]{2}\b(\W+\d{5}(\-\d{4})?)?)' +    # state with optional zip
                r'|' +              
                r'(\d{5}(\-\d{4})?)' +                   # just zip
            r')\W*$',                   # assert string ends after the state/zip
            re.IGNORECASE)      # ignore case for the "new" string
postcode_pattern = re.compile(r'\b(\d{5}(\-\d{4})?)\W*$')
splitter_pattern = re.compile(r'[\|\;\(\)]|(\s-{1,2}\s)')
def _parse_raw_address(address):
    '''
    Returns a dict of various values used in text_to_place to help
    resolve unstructured address requests
    '''
    result_dict = {}
    # split input by semicolons, pipes, parentheses and dashes (we'll split by commas 
    #  as well, but not now -- potential city/state/postcode patterns depend on not 
    #  splitting by comma)
    fields = [f.strip() for f in splitter_pattern.split(address)[::2]]  # even elements are grouping matches
    
    # look for potential city, state and postal code in the fields
    # overwrite on multiple matches - last one found is most likely to 
    # be the tail of an address
    
    for field in fields:
        m = city_pattern.search(field)
        if m: 
            result_dict['potential_town'] = m.group(1)
            # see if a state was matched in group #3
            try:
                result_dict['potential_state'] = re.match(r'[A-Za-z]{2}\b',m.group(3)).group(0)
            except AttributeError:
                if 'potential_state' in result_dict: result_dict.pop('potential_state')
        m = postcode_pattern.search(field)
        if m: result_dict['potential_postcode'] = m.group(1)

    # now split the fields by comma
    result_dict['all_fields'] = list(chain.from_iterable([f.split(',') for f in fields]))

    # grab the inside and left-outside of last set of parentheses in raw string
    p_match = re.match(r'^(.+)\((.+)\)',address)
    if p_match:
        result_dict['paren_outside'] = p_match.group(1).strip()
        result_dict['paren_inside'] = p_match.group(2).strip()
    return result_dict

import sys
def text_to_place(address_text,fallback_place_name='',seed_location=None,fout=sys.stdout):
    '''
    Attempts to resolve a raw text string into a Place using a series of
    strategies.

    First, the Resolve API is queried using various mutations of the
    fields in the input text. 

    If none of these attempts are successful, the Google Geocoding API 
    is used to at least get a physical location. In addition, some simple
    parsing of the text will be used to guess at a potential name for the
    place. If no such place name can be discerned, the fallback_place_name
    argument will be used as a last result.

    If Location object is provided as seed_location Location, the completed
    fields from it are used as hints to help resolving. These hints are more
    forgiving than those used in the Resolve API. Note that the Location's 
    address field will have no bearing on the results.

    Will never fail -- worst case behavior returns a simple Place object with
    the fallback place name and no location.
    '''
    if address_text == '':
        return Place()
    
    # parse out various fields of interest 
    parsed_content = _parse_raw_address(address_text) 

    fields = parsed_content['all_fields']
    inside = parsed_content.get('paren_inside')
    outside = parsed_content.get('paren_outside')
    pot_town = parsed_content.get('potential_town')
    pot_state = parsed_content.get('potential_state')
    pot_postcode = parsed_content.get('potential_postcode')

    ### Resolve API battery
    def _seeded_resolve(name=None,address=None,postcode=None,town=None,state=None):
        if seed_location:
            l = deepcopy(seed_location)
        else:
            l = Location()
        if name:        l.name = name
        if address:     l.address = address
        if postcode:    l.postcode = postcode
        if town:        l.town = town
        if state:       l.state = state
        return resolve_place(Place(name=name,location=l))
    
    # 1: Try the whole string as the name
    result = _seeded_resolve(name=address_text)
    if result:
        print >>fout, "RESOLVED: FULL STRING NAME"
        return result
    
    # 2: The first split field as the name
    result = _seeded_resolve(name=fields[0])
    if result: 
        print >>fout, "RESOLVED: NAME"
        return result

    # 3: First split field as the name, second as the address
    if len(fields) > 1:
        result = _seeded_resolve(name=fields[0],address=fields[1])
        if result: 
            print >>fout, "RESOLVED: NAME & ADDRESS"
            return result

    # 4: First split as name, potential zip code (only if it exists)
    # (Potential zip code is more reliable than city/state. Try this alone before others.)
    if pot_postcode:
        result = _seeded_resolve(name=fields[0],postcode=pot_postcode)
        if result: 
            print >>fout, "RESOLVED: NAME & POSTCODE"
            return result

    # 5: Now try all other potential fields (assuming a potential city was found)
    if pot_town:
        result = _seeded_resolve(name=fields[0],
                                    town=pot_town,
                                    state=pot_state,
                                    postcode=pot_postcode)
        if result: 
            print >>fout, "RESOLVED: NAME, POSTCODE, TOWN, STATE"
            return result

    # 6: If parenthesized expression is in string, Try inside as address, outside as name and vice versa
    if outside:
        result = _seeded_resolve(name=outside,address=inside)
        if result: 
            print >>fout, "RESOLVED: NAME (ADDRESS)"
            return result
    if inside:
        result = _seeded_resolve(name=inside,address=outside)
        if result: 
            print >>fout, "RESOLVED: ADDRESS (NAME)"
            return result
            
    result = text_to_location(address_text,seed_location,allow_numberless=False)
    if result is not None:
        print >>fout, "GEOCODED: FULL STRING"
        return Place(name='',location=result)

    # 2: Try geocoding the concatenation of split fields 2 through end
    #    If successful, use first field as place name
    if len(fields) > 1:
        result = text_to_location(','.join(fields[1:]),seed_location,allow_numberless=False)
        if result is not None:
            print >>fout, "GEOCODED: TAIL CONCAT"
            return Place(name=fields[0],location=result)

    # 3a: Try geocoding the inside, use outside as place on success
    if inside:        
        result = text_to_location(inside,seed_location,allow_numberless=False)
        if result is not None:
            print >>fout, "GEOCODED: (ADDRESS)"
            return Place(name=outside,location=result)
    # 3b: Try geocoding the outside, use inside as place on success
    if outside:
        result = text_to_location(outside,seed_location,allow_numberless=False)
        if result is not None:
            print >>fout, "GEOCODED: ADDRESS (...)"
            return Place(name=inside,location=result)
    
    # gnarly address, dude. return the fallback
    print >>fout, 'FALLBACK!'
    return Place(name=fallback_place_name,location=None)    

def normalize_street_address(address_text):
    '''
    Given a free-formed address in a string, returns the normalized street
    address portion of a result obtained by Google Geocoding API.

    Including additional address information (e.g. city, zip code) is useful
    for the API query, but will the information will not be included in
    the result.

    Returns None if normalization was not possible.
    '''
    response = google.GoogleGeocodingClient.run_geocode_request(address_text)
    result = response.best_result(wrapped=True)
    # TODO: add ambiguous result handling
    if not result:
        return None
    return result.get_street_address()

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
                opts = copy(search_opts)
                opts['q']=letter
                batch_commands.append(BatchCommand('search',options=opts))
            for response in fb_client.run_batch_request(batch_commands):
                pages_unfilitered.extend(response['data'])
        else:
            for letter in letters:
                pages_unfilitered.extend(fb_client.graph_api_query('search',q=letter,**search_opts))
                  
        # need to go through the 26 separate page sets to filter out dups
        ids_seen = set()    # cache the ids in the list for a quick duplicate check
        pages = []
        for page in pages_unfilitered:
            if page['id'] not in ids_seen:
                ids_seen.add(page['id'])
                pages.append(page)
        return pages
    else:
        return fb_client.graph_api_query('search',q=query,**search_opts)

def get_full_place_pages(pids):
    '''
    Returns a list of full page information dicts, one per page id.
    '''
    page_details = []
    cmds = []
    ctr = 0
    def _add_batch(batch):
        responses = facebook.oip_client.run_batch_request(batch)
        # TODO: DEBUG REMOVE
        for req,resp in zip(batch,responses):
            if not resp:
                print 'Batch response: %s => %s' % (str(req.url),str(resp))
            elif 'error' in resp:
                print 'Batch response: %s => %s:%s' % (req.url, resp['error'].get('type'), resp['error'].get('message'))

        page_details.extend([resp if resp and 'error' not in resp.keys() else None 
                                for resp in responses ])

    for pid in pids:
        cmds.append(facebook.BatchCommand(pid))
        if len(cmds) == 50:
            ctr = ctr + 1
            print 'batch', ctr, 'of', len(pids)/50+1
            _add_batch(cmds)
            cmds = []
    if len(cmds) > 0:
        ctr = ctr + 1
        print 'batch', ctr, 'of', len(pids)/50+1
        _add_batch(cmds)
    return page_details    

def _create_place_meta(page,place,fb_key,meta_key):
    try:
        # TODO: revisit 
        if fb_key == 'url':
            val = page.get('website',page.get('link','')).strip()
        else:
            val = str(page.get(fb_key,'')).strip()
        
        if val:
            PlaceMeta.objects.get_or_create(place=place,meta_key=meta_key,
                                            defaults={'meta_value':val})
    except UnicodeEncodeError as e:
        print page['id'], e.message

def fbloc_to_loc(fbloc):
    # TODO: temp
    state = fbloc.get('state','').strip()
    if len(state) != 2 and state != '':
        try:
            state = state.lower()
            state = (ab for ab,full in US_STATE_MAP.items() if full.lower()==state).next()
        except StopIteration:
            print 'non-PA state found:',state
            state = ''

    return Location(address=fbloc.get('street','').strip(),
                    town=fbloc.get('city','').strip(),
                    state=state,
                    postcode=fbloc.get('postcode','').strip(),
                    latitude=fbloc.get('latitude'),
                    longitude=fbloc.get('longitude'))

# TODO: revisit page cache thing
def page_id_to_organization(page_id,create_new=True,page_cache={}):
    '''
    Takes a fb page ID and tries to resolve an Organization object 
    from it. First queries the FacebookPageRecord table. If that fails, 
    and create_new is True, it will try to create a new one and return 
    that.

    If page information has been loaded at a prior time for a group of 
    pages, the page_cache argument can be used (dict of ids to page 
    details).

    Returns None if no Organization could be retreived.
    '''
    try:
        organization = FacebookPageRecord.objects.get(fb_id=page_id).associated_organization
        dbglog.info('found existing organization for fbid %s'%page_id)
    except FacebookPageRecord.DoesNotExist:
        organization = None
    
    # we return if we either found a record, or didn't but can't create
    if organization or not create_new:
        return organization

    dbglog.info('gathering data for creating org with fbid %s' % page_id)
    if page_id in page_cache:
        page = page_cache[page_id]
        dbglog.debug('retreiving page info from cache')
    else:
        try:
            dbglog.debug('retreiving page info from facebook')
            page = facebook.oip_client.graph_api_objects(page_id)

        except facebook.FacebookAPIError as e:
            dbglog.error('Facebook error occured!')
            dbglog.error(str(e))
            return None

    pname = page['name'].strip()

    # TODO: temp because of idiotic page http://graph.facebook.com/104712989579167
    try:
        url = page.get('website','').split()[0].strip()
    except IndexError:
        url = page.get('link','http://www.facebook.com/%s'%page_id)
    organization = Organization(name=pname,
                        avatar=page.get('picture',''),
                        url=url)
    organization.save()
    # TODO: wtf page 115400921824318?
    # TODO: ensure page isn't just a user
    try:
        ostr = unicode(organization)
    except UnicodeDecodeError:
        ostr = '<UNICODE ERROR>'
    dbglog.info(u'created new organization for fbid %s: "%s"' % (page_id,ostr))

    try:
        record = FacebookPageRecord.objects.get(fb_id=page_id)
    except FacebookPageRecord.DoesNotExist:
        record = FacebookPageRecord(fb_id=page_id)

    record.associated_organization = organization
    record.save()

    return organization

def debug_loc_print(l):
    return '%s, %s, %s %s (%.3f,%.3f)' % \
                (l.address,l.town,l.state,l.postcode,l.latitude or 0,l.longitude or 0)

def debug_place_print(place):
    return '%s: %s' % (place.name,debug_loc_print(place.location))

# TODO: revisit page cache thing
def page_id_to_place(page_id,create_new=True,create_owner=True,page_cache={}):
    '''
    Takes a fb page ID and tries to resolve a Place object from it. First 
    queries the FacebookPageRecord table. If that fails, and create_new 
    is True, it will try to create a new one and return that.

    If page information has been loaded at a prior time for a group of 
    pages, the page_cache argument can be used (dict of ids to page 
    details).

    Returns None if no Place could be retreived.
    '''
    try:
        place = FacebookPageRecord.objects.get(fb_id=page_id).associated_place
        dbglog.info('found existing place for fbid %s'%page_id)
    except FacebookPageRecord.DoesNotExist:
        place = None
    
    # we return if we either found a record, or didn't but can't create
    if place or not create_new:
        return place

    # Create a new Place
    dbglog.info('gathering data for creating place from fbid %s' % page_id)
    if page_id in page_cache:
        page = page_cache[page_id]
        dbglog.debug('retreiving page info from cache')
    else:
        try:
            page = facebook.oip_client.graph_api_objects(page_id)    
            dbglog.debug('retreiving page info from facebook')
        except facebook.FacebookAPIError as e:
            dbglog.error('Facebook error occured!')
            dbglog.error(str(e))
            return None

    pname = page['name'].strip()

    place = Place(name=pname,
                    description=page.get('description','').strip())
    
    ### Figure out the new Place's location field
    # TODO: REVISIT THIS FLOW
    fbloc = page.get('location')
    if not fbloc:
        dbglog.warning('no location for page %s. aborting' % page_id)
        return None
    if 'id' in fbloc:
        dbglog.notice('page %s has id in location (%s)' % (page_id,fbloc['id']))
    location = fbloc_to_loc(fbloc)

    # if there's no address or geocoding, we'll need to talk to outside services
    if not location.address:
        dbglog.debug('attempting to resolve place with API calls')
        # TODO: insert more factual logic? (i.e. saving uid, setting place to this uid, etc.)
        seed_place = Place(name=pname,location=location)
        resolved_place = resolve_place(seed_place)
        if resolved_place:
            dbglog.debug('successful Factual resolve: "%s" => "%s"' % \
                            (debug_place_print(seed_place),debug_place_print(resolved_place)))
            location = resolved_place.location
    
    # really want geolocation, go to Google Geocoding for it if we need it
    if location.longitude is None or location.latitude is None:
        seed_loc = deepcopy(location)
        resolved_location = resolve_location(seed_loc)
        if resolved_location: 
            location = resolved_location
            dbglog.debug('successful geocoding: "%s" => "%s"' % \
                            (debug_loc_print(seed_loc),debug_loc_print(resolved_location)))

    if location:
        # TODO: put this into the manager or a Location.save override
        location, created = Location.objects.get_or_create(
                        address=location.address,
                        postcode=location.postcode,
                        town=location.town,
                        state=location.state,
                        country=location.country,
                        neighborhood=location.neighborhood,
                        latitude=location.latitude,
                        longitude=location.longitude)
        if created:
            dbglog.debug('saved new location "%s"' % debug_loc_print(location))
        else:
            dbglog.debug('retrieved existing location "%s"' % debug_loc_print(location))

    place.location = location
    dbglog.debug('resolving owner %s' % page_id)
    place.owner = page_id_to_organization(page_id,create_new=create_owner,page_cache=page_cache)
    try:
        # TODO: put this into the manager or a Place.save override. Handle nonunique name,location combo
        place, created = Place.objects.get_or_create(
                                name=place.name,
                                description=place.description,
                                location=place.location,
                                owner=place.owner)
        if created:
            dbglog.info('created new place for fbid %s: "%s"' % (page_id,debug_place_print(place)))
        else:
            dbglog.info('retreived existing place for fbid %s: "%s"' % (page_id,debug_place_print(place)))
    except Warning as w:
        dbglog.warning('while saving place for fbid %s: %s' % (page_id,str(w)))
        # TODO: soooo apparently the place gets saved, but then the id gets removed? wtf.
        # This means we can't save the record. hm.
        return

    # We've got a new FB page record
    try:
        record = FacebookPageRecord.objects.get(fb_id=page_id)
    except FacebookPageRecord.DoesNotExist:
        record = FacebookPageRecord(fb_id=page_id)
    record.associated_place = place
    record.save()

    # add place meta info that exists      
    _create_place_meta(page,place,'url','url')
    _create_place_meta(page,place,'phone','phone')
    _create_place_meta(page,place,'hours','hours')
    _create_place_meta(page,place,'picture','image_url')

    # finally create an more generally useful external UID reference to the fb page
    ExternalPlaceSource.objects.create(place=record.associated_place,
        service='fb',uid=page_id)
    return place

def _get_all_places_from_cron_job():
    '''
    Runs a series of queries to return the same results that the old oip
    fb5_getLocal.execute_quadrants Java code searches over.
    '''
    search_coords = [ (40.44181,-80.01277),
                      (40.666667,-79.700556),
                      (40.666667,-80.308056),
                      (40.216944,-79.700556),
                      (40.216944,-80.308056),
                      (40.44181,-80.01277),
                    ]

    all_ids = set()
    for coords in search_coords:
        ids = [page['id'] for page in gather_place_pages(coords,25000)]
        all_ids.update(ids)
    return list(all_ids)
