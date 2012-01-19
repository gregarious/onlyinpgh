from django.contrib import admin
from onlyinpgh.oldevents.models import Event, Location, Organization, Attendee, Role, Meta

admin.site.register(Event)
admin.site.register(Location)
admin.site.register(Organization)