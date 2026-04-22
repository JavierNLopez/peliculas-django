from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.db.models import Avg, Q

from movies.models import Movie, MovieReview, Person, MovieCredit
from movies.forms import MovieReviewForm


def index(request):
    query = request.GET.get('q', '').strip()

    movies = Movie.objects.all().order_by('-release_date')

    if query:
        movies = movies.filter(
            Q(title__icontains=query) |
            Q(overview__icontains=query)
        ).order_by('-release_date')

    featured_movie = Movie.objects.order_by('-release_date').first()

    context = {
        'movies': movies,
        'query': query,
        'featured_movie': featured_movie,
    }
    return render(request, 'movies/index.html', context)


def movie(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    reviews = MovieReview.objects.filter(movie=movie).order_by('-created_at')

    genres = movie.genres.all()
    recommended = Movie.objects.filter(
        genres__in=genres
    ).exclude(id=movie.id).distinct()[:4]

    average_rating = reviews.aggregate(avg=Avg('rating'))['avg']
    credits = MovieCredit.objects.filter(movie=movie).select_related('person', 'job')[:12]

    context = {
        'movie': movie,
        'reviews': reviews,
        'recommended': recommended,
        'average_rating': average_rating,
        'credits': credits,
    }
    return render(request, 'movies/movie.html', context)


def movie_reviews(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    reviews = MovieReview.objects.filter(movie=movie).order_by('-created_at')

    return render(request, 'movies/reviews.html', {
        'movie': movie,
        'reviews': reviews,
    })


def add_review(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)

    if not request.user.is_authenticated:
        return redirect('login')

    if request.method == 'POST':
        form = MovieReviewForm(request.POST)
        if form.is_valid():
            MovieReview.objects.create(
                movie=movie,
                rating=form.cleaned_data['rating'],
                title=form.cleaned_data['title'],
                review=form.cleaned_data['review'],
                user=request.user
            )
            return redirect('movie_detail', movie_id=movie.id)
    else:
        form = MovieReviewForm()

    return render(request, 'movies/movie_review_form.html', {
        'movie_review_form': form,
        'movie': movie
    })


def person_detail(request, person_id):
    person = get_object_or_404(Person, id=person_id)
    credits = MovieCredit.objects.filter(person=person).select_related('movie', 'job')

    return render(request, 'movies/person.html', {
        'person': person,
        'credits': credits
    })


def my_reviews(request):
    if not request.user.is_authenticated:
        return redirect('login')

    reviews = MovieReview.objects.filter(user=request.user).select_related('movie').order_by('-created_at')

    return render(request, 'movies/my_reviews.html', {
        'reviews': reviews
    })
