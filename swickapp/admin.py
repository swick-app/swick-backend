from django.contrib import admin
from swickapp.models import Restaurant, Customer, Server, Meal, Customization, \
    Order, OrderItem, OrderItemCustomization

# Display models on Django admin
admin.site.register(Restaurant)
admin.site.register(Customer)
admin.site.register(Server)
admin.site.register(Meal)
admin.site.register(Customization)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(OrderItemCustomization)
