from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from movies.forms import MovieReviewForm
from movies.models import Favorite, Genre, Movie, MovieCredit, MovieReview, Person


def index(request):
    query = request.GET.get("q", "").strip()
    genre_id = request.GET.get("genre", "").strip()
    ajax = request.GET.get("ajax") == "1"

    movies = (
        Movie.objects.all()
        .prefetch_related("genres")
        .annotate(avg_rating=Avg("reviews__rating"))
        .order_by("-release_date", "-id")
    )

    if query:
        movies = (
            movies.filter(
                Q(title__icontains=query) |
                Q(overview__icontains=query) |
                Q(genres__name__icontains=query)
            )
            .distinct()
        )

    if genre_id:
        movies = movies.filter(genres__id=genre_id)

    movies = movies.order_by("-release_date", "-id")

    favorite_ids = set()
    if request.user.is_authenticated:
        favorite_ids = set(
            Favorite.objects.filter(user=request.user).values_list("movie_id", flat=True)
        )

    if ajax:
        items = []
        for movie in movies[:24]:
            items.append({
                "id": movie.id,
                "title": movie.title,
                "release_date": str(movie.release_date) if movie.release_date else "",
                "poster_url": f"https://image.tmdb.org/t/p/w500{movie.poster_path}" if movie.poster_path else "https://via.placeholder.com/500x750?text=Sin+imagen",
                "genres": [g.name for g in movie.genres.all()[:3]],
                "avg_rating": round(movie.avg_rating, 1) if movie.avg_rating else None,
                "tmdb_vote_average": round(movie.tmdb_vote_average, 1) if movie.tmdb_vote_average else None,
                "is_favorite": movie.id in favorite_ids,
            })
        return JsonResponse({"movies": items})

    featured_movies = list(
        Movie.objects.exclude(poster_path__isnull=True)
        .exclude(poster_path="")
        .annotate(avg_rating=Avg("reviews__rating"))
        .order_by("-release_date")[:8]
    )

    genres = Genre.objects.all().order_by("name")

    context = {
        "movies": movies,
        "query": query,
        "genre_id": genre_id,
        "genres": genres,
        "featured_movies": featured_movies,
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
        .annotate(
            num_genres=Count("genres"),
            avg_rating=Avg("reviews__rating"),
        )
        .distinct()
        .order_by("-num_genres", "-avg_rating", "-tmdb_vote_average", "-release_date")[:6]
    )

    average_rating = reviews.aggregate(avg=Avg("rating"))["avg"]

    credits = (
        MovieCredit.objects.filter(movie=movie)
        .select_related("person", "job")
        .order_by("credit_order", "person__name")
    )

    cast_credits = list(credits.filter(job__name__icontains="Act")[:10])
    crew_credits = list(credits.exclude(job__name__icontains="Act")[:8])

    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = Favorite.objects.filter(user=request.user, movie=movie).exists()

    context = {
        "movie": movie,
        "reviews": reviews,
        "recommended": recommended,
        "average_rating": average_rating,
        "cast_credits": cast_credits,
        "crew_credits": crew_credits,
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


@login_required
def edit_review(request, review_id):
    review = get_object_or_404(MovieReview, id=review_id, user=request.user)

    if request.method == "POST":
        form = MovieReviewForm(request.POST)
        if form.is_valid():
            review.rating = form.cleaned_data["rating"]
            review.title = form.cleaned_data["title"]
            review.review = form.cleaned_data["review"]
            review.save()
            return redirect("movie_detail", movie_id=review.movie.id)
    else:
        initial = {
            "rating": review.rating,
            "title": review.title,
            "review": review.review,
        }
        form = MovieReviewForm(initial=initial)

    return render(request, "movies/edit_review.html", {
        "movie_review_form": form,
        "review_obj": review,
        "movie": review.movie,
        "query": request.GET.get("q", ""),
    })


@login_required
def delete_review(request, review_id):
    review = get_object_or_404(MovieReview, id=review_id, user=request.user)
    movie_id = review.movie.id

    if request.method == "POST":
        review.delete()
        return redirect("movie_detail", movie_id=movie_id)

    return render(request, "movies/delete_review.html", {
        "review_obj": review,
        "movie": review.movie,
        "query": request.GET.get("q", ""),
    })


def person_detail(request, person_id):
    person = get_object_or_404(Person, id=person_id)

    credits = (
        MovieCredit.objects.filter(person=person)
        .select_related("movie", "job")
        .order_by("credit_order", "-movie__release_date", "movie__title")
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

    previous_url = request.META.get("HTTP_REFERER")
    if previous_url:
        return redirect(previous_url)
    return redirect("movie_detail", movie_id=movie.id)


@login_required
def my_favorites(request):
    favorites = (
        Favorite.objects.filter(user=request.user)
        .select_related("movie")
        .prefetch_related("movie__genres")
        .annotate(avg_rating=Avg("movie__reviews__rating"))
        .order_by("-created_at")
    )

    return render(request, "movies/my_favorites.html", {
        "favorites": favorites,
        "query": request.GET.get("q", ""),
    })
