from onlyinpgh.outsourcing.apitools import facebook_client
from onlyinpgh.outsourcing.models import FacebookEventRecord

def run():
	records = FacebookEventRecord.objects.filter(ignore=False,event__image_url='')
	
	for i,record in enumerate(records):
		try:
			pic = facebook_client.graph_api_picture_request(record.fb_id)
		except IOError as e:
			outsourcing_log.error('Error retreiving picture for event %s: %s' % (unicode(eid),unicode(e)))
			pic = ''
		record.event.image_url = pic
		record.event.save()
		if (i+1)%100 == 0:
			print i