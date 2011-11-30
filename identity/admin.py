from django.contrib import admin
from onlyinpgh.identity.models import Identity, Individual, Organization

admin.site.register(Identity)
admin.site.register(Individual)
admin.site.register(Organization)