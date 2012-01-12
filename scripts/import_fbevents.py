from onlyinpgh.outsourcing.fbevents import EventImportManager, EventImportReport
from onlyinpgh.outsourcing.models import FacebookOrgRecord

import logging
importlog = logging.getLogger('onlyinpgh.fb_import')

from datetime import datetime

def import_events(start_filter=None)
    page_ids = [obj.fb_id for obj in FacebookOrgRecord.objects.all()]
    page_ids = page_ids[:10]

    event_mgr = EventImportManager()
    reports_by_page = event_mg.import_events_from_pages(page_ids,start_filter)

    for page_id,reports in zip(page_ids,reports_by_page):
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

def run():
    import_events(datetime(2011,12,1))