from django.contrib import admin
from events.models import Event, Role, Attendee

class RoleInline(admin.TabularInline):
    model = Role
    extra = 1

class EventAdmin(admin.ModelAdmin):
    inlines = [RoleInline]
    exclude = ('rrule','rdate','exrule','exdate')

admin.site.register(Event,EventAdmin)