import os
import json
import logging
import math
import subprocess
from pathlib import Path
# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def fetch_overture_nearby(lat: float, lng: float, radius: int = 20000) -> list:
    """
    Fetches places nearby a location using Overture Maps Foundation open data.
    Uses overturemaps CLI to download data for a bounding box.
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
    
    # Cache files
    cache_file = CACHE_DIR / f"overture_nearby_{lat}_{lng}_{radius}.geojson"
    json_cache_file = CACHE_DIR / f"overture_nearby_{lat}_{lng}_{radius}_parsed.json"
    
    if json_cache_file.exists():
        logger.info(f"Cache hit! Loading parsed data from {json_cache_file}")
        with open(json_cache_file, "r", encoding="utf-8") as f:
            return json.load(f)

    logger.info(f"Cache miss. Fetching from Overture Maps for bounding box: {west},{south},{east},{north}...")
    
    if not cache_file.exists():
        # Requires overturemaps to be installed: pip install overturemaps
        cmd = [
            "overturemaps", "download",
            "--bbox", f"{west},{south},{east},{north}",
            "--type", "place",
            "-f", "geojson",
            "-o", str(cache_file)
        ]
        
        try:
            logger.info("Running overturemaps CLI. This may take a moment as it queries massive datasets...")
            
            # Force UTF-8 encoding for Windows so Vietnamese characters don't crash the CLI
            env = os.environ.copy()
            env["PYTHONUTF8"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"
            
            subprocess.run(cmd, check=True, env=env)
        except FileNotFoundError:
            logger.error("overturemaps CLI not found. Please install it using: pip install overturemaps")
            return []
        except subprocess.CalledProcessError as e:
            logger.error(f"Error executing overturemaps CLI: {e}")
            return []

    # Parse the GeoJSON file to our standard format
    activities = []
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            geojson_data = json.load(f)
            
        # Overture is free and open data (no API key needed), so no limits
        # Don't format, just dump raw features
        activities.extend(geojson_data.get("features", []))
            
        # Save parsed JSON to cache
        with open(json_cache_file, "w", encoding="utf-8") as f:
            json.dump(activities, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Successfully parsed and cached {len(activities)} activities from Overture.")
        
    except Exception as e:
        logger.error(f"Error parsing Overture GeoJSON: {e}")
        
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
    
    logger.info(f"Starting N12 Overture Retrieval for: {loc_name} at {lat}, {lng}")
    
    results = fetch_overture_nearby(lat=lat, lng=lng, radius=20000)
    
    if results:
        output_file = Path(__file__).parent / f"{loc_id}_overture_activities.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
            
        print(f"\n--- OVERTURE RESULTS FOR {loc_name.upper()} ---")
        for r in results[:5]:
            props = r.get('properties', {})
            name = props.get('primary_name', 'Unknown')
            cat = props.get('categories', {}).get('main', 'Unknown') if props.get('categories') else 'Unknown'
            print(f"- {name} (Category: {cat})")
        print(f"... and {len(results) - 5} more." if len(results) > 5 else "")
        print(f"Saved {len(results)} activities to {output_file}")
