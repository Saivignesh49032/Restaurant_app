import json
import os
import threading
import uuid
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional

DATA_DIR = 'data'
STORE_FILE = os.path.join(DATA_DIR, 'personalization_store.json')
_LOCK = threading.Lock()


def _ensure_store() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(STORE_FILE):
        with open(STORE_FILE, 'w', encoding='utf-8') as fp:
            json.dump({}, fp, indent=2)


def _read_store() -> Dict[str, Any]:
    _ensure_store()
    try:
        with open(STORE_FILE, 'r', encoding='utf-8') as fp:
            return json.load(fp) or {}
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def _write_store(data: Dict[str, Any]) -> None:
    tmp_path = f"{STORE_FILE}.tmp"
    with open(tmp_path, 'w', encoding='utf-8') as fp:
        json.dump(data, fp, indent=2)
    os.replace(tmp_path, STORE_FILE)


def _default_profile() -> Dict[str, Any]:
    return {
        "favorite_cuisines": [],
        "dietary_needs": [],
        "budget": 2,
        "budget_band_min": 1,
        "budget_band_max": 4,
        "flexible_prefs": {},
        "preferred_visit_type": "visit",
        "preferred_table_booking": "No",
        "mood_tags": [],
        "occasion_tags": [],
        "saved_filters": {},
        "updated_at": datetime.utcnow().isoformat()
    }


def _default_record() -> Dict[str, Any]:
    return {
        "profile": _default_profile(),
        "bookmarks": [],
        "ratings": {},
        "history": [],
        "interactions": [],
        "analytics": {
            "cities": {},
            "filters": {},
            "search_modes": {"dataset": 0, "hybrid": 0, "gemini": 0, "google": 0},
            "source_usage": {"dataset": 0, "gemini": 0, "google": 0}
        }
    }


