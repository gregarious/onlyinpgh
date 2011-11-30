from django.shortcuts import render_to_response
from news.models import Article

def demo_news(request):
    variables = { 'articles': Article.objects.all() }
    return render_to_response('broadcast/news.html',variables)