from django.shortcuts import render_to_response
from onlyinpgh.events.models import Event

def events_page(request):
    variables = { 'events': Event.objects.filter(invisible=False) }
    return render_to_response('events/events_page.html',variables)

def single_event_page(request, id):
    variables = { 'e' : Event.objects.get(id=id) }
    return render_to_response('events/events_single.html', variables)
    