from django.conf.urls.defaults import patterns, include, url
from django.views.generic.simple import direct_to_template

# Uncomment the next two lines to enable the admin:
from django.contrib import admin

from onlyinpgh.chatter import views as chatter_views
from onlyinpgh.places import views as places_views
from onlyinpgh.events import views as events_views
from onlyinpgh.offers import views as offers_views
from onlyinpgh.news import views as news_views
from onlyinpgh.tagging import views as tag_views
from onlyinpgh import views as home_views

admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'onlyinpgh.views.home', name='home'),
    # url(r'^onlyinpgh/', include('onlyinpgh.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^$', home_views.hot_page),
    url(r'^map$', home_views.map_page),
    url(r'^specials$', offers_views.offers_page),
    url(r'^news$', news_views.news_page),
    url(r'^events$', events_views.events_page),
    url(r'^places$', places_views.places_page),
    url(r'^search$', home_views.search_page),
   # url(r'^tags$', tag_views.all_tags),

    url(r'^chatter$', chatter_views.chatter_posts_hot),
    url(r'^chatter/new$', chatter_views.chatter_posts_new),
    url(r'^chatter/questions$', chatter_views.chatter_posts_questions),
    url(r'^chatter/discuss$', chatter_views.chatter_posts_conversations),
    url(r'^chatter/pics$', chatter_views.chatter_posts_photos),

    url(r'^chatter/(?P<id>\d+)/$', chatter_views.single_post_page),
    url(r'^chatter/post-form/$', chatter_views.post_form),
    
    url(r'^specials/(?P<id>\d+)/$', offers_views.single_offer_page),
    url(r'^news/(?P<id>\d+)/$', news_views.single_article_page),
    url(r'^events/(?P<id>\d+)/$', events_views.single_event_page),
    url(r'^places/(?P<id>\d+)/$', places_views.single_place_page)

)