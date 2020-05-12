from django.contrib import admin
from django.urls import path, include
from swickapp import views
from django.conf.urls.static import static
from django.conf import settings

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
        name = 'sign_up'),

    ##### RESTAURANT URLS #####
    # Restaurant home page url
    path('restaurant/', views.restaurant_home, name = 'restaurant_home'),
    # Restaurant menu page url
    path('restaurant/menu/', views.restaurant_menu,
        name = 'restaurant_menu'),
    # Restaurant add meal page url
    path('restaurant/menu/add_meal', views.restaurant_add_meal,
        name = 'restaurant_add_meal'),
    # Restaurant edit meal page url
    path('restaurant/menu/edit_meal/<int:meal_id>/', views.restaurant_edit_meal,
        name = 'restaurant_edit_meal'),
    # Restaurant order history page url
    path('restaurant/order_history/', views.restaurant_order_history,
        name = 'restaurant_order_history'),
    # Restaurant servers page url
    path('restaurant/servers/', views.restaurant_servers,
        name = 'restaurant_servers'),
    # Restaurant account page url
    path('restaurant/account/', views.restaurant_account,
        name = 'restaurant_account'),

    # Facebook authentication
    # /api/social/convert-token POST request to get Django access token
    # grant_type: convert-token
    # client_id: [in Django -> Applications]
    # client_secret: [in Django -> Applications]
    # backend: facebook
    # token: [Facebook access token], get test user token from:
    #   https://developers.facebook.com/tools/explorer
    # user_type: [customer or server]
    # /revoke-token POST request to delete Django access token
    # client_id: [in Django -> Applications]
    # client_secret: [in Django -> Applications]
    # token: [Django -> Access tokens]
    path('api/social/', include('rest_framework_social_oauth2.urls')),

# Specify where images should be stored
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
