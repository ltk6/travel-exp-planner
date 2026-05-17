import os
import json
import time
import logging
import requests
from pathlib import Path
from dotenv import load_dotenv
# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
GOONG_API_KEY = os.getenv("GOONG_API_KEY")

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def fetch_goong_nearby(lat: float, lng: float, radius: int = 20000, type_filter: str = "") -> list:
    """
    Fetches places nearby a location using Goong API.
    Uses caching to preserve the $100 free usage limit.
    """
    if not GOONG_API_KEY:
        logger.error("GOONG_API_KEY not found in environment variables. Please add it to your .env file.")
        return []

    # Cache key based on coordinates and radius
    cache_file = CACHE_DIR / f"goong_nearby_{lat}_{lng}_{radius}.json"
    
    # Technique 1: Caching to avoid duplicate API charges
    if cache_file.exists():
        logger.info(f"Cache hit! Loading data from {cache_file}")
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)

    logger.info(f"Cache miss. Fetching from Goong API for location {lat}, {lng}...")
    
    url = "https://rsapi.goong.io/Place/Autocomplete"
    
    # Since Goong removed NearbySearch, we must use Autocomplete.
    # Autocomplete requires an 'input' string and returns max 5-10 predictions.
    # We simulate a NearbySearch by querying common travel categories.
    keywords = ["du lịch", "nhà hàng", "cafe", "khách sạn", "resort", "homestay", "chùa", "bảo tàng", "điểm tham quan", "quán ăn"]
    
    activities = []
    seen_ids = set()
    
    try:
        for kw in keywords:
            params = {
                "location": f"{lat},{lng}",
                "radius": radius,
                "input": kw,
                "api_key": GOONG_API_KEY,
                "limit": 10 # Goong autocomplete usually caps at a low number
            }
            
            response = requests.get(url, params=params, timeout=10)
            if not response.ok:
                continue
                
            data = response.json()
            predictions = data.get("predictions", [])
            
            for p in predictions:
                pid = p.get("place_id")
                if pid and pid not in seen_ids:
                    seen_ids.add(pid)
                    activities.append(p)
                    
            # Stop if we reach 100 to stay within budget limit
            if len(activities) >= 100:
                activities = activities[:100]
                break
            
        # Technique 3: Save to cache immediately
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(activities, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Successfully fetched and cached {len(activities)} activities.")
        
    except Exception as e:
        logger.error(f"Error fetching from Goong API: {e}")
        
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
    
    logger.info(f"Starting N10 Goong Retrieval for: {loc_name} at {lat}, {lng}")
    
    # Fetch everything in a 20km radius (20000 meters)
    results = fetch_goong_nearby(lat=lat, lng=lng, radius=20000)
    
    output_file = Path(__file__).parent / f"{loc_id}_goong_activities.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print(f"\n--- GOONG RESULTS FOR {loc_name.upper()} ---")
    for r in results[:5]:  # Print first 5 for preview
        # Autocomplete returns 'description' or 'structured_formatting.main_text'
        name = r.get('structured_formatting', {}).get('main_text') or r.get('description', 'Unknown')
        print(f"- {name} (Type: {', '.join(r.get('types', []))})")
    print(f"... and {len(results) - 5} more." if len(results) > 5 else "")
    print(f"Saved {len(results)} activities to {output_file}")
