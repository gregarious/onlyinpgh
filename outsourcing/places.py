'''
Module containing utilities that use external APIs to perform 
places-related tasks.
'''

from itertools import chain
import re, time, json, datetime, copy

from django.db.models import Q
from django.db import transaction

from onlyinpgh.outsourcing.apitools import google
from onlyinpgh.outsourcing.apitools import factual
from onlyinpgh.outsourcing.apitools import facebook

from onlyinpgh.outsourcing.identity import store_fbpage_organization
from onlyinpgh.outsourcing.models import *
from onlyinpgh.places.models import *

import logging
dbglog = logging.getLogger('onlyinpgh.debugging')
resolvelog = logging.getLogger('onlyinpgh.resolve')

# reverse the US_STATE_MAP for eaach lookup of full names to abbreviations
from onlyinpgh.places import US_STATE_MAP
state_name_to_abbrev = {name:code for code,name in US_STATE_MAP}
 
def _resolve_result_to_place(result):
    '''
    Returns a tuple of Place, Factual GUID from a Resolve result
    '''
    resolved_loc = Location(
            country='US',           
            address=result.get('address',''),
            town=result.get('locality',''),
            state=result.get('region',''),
            postcode=result.get('postcode',''),
            latitude=result.get('latitude'),
            longitude=result.get('longitude'))
    
    return Place(name=result.get('name'),location=resolved_loc), result.get('factual_id')

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
        location = copy.deepcopy(seed_location)
    else:
        location = Location()
    location.address = address_text

    return resolve_location(location,allow_numberless)

#### Helper functions for processing raw address text in text_to_place
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

def text_to_place(address_text,fallback_place_name='',seed_location=None):
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
            l = copy.deepcopy(seed_location)
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
        resolvelog.debug("FULL STRING NAME: %s => %s" % (address_text,debug_place_print(result)))
        return result
    
    # 2: The first split field as the name
    result = _seeded_resolve(name=fields[0])
    if result: 
        resolvelog.debug("NAME: %s => %s" % (fields[0],debug_place_print(result)))
        return result

    # 3: First split field as the name, second as the address
    if len(fields) > 1:
        result = _seeded_resolve(name=fields[0],address=fields[1])
        if result: 
            resolvelog.debug("NAME & ADDRESS %s,%s => %s" % \
                                (fields[0],
                                 fields[1],
                                 debug_place_print(result)))
            return result

    # 4: First split as name, potential zip code (only if it exists)
    # (Potential zip code is more reliable than city/state. Try this alone before others.)
    if pot_postcode:
        result = _seeded_resolve(name=fields[0],postcode=pot_postcode)
        if result: 
            resolvelog.debug("NAME & POSTCODE %s,%s => %s" % \
                                (fields[0],
                                 pot_postcode,
                                 debug_place_print(result)))
            return result

    # 5: Now try all other potential fields (assuming a potential city was found)
    if pot_town:
        result = _seeded_resolve(name=fields[0],
                                    town=pot_town,
                                    state=pot_state,
                                    postcode=pot_postcode)
        if result: 
            resolvelog.debug("NAME, POSTCODE, TOWN, STATE %s,%s,%s,%s => %s" % \
                                (fields[0],
                                 pot_town,
                                 pot_state,
                                 pot_postcode,
                                 debug_place_print(result)))
            return result

    # 6: If parenthesized expression is in string, Try inside as address, outside as name and vice versa
    if outside:
        result = _seeded_resolve(name=outside,address=inside)
        if result: 
            resolvelog.debug("NAME (ADDRESS) %s (%s) => %s" % \
                                (outside,
                                inside,
                                debug_place_print(result)))
            return result
    if inside:
        result = _seeded_resolve(name=inside,address=outside)
        if result: 
            resolvelog.debug("ADDRESS (NAME) %s (%s) => %s" % \
                                (inside,
                                 outside,
                                 debug_place_print(result)))
            return result
            
    ### no resolve calls worked. falling back to geocoding
    
    # 1: Try geocoding the address part, with seed
    result = text_to_location(address_text,seed_location,allow_numberless=False)
    if result is not None:
        resolvelog.debug("[GEOCODED] FULL STRING: %s <seed %s> => %s" % \
                            (address_text,
                             debug_loc_print(seed_location),
                             debug_loc_print(result)))
        return Place(name='',location=result)

    # 2: Try geocoding the concatenation of split fields 2 through end
    #    If successful, use first field as place name
    if len(fields) > 1:
        result = text_to_location(','.join(fields[1:]),seed_location,allow_numberless=False)
        if result is not None:
            resolvelog.debug("[GEOCODED] TAIL CONCAT: %s <seed %s> => %s" % \
                                (','.join(fields[1:]),
                                 debug_loc_print(seed_location),
                                 debug_loc_print(result)))
            return Place(name=fields[0],location=result)

    # 3a: Try geocoding the inside, use outside as place on success
    if inside:        
        result = text_to_location(inside,seed_location,allow_numberless=False)
        if result is not None:
            resolvelog.debug("[GEOCODED] (ADDRESS): %s <seed %s> => %s" % \
                                (inside,
                                 debug_loc_print(seed_location),
                                 debug_loc_print(result)))
            return Place(name=outside,location=result)
    # 3b: Try geocoding the outside, use inside as place on success
    if outside:
        result = text_to_location(outside,seed_location,allow_numberless=False)
        if result is not None:
            resolvelog.debug("[GEOCODED] ADDRESS (...): %s <seed %s> => %s" % \
                                (outside,
                                 debug_loc_print(seed_location),
                                 debug_loc_print(result)))
            return Place(name=inside,location=result)
    
    # gnarly address, dude. return the fallback
    resolvelog.debug("[FAILURE] %s" % address_text)
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
                opts = copy.copy(search_opts)
                opts['q']=letter
                batch_commands.append(facebook.BatchCommand('search',options=opts))
            for response in facebook.oip_client.run_batch_request(batch_commands):
                pages_unfilitered.extend(response['data'])
        else:
            for letter in letters:
                pages_unfilitered.extend(facebook.oip_client.graph_api_collection_request('search',q=letter,**search_opts))
                  
        # need to go through the 26 separate page sets to filter out dups
        ids_seen = set()    # cache the ids in the list for a quick duplicate check
        pages = []
        for page in pages_unfilitered:
            if page['id'] not in ids_seen:
                ids_seen.add(page['id'])
                pages.append(page)
        return pages
    else:
        return facebook.oip_client.graph_api_collection_request('search',q=query,**search_opts)

