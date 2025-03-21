# src/datacenter_change_trigger/query.py

def build_query_url(network, station, location, channel, starttime, endtime):
    return f"https://eida.gein.noa.gr/fdsnws/station/1/query?network={','.join(network)}&station={','.join(station)}"
