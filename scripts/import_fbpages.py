import logging
from onlyinpgh.settings import to_abspath

from onlyinpgh.outsourcing.fbpages import gather_fb_place_pages, PageImportManager, PageImportReport
from onlyinpgh.outsourcing.fbevents import EventImportManager

importlog = logging.getLogger('onlyinpgh.fb_import')

def import_pages():
    search_coords = [ (40.44181,-80.01277),
                  (40.666667,-79.700556),
                  (40.666667,-80.308056),
                  (40.216944,-79.700556),
                  (40.216944,-80.308056),
                  (40.44181,-80.01277),
                ]
    radius = 25000
    all_ids = set()
    for coords in search_coords:
        lat,lng = coords
        importlog.info('Searching for all events within %dm of (%.3f,%.3f)' % (radius,lat,lng))
        try:
            page_stubs = gather_fb_place_pages(coords,radius,batch_requests=False)
        except Exception as e:
            importlog.error('Failure searching region (%.3f,%.3f): %s' % (lat,lng,str(e)))
            continue

        orig_count = len(all_ids)
        all_ids.update([stub['id'] for stub in page_stubs])
        new_count = len(all_ids) - orig_count
        importlog.info('Found %d pages (%d new).' % (len(page_stubs), new_count))
    
    importlog.info('Importing Organizations into database from %d pages' % len(all_ids))

    page_mgr = PageImportManager()

    reports = page_mgr.import_orgs(all_ids)    # generator object
    for report in reports:
        if report.notices:
            for notice in report.notices:
                if isinstance(notice,PageImportReport.ModelInstanceExists):
                    importlog.info('%s: Record for Organization exists' % report.page_id)
                else:
                    importlog.error('%s: %s' % (report.page_id,unicode(notice)))
        else:
            importlog.info('%s: Imported successfully as %s' % (report.page_id,unicode(report.model_instance)))

    reports = page_mgr.import_places(all_ids,import_owners=True)    # generator object
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
    try:
        importlog.info('Page import start')
        import_pages()
        importlog.info('Page import complete')
    except Exception as e:
        importlog.critical('Unexpected error: %s' % str(e))