from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('today-shows/', views.today_shows, name='today_shows'),
    path('movies/', views.movie_list, name='movie_list'),
    path('<int:movie_id>/theaters/', views.theater_list, name='theater_list'),
    path('theater/<int:theater_id>/seats/book/', views.book_seats, name='book_seats'),
    path('theater/<int:theater_id>/seats/', views.seat_selection, name='seat_selection'),
    path('theater/<int:theater_id>/payment/', views.payment, name='payment'),
    path('theater/<int:theater_id>/confirm/', views.confirm_booking, name='confirm_booking'),
    path('test/', views.test_view, name='test_view'),
    path('fix-bookings/', views.fix_bookings, name='fix_bookings'),
]
