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

    ##### STRIPE REDIRECT URLS #####
    path('accounts/refresh_stripe_link/', views.refresh_stripe_link),

    ##### RESTAURANT URLS #####
    # Home
    path('restaurant/', views.restaurant_home, name='restaurant_home'),
    # Menu
    path('restaurant/menu/', views.restaurant_menu,
        name='restaurant_menu'),
    path('restaurant/menu/add_category/', views.restaurant_add_category,
        name='restaurant_add_category'),
    path('restaurant/menu/edit_category/<int:category_id>/', views.restaurant_edit_category,
        name='restaurant_edit_category'),
    path('restaurant/menu/delete_category/<int:category_id>/', views.restaurant_delete_category,
        name='restaurant_delete_category'),
    path('restaurant/menu/add_meal/<int:category_id>/', views.restaurant_add_meal,
        name='restaurant_add_meal'),
    path('restaurant/menu/edit_meal/<int:meal_id>/', views.restaurant_edit_meal,
        name='restaurant_edit_meal'),
    path('restaurant/menu/delete_meal/<int:meal_id>/', views.restaurant_delete_meal,
        name='restaurant_delete_meal'),
    path('restaurant/menu/enable_meal/<int:meal_id>/', views.restaurant_enable_meal,
        name='restaurant_enable_meal'),
    path('restaurant/menu/disable_meal/<int:meal_id>/', views.restaurant_disable_meal,
        name='restaurant_disable_meal'),
    # Orders
    path('restaurant/orders/', views.restaurant_orders,
        name='restaurant_orders'),
    path('restaurant/orders/view/<int:order_id>/', views.restaurant_view_order,
        name='restaurant_view_order'),
    # Finances
    path('restaurant/finances/', views.restaurant_finances,
        name='restaurant_finances'),
    path('restaurant/finances/add_tax_category', views.restaurant_add_tax_category,
        name='restaurant_add_tax_category'),
    path('restaurant/finances/edit_tax_category/<int:id>', views.restaurant_edit_tax_category,
        name='restaurant_edit_tax_category'),
    path('restaurant/finances/delete_tax_category/<int:id>', views.restaurant_delete_tax_category,
        name='restaurant_delete_tax_category'),
    path('restaurant/finances/popup_tax_category', views.TaxCategoryCreateView.as_view(),
        name='popup_tax_category'),
    path('restaurant/finances/get_tax_categories', views.get_tax_categories,
        name='get_tax_categories'),
    # Requests
    path('restaurant/requests/', views.restaurant_requests,
        name='restaurant_requests'),
    path('restaurant/requests/add/', views.restaurant_add_request,
        name='restaurant_add_request'),
    path('restaurant/requests/edit/<int:id>', views.restaurant_edit_request,
        name='restaurant_edit_request'),
    path('restaurant/requests/delete/<int:id>', views.restaurant_delete_request,
        name='restaurant_delete_request'),
    # Servers
    path('restaurant/servers/', views.restaurant_servers,
        name='restaurant_servers'),
    path('restaurant/servers/add/', views.restaurant_add_server,
        name='restaurant_add_server'),
    path('restaurant/servers/delete/<int:id>', views.restaurant_delete_server,
        name='restaurant_delete_server'),
    path('restaurant/servers/delete_request/<int:id>', views.restaurant_delete_server_request,
        name='restaurant_delete_server_request'),
    # Account
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
    path('api/customer/get_meals/<int:restaurant_id>/<int:category_id>/', apis.customer_get_meals),
    path('api/customer/get_meal/<int:meal_id>/', apis.customer_get_meal),
    path('api/customer/place_order/', apis.customer_place_order),
    path('api/customer/retry_payment/', apis.customer_retry_payment),
    path('api/customer/get_orders/', apis.customer_get_orders),
    path('api/customer/get_order_details/<int:order_id>/', apis.customer_get_order_details),
    path('api/customer/get_request_options/<int:restaurant_id>/', apis.customer_get_request_options),
    path('api/customer/make_request/', apis.customer_make_request),
    path('api/customer/get_info/', apis.customer_get_info),
    path('api/customer/setup_card/', apis.customer_setup_card),
    path('api/customer/get_cards/', apis.customer_get_cards),
    path('api/customer/remove_card/', apis.customer_remove_card),

    ##### SERVER API URLS #####
    path('api/server/create_account/', apis.server_create_account),
    path('api/server/get_orders/', apis.server_get_orders),
    path('api/server/get_order/<int:order_id>/', apis.server_get_order),
    path('api/server/get_order_details/<int:order_id>/', apis.server_get_order_details),
    path('api/server/get_order_items_to_cook/', apis.server_get_order_items_to_cook),
    path('api/server/get_items_to_send/', apis.ServerGetItemsToSend.as_view()),
    path('api/server/update_order_item_status/', apis.server_update_order_item_status),
    path('api/server/delete_request/', apis.server_delete_request),
    path('api/server/get_info/', apis.server_get_info),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
