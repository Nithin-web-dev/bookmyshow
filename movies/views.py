from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.utils.timezone import now
from .models import Movie, Theater, Seat, Booking, Show
from datetime import datetime, timedelta
from django.contrib import messages
from decimal import Decimal
from .tasks import release_expired_seats

from django.db.models import Q
from django.db import transaction
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def movie_list(request):
    search_query = request.GET.get('search', '').strip()
    genre_filter = request.GET.get('genre', '')
    language_filter = request.GET.get('language', '')

    movies = Movie.objects.all()

    # Search functionality (by name or cast)
    if search_query:
        movies = movies.filter(Q(name__icontains=search_query) | Q(cast__icontains=search_query))

    # Filter by genre
    if genre_filter:
        movies = movies.filter(genre=genre_filter)

    # Filter by language
    if language_filter:
        movies = movies.filter(language=language_filter)

    # Order by rating (highest-rated first)
    movies = movies.order_by('-rating')

    genres = Movie.GENRE_CHOICES
    languages = Movie.LANGUAGE_CHOICES

    return render(request, 'movies/movie_list.html', {
        'movies': movies,
        'genres': genres,
        'languages': languages,
        'selected_genre': genre_filter,
        'selected_language': language_filter,
        'search_query': search_query,
    })



def theater_list(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    current_datetime = now()
    
    # Get theaters that have shows for this movie from current time onwards
    theaters = Theater.objects.filter(
        movie=movie,
        time__gte=current_datetime
    ).order_by('time')
    
    # Debug prints
    print(f"\n=== THEATER LIST DEBUG ===")
    print(f"Movie: {movie.name}")
    print(f"Current datetime: {current_datetime}")
    print(f"Number of theaters found: {theaters.count()}")
    for theater in theaters:
        print(f"Theater: {theater.name}, Show time: {theater.time}")
    print("=== END DEBUG ===\n")
    
    context = {
        'movie': movie,
        'theaters': theaters,
        'current_datetime': current_datetime,
    }
    return render(request, 'movies/theater_list.html', context)


@login_required
def book_seats(request, theater_id):
    theater = get_object_or_404(Theater, id=theater_id)
    
    if request.method == 'POST':
        # Get selected seats and clean the data
        selected_seats = request.POST.getlist('seats', [])
        
        try:
            # Clean and validate seat IDs
            selected_seat_ids = []
            for seat_id in selected_seats:
                if str(seat_id).isdigit():  # Check if it's a valid number
                    selected_seat_ids.append(int(seat_id))
            
            if not selected_seat_ids:
                messages.error(request, 'Please select at least one seat.')
                return redirect('book_seats', theater_id=theater_id)
            
            # Verify seats are still available
            seats = Seat.objects.filter(id__in=selected_seat_ids)
            unavailable_seats = [seat for seat in seats if not seat.is_available()]
            
            if unavailable_seats:
                messages.error(request, 
                    f'Seats {", ".join(s.seat_number for s in unavailable_seats)} are no longer available.')
                return redirect('book_seats', theater_id=theater_id)
            
            # Store in session for payment
            request.session['selected_seats'] = selected_seat_ids
            request.session['theater_id'] = theater_id
            request.session['reservation_time'] = now().isoformat()
            
            # Redirect to payment page
            return redirect('payment', theater_id=theater_id)
            
        except Exception as e:
            print(f"Error processing seats: {e}")  # Debug print
            messages.error(request, 'An error occurred while processing your selection. Please try again.')
            return redirect('book_seats', theater_id=theater_id)
    
    # For GET request, show available seats
    seats = Seat.objects.filter(theater=theater)
    
    # Organize seats into rows
    seat_rows = {}
    for seat in seats:
        row = seat.seat_number[0]
        if row not in seat_rows:
            seat_rows[row] = []
        seat_rows[row].append(seat)
    
    # Sort rows and seats
    sorted_rows = sorted(seat_rows.items())
    for row in seat_rows.values():
        row.sort(key=lambda x: int(''.join(filter(str.isdigit, x.seat_number))))
    
    context = {
        'theater': theater,
        'seat_rows': sorted_rows,
        'reservation_timeout': 5,
    }
    # Changed template name from book_seats.html to seat_selection.html
    return render(request, 'movies/seat_selection.html', context)

def home(request):
    today = now().date()
    today_shows = Show.objects.select_related('movie', 'theater').filter(date=today)
    movies = Movie.objects.all()[:4]
    
    # Debug prints
    print(f"Home view - Date: {today}")
    print(f"Home view - Shows found: {len(today_shows)}")
    for show in today_shows:
        print(f"Show: {show.movie.name} at {show.theater.name}")
    
    context = {
        'today_shows': today_shows,
        'movies': movies,
        'today': today,
        'debug_message': f"Found {len(today_shows)} shows for today"
    }
    return render(request, 'home.html', context)

def today_shows(request):
    today = now().date()
    today_shows = Show.objects.select_related('movie', 'theater').filter(date=today)
    
    # Debug prints
    print(f"Today shows view - Date: {today}")
    print(f"Today shows view - Shows found: {len(today_shows)}")
    
    context = {
        'today_shows': today_shows,
        'today': today,
        'debug_message': f"Found {len(today_shows)} shows for today"
    }
    return render(request, 'movies/today_shows.html', context)

@login_required
def seat_selection(request, theater_id):
    theater = get_object_or_404(Theater, id=theater_id)
    seats = Seat.objects.filter(theater=theater)
    
    context = {
        'theater': theater,
        'seats': seats,
    }
    return render(request, 'movies/seat_selection.html', context)

@login_required
def payment(request, theater_id):
    from decimal import Decimal
    from django.db import transaction
    
    theater = get_object_or_404(Theater, id=theater_id)
    selected_seat_ids = request.session.get('selected_seats', [])
    
    if not selected_seat_ids:
        messages.error(request, 'No seats selected.')
        return redirect('book_seats', theater_id=theater_id)
    
    try:
        with transaction.atomic():
            # Get selected seats with lock
            selected_seats = Seat.objects.select_for_update().filter(id__in=selected_seat_ids)
            
            if not selected_seats.exists():
                messages.error(request, 'Selected seats not found.')
                return redirect('book_seats', theater_id=theater_id)
            
            # Verify seats are still available
            unavailable_seats = [seat for seat in selected_seats if not seat.is_available()]
            if unavailable_seats:
                messages.error(request, 
                    f'Seats {", ".join(s.seat_number for s in unavailable_seats)} are no longer available.')
                return redirect('book_seats', theater_id=theater_id)
            
            if request.method == 'POST':
                # Process payment (dummy success for now)
                payment_successful = True
                
                if payment_successful:
                    dynamic_price = theater.get_dynamic_price()
                    
                    # Process each seat separately to ensure proper booking
                    for seat in selected_seats:
                        # First mark the seat as booked
                        seat.is_booked = True
                        seat.reserved_by = None
                        seat.reserved_at = None
                        seat.save()
                        
                        # Then create the booking record
                        Booking.objects.create(
                            user=request.user,
                            movie=theater.movie,
                            theater=theater,
                            seat=seat,
                            amount_paid=dynamic_price
                        )
                    
                    # Clear session data
                    request.session.pop('selected_seats', None)
                    request.session.pop('theater_id', None)
                    request.session.pop('reservation_time', None)
                    
                    messages.success(request, f'Successfully booked {len(selected_seats)} seats!')
                    return redirect('profile')
                else:
                    messages.error(request, 'Payment failed. Please try again.')
                    return redirect('payment', theater_id=theater_id)
            
            # For GET request, calculate prices
            dynamic_price = theater.get_dynamic_price()
            total_seats = Decimal(str(len(selected_seats)))
            total_price = dynamic_price * total_seats
            
            # Ensure reservation time is set
            if 'reservation_time' not in request.session:
                request.session['reservation_time'] = now().isoformat()
            
            context = {
                'theater': theater,
                'selected_seats': selected_seats,
                'dynamic_price': dynamic_price,
                'base_price': theater.base_price,
                'price_difference': dynamic_price - theater.base_price,
                'total_seats': total_seats,
                'total_price': total_price,
                'reservation_time': request.session.get('reservation_time'),
            }
            
            return render(request, 'movies/payment.html', context)
            
    except Exception as e:
        print(f"Payment error: {e}")  # Debug print
        messages.error(request, 'An error occurred. Please try again.')
        return redirect('book_seats', theater_id=theater_id)

@login_required
def confirm_booking(request, theater_id):
    if request.method == 'POST':
        theater = get_object_or_404(Theater, id=theater_id)
        selected_seat_ids = request.session.get('selected_seats', [])
        
        if not selected_seat_ids:
            messages.error(request, 'No seats selected.')
            return redirect('book_seats', theater_id=theater_id)
        
        try:
            # Process payment here (integrate with payment gateway)
            payment_successful = True  # Replace with actual payment processing
            
            if payment_successful:
                # Create bookings
                seats = Seat.objects.filter(id__in=selected_seat_ids)
                for seat in seats:
                    if seat.is_available() or seat.reserved_by == request.user:
                        seat.is_booked = True
                        seat.reserved_by = None
                        seat.reserved_at = None
                        seat.save()
                        
                        Booking.objects.create(
                            user=request.user,
                            movie=theater.movie,
                            theater=theater,
                            seat=seat
                        )
                
                # Clear session
                request.session.pop('selected_seats', None)
                request.session.pop('reservation_time', None)
                
                messages.success(request, 'Booking confirmed successfully!')
                return redirect('profile')
                
        except Exception as e:
            messages.error(request, 'Payment failed. Please try again.')
    
    return redirect('book_seats', theater_id=theater_id)

def test_view(request):
    return render(request, 'movies/test.html', {'message': 'Test view is working!'})

def fix_bookings(request):
    """Fix any inconsistencies between bookings and seat statuses"""
    from django.db import transaction
    
    # Only allow admins to access this view
    if not request.user.is_superuser:
        messages.error(request, 'Only administrators can access this page.')
        return redirect('home')
        
    with transaction.atomic():
        # 1. Find all seats that have bookings but aren't marked as booked
        bookings = Booking.objects.all().select_related('seat')
        seats_to_update = []
        
        for booking in bookings:
            if not booking.seat.is_booked:
                booking.seat.is_booked = True
                booking.seat.reserved_by = None
                booking.seat.reserved_at = None
                seats_to_update.append(booking.seat)
        
        # Bulk update the seats
        if seats_to_update:
            Seat.objects.bulk_update(seats_to_update, ['is_booked', 'reserved_by', 'reserved_at'])
            messages.success(request, f'Fixed {len(seats_to_update)} inconsistent seat statuses.')
        else:
            messages.info(request, 'No inconsistencies found in seat bookings.')
            
    return redirect('home')
