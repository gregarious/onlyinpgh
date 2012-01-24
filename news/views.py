from django.shortcuts import render_to_response
from onlyinpgh.news.models import Article

def news_page(request):
    variables = { 'articles': Article.objects.all() }
    return render_to_response('news.html',variables)
