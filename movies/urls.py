from django.urls import path
from .views import index, movie, movie_reviews, add_review, person_detail, my_reviews

urlpatterns = [
    path('', index, name='home'),
    path('movie/<int:movie_id>/', movie, name='movie_detail'),
    path('movie/<int:movie_id>/reviews/', movie_reviews, name='movie_reviews'),
    path('movie/<int:movie_id>/review/add/', add_review, name='add_review'),
    path('person/<int:person_id>/', person_detail, name='person_detail'),
    path('my-reviews/', my_reviews, name='my_reviews'),
]
