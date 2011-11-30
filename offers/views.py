from django.shortcuts import render_to_response
from offers.models import Offer

def demo_offers(request):
    variables = { 'offers': Offer.objects.all() }
    return render_to_response('broadcast/sandwich_board.html',variables)