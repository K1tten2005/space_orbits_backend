from django.contrib import admin
from space_orbits.views import *
from django.urls import include, path
from rest_framework import routers

router = routers.DefaultRouter()

urlpatterns = [
    path('api/orbits/search/', get_orbits_list, name='get_orbits_list'),  # GET
    path('api/orbits/<int:orbit_id>/', get_orbit_by_id, name='get_orbit_by_id'),  # GET
    path('api/orbits/create/', create_orbit, name='create_orbit'),  # POST
    path('api/orbits/<int:orbit_id>/update/', update_orbit, name='update_orbit'),  # PUT
    path('api/orbits/<int:orbit_id>/delete/', delete_orbit, name='delete_orbit'),  # DELETE
    path('api/orbits/<int:orbit_id>/add_orbit_to_transition/', add_orbit_to_transition, name='add_orbit_to_transition'),  # POST
    path('api/orbits/<int:orbit_id>/update_image/', update_orbit_image, name='update_image'),  # POST

    # Набор методов для заявок
    path('api/transitions/search/', get_transitions_list, name=' get_transitions_list'),  # GET
    path('api/transitions/<int:transition_id>/', get_transition_by_id, name='get_transition_by_id'),  # GET
    path('api/transitions/<int:transition_id>/update/', update_transition, name='update_transition'),  # PUT
    path('api/transitions/<int:transition_id>/update_status_user/', update_status_user, name='update_status_user'),  # PUT
    path('api/transitions/<int:transition_id>/update_status_admin/', update_status_admin, name='update_status_admin'),# PUT
    path('api/transitions/<int:transition_id>/delete/', delete_transition, name='delete_transition'),  # DELETE

    # Набор методов для м-м
    path('api/orbit_transitions/<int:orbit_transition_id>/update_orbit_transition/', update_orbit_transition,
         name='update_orbit_transition'),  # PUT
    path('api/orbit_transitions/<int:orbit_transition_id>/delete_orbit_from_transition/', delete_orbit_from_transition,
         name='delete_orbit_from_transition'),  # DELETE

    # Набор методов пользователей
    path('api/users/register/', register, name='register'),  # POST
    path('api/users/login/', login, name='login'),  # POST
    path('api/users/logout/', logout, name='logout'),  # POST
    path('api/users/<int:user_id>/update/', update_user, name='update_user'),  # PUT
]
