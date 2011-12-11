'''
Module containing utilities that use external APIs to perform 
places-related tasks.
'''
from copy import deepcopy
from itertools import chain

from onlyinpgh.apitools import google
from onlyinpgh.apitools import factual
from onlyinpgh.places.models import Location, Place

import re, time

def _resolve_result_to_place(result):
    resolved_loc = Location(
            country='US',           
            address=result.get('address'),
            town=result.get('locality'),
            state=result.get('region'),
            postcode=result.get('postcode'),
            latitude=result.get('latitude'),
            longitude=result.get('longitude'))
    
    return Place(name=result.get('name'),
                    location=resolved_loc,
                    url=result.get('website'))

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

    time.sleep(1)   # TODO: remove
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
    time.sleep(1)   # TODO: remove
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

# TODO: consider geocoding notice handling here