import asyncio, json, collections, urllib.request
import websockets

def post(path, body):
    req = urllib.request.Request("http://localhost:8000"+path, data=json.dumps(body).encode(), headers={"Content-Type":"application/json"}, method="POST")
    return json.load(urllib.request.urlopen(req))

async def main():
    r = post("/races", {"circuit":{"id":"interlagos","layout_id":"interlagos-2"},"laps":2,"grid":["max-verstappen","lando-norris","charles-leclerc","george-russell"],"weather":"dry"})
    print("race:", r["race_id"], "grid:", [g["driver_id"] for g in r["grid"]])
    counts = collections.Counter()
    overtakes = 0
    last_positions = None
    ticks = 0
    async with websockets.connect("ws://localhost:8000"+r["ws_path"]) as ws:
        async for raw in ws:
            m = json.loads(raw)
            counts[m["type"]] += 1
            if m["type"] == "tick":
                ticks += 1
                order = [p["driver_id"] for p in sorted(m["positions"], key=lambda p: p["position"])]
                if last_positions and order != last_positions:
                    overtakes += 1
                last_positions = order
                if ticks == 50:
                    print("tick sample pos[0..1]:", json.dumps(m["positions"][:2])[:400])
            if m["type"] in ("race_control","pit_stop","weather_changed","tyre_worn","race_end"):
                print("evento:", m["type"], m.get("message", m.get("driver_name","")), m.get("sim_ts"))
    print("mensagens:", dict(counts))
    print("mudanças de ordem nos ticks:", overtakes)

asyncio.run(main())
