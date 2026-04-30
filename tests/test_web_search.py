from tools import web_search


class _FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "daily": {
                "temperature_2m_max": [20, 22],
                "temperature_2m_min": [10, 12],
                "precipitation_sum": [1, 0],
            }
        }


def test_get_weather_summary_uses_requested_year(monkeypatch):
    captured = {}

    def fake_get(url, params, timeout):
        captured["params"] = params
        return _FakeResponse()

    monkeypatch.setattr(web_search.requests, "get", fake_get)
    result = web_search.get_weather_summary("Paris", 48.8566, 2.3522, month=8, year=2025)

    assert captured["params"]["start_date"] == "2025-08-01"
    assert captured["params"]["end_date"] == "2025-08-28"
    assert result["avg_high_c"] == 21.0
