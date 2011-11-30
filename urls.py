from django.conf.urls.defaults import patterns, include, url
from django.views.generic.simple import direct_to_template

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'onlyinpgh.views.home', name='home'),
    # url(r'^onlyinpgh/', include('onlyinpgh.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url('^$',           direct_to_template,     {'template':'base.html'}),
    url(r'^admin/',     include(admin.site.urls)),
)
