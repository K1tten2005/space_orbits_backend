from rest_framework import serializers
from space_orbits.models import *

class OrbitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Orbit
        fields = ['id', 'height', 'type', 'full_description', 'short_description', 'image']

        def get_fields(self):
            new_fields = OrderedDict()
            for name, field in super().get_fields().items():
                field.required = False
                new_fields[name] = field
            return new_fields 
        
class SingleOrbitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Orbit
        fields = ['id', 'height', 'type', 'full_description', 'short_description', 'image', 'status']

class CreateUpdateOrbitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Orbit
        fields = ['id', 'height', 'type', 'full_description', 'short_description']


class TransitionSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    moderator = serializers.SerializerMethodField()

    def get_orbits(self, transition):
        orbit_transition = OrbitTransition.objects.filter(transition=transition)
        orbits = [orbit_transition.orbit for orbit_transition in orbit_transition]
        serializer = OrbitSerializer(orbits, many=True)
        return serializer.data

    def get_user(self, transition):
        return transition.user.username

    def get_moderator(self, transition):
        if transition.moderator:
            return transition.moderator.username
        return None

    class Meta:
        model = Transition
        fields = ['id', 'planned_date', 'planned_time', 'spacecraft', 'user', 'moderator', 'status', 'creation_date', 'formation_date',
                  'completion_date', 'highest_orbit']
        
        def get_fields(self):
            new_fields = OrderedDict()
            for name, field in super().get_fields().items():
                field.required = False
                new_fields[name] = field
            return new_fields
        
class SingleTransitionSerializer(serializers.ModelSerializer):
    orbits = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    moderator = serializers.SerializerMethodField()

    def get_orbits(self, transition):
        orbit_transitions = OrbitTransition.objects.filter(transition=transition)
        
        orbits_data = []
        for orbit_transition in orbit_transitions:
            orbit_data = OrbitSerializer(orbit_transition.orbit).data
            orbit_data['position'] = orbit_transition.position
            orbits_data.append(orbit_data)
        
        return orbits_data
    
    def get_user(self, transition):
        return transition.user.username

    def get_moderator(self, transition):
        if transition.moderator:
            return transition.moderator.username
        return None
    
    class Meta:
        model = Transition
        fields = '__all__'


class OrbitTransitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrbitTransition
        fields = '__all__'

        def get_fields(self):
            new_fields = OrderedDict()
            for name, field in super().get_fields().items():
                field.required = False
                new_fields[name] = field
            return new_fields 


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'password', 'first_name', 'last_name', 'username')
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            email=validated_data.get("email", ""),
        )
        return user

    def update(self, instance, validated_data):
        instance.email = validated_data.get("email", instance.email)
        if "password" in validated_data:
            instance.set_password(validated_data["password"])
        instance.save()
        return instance

