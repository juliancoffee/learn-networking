from django.shortcuts import render
from django.http import HttpResponse, JsonResponse

from .models import Post

# Create your views here.
def index(request) -> HttpResponse:
    posts = Post.objects.order_by("pub_date")
    response = JsonResponse({"posts": [
        {"id": p.id, "text": p.post_text} for p in posts]
    })
    return response

def read(request, post_id):
    p = Post.objects.get(pk=post_id)
    response = JsonResponse({
        "post": p.post_text,
        "comments": [
            c.comment_text for c in p.comment_set.all()
        ],
    })
    return response
