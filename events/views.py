from django.shortcuts import render_to_response
from onlyinpgh.events.models import Event

def demo_events(request):
    variables = { 'events': Event.objects.all() }
    return render_to_response('feeds/events_feed.html',variables)


# Note to Greg: Lara is muddling! 
# Duplicating functions and shit for the sake of speed

def demo_events_page(request):
    variables = { 'events': Event.objects.all() }
    return render_to_response('pages/events_page.html',variables)


def demo_events_single(request):
    variables = { 'events': Event.objects.all() }
    return render_to_response('single/event_single.html',variables)