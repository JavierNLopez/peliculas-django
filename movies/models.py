from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator


class Genre(models.Model):
    name = models.CharField(max_length=80)

    def __str__(self):
        return self.name


class Person(models.Model):
    name = models.CharField(max_length=128)
    tmdb_person_id = models.IntegerField(null=True, blank=True, unique=True)
    birth_date = models.DateField(null=True, blank=True)
    country = models.CharField(max_length=120, blank=True, null=True)
    image_url = models.URLField(blank=True, null=True)
    biography = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Job(models.Model):
    name = models.CharField(max_length=128)

    def __str__(self):
        return self.name


class Movie(models.Model):
    title = models.CharField(max_length=200)
    overview = models.TextField(blank=True)
    release_date = models.DateField(null=True, blank=True)
    running_time = models.IntegerField(null=True, blank=True)
    budget = models.BigIntegerField(null=True, blank=True)
    revenue = models.BigIntegerField(null=True, blank=True)
    tmdb_id = models.IntegerField(unique=True, null=True, blank=True)
    poster_path = models.CharField(max_length=255, blank=True, null=True)
    genres = models.ManyToManyField(Genre, blank=True)

    def __str__(self):
        return self.title


class MovieCredit(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    role_name = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.movie} - {self.person} - {self.job}"


class MovieReview(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    review = models.TextField()
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.rating}"


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorites")
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "movie")

    def __str__(self):
        return f"{self.user.username} - {self.movie.title}"
