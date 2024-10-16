from django.db import models
from django.contrib.auth.models import User
from django.db.models import UniqueConstraint


class Orbit(models.Model):
    height = models.IntegerField(verbose_name='Высота орбиты')
    type = models.CharField(max_length=75, verbose_name='Тип орбиты')
    full_description = models.TextField(verbose_name='Полное описание')
    short_description = models.CharField(max_length=200, verbose_name='Короткое описание')
    image = models.URLField(null=True, verbose_name='Изображение')

    STATUS_CHOICES = [
        (True, 'Действует'),
        (False, 'Удален'),
    ]
    status = models.BooleanField(choices=STATUS_CHOICES, default=True, verbose_name="Статус")

    def __str__(self):
        return f"Orbit {self.id} (Высота {self.height} км)"


class Transition(models.Model):
    planned_date = models.DateField(verbose_name='Запланированная дата')
    planned_time = models.TimeField(verbose_name='Запланированное время')
    spacecraft = models.CharField(max_length=50, verbose_name='Космический аппарат')
    user = models.ForeignKey(User, related_name='transitions', on_delete=models.CASCADE, verbose_name='Пользователь')
    moderator = models.ForeignKey(User, related_name='moderated_transitions', on_delete=models.SET_NULL,
                                  null=True, verbose_name='Модератор')
    orbits = models.ManyToManyField(Orbit, through='OrbitTransition')
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('deleted', 'Удален'),
        ('formed', 'Сформирован'),
        ('completed', 'Завершен'),
        ('rejected', 'Отклонен'),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='Статус')

    def __str__(self):
        return f"Transition {self.id} - {self.spacecraft} on {self.planned_date}"


class OrbitTransition(models.Model):
    orbit = models.ForeignKey(Orbit, on_delete=models.CASCADE, verbose_name='Орбита')
    transition = models.ForeignKey(Transition, on_delete=models.CASCADE, verbose_name='Переход')
    position = models.IntegerField(verbose_name='Позиция')

    class Meta:
        unique_together = ('orbit', 'transition')
        constraints = [
            UniqueConstraint(fields=['orbit', 'position'], name='unique_position_per_transition')
        ]

    def __str__(self):
        return f"OrbitTransition (Orbit {self.orbit.id} - Transition {self.transition.id}, Position {self.position})"
