"""MongoDB-backed persistence layer compatible with the existing Flask routes."""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from pymongo import MongoClient


class QuerySet:
    def __init__(self, model_cls, filters: Optional[Dict[str, Any]] = None, order_by: Optional[List[str]] = None):
        self.model_cls = model_cls
        self.filters = filters or {}
        self.order_by_fields = order_by or []

    def filter_by(self, **kwargs):
        new_filters = dict(self.filters)
        new_filters.update(kwargs)
        return QuerySet(self.model_cls, new_filters, self.order_by_fields)

    def order_by(self, field):
        return QuerySet(self.model_cls, self.filters, self.order_by_fields + [field])

    def _collection(self):
        return db.get_collection(self.model_cls.__collection_name__)

    def _documents(self):
        docs = list(self._collection().find(self.filters))
        if self.order_by_fields:
            docs.sort(key=lambda item: tuple(item.get(field) for field in self.order_by_fields if field in item))
        return docs

    def all(self):
        return [self.model_cls.from_dict(doc) for doc in self._documents()]

    def first(self):
        docs = self._documents()
        if not docs:
            return None
        return self.model_cls.from_dict(docs[0])

    def count(self):
        return len(self._documents())

    def update(self, values: Dict[str, Any]):
        collection = self._collection()
        result = collection.update_many(self.filters, {"$set": values})
        return result.modified_count


class QueryManager:
    def __init__(self, model_cls):
        self.model_cls = model_cls

    def filter_by(self, **kwargs):
        return QuerySet(self.model_cls, kwargs)

    def get(self, pk):
        if pk is None:
            return None
        collection = db.get_collection(self.model_cls.__collection_name__)
        doc = collection.find_one({"_id": pk})
        if not doc:
            return None
        return self.model_cls.from_dict(doc)

    def get_or_404(self, pk):
        obj = self.get(pk)
        if obj is None:
            raise LookupError(pk)
        return obj

    def count(self):
        return QuerySet(self.model_cls).count()


class MongoSession:
    def __init__(self, database):
        self.database = database
        self._pending_add = []
        self._pending_delete = []

    def add(self, obj):
        if obj not in self._pending_add:
            self._pending_add.append(obj)

    def delete(self, obj):
        if obj not in self._pending_delete:
            self._pending_delete.append(obj)

    def commit(self):
        for obj in self._pending_add:
            self.database._save_document(obj)
        for obj in self._pending_delete:
            self.database._delete_document(obj)
        self._pending_add = []
        self._pending_delete = []

    def rollback(self):
        self._pending_add = []
        self._pending_delete = []


class MongoDB:
    def __init__(self):
        self.client = None
        self.db = None
        self.session = MongoSession(self)

    def init_app(self, app):
        uri = os.environ.get("MONGODB_URI", "mongodb://127.0.0.1:27017")
        db_name = os.environ.get("MONGODB_DB", "coc_bot")
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.session = MongoSession(self)
        app.extensions["mongo_db"] = self
        self.create_all()
        return self

    def create_all(self):
        if self.db is None:
            return
        self.db["counters"].create_index("name", unique=True)
        self.db["users"].create_index("username", unique=True)
        self.db["devices"].create_index("user_id")
        self.db["device_configs"].create_index("device_id", unique=True)
        self.db["banned_ips"].create_index("ip_address")
        self.db["notices"].create_index("created_at")
        self.db["bot_sessions"].create_index("session_token", unique=True)
        self.db["audit_logs"].create_index("timestamp")

    def get_collection(self, name: str):
        if self.db is None:
            raise RuntimeError("MongoDB is not initialized")
        return self.db[name]

    def _next_id(self, collection_name: str) -> int:
        counter_collection = self.get_collection("counters")
        counter_doc = counter_collection.find_one({"name": collection_name})
        if not counter_doc:
            counter_collection.insert_one({"name": collection_name, "value": 1})
            return 1
        current_value = int(counter_doc.get("value", 1))
        counter_collection.update_one({"name": collection_name}, {"$set": {"value": current_value + 1}})
        return current_value + 1

    def _save_document(self, obj):
        collection = self.get_collection(obj.__collection_name__)
        if getattr(obj, "id", None) is None:
            obj.id = self._next_id(obj.__collection_name__)
        payload = obj.to_dict()
        payload["_id"] = payload["id"]
        collection.replace_one({"_id": payload["_id"]}, payload, upsert=True)

    def _delete_document(self, obj):
        collection = self.get_collection(obj.__collection_name__)
        if getattr(obj, "id", None) is not None:
            collection.delete_one({"_id": obj.id})


