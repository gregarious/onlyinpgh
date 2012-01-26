import csv, time, os, re, json

from onlyinpgh.places.models import Location, Place, Meta as PlaceMeta
from onlyinpgh.outsourcing.places import resolve_location
from onlyinpgh.identity.models import Organization
from onlyinpgh.outsourcing.models import ExternalPlaceSource, FacebookPage, FacebookOrgRecord
from onlyinpgh.outsourcing.fbpages import PageImportManager
from onlyinpgh.tagging.categories import load_category_map
from onlyinpgh.outsourcing.apitools import gplaces_client
# from onlyinpgh.outsourcing.apitools.facebook import oip_client as fb_client

def add_from_facebook(fb_id,place,import_org=True):
    assert fb_id and place
    fb_mgr.import_orgs([fb_id])

    # manually hook up the place page
    ExternalPlaceSource.objects.create(service='fb',uid=fb_id,place=place)

class OBIDRow:
    def __init__(self,fields):
        '''
        The following structure is assumed for the fields
        [owner,place,address,phone,url,?,fbid]
        '''
        # ensure each row is at least 6 fields long (fill with blanks if not)
        if len(fields) < 6:
            fields.extend(['']*(7-len(fields)))

        self.org =      fields[0].strip()
        self.place =    fields[1].strip()
        self.address =  fields[2].strip()
        self.phone =    fields[3].strip()
        self.url =      fields[4].strip()
        # [5] is ignored
        self.fb_id =    fields[6].strip()
    
    @classmethod
    def rows_from_csv(cls,csv_filename,has_header=False):
        '''
        Returns a list of OBIDRow objects from a csv file.
        '''
        with open(csv_filename) as f:
            reader = csv.reader(f)
            return [OBIDRow(row) for row in reader]

def run():
    in_filename = os.path.join(os.path.dirname(__file__),'obid.csv')

    #clear all tables
    Location.objects.all().delete()
    PlaceMeta.objects.all().delete()
    Place.objects.all().delete()
    Organization.objects.all().delete()
    ExternalPlaceSource.objects.all().delete()
    FacebookPage.objects.all().delete()
    FacebookOrgRecord.objects.all().delete()

    gplaces_category_map = load_category_map('google_places')
    gp_hits, gp_misses = 0,0

    rows = OBIDRow.rows_from_csv(in_filename)
    
    # cycle through each row with a facebook reference and store a reference
    page_mgr = PageImportManager()
    fb_rows = [row for row in rows if row.fb_id]
    for row,info in zip(fb_rows,page_mgr.pull_page_info([row.fb_id for row in fb_rows])):
        if isinstance(info,dict):
            info.pop('metadata',None)       # don't need to store metadata if it exists
            FacebookPage.objects.get_or_create(fb_id=info['id'],
                                        defaults=dict(pageinfo_json=json.dumps(info)))
            row.fb_id = info['id']  # ensure a numeric id
        else:
            print 'ERROR: Pulling fb page %s resulted in the following exception: "%s"' % (str(row.fb_id),str(info))
            row.fb_id = ''

    # cycle through all rows and store everything
    for i,row in enumerate(rows):
        if not row.place:
            print 'ERROR: no place for entry %d' % i
        
        # resolve the location
        location = resolve_location(Location(address=row.address,postcode='15213'))

        if location:
            # hack to get around Google Geocoding appending the unviersity onto all addresses
            if ( location.address.startswith('University') and not row.address.lower().startswith('univ') ) or \
               ( location.address.startswith('Carnegie Mellon') and row.address.lower().startswith('carnegie mellon') ):
               location.address = ','.join(location.address.split(',')[1:])

            try:
                # if exact match exists, use it instead of the newly found one
                location = Location.objects.get(address=location.address,postcode=location.postcode)
            except Location.DoesNotExist:
                location.save()
        else:
            print 'WARNING: Geocoding failed for entry %d ("%s")' % (i,row.place)

        diff_org = row.org != row.place
        org, place = None, None

        # import org
        # if the row has a fb id, we'll try to import the Org from Facebook
        # only import Org from Facebook if it's the same as the Place (fb id relates to place only)
        if row.fb_id and not diff_org:
            try:
                org = FacebookOrgRecord.objects.get(fb_id=row.fb_id)
            except FacebookOrgRecord.DoesNotExist:
                report = page_mgr.import_org(row.fb_id)
                if report.model_instance:
                    org = report.model_instance
                else:
                    print 'WARNING: Organization FB import failed for entry %d (fbid %s)' % (i,str(row.fb_id))

        if not org:
            org,created = Organization.objects.get_or_create(name=row.org)

        # import place
        if row.fb_id:
            try:
                place = ExternalPlaceSource.facebook.get(uid=row.fb_id)
            except ExternalPlaceSource.DoesNotExist:
                report = page_mgr.import_place(row.fb_id,import_owners=False)
                if report.model_instance:
                    place = report.model_instance
                    if not place.owner:     # no owner is created automatically, so set it if not created
                        place.owner = org
                        place.save()
                else:
                    print 'WARNING: Place FB import failed for entry %d (fbid %s)' % (i,str(row.fb_id))
        
        if not place:
            place,created = Place.objects.get_or_create(name=row.place,location=location,owner=org)
        
        if row.url:
            PlaceMeta.objects.create(place=place,meta_key='url',meta_value=row.url)
            if not diff_org:    # also save the url as the org's url if they're the same
                org.url = row.url
                org.save()

        if row.phone:
            PlaceMeta.objects.create(place=place,meta_key='phone',meta_value=row.phone)

        print 'Imported %s' % row.place
        try:
            print '  (linked to FB page %s)' % ExternalPlaceSource.facebook.get(place=place).uid
        except ExternalPlaceSource.DoesNotExist:
            pass

        # store tags from Google Place lookup
        if location and \
            location.latitude is not None and location.longitude is not None:
            coords = (location.latitude,location.longitude)
            radius = 1000
        else:
            coords = (40.4425,-79.9575)
            radius = 5000

        response = gplaces_client.search_request(coords,radius,keyword=row.place)

        if len(response) > 0 and 'reference' in response[0]:
            details = gplaces_client.details_request(response[0]['reference'])
            all_tags = set()
            for typ in details.get('types',[]):
                if typ in gplaces_category_map:
                    all_tags.update(gplaces_category_map[typ])
                else:
                    print 'WARNING: Unknown Google Places type: "%s"' % typ
            if len(all_tags) > 0:
                print '  Tags:',
                for t in all_tags:
                    print '%s,' % t,
                print
            gp_hits += 1
        else:
            print '  WARNING: Failure querying Google Places for "%s" within %dm of (%f,%f)' % (row.place,radius,coords[0],coords[1])
            gp_misses += 1
    print gp_hits, gp_misses