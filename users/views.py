from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from .forms import UserRegisterForm, UserUpdateForm
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from movies.models import Movie, Booking, Theater, Show
from django.utils.timezone import now
from datetime import datetime, time

def home(request):
    movies = Movie.objects.all()
    return render(request, 'home.html', {'movies': movies})

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            login(request, user)
            return redirect('profile')
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('/')
    else:
        form = AuthenticationForm()
    return render(request, 'users/login.html', {'form': form})

@login_required
def profile(request):
    # Get user's bookings ordered by booking time
    bookings = Booking.objects.filter(user=request.user).select_related('movie', 'theater', 'seat').order_by('-booked_at')
    
    # Separate upcoming and past bookings
    current_time = now()
    upcoming_bookings = []
    past_bookings = []
    
    for booking in bookings:
        if booking.theater.time > current_time:
            upcoming_bookings.append(booking)
        else:
            past_bookings.append(booking)
    
    # Debug prints
    print(f"\n=== PROFILE DEBUG ===")
    print(f"Total bookings: {len(bookings)}")
    print(f"Upcoming bookings: {len(upcoming_bookings)}")
    print(f"Past bookings: {len(past_bookings)}")
    for booking in bookings:
        print(f"Booking: {booking.movie.name} - Seat {booking.seat.seat_number} - Time: {booking.theater.time}")
    print("=== END DEBUG ===\n")
    
    context = {
        'upcoming_bookings': upcoming_bookings,
        'past_bookings': past_bookings,
    }
    
    return render(request, 'users/profile.html', context)

@login_required
def reset_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = PasswordChangeForm(user=request.user)
    return render(request, 'users/reset_password.html', {'form': form})

@login_required
def edit_profile(request):
    if request.method == 'POST':
        profile = request.user.profile
        profile.phone_number = request.POST.get('phone_number', '')
        profile.address = request.POST.get('address', '')
        profile.save()
        return redirect('profile')
    return redirect('profile')

def logout_view(request):
    logout(request)
    return redirect('home')