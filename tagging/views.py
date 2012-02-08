from django.shortcuts import render_to_response
from onlyinpgh.tagging.models import Tag

def all_tags(request):
	variables = { 'tags': Tag.objects.all() }
	return render_to_response('tags.html', variables)