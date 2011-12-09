'''
Module containing utilities that use external APIs to perform 
places-related tasks.
'''
from copy import deepcopy

from onlyinpgh.apitools import google
from onlyinpgh.apitools import factual
from onlyinpgh.places.models import Location

def resolve_place(partial_place=None,partial_location=None):
    '''
    Resolves a partial Place or Location object into a complete Place 
    using the Factual Resolve API. Returns None if resolution was not 
    possible.

    Exactly one of the arguments must be provided.
    '''
    # run a straightforward factual query on Place/Location.
    raise NotImplementedError

def resolve_location(partial_location):
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
    if not result:
        return None

    # convert geocoding result to Location
    geocode = result.get_geocoding()
    return Location(
        address = result.get_street_address(),
        postcode = result.get_postalcode(),
        town = result.get_town(),
        state = result.get_state(),
        country = result.get_country(),
        latitude = geocode[0],
        longitude = geocode[1]
    )

# can be a little more creative with address_text. Try simple
# query with name, maybe try address, splitting by comma, extracting
# zip, etc.
def text_to_place(address_text,seed_location=None):
    '''
    Attempts to resolve a raw text string into a Place using the Factual
    Resolve API. 

    If Location object is provided as seed_location Location, the completed
    fields from it are used as hints to help resolving. Note that if any of
    these "hints" are erroneous, resolution may fail since the Resolve API
    is fairly strict.

    Returns None if resolution was not possible. Can raise APIError if 
    critical error occurs.
    '''
    raise NotImplementedError

def text_to_location(address_text,seed_location=None):
    '''
    Attempts to resolve a raw text string into a Location using the Google
    Geocoding API.

    If Location object is provided as seed_location Location, the completed
    fields from it are used as hints to help resolving. These hints are more
    forgiving than those used in the Resolve API. Note that the Location's 
    address field will have no bearing on the results.

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

    return resolve_location(location)

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