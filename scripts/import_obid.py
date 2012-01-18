import csv, time, os, re

from onlyinpgh.places.models import Location, Place, Meta as PlaceMeta
from onlyinpgh.outsourcing.places import resolve_location
from onlyinpgh.identity.models import Organization
from onlyinpgh.outsourcing.models import ExternalPlaceSource
from onlyinpgh.outsourcing.fbpages import PageImportManager
from onlyinpgh.outsourcing.apitools.facebook import oip_client as fb_client

fb_mgr = PageImportManager()

def add_from_facebook(fb_id,place,import_org=True):
    assert fb_id and place
    fb_mgr.import_orgs([fb_id])

    # manually hook up the place page
    ExternalPlaceSource.objects.create(service='fb',uid=fb_id,place=place)

def run():
    in_filename = os.path.join(os.path.dirname(__file__),'obid.csv')
    err_filename = os.path.join(os.path.dirname(__file__),'errors.csv')

    #clear all tables
    Location.objects.all().delete()
    PlaceMeta.objects.all().delete()
    Place.objects.all().delete()
    Organization.objects.all().delete()
    ExternalPlaceSource.objects.all().delete()

    with open(err_filename,'w') as err_f:
        writer = csv.writer(err_f)
        with open(in_filename) as f:
            num_rows = len(f.readlines())
            f.seek(0)
            reader = csv.reader(f)
            reader.next()        # throw away header
            for i,row in enumerate(reader):
                if i % 50 == 1:
                    print 'row %d of %d completed' % (i,num_rows)
                # ensure each row is at least 6 fields long
                if len(row) < 6:
                    row.extend(['']*(7-len(row)))
                org_str, place_str, loc_str, phone, url, _, fb_id = [x.strip() for x in row[:7]]

                if org_str == '':
                    if place_str == '':
                        writer.writerow(row)
                        continue
                    else:
                        org_str = place_str

                location = resolve_location(Location(address=loc_str,postcode='15213'))
                if location and ( location.address.startswith('University') and not loc_str.lower().startswith('univ') ) or \
                                ( location.address.startswith('Carnegie Mellon') and loc_str.lower().startswith('carnegie mellon') ):
                    location.address = ','.join(location.address.split(',')[1:])

                if location:
                    try:
                        # if exact match exists, use it instead of the newly found one
                        location = Location.objects.get(address=location.address,postcode=location.postcode)
                    except Location.DoesNotExist:
                        location.save()
                else:
                    print 'WARNING: Geocoding failed for %s' % loc_str

                org,created = Organization.objects.get_or_create(name=org_str)
                if created:
                    if org_str == place_str and url:
                        org.url = url
                        org.save()
                    if fb_id:
                        fb_mgr.import_orgs([fb_id])

                
                place,created = Place.objects.get_or_create(name=place_str,location=location,owner=org)
                if not created:
                    raise Exception('%s already exists?' % str(place))
                print 'inserted',place

                if url:
                    PlaceMeta.objects.create(place=place,meta_key='url',meta_value=url)
                if phone:
                    PlaceMeta.objects.create(place=place,meta_key='phone',meta_value=phone)
                if fb_id:
                    save_facebook_ref(fb_id,place)