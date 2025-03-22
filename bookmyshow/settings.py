INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'movies',
    'users',
    'channels',  # Add channels to installed apps
]

# Channels Configuration
ASGI_APPLICATION = 'bookmyshow.asgi.application'

# Channel Layers Configuration - Using In-Memory Channel Layer
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
} 