from django.shortcuts import render_to_response
from onlyinpgh.events.models import Event

def demo_events(request):
    variables = { 'events': Event.objects.all() }
    return render_to_response('broadcast/events.html',variables)