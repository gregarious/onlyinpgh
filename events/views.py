from django.shortcuts import render_to_response
from onlyinpgh.events.models import Event

def events_page(request):
    variables = { 'events': Event.objects.filter(invisible=False) }
    return render_to_response('events.html',variables)


#def demo_events_single(request):
#    variables = { 'events': Event.objects.filter(invisible=False) }
#    return render_to_response('single/event_single.html',variables)