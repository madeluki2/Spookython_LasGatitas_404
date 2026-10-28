import urllib.request
import urllib.parse
import json

overpass_url = "https://overpass-api.de/api/interpreter"
# Manta bounding box: South, West, North, East
query = """
[out:json][timeout:30];
(
  way["highway"~"primary|secondary|tertiary|residential|trunk"](-0.970,-80.750,-0.940,-80.680);
);
out body;
>;
out skel qt;
"""

data = urllib.parse.urlencode({"data": query}).encode("utf-8")
req = urllib.request.Request(overpass_url, data=data, headers={"User-Agent": "SpookythonMantaBot/1.0"})

try:
    print("Sending query to Overpass API...")
    with urllib.request.urlopen(req, timeout=35) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        elements = res.get("elements", [])
        print(f"Success! Retrieved {len(elements)} elements from OpenStreetMap.")
        with open("manta_osm_raw.json", "w", encoding="utf-8") as f:
            json.dump(res, f)
        print("Saved raw OSM data to manta_osm_raw.json")
except Exception as e:
    print(f"Error querying Overpass API: {e}")
