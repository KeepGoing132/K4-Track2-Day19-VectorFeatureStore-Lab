"""Real Feast profile lookups and online updates for the single-process POC."""
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
import time

FEATURES = [
    "user_profile_features:reading_speed_wpm",
    "user_profile_features:preferred_language",
    "user_profile_features:topic_affinity",
    "query_velocity_features:queries_last_hour",
    "query_velocity_features:distinct_topics_24h",
]
REPO = Path(__file__).resolve().parents[1] / "app" / "feast_repo"


class FeastOnlineStore:
    """Use the lab's registered views; count this process's queries in a 1h window.

    The activity window starts empty on process restart. A production deployment
    needs durable events and a shared stream aggregator across workers.
    """

    def __init__(self, store=None):
        if store is None:
            from feast import FeatureStore
            store = FeatureStore(repo_path=str(REPO))
        self.store = store
        self._queries = defaultdict(deque)

    def get_online_features(self, entity_rows):
        user_id = entity_rows[0]["user_id"]
        values = self.store.get_online_features(
            features=FEATURES, entity_rows=entity_rows,
        ).to_dict()
        profile = {key: value[0] for key, value in values.items()}
        profile["user_id"] = user_id
        profile["preferred_lang"] = profile.pop("preferred_language", None) or "unknown"
        profile["topic_affinity"] = profile.get("topic_affinity") or "unknown"
        profile["reading_speed_wpm"] = profile.get("reading_speed_wpm") or 0
        profile["queries_last_hour"] = profile.get("queries_last_hour") or 0
        profile["distinct_topics_24h"] = profile.get("distinct_topics_24h") or 0
        return profile

    def record_query(self, user_id):
        import pandas as pd
        now = time.monotonic()
        events = self._queries[user_id]
        while events and events[0] <= now - 3600:
            events.popleft()
        events.append(now)
        profile = self.get_online_features([{"user_id": user_id}])
        self.store.write_to_online_store(
            feature_view_name="query_velocity_features",
            df=pd.DataFrame([{
                "user_id": user_id,
                "queries_last_hour": len(events),
                "distinct_topics_24h": profile["distinct_topics_24h"],
                "event_timestamp": datetime.now(timezone.utc),
            }]),
        )
