from rest_framework.response import Response
from rest_framework import status
from .serializers import *
from .models import *
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.db.models import Max
from django.contrib.auth import authenticate
from .minio import *
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import AllowAny
from .authorization import *
from .redis import session_storage
from rest_framework.parsers import FormParser, MultiPartParser
import uuid
from drf_yasg import openapi
from rest_framework.decorators import (
    api_view,
    permission_classes,
    authentication_classes,
    parser_classes,
)


@swagger_auto_schema(
    method="get",
    manual_parameters=[
        openapi.Parameter(
            "orbit_height",
            openapi.IN_QUERY,
            description="Фильтрация по совпадению высоты орбиты",
            type=openapi.TYPE_STRING,
        ),
    ],
    responses={
        status.HTTP_200_OK: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "orbit": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_OBJECT),
                    description="Список найденных орбит",
                ),
                "draft_transition": openapi.Schema(
                    type=openapi.TYPE_NUMBER,
                    description="ID черновика перехода, если существует",
                    nullable=True,
                ),
            },
        ),
        status.HTTP_400_BAD_REQUEST: "Неверный запрос",
        status.HTTP_403_FORBIDDEN: "Доступ запрещен",
    },
)


@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([AuthBySessionIDIfExists])
def get_orbits_list(request):
    orbit_height = request.GET.get('orbit_height', '')

    orbits = Orbit.objects.filter(status=True).filter(height__istartswith=orbit_height)

    serializer = OrbitSerializer(orbits, many=True)

    draft_transition = None
    orbits_to_transfer = None
    if request.user and request.user.is_authenticated:
        try:
            draft_transition = Transition.objects.filter(status='draft', user=request.user).first()
            orbits_to_transfer = len(draft_transition.orbits.all()) if draft_transition else None
        except Transition.DoesNotExist:
            draft_transition = None

    response = {
        'orbits': serializer.data,
        'draft_transition': draft_transition.pk if draft_transition else None,
        'orbits_to_transfer': orbits_to_transfer,
    }
    return Response(response, status=status.HTTP_200_OK)

@swagger_auto_schema(
    method="get",
    manual_parameters=[
        openapi.Parameter(
            name="orbit_id",
            in_=openapi.IN_PATH,
            type=openapi.TYPE_INTEGER,
            description="ID искомой орбиты"
        )
    ],
    responses={
        status.HTTP_200_OK: SingleOrbitSerializer(),
        status.HTTP_404_NOT_FOUND: "Орбита не найдена",
    },
)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_orbit_by_id(request, orbit_id):
    try:
        orbit = Orbit.objects.get(pk=orbit_id)
    except Orbit.DoesNotExist:
        return Response({'error': 'Орбита не найдена'}, status=status.HTTP_404_NOT_FOUND)

    serializer = SingleOrbitSerializer(orbit, many=False)
    return Response(serializer.data)

@swagger_auto_schema(
    method="post",
    request_body=CreateUpdateOrbitSerializer,
    responses={
        status.HTTP_201_CREATED: OrbitSerializer(),
        status.HTTP_400_BAD_REQUEST: "Неверные данные",
        status.HTTP_403_FORBIDDEN: "Вы не вошли в систему как модератор",
    },
)

@api_view(['POST'])
def create_orbit(request):
    orbit_data = request.data.copy()    
    orbit_data.pop('image', None)
    serializer = CreateUpdateOrbitSerializer(data=orbit_data)
    serializer.is_valid(raise_exception=True)

    new_orbit = serializer.save()
    return Response(CreateUpdateOrbitSerializer(new_orbit).data, status=status.HTTP_201_CREATED)


@swagger_auto_schema(
    method="put",
    request_body=CreateUpdateOrbitSerializer,
    manual_parameters=[
        openapi.Parameter(
            name="orbit_id",
            in_=openapi.IN_PATH,
            type=openapi.TYPE_INTEGER,
            description="ID обновляемой орбиты"
        )
    ],
    responses={
        status.HTTP_200_OK: OrbitSerializer(),
        status.HTTP_403_FORBIDDEN: "Вы не вошли в систему как модератор",
        status.HTTP_404_NOT_FOUND: "Орбита не найдена",
        status.HTTP_400_BAD_REQUEST: "Неверные данные",
    },
)

