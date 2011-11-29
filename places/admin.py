from django.contrib import admin
from onlyinpgh.places.models import Place,Location,Establishment


class PlaceAdmin(admin.ModelAdmin):
    filter_horizontal = ('tags',)

class LocationAdmin(admin.ModelAdmin):
    pass

class EstablishmentAdmin(admin.ModelAdmin):
    filter_horizontal = ('tags',)

admin.site.register(Place,PlaceAdmin)
admin.site.register(Location,LocationAdmin)
admin.site.register(Establishment,EstablishmentAdmin)