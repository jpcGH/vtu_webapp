from django.urls import path
from .views import operations_console

app_name = 'dashboard'

urlpatterns = [
    path('', operations_console, name='console'),
]
