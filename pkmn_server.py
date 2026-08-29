import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import time
import threading
import pokebase as pb

# Import all handler functions from handlers.py
import pkmn_handlers as handlers

PORT = 1350

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _run_ev_cache_loop():
    global LOCAL_EV_YIELDS

    print("[EV CACHE] Starting background EV prefetcher (0.75s cadence)...")
    
    # Standard National Dex IDs 1 to 1025
    TOTAL_DEX = 1025
    dirty_count = 0

    for p_id in range(1, TOTAL_DEX + 1):
        # Determine if we already have this Pokémon by ID or slug in memory
        # (We check by slug after resolving or fallback check)
        try:
            # 1. Quick check without network if possible
            # If you already have slug mappings, you can skip here.
            p_data = pb.pokemon(p_id)
            slug = str(p_data.name).lower().strip()

            if slug in handlers.LOCAL_EV_YIELDS and handlers.LOCAL_EV_YIELDS[slug]:
                continue  # Already cached

            # 2. Extract base stat effort values (EV yield)
            ev_yield = {}
            for stat_entry in p_data.stats:
                effort = getattr(stat_entry, "effort", 0)
                if effort > 0:
                    stat_name = getattr(stat_entry.stat, "name", "").lower()
                    if stat_name:
                        ev_yield[stat_name] = effort

            # 3. Store in LOCAL_EV_YIELDS dictionary
            if ev_yield:
                handlers.LOCAL_EV_YIELDS[slug] = ev_yield
                dirty_count += 1
                print(f"[EV CACHE] [{p_id}/{TOTAL_DEX}] Cached {slug.title()}: {ev_yield}")

            # 4. Flush to disk every 10 new entries so progress is preserved across restarts
            if dirty_count >= 10:
                handlers.save_local_ev_yields(handlers.LOCAL_EV_YIELDS)
                dirty_count = 0

            # 5. Polite timing interval (0.75s)
            time.sleep(0.75)

        except Exception as e:
            # Handle rate-limit 429 or network hiccups gracefully
            err_str = str(e).lower()
            if "429" in err_str or "too many requests" in err_str:
                print("[EV CACHE] Hit rate limit (429), pausing for 60s...")
                time.sleep(60)
            else:
                print(f"[EV CACHE ERROR] ID {p_id}: {e}")
                time.sleep(1.5)

    # Final flush to disk when complete
    if dirty_count > 0:
        handlers.save_local_ev_yields(handlers.LOCAL_EV_YIELDS)
        
    print("[EV CACHE] Complete! All National Dex species EV yields cached locally.")


def start_ev_cache_worker():
    """Starts the EV cache worker in a daemon thread so it runs in the background."""
    worker = threading.Thread(target=_run_ev_cache_loop, daemon=True)
    worker.start()


class UnifiedTrackerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query_params = urllib.parse.parse_qs(parsed_path.query)

        if path in handlers.ROUTES:
            handler = handlers.ROUTES[path]
            result = handler(query_params)

            # Unpack tuple if handler explicitly provided a header
            if isinstance(result, tuple):
                body_text, (header_name, header_value) = result
            else:
                body_text = str(result)
                header_name, header_value = "Content-Type", "text/plain"

            self.send_response(200)
            self.send_header(header_name, header_value)
            self.end_headers()

            # Always encode body_text (which is strictly a string now)
            self.wfile.write(body_text.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")

if __name__ == "__main__":
    handlers.init()
    handlers.LOCAL_EV_YIELDS = handlers.load_local_ev_yields()
    
    start_ev_cache_worker()

    ip = get_local_ip()
    server = HTTPServer(("0.0.0.0", PORT), UnifiedTrackerHandler)
    print("=====================================================")
    print(f"PKMN Backend tool Running on http://{ip}:{PORT}")
    print("Active Endpoints:")
    for endpoint in handlers.ROUTES.keys():
        print(f"  - {endpoint}")
    print("=====================================================")
    server.serve_forever()