@api_view(['PUT'])
@permission_classes([IsManagerAuth])
def update_orbit(request, orbit_id):
    try:
        orbit = Orbit.objects.get(pk=orbit_id)
    except Orbit.DoesNotExist:
        return Response({'error': 'Орбита не найдена'}, status=status.HTTP_404_NOT_FOUND)

    orbit_data = request.data.copy()
    orbit_data.pop('image', None)

    serializer = CreateUpdateOrbitSerializer(orbit, data=orbit_data, partial=True)
    serializer.is_valid(raise_exception=True)
    updated_orbit = serializer.save()


    return Response(OrbitSerializer(updated_orbit).data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method="delete",
    manual_parameters=[
        openapi.Parameter(
            name="orbit_id",
            in_=openapi.IN_PATH,
            type=openapi.TYPE_INTEGER,
            description="ID удаляемой орбиты"
        )
    ],
    responses={
        status.HTTP_200_OK: OrbitSerializer(many=True),
        status.HTTP_403_FORBIDDEN: "Вы не вошли в систему как модератор",
        status.HTTP_404_NOT_FOUND: "Орбита не найдена",
    },
)


@api_view(['DELETE'])
@permission_classes([IsManagerAuth])
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


@swagger_auto_schema(
    method="post",
    manual_parameters=[
        openapi.Parameter(
            name="orbit_id",
            in_=openapi.IN_PATH,
            type=openapi.TYPE_INTEGER,
            description="ID орбиты, добавляемой в переход"
        )
    ],
    responses={
        status.HTTP_201_CREATED: TransitionSerializer(),
        status.HTTP_404_NOT_FOUND: "Орбита не найдена",
        status.HTTP_400_BAD_REQUEST: "Орбита уже добавлена в черновик",
        status.HTTP_403_FORBIDDEN: "Вы не вошли в систему",
        status.HTTP_500_INTERNAL_SERVER_ERROR: "Ошибка при создании связки",
    },
)
@api_view(['POST'])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
def add_orbit_to_transition(request, orbit_id):
    if not request.user or not request.user.is_authenticated:
        return Response({'error': 'Пользователь не аутентифицирован'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        orbit = Orbit.objects.get(pk=orbit_id)
    except Orbit.DoesNotExist:
        return Response({'error': 'Орбита не найдена'}, status=status.HTTP_404_NOT_FOUND)

    draft_transition = Transition.objects.filter(status='draft', user=request.user).first()

    if draft_transition is None:
        draft_transition = Transition.objects.create(
            creation_date=timezone.now().date(),
            user=request.user
        )

    if OrbitTransition.objects.filter(transition=draft_transition, orbit=orbit).exists():
        return Response({'error': 'Орбита уже добавлена в перемещение'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    try:
        OrbitTransition.objects.create(
            transition=draft_transition,
            orbit=orbit,
            position=len(draft_transition.orbits.all()) + 1,
        )
    except Exception as e:
        return Response({'error': f'Ошибка при создании связки: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    serializer = TransitionSerializer(draft_transition)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@swagger_auto_schema(
    method="post",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "image": openapi.Schema(type=openapi.TYPE_FILE, description="Новое изображение для орбиты"),
        },
        required=["image"]
    ),
    manual_parameters=[
        openapi.Parameter(
            name="orbit_id",
            in_=openapi.IN_PATH,
            type=openapi.TYPE_INTEGER,
            description="ID орбиты, для которой загружается/изменяется изображение"
        )
    ],
    responses={
        status.HTTP_200_OK: OrbitSerializer(),
        status.HTTP_400_BAD_REQUEST: "Изображение не предоставлено",
        status.HTTP_403_FORBIDDEN: "Вы не вошли в систему как модератор",
        status.HTTP_404_NOT_FOUND: "Орбита не найдена",
    },
)

@api_view(["POST"])
@permission_classes([IsManagerAuth])
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



@swagger_auto_schema(
    method="get",
    manual_parameters=[
        openapi.Parameter(
            name="status",
            in_=openapi.IN_QUERY,
            type=openapi.TYPE_STRING,
            description="Фильтр по статусу перехода",
        ),
        openapi.Parameter(
            name="date_formation_start",
            in_=openapi.IN_QUERY,
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_DATETIME,
            description="Начальная дата формирования (формат: YYYY-MM-DDTHH:MM:SS)",
        ),
        openapi.Parameter(
            name="date_formation_end",
            in_=openapi.IN_QUERY,
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_DATETIME,
            description="Конечная дата формирования (формат: YYYY-MM-DDTHH:MM:SS)",
        ),
    ],
    responses={
        status.HTTP_200_OK: TransitionSerializer(many=True),
        status.HTTP_400_BAD_REQUEST: "Некорректный запрос",
        status.HTTP_403_FORBIDDEN: "Вы не вошли в систему",
    },
)

@api_view(["GET"])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
def get_transitions_list(request):
    status = request.GET.get("status", '')
    date_formation_start = request.GET.get("date_formation_start")
    date_formation_end = request.GET.get("date_formation_end")

    transitions = Transition.objects.exclude(status__in=['draft', 'deleted'])

    if not request.user.is_superuser:
        transitions = transitions.filter(user=request.user)

    if status in ['formed', 'completed', 'rejected']:
        transitions = transitions.filter(status=status)

    if date_formation_start and parse_datetime(date_formation_start):
        transitions = transitions.filter(planned_date__gte=parse_datetime(date_formation_start))

    if date_formation_end and parse_datetime(date_formation_end):
        transitions = transitions.filter(planned_date__lt=parse_datetime(date_formation_end))

    serializer = TransitionSerializer(transitions, many=True)

    return Response(serializer.data)


@swagger_auto_schema(
    method="get",
    manual_parameters=[
        openapi.Parameter(
            name="transition_id",
            in_=openapi.IN_PATH,
            type=openapi.TYPE_INTEGER,
            description="ID искомого перехода",
        ),
    ],
    responses={
        status.HTTP_200_OK: SingleTransitionSerializer(),
        status.HTTP_403_FORBIDDEN: "Вы не вошли в систему",
        status.HTTP_404_NOT_FOUND: "Переход не найден",
    },
)

@api_view(["GET"])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
def get_transition_by_id(request, transition_id):
    try:
        transition = Transition.objects.get(pk=transition_id)
    except Transition.DoesNotExist:
        return Response({"error": "Переход не найден"}, status=status.HTTP_404_NOT_FOUND)

    serializer = SingleTransitionSerializer(transition, many=False)

    return Response(serializer.data)


@swagger_auto_schema(
    method="put",
    manual_parameters=[
        openapi.Parameter(
            name="transition_id",
            in_=openapi.IN_PATH,
            type=openapi.TYPE_INTEGER,
            description="ID изменяемой заявки",
        )
    ],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "planned_date": openapi.Schema(
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_DATETIME,
                description="Запланированная дата отправки (формат: YYYY-MM-DDTHH:MM:SS)",
            ),
            "planned_time": openapi.Schema(
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_DATETIME,
                description="Запланированная дата отправки (HH:MM:SS)",
            ),
            "spacecraft": openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Название космического аппарата, соверщающего переход",
            ),
        },
    ),
    responses={
        status.HTTP_200_OK: TransitionSerializer(),
        status.HTTP_400_BAD_REQUEST: "Нет данных для обновления или поля не разрешены",
        status.HTTP_403_FORBIDDEN: "Доступ запрещен",
        status.HTTP_404_NOT_FOUND: "Переход не найден",
    },
)

