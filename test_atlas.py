#!/usr/bin/env python3
"""Quick test: verify MongoDB Atlas connection."""

from pymongo import MongoClient

uri = "mongodb+srv://404abus_db_user:Samin%40123qwe@cluster0.kmvvrae.mongodb.net/coc_bot?retryWrites=true&w=majority"

try:
    c = MongoClient(uri, serverSelectionTimeoutMS=5000)
    info = c.server_info()
    print("[OK] MongoDB Atlas connected successfully!")
    print("   Server version:", info.get('version'))
    colls = c['coc_bot'].list_collection_names()
    print("   Collections in coc_bot:", colls if colls else "(empty - will be created on first write)")
except Exception as e:
    print("[ERROR] Connection failed:", type(e).__name__, str(e))
