from django.urls import path
from .views import (
    add_review,
    index,
    movie,
    movie_reviews,
    my_favorites,
    my_reviews,
    person_detail,
    toggle_favorite,
)

urlpatterns = [
    path("", index, name="home"),
    path("movie/<int:movie_id>/", movie, name="movie_detail"),
    path("movie/<int:movie_id>/reviews/", movie_reviews, name="movie_reviews"),
    path("movie/<int:movie_id>/review/add/", add_review, name="add_review"),
    path("movie/<int:movie_id>/favorite/", toggle_favorite, name="toggle_favorite"),
    path("person/<int:person_id>/", person_detail, name="person_detail"),
    path("my-reviews/", my_reviews, name="my_reviews"),
    path("my-favorites/", my_favorites, name="my_favorites"),
]
