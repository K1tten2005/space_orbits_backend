from django.utils import timezone
from django.contrib.auth.models import User
from django.db import connection
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from orbits_data import ORBITS_DATA
from transitions_data import DRAFT_TRANSITION
from space_orbits.models import Orbit, Transition, OrbitTransition


def orbits(request):
    orbit_height = request.GET.get('orbit_height', '')
    if orbit_height:
        orbits = Orbit.objects.filter(height__istartswith=orbit_height)
    else:
        orbits = Orbit.objects.all()

    draft_transition = Transition.objects.filter(status='draft').first()
    for orbit in orbits:
        orbit.added = orbit.id in OrbitTransition.objects.filter(transition=draft_transition).values_list('orbit_id',
                                                                                                          flat=True)

    return render(request, 'index.html', {
        'orbits': orbits,
        'draft_transition': draft_transition,
        'orbits_to_transfer': len(draft_transition.orbits.all()) if draft_transition else None,
        'orbit_height': orbit_height,
    })


def add_orbit(request, orbit_id):
    orbit = get_object_or_404(Orbit, pk=orbit_id)
    draft_transition = Transition.objects.filter(status='draft').first()
    if draft_transition is None:
        draft_transition = Transition.objects.create(
            planned_date=timezone.now().date(),
            planned_time=timezone.now().time(),
            spacecraft='Спутник',
            user=User.objects.filter(is_superuser=False).first()
        )
        draft_transition.save()
    if OrbitTransition.objects.filter(transition=draft_transition, orbit=orbit).exists():
        orbit_height = request.POST.get('height', '')
        if orbit_height:
            return redirect(f"/?height={orbit_height}")
        else:
            return redirect('orbits')

    orbit_transition = OrbitTransition(
        transition=draft_transition,
        orbit=orbit,
        position=len(draft_transition.orbits.all()) + 1,
    )
    orbit_transition.save()

    orbit_height = request.POST.get('height', '')
    if orbit_height:
        return redirect(f"/?height={orbit_height}")
    else:
        return redirect('orbits')


def orbit(request, orbit_id):
    needed_orbit = Orbit.objects.get(id=orbit_id)
    return render(request, 'orbit.html', {'orbit': needed_orbit})


def transition(request, transition_id):
    transition = get_object_or_404(Transition, pk=transition_id)
    if transition.status == 'deleted':
        return render(request, 'transition.html',
                      {'error': 'Ошибка! Невозможно посмотреть данный переход'})
    if not transition:
        return redirect('orbits')

    orbit_transitions = OrbitTransition.objects.filter(transition=transition).order_by('position')

    orbits = [ot.orbit for ot in orbit_transitions]

    return render(request, 'transition.html', {'transition': transition, 'orbits': orbits,
                                               'num_of_orbits': len(orbits)})


def delete(request, transition_id):
    with connection.cursor() as cursor:
        cursor.execute("UPDATE space_orbits_transition SET status = 'deleted' WHERE id = %s", [transition_id])
    return redirect("orbits")
