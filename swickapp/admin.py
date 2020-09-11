from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User, Restaurant, Customer, Server, Meal, Customization, \
    Order, OrderItem, OrderItemCustomization

# Custom user model display on admin dashboard
@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('name',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    list_display = ('email', 'name', 'is_staff')
    search_fields = ('email', 'name')
    ordering = ('email',)

# Display models on Django admin
admin.site.register(Restaurant)
admin.site.register(Customer)
admin.site.register(Server)
admin.site.register(Meal)
admin.site.register(Customization)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(OrderItemCustomization)
