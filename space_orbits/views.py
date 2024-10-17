from rest_framework.response import Response
from rest_framework import status
from .serializers import *
from .models import *
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import api_view
from django.utils import timezone
from django.contrib.auth import authenticate
from .minio import *


def get_user():
    return User.objects.filter(is_superuser=False).first()


def get_moderator():
    return User.objects.filter(is_superuser=True).first()


@api_view(['GET'])
def get_orbits_list(request):
    orbit_height = request.GET.get('orbit_height', '')

    orbits = Orbit.objects.filter(status=True).filter(height__istartswith=orbit_height)

    serializer = OrbitSerializer(orbits, many=True)

    draft_transition = Transition.objects.filter(status='draft').first()

    response = {
        'orbits': serializer.data,
        'draft_transition': draft_transition.id if draft_transition else None,
        'orbits_to_transfer': len(draft_transition.orbits.all()) if draft_transition else None,
        'orbit_height': orbit_height,
    }
    return Response(response, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_orbit_by_id(request, orbit_id):
    try:
        orbit = Orbit.objects.get(pk=orbit_id)
    except Orbit.DoesNotExist:
        return Response({'error': 'Орбита не найдена!'}, status=status.HTTP_404_NOT_FOUND)

    serializer = OrbitSerializer(orbit, many=False)
    return Response(serializer.data)


@api_view(['POST'])
def create_orbit(request):
    orbit_data = request.data.copy()
    orbit_data.pop('image', None)
    serializer = OrbitSerializer(data=orbit_data)
    serializer.is_valid(raise_exception=True)

    new_orbit = serializer.save()
    return Response(OrbitSerializer(new_orbit).data, status=status.HTTP_201_CREATED)


@api_view(['PUT'])
def update_orbit(request, orbit_id):
    try:
        orbit = Orbit.objects.get(pk=orbit_id)
    except Orbit.DoesNotExist:
        return Response({'error': 'Орбита не найдена'}, status=status.HTTP_404_NOT_FOUND)

    orbit_data = request.data.copy()
    orbit_data.pop('image', None)

    serializer = OrbitSerializer(orbit, data=orbit_data, partial=True)
    serializer.is_valid(raise_exception=True)
    updated_orbit = serializer.save()

    pic = request.FILES.get('image')
    if pic:
        pic_result = add_pic(updated_orbit, pic)
        if 'error' in pic_result.data:
            return pic_result

    return Response(OrbitSerializer(updated_orbit).data, status=status.HTTP_200_OK)


@api_view(['DELETE'])
def delete_orbit(request, orbit_id):
    try:
        orbit = Orbit.objects.get(pk=orbit_id)
    except Orbit.DoesNotExist:
        return Response({'error': 'Орбита не найдена'}, status=status.HTTP_404_NOT_FOUND)

    orbit.status = False
    orbit.save()

    orbits = Orbit.objects.filter(status=True)
    serializer = OrbitSerializer(orbits, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def add_orbit_to_transition(request, orbit_id):
    try:
        orbit = Orbit.objects.get(pk=orbit_id)
    except Orbit.DoesNotExist:
        return Response({'error': 'Орбита не найдена'}, status=status.HTTP_404_NOT_FOUND)

    draft_transition = Transition.objects.filter(status='draft').first()

    if draft_transition is None:
        draft_transition = Transition.objects.create(
            user_id=get_user().id,
            planned_date=timezone.now().date(),
            planned_time=timezone.now().time(),
            spacecraft='Спутник',
        )
        draft_transition.save()

    if OrbitTransition.objects.filter(transition=draft_transition, orbit=orbit).exists():
        return Response({'error': 'Орбита уже добавлена в перемещение'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    try:
        orbit_transition = OrbitTransition.objects.create(
            transition=draft_transition,
            orbit=orbit,
            position=len(draft_transition.orbits.all()) + 1,
        )
    except Exception as e:
        return Response({'error': f'Ошибка при создании связки: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    serializer = TransitionSerializer(draft_transition)
    return Response(serializer.data.get('orbits', []), status=status.HTTP_200_OK)


@api_view(["POST"])
def update_orbit_image(request, orbit_id):
    try:
        orbit = Orbit.objects.get(pk=orbit_id)
    except Orbit.DoesNotExist:
        return Response({"Ошибка": "Орбита не найдена"}, status=status.HTTP_404_NOT_FOUND)

    image = request.FILES.get("image")

    if image is not None:
        pic_result = add_pic(orbit, image)
        if 'error' in pic_result.data:
            return pic_result

        serializer = OrbitSerializer(orbit)
        return Response(serializer.data, status=status.HTTP_200_OK)

    return Response({"error": "Изображение не предоставлено"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def get_transitions_list(request):
    status = request.GET.get("status", '')
    date_formation_start = request.GET.get("date_formation_start")
    date_formation_end = request.GET.get("date_formation_end")

    transitions = Transition.objects.exclude(status__in=['draft', 'deleted'])

    if status in ['formed', 'completed', 'rejected']:
        transitions = transitions.filter(status=status)

    if date_formation_start and parse_datetime(date_formation_start):
        transitions = transitions.filter(planned_date__gte=parse_datetime(date_formation_start))

    if date_formation_end and parse_datetime(date_formation_end):
        transitions = transitions.filter(planned_date__lt=parse_datetime(date_formation_end))

    serializer = TransitionSerializer(transitions, many=True)

    return Response(serializer.data)


@api_view(["GET"])
def get_transition_by_id(request, transition_id):
    try:
        transition = Transition.objects.get(pk=transition_id)
    except Transition.DoesNotExist:
        return Response({"error": "Переход не найден"}, status=status.HTTP_404_NOT_FOUND)

    serializer = TransitionSerializer(transition, many=False)

    return Response(serializer.data)


@api_view(["PUT"])
def update_transition(request, transition_id):
    try:
        transition = Transition.objects.get(pk=transition_id)
    except Transition.DoesNotExist:
        return Response({"error": "Переход не найден"}, status=status.HTTP_404_NOT_FOUND)

    allowed_fields = ['planned_date', 'planned_time', 'spacecraft']

    data = {key: value for key, value in request.data.items() if key in allowed_fields}

    if not data:
        return Response({"error": "Нет данных для обновления или поля не разрешены"},
                        status=status.HTTP_400_BAD_REQUEST)

    serializer = TransitionSerializer(transition, data=data, partial=True)

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["PUT"])
def update_status_user(request, transition_id):
    try:
        transition = Transition.objects.get(pk=transition_id)
    except Transition.DoesNotExist:
        return Response({"error": "Переход не найден"}, status=status.HTTP_404_NOT_FOUND)

    if transition.status != 'draft':
        return Response({"error": "Переход нельзя изменить, так как он не в статусе 'Черновик'"},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)

    required_fields = ['planned_date', 'planned_time', 'spacecraft']

    missing_fields = [field for field in required_fields if not getattr(transition, field)]

    if missing_fields:
        return Response(
            {"error": f"Не заполнены обязательные поля: {', '.join(missing_fields)}"},
            status=status.HTTP_400_BAD_REQUEST
        )

    transition.status = 'formed'
    transition.formation_date = timezone.now()
    transition.save()

    serializer = TransitionSerializer(transition, many=False)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["PUT"])
def update_status_admin(request, transition_id):
    try:
        transition = Transition.objects.get(pk=transition_id)
    except Transition.DoesNotExist:
        return Response({"error": "Переход не найден"}, status=status.HTTP_404_NOT_FOUND)

    request_status = request.data["status"]

    if request_status not in ['completed', 'rejected']:
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    if transition.status != 'formed':
        return Response({'error': "Переход ещё не сформирован"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    transition.status = request_status
    transition.moderator = get_moderator()
    transition.save()

    serializer = TransitionSerializer(transition, many=False)

    return Response(serializer.data)


@api_view(["DELETE"])
def delete_transition(request, transition_id):
    try:
        transition = Transition.objects.get(pk=transition_id)
    except Transition.DoesNotExist:
        return Response({"error": "Переход не найден"}, status=status.HTTP_404_NOT_FOUND)

    if transition.status != 'draft':
        return Response({'error': 'Нельзя удалить данную заявку'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    transition.status = 'deleted'
    transition.save()
    serializer = TransitionSerializer(transition, many=False)

    return Response(serializer.data)


@api_view(["DELETE"])
def delete_orbit_from_transition(request, orbit_transition_id):
    try:
        orbit_transition = OrbitTransition.objects.get(pk=orbit_transition_id)
    except OrbitTransition.DoesNotExist:
        return Response({"error": "Связь между орбитой и переходом не найдена"}, status=status.HTTP_404_NOT_FOUND)

    transition_id = orbit_transition.transition_id

    orbit_transition.delete()

    try:
        transition = Transition.objects.get(pk=transition_id)
    except Transition.DoesNotExist:
        return Response({"error": "Переход не найден после удаления орбиты"}, status=status.HTTP_404_NOT_FOUND)

    serializer = TransitionSerializer(transition, many=False)

    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["PUT"])
def update_orbit_transition(request, orbit_transition_id):
    try:
        orbit_transition = OrbitTransition.objects.get(pk=orbit_transition_id)
    except OrbitTransition.DoesNotExist:
        return Response({"error": "Переход на орбиту не найден"}, status=status.HTTP_404_NOT_FOUND)

    position = request.data.get("position")

    if position is not None:
        orbit_transition.position = position
        orbit_transition.save()
        serializer = OrbitTransitionSerializer(orbit_transition)
        return Response(serializer.data, status=status.HTTP_200_OK)

    return Response({"error": "Позиция не предоставлена"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def register(request):
    serializer = UserRegisterSerializer(data=request.data)

    if not serializer.is_valid():
        return Response({"error": "Некорректные данные"}, status=status.HTTP_400_BAD_REQUEST)

    user = serializer.save()

    serializer = UserSerializer(user)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["PUT"])
def update_user(request, user_id):
    if not User.objects.filter(pk=user_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    user = User.objects.get(pk=user_id)
    serializer = UserSerializer(user, data=request.data, many=False, partial=True)

    if not serializer.is_valid():
        return Response(status=status.HTTP_409_CONFLICT)

    serializer.save()

    return Response(serializer.data)


@api_view(["POST"])
def login(request):
    serializer = UserLoginSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

    user = authenticate(**serializer.data)
    if user is None:
        return Response(status=status.HTTP_401_UNAUTHORIZED)

    return Response(status=status.HTTP_200_OK)


@api_view(["POST"])
def logout(request):
    return Response(status=status.HTTP_200_OK)
