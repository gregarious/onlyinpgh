from django.shortcuts import render_to_response
from onlyinpgh.offers.models import Offer

def offers_page(request):
	variables = { 'offers': Offer.objects.all() }
	return render_to_response('offers/offers_page.html',variables)

def single_offer_page(request, id):
    variables = { 'o' : Offer.objects.get(id=id) }
    return render_to_response('offers/offers_single.html', variables)
    