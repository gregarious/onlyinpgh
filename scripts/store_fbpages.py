from onlyinpgh.outsourcing.models import FacebookPage
from onlyinpgh.outsourcing.fbpages import gather_fb_place_pages
from onlyinpgh.outsourcing.apitools.facebook import FacebookAPIError

import logging
importlog = logging.getLogger('onlyinpgh.fb_import')

def store_pages(coords,radius,infinite_attempts=False):
    '''
    If infinite_attempts is True, any call to gather_fb_place_pages that 
    fails with a FacebookAPIError will be re-run indefinitely. These calls
    tend to fail a lot.
    '''
    page_stubs = []
    # manually cycle through the letters. gather_fb_place_pages will do this too, but one failure will ruin the whole lot
    for letter in [chr(o) for o in range(ord('a'),ord('z')+1)]:
        importlog.info('Query: %s' % letter)
        try_again = True
        while try_again:
            try:
                page_stubs.extend(gather_fb_place_pages(coords,radius,query=letter,batch_requests=False))
                try_again = False  
            except FacebookAPIError as e:
                if infinite_attempts:
                    importlog.error('API Error: "%s". Trying again.' % str(e))
                else:
                    raise

    page_ids = [stub['id'] for stub in page_stubs]
    page_ids = list(set(page_ids))
    importlog.info('Found %d pages.' % len(page_ids))
    
    total_created = 0
    for pid in page_ids:
        _, created = FacebookPage.objects.get_or_create(fb_id=pid)
        total_created += int(created)

    importlog.info('%d new page IDs stored.' % total_created)

def run():
    search_coords = [ (40.44181,-80.01277),
                      (40.666667,-79.700556),
                      (40.666667,-80.308056),
                      (40.216944,-79.700556),
                      (40.216944,-80.308056),
        ]
    radius = 25000
    
    try:
        importlog.info('Page import start')
        for coords in search_coords:
            lat,lng = coords
            importlog.info('Searching for all pages within %dm of (%.3f,%.3f)' % (radius,lat,lng))
            store_pages(coords,radius,infinite_attempts=False)
        importlog.info('Page import complete')
    except Exception as e:
        importlog.critical('Failure searching region (%.3f,%.3f): %s. Aborting.' % (lat,lng,str(e)))
