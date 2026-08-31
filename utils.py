import io
import csv
import urllib.request
import os
import json
from datetime import datetime
from urllib.parse import quote_plus, unquote_plus
import pokebase as pb
from constants import *

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# File storage locations
TEAM_FILE = os.path.join(BASE_DIR, "team_list.json")
ACTIVE_TARGET_FILE = os.path.join(BASE_DIR, "active_target.json")
TASKS_DATA_FILE = os.path.join(BASE_DIR, "tasks_list.json")
CURRENT_TASK_FILE = os.path.join(BASE_DIR, "current_task.txt")
CATCH_TARGETS_DATA = os.path.join(BASE_DIR, "pokemon_list.txt")
NOTE_FILE = os.path.join(BASE_DIR, "video_message.txt")
PKMN_NAMES_CACHE = os.path.join(BASE_DIR, "all_pokemon_names.json")
ROUTES_CACHE_FILE = os.path.join(BASE_DIR, "all_location_areas.json")
ACTIVE_ROUTE_FILE = os.path.join(BASE_DIR, "active_route.json")
SHINY_HUNT_FILE = os.path.join(BASE_DIR, "shiny_hunt.json")
STATE_FILE = os.path.join(BASE_DIR, "stream_state.json")
EV_CACHE_FILE = os.path.join(BASE_DIR, "ev_yields.json")
IGNORED_CACHE_FILE = os.path.join(BASE_DIR, "deselected_pokemon.json")


TARGET_CACHE_DIR = "target_cache"
os.makedirs(TARGET_CACHE_DIR, exist_ok=True)



def calculate_matchups(types, gen="modern"):
    """
    Computes defending damage multipliers.
    gen: 'gen-1', 'gen-2', 'gen-3', 'gen-4', 'gen-5', or 'modern'
    """
    all_types = list(BASE_TYPE_CHART.keys())
    
    valid_attackers = []
    for t in all_types:
        if gen == 'gen-1' and t in ['dark', 'steel', 'fairy']:
            continue
        if gen in ['gen-2', 'gen-3', 'gen-4', 'gen-5'] and t == 'fairy':
            continue
        valid_attackers.append(t)

    multipliers = {t: 1.0 for t in valid_attackers}

    for def_type in types:
        def_t = str(def_type).lower().strip()
        for atk in valid_attackers:
            eff = BASE_TYPE_CHART.get(atk, {}).get(def_t, 1.0)

            # Gen 1 Quirks
            if gen == 'gen-1':
                if atk == 'ghost' and def_t == 'psychic':
                    eff = 0.0  # Gen 1 psychic immunity bug
                elif (atk == 'poison' and def_t == 'bug') or (atk == 'bug' and def_t == 'poison'):
                    eff = 2.0  # Gen 1 mutual super-effective
                elif atk == 'ice' and def_t == 'fire':
                    eff = 1.0  # Neutral in Gen 1

            # Gens 2-5 Steel Resistances
            elif gen in ['gen-2', 'gen-3', 'gen-4', 'gen-5']:
                if (atk == 'dark' or atk == 'ghost') and def_t == 'steel':
                    eff = 0.5  # Steel resisted Ghost and Dark before Gen 6

            multipliers[atk] *= eff

    weaknesses = {k: v for k, v in multipliers.items() if v > 1.0}
    resistances = {k: v for k, v in multipliers.items() if 0.0 < v < 1.0}
    immunities = [k for k, v in multipliers.items() if v == 0.0]

    return weaknesses, resistances, immunities


