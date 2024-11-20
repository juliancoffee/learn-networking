from django.db import models

class Post(models.Model):
    post_text = models.CharField(max_length=500)
    pub_date = models.DateTimeField("publishing date")

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    comment_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField("publishing date")
