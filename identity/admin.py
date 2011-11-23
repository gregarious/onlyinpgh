from django.contrib import admin
from identity.models import Identity, Individual, Organization

admin.site.register(Identity)
admin.site.register(Individual)
admin.site.register(Organization)