def load_deselected_pokemon():
    if os.path.exists(IGNORED_CACHE_FILE):
        try:
            with open(IGNORED_CACHE_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()

def save_deselected_pokemon(deselected_set):
    try:
        with open(IGNORED_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(list(deselected_set), f, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to save deselected pokemon: {e}")

def load_local_ev_yields(file_path=EV_CACHE_FILE) -> dict:
    """Loads yield cache from disk or initializes it with seed data."""
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    
    # Initialize file if missing or corrupted
    save_local_ev_yields(INITIAL_LOCAL_EV_YIELDS, file_path)
    return INITIAL_LOCAL_EV_YIELDS.copy()

def save_local_ev_yields(data: dict, file_path=EV_CACHE_FILE):
    """Persists current in-memory cache to disk."""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving EV yields cache: {e}")


LOCAL_EV_YIELDS = load_local_ev_yields()


# --- Resolution Logic ---
def resolve_ev_yield_for_version(species_slug, ev_yield_modern, past_ev_yields, version_name):
    s_clean = str(species_slug).lower().strip()
    v_clean = str(version_name).lower().replace(" ", "-")
    target_gen = VERSION_TO_GEN.get(v_clean)

    # 1. Check Hardcoded Gen Overrides First (e.g. Gen 3 Roselia)
    if target_gen and s_clean in HISTORICAL_EV_OVERRIDES:
        try:
            target_idx = GEN_ORDER.index(target_gen)
            for past_gen_slug, override_yield in HISTORICAL_EV_OVERRIDES[s_clean].items():
                if past_gen_slug in GEN_ORDER:
                    past_idx = GEN_ORDER.index(past_gen_slug)
                    if target_idx <= past_idx:
                        return override_yield
        except ValueError:
            pass

    # 2. Check PokéAPI past_stats
    if target_gen and past_ev_yields:
        try:
            target_idx = GEN_ORDER.index(target_gen)
            for past_gen_slug, past_yield in past_ev_yields.items():
                if past_gen_slug in GEN_ORDER and past_yield:
                    past_idx = GEN_ORDER.index(past_gen_slug)
                    if target_idx <= past_idx:
                        return past_yield
        except ValueError:
            pass

    # 3. Fast lookup from local persistent cache
    if s_clean in LOCAL_EV_YIELDS:
        return LOCAL_EV_YIELDS[s_clean]

    # 4. Fallback: Dynamic Cache Miss
    # If the modern yield was resolved, cache it to memory and write to ev_yields.json
    final_yield = ev_yield_modern if ev_yield_modern else {}
    if final_yield:
        LOCAL_EV_YIELDS[s_clean] = final_yield
        save_local_ev_yields(LOCAL_EV_YIELDS)

    return final_yield





def load_exp_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("exp_state", DEFAULT_EXP_STATE.copy())
        except Exception:
            return DEFAULT_EXP_STATE.copy()
    return DEFAULT_EXP_STATE.copy()

def save_exp_state(state):
    data = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    data["exp_state"] = state
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())


# --- State Loading & Saving ---
def load_ev_state():
    state = DEFAULT_EV_STATE.copy()
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                raw = data.get("ev_state", {})
                
                needs_migration = not any(k in raw for k in DEFAULT_EV_STATE)
                
                for k in DEFAULT_EV_STATE:
                    try:
                        state[k] = int(raw.get(k, 0))
                    except (ValueError, TypeError):
                        state[k] = 0
                
                if needs_migration:
                    save_ev_state(state)
        except Exception:
            state = DEFAULT_EV_STATE.copy()
    return state

def save_ev_state(state):
    clean_state = {k: int(state.get(k, 0)) for k in DEFAULT_EV_STATE}
    data = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
            
    data["ev_state"] = clean_state
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_catch_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                state = data.get("catch_state", DEFAULT_CATCH_STATE.copy())
                return state
        except Exception:
            return DEFAULT_CATCH_STATE.copy()
    return DEFAULT_CATCH_STATE.copy()

def save_catch_state(state):
    data = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    data["catch_state"] = state
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())


def resolve_pokemon_endpoint_slug(name_or_slug):
    """Maps base species slugs to PokéAPI /pokemon/ default form endpoints."""
    raw = str(name_or_slug or "").lower().strip().replace(" ", "-").replace("'", "").replace(".", "").replace(":", "")
    return DEFAULT_FORM_ALIASES.get(raw, raw)



def _http_get_json(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (PokemonStreamOverlay/1.0)"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_complete_pokemon_info(name):
    base_slug = str(name).lower().strip().replace(" ", "-").replace("'", "").replace(".", "").replace(":", "")
    endpoint_slug = resolve_pokemon_endpoint_slug(base_slug)
    
    os.makedirs(TARGET_CACHE_DIR, exist_ok=True)
    
    cache_path_base = os.path.join(TARGET_CACHE_DIR, f"{base_slug}.json")
    cache_path_endpoint = os.path.join(TARGET_CACHE_DIR, f"{endpoint_slug}.json")

    # 1. Cache Check
    for p in [cache_path_base, cache_path_endpoint]:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    print(f"[CACHE HIT] Loaded {name} from {p}")
                    return data
            except Exception as e:
                print(f"[CACHE READ ERROR] {p}: {e}")

    print(f"[DOWNLOADING] Fetching {endpoint_slug} from PokeAPI...")

    # 2. Network Fetch
    try:
        p_data = _http_get_json(f"https://pokeapi.co/api/v2/pokemon/{endpoint_slug}")
        if not p_data:
            print(f"[ERROR] No data returned for endpoint: {endpoint_slug}")
            return None
        
        species_url = p_data.get("species", {}).get("url")
        s_data = _http_get_json(species_url) if species_url else {}
    except Exception as e:
        print(f"[NETWORK ERROR] Failed for {endpoint_slug}: {e}")
        return None

    # Base Stats & EVs
    stats = {}
    ev_yield = {}
    bst = 0
    for st in p_data.get("stats", []):
        s_name = st.get("stat", {}).get("name", "").lower()
        val = int(st.get("base_stat", 0) or 0)
        effort = int(st.get("effort", 0) or 0)
        if s_name:
            stats[s_name] = val
            bst += val
            if effort > 0:
                ev_yield[s_name] = effort

    # Types & Matchups
    types = [t.get("type", {}).get("name", "").title() for t in p_data.get("types", [])]
    try:
        weaknesses, resistances, immunities = calculate_matchups(types, gen="modern")
    except Exception as e:
        print(f"[MATCHUP ERROR] {endpoint_slug}: {e}")
        weaknesses, resistances, immunities = [], [], []

    # Moves
    tm_moves = []
    level_moves = []
    for m in p_data.get("moves", []):
        m_name = m.get("move", {}).get("name", "").replace("-", " ").title()
        for vgd in m.get("version_group_details", []):
            method = vgd.get("move_learn_method", {}).get("name", "")
            if method == "machine":
                tm_moves.append(m_name)
            elif method == "level-up":
                raw_lvl = vgd.get("level_learned_at", 0)
                try:
                    lvl_int = int(raw_lvl) if raw_lvl is not None else 0
                except Exception:
                    lvl_int = 0
                level_moves.append({
                    "move": m_name,
                    "level": lvl_int,
                    "vg": str(vgd.get("version_group", {}).get("name", "all")).lower().replace("_", "-")
                })

    tm_moves = sorted(list(set(tm_moves)))
    level_moves.sort(key=lambda x: (x.get("level", 0), str(x.get("move", ""))))

    # Sprites
    p_id = int(p_data.get("id", 1) or 1)
    sprites_raw = p_data.get("sprites", {}) or {}
    versions = sprites_raw.get("versions", {}) or {}
    
    gen_sprites = {
        "gen-1": versions.get("generation-i", {}).get("red-blue", {}).get("front_default") or versions.get("generation-i", {}).get("yellow", {}).get("front_default"),
        "gen-2": versions.get("generation-ii", {}).get("crystal", {}).get("front_default") or versions.get("generation-ii", {}).get("gold", {}).get("front_default"),
        "gen-3": versions.get("generation-iii", {}).get("emerald", {}).get("front_default") or versions.get("generation-iii", {}).get("ruby-sapphire", {}).get("front_default"),
        "gen-4": versions.get("generation-iv", {}).get("platinum", {}).get("front_default") or versions.get("generation-iv", {}).get("diamond-pearl", {}).get("front_default"),
        "gen-5": versions.get("generation-v", {}).get("black-white", {}).get("front_default"),
        "gen-6": versions.get("generation-vi", {}).get("x-y", {}).get("front_default"),
        "gen-7": versions.get("generation-vii", {}).get("ultra-sun-ultra-moon", {}).get("front_default"),
        "modern": sprites_raw.get("other", {}).get("showdown", {}).get("front_default") or sprites_raw.get("front_default")
    }

    result = {
        "name": s_data.get("name", base_slug).replace("-", " ").title() if isinstance(s_data, dict) else base_slug.title(),
        "slug": base_slug,
        "endpoint_slug": endpoint_slug,
        "id": p_id,
        "sprite": gen_sprites["modern"] or sprites_raw.get("front_default") or f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{p_id}.png",
        "sprites": gen_sprites,
        "types": types,
        "bst": bst,
        "stats": stats,
        "ev_yield": ev_yield,
        "weaknesses": list(weaknesses) if isinstance(weaknesses, (set, tuple)) else (weaknesses or []),
        "resistances": list(resistances) if isinstance(resistances, (set, tuple)) else (resistances or []),
        "immunities": list(immunities) if isinstance(immunities, (set, tuple)) else (immunities or []),
        "catch_rate": s_data.get("capture_rate", 45) if isinstance(s_data, dict) else 45,
        "growth_rate": s_data.get("growth_rate", {}).get("name", "Unknown").title() if isinstance(s_data, dict) else "Medium",
        "level_moves": level_moves,
        "tm_moves": tm_moves,
    }

    # Save to disk
    for save_path in {cache_path_base, cache_path_endpoint}:
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, default=list)
            print(f"[CACHE WRITE SUCCESS] Saved {save_path}")
        except Exception as e:
            print(f"[CACHE WRITE FAILED] {save_path}: {e}")

    return result