class BaseDocument:
    __collection_name__ = None
    __fields__ = ()

    query = QueryManager(None)  # placeholder

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.query = QueryManager(cls)

    def __init__(self, **kwargs):
        self.id = kwargs.pop("id", None)
        for field in self.__fields__:
            setattr(self, field, None)
        for field in self.__fields__:
            if field in kwargs:
                setattr(self, field, kwargs.pop(field))
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_dict(self) -> Dict[str, Any]:
        payload = {"id": self.id}
        for field in self.__fields__:
            payload[field] = getattr(self, field, None)
        for key, value in self.__dict__.items():
            if key.startswith("_") or key in {"id", "query"}:
                continue
            if key in self.__fields__:
                continue
            payload[key] = value
        return payload

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        payload = {}
        for field in cls.__fields__:
            payload[field] = data.get(field)
        payload["id"] = data.get("id", data.get("_id"))
        for key, value in data.items():
            if key.startswith("_") or key in {"id"} or key in cls.__fields__:
                continue
            payload[key] = value
        return cls(**payload)

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.id}>"


class User(BaseDocument):
    __collection_name__ = "users"
    __fields__ = (
        "username",
        "password_hash",
        "role",
        "is_banned",
        "ban_reason",
        "banned_at",
        "created_at",
        "session_version",
    )

    def __init__(self, **kwargs):
        kwargs.setdefault("role", "user")
        kwargs.setdefault("is_banned", False)
        kwargs.setdefault("session_version", 0)
        kwargs.setdefault("created_at", datetime.utcnow())
        super().__init__(**kwargs)

    @property
    def devices(self):
        return Device.query.filter_by(user_id=self.id).all()


class Device(BaseDocument):
    __collection_name__ = "devices"
    __fields__ = ("user_id", "device_name", "adb_host", "adb_port", "is_active", "created_at")

    def __init__(self, **kwargs):
        kwargs.setdefault("device_name", "My Device")
        kwargs.setdefault("adb_host", "127.0.0.1")
        kwargs.setdefault("adb_port", 5555)
        kwargs.setdefault("is_active", False)
        kwargs.setdefault("created_at", datetime.utcnow())
        super().__init__(**kwargs)

    @property
    def config(self):
        return DeviceConfig.query.filter_by(device_id=self.id).first()


class DeviceConfig(BaseDocument):
    __collection_name__ = "device_configs"
    __fields__ = (
        "device_id",
        "attack_limit",
        "attacks_today",
        "last_reset",
        "min_gold",
        "min_elixir",
        "min_dark",
        "troops",
        "deploy_speed",
        "delays",
        "deploy_zone_x",
        "deploy_zone_y",
        "zone_cache_confidence",
        "bot_running",
        "updated_at",
    )

    def __init__(self, **kwargs):
        kwargs.setdefault("attack_limit", 50)
        kwargs.setdefault("attacks_today", 0)
        kwargs.setdefault("last_reset", datetime.utcnow())
        kwargs.setdefault("min_gold", 0)
        kwargs.setdefault("min_elixir", 6000)
        kwargs.setdefault("min_dark", 0)
        kwargs.setdefault("troops", "[]")
        kwargs.setdefault("deploy_speed", 0.08)
        kwargs.setdefault("delays", "{}")
        kwargs.setdefault("zone_cache_confidence", 0.0)
        kwargs.setdefault("bot_running", False)
        kwargs.setdefault("updated_at", datetime.utcnow())
        super().__init__(**kwargs)


class BannedIP(BaseDocument):
    __collection_name__ = "banned_ips"
    __fields__ = ("ip_address", "user_id", "reason", "banned_at", "is_active")

    def __init__(self, **kwargs):
        kwargs.setdefault("banned_at", datetime.utcnow())
        kwargs.setdefault("is_active", True)
        super().__init__(**kwargs)


class Notice(BaseDocument):
    __collection_name__ = "notices"
    __fields__ = ("message", "level", "is_active", "created_at", "created_by")

    def __init__(self, **kwargs):
        kwargs.setdefault("level", "info")
        kwargs.setdefault("is_active", True)
        kwargs.setdefault("created_at", datetime.utcnow())
        super().__init__(**kwargs)


class BotSession(BaseDocument):
    __collection_name__ = "bot_sessions"
    __fields__ = (
        "user_id",
        "device_id",
        "session_token",
        "started_at",
        "ended_at",
        "is_running",
        "total_cycles",
        "total_attacks",
        "total_gold",
        "total_elixir",
        "total_dark",
        "status",
        "error_message",
    )

    def __init__(self, **kwargs):
        kwargs.setdefault("started_at", datetime.utcnow())
        kwargs.setdefault("is_running", True)
        kwargs.setdefault("total_cycles", 0)
        kwargs.setdefault("total_attacks", 0)
        kwargs.setdefault("total_gold", 0)
        kwargs.setdefault("total_elixir", 0)
        kwargs.setdefault("total_dark", 0)
        kwargs.setdefault("status", "running")
        super().__init__(**kwargs)


class AuditLog(BaseDocument):
    __collection_name__ = "audit_logs"
    __fields__ = ("user_id", "action", "resource", "details", "ip_address", "timestamp", "status")

    def __init__(self, **kwargs):
        kwargs.setdefault("timestamp", datetime.utcnow())
        kwargs.setdefault("status", "success")
        super().__init__(**kwargs)


db = MongoDB()
