"""swick URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from swickapp import views
from django.contrib.auth import views as auth_views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    # Admin page url
    path('admin/', admin.site.urls),
    # Home page url
    path('', views.home, name='home'),
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
# Specify where images should be stored
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
