from django.shortcuts import render_to_response
from onlyinpgh.places.models import Establishment

def demo_establishments_page(request):
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

    variables = { 'establishments': Establishment.objects.filter(name__in=subset_names),
                }

            
    return render_to_response('pages/places_page.html',variables)



# Note to Greg: Lara is muddling! 
# Duplicating functions and shit for the sake of speed

def demo_establishments_single(request):
        
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

    variables = { 'establishments': Establishment.objects.filter(name__in=subset_names),
                }
    return render_to_response('single/place_single.html',variables)
