import requests
from urllib.parse import urlencode
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

FDSN_ENDPOINT = "station/1/query"

def build_station_query_url(base_url: str, params: dict) -> str:
    query_params = {
        "starttime": params["starttime"],
        "endtime": params["endtime"],
        "network": ",".join(params["network"]),
        "station": ",".join(params["station"]),
        "location": ",".join(params["location"]),
        "channel": ",".join(params["channel"]),
        "nodata": 404,
        "level": "response",
    }
    return f"{base_url.rstrip('/')}/{FDSN_ENDPOINT}?{urlencode(query_params)}"

def query_node(base_url: str, params: dict, timeout: int = 10):
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

def query_all_nodes_parallel(endpoints: list[str], params: dict):
    logging.info("Querying all configured endpoints in parallel...")

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(query_node, base_url.rstrip("/") + "/fdsnws", params): base_url
            for base_url in endpoints
        }

        for future in as_completed(futures):
            result = future.result()
            if result:
                return result  # Return first valid response

    return None
