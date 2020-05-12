from django.contrib import admin
from swickapp.models import Restaurant, Customer, Server, Meal

# Display models on Django dashboard
admin.site.register(Restaurant)
admin.site.register(Customer)
admin.site.register(Server)
admin.site.register(Meal)
