'''
Module containing utilities that use external APIs to perform 
places-related tasks.
'''

from itertools import chain
import re, copy

from onlyinpgh.outsourcing.apitools.factual import FactualAPIError
from onlyinpgh.outsourcing.apitools import geocoding_client, factual_client
from onlyinpgh.places.models import Place, Location

import logging  
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
            address=result.get('address','').strip(),
            town=result.get('locality','').strip(),
            state=result.get('region','').strip(),
            postcode=result.get('postcode','').strip(),
            latitude=result.get('latitude'),
            longitude=result.get('longitude'))
    
    return Place(name=result.get('name'),location=resolved_loc)

def _geocode_result_to_location(result):
    coords = result.get_geocoding()
    return Location(
        address = result.get_street_address().strip(),
        postcode = result.get_postalcode().strip(),
        town = result.get_town().strip(),
        state = result.get_state().strip(),
        country = result.get_country().strip(),
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

    try:
        if loc is None:
            resp = factual_client.resolve(name=pl_name)
        else:
            resp = factual_client.resolve(
                name=pl_name,
                address=loc.address,
                town=loc.town,
                state=loc.state,
                postcode=loc.postcode,
                latitude=loc.latitude,
                longitude=loc.longitude)
    except FactualAPIError:
        return None

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
    response = geocoding_client.run_geocode_request(address_text,**biasing_args)
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

#### Helper functions for processing raw address text in smart_text_resolve
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
    Returns a dict of various values used in smart_text_resolve to help
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

class SmartTextResolveResult():
    parse_statuses = [
        'RESOLVED_FULL_STRING',
        'RESOLVED_FIELD0_NAME',
        'RESOLVED_FIELD0_NAME_FIELD1_ADDRESS',
        'RESOLVED_FIELD0_NAME_POSTCODE',
        'RESOLVED_FIELD0_NAME_TOWN_POSTCODE',
        'RESOLVED_OUT_NAME_IN_ADDRESS',
        'RESOLVED_IN_NAME_OUT_ADDRESS',
        'GEOCODED_FULL_STRING',
        'GEOCODED_FIELD0_EXCLUDED',
        'GEOCODED_IN_PARENTHESIS',
        'GEOCODED_OUT_PARENTHESIS',
        'FAILURE'
    ]
    parse_status_priorities = dict(zip(parse_statuses,
                                        range(len(parse_statuses))))

    def __init__(self,text,parse_status,place=None,location=None):
        self.text = text
        self.parse_status = parse_status
        self.location = location
        self.place = place


def smart_text_resolve(address_text,seed_location=None):
    '''
    Attempts to resolve a raw text string into a Place or Location using
    a series of strategies. Returns a TextResolveResult object which 
    contains the resulting place/location as well as a code for the 
    parsing strategy used.

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
        return SmartTextResolveResult(address_text,'FAILURE')
    
    # parse out various fields of interest 
    parsed_content = _parse_raw_address(address_text) 

    fields = parsed_content['all_fields']
    inside = parsed_content.get('paren_inside')
    outside = parsed_content.get('paren_outside')
    pot_town = parsed_content.get('potential_town')
    pot_state = parsed_content.get('potential_state')
    pot_postcode = parsed_content.get('potential_postcode')

    # helper to call resolve_place with a newly constructed partial place
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
    
    ### Resolve API battery
    # 1: First try first field as the name, second as address
    if len(fields) > 1:
        result = _seeded_resolve(name=fields[0],address=fields[1])
        if result: 
            return SmartTextResolveResult(address_text,'RESOLVED_FIELD0_NAME_FIELD1_ADDRESS',place=result)

    # 2: Try the whole string as the name
    result = _seeded_resolve(name=address_text)
    if result:
        return SmartTextResolveResult(address_text,'RESOLVED_FULL_STRING',place=result)
    
    # 2: The first split field as the name
    result = _seeded_resolve(name=fields[0])
    if result: 
        return SmartTextResolveResult(address_text,'RESOLVED_FIELD0_NAME',place=result)

    # 4: First split as name, potential zip code (only if it exists)
    # (Potential zip code is more reliable than city/state. Try this alone before others.)
    if pot_postcode:
        result = _seeded_resolve(name=fields[0],postcode=pot_postcode)
        if result: 
            return SmartTextResolveResult(address_text,'RESOLVED_FIELD0_NAME_POSTCODE',place=result)

    # 5: Now try all other potential fields (assuming a potential city was found)
    if pot_town:
        result = _seeded_resolve(name=fields[0],
                                    town=pot_town,
                                    state=pot_state,
                                    postcode=pot_postcode)
        if result: 
            return SmartTextResolveResult(address_text,'RESOLVED_FIELD0_NAME_TOWN_POSTCODE',place=result)

    # 6: If parenthesized expression is in string, Try inside as address, outside as name and vice versa
    if outside:
        result = _seeded_resolve(name=outside,address=inside)
        if result: 
            return SmartTextResolveResult(address_text,'RESOLVED_OUT_NAME_IN_ADDRESS',place=result)

    if inside:
        result = _seeded_resolve(name=inside,address=outside)
        if result: 
            return SmartTextResolveResult(address_text,'RESOLVED_IN_NAME_OUT_ADDRESS',place=result)

            
    ### no resolve calls worked. falling back to geocoding
    
    # 1: Try geocoding the address part, with seed
    result = text_to_location(address_text,seed_location,allow_numberless=False)
    if result is not None:
        return SmartTextResolveResult(address_text,'GEOCODED_FULL_STRING',location=result)

    # 2: Try geocoding the concatenation of split fields 2 through end
    #    If successful, use first field as place name
    if len(fields) > 1:
        result = text_to_location(','.join(fields[1:]),seed_location,allow_numberless=False)
        if result is not None:
            return SmartTextResolveResult(address_text,'GEOCODED_FIELD0_EXCLUDED',location=result)

    # 3a: Try geocoding the inside, use outside as place on success
    if inside:        
        result = text_to_location(inside,seed_location,allow_numberless=False)
        if result is not None:
            return SmartTextResolveResult(address_text,'GEOCODED_IN_PARENTHESIS',location=result)

    # 3b: Try geocoding the outside, use inside as place on success
    if outside:
        result = text_to_location(outside,seed_location,allow_numberless=False)
        if result is not None:
            return SmartTextResolveResult(address_text,'GEOCODED_OUT_PARENTHESIS',location=result)
    
    # gnarly address, dude. return the fallback
    return SmartTextResolveResult(address_text,'FAILURE')

def normalize_street_address(address_text):
    '''
    Given a free-formed address in a string, returns the normalized street
    address portion of a result obtained by Google Geocoding API.

    Including additional address information (e.g. city, zip code) is useful
    for the API query, but will the information will not be included in
    the result.

    Returns None if normalization was not possible.
    '''
    response = geocoding_client.run_geocode_request(address_text)
    result = response.best_result(wrapped=True)
    # TODO: add ambiguous result handling
    if not result:
        return None
    return result.get_street_address()