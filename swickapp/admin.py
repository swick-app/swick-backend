from django.contrib import admin
from swickapp.models import Restaurant, Customer, Server, Meal, Order, OrderItem

# Display models on Django dashboard
admin.site.register(Restaurant)
admin.site.register(Customer)
admin.site.register(Server)
admin.site.register(Meal)
admin.site.register(Order)
admin.site.register(OrderItem)
