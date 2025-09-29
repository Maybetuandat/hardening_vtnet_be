#!/usr/bin/env python3
"""
Script để check Redis cache
Usage: python check_redis.py
"""
import redis
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    # Get Redis config từ environment variables
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("REDIS_DB", 0))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
    
    print("=" * 80)
    print("REDIS CACHE INSPECTOR")
    print("=" * 80)
    print(f"Connecting to: {REDIS_HOST}:{REDIS_PORT} (DB: {REDIS_DB})")
    
    # Connect Redis với password
    try:
        r = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            decode_responses=True
        )
        r.ping()
        print("✅ Redis connection OK\n")
    except redis.AuthenticationError:
        print("❌ Redis authentication failed!")
        print(f"\n💡 Current REDIS_PASSWORD in .env: {REDIS_PASSWORD}")
        print("\nFix:")
        print("  1. Check REDIS_PASSWORD in .env file")
        print("  2. Or remove password if Redis không cần auth:")
        print("     REDIS_PASSWORD=")
        return
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print(f"\nDebug info:")
        print(f"  Host: {REDIS_HOST}")
        print(f"  Port: {REDIS_PORT}")
        print(f"  DB: {REDIS_DB}")
        print(f"  Password: {'***' if REDIS_PASSWORD else 'None'}")
        return
    
    # Get all DCIM keys
    dcim_keys = r.keys("dcim:*")
    
    print(f"📊 Total DCIM cache keys: {len(dcim_keys)}\n")
    
    if not dcim_keys:
        print("⚠️  No DCIM cache found!")
        print("\nTips:")
        print("  1. Call API: GET /api/dcim/instances?use_cache=true")
        print("  2. Run this script again")
        return
    
    # Show all keys with TTL
    print("📋 Cache Keys:")
    print("-" * 80)
    
    for i, key in enumerate(dcim_keys, 1):
        ttl = r.ttl(key)
        ttl_human = f"{ttl}s" if ttl > 0 else "expired" if ttl == -2 else "no expiry"
        
        print(f"{i}. Key: {key}")
        print(f"   TTL: {ttl_human}")
        print()
    
    # Inspect first key in detail
    if dcim_keys:
        print("=" * 80)
        print(f"🔍 Inspecting first key: {dcim_keys[0]}")
        print("=" * 80)
        
        data = r.get(dcim_keys[0])
        if data:
            try:
                parsed_data = json.loads(data)
                print(json.dumps(parsed_data, indent=2, ensure_ascii=False))
            except:
                print(data)
    
    # Redis info
    print("\n" + "=" * 80)
    print("📈 Redis Info:")
    print("=" * 80)
    info = r.info("keyspace")
    print(f"Database: {info}")
    
    memory_info = r.info("memory")
    print(f"Used Memory: {memory_info.get('used_memory_human', 'N/A')}")

if __name__ == "__main__":
    main()