from django.contrib import admin
from onlyinpgh.news.models import Article

class ArticleAdmin(admin.ModelAdmin):
    filter_horizontal = ('tags',)

admin.site.register(Article,ArticleAdmin)