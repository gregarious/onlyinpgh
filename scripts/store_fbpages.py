from onlyinpgh.outsourcing.models import FacebookPage
from onlyinpgh.outsourcing.fbpages import gather_fb_place_pages

import logging
importlog = logging.getLogger('onlyinpgh.fb_import')

def store_pages(coords,radius):
    page_stubs = gather_fb_place_pages(coords,radius,batch_requests=False)
    
    page_ids = [stub['id'] for stub in page_stubs]
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
    radius = 1000   #25000

    try:
        importlog.info('Page import start')
        for coords in search_coords:
            lat,lng = coords
            importlog.info('Searching for all pages within %dm of (%.3f,%.3f)' % (radius,lat,lng))
            store_pages(coords,radius)
        importlog.info('Page import complete')
    except Exception as e:
        importlog.error('Failure searching region (%.3f,%.3f): %s. Aborting.' % (lat,lng,str(e)))
