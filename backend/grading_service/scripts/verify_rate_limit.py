import asyncio
import httpx
import time

async def verify_rate_limit():
    url = "http://localhost:8002/api/v1/queue/metrics"
    # Limit is 30/minute
    
    async with httpx.AsyncClient() as client:
        # First ensure service is up
        try:
            resp = await client.get("http://localhost:8002/health")
            if resp.status_code != 200:
                print(f"Service not healthy: {resp.status_code}")
                return
            print("Service is healthy.")
        except Exception as e:
            print(f"Failed to connect: {e}")
            return

        print("Testing rate limit on /api/v1/queue/metrics (limit 30/min)...")
        
        start_time = time.time()
        count = 0
        limit_hit = False
        
        for i in range(40):
            resp = await client.get(url)
            if resp.status_code == 429:
                print(f"Rate limit hit at request #{i+1}!")
                print(f"Response: {resp.text}")
                limit_hit = True
                break
            elif resp.status_code == 200:
                print(f"Request #{i+1}: 200 OK")
                count += 1
            else:
                print(f"Request #{i+1}: {resp.status_code}")
                
        if limit_hit:
            print("SUCCESS: Rate limiting is ACTIVE.")
        else:
            print("FAILURE: Rate limiting is NOT ACTIVE (or limit not reached).")

if __name__ == "__main__":
    asyncio.run(verify_rate_limit())
