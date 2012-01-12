from onlyinpgh.outsourcing.fbpages import gather_fb_place_pages, PageImportManager, PageImportReport
from onlyinpgh.outsourcing.fbevents import EventImportManager

import logging
importlog = logging.getLogger('onlyinpgh.fb_import')

def import_pages(coords,radius):
    try:
        page_stubs = gather_fb_place_pages(coords,radius,batch_requests=False)
    except Exception as e:
        importlog.error('Failure searching region (%.3f,%.3f): %s' % (lat,lng,str(e)))
        return

    page_ids = [stub['id'] for stub in page_stubs]
    importlog.info('Found %d pages.' % len(page_ids))
    
    importlog.info('Importing Organizations into database from %d pages' % len(page_ids))
    page_mgr = PageImportManager()
    reports = page_mgr.import_orgs(page_ids)    # generator object
    for report in reports:
        if report.notices:
            for notice in report.notices:
                if isinstance(notice,PageImportReport.ModelInstanceExists):
                    importlog.info('%s: Record for Organization exists' % report.page_id)
                else:
                    importlog.error('%s: %s' % (report.page_id,unicode(notice)))
        else:
            importlog.info('%s: Imported successfully as %s' % (report.page_id,unicode(report.model_instance)))

    reports = page_mgr.import_places(page_ids,import_owners=True)    # generator object
    for report in reports:
        if report.notices:
            for notice in report.notices:
                if isinstance(notice,PageImportReport.ModelInstanceExists):
                    importlog.info('%s: Record for Place exists' % report.page_id)
                else:
                    importlog.error('%s: %s' % (report.page_id,unicode(notice)))
        else:
            importlog.info('%s: Imported successfully as %s' % (report.page_id,unicode(report.model_instance)))

def import_events():
    pass

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
            import_pages(coords,radius)
        importlog.info('Page import complete')
    except Exception as e:
        importlog.critical('Unexpected error: %s' % str(e))