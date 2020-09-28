from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from swickapp import views, apis

urlpatterns = [
    # Admin page url
    path('admin/', admin.site.urls),
    # Home page url
    path('', views.home, name='home'),

    ##### RESTAURANT REGISTRATION URLS #####
    # accounts/login/ [name='login']
    # accounts/logout/ [name='logout']
    # accounts/password_change/ [name='password_change']
    # accounts/password_change/done/ [name='password_change_done']
    # accounts/password_reset/ [name='password_reset']
    # accounts/password_reset/done/ [name='password_reset_done']
    # accounts/reset/<uidb64>/<token>/ [name='password_reset_confirm']
    # accounts/reset/done/ [name='password_reset_complete']
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/sign_up/', views.restaurant_sign_up,
        name='sign_up'),

    ##### RESTAURANT URLS #####
    # Restaurant home page url
    path('restaurant/', views.restaurant_home, name='restaurant_home'),
    # Restaurant menu page url
    path('restaurant/menu/', views.restaurant_menu,
        name='restaurant_menu'),
    # Restaurant add meal page url
    path('restaurant/menu/add_meal/', views.restaurant_add_meal,
        name='restaurant_add_meal'),
    # Restaurant edit meal page url
    path('restaurant/menu/edit_meal/<int:meal_id>/', views.restaurant_edit_meal,
        name='restaurant_edit_meal'),
    # Restaurant orders page url
    path('restaurant/orders/', views.restaurant_orders,
        name='restaurant_orders'),
    # Restaurant view order page url
    path('restaurant/view_order/<int:order_id>/', views.restaurant_view_order,
        name='restaurant_view_order'),
    # Restaurant servers page url
    path('restaurant/servers/', views.restaurant_servers,
        name='restaurant_servers'),
    # Restaurant add server page url
    path('restaurant/servers/add_server/', views.restaurant_add_server,
        name='restaurant_add_server'),
    # Restaurant delete server url
    path('restaurant/servers/delete/<int:id>', views.restaurant_delete_server,
        name='restaurant_delete_server'),
    # Restaurant delete server request url
    path('restaurant/servers/delete_request/<int:id>', views.restaurant_delete_server_request,
        name='restaurant_delete_server_request'),
    # Restaurant account page url
    path('restaurant/account/', views.restaurant_account,
        name='restaurant_account'),

    ##### SERVER REGISTRATION URLS #####
    path('server/link_restaurant/<str:token>/', views.server_link_restaurant,
        name='server_link_restaurant'),

    ##### DRFPASSWORDLESS AUTHENICATION URLS #####
    # auth/email/ (send email with callback token)
    # params:
    #   email
    # auth/token/ (receive auth token)
    # params:
    #   email
    #   token (callback)
    path('', include('drfpasswordless.urls')),

    ##### CUSTOMER AND SERVER SHARED API URLS #####
    path('api/update_info/', apis.update_info),

    ##### CUSTOMER API URLS #####
    path('api/customer/create_account/', apis.customer_create_account),
    path('api/customer/get_restaurants/', apis.customer_get_restaurants),
    path('api/customer/get_restaurant/<int:restaurant_id>/', apis.customer_get_restaurant),
    path('api/customer/get_categories/<int:restaurant_id>/', apis.customer_get_categories),
    path('api/customer/get_menu/<int:restaurant_id>/<str:category>/', apis.customer_get_menu),
    path('api/customer/get_meal/<int:meal_id>/', apis.customer_get_meal),
    path('api/customer/place_order/', apis.customer_place_order),
    path('api/customer/get_orders/', apis.customer_get_orders),
    path('api/customer/get_order_details/<int:order_id>/', apis.customer_get_order_details),
    path('api/customer/get_info/', apis.customer_get_info),

    ##### SERVER API URLS #####
    path('api/server/create_account/', apis.server_create_account),
    path('api/server/get_orders/<int:status>/', apis.server_get_orders),
    path('api/server/get_order_details/<int:order_id>/', apis.server_get_order_details),
    path('api/server/update_order_status/', apis.server_update_order_status),
    path('api/server/get_info/', apis.server_get_info),
]
