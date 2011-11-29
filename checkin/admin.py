from django.contrib import admin
from onlyinpgh.checkin.models import PlaceCheckin, EventCheckin

admin.site.register(PlaceCheckin)
admin.site.register(EventCheckin)