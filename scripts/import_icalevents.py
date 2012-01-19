from onlyinpgh.outsourcing.models import ICalendarFeed
from onlyinpgh.outsourcing.icalevents import FeedImporter, EventImportReport

from datetime import datetime

import logging
importlog = logging.getLogger('onlyinpgh.ical_import')

def import_all():
    feeds = ICalendarFeed.objects.all()
    
    importlog.info('Reading %d feeds for Event importing' % len(feeds))
    
    for feed in feeds:
        import_count = 0
        importlog.info('Processing new events from feed "%s"' % (unicode(feed)))
        importer = FeedImporter(feed)
        for report in importer.import_new(start_filter=datetime(2012,1,1)):
            if not report:
                importlog.error(u'UID %s: Unexpected failure' % record.uid)
                continue
            record = report.vevent_record
            if record.event:
                importlog.info(u'UID %s: Imported new event, id=%s' % (record.uid,record.event.id))
                # increment the counter for every new event added
                if len([1 for n in report.notices 
                        if isinstance(n,EventImportReport.RecordExists)]) == 0:
                    import_count += 1
            else:
                importlog.warning(u'UID %s: Event import failed due to a problem with the feed entry.' % report.uid)
            for notice in report.notices:
                importlog.info(u'UID %s: Report status notice: %s' % (record.uid,notice))
            
        importlog.info('%d new Events imported from feed "%s"' % (import_count,unicode(feed)))

def run():
    try:
        # TODO: have import_all return VEvents, not Events
        importlog.info('Event import start')
        import_all()
        importlog.info('Event import complete')
    except Exception as e:
        importlog.critical('Unexpected error: %s' % str(e))