from django.conf.urls.defaults import patterns, include, url
from django.views.generic.simple import direct_to_template

# Uncomment the next two lines to enable the admin:
from django.contrib import admin

from onlyinpgh.places import views as places_views
from onlyinpgh.events import views as events_views
from onlyinpgh.offers import views as offers_views
from onlyinpgh.news import views as news_views

admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'onlyinpgh.views.home', name='home'),
    # url(r'^onlyinpgh/', include('onlyinpgh.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^$',      direct_to_template,     {'template':'base.html'}),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^ajax/places$', places_views.demo_establishments),
    url(r'^ajax/events$', events_views.demo_events),
    url(r'^ajax/offers$', offers_views.demo_offers),
    url(r'^ajax/news$', news_views.demo_news),
)
