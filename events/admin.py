from django.contrib import admin
from onlyinpgh.events.models import Event, Role, Attendee, Meta

class RoleInline(admin.TabularInline):
    model = Role
    extra = 1
    radio_fields = {'role_name':admin.VERTICAL}

class MetaInline(admin.TabularInline):
    model = Meta
    extra = 1

class EventAdmin(admin.ModelAdmin):
    inlines = [RoleInline,MetaInline]
    exclude = ('rrule','rdate','exrule','exdate')
    filter_horizontal = ('tags',)
    list_display = ('name','place','dtstart','dtend')
    search_fields = ['name']
    ordering = ['dtstart']

admin.site.register(Event,EventAdmin)