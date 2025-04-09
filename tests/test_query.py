from dmtri.query import build_station_query_url
import pytest
from unittest.mock import patch, MagicMock , Mock
from dmtri.query import query_node, build_station_query_url
from requests.exceptions import RequestException
from dmtri import query
def test_build_station_query_url():
    base_url = " https://ws.resif.fr/fdsnws"
    params = {
        "network": ["FR"],
        "station": ["CIEL"],
        "location": ["*"],
        "channel": ["*"],
        "starttime": "2025-01-01T00:00:00",
        "endtime": "2025-01-02T00:00:00",
        "type": ["metadata"],
    }

    url = build_station_query_url(base_url, params)
    
    assert url.startswith(" https://ws.resif.fr/fdsnws/station/1/query?")
    assert "network=FR" in url
    assert "station=CIEL" in url
    assert "starttime=2025-01-01T00%3A00%3A00" in url

def test_query_node_success_returns_data():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "metadata result"

    with patch("dmtri.query.requests.get", return_value=mock_response):
        result = query_node("https://ws.resif.fr/fdsnws", {
            "network": ["FR"],
            "station": ["CIEL"],
            "location": ["*"],
            "channel": ["*"],
            "starttime": "2025-01-01T00:00:00",
            "endtime": "2025-01-02T00:00:00",
            "type": ["metadata"],
        })
        assert result is not None
        assert "ws.resif.fr" in result[0]  # URL
        assert result[2] == "metadata result"

def test_query_node_404_returns_none():
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = ""

    with patch("dmtri.query.requests.get", return_value=mock_response):
        result = query_node("https://ws.resif.fr/fdsnws", {
            "network": ["FR"],
            "station": ["CIEL"],
            "location": ["*"],
            "channel": ["*"],
            "starttime": "2025-01-01T00:00:00",
            "endtime": "2025-01-02T00:00:00",
            "type": ["metadata"],
        })
        assert result is None



def test_query_node_raises_exception_returns_none():
    with patch("dmtri.query.requests.get", side_effect=RequestException("Network error")):
        result = query_node("https://ws.resif.fr/fdsnws", {
            "network": ["FR"],
            "station": ["CIEL"],
            "location": ["*"],
            "channel": ["*"],
            "starttime": "2025-01-01T00:00:00",
            "endtime": "2025-01-02T00:00:00",
            "type": ["metadata"],
        })
        assert result is None


@patch("dmtri.query.query_node")
def test_query_all_nodes_returns_first_success(mock_query_node):
    def side_effect(url, params):
        if "good-node" in url:
            return ("https://good-node/fdsnws/station/1/query", "https://good-node/fdsnws", "valid metadata")
        return None

    mock_query_node.side_effect = side_effect

    endpoints = [
        "https://bad-node1",
        "https://bad-node2",
        "https://good-node",  # This one will return data
        "https://bad-node3"
    ]

    params = {
        "network": ["FR"],
        "station": ["CIEL"],
        "location": ["*"],
        "channel": ["*"],
        "starttime": "2025-01-01T00:00:00",
        "endtime": "2025-01-02T00:00:00",
        "type": ["metadata"],
    }

    result = query.query_all_nodes_parallel(endpoints, params)

    assert result is not None
    assert "good-node" in result[0]
@patch("dmtri.query.query_node", return_value=None)
def test_query_all_nodes_returns_none_if_all_fail(mock_query_node):
    endpoints = [
        "https://bad-node1",
        "https://bad-node2",
        "https://bad-node3"
    ]

    params = {
        "network": ["FR"],
        "station": ["CIEL"],
        "location": ["*"],
        "channel": ["*"],
        "starttime": "2025-01-01T00:00:00",
        "endtime": "2025-01-02T00:00:00",
        "type": ["metadata"],
    }

    result = query.query_all_nodes_parallel(endpoints, params)

    assert result is None
    assert mock_query_node.call_count == len(endpoints)
@patch("dmtri.query.requests.get")
def test_query_logs_bad_response_with_content(mock_get, caplog):
    # Simulate 500 response with some body
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Server error occurred. Here's the stack trace..."
    mock_get.return_value = mock_response

    with caplog.at_level("DEBUG"):
        result = query_node("https://test.endpoint", {
            "network": ["FR"],
            "station": ["CIEL"],
            "location": ["00"],
            "channel": ["HHZ"],
            "starttime": "2025-01-01T00:00:00",
            "endtime": "2025-01-02T00:00:00",
            "type": ["metadata"]
        })

    assert result is None
    assert "No data or bad response" in caplog.text
    assert "Response content" in caplog.text
    assert "Server error occurred" in caplog.text