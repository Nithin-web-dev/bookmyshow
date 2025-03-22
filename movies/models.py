from django.db import models
from django.contrib.auth.models import User 
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.timezone import now
from datetime import timedelta
from decimal import Decimal


class Movie(models.Model):
    GENRE_CHOICES = [
        ('Action', 'Action'),
        ('Comedy', 'Comedy'),
        ('Drama', 'Drama'),
        ('Horror', 'Horror'),
        ('Sci-Fi', 'Sci-Fi'),
    ]

    LANGUAGE_CHOICES = [
        ('English', 'English'),
        ('Hindi', 'Hindi'),
        ('Spanish', 'Spanish'),
        ('French', 'French'),
    ]

    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to='movies/')
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=0.0)
    cast = models.TextField()
    description = models.TextField(blank=True, null=True)  # Optional
    genre = models.CharField(max_length=50, choices=GENRE_CHOICES, default='Action')
    language = models.CharField(max_length=50, choices=LANGUAGE_CHOICES, default='English')

    def __str__(self):
        return self.name



class Theater(models.Model):
    name = models.CharField(max_length=255)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='theaters')
    time = models.DateTimeField()
    base_price = models.DecimalField(max_digits=6, decimal_places=2, default=200.00)  # Base ticket price

    def get_dynamic_price(self):
        """Calculate dynamic price based on demand and time"""
        total_seats = self.seats.count()
        booked_seats = self.seats.filter(is_booked=True).count()
        time_to_show = self.time - now()
        hours_to_show = time_to_show.total_seconds() / 3600

        # Calculate occupancy percentage
        occupancy = (booked_seats / total_seats) * 100 if total_seats > 0 else 0

        # Base multiplier (as Decimal)
        price_multiplier = Decimal('1.0')

        # Adjust price based on occupancy
        if occupancy >= 80:
            price_multiplier = Decimal('1.5')  # 50% increase for high demand
        elif occupancy >= 60:
            price_multiplier = Decimal('1.3')  # 30% increase for medium-high demand
        elif occupancy <= 20:
            price_multiplier = Decimal('0.8')  # 20% discount for low demand

        # Adjust price based on time to show
        if hours_to_show <= 2:
            price_multiplier *= Decimal('0.7')  # Last-minute discount
        elif hours_to_show <= 24:
            price_multiplier *= Decimal('0.9')  # Same-day slight discount
        elif hours_to_show >= 168:  # 7 days
            price_multiplier *= Decimal('0.8')  # Early bird discount

        # Calculate final price and round to 2 decimal places
        return (self.base_price * price_multiplier).quantize(Decimal('0.01'))

    def __str__(self):
        return f'{self.name} - {self.movie.name} at {self.time}'


class Seat(models.Model):
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE, related_name='seats')
    seat_number = models.CharField(max_length=10)
    is_booked = models.BooleanField(default=False)
    reserved_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)
    reserved_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f'{self.seat_number} in {self.theater.name}'
    
    def reserve(self, user):
        self.reserved_by = user
        self.reserved_at = now()
        self.save()
    
    def release(self):
        self.reserved_by = None
        self.reserved_at = None
        self.save()
    
    def is_available(self):
        if self.is_booked:
            return False
        if self.reserved_at:
            # Check if reservation has expired (5 minutes)
            timeout = self.reserved_at + timedelta(minutes=5)
            if now() >= timeout:
                self.release()
                return True
            return False
        return True


# 🔹 Auto-create 150 seats when a new theater is added
@receiver(post_save, sender=Theater)
def create_seats_for_theater(sender, instance, created, **kwargs):
    if created:  # Only create seats when a new theater is added
        rows = "ABCDEFGHIJ"  # 10 rows (A to J)
        seats_per_row = 15  # 15 seats in each row
        for row in rows:
            for num in range(1, seats_per_row + 1):
                Seat.objects.create(theater=instance, seat_number=f"{row}{num}")


class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE)
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE)
    booked_at = models.DateTimeField(auto_now_add=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('200.00'))  # Default base price

    class Meta:
        ordering = ['-booked_at']
        # Ensure each seat can only be booked once
        unique_together = ['theater', 'seat']

    def __str__(self):
        return f"{self.user.username} - {self.movie.name} - Seat {self.seat.seat_number}"

    @property
    def show_time(self):
        return self.theater.time


class Show(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateField()
    time = models.TimeField()

    def is_today(self):
        return self.date == now().date()

    def __str__(self):
        return f'{self.movie.name} at {self.theater.name if self.theater else "TBA"} - {self.time} ({self.date})'


# 🔹 Auto-create Show for today's date when a new theater is added
@receiver(post_save, sender=Theater)
def create_show_for_theater(sender, instance, created, **kwargs):
    if created:  # Only create a show when a new theater is added
        today = now().date()
        
        if instance.time.date() == today:  # Check if the show is for today
            Show.objects.get_or_create(
                movie=instance.movie,
                theater=instance,
                date=today,
                time=instance.time.time()  # Ensure time is properly stored
            )
