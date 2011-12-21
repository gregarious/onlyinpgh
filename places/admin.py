from django.contrib import admin
from onlyinpgh.places.models import *

class PlaceMetaInline(admin.TabularInline):
    model = PlaceMeta
    extra = 3

class PlaceAdmin(admin.ModelAdmin):
    filter_horizontal = ('tags',)
    inlines = [PlaceMetaInline]

class LocationAdmin(admin.ModelAdmin):
    pass

admin.site.register(Place,PlaceAdmin)
admin.site.register(Location,LocationAdmin)
admin.site.register(FacebookPageRecord)
admin.site.register(ExternalPlaceSource)