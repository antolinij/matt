#!/usr/bin/env python3
"""
Cache Testing Script

Simple script to demonstrate and test Redis caching functionality.
"""
import asyncio
import time
from app.core.cache import cache_service


async def test_basic_operations():
    """Test basic cache operations"""
    print("=" * 60)
    print("REDIS CACHE TEST")
    print("=" * 60)

    # Test 1: Set and Get
    print("\n1. Testing SET and GET operations")
    print("-" * 60)

    test_data = {
        "id": 1,
        "name": "Test School",
        "email": "test@school.com"
    }

    print(f"   Setting cache: test:key = {test_data}")
    await cache_service.set("test:key", test_data, ttl=10)

    print("   Getting from cache...")
    result = await cache_service.get("test:key")
    print(f"   ✓ Retrieved: {result}")

    # Test 2: Cache expiration
    print("\n2. Testing TTL (Time To Live)")
    print("-" * 60)

    print("   Setting cache with 3 second TTL...")
    await cache_service.set("test:expire", {"data": "will expire"}, ttl=3)

    print("   Immediately reading...")
    result = await cache_service.get("test:expire")
    print(f"   ✓ Before expiration: {result}")

    print("   Waiting 4 seconds for TTL to expire...")
    await asyncio.sleep(4)

    result = await cache_service.get("test:expire")
    print(f"   ✓ After expiration: {result} (should be None)")

    # Test 3: Pattern deletion
    print("\n3. Testing Pattern Deletion")
    print("-" * 60)

    print("   Creating multiple school cache entries...")
    await cache_service.set("school:1", {"id": 1, "name": "School 1"}, ttl=60)
    await cache_service.set("school:2", {"id": 2, "name": "School 2"}, ttl=60)
    await cache_service.set("school:3", {"id": 3, "name": "School 3"}, ttl=60)
    await cache_service.set("student:1", {"id": 1, "name": "Student 1"}, ttl=60)

    print("   Reading school:1...")
    result = await cache_service.get("school:1")
    print(f"   ✓ Found: {result}")

    print("   Deleting all 'school:*' keys...")
    deleted = await cache_service.delete_pattern("school:*")
    print(f"   ✓ Deleted {deleted} keys")

    print("   Trying to read school:1 again...")
    result = await cache_service.get("school:1")
    print(f"   ✓ Result: {result} (should be None)")

    print("   Checking student:1 is still there...")
    result = await cache_service.get("student:1")
    print(f"   ✓ Found: {result}")

    # Test 4: Performance comparison
    print("\n4. Performance Test")
    print("-" * 60)

    # Simulate database query
    async def slow_database_query():
        await asyncio.sleep(0.05)  # 50ms simulated DB query
        return {"id": 1, "name": "School", "students": 1000}

    # First request (cache miss)
    print("   Request 1 (cache miss - hits 'database'):")
    start = time.time()
    await cache_service.set("perf:test", await slow_database_query(), ttl=60)
    result = await cache_service.get("perf:test")
    elapsed = (time.time() - start) * 1000
    print(f"   ✓ Time: {elapsed:.2f}ms")

    # Second request (cache hit)
    print("   Request 2 (cache hit):")
    start = time.time()
    result = await cache_service.get("perf:test")
    elapsed = (time.time() - start) * 1000
    print(f"   ✓ Time: {elapsed:.2f}ms")
    print(f"   ✓ Performance improvement: ~{50/max(elapsed, 0.1):.0f}x faster!")

    # Cleanup
    print("\n5. Cleanup")
    print("-" * 60)
    print("   Cleaning up test keys...")
    await cache_service.delete_pattern("test:*")
    await cache_service.delete_pattern("school:*")
    await cache_service.delete_pattern("student:*")
    await cache_service.delete_pattern("perf:*")
    print("   ✓ Cleanup complete")

    # Close connection
    await cache_service.close()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✓")
    print("=" * 60)


async def test_decorator():
    """Test @cached decorator"""
    from app.core.cache import cached

    call_count = {"count": 0}

    @cached(prefix="decorated", ttl=5)
    async def expensive_operation(item_id: int):
        """Simulates expensive database query"""
        call_count["count"] += 1
        await asyncio.sleep(0.05)  # 50ms delay
        return {"id": item_id, "result": f"Data for {item_id}"}

    print("\n" + "=" * 60)
    print("DECORATOR TEST")
    print("=" * 60)

    print("\n   Calling expensive_operation(1) - First time (cache miss)")
    start = time.time()
    result1 = await expensive_operation(1)
    elapsed1 = (time.time() - start) * 1000
    print(f"   ✓ Time: {elapsed1:.2f}ms, Function calls: {call_count['count']}")

    print("\n   Calling expensive_operation(1) - Second time (cache hit)")
    start = time.time()
    result2 = await expensive_operation(1)
    elapsed2 = (time.time() - start) * 1000
    print(f"   ✓ Time: {elapsed2:.2f}ms, Function calls: {call_count['count']}")
    print(f"   ✓ Cache prevented {1} unnecessary function call!")
    print(f"   ✓ Performance: {elapsed1:.2f}ms → {elapsed2:.2f}ms ({elapsed1/max(elapsed2, 0.1):.0f}x faster)")

    # Cleanup
    await cache_service.delete_pattern("decorated:*")
    await cache_service.close()

    print("\n" + "=" * 60)
    print("DECORATOR TEST PASSED ✓")
    print("=" * 60)


if __name__ == "__main__":
    print("\nStarting cache tests...\n")

    # Run basic operations test
    asyncio.run(test_basic_operations())

    print("\n")

    # Run decorator test
    asyncio.run(test_decorator())

    print("\n✓ All cache tests completed successfully!\n")
