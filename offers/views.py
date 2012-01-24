from django.shortcuts import render_to_response
from onlyinpgh.offers.models import Offer

def offers_page(request):
    variables = { 'offers': Offer.objects.all() }
    return render_to_response('offers.html',variables)