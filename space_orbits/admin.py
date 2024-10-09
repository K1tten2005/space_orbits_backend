from django.contrib import admin
from .models import Orbit, OrbitTransition, Transition

admin.site.register(Orbit)
admin.site.register(OrbitTransition)
admin.site.register(Transition)