@api_view(["PUT"])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
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



@swagger_auto_schema(
    method="put",
    manual_parameters=[
        openapi.Parameter(
            name="transition_id",
            in_=openapi.IN_PATH,
            type=openapi.TYPE_INTEGER,
            description="ID отправки, формируемой создателем",
        ),
    ],
    responses={
        status.HTTP_200_OK: TransitionSerializer(),
        status.HTTP_400_BAD_REQUEST: "Не заполнены обязательные поля: [поля, которые не заполнены]",
        status.HTTP_403_FORBIDDEN: "Доступ запрещен",
        status.HTTP_404_NOT_FOUND: "Переход не найден",
        status.HTTP_405_METHOD_NOT_ALLOWED: "Переход не в статусе 'Черновик'",
    },
)

@api_view(["PUT"])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
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
    transition.highest_orbit = transition.orbits.aggregate(max_height=Max('height'))['max_height']
    transition.formation_date = timezone.now().date()
    transition.save()

    serializer = TransitionSerializer(transition, many=False)
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method="put",
    manual_parameters=[
        openapi.Parameter(
            name="transition_id",
            in_=openapi.IN_PATH,
            type=openapi.TYPE_INTEGER,
            description="ID заявки, обрабатываемой модератором",
        ),
    ],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "status": openapi.Schema(
                type=openapi.TYPE_INTEGER,
                description="Новый статус перехода ('completed' для завершения, 'rejected' для отклонения)",
            ),
        },
        required=["status"],
    ),
    responses={
        status.HTTP_200_OK: TransitionSerializer(),
        status.HTTP_403_FORBIDDEN: "Вы не вошли в систему как модератор",
        status.HTTP_404_NOT_FOUND: "Переход не найден",
        status.HTTP_405_METHOD_NOT_ALLOWED: "Переход не статусе 'Сформирован'",
    },
)

