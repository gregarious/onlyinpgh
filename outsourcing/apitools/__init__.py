import urllib2, time
from urlparse import urlparse, parse_qsl

import oauth

class APIError(IOError):
    def __init__(self,api_name,*args):
        self.api = api_name
        super(APIError,self).__init__(*args)

def build_oauth_request(url,key,secret):
    '''
    Returns an oauth signed urllib2.Request object
    '''
    params    = parse_qsl(urlparse(url).query)
    consumer  = oauth.OAuthConsumer(key=key, secret=secret)
    request   = oauth.OAuthRequest.from_consumer_and_token(consumer, http_method='GET', http_url=url, parameters=params)

    request.sign_request(oauth.OAuthSignatureMethod_HMAC_SHA1(), consumer, None)

    return urllib2.Request(url, None, request.to_header())

def delayed_retry_on_ioerror(apicall,delay_seconds,retry_limit=1,logger=None):
    '''
    Function designed to automatically reattempt a function call on the
    event that it returns an IOError. Each reattempt is preceded by a
    sleep count. The delay time will be doubled each retry.

    This is a convenient way to avoid the common pattern of causing a 
    delayed-retry when an API service denies access momentarily because
    of throttling concerns.
    '''
    retry_count = 0
    while True:
        try:
            return apicall()
        except IOError as e:
            # we're out of retries -- just raise the error
            if retry_count >= retry_limit:
                raise
            retry_count += 1
            if logger:
                logger.info(u'IOError "%s": Will attempt retry %d (of %d max) in %d secs...' %\
                    (unicode(e),
                    retry_count,
                    retry_limit,
                    delay_seconds))
            time.sleep(delay_seconds)
            delay_seconds *= 2
            
import google
import facebook
import factual

geocoding_client = google.GoogleGeocodingClient()
gplaces_client = google.GooglePlacesClient(google.OIP_PLACES_ACCESS_TOKEN)
facebook_client = facebook.GraphAPIClient(facebook.OIP_ACCESS_TOKEN)
factual_client = factual.FactualClient(factual.OIP_OAUTH_KEY,factual.OIP_OAUTH_SECRET)