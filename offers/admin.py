from django.contrib import admin
from onlyinpgh.offers.models import Offer

class OfferAdmin(admin.ModelAdmin):
    filter_horizontal = ('tags',)

admin.site.register(Offer,OfferAdmin)