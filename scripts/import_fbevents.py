from onlyinpgh.outsourcing.fbevents import EventImportManager, EventImportReport
from onlyinpgh.outsourcing.models import FacebookOrgRecord

import logging
importlog = logging.getLogger('onlyinpgh.fb_import')

from datetime import datetime
from itertools import izip

def import_by_pageids(page_ids,start_filter=None):
    event_mgr = EventImportManager()
    importlog.info('Searching %d pages for events.' % len(page_ids))
    event_mgr.pull_event_info_from_pages(page_ids)

    import_count = 0
    for page_id in page_ids:
        reports = event_mgr.import_events_from_page(page_id,start_filter)
        if len(reports):
            importlog.info('Importing events for Facebook page %s' % page_id)
        for report in reports:
            if report.notices:
                for notice in report.notices:
                    if isinstance(notice,EventImportReport.EventInstanceExists):
                        importlog.info('%s: Record for Event exists' % report.fbevent_id)
                    else:
                        importlog.error('%s: %s' % (report.fbevent_id,unicode(notice)))
            else:
                importlog.info('%s: Imported successfully as %s' % (report.fbevent_id,unicode(report.event_instance)))
                import_count += 1
    importlog.info('Imported %d new Events' % import_count)

def import_all(start_filter=None):
    page_ids = [obj.fb_id for obj in FacebookOrgRecord.objects.filter(ignore=False)]
    import_by_pageids(page_ids,start_filter)

def run():
    import_all(datetime(2011,12,1))