import os
import json
import logging
import requests
from pathlib import Path
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY", "").strip()

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def fetch_geoapify_nearby(lat: float, lng: float, radius: int = 20000) -> list:
    if not GEOAPIFY_API_KEY:
        logger.error("GEOAPIFY_API_KEY not found in environment variables. Please add it to your .env file.")
        return []

    cache_file = CACHE_DIR / f"geoapify_nearby_{lat}_{lng}_{radius}.json"
    
    if cache_file.exists():
        logger.info(f"Cache hit! Loading data from {cache_file}")
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)

    logger.info(f"Cache miss. Fetching from Geoapify API for location {lat}, {lng}...")
    
    url = "https://api.geoapify.com/v2/places"
    
    # Categories: catering (food), entertainment, leisure, natural, tourism
    categories = "catering,entertainment,leisure,natural,tourism"
    
    params = {
        "categories": categories,
        "filter": f"circle:{lng},{lat},{radius}",
        "limit": 500, # Geoapify allows up to 500 results per request
        "apiKey": GEOAPIFY_API_KEY
    }
    
    activities = []
    
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        # Geoapify returns a FeatureCollection. We dump the raw features.
        activities.extend(data.get("features", []))
            
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(activities, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Successfully fetched and cached {len(activities)} activities from Geoapify.")
        
    except Exception as e:
        logger.error(f"Error fetching from Geoapify API: {e}")
        if 'response' in locals() and hasattr(response, 'text'):
            logger.error(f"Response body: {response.text}")
            
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
    
    logger.info(f"Starting N14 Geoapify Retrieval for: {loc_name} at {lat}, {lng}")
    
    results = fetch_geoapify_nearby(lat=lat, lng=lng, radius=20000)
    
    output_file = Path(__file__).parent / f"{loc_id}_geoapify_activities.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print(f"\n--- GEOAPIFY RESULTS FOR {loc_name.upper()} ---")
    for r in results[:5]:
        props = r.get("properties", {})
        print(f"- {props.get('name', 'Unknown')} (Categories: {', '.join(props.get('categories', []))})")
    print(f"... and {len(results) - 5} more." if len(results) > 5 else "")
    print(f"Saved {len(results)} activities to {output_file}")
