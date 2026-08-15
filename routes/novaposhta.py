import requests
from flask import Blueprint, current_app, jsonify, request

novaposhta_bp = Blueprint("novaposhta", __name__)

REQUEST_TIMEOUT = 5


def _np_request(payload):
    """Проксі до Nova Poshta API. Повертає (ok, json_or_none)."""
    url = current_app.config["NP_API_URL"]
    try:
        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return True, response.json()
    except (requests.RequestException, ValueError):
        current_app.logger.warning("Nova Poshta API недоступний або повернув помилку")
        return False, None


# ── Nova Poshta: міста ──
@novaposhta_bp.route("/get_cities", methods=["POST"])
def get_cities():
    search = (request.json or {}).get("search", "").strip()
    if len(search) < 2:
        return jsonify({"success": False, "data": []})

    payload = {
        "apiKey": current_app.config["NP_API_KEY"],
        "modelName": "AddressGeneral",
        "calledMethod": "getSettlements",
        "methodProperties": {"FindByString": search, "Warehouse": "1", "Limit": "10"},
    }
    ok, result = _np_request(payload)
    if not ok:
        return jsonify({"success": False, "data": []}), 502

    return jsonify({"success": result.get("success", False), "data": result.get("data", [])})


# ── Nova Poshta: відділення ──
@novaposhta_bp.route("/get_warehouses", methods=["POST"])
def get_warehouses():
    data = request.json or {}
    city = data.get("city", "").strip()
    if not city:
        return jsonify({"success": False, "data": []})

    payload = {
        "apiKey": current_app.config["NP_API_KEY"],
        "modelName": "Address",
        "calledMethod": "getWarehouses",
        "methodProperties": {
            "CityName": city,
            "FindByString": data.get("search", ""),
            "Limit": "50",
        },
    }
    ok, result = _np_request(payload)
    if not ok:
        return jsonify({"success": False, "data": []}), 502

    return jsonify({"success": result.get("success", False), "data": result.get("data", [])})
