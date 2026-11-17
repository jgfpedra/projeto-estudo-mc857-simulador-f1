"""Cruzamento conservador de circuitos históricos por localização e ano."""
import math
import re


def distance_km(lat1, lon1, lat2, lon2):
    return math.hypot((lat1-lat2)*111.2, (lon1-lon2)*111.2*math.cos(math.radians(lat1)))


def year_in_ranges(year, ranges):
    for text in ranges or []:
        match = re.fullmatch(r'\s*(\d{4})(?:\s*[-–]\s*(\d{4}))?\s*', str(text))
        if match and int(match.group(1)) <= year <= int(match.group(2) or match.group(1)):
            return True
    return False


def find_circuit(lat, lon, circuits, layouts, years):
    if lat is None or lon is None or not years:
        return None
    choices = []
    for c in circuits:
        loc = c.get('location') or {}
        if loc.get('latitude') is None or loc.get('longitude') is None:
            continue
        km = distance_km(lat, lon, loc['latitude'], loc['longitude'])
        if km > 3:
            continue
        history = layouts.get(c['id'], [])
        score = sum(any(year_in_ranges(year, layout.get('years')) for layout in history) for year in years)
        if score:
            choices.append((score, km, c['id']))
    choices.sort(key=lambda value: (-value[0], value[1], value[2]))
    if not choices or (len(choices) > 1 and choices[0][0] == choices[1][0]):
        return None
    return choices[0][2]