@api_view(["PUT"])
@permission_classes([IsManagerAuth])
@authentication_classes([AuthBySessionID])
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
    transition.moderator = request.user
    transition.completion_date = timezone.now().date()
    transition.save()

    serializer = TransitionSerializer(transition, many=False)

    return Response(serializer.data)


@swagger_auto_schema(
    method="delete",
    manual_parameters=[
        openapi.Parameter(
            name="transition_id",
            in_=openapi.IN_PATH,
            type=openapi.TYPE_INTEGER,
            description="ID удаляемого перехода",
        ),
    ],
    responses={
        status.HTTP_200_OK: TransitionSerializer(),
        status.HTTP_403_FORBIDDEN: "Доступ запрещен",
        status.HTTP_404_NOT_FOUND: "Переход не найден",
        status.HTTP_405_METHOD_NOT_ALLOWED: "Удаление возможно только для перехода в статусе 'Черновик'",
    },
)

@api_view(["DELETE"])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
def delete_transition(request, transition_id):
    try:
        transition = Transition.objects.get(pk=transition_id)
    except Transition.DoesNotExist:
        return Response({"error": "Переход не найден"}, status=status.HTTP_404_NOT_FOUND)
    
    if not request.user.is_superuser and transition.user != request.user:
        return Response(status=status.HTTP_403_FORBIDDEN)

    if transition.status != 'draft':
        return Response({'error': 'Нельзя удалить данный переход'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    transition.status = 'deleted'
    transition.save()
    serializer = TransitionSerializer(transition, many=False)

    return Response(serializer.data)


@swagger_auto_schema(
    method="delete",
    manual_parameters=[
        openapi.Parameter(
            name="orbit_id",
            in_=openapi.IN_PATH,
            type=openapi.TYPE_INTEGER,
            description="ID орбиты в переходе"
        ),
        openapi.Parameter(
            name="transition_id",
            in_=openapi.IN_PATH,
            type=openapi.TYPE_INTEGER,
            description="ID перехода"
        ),
    ],
    responses={
        status.HTTP_200_OK: TransitionSerializer(),
        status.HTTP_403_FORBIDDEN: "Доступ запрещен",
        status.HTTP_404_NOT_FOUND: "Связь между орбитой и переходом не найдена",
    },
)

@api_view(["DELETE"])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
def delete_orbit_from_transition(request, orbit_id, transition_id):
    try:
        orbit_transition = OrbitTransition.objects.get(orbit_id=orbit_id, transition_id=transition_id)
    except OrbitTransition.DoesNotExist:
        return Response({"error": "Связь между орбитой и переходом не найдена"}, status=status.HTTP_404_NOT_FOUND)

    if not request.user.is_superuser and orbit_transition.transition.user != request.user:
        return Response(status=status.HTTP_403_FORBIDDEN)
    
    orbit_transition.delete()

    remaining_orbits = OrbitTransition.objects.filter(transition_id=transition_id).order_by('position')
    
    for index, orbit in enumerate(remaining_orbits, start=1):
        orbit.position = index
        orbit.save()

    try:
        transition = Transition.objects.get(pk=transition_id)
    except Transition.DoesNotExist:
        return Response({"error": "Переход не найден после удаления орбиты"}, status=status.HTTP_404_NOT_FOUND)

    serializer = TransitionSerializer(transition, many=False)
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method="put",
    manual_parameters=[
        openapi.Parameter(
            name="orbit_id",
            in_=openapi.IN_PATH,
            type=openapi.TYPE_INTEGER,
            description="ID орбиты в переходе"
        ),
        openapi.Parameter(
            name="transition_id",
            in_=openapi.IN_PATH,
            type=openapi.TYPE_INTEGER,
            description="ID перехода"
        ),
    ],
    responses={
        status.HTTP_200_OK: OrbitTransitionSerializer(),
        status.HTTP_403_FORBIDDEN: "Доступ запрещен",
        status.HTTP_404_NOT_FOUND: "Переход не найден",
    },
)

@api_view(["PUT"])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
def update_orbit_transition(request, orbit_id, transition_id):
    try:
        orbit_transition = OrbitTransition.objects.get(orbit_id=orbit_id, transition_id=transition_id)
    except OrbitTransition.DoesNotExist:
        return Response({"error": "Связь между орбитой и переходом не найдена"}, status=status.HTTP_404_NOT_FOUND)

    current_position = orbit_transition.position

    if current_position == 1:
        return Response({"error": "Позиция уже минимальная (1), нельзя уменьшить"}, status=status.HTTP_400_BAD_REQUEST)

    new_position = current_position - 1

    OrbitTransition.objects.filter(
        transition_id=transition_id,
        position=new_position
    ).update(position=current_position)

    orbit_transition.position = new_position
    orbit_transition.save()

    serializer = OrbitTransitionSerializer(orbit_transition)
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method="post",
    request_body=UserSerializer,
    responses={
        status.HTTP_201_CREATED: "Created",
        status.HTTP_400_BAD_REQUEST: "Bad Request",
    },
)

