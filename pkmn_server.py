import os
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import time
import threading
import pokebase as pb

# Import all handler functions from handlers.py
import pkmn_handlers as handlers
from pkmn_handlers import *

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
    import os
    import time
    global LOCAL_EV_YIELDS

    print("[DEX CACHE] Starting background National Dex prefetcher...")

    cache_dir = getattr(handlers, "TARGET_CACHE_DIR", "target_cache")
    os.makedirs(cache_dir, exist_ok=True)

    # 1. Get all names locally if already loaded in memory, otherwise range 1..1025
    species_list = []
    pkmn_evos = getattr(handlers, "all_pkmn_collection", None) or getattr(handlers, "load_all_pokemon_names", lambda: {})()
    if isinstance(pkmn_evos, dict) and pkmn_evos:
        species_list = list(pkmn_evos.keys())
    else:
        species_list = [str(i) for i in range(1, 1026)]

    total = len(species_list)
    dirty_count = 0

    for idx, item in enumerate(species_list, 1):
        slug = str(item).lower().strip().replace(" ", "-")
        endpoint_slug = getattr(handlers, "resolve_pokemon_endpoint_slug", lambda x: x)(slug)

        target_file = os.path.join(cache_dir, f"{slug}.json")
        endpoint_file = os.path.join(cache_dir, f"{endpoint_slug}.json")

        # Check either file path
        found_file = target_file if os.path.exists(target_file) else (endpoint_file if os.path.exists(endpoint_file) else None)

        # 1. FAST CHECK: If either target file exists, read EVs instantly (0 network calls)
        if found_file:
            if slug not in handlers.LOCAL_EV_YIELDS:
                try:
                    import json
                    with open(found_file, "r", encoding="utf-8") as f:
                        cached_data = json.load(f)
                        if "ev_yield" in cached_data and cached_data["ev_yield"]:
                            handlers.LOCAL_EV_YIELDS[slug] = cached_data["ev_yield"]
                            dirty_count += 1
                except Exception:
                    pass
            continue

        # 2. MISS: Only hit PokéAPI if neither file exists
        try:
            print(f"[DEX CACHE] [{idx}/{total}] Downloading & baking {slug.title()}...")
            data = handlers.fetch_complete_pokemon_info(slug)

            if data and "ev_yield" in data:
                handlers.LOCAL_EV_YIELDS[slug] = data["ev_yield"]
                dirty_count += 1

            time.sleep(0.6)

            if dirty_count >= 10:
                handlers.save_local_ev_yields(handlers.LOCAL_EV_YIELDS)
                dirty_count = 0

        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "too many requests" in err_str:
                print(f"[DEX CACHE] Hit 429 rate limit at {slug}. Pausing 60s...")
                time.sleep(60)
            else:
                print(f"[DEX CACHE ERROR] {slug}: {e}")
                time.sleep(1.0)

    if dirty_count > 0:
        handlers.save_local_ev_yields(handlers.LOCAL_EV_YIELDS)

    print("[DEX CACHE] Finished National Dex check.")

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