def _get_record(data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    if user_id not in data:
        data[user_id] = _default_record()
    return data[user_id]


def _limit_history(history: List[Dict[str, Any]], limit: int = 50) -> List[Dict[str, Any]]:
    return history[-limit:]


def get_profile(user_id: str) -> Dict[str, Any]:
    with _LOCK:
        data = _read_store()
        record = _get_record(data, user_id)
        return deepcopy(record['profile'])


def update_profile(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    with _LOCK:
        data = _read_store()
        record = _get_record(data, user_id)
        profile = record['profile']
        filtered_updates = {k: v for k, v in updates.items() if v is not None}
        if 'budget_band_min' in filtered_updates or 'budget_band_max' in filtered_updates:
            profile['budget_band_min'] = int(filtered_updates.get('budget_band_min', profile.get('budget_band_min', 1)))
            profile['budget_band_max'] = int(filtered_updates.get('budget_band_max', profile.get('budget_band_max', 4)))
            profile['budget'] = int(round((profile['budget_band_min'] + profile['budget_band_max']) / 2))
            filtered_updates.pop('budget_band_min', None)
            filtered_updates.pop('budget_band_max', None)
        if 'flexible_prefs' in filtered_updates and not isinstance(filtered_updates['flexible_prefs'], dict):
            filtered_updates['flexible_prefs'] = profile.get('flexible_prefs', {})
        profile.update(filtered_updates)
        profile.setdefault('flexible_prefs', {})
        profile['updated_at'] = datetime.utcnow().isoformat()
        _write_store(data)
        return deepcopy(profile)


def list_bookmarks(user_id: str) -> List[Dict[str, Any]]:
    with _LOCK:
        data = _read_store()
        record = _get_record(data, user_id)
        return deepcopy(record['bookmarks'])


def _build_bookmark_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    bookmark_id = payload.get('bookmark_id') or str(uuid.uuid4())
    payload['bookmark_id'] = bookmark_id
    payload['saved_at'] = datetime.utcnow().isoformat()
    return payload


def add_bookmark(user_id: str, restaurant_payload: Dict[str, Any]) -> Dict[str, Any]:
    with _LOCK:
        data = _read_store()
        record = _get_record(data, user_id)
        bookmark_payload = _build_bookmark_payload(restaurant_payload)
        existing_ids = {b['bookmark_id'] for b in record['bookmarks']}
        if bookmark_payload['bookmark_id'] in existing_ids:
            record['bookmarks'] = [
                bookmark_payload if b['bookmark_id'] == bookmark_payload['bookmark_id'] else b
                for b in record['bookmarks']
            ]
        else:
            record['bookmarks'].append(bookmark_payload)
        record['bookmarks'] = record['bookmarks'][-100:]
        _write_store(data)
        return deepcopy(bookmark_payload)


def remove_bookmark(user_id: str, bookmark_id: str) -> List[Dict[str, Any]]:
    with _LOCK:
        data = _read_store()
        record = _get_record(data, user_id)
        record['bookmarks'] = [b for b in record['bookmarks'] if b['bookmark_id'] != bookmark_id]
        _write_store(data)
        return deepcopy(record['bookmarks'])


def set_rating(user_id: str, restaurant_id: str, rating: float) -> Dict[str, Any]:
    with _LOCK:
        data = _read_store()
        record = _get_record(data, user_id)
        record['ratings'][restaurant_id] = {
            "rating": rating,
            "updated_at": datetime.utcnow().isoformat()
        }
        _write_store(data)
        return deepcopy(record['ratings'])


def list_ratings(user_id: str) -> Dict[str, Any]:
    with _LOCK:
        data = _read_store()
        record = _get_record(data, user_id)
        return deepcopy(record['ratings'])


def add_history_event(user_id: str, event: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
    with _LOCK:
        data = _read_store()
        record = _get_record(data, user_id)
        event['id'] = str(uuid.uuid4())
        event['timestamp'] = datetime.utcnow().isoformat()
        record['history'].append(event)
        record['history'] = _limit_history(record['history'], limit)
        _write_store(data)
        return deepcopy(record['history'])


def list_history(user_id: str, limit: int = 25) -> List[Dict[str, Any]]:
    with _LOCK:
        data = _read_store()
        record = _get_record(data, user_id)
        return deepcopy(record['history'][-limit:])


def add_interaction(user_id: str, interaction: Dict[str, Any], limit: int = 300) -> Dict[str, Any]:
    with _LOCK:
        data = _read_store()
        record = _get_record(data, user_id)
        entity_id = interaction.get('entity_id')
        entry = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "entity_id": str(entity_id) if entity_id is not None else None,
            "entity_type": interaction.get('entity_type', 'restaurant'),
            "interaction_type": interaction.get('interaction_type'),
            "value": interaction.get('value'),
            "metadata": interaction.get('metadata') or {},
            "created_at": datetime.utcnow().isoformat()
        }
        record.setdefault('interactions', []).append(entry)
        record['interactions'] = record['interactions'][-limit:]
        _write_store(data)
        return deepcopy(entry)


def list_interactions(user_id: str, interaction_type: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    with _LOCK:
        data = _read_store()
        record = _get_record(data, user_id)
        interactions = record.get('interactions', [])
        if interaction_type:
            interactions = [i for i in interactions if i.get('interaction_type') == interaction_type]
        subset = interactions[-limit:]
        subset.reverse()
        return deepcopy(subset)


def record_search_analytics(
    user_id: str,
    city: Optional[str],
    filters: Optional[Dict[str, Any]],
    source: str,
    hybrid_fallback: Optional[str] = None
) -> Dict[str, Any]:
    with _LOCK:
        data = _read_store()
        record = _get_record(data, user_id)
        analytics = record['analytics']

        if city:
            analytics['cities'][city.lower()] = analytics['cities'].get(city.lower(), 0) + 1

        if filters:
            for key, value in filters.items():
                if value in (None, '', []):
                    continue
                analytics['filters'][key] = analytics['filters'].get(key, 0) + 1

        source = source or 'dataset'
        analytics['search_modes'][source] = analytics['search_modes'].get(source, 0) + 1

        if hybrid_fallback:
            analytics['source_usage'][hybrid_fallback] = analytics['source_usage'].get(hybrid_fallback, 0) + 1
        else:
            analytics['source_usage'][source] = analytics['source_usage'].get(source, 0) + 1

        _write_store(data)
        return deepcopy(analytics)


def get_analytics_snapshot() -> Dict[str, Any]:
    with _LOCK:
        data = _read_store()
        snapshot = {
            "cities": {},
            "filters": {},
            "search_modes": {"dataset": 0, "hybrid": 0, "gemini": 0, "google": 0},
            "source_usage": {"dataset": 0, "gemini": 0, "google": 0, "hybrid": 0}
        }
        for record in data.values():
            analytics = record.get('analytics', {})
            for city, count in analytics.get('cities', {}).items():
                snapshot['cities'][city] = snapshot['cities'].get(city, 0) + count
            for filt, count in analytics.get('filters', {}).items():
                snapshot['filters'][filt] = snapshot['filters'].get(filt, 0) + count
            for mode, count in analytics.get('search_modes', {}).items():
                snapshot['search_modes'][mode] = snapshot['search_modes'].get(mode, 0) + count
            for source, count in analytics.get('source_usage', {}).items():
                snapshot['source_usage'][source] = snapshot['source_usage'].get(source, 0) + count
        return snapshot

