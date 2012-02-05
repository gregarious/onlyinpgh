from django.shortcuts import render_to_response
from onlyinpgh.chatter.models import Post, Comment

def chatter_teasers(request):
    variables = { 'posts': Post.objects.all().order_by('-dt') }
    return render_to_response('chatter_teaser.html',variables)

def chatter_posts_hot(request):
    variables = { 'posts': Post.objects.all().order_by('-dt'),
                    'id_prefix': 'hot-' }
    return render_to_response('chatter/chatter_page.html',variables)

def chatter_posts_new(request):
    variables = { 'posts': Post.objects.all().order_by('-dt'),
                    'id_prefix': 'new-' }
    return render_to_response('chatter/chatter_page.html',variables)

def chatter_posts_photos(request):
    variables = { 'posts': Post.objects.filter(post_type='photo').order_by('-dt'),
                    'id_prefix': 'photo-' }
    return render_to_response('chatter/chatter_page.html',variables)

def chatter_posts_conversations(request):
    variables = { 'posts': Post.objects.filter(post_type='conversation').order_by('-dt'),
                    'id_prefix': 'conversation-' }
    return render_to_response('chatter/chatter_page.html',variables)

def chatter_posts_questions(request):
    variables = { 'posts': Post.objects.filter(post_type='question').order_by('-dt'),
                    'id_prefix': 'question-' }
    return render_to_response('chatter/chatter_page.html',variables)

def single_post_page(request, id):
    variables = { 'posts': Post.objects.all().get(id=id) }
    return render_to_response('chatter/chatter_single.html', variables)

def post_form(request, id):
    variables = { 'posts': Post.objects.all().get(id=id) }
    return render_to_response('chatter/post_form.html', variables)
