import json
import logging
import threading
import requests
import time
import sys
import itertools
from pathlib import Path
from urllib.parse import urlparse
from appdirs import user_cache_dir

# --- Constants ---

DEFAULT_NODES = [
    ("GFZ", "https://geofon.gfz.de/fdsnws/", True),
    ("ODC", "https://orfeus-eu.org/fdsnws/", True),
    ("ETHZ", "https://eida.ethz.ch/fdsnws/", True),
    ("RESIF", "https://ws.resif.fr/fdsnws/", True),
    ("INGV", "https://webservices.ingv.it/fdsnws/", True),
    ("LMU", "https://erde.geophysik.uni-muenchen.de/fdsnws/", True),
    ("ICGC", "https://ws.icgc.cat/fdsnws/", True),
    ("NOA", "https://eida.gein.noa.gr/fdsnws/", True),
    ("BGR", "https://eida.bgr.de/fdsnws/", True),
    ("BGS", "https://eida.bgs.ac.uk/fdsnws/", True),
    ("NIEP", "https://eida-sc3.infp.ro/fdsnws/", True),
    ("KOERI", "https://eida.koeri.boun.edu.tr/fdsnws/", True),
    ("UIB-NORSAR", "https://eida.geo.uib.no/fdsnws/", True),
]

ROUTING_URL = "https://www.orfeus-eu.org/eidaws/routing/1/globalconfig?format=fdsn"
CACHE_DIR = Path(user_cache_dir("datacenter-change-trigger"))
CACHE_FILE = CACHE_DIR / "nodes_cache.json"

# --- Utilities ---

def ensure_cache_dir():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

def loading_animation(stop_event):
    """Display a spinner while fetching nodes."""
    for frame in itertools.cycle(['|', '/', '-', '\\']):
        if stop_event.is_set():
            break
        sys.stdout.write(f"\rFetching nodes... {frame} ")
        sys.stdout.flush()
        time.sleep(0.2)
    sys.stdout.write("\rFetching complete.       \n")

# --- Node Loading Logic ---

def fetch_nodes_from_api():
    """
    Fetch nodes from the EIDA routing service and save to cache.
    Returns a list of tuples: (name, base_url, True)
    """
    nodes = []
    stop_event = threading.Event()
    animation_thread = threading.Thread(target=loading_animation, args=(stop_event,))
    animation_thread.start()

    try:
        response = requests.get(ROUTING_URL, timeout=60)
        response.raise_for_status()
        data = response.json()

        for dc in data.get("datacenters", []):
            node_name = dc.get("name")
            fdsnws_url = None

            for repo in dc.get("repositories", []):
                for service in repo.get("services", []):
                    if service.get("name") == "fdsnws-station-1":
                        fdsnws_url = service.get("url")
                        break
                if fdsnws_url:
                    break

            if fdsnws_url:
                parsed = urlparse(fdsnws_url)
                base_url = f"{parsed.scheme}://{parsed.netloc}/fdsnws/"
                nodes.append((node_name, base_url, True))

        if nodes:
            save_nodes_to_cache(nodes)

    except requests.RequestException as e:
        logging.warning(f"Failed to fetch nodes from routing service: {e}")

    finally:
        stop_event.set()
        animation_thread.join()

    return nodes if nodes else None

def save_nodes_to_cache(nodes):
    ensure_cache_dir()
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump({"nodes": nodes}, f)

def load_cached_nodes():
    ensure_cache_dir()

    if CACHE_FILE.exists():
        try:
            print(f"Loading nodes from cached directory: {CACHE_FILE}")
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
                nodes = cache_data.get("nodes", [])

                if not all(isinstance(n, list) and len(n) == 3 for n in nodes):
                    raise ValueError("Invalid cache format")

                return [(str(name), str(url), True) for name, url, _ in nodes]

        except (json.JSONDecodeError, ValueError) as e:
            logging.warning(f"Cache file is corrupted: {e}. Deleting it.")
            CACHE_FILE.unlink()


    # If cache is missing or bad, try fetching again
    return fetch_nodes_from_api()

def load_nodes():
    """
    Public function to load nodes:
    - Try cache
    - Fallback to API
    - Fallback to DEFAULT_NODES
    """
    nodes = load_cached_nodes()
    return nodes if nodes else DEFAULT_NODES
