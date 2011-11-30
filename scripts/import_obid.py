import csv, time, os

from places.models import Establishment, Location
from places.external import LocationValidator, LocationValidationError
from identity.models import Organization, Identity

def run():
    in_filename = os.path.join(os.path.dirname(__file__),'obid.csv')
    err_filename = os.path.join(os.path.dirname(__file__),'errors.csv')

    #clear all tables
    Location.objects.all().delete()
    Establishment.objects.all().delete()
    Identity.objects.all().delete()
    Organization.objects.all().delete()

    validator = LocationValidator('GG')
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
                org_str, estab_str, loc_str = row[1:4]
                if len(row) > 4:
                    phone = row[4]
                else:
                    phone = ''
                if len(row) > 5:
                    url = row[5]
                else:
                    url = ''

                if org_str == '':
                    if estab_str == '':
                        writer.writerow(row)
                        continue
                    else:
                        org_str = estab_str

                try:
                    time.sleep(.2)
                    location = validator.resolve_full(Location(address=loc_str,postcode='15213'))
                except LocationValidationError:
                    writer.writerow(row)
                    continue
                
                try:
                    # if exact match exists, use it instead of the newly found one
                    location = Location.objects.get(address=location.address,postcode=location.postcode)
                except Location.DoesNotExist:
                    location.save()

                identity,_ = Identity.objects.get_or_create(display_name=org_str)
                org,_ = Organization.objects.get_or_create(identity=identity)
                
                try:
                    estab = Establishment.objects.get(owner=org,name=estab_str,location=location)
                except Establishment.DoesNotExist:
                    estab = Establishment.objects.create(owner=org,name=estab_str,location=location,phone_number=phone,url=url)

