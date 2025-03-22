import requests
import logging
from urllib.parse import urlencode
from concurrent.futures import ThreadPoolExecutor, as_completed

FDSN_ENDPOINT = "station/1/query"

def build_station_query_url(base_url: str, params: dict) -> str:
    """
    Build a complete FDSN Station query URL from a base and parameter dictionary.
    """
    query_params = {
        "starttime": params["starttime"],
        "endtime": params["endtime"],
        "network": ",".join(params["network"]),
        "station": ",".join(params["station"]),
        "location": ",".join(params["location"]),
        "channel": ",".join(params["channel"]),
        "nodata": 404,
        
    }

    return f"{base_url.rstrip('/')}/{FDSN_ENDPOINT}?{urlencode(query_params)}"

def query_node(base_url: str, params: dict, timeout: int = 10):
    """
    Query a single node and return the full query URL, base URL, and response text if successful.
    """
    full_url = build_station_query_url(base_url, params)
    try:
        response = requests.get(full_url, timeout=timeout)
        if response.status_code == 200 and response.text.strip():
            return full_url, base_url, response.text.strip()
        else:
            logging.debug(f"No data or bad response from {base_url} ({response.status_code})")
    except requests.RequestException as e:
        logging.debug(f"Request to {base_url} failed: {e}")
    return None

def query_all_nodes_parallel(nodes: list, params: dict):
    """
    Query all nodes concurrently and return the first successful response.
    """
    logging.info("Querying all nodes in parallel...")

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(query_node, base_url, params): (name, base_url)
            for name, base_url, _ in nodes
        }

        for future in as_completed(futures):
            result = future.result()
            if result:
                full_url, base_url, data = result
                name, _ = futures[future]
                logging.info(f"Valid response from: {name} ({base_url})")
                return full_url, base_url, data

    logging.error("No node returned valid metadata.")
    return None
