import datetime
import os
import random
from unittest import skip

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from .models import Post


# please, pretend that you didn't see it
class PredictionGenerator(TestCase):
    __doc__ = random.choice(
        [
            "Linux will be rewritten in Python by 2050. Get ready!",
            "RustPython will be the official interpreter by 2035!",
            "I can't believe this is possible.",
            "9.11 > 9.9, we consulted AI.",
            "Do you believe in Guido?",
            "Dit is duidelijk!",
        ]
    )

    def __call__(self):
        if os.environ.get("PY_PREDICT") is None:
            return
        self.assertIs(True, False)


# Create your tests here
class PostModelTests(TestCase):
    def test_was_published_recently_with_future_post(self):
        """
        was_published_recently() should return False for posts whose pub_date
        is in the future.
        """
        # in fairness, this is a silliest example I can think of
        #
        # like, should we allow such things in the first place?
        # also, if a time traveler does go along and makes a post tomorrow
        # should we just ignore his post until the right time comes?
        #
        # well, actually maybe this makes sense, but I'm still not convinced
        # and tbh, if we already went sci-fi, and this would be implemented in
        # Rust we would probably return Result::Err instead
        #
        # but here we are, discussing the test from Django tutorial
        # and I think we're definitely not in the future yet
        # so yeah, if we don't have an error, let's just return False
        time = timezone.now() + datetime.timedelta(days=30)
        time_traveler_post = Post(post_text="42!?", pub_date=time)
        self.assertIs(time_traveler_post.was_published_recently(), False)
        # P. s., AssertionError: True is not False is the best answer to failing
        # this test I could imagine
        # P. p. s. why on Earth I would even write this docstring if test
        # harness only shows the first line
        #
        # I guess, at least it would be useful for other people reading this
        #
        # btw, if someone who is not me, reading this, hi!
        # if this someone is me, but forgot about these comments, hi too :3

    def test_published_yesterday_recently(self):
        """
        was_published_recently() should return True for a post that was posted
        a day ago.
        """
        # yep, and the test harness will display something like
        # "was_published_..() should return True for a post that was posted"
        # which is simply brilliant, I think
        time = timezone.now() - datetime.timedelta(days=1)
        post = Post(
            post_text="I know I don't need to put this text",
            pub_date=time,
        )
        self.assertIs(post.was_published_recently(), True)

    def test_published_now(self):
        """was published now ~ was published recently"""
        # I wonder if I could programmatically make a docstring
        # so like, the test fails and you see a joke in your terminal
        #
        # yeah, the test is broken, but at least you'll laugh
        # probably will be even more annoying after jokes start to repeat
        # but as they are, these docstrings are mostly useless anyway
        time = timezone.now()
        # p. s. it's impossible to reproduce this one, because you know,
        # time flows
        # but I guess it's still useful indicator whether the code works
        #
        # even if the code itself is totally useless
        post = Post(
            post_text="should it be legal to omit this text?",
            pub_date=time,
        )
        self.assertIs(post.was_published_recently(), True)

    def test_published_recently_year_ago(self):
        """was published a year ago ain't the recent post, mate"""
        time = timezone.now() - datetime.timedelta(weeks=53)
        post = Post(
            post_text="\
i imagine it would be annoying to change all these if I rename\
 the post_text field to something else",
            pub_date=time,
        )
        self.assertIs(post.was_published_recently(), False)

    def test_post_too_long_must_fail(self):
        """Too much characters must fail"""
        with self.assertRaises(ValidationError):
            Post(post_text="*" * 501, pub_date=timezone.now()).full_clean()

    def test_post_complicated_length(self):
        # ok, I tried to insert composite emoji here to test the length
        # but then gave up, because it broke both my terminal and editor
        # gosh
        #
        # p. s. composite emoji count as more than one character, so you will
        # hit the limit
        pass

    def test_post_just_right(self):
        """emoji + non-latin 250 times over"""
        Post(post_text="є🐾" * 250, pub_date=timezone.now()).full_clean()

    @skip("look, this must fail, it's 1k bytes, but it works")
    def test_post_too_long_cyrilic_must_fail(self):
        """500 non-latin characters are ok, apparently"""
        with self.assertRaises(ValidationError):
            Post(post_text="є" * 500, pub_date=timezone.now()).full_clean()

    @skip("look, this must fail, it's 2k bytes, but it works")
    def test_post_too_long_bytes_must_fail(self):
        """500 emoji are ok, too"""
        with self.assertRaises(ValidationError):
            # I even tried this on postgres directly, and it works just fine
            #
            # it even shows the octet length of 2000
            #
            # I guess they are using UTF-32 or something
            # or just count in codepoints? which is ... interesting
            Post(post_text="🐾" * 500, pub_date=timezone.now()).full_clean()

    # ok, this one is here just to see if it works, I love Python
    # p. s. yes, it does count as a test
    test_published_dynamic = lambda self: self.assertIs(True, True)  # noqa: E731
    # this one is more real, but still just for fun, of course
    # don't worry, this one shouldn't run until you set PY_PREDICT variable
    test_predictor = PredictionGenerator()