# TODO: on the chopping block. once FB page creation manager is created, axe it
def get_full_place_pages(pids):
    '''
    Returns a list of full page information dicts, one per page id.
    '''
    page_details = []
    cmds = []
    def _add_batch(batch):
        responses = facebook.oip_client.run_batch_request(batch)
        page_details.extend([resp if resp and 'error' not in resp.keys() else None 
                                for resp in responses ])

    for pid in pids:
        cmds.append(facebook.BatchCommand(pid))
        if len(cmds) == 50:
            _add_batch(cmds)
            cmds = []
    if len(cmds) > 0:
        _add_batch(cmds)
    return page_details    

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

def debug_loc_print(l):
    return '%s, %s, %s %s (%.3f,%.3f)' % \
                (l.address,l.town,l.state,l.postcode,l.latitude or 0,l.longitude or 0)

def debug_place_print(place):
    return '%s: %s' % (place.name,debug_loc_print(place.location))

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
        url = page_info.get('link','http://www.facebook.com/%s'%pid)
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
        dbglog.info('Existing fb page Place found for fbid %s' % str(pid))
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
        dbglog.notice('Facebook page %s has id in location (%s)' % (pid,fbloc['id']))
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
        resolved_location = resolve_location(seed_loc)
        if resolved_location: 
            location = resolved_location

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
        dbglog.debug('Saved new location "%s"' % debug_loc_print(location))
    else:
        dbglog.debug('Retrieved existing location "%s"' % debug_loc_print(location))

    try:
        owner = FacebookOrgRecord.objects.get(page_fbid=pid).organization
    except FacebookOrgRecord.DoesNotExist:
        if create_owner:
            dbglog.info('Creating new Organization as byproduct of creating Place from Facebook page %s' % str(pid))
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

def create_place_from_fbpage(page_id):
    '''
    Polls given Facebook page id and creates a Place instance from it.
    '''
    page_info = facebook.oip_client.graph_api_page_request(page_id)
    return store_fbpage_place(page_info)

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
        ids = [page['id'] for page in gather_fb_place_pages(coords,25000)]
        all_ids.update(ids)
    return list(all_ids)
