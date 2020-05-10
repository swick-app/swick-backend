from django.contrib import admin
from swickapp.models import Restaurant

# Display restaurants on Django dashboard
admin.site.register(Restaurant)
