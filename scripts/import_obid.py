import csv, time, os

from onlyinpgh.places.models import Location, Place, Meta as PlaceMeta
from onlyinpgh.outsourcing.places import resolve_location
from onlyinpgh.identity.models import Organization

def run():
    in_filename = os.path.join(os.path.dirname(__file__),'obid.csv')
    err_filename = os.path.join(os.path.dirname(__file__),'errors.csv')

    #clear all tables
    Location.objects.all().delete()
    PlaceMeta.objects.all().delete()
    Place.objects.all().delete()
    Organization.objects.all().delete()

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
                try:
                    org_str, place_str, loc_str = map(unicode,row[1:4])
                except UnicodeDecodeError:
                    writer.writerow(row)
                    continue

                if len(row) > 4:
                    phone = row[4]
                else:
                    phone = ''
                if len(row) > 5:
                    url = row[5]
                else:
                    url = ''

                if org_str == '':
                    if place_str == '':
                        writer.writerow(row)
                        continue
                    else:
                        org_str = place_str

                time.sleep(.1)
                location = resolve_location(Location(address=loc_str,postcode='15213'))
                if not location:
                    writer.writerow(row)
                    continue
                elif ( location.address.startswith('University') and not loc_str.lower().startswith('univ') ) or \
                     ( location.address.startswith('Carnegie Mellon') and loc_str.lower().startswith('carnegie mellon') ):
                    location.address = ','.join(location.address.split(',')[1:])

                try:
                    # if exact match exists, use it instead of the newly found one
                    location = Location.objects.get(address=location.address,postcode=location.postcode)
                except Location.DoesNotExist:
                    location.save()

                org,created = Organization.objects.get_or_create(name=org_str)
                if not created:
                    print '%s already exists' % org
                
                place,created = Place.objects.get_or_create(name=place_str,location=location,owner=org)
                if not created:
                    raise Exception('%s already exists?' % str(place))
                print 'inserted',unicode(place)

                if url:
                    PlaceMeta.objects.create(place=place,meta_key='url',meta_value=url)
                    PlaceMeta.objects.create(place=place,meta_key='phone',meta_value=phone)
