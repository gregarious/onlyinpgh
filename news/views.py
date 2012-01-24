from django.shortcuts import render_to_response
from onlyinpgh.news.models import Article

def news_page(request):
    variables = { 'articles': Article.objects.all() }
    return render_to_response('news/news_page.html',variables)

def single_article_page(request, id):
    variables = { 'a' : Article.objects.get(id=id) }
    return render_to_response('news/news_single.html', variables)
    