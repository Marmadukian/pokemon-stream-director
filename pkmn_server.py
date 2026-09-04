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
STAT_MAP = {
    "1": "hp",
    "2": "attack",
    "3": "defense",
    "4": "special-attack",
    "5": "special-defense",
    "6": "speed"
}

POKEMON_CSV_URL = "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/pokemon.csv"
STATS_CSV_URL = "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/pokemon_stats.csv"

CURRENT_VERSION = "v1.0.0"
REPO_OWNER = "Marmadukian"
REPO_NAME = "pokemon-stream-director"

def parse_semver(tag: str) -> tuple[int, ...]:
    """Strips non-digits (like 'v') and parses major, minor, patch."""
    numbers = re.findall(r"\d+", tag)
    return tuple(map(int, numbers)) if numbers else (0,)

def check_for_updates() -> dict:
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": f"{REPO_NAME}-UpdateCheck"}  # GitHub API requires a User-Agent
    )

    try:
        with urllib.request.urlopen(req, timeout=3) as response:
            if response.status != 200:
                return {"update_available": False}

            data = json.loads(response.read().decode("utf-8"))
            latest_tag = data.get("tag_name", "")
            release_url = data.get("html_url", "")

            # Compares tuples, e.g. (1, 1, 0) > (1, 0, 0)
            if parse_semver(latest_tag) > parse_semver(CURRENT_VERSION):
                return {
                    "update_available": True,
                    "latest_version": latest_tag,
                    "release_url": release_url,
                }

    except Exception:
        # Fails silently so offline play or rate-limits never stall the server
        pass

    return {"update_available": False}



def _run_bulk_ev_sync():
    print("[DEX CACHE] Starting bulk National Dex download from PokéAPI GitHub...")

    cache_dir = getattr(handlers, "TARGET_CACHE_DIR", "target_cache")
    os.makedirs(cache_dir, exist_ok=True)

    try:
        # 1. Fetch pokemon.csv (ID -> Slug mapping)
        print("[DEX CACHE] Downloading pokemon list...")
        req = urllib.request.Request(POKEMON_CSV_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            pokemon_csv_text = resp.read().decode("utf-8")

        # 2. Fetch pokemon_stats.csv (EV effort values per stat)
        print("[DEX CACHE] Downloading EV stats...")
        req = urllib.request.Request(STATS_CSV_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            stats_csv_text = resp.read().decode("utf-8")

        # 3. Parse pokemon identifiers
        # id -> slug
        id_to_slug = {}
        reader = csv.DictReader(io.StringIO(pokemon_csv_text))
        for row in reader:
            pk_id = row.get("id")
            slug = row.get("identifier")
            if pk_id and slug:
                id_to_slug[pk_id] = slug.lower().strip()

        # 4. Parse effort yields grouped by pokemon_id
        # pokemon_id -> { "attack": 2, ... }
        ev_by_id = {}
        reader = csv.DictReader(io.StringIO(stats_csv_text))
        for row in reader:
            pk_id = row.get("pokemon_id")
            stat_id = row.get("stat_id")
            effort = int(row.get("effort", 0))

            if effort > 0 and stat_id in STAT_MAP:
                stat_name = STAT_MAP[stat_id]
                if pk_id not in ev_by_id:
                    ev_by_id[pk_id] = {}
                ev_by_id[pk_id][stat_name] = effort

        # 5. Populate LOCAL_EV_YIELDS in memory
        updated_count = 0
        for pk_id, ev_dict in ev_by_id.items():
            slug = id_to_slug.get(pk_id)
            if slug:
                handlers.LOCAL_EV_YIELDS[slug] = ev_dict
                updated_count += 1

        # 6. Commit to disk through your existing save handler
        if hasattr(handlers, "save_local_ev_yields"):
            handlers.save_local_ev_yields(handlers.LOCAL_EV_YIELDS)

        print(f"[DEX CACHE] Successfully bulk-loaded {updated_count} EV yields in seconds.")

    except Exception as e:
        print(f"[DEX CACHE ERROR] Bulk sync failed: {e}")

def start_ev_cache_worker():
    """Starts the bulk EV loader in a daemon thread so it runs in the background."""
    worker = threading.Thread(target=_run_bulk_ev_sync, daemon=True)
    worker.start()


class UnifiedTrackerHandler(BaseHTTPRequestHandler):
    def _dispatch_route(self, path, params):
        if path in handlers.ROUTES:
            handler = handlers.ROUTES[path]
            # Handlers expect (params, self) or (params)
            try:
                result = handler(params, self)
            except TypeError:
                result = handler(params)

            # Check if the handler already handled headers/writing (e.g. sync_catch)
            if self.wfile.closed:
                return

            if isinstance(result, tuple):
                body_text, (header_name, header_value) = result
            else:
                body_text = str(result)
                header_name, header_value = "Content-Type", "text/plain"

            self.send_response(200)
            self.send_header(header_name, header_value)
            self.end_headers()
            self.wfile.write(body_text.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query_params = urllib.parse.parse_qs(parsed_path.query)
        self._dispatch_route(path, query_params)

    def do_POST(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        # Start with URL query params if any were attached to the POST
        params = urllib.parse.parse_qs(parsed_path.query)

        # Read POST body content
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            body_bytes = self.rfile.read(content_length)
            content_type = self.headers.get("Content-Type", "").lower()

            # Handle JSON body (e.g., {"action": "shiny_inc"})
            if "application/json" in content_type:
                try:
                    json_data = json.loads(body_bytes.decode("utf-8"))
                    for k, v in json_data.items():
                        # Wrap values in lists to preserve compatibility with parse_qs dictionary shapes
                        params[k] = [str(v)] if not isinstance(v, list) else [str(i) for i in v]
                except Exception:
                    pass
            else:
                # Handle form-urlencoded body (action=shiny_inc)
                form_params = urllib.parse.parse_qs(body_bytes.decode("utf-8"))
                for k, v in form_params.items():
                    params[k] = v

        self._dispatch_route(path, params)

if __name__ == "__main__":
    handlers.init()
    handlers.LOCAL_EV_YIELDS = handlers.load_local_ev_yields()
    
    result = check_for_updates()

    start_ev_cache_worker()

    ip = get_local_ip()
    server = HTTPServer(("0.0.0.0", PORT), UnifiedTrackerHandler)
    print("=====================================================")
    print(f"PKMN Backend tool Running on http://{ip}:{PORT}")
    print("Active Endpoints:")
    for endpoint in handlers.ROUTES.keys():
        print(f"  - http://{ip}:{PORT}{endpoint}")
    print("=====================================================")
    if result.get("update_available"):
        print(f"*****\n********\n*********\n************Update available: {result['latest_version']} -> {result['release_url']}")
    else:
        print("Server up to date.")
    server.serve_forever()