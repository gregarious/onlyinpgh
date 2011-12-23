from django.shortcuts import render_to_response
from onlyinpgh.offers.models import Offer

def demo_offers(request):
    variables = { 'offers': Offer.objects.all() }
    return render_to_response('feeds/sammichboard_feed.html',variables)