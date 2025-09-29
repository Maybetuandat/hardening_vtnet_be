#!/usr/bin/env python3
"""
Script để check Redis cache với summary chi tiết
Usage: python check_redis.py
"""
import redis
import json
import os
from dotenv import load_dotenv
from collections import defaultdict

# Load environment variables
load_dotenv()

def analyze_json_structure(data):
    """Phân tích cấu trúc JSON để tạo summary"""
    summary = {}
    
    if isinstance(data, dict):
        summary['type'] = 'object'
        summary['keys'] = list(data.keys())
        summary['key_count'] = len(data.keys())
        
        # Phân tích chi tiết từng field
        for key, value in data.items():
            if isinstance(value, list):
                summary[f'{key}_count'] = len(value)
                if value:
                    summary[f'{key}_first_item_type'] = type(value[0]).__name__
            elif isinstance(value, dict):
                summary[f'{key}_keys'] = list(value.keys())
            else:
                summary[f'{key}_type'] = type(value).__name__
    
    elif isinstance(data, list):
        summary['type'] = 'array'
        summary['length'] = len(data)
        if data:
            summary['first_item_type'] = type(data[0]).__name__
            if isinstance(data[0], dict):
                summary['item_keys'] = list(data[0].keys())
    
    return summary

def print_json_summary(parsed_data):
    """In summary của JSON data"""
    print("\n" + "=" * 80)
    print("📊 DATA SUMMARY")
    print("=" * 80)
    
    summary = analyze_json_structure(parsed_data)
    
    for key, value in summary.items():
        if isinstance(value, list) and len(value) > 10:
            print(f"  {key}: {value[:10]} ... ({len(value)} total)")
        else:
            print(f"  {key}: {value}")

