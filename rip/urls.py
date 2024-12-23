from django.contrib import admin
from space_orbits.views import *
from django.urls import include, path
from rest_framework import routers, permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


schema_view = get_schema_view(
   openapi.Info(
      title="Orbit transitions API",
      default_version='v1',
      description="API for orbit transitions",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="nikvop05@mail.ru"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)


urlpatterns = [
   path("admin/", admin.site.urls),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),

    path('api/orbits/', get_orbits_list, name='get_orbits_list'),  # GET
    path('api/orbits/<int:orbit_id>/', get_orbit_by_id, name='get_orbit_by_id'),  # GET
    path('api/orbits/create/', create_orbit, name='create_orbit'),  # POST
    path('api/orbits/<int:orbit_id>/update/', update_orbit, name='update_orbit'),  # PUT
    path('api/orbits/<int:orbit_id>/delete/', delete_orbit, name='delete_orbit'),  # DELETE
    path('api/orbits/<int:orbit_id>/add_to_transition/', add_orbit_to_transition, name='add_orbit_to_transition'),  # POST
    path('api/orbits/<int:orbit_id>/update_image/', update_orbit_image, name='update_image'),  # POST

    # Набор методов для заявок
    path('api/transitions/', get_transitions_list, name=' get_transitions_list'),  # GET
    path('api/transitions/<int:transition_id>/', get_transition_by_id, name='get_transition_by_id'),  # GET
    path('api/transitions/<int:transition_id>/update/', update_transition, name='update_transition'),  # PUT
    path('api/transitions/<int:transition_id>/update_status_user/', update_status_user, name='update_status_user'),  # PUT
    path('api/transitions/<int:transition_id>/update_status_admin/', update_status_admin, name='update_status_admin'),# PUT
    path('api/transitions/<int:transition_id>/delete/', delete_transition, name='delete_transition'),  # DELETE

    # Набор методов для м-м
    path('api/transitions/<int:transition_id>/update_orbit_transition/<int:orbit_id>/', update_orbit_transition,
         name='update_orbit_transition'),  # PUT
    path('api/transitions/<int:transition_id>/delete_orbit_from_transition/<int:orbit_id>/', delete_orbit_from_transition,
         name='delete_orbit_from_transition'),  # DELETE

    # Набор методов пользователей
    path('api/users/register/', register, name='register'),  # POST
    path('api/users/login/', login, name='login'),  # POST
    path('api/users/logout/', logout, name='logout'),  # POST
    path('api/users/update/', update_user, name='update_user'),  # PUT
]
