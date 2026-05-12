"""
Soft grounding: curated JSON as preferential anchors + deterministic confidence hints.
No external APIs, embeddings, or frameworks.
"""
from __future__ import annotations

import json
from pathlib import Path

_PLACES_ROOT = Path(__file__).resolve().parent / "data" / "places"
_PLACES_CACHE: dict[str, list] | None = None

_VALID_CONFIDENCE = frozenset({"high", "medium", "low"})

TRANSPORT_KEYWORDS = (
    "metro", "метро", "aeropuerto", "airport", "аэропорт", "bus", "автобус",
    "línea", "linea", "line ", "линия", "machado", "benimaclet",
    "transport", "транспорт", "ruta", "how to get", "cómo llegar", "como llegar",
    "такси", "taxi", "uber", "bolt", "cabify",
)

PHARMACY_KEYWORDS = (
    "pharmacy", "farmacia", "farmacias", "аптек", "аптека",
)

RESTAURANT_KEYWORDS = (
    "restaurant", "ресторан", "comer", "dónde comer", "donde comer",
    "tapas", "café", "cafe", "кафе", "еда", "food",
)

CHURCH_KEYWORDS = (
    "church", "iglesia", "parroquia", "catedral", "cathedral", "церк",
)


def _places_path(name: str) -> Path:
    return _PLACES_ROOT / name


def _read_json_array(path: Path) -> list:
    if not path.is_file():
        return []
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(data, list):
        return data
    return []


def _sanitize_entry(entry: object) -> dict | None:
    if not isinstance(entry, dict):
        return None
    eid = entry.get("id")
    name = entry.get("name")
    district = entry.get("district")
    conf = entry.get("confidence")
    verified_at = entry.get("verified_at")
    if not isinstance(eid, str) or not eid.strip():
        return None
    if not isinstance(name, str) or not name.strip():
        return None
    if not isinstance(district, str) or not district.strip():
        return None
    if conf not in _VALID_CONFIDENCE:
        return None
    if not isinstance(verified_at, str) or not verified_at.strip():
        return None
    notes = entry.get("notes")
    out = {
        "id": eid.strip(),
        "name": name.strip(),
        "district": district.strip(),
        "confidence": conf,
        "verified_at": verified_at.strip(),
    }
    if isinstance(notes, str) and notes.strip():
        out["notes"] = notes.strip()
    return out


def load_places() -> dict[str, list]:
    """Load curated place lists from data/places/*.json (cached)."""
    global _PLACES_CACHE
    if _PLACES_CACHE is not None:
        return _PLACES_CACHE

    files = {
        "core": _places_path("core.json"),
        "transport": _places_path("transport.json"),
        "pharmacies": _places_path("pharmacies.json"),
        "restaurants": _places_path("restaurants.json"),
        "churches": _places_path("churches.json"),
    }
    out: dict[str, list] = {}
    for key, path in files.items():
        raw_list = _read_json_array(path)
        out[key] = [x for x in (_sanitize_entry(e) for e in raw_list) if x is not None]

    _PLACES_CACHE = out
    return out


def detect_place_category(text: str) -> str | None:
    """Lightweight keyword router; first category match wins."""
    t = text.lower()
    checks = (
        ("transport", TRANSPORT_KEYWORDS),
        ("pharmacies", PHARMACY_KEYWORDS),
        ("restaurants", RESTAURANT_KEYWORDS),
        ("churches", CHURCH_KEYWORDS),
    )
    for category, keywords in checks:
        if any(k in t for k in keywords):
            return category
    return None


def _bundle_key_for_category(category: str) -> str:
    if category == "transport":
        return "transport"
    if category == "pharmacies":
        return "pharmacies"
    if category == "restaurants":
        return "restaurants"
    if category == "churches":
        return "churches"
    return "core"


def _dominant_tier(entries: list) -> str:
    if not entries:
        return "medium"
    order = {"low": 0, "medium": 1, "high": 2}
    weakest = "high"
    for e in entries:
        c = e.get("confidence", "medium")
        if order.get(c, 1) < order.get(weakest, 2):
            weakest = c
    return weakest


def build_grounding_bundle(category: str | None, places: dict[str, list]) -> dict:
    """
    Build a small bundle for the LLM: trimmed entries + deterministic tier hint.
    `category` is one of transport|pharmacies|restaurants|churches or None.
    """
    if not category:
        return {
            "category": None,
            "entries": [],
            "anchor_entries": [],
            "dominant_tier": None,
            "policy_tag": "NONE",
        }

    key = _bundle_key_for_category(category)
    entries = list(places.get(key, []))[:5]
    anchor_entries = list(places.get("core", []))[:2]

    combined = entries + anchor_entries
    dominant = _dominant_tier(combined) if combined else "medium"

    if not entries:
        policy_tag = "SOFT_NO_LISTED_POIS"
    elif dominant == "high":
        policy_tag = "HIGH_FOR_VERIFIED_LINES"
    elif dominant == "medium":
        policy_tag = "MEDIUM_HEDGE"
    else:
        policy_tag = "LOW_NUMBERS_AND_ROUTES"

    return {
        "category": category,
        "entries": entries,
        "anchor_entries": anchor_entries,
        "dominant_tier": dominant,
        "policy_tag": policy_tag,
    }


def format_grounding_block(bundle: dict) -> str:
    """Compact block for the user turn (not the whole system prompt)."""
    if not bundle.get("category"):
        return ""

    lines: list[str] = []
    lines.append("PREFERRED VERIFIED FACTS (anchors; prefer these names and notes):")
    for e in bundle.get("anchor_entries", []):
        note = e.get("notes")
        tail = f" | notes: {note}" if note else ""
        lines.append(
            f"- [{e['confidence']}] {e['name']} | district/area: {e['district']} "
            f"| verified_at: {e['verified_at']}{tail}"
        )
    if bundle.get("entries"):
        for e in bundle["entries"]:
            note = e.get("notes")
            tail = f" | notes: {note}" if note else ""
            lines.append(
                f"- [{e['confidence']}] {e['name']} | district/area: {e['district']} "
                f"| verified_at: {e['verified_at']}{tail}"
            )
    else:
        lines.append(
            "- (no extra curated venue rows for this topic — still give friendly "
            "neighborhood-level advice; do not fabricate specific venue names, "
            "exact addresses, minute-level timings, or km.)"
        )

    tag = bundle.get("policy_tag", "MEDIUM_HEDGE")
    tier = bundle.get("dominant_tier", "medium")
    lines.append(
        f"CONFIDENCE_POLICY_TAG: {tag} | dominant_data_tier: {tier}. "
        "HIGH lines may sound factual; MEDIUM = natural local guidance without "
        "GPS-level precision; for unknowns skip invented numbers—give ranges or "
        "habits instead of pushing the user to apps repeatedly."
    )
    return "\n".join(lines)


def reload_places() -> dict[str, list]:
    """Debug: clear cache and reload from disk."""
    global _PLACES_CACHE
    _PLACES_CACHE = None
    return load_places()
