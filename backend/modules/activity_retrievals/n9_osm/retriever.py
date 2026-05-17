import os
import json
import logging
import math
import requests
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def fetch_osm_nearby(lat: float, lng: float, radius: int = 20000) -> list:
    """
    Fetches activities (POIs) from OpenStreetMap via Overpass API using a bounding box.
    """
    # Calculate Bounding Box
    # 1 degree of latitude is ~111.32 km
    d_lat = (radius / 1000.0) / 111.32
    # 1 degree of longitude is ~111.32 * cos(latitude)
    d_lng = (radius / 1000.0) / (111.32 * math.cos(math.radians(lat)))
    
    west = lng - d_lng
    south = lat - d_lat
    east = lng + d_lng
    north = lat + d_lat

    # Cache file
    cache_file = CACHE_DIR / f"osm_nearby_{lat}_{lng}_{radius}.json"
    
    if cache_file.exists():
        logger.info(f"Cache hit! Loading data from {cache_file}")
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)

    logger.info(f"Cache miss. Fetching from OSM for bounding box: {west},{south},{east},{north}...")

    # Using lz4 endpoint for faster queries
    overpass_url = "https://lz4.overpass-api.de/api/interpreter"
    
    # Query for tourism, historic sites, parks, cafes, restaurants, malls (must have a name)
    # Using NW (node, way) instead of NWR to avoid massive relation geometry calculations which cause timeouts.
    overpass_query = f"""
    [out:json][timeout:90];
    (
      nw["tourism"]["name"]({south},{west},{north},{east});
      nw["historic"]["name"]({south},{west},{north},{east});
      nw["leisure"]["name"]({south},{west},{north},{east});
      nw["amenity"="cafe"]["name"]({south},{west},{north},{east});
      nw["amenity"="restaurant"]["name"]({south},{west},{north},{east});
      nw["shop"="mall"]["name"]({south},{west},{north},{east});
    );
    out center;
    """
    
    headers = {
        "User-Agent": "travel-exp-planner-n9/1.0",
        "Accept": "application/json"
    }
    
    activities = []
    
    try:
        response = requests.post(overpass_url, data={'data': overpass_query}, headers=headers, timeout=90)
        response.raise_for_status()
        data = response.json()
        
        activities = data.get('elements', [])
            
        # Save to cache immediately
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(activities, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Successfully fetched and cached {len(activities)} activities from OSM.")
        
    except Exception as e:
        logger.error(f"Error fetching activities from OSM: {e}")
        
    return activities

if __name__ == "__main__":
    TEST_LOCATION = {
        "location_id": "loc_001",
        "name": "Fansipan Sapa",
        "lat": 22.30,
        "lng": 103.77
    }
    
    loc_id = TEST_LOCATION["location_id"]
    loc_name = TEST_LOCATION["name"]
    lat = TEST_LOCATION["lat"]
    lng = TEST_LOCATION["lng"]
    
    logger.info(f"Starting N9 OSM Retrieval for: {loc_name} at {lat}, {lng}")
    
    # Fetch everything in a 20km radius (20000 meters)
    results = fetch_osm_nearby(lat=lat, lng=lng, radius=20000)
    
    output_file = Path(__file__).parent / f"{loc_id}_osm_activities.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print(f"\n--- OSM RESULTS FOR {loc_name.upper()} ---")
    for r in results[:5]:  # Print first 5 for preview
        tags = r.get('tags', {})
        name = tags.get('name') or tags.get('name:en') or 'Unknown'
        print(f"- {name} (Type: {tags.get('amenity') or tags.get('tourism', 'unknown')})")
    print(f"... and {len(results) - 5} more." if len(results) > 5 else "")
    print(f"Saved {len(results)} activities to {output_file}")
