from django.shortcuts import render_to_response
from onlyinpgh.chatter.models import Post, Comment

def demo_teasers(request):
    variables = { 'posts': Post.objects.all().order_by('-dt') }
    return render_to_response('chatter_teaser.html',variables)

def demo_posts_hot(request):
    variables = { 'posts': Post.objects.all().order_by('-dt'),
                    'id_prefix': 'hot-' }
    return render_to_response('chatterbox_inner.html',variables)

def demo_posts_new(request):
    variables = { 'posts': Post.objects.all().order_by('-dt'),
                    'id_prefix': 'new-' }
    return render_to_response('chatterbox_inner.html',variables)

def demo_posts_photos(request):
    variables = { 'posts': Post.objects.filter(post_type='photo').order_by('-dt'),
                    'id_prefix': 'photo-' }
    return render_to_response('chatterbox_inner.html',variables)

def demo_posts_conversations(request):
    variables = { 'posts': Post.objects.filter(post_type='conversation').order_by('-dt'),
                    'id_prefix': 'conversation-' }
    return render_to_response('chatterbox_inner.html',variables)

def demo_posts_questions(request):
    variables = { 'posts': Post.objects.filter(post_type='question').order_by('-dt'),
                    'id_prefix': 'question-' }
    return render_to_response('chatterbox_inner.html',variables)