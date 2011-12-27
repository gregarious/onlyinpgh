from django.conf.urls.defaults import patterns, include, url
from django.views.generic.simple import direct_to_template

# Uncomment the next two lines to enable the admin:
from django.contrib import admin

from onlyinpgh.places import views as places_views
from onlyinpgh.events import views as events_views
from onlyinpgh.offers import views as offers_views
from onlyinpgh.news import views as news_views
from onlyinpgh.chatter import views as chatter_views

admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'onlyinpgh.views.home', name='home'),
    # url(r'^onlyinpgh/', include('onlyinpgh.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^$', direct_to_template, {'template':'base.html'}),
    url(r'^admin/', include(admin.site.urls)),
    # For "A a Glance"
    url(r'^ajax/offers$', offers_views.demo_offers),
    url(r'^ajax/news$', news_views.demo_news),
    url(r'^ajax/events$', events_views.demo_events),
    
    # For single/all
    url(r'^ajax/events-page$', events_views.demo_events_page),
    url(r'^ajax/places-page$', places_views.demo_establishments_page),
    url(r'^ajax/offers-page$', offers_views.demo_offers),
    url(r'^ajax/news-page$', news_views.demo_news),

    url(r'^ajax/place-single$', places_views.demo_establishments_single),
    url(r'^ajax/event-single$', events_views.demo_events_single),
    
    # Chatter - not in use for OBID
    url(r'^ajax/chatter/teaser$', chatter_views.demo_teasers),
    url(r'^ajax/chatter/hot$', chatter_views.demo_posts_hot),
    url(r'^ajax/chatter/new$', chatter_views.demo_posts_new),
    url(r'^ajax/chatter/photos$', chatter_views.demo_posts_photos),
    url(r'^ajax/chatter/conversations$', chatter_views.demo_posts_conversations),
    url(r'^ajax/chatter/questions$', chatter_views.demo_posts_questions),
)
