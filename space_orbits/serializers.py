from rest_framework import serializers

from space_orbits.models import *

class OrbitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Orbit
        fields = '__all__'

class TransitionSerializer(serializers.ModelSerializer):
    orbits = serializers.SerializerMethodField()
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
        fields = '__all__'

class OrbitTransitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrbitTransition
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'first_name', 'last_name', 'email', 'date_joined')

class UserRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'first_name', 'last_name', 'email')
        write_only_fields = ('password',)
        read_only_fields = ('id',)

    def create(self, validated_data):
        user = User.objects.create(
            username=validated_data['username'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            email=validated_data['email'],
        )

        user.set_password(validated_data['password'])
        user.save()
        return user

class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)
