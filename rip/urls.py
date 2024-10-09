"""
URL configuration for rip project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from django.urls import include, path

from rip import settings
from space_orbits import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('orbits/', views.orbits, name='orbits'),
    path('orbits/<int:orbit_id>/', views.orbit, name='orbit'),
    path('transition/<int:transition_id>/', views.transition, name='transition'),
    path('transition/<int:transition_id>/delete/', views.delete, name='transition_delete'),
    path('orbits/<int:orbit_id>/add_orbit/', views.add_orbit, name='transition'),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_URL)

