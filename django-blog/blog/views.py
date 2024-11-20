from django.shortcuts import render
from django.http import HttpResponse

from .models import Post

# Create your views here.
def index(request) -> HttpResponse:
    posts = Post.objects.order_by("pub_date")
    page = " ".join([f"{p.id}) {p.post_text}" for p in posts])
    return HttpResponse(page)

def read(request, post_id):
    p = Post.objects.get(pk=post_id)
    comments = " * ".join(c.comment_text for c in p.comment_set.all())
    page = f"{p.post_text} <> {comments}"
    return HttpResponse(page)
