from django.apps import AppConfig
from django.utils.timezone import now
import threading
import time


class MoviesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'movies'
