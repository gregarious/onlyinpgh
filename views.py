from django.shortcuts import render_to_response

from onlyinpgh.places.models import Place, Meta as PlaceMeta
from onlyinpgh.events.models import Event
from onlyinpgh.news.models import Article
from onlyinpgh.offers.models import Offer


def hot_page(request):
    variables = { 'places': Place.objects.all(), 'events': Event.objects.all(), 'news': Article.objects.all(), 'offers': Offer.objects.all() }
    return render_to_response('hot.html',variables)

def map_page(request):
	variables = { 'places': Place.objects.all(), 'events': Event.objects.all(), 'news': Article.objects.all(), 'offers': Offer.objects.all() }
	return render_to_response('map.html',variables)	

# Empty template for splash and search pages
def home_page(request):
	variables = {}
	return render_to_response('home.html',variables)	

def search_page(request):
	variables = {}
	return render_to_response('search.html',variables)		