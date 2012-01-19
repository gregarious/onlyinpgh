from django.shortcuts import render_to_response
from onlyinpgh.places.models import Place, Meta as PlaceMeta

subset_names = [
    "3 Guys Optical Center",
    "Antoon's Pizza",
    "Bootlegger's",
    "Carnegie Mellon University",
    "Carnegie Music Hall",
    "Dave & Andy's Ice Cream",
    "Kiva Han Cafe",
    "Milano's Pizza",
    "Oakland BID",
    "Panther Hollow Inn",
    "Peter's Pub",
    "Sir Speedy Printing",
    "Touch of Gold and Silver",
    "Uncle Sam's Subs",
    "Union Grill",
    "Vera Cruz"
]

# TODO: there must obviously be a better way to do this. Works for now
class PlaceForTemplate:
    def __init__(self,place,url='',phone=''):
        self.phone = phone
        self.url = url
        self.owner = place.owner
        self.description = place.description
        self.name = place.name
        self.location = place.location

def _package_place(place):
    p = PlaceForTemplate(place)
    urls = place.meta_set.filter(meta_key='url')
    if urls and urls[0].meta_value:
        p.url = urls[0].meta_value
    phone_numbers = place.meta_set.filter(meta_key='phone')
    if phone_numbers and phone_numbers[0].meta_value:
        p.phone = phone_numbers[0].meta_value
    return p

def demo_places_page(request):
    variables = { 'places': [_package_place(p) for p in Place.objects.filter(name__in=subset_names)] }
    return render_to_response('pages/places_page.html',variables)

def demo_places_single(request):
    variables = { 'places': [_package_place(p) for p in Place.objects.filter(name__in=subset_names)] }
    return render_to_response('pages/places_page.html',variables)
