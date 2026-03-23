import asyncio
import time
from collections import Counter
import httpx

# Target URL for the test (we will run a temp server on 8081 for testing so we don't break your main setup)
URL = "http://localhost:8081/webhook"

# How many total requests to send
NUM_REQUESTS = 500
# How many requests to process at exactly the same time
CONCURRENCY = 100

def make_payload(update_id: int):
    # This mocks a standard Telegram bot '/start' message
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id,
            "date": int(time.time()),
            "chat": {"id": 999999999, "type": "private"},
            "text": "/start",
            "from": {"id": 999999999, "is_bot": False, "first_name": "LoadTest"}
        }
    }

async def fetch(client, update_id, semaphore, stats):
    async with semaphore:
        start = time.perf_counter()
        try:
            response = await client.post(URL, json=make_payload(update_id), timeout=10.0)
            status = response.status_code
        except Exception as e:
            status = type(e).__name__
        elapsed = time.perf_counter() - start
        
        stats['statuses'][status] += 1
        stats['times'].append(elapsed)

async def main():
    print(f"🚀 Starting load test on {URL}...")
    print(f"📊 Sending {NUM_REQUESTS} requests with {CONCURRENCY} concurrent users.")
    
    semaphore = asyncio.Semaphore(CONCURRENCY)
    stats = {'statuses': Counter(), 'times': []}
    
    # Wait for the server to be up
    await asyncio.sleep(2)
    
    async with httpx.AsyncClient() as client:
        start_time = time.perf_counter()
        tasks = [fetch(client, i, semaphore, stats) for i in range(NUM_REQUESTS)]
        await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_time
        
    print("\n--- 📈 Load Test Results ---")
    print(f"⏱️ Total time   : {total_time:.2f} seconds")
    print(f"⚡ Reqs/second  : {NUM_REQUESTS / total_time:.2f} rps")
    
    times = stats['times']
    if times:
        print(f"🟢 Fast latency : {min(times)*1000:.2f} ms")
        print(f"🟡 Avg latency  : {sum(times)/len(times)*1000:.2f} ms")
        print(f"🔴 Max latency  : {max(times)*1000:.2f} ms")
        
    print("📋 Status codes :", dict(stats['statuses']))
    
    if stats['statuses'].get(200) == NUM_REQUESTS:
        print("\n✅ SUCCESS: The bot safely enqueued all requests without failing!")
    else:
        print("\n⚠️ WARNING: Not all requests returned 200 OK.")

if __name__ == "__main__":
    asyncio.run(main())