@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method="post",
    manual_parameters=[
        openapi.Parameter(
            "username",
            type=openapi.TYPE_STRING,
            description="username",
            in_=openapi.IN_FORM,
            required=True,
        ),
        openapi.Parameter(
            "password",
            type=openapi.TYPE_STRING,
            description="password",
            in_=openapi.IN_FORM,
            required=True,
        ),
    ],
    responses={
        status.HTTP_200_OK: "OK",
        status.HTTP_400_BAD_REQUEST: "Bad Request",
    },
)


@api_view(["POST"])
@parser_classes((MultiPartParser, FormParser))
@permission_classes([AllowAny])
def login(request):
    username = request.data.get("username")
    password = request.data.get("password")
    user = authenticate(username=username, password=password)
    if user is not None:
        session_id = str(uuid.uuid4())
        session_storage.set(session_id, username)
        response = Response(status=status.HTTP_200_OK)
        response.set_cookie("session_id", session_id, samesite="Lax")
        return response
    return Response(
        {"error": "Invalid Credentials"}, status=status.HTTP_400_BAD_REQUEST
    )


@swagger_auto_schema(
    method="post",
    responses={
        status.HTTP_204_NO_CONTENT: "No content",
        status.HTTP_403_FORBIDDEN: "Forbidden",
    },
)

@api_view(["POST"])
@permission_classes([IsAuth])
def logout(request):
    session_id = request.COOKIES["session_id"]
    if session_storage.exists(session_id):
        session_storage.delete(session_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response(status=status.HTTP_403_FORBIDDEN)



@swagger_auto_schema(
    method="put",
    request_body=UserSerializer,
    responses={
        status.HTTP_200_OK: UserSerializer(),
        status.HTTP_400_BAD_REQUEST: "Bad Request",
        status.HTTP_403_FORBIDDEN: "Forbidden",
    },
)

@api_view(["PUT"])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
def update_user(request):
    serializer = UserSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




