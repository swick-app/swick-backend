from django.contrib import admin
from swickapp.models import Restaurant, Customer, Server, Meal, Customization, Order, OrderItem
from swickapp.forms import CustomizationForm

# Display models on Django admin
admin.site.register(Restaurant)
admin.site.register(Customer)
admin.site.register(Server)
admin.site.register(Meal)
admin.site.register(Order)
admin.site.register(OrderItem)

# Use custom customization form
@admin.register(Customization)
class CustomizationAdmin(admin.ModelAdmin):
    form = CustomizationForm
