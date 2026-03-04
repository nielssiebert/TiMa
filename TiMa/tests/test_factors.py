from __future__ import annotations

import sys

from .api_helpers import create_factor


def test_factors_gets_and_typeahead(client):
    create_factor(client)

    resp = client.get("/api/factors/test_id_1")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["id"] == "test_id_1"
    assert data["name"] == "test_name_1"
    assert data["activated"] is True
    assert data["min_val"] == 0.7
    assert data["max_val"] == 1.5

    resp = client.get("/api/factors")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1

    resp = client.get("/api/factors/find?query=test_name_1")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["id"] == "test_id_1"


def test_update_factor_value_allows_zero(client):
    resp = client.post(
        "/api/factors",
        json={"id": "test_id_2", "name": "test_name_2"},
    )
    assert resp.status_code == 201

    resp = client.post(
        "/api/factors/updateFactor",
        json={"id": "test_id_2", "value": 0.0},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["factor"] == 0.0


def test_update_factor_value_rejects_negative(client):
    resp = client.post(
        "/api/factors",
        json={"id": "test_id_2", "name": "test_name_2"},
    )
    assert resp.status_code == 201

    resp = client.post(
        "/api/factors/updateFactor",
        json={"id": "test_id_2", "value": -0.1},
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["message"] == f"factor must be between 0.0 and {sys.float_info.max}"


def test_update_factor_value_rejects_over_float_max(client):
    resp = client.post(
        "/api/factors",
        json={"id": "test_id_2", "name": "test_name_2"},
    )
    assert resp.status_code == 201

    resp = client.post(
        "/api/factors/updateFactor",
        json={"id": "test_id_2", "value": "1e309"},
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["message"] == f"factor must be between 0.0 and {sys.float_info.max}"


def test_update_factor_value_still_validates_min_max_bounds(client):
    create_factor(client)

    resp = client.post(
        "/api/factors/updateFactor",
        json={"id": "test_id_1", "value": 0.5},
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["message"] == "factor must be between min_val and max_val"


def test_factor_create_rejects_activated(client):
    resp = client.post(
        "/api/factors",
        json={"id": "test_id_3", "name": "test_name_3", "activated": False},
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["message"] == "activated must be updated via activate/deactivate endpoints"


def test_factor_update_rejects_activated(client):
    create_factor(client)

    resp = client.put(
        "/api/factors",
        json={"id": "test_id_1", "name": "test_name_1", "activated": False},
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["message"] == "activated must be updated via activate/deactivate endpoints"


def test_factor_can_be_activated_and_deactivated_via_dedicated_endpoints(client):
    create_factor(client)

    resp = client.post("/api/factors/test_id_1/deactivate")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["activated"] is False

    resp = client.post("/api/factors/test_id_1/activate")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["activated"] is True
