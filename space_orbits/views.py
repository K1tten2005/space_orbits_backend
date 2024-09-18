from django.http import HttpResponse
from django.shortcuts import render
from orbits_data import ORBITS_DATA
from transitions_data import DRAFT_TRANSITION

def orbits(request):
    orbit_height = request.GET.get('orbit_height', '')
    orbits = search_orbit(orbit_height)
    orbits_to_transfer = sum(1 for orbit in DRAFT_TRANSITION['orbits'])
    return render(request, 'index.html', {
        'orbits': orbits,
        'orbit_height': orbit_height,
        'draft_transition': DRAFT_TRANSITION,
        'orbits_to_transfer': orbits_to_transfer,
    })


def orbit(request, orbit_id):
    orbit = get_orbit_by_id(orbit_id)
    if not orbit:
        return render(request, '404.html', status=404)
    return render(request, 'orbit.html', {'orbit': orbit})

def transition(request, transition_id):
    transition = get_transition_by_id(transition_id)
    return render(request, 'transition.html', {'transition': transition})


def get_orbit_by_id(orbit_id):
    for orbit in ORBITS_DATA:
        if orbit_id == orbit['id']:
            return orbit
    return None


def search_orbit(orbit_height):
    result = []
    for orbit in ORBITS_DATA:
        if orbit_height in orbit["orbit_height"]:
            result.append(orbit)
    return result


def get_transition_by_id(transition_id):
    return DRAFT_TRANSITION
