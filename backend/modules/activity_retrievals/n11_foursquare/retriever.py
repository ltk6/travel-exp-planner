import os
import json
import logging
import requests
from pathlib import Path
from dotenv import load_dotenv
# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
FOURSQUARE_API_KEY = os.getenv("FOURSQUARE_API_KEY", "").strip()

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def fetch_foursquare_nearby(lat: float, lng: float, radius: int = 20000) -> list:
    """
    Fetches places nearby a location using Foursquare Places API (v3).
    Uses caching to preserve the $200 free usage limit.
    """
    if not FOURSQUARE_API_KEY:
        logger.error("FOURSQUARE_API_KEY not found in environment variables. Please add it to your .env file.")
        return []

    # Cache key based on coordinates and radius
    cache_file = CACHE_DIR / f"foursquare_nearby_{lat}_{lng}_{radius}.json"
    
    # Caching check
    if cache_file.exists():
        logger.info(f"Cache hit! Loading data from {cache_file}")
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)

    logger.info(f"Cache miss. Fetching from Foursquare API for location {lat}, {lng}...")
    
    url = "https://places-api.foursquare.com/places/search"
    
    # Handle new Service API Keys which act as Bearer tokens
    auth_header = FOURSQUARE_API_KEY
    if not auth_header.startswith("fsq3") and not auth_header.startswith("Bearer"):
        auth_header = f"Bearer {auth_header}"
        
    headers = {
        "Accept": "application/json",
        "Authorization": auth_header,
        "X-Places-Api-Version": "2025-06-17"
    }
    
    params = {
        "ll": f"{lat},{lng}",
        "radius": radius,
        "limit": 50, # Foursquare max limit per request
        "sort": "RATING" # Get the best places first
    }
    
    activities = []
    
    try:
        while url:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if not response.ok:
                logger.error(f"Foursquare Error Body: {response.text}")
            response.raise_for_status()
            data = response.json()
            
            # Don't format, just dump raw
            activities.extend(data.get("results", []))
                
            # Foursquare pagination via Link header
            link_header = response.headers.get("Link", "")
            next_url = None
            if 'rel="next"' in link_header:
                links = link_header.split(",")
                for link in links:
                    if 'rel="next"' in link:
                        next_url = link[link.find("<")+1:link.find(">")]
            
            url = next_url
            params = None # The next_url already contains the cursor and params
            
        # Save to cache immediately
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(activities, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Successfully fetched and cached {len(activities)} activities from Foursquare.")
        
    except Exception as e:
        logger.error(f"Error fetching from Foursquare API: {e}")
        
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
    
    logger.info(f"Starting N11 Foursquare Retrieval for: {loc_name} at {lat}, {lng}")
    
    results = fetch_foursquare_nearby(lat=lat, lng=lng, radius=20000)
    
    output_file = Path(__file__).parent / f"{loc_id}_foursquare_activities.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print(f"\n--- FOURSQUARE RESULTS FOR {loc_name.upper()} ---")
    for r in results[:5]:
        cats = [c.get('name', 'Unknown') for c in r.get('categories', [])]
        print(f"- {r.get('name', 'Unknown')} (Categories: {', '.join(cats)})")
    print(f"... and {len(results) - 5} more." if len(results) > 5 else "")
    print(f"Saved {len(results)} activities to {output_file}")
