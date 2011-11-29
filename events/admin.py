from django.contrib import admin
from onlyinpgh.events.models import Event, Role, Attendee

class RoleInline(admin.TabularInline):
    model = Role
    extra = 1
    radio_fields = {'role_name':admin.VERTICAL}

class EventAdmin(admin.ModelAdmin):
    inlines = [RoleInline]
    exclude = ('rrule','rdate','exrule','exdate')
    filter_horizontal = ('tags',)
    list_display = ('name','place','dtstart','dtend')

admin.site.register(Event,EventAdmin)