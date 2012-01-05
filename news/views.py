from django.shortcuts import render_to_response
from onlyinpgh.news.models import Article

def demo_news(request):
    variables = { 'articles': Article.objects.all() }
    return render_to_response('feeds/news_feed.html',variables)

# Note to Greg: Lara is muddling! 
# Duplicating functions for the sake of speed

def demo_news_page(request):
    variables = { 'articles': Article.objects.all() }
    return render_to_response('pages/news_page.html',variables)