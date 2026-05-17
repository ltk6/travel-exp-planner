import os
import json
import logging
import requests
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def fetch_wikidata_nearby(lat: float, lng: float, radius: int = 20000) -> list:
    radius_km = radius / 1000.0
    cache_file = CACHE_DIR / f"wikidata_nearby_{lat}_{lng}_{radius}.json"
    
    if cache_file.exists():
        logger.info(f"Cache hit! Loading data from {cache_file}")
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)

    logger.info(f"Cache miss. Fetching from Wikidata SPARQL for location {lat}, {lng}...")
    
    url = "https://query.wikidata.org/sparql"
    
    # Query for entities within the radius that have coordinates.
    # P31 = "instance of" — dùng để map sang activity_type ở normalizer.
    # Một place có thể có nhiều P31 → DISTINCT để giảm trùng; nếu vẫn duplicate
    # thì normalizer dedupe theo entity Q-ID.
    query = f"""
    SELECT DISTINCT ?place ?placeLabel ?location ?image ?description ?article
                    ?instance_of ?instance_ofLabel WHERE {{
      SERVICE wikibase:around {{
        ?place wdt:P625 ?location .
        bd:serviceParam wikibase:center "Point({lng} {lat})"^^geo:wktLiteral .
        bd:serviceParam wikibase:radius "{radius_km}" .
      }}
      OPTIONAL {{ ?place wdt:P18 ?image. }}
      OPTIONAL {{ ?place schema:description ?description. FILTER(LANG(?description) = "en") }}
      OPTIONAL {{
        ?article schema:about ?place .
        ?article schema:inLanguage "en" .
        ?article schema:isPartOf <https://en.wikipedia.org/> .
      }}
      OPTIONAL {{ ?place wdt:P31 ?instance_of. }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    """
    
    headers = {
        "User-Agent": "travel-exp-planner-n13/1.0",
        "Accept": "application/sparql-results+json"
    }
    
    activities = []
    
    try:
        response = requests.get(url, params={"query": query}, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Raw dump of the bindings
        activities.extend(data.get("results", {}).get("bindings", []))
            
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(activities, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Successfully fetched and cached {len(activities)} activities from Wikidata.")
        
    except Exception as e:
        logger.error(f"Error fetching from Wikidata API: {e}")
        
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
    
    logger.info(f"Starting N13 Wikidata Retrieval for: {loc_name} at {lat}, {lng}")
    
    results = fetch_wikidata_nearby(lat=lat, lng=lng, radius=20000)
    
    output_file = Path(__file__).parent / f"{loc_id}_wikidata_activities.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print(f"\n--- WIKIDATA RESULTS FOR {loc_name.upper()} ---")
    for r in results[:5]:
        name = r.get("placeLabel", {}).get("value", "Unknown")
        desc = r.get("description", {}).get("value", "No description")
        print(f"- {name} (Description: {desc})")
    print(f"... and {len(results) - 5} more." if len(results) > 5 else "")
    print(f"Saved {len(results)} activities to {output_file}")
