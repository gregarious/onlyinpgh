from django.contrib import admin
from chatter.models import Post, Comment

class CommentInline(admin.StackedInline):
    model = Comment
    extra = 3

class PostAdmin(admin.ModelAdmin):
    inlines = [CommentInline]

admin.site.register(Post,PostAdmin)