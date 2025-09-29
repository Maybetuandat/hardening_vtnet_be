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

def print_data_with_limit(data_str, max_chars=5000):
    """In dữ liệu với giới hạn ký tự, hiển thị thông báo nếu quá dài"""
    if len(data_str) <= max_chars:
        print(data_str)
    else:
        print(data_str[:max_chars])
        print("\n" + "." * 80)
        print(f"⚠️  DATA TOO LONG! Showing first {max_chars} chars")
        print(f"📏 Total length: {len(data_str)} chars")
        print(f"💡 To see full data, increase max_chars or save to file")
        print("." * 80)

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
    
    # Get ALL keys (không chỉ dcim:*)
    all_keys = r.keys("*")
    
    print(f"📊 Total cache keys: {len(all_keys)}\n")
    
    if not all_keys:
        print("⚠️  No cache found!")
        return
    
    # Nhóm keys theo pattern
    dcim_keys = [k for k in all_keys if k.startswith("dcim")]
    other_keys = [k for k in all_keys if not k.startswith("dcim")]
    
    print(f"🔑 DCIM keys: {len(dcim_keys)}")
    print(f"🔑 Other keys: {len(other_keys)}\n")
    
    # In toàn bộ dữ liệu của từng key
    for i, key in enumerate(all_keys, 1):
        print("=" * 80)
        print(f"🔑 KEY #{i}: {key}")
        print("=" * 80)
        
        # Get TTL
        ttl = r.ttl(key)
        ttl_human = f"{ttl}s ({ttl//60}m {ttl%60}s)" if ttl > 0 else "expired" if ttl == -2 else "no expiry"
        print(f"⏱️  TTL: {ttl_human}")
        
        # Get data type
        key_type = r.type(key)
        print(f"📝 Type: {key_type}")
        
        # Get size
        if key_type == "string":
            size = r.memory_usage(key) or 0
            print(f"💾 Memory: {size} bytes ({size/1024:.2f} KB)")
        
        # Get data
        print(f"\n📦 DATA:")
        print("-" * 80)
        
        try:
            if key_type == "string":
                data = r.get(key)
                if data:
                    try:
                        # Try parse JSON
                        parsed_data = json.loads(data)
                        formatted_json = json.dumps(parsed_data, indent=2, ensure_ascii=False)
                        
                        # In toàn bộ hoặc giới hạn nếu quá dài
                        print_data_with_limit(formatted_json, max_chars=10000)
                        
                        # Thống kê nếu là list/dict
                        if isinstance(parsed_data, list):
                            print(f"\n📊 Array length: {len(parsed_data)} items")
                        elif isinstance(parsed_data, dict):
                            print(f"\n📊 Object keys: {list(parsed_data.keys())}")
                            if 'data' in parsed_data and isinstance(parsed_data['data'], list):
                                print(f"   └─ data: {len(parsed_data['data'])} items")
                        
                    except json.JSONDecodeError:
                        # Not JSON, print as is
                        print_data_with_limit(data, max_chars=10000)
                else:
                    print("(empty)")
            
            elif key_type == "list":
                data = r.lrange(key, 0, -1)
                print(f"List length: {len(data)}")
                for idx, item in enumerate(data[:100]):  # Giới hạn 100 items
                    print(f"[{idx}] {item}")
                if len(data) > 100:
                    print(f"... and {len(data) - 100} more items")
            
            elif key_type == "set":
                data = r.smembers(key)
                print(f"Set size: {len(data)}")
                for item in list(data)[:100]:
                    print(f"  - {item}")
                if len(data) > 100:
                    print(f"... and {len(data) - 100} more items")
            
            elif key_type == "zset":
                data = r.zrange(key, 0, -1, withscores=True)
                print(f"Sorted set size: {len(data)}")
                for item, score in data[:100]:
                    print(f"  {score}: {item}")
                if len(data) > 100:
                    print(f"... and {len(data) - 100} more items")
            
            elif key_type == "hash":
                data = r.hgetall(key)
                print(json.dumps(data, indent=2, ensure_ascii=False))
            
            else:
                print(f"Unknown type: {key_type}")
        
        except Exception as e:
            print(f"❌ Error reading key: {e}")
        
        print("\n")
    
    # Redis info
    print("=" * 80)
    print("📈 REDIS INFO")
    print("=" * 80)
    info = r.info("keyspace")
    print(f"Keyspace: {info}")
    
    memory_info = r.info("memory")
    print(f"\nMemory:")
    print(f"  Used: {memory_info.get('used_memory_human', 'N/A')}")
    print(f"  Peak: {memory_info.get('used_memory_peak_human', 'N/A')}")
    print(f"  Fragmentation: {memory_info.get('mem_fragmentation_ratio', 'N/A')}")

if __name__ == "__main__":
    main()