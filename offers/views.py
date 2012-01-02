from django.shortcuts import render_to_response
from onlyinpgh.offers.models import Offer

def demo_offers(request):
    variables = { 'offers': Offer.objects.all() }
    return render_to_response('feeds/offers_feed.html',variables)


# Note to Greg: Lara is muddling! 
# Duplicating functions and shit for the sake of speed

def demo_offers_page(request):
    variables = { 'offers': Offer.objects.all() }
    return render_to_response('pages/offers_page.html',variables)