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




def _http_get_json(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (PokemonStreamOverlay/1.0)"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))

def fetch_complete_pokemon_info(name):
    clean_name = str(name).lower().strip().replace(" ", "-")
    cache_path = os.path.join(TARGET_CACHE_DIR, f"{clean_name}.json")

    # 1. Instant Cache Hit (< 1ms)
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # 2. Fetch raw JSON payloads directly (2 fast HTTP calls)
    try:
        p_data = _http_get_json(f"https://pokeapi.co/api/v2/pokemon/{clean_name}")
        s_data = _http_get_json(p_data["species"]["url"])
    except Exception as e:
        print(f"[POKEAPI ERROR] Failed fetching {name}: {e}")
        return None

    # Base Stats & EV Yields
    stats = {}
    ev_yield = {}
    bst = 0
    for st in p_data.get("stats", []):
        s_name = st.get("stat", {}).get("name", "").lower()
        val = int(st.get("base_stat", 0))
        effort = int(st.get("effort", 0))
        if s_name:
            stats[s_name] = val
            bst += val
            if effort > 0:
                ev_yield[s_name] = effort

    # Types & RAM-based Matchup Multipliers
    types = [t.get("type", {}).get("name", "").title() for t in p_data.get("types", [])]
    weaknesses, resistances, immunities = calculate_matchups(types, gen="modern")

    # Movepool Parsing
    tm_moves = []
    level_moves = []
    for m in p_data.get("moves", []):
        m_name = m.get("move", {}).get("name", "").replace("-", " ").title()
        for vgd in m.get("version_group_details", []):
            method = vgd.get("move_learn_method", {}).get("name", "")
            if method == "machine":
                tm_moves.append(m_name)
            elif method == "level-up":
                level_moves.append({
                    "move": m_name,
                    "level": int(vgd.get("level_learned_at", 0)),
                    "vg": str(vgd.get("version_group", {}).get("name", "all")).lower().replace("_", "-")
                })

    tm_moves = sorted(list(set(tm_moves)))
    level_moves.sort(key=lambda x: (x["level"], x["move"]))

    # Evolution Chain (Cached by Chain URL)
    evo_details = []
    try:
        evo_url = s_data.get("evolution_chain", {}).get("url")
        if evo_url:
            if evo_url in GLOBAL_EVO_CACHE:
                evo_details = GLOBAL_EVO_CACHE[evo_url]
            else:
                c_data = _http_get_json(evo_url)
                chain_node = c_data.get("chain", {})

                def parse_evo_node(node, acc):
                    sp_name = node.get("species", {}).get("name", "").title()
                    for next_node in node.get("evolves_to", []):
                        target_name = next_node.get("species", {}).get("name", "").title()
                        methods = []
                        for det in next_node.get("evolution_details", []):
                            if det.get("min_level"):
                                methods.append(f"Level {det['min_level']}")
                            if det.get("item"):
                                methods.append(f"Use {det['item']['name'].replace('-', ' ').title()}")
                            if det.get("trigger", {}).get("name") == "trade":
                                held = det.get("held_item")
                                held_str = f" holding {held['name'].replace('-', ' ').title()}" if held else ""
                                methods.append(f"Trade{held_str}")
                            if det.get("min_happiness"):
                                methods.append(f"Happiness {det['min_happiness']}")
                            if det.get("time_of_day"):
                                methods.append("Daytime" if det["time_of_day"] == "day" else "Night")

                        m_desc = ", ".join(methods) if methods else "Level up / Special"
                        acc.append(f"{sp_name} ➔ {target_name} ({m_desc})")
                        parse_evo_node(next_node, acc)

                parsed_list = []
                parse_evo_node(chain_node, parsed_list)
                GLOBAL_EVO_CACHE[evo_url] = parsed_list if parsed_list else ["Does not evolve"]
                evo_details = GLOBAL_EVO_CACHE[evo_url]
    except Exception as e:
        print(f"[EVO ERROR] {clean_name}: {e}")
        evo_details = ["Does not evolve"]

    # Growth & Egg Groups
    growth_name = s_data.get("growth_rate", {}).get("name", "Unknown").replace("-", " ").title()
    egg_groups = [g.get("name", "").replace("-", " ").title() for g in s_data.get("egg_groups", [])]
    hatch_counter = s_data.get("hatch_counter")
    hatch_steps = (hatch_counter + 1) * 255 if hatch_counter is not None else 0

    p_id = int(p_data.get("id", 1))
    sprites_raw = p_data.get("sprites", {}) or {}
    versions = sprites_raw.get("versions", {}) or {}

    gen_sprites = {
        # Generation 1 (Red/Blue / Yellow)
        "gen-1": (
            versions.get("generation-i", {}).get("red-blue", {}).get("front_default")
            or versions.get("generation-i", {}).get("yellow", {}).get("front_default")
        ),
        # Generation 2 (Gold/Silver / Crystal)
        "gen-2": (
            versions.get("generation-ii", {}).get("crystal", {}).get("front_default")
            or versions.get("generation-ii", {}).get("gold", {}).get("front_default")
        ),
        # Generation 3 (Ruby/Sapphire / Emerald / FireRed-LeafGreen)
        "gen-3": (
            versions.get("generation-iii", {}).get("emerald", {}).get("front_default")
            or versions.get("generation-iii", {}).get("ruby-sapphire", {}).get("front_default")
            or versions.get("generation-iii", {}).get("firered-leafgreen", {}).get("front_default")
        ),
        # Generation 4 (Diamond/Pearl / Platinum / HeartGold-SoulSilver)
        "gen-4": (
            versions.get("generation-iv", {}).get("platinum", {}).get("front_default")
            or versions.get("generation-iv", {}).get("diamond-pearl", {}).get("front_default")
            or versions.get("generation-iv", {}).get("heartgold-soulsilver", {}).get("front_default")
        ),
        # Generation 5 (Black/White / Animated)
        "gen-5": (
            versions.get("generation-v", {}).get("black-white", {}).get("animated", {}).get("front_default")
            or versions.get("generation-v", {}).get("black-white", {}).get("front_default")
        ),
        # Generation 6 (X/Y / Omega Ruby-Alpha Sapphire)
        "gen-6": (
            versions.get("generation-vi", {}).get("x-y", {}).get("front_default")
            or versions.get("generation-vi", {}).get("omegaruby-alphasapphire", {}).get("front_default")
        ),
        # Generation 7 (Sun/Moon / Ultra Sun-Ultra Moon)
        "gen-7": (
            versions.get("generation-vii", {}).get("ultra-sun-ultra-moon", {}).get("front_default")
            or versions.get("generation-vii", {}).get("icons", {}).get("front_default")
        ),
        # Modern / Showdown / Default
        "modern": (
            sprites_raw.get("other", {}).get("showdown", {}).get("front_default")
            or sprites_raw.get("front_default")
            or f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{p_id}.png"
        ),
    }

    # Default fallback sprite if a specific gen doesn't exist (e.g. Gen 9 Pokémon in Gen 1)
    default_sprite = (
        gen_sprites["modern"]
        or sprites_raw.get("front_default")
        or f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{p_id}.png"
    )

    result = {
        "name": p_data.get("name", clean_name).title(),
        "id": int(p_data.get("id", 1)),
        "sprite": default_sprite,            # default modern/standard
        "sprites": gen_sprites,              # full map of all gen sprites
        "types": types,
        "past_types": {},
        "past_damage_relations": {},
        "bst": bst,
        "stats": stats,
        "ev_yield": ev_yield,
        "weaknesses": weaknesses,
        "resistances": resistances,
        "immunities": immunities,
        "catch_rate": s_data.get("capture_rate", 45),
        "base_experience": p_data.get("base_experience", 0),
        "growth_rate": growth_name,
        "egg_groups": egg_groups,
        "hatch_steps": hatch_steps,
        "evolutions": evo_details,
        "level_moves": level_moves,
        "tm_moves": tm_moves,
    }

    # Save to disk
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
    except Exception as e:
        print(f"[CACHE WRITE ERROR] {clean_name}: {e}")

    return result

