from django.http import (
    HttpResponse,
    HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone

from .models import Post


# Create your views here.
def index(request) -> HttpResponse:
    posts = Post.objects.order_by("pub_date")
    context = {"post_list": posts}
    return render(request, "blog/index.html", context)


def detail(request, post_id: int) -> HttpResponse:
    p = get_object_or_404(Post, pk=post_id)
    return render(
        request,
        "blog/detail.html",
        {
            "post": p,
            "comments": p.comment_set.all(),
        },
    )


def comment(request, post_id) -> HttpResponse:
    p = get_object_or_404(Post, pk=post_id)
    # p. s. this could be pattern match (or if) on .get()
    try:
        comment = request.POST["comment"]
    except KeyError:
        return render(
            request,
            "blog/detail.html",
            {
                "post": p,
                "comments": p.comment_set.all(),
                # TODO(me): actually use this at some point
                "error": "we couldn't get your comment, sommry!",
            },
        )
    else:
        p.comment_set.create(comment_text=comment, pub_date=timezone.now())
        # Always return an HttpResponseRedirect after successfully dealing
        # with POST data. This prevents data from being posted twice if a
        # user hits the Back button.
        #
        # ^ source: Django Docs, Tutorial part 4
        return HttpResponseRedirect(reverse("blog:detail", args=(post_id,)))