def main():
    # Get Redis config từ environment variables
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("REDIS_DB", 0))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
    
    print("=" * 80)
    print("🔍 REDIS CACHE INSPECTOR - FULL DISPLAY")
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
    
    # Get ALL keys
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
    
    # Statistics
    total_memory = 0
    key_stats = []
    
    # In toàn bộ dữ liệu của từng key
    for i, key in enumerate(all_keys, 1):
        print("=" * 80)
        print(f"🔑 KEY #{i}/{len(all_keys)}: {key}")
        print("=" * 80)
        
        # Get TTL
        ttl = r.ttl(key)
        if ttl > 0:
            ttl_human = f"{ttl}s ({ttl//3600}h {(ttl%3600)//60}m {ttl%60}s)"
        elif ttl == -2:
            ttl_human = "expired"
        else:
            ttl_human = "no expiry"
        print(f"⏱️  TTL: {ttl_human}")
        
        # Get data type
        key_type = r.type(key)
        print(f"📝 Type: {key_type}")
        
        # Get size
        memory_usage = 0
        if key_type == "string":
            memory_usage = r.memory_usage(key) or 0
            total_memory += memory_usage
            print(f"💾 Memory: {memory_usage:,} bytes ({memory_usage/1024:.2f} KB)")
        
        # Get data
        print(f"\n📦 FULL DATA:")
        print("-" * 80)
        
        item_count = 0
        
        try:
            if key_type == "string":
                data = r.get(key)
                if data:
                    try:
                        # Try parse JSON
                        parsed_data = json.loads(data)
                        
                        # In TOÀN BỘ data (không giới hạn)
                        formatted_json = json.dumps(parsed_data, indent=2, ensure_ascii=False)
                        print(formatted_json)
                        
                        # Đếm số items
                        if isinstance(parsed_data, list):
                            item_count = len(parsed_data)
                        elif isinstance(parsed_data, dict):
                            if 'instances' in parsed_data and isinstance(parsed_data['instances'], list):
                                item_count = len(parsed_data['instances'])
                            elif 'data' in parsed_data and isinstance(parsed_data['data'], list):
                                item_count = len(parsed_data['data'])
                        
                        # In summary
                        print_json_summary(parsed_data)
                        
                    except json.JSONDecodeError:
                        # Not JSON, print as is
                        print(data)
                        item_count = 1
                else:
                    print("(empty)")
            
            elif key_type == "list":
                data = r.lrange(key, 0, -1)
                item_count = len(data)
                print(f"📋 List length: {item_count} items\n")
                
                for idx, item in enumerate(data):
                    try:
                        parsed = json.loads(item)
                        print(f"[{idx}]")
                        print(json.dumps(parsed, indent=2, ensure_ascii=False))
                    except:
                        print(f"[{idx}] {item}")
                    print()
            
            elif key_type == "set":
                data = r.smembers(key)
                item_count = len(data)
                print(f"📋 Set size: {item_count} items\n")
                
                for item in data:
                    try:
                        parsed = json.loads(item)
                        print(json.dumps(parsed, indent=2, ensure_ascii=False))
                    except:
                        print(f"  - {item}")
                    print()
            
            elif key_type == "zset":
                data = r.zrange(key, 0, -1, withscores=True)
                item_count = len(data)
                print(f"📋 Sorted set size: {item_count} items\n")
                
                for item, score in data:
                    try:
                        parsed = json.loads(item)
                        print(f"Score: {score}")
                        print(json.dumps(parsed, indent=2, ensure_ascii=False))
                    except:
                        print(f"  {score}: {item}")
                    print()
            
            elif key_type == "hash":
                data = r.hgetall(key)
                item_count = len(data)
                print(f"📋 Hash fields: {item_count}\n")
                print(json.dumps(data, indent=2, ensure_ascii=False))
            
            else:
                print(f"Unknown type: {key_type}")
        
        except Exception as e:
            print(f"❌ Error reading key: {e}")
            import traceback
            traceback.print_exc()
        
        # Save stats
        key_stats.append({
            'key': key,
            'type': key_type,
            'ttl': ttl,
            'memory': memory_usage,
            'items': item_count
        })
        
        print("\n")
    
    # Print overall summary
    print("=" * 80)
    print("📊 OVERALL SUMMARY")
    print("=" * 80)
    
    print(f"\n🔑 Keys Breakdown:")
    print(f"  Total keys: {len(all_keys)}")
    print(f"  DCIM keys: {len(dcim_keys)}")
    print(f"  Other keys: {len(other_keys)}")
    
    print(f"\n💾 Memory Usage:")
    print(f"  Total: {total_memory:,} bytes ({total_memory/1024:.2f} KB / {total_memory/1024/1024:.2f} MB)")
    
    print(f"\n📦 Items per Key:")
    for stat in key_stats:
        if stat['items'] > 0:
            memory_str = f"{stat['memory']:,} bytes" if stat['memory'] > 0 else "N/A"
            print(f"  {stat['key']}: {stat['items']:,} items ({memory_str})")
    
    # Type distribution
    type_count = defaultdict(int)
    for stat in key_stats:
        type_count[stat['type']] += 1
    
    print(f"\n📝 Type Distribution:")
    for key_type, count in type_count.items():
        print(f"  {key_type}: {count} keys")
    
    # Redis info
    print("\n" + "=" * 80)
    print("📈 REDIS SERVER INFO")
    print("=" * 80)
    
    info = r.info("keyspace")
    print(f"\nKeyspace: {info}")
    
    memory_info = r.info("memory")
    print(f"\nMemory:")
    print(f"  Used: {memory_info.get('used_memory_human', 'N/A')}")
    print(f"  Peak: {memory_info.get('used_memory_peak_human', 'N/A')}")
    print(f"  Fragmentation: {memory_info.get('mem_fragmentation_ratio', 'N/A')}")
    
    server_info = r.info("server")
    print(f"\nServer:")
    print(f"  Redis Version: {server_info.get('redis_version', 'N/A')}")
    print(f"  Uptime: {server_info.get('uptime_in_days', 'N/A')} days")

if __name__ == "__main__":
    main()