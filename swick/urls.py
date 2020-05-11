from django.contrib import admin
from django.urls import path, include
from swickapp import views
from django.contrib.auth import views as auth_views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    # Admin page url
    path('admin/', admin.site.urls),
    # Home page url
    path('', views.home, name='home'),

    ##### RESTAURANT URLS #####
    # Restaurant home page url
    path('restaurant/', views.restaurant_home, name = 'restaurant-home'),
    # Restaurant login url
    # registration/login.html is automatically set as template
    path('restaurant/login/', auth_views.LoginView.as_view(),
        name = 'restaurant-login'),
    # Restaurant logout url
    path('restaurant/logout/', auth_views.LogoutView.as_view(),
        {'next_page': '/'}, name = 'restaurant-logout'),
    # Restaurant sign-up url
    path('restaurant/sign-up/', views.restaurant_sign_up,
        name = 'restaurant-sign-up'),

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
