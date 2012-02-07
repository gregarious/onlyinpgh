'''
Temporary script: will import orgs/places/events from any FB id. However, requires hardcoded
values since ./manage runscript doesn't allow arguments.
'''

from onlyinpgh.outsourcing.models import FacebookPage
from datetime import datetime

import import_fbpages
import import_fbevents

page_ids = []		# set ids here for each new run
start_filter = datetime(2011,12,1)

def run():
	for page_id in page_ids:
		FacebookPage.objects.get_or_create(fb_id=page_id)
	import_fbpages.import_ids(page_ids)
	import_fbevents.import_by_pageids(page_ids,start_filter=start_filter)
