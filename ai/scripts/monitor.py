import json, redis

r = redis.Redis(decode_responses=True)
p = r.pubsub()
p.psubscribe("race:*")
seen_ids = False

for m in p.listen():
    if m["type"] != "pmessage":
        continue
    try:
        e = json.loads(m["data"])
    except json.JSONDecodeError:
        continue
    if e.get("type") == "tick":
        if not seen_ids:
            print("driver_ids:", [d["driver_id"] for d in e["positions"]])
            seen_ids = True
        continue
    print(m["channel"], e.get("type"), str(e)[:150], flush=True)
