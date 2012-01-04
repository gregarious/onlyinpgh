from django.contrib import admin
from onlyinpgh.identity.models import  Individual, Organization

admin.site.register(Individual)
admin.site.register(Organization)