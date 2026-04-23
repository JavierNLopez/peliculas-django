import random

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from movies.forms import MovieReviewForm
from movies.models import Favorite, Movie, MovieCredit, MovieReview, Person


def index(request):
    query = request.GET.get("q", "").strip()

    movies = Movie.objects.all().prefetch_related("genres").order_by("-release_date", "-id")

    if query:
        movies = movies.filter(
            Q(title__icontains=query) |
            Q(overview__icontains=query) |
            Q(genres__name__icontains=query)
        ).distinct().order_by("-release_date", "-id")

    featured_candidates = list(Movie.objects.exclude(poster_path__isnull=True).exclude(poster_path=""))
    featured_movie = random.choice(featured_candidates) if featured_candidates else Movie.objects.order_by("-release_date").first()

    favorite_ids = set()
    if request.user.is_authenticated:
        favorite_ids = set(
            Favorite.objects.filter(user=request.user).values_list("movie_id", flat=True)
        )

    context = {
        "movies": movies,
        "query": query,
        "featured_movie": featured_movie,
        "favorite_ids": favorite_ids,
    }
    return render(request, "movies/index.html", context)


def movie(request, movie_id):
    movie = get_object_or_404(Movie.objects.prefetch_related("genres"), id=movie_id)
    reviews = MovieReview.objects.filter(movie=movie).select_related("user").order_by("-created_at")

    genres = movie.genres.all()

    recommended = (
        Movie.objects.filter(genres__in=genres)
        .exclude(id=movie.id)
        .annotate(num_genres=Count("genres"))
        .distinct()
        .order_by("-num_genres", "-release_date")[:6]
    )

    average_rating = reviews.aggregate(avg=Avg("rating"))["avg"]

    credits = (
        MovieCredit.objects.filter(movie=movie)
        .select_related("person", "job")
        .order_by("job__name", "person__name")[:16]
    )

    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = Favorite.objects.filter(user=request.user, movie=movie).exists()

    context = {
        "movie": movie,
        "reviews": reviews,
        "recommended": recommended,
        "average_rating": average_rating,
        "credits": credits,
        "is_favorite": is_favorite,
        "query": request.GET.get("q", ""),
    }
    return render(request, "movies/movie.html", context)


def movie_reviews(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    reviews = MovieReview.objects.filter(movie=movie).select_related("user").order_by("-created_at")

    return render(request, "movies/reviews.html", {
        "movie": movie,
        "reviews": reviews,
        "query": request.GET.get("q", ""),
    })


@login_required
def add_review(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)

    if request.method == "POST":
        form = MovieReviewForm(request.POST)
        if form.is_valid():
            MovieReview.objects.create(
                movie=movie,
                rating=form.cleaned_data["rating"],
                title=form.cleaned_data["title"],
                review=form.cleaned_data["review"],
                user=request.user,
            )
            return redirect("movie_detail", movie_id=movie.id)
    else:
        form = MovieReviewForm()

    return render(request, "movies/movie_review_form.html", {
        "movie_review_form": form,
        "movie": movie,
        "query": request.GET.get("q", ""),
    })


def person_detail(request, person_id):
    person = get_object_or_404(Person, id=person_id)
    credits = (
        MovieCredit.objects.filter(person=person)
        .select_related("movie", "job")
        .order_by("-movie__release_date", "movie__title")
    )

    acting_credits = credits.filter(job__name__icontains="Act")
    other_credits = credits.exclude(job__name__icontains="Act")

    return render(request, "movies/person.html", {
        "person": person,
        "credits": credits,
        "acting_credits": acting_credits,
        "other_credits": other_credits,
        "query": request.GET.get("q", ""),
    })


@login_required
def my_reviews(request):
    reviews = (
        MovieReview.objects.filter(user=request.user)
        .select_related("movie")
        .order_by("-created_at")
    )

    return render(request, "movies/my_reviews.html", {
        "reviews": reviews,
        "query": request.GET.get("q", ""),
    })


@login_required
def toggle_favorite(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)

    favorite = Favorite.objects.filter(user=request.user, movie=movie).first()
    if favorite:
        favorite.delete()
    else:
        Favorite.objects.create(user=request.user, movie=movie)

    return redirect(request.META.get("HTTP_REFERER", "movie_detail"), movie_id=movie.id if request.resolver_match and request.resolver_match.url_name == "movie_detail" else None)


@login_required
def my_favorites(request):
    favorites = (
        Favorite.objects.filter(user=request.user)
        .select_related("movie")
        .order_by("-created_at")
    )

    return render(request, "movies/my_favorites.html", {
        "favorites": favorites,
        "query": request.GET.get("q", ""),
    })
