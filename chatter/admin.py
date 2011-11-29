from django.contrib import admin
from onlyinpgh.chatter.models import Post, Comment

class CommentInline(admin.StackedInline):
    model = Comment
    extra = 3
    fields = ['commenter','dt','content']

class PostAdmin(admin.ModelAdmin):
    inlines = [CommentInline]
    filter_horizontal = ('tags',)

admin.site.register(Post,PostAdmin)