"""
maps/activity_tags.py
=====================

A specialized ontology focused strictly on activities and experiences.
Derived from the master tags.py ontology.

This file provides a clean, consolidated vocabulary for systems that 
need to generate, rank, or filter specific activities (like N5/N6) 
without pulling in non-activity tags (like terrain, vibes, or budget).
"""

from .tags import (
    ACTIVITIES_LAND,
    ACTIVITIES_WATER,
    ACTIVITIES_LEISURE,
    ECOSYSTEM,
    FOOD,
    CULTURE,
    SPECIAL_INTEREST,
)

# Pulling cross-category tags from tags.py that function primarily as activities
CROSS_CATEGORY_ACTIVITIES = {
    "birdwatching": ECOSYSTEM["birdwatching"],
    "meditation": CULTURE["meditation"],
    "food tour": FOOD["food tour"],
    "photography tour": SPECIAL_INTEREST["photography tour"],
}

# The master dictionary of all valid activity tags
ALL_ACTIVITIES: dict[str, str] = {
    **ACTIVITIES_LAND,
    **ACTIVITIES_WATER,
    **ACTIVITIES_LEISURE,
    **CROSS_CATEGORY_ACTIVITIES,
}

# Grouped dictionary for UI or structured retrieval purposes
ACTIVITY_CATEGORIES = {
    "Land & Adventure": ACTIVITIES_LAND,
    "Water & Beach": ACTIVITIES_WATER,
    "Leisure & Culture": ACTIVITIES_LEISURE,
    "Special Interest": CROSS_CATEGORY_ACTIVITIES,
}
