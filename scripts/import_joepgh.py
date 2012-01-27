from onlyinpgh.identity.models import Organization
from onlyinpgh.outsourcing.models import FacebookEventRecord
from onlyinpgh.events.models import Role

import re, urllib
from datetime import datetime

from onlyinpgh.outsourcing.fbevents import EventImportManager, EventImportReport

import logging
importlog = logging.getLogger('onlyinpgh.fb_import')

def import_all():
    ical_url = 'http://www.facebook.com/ical/u.php?uid=100002229140530&key=AQAInfO7K7HJekoR'
    ical = urllib.urlopen(ical_url).read()

    pattern = re.escape('URL:http') + 's?' + re.escape('://www.facebook.com/events/') + '(\d+)'
    fbevent_ids = re.findall(pattern,ical)

    joepgh, _ = Organization.objects.get_or_create(name="Individuals on Facebook",
                                                url="http://www.facebook.com/profile.php?id=100002229140530")

    importlog.info('Importing %d JoePgh events' % len(fbevent_ids))
    mgr = EventImportManager()
    mgr.pull_event_info(fbevent_ids)
    for fbid in fbevent_ids:
        report = mgr.import_event(fbid,import_owners=False)
        if report.notices:
            for notice in report.notices:
                if isinstance(notice,EventImportReport.EventInstanceExists):
                    pass
                    #importlog.info('%s: Record for Event exists' % report.fbevent_id)
                else:
                    importlog.error('%s: %s' % (report.fbevent_id,unicode(notice)))
        else:
            importlog.info('%s: Imported successfully as %s' % (report.fbevent_id,unicode(report.event_instance)))
            # set the hosting organization manually to joepgh
            Role.objects.get_or_create(event=report.event_instance,
                                        role_type='host',
                                        defaults={'organization':joepgh})

def run():
    try:
        importlog.info('Org/Place import start')
        import_all()
        importlog.info('Org/Place import complete')
    except Exception as e:
        importlog.critical('Unexpected error: %s' % str(e))