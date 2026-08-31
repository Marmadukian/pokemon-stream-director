import io
import csv
import urllib.request
import os
import json
from datetime import datetime
from urllib.parse import quote_plus, unquote_plus
import pokebase as pb

from utils import *
from obs_overlays import *
from constants import *


JS_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "shared.js")
with open(JS_FILE_PATH, "r", encoding="utf-8") as f:
    SHARED_POKEMON_JS = f.read()




TARGET_CACHE_DIR = "target_cache"
os.makedirs(TARGET_CACHE_DIR, exist_ok=True)

# In-memory session cache for shared evolution chains
GLOBAL_EVO_CACHE = {}

all_location_areas = []
all_pkmn_collection = []


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
def generate_ev_widget(ev_state, target, is_remote=False):
    total_evs = sum(
        v for k, v in ev_state.items()
        if k in ["hp", "attack", "defense", "special-attack", "special-defense", "speed"]
        and isinstance(v, (int, float))
    )
    base_url = "/remote" if is_remote else "/"

    target_yields = target.get("ev_yield", {}) if target else {}
    if target_yields:
        yield_summary = " +".join([
            f"{v} {k.replace('special-', 'Sp. ').title()}"
            for k, v in target_yields.items()
        ])
        button_label = f"+1 DEFEATED (+{yield_summary})"
        button_disabled = ""
    else:
        button_label = "+1 DEFEATED (Select Target to Auto-Add)"
        button_disabled = "opacity-60 pointer-events-none"

    stat_config = [
        ("hp", "HP", "bg-emerald-500", "text-emerald-400", "border-emerald-500"),
        ("attack", "ATK", "bg-rose-500", "text-rose-400", "border-rose-500"),
        ("defense", "DEF", "bg-blue-500", "text-blue-400", "border-blue-500"),
        ("special-attack", "SPA", "bg-purple-500", "text-purple-400", "border-purple-500"),
        ("special-defense", "SPD", "bg-indigo-500", "text-indigo-400", "border-indigo-500"),
        ("speed", "SPE", "bg-amber-500", "text-amber-400", "border-amber-500"),
    ]

    rows = []
    for stat_key, label, bar_color, text_color, border_color in stat_config:
        val = int(ev_state.get(stat_key, 0))
        pct = min(100, int((val / 252) * 100))

        rows.append(f"""
        <div class="bg-slate-950/70 border border-slate-800 rounded-xl p-2.5 space-y-1.5">
            <div class="flex items-center justify-between">
                <span class="text-xs font-black {text_color} tracking-wider">{label}</span>
                <span class="font-mono text-xs font-bold text-slate-200">{val} <span class="text-[10px] text-slate-500">/ 252</span></span>
            </div>
            <div class="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                <div class="{bar_color} h-full rounded-full transition-all duration-300" style="width: {pct}%"></div>
            </div>
            <div class="flex items-center justify-between gap-1 pt-1">
                <div class="flex gap-1">
                    <a href="{base_url}?action=ev_adjust&stat={stat_key}&amt=-4" class="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-[10px] rounded transition">-4</a>
                    <a href="{base_url}?action=ev_adjust&stat={stat_key}&amt=-1" class="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-[10px] rounded transition">-1</a>
                </div>
                <div class="flex gap-1">
                    <a href="{base_url}?action=ev_adjust&stat={stat_key}&amt=1" class="px-2.5 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-100 font-bold text-[10px] rounded border border-slate-700 transition">+1</a>
                    <a href="{base_url}?action=ev_adjust&stat={stat_key}&amt=4" class="px-2.5 py-0.5 {bar_color}/20 {text_color} border {border_color}/40 font-bold text-[10px] rounded transition">+4</a>
                    <a href="{base_url}?action=ev_adjust&stat={stat_key}&amt=10" class="px-2 py-0.5 bg-slate-700 hover:bg-slate-600 text-white font-bold text-[10px] rounded transition">+10</a>
                </div>
            </div>
        </div>
        """)

    return f"""
    <div class="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-4 space-y-3">
        <div class="flex items-center justify-between">
            <h3 class="text-xs uppercase font-bold text-emerald-400 flex items-center gap-1.5">
                <span>💪 EV Training Tracker</span>
            </h3>
            <div class="flex items-center gap-2">
                <a href="/obs/evs" target="_blank" class="text-[11px] text-emerald-400/80 hover:underline">OBS Overlay ↗</a>
                <a href="{base_url}?action=ev_reset" onclick="return confirm('Reset all EV stats to 0?');" class="text-[10px] text-rose-400 hover:text-rose-300">Reset All</a>
            </div>
        </div>

        <a href="{base_url}?action=ev_add_target" class="block w-full text-center py-3 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black text-xs uppercase tracking-wider rounded-xl shadow-lg shadow-emerald-500/20 active:scale-[0.98] transition {button_disabled}">
            {button_label}
        </a>

        <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-3">
            <div class="flex justify-between text-xs font-bold mb-1">
                <span class="text-slate-400">Total Investment</span>
                <span class="font-mono text-emerald-400">{total_evs} <span class="text-slate-500">/ 510</span></span>
            </div>
            <div class="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                <div class="bg-emerald-500 h-full rounded-full transition-all duration-300" style="width: {min(100, int((total_evs / 510) * 100))}%"></div>
            </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
            {''.join(rows)}
        </div>
    </div>
    """


def init():
    global all_pkmn_collection
    all_pkmn_collection = load_all_pokemon_names()
    global all_location_areas
    all_location_areas = load_all_location_areas()

def format_area_name(slug):
    clean = slug[:-5] if slug.endswith("-area") else slug
    return clean.replace("-", " ").title()

def load_active_route():
    if os.path.exists(ACTIVE_ROUTE_FILE):
        try:
            with open(ACTIVE_ROUTE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def load_all_pokemon_names():
    global all_pkmn_collection
    
    # 1. Load from local cache if exists
    if os.path.exists(PKMN_NAMES_CACHE):
        try:
            with open(PKMN_NAMES_CACHE, "r", encoding="utf-8") as f:
                all_pkmn_collection = json.load(f)
                if all_pkmn_collection and isinstance(all_pkmn_collection, dict):
                    return all_pkmn_collection
        except Exception:
            pass

    print("[POKEMON] Fetching full species dataset in 1 request from GitHub...")
    evo_map = {}
    try:
        # Fetch PokeAPI's raw species CSV directly from GitHub (single request, ~50KB)
        url = "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/pokemon_species.csv"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            csv_text = response.read().decode('utf-8')
        
        reader = csv.DictReader(io.StringIO(csv_text))
        
        # 1. Group species count by evolution_chain_id
        chain_counts = {}
        species_entries = []
        for row in reader:
            s_name = row['identifier'].replace('-', ' ').title()
            chain_id = row['evolution_chain_id']
            species_entries.append((s_name, chain_id))
            chain_counts[chain_id] = chain_counts.get(chain_id, 0) + 1

        # 2. Map each species name to its total line count
        for s_name, chain_id in species_entries:
            evo_map[s_name] = chain_counts.get(chain_id, 1)

        all_pkmn_collection = evo_map

        # Save to local cache file
        with open(PKMN_NAMES_CACHE, "w", encoding="utf-8") as f:
            json.dump(all_pkmn_collection, f, indent=2)
            
        print(f"[POKEMON] Successfully built & cached {len(all_pkmn_collection)} species in 1 request.")

    except Exception as e:
        print(f"[POKEMON ERROR] Bulk fetch failed ({e}), falling back to 1s.")
        all_pkmn_collection = {}

    return all_pkmn_collection


def load_ev_state():
    global ev_state
    ev_state = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                ev_state = data.get("ev_state", {"kills": 0, "total_evs": 0, "target_stat": "All"})
        except Exception:
            pass
    return ev_state

def save_ev_state(state):
    global ev_state
    ev_state = state
    data = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
    data["ev_state"] = ev_state
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def infer_versions_from_slug(slug: str) -> list:
    """Infers known game versions from the location area slug prefix."""
    slug_lower = slug.lower().strip()
    for region, versions in REGION_VERSION_MAP.items():
        if slug_lower.startswith(region):
            return versions
    return []


def infer_versions_from_slug(slug: str) -> list:
    slug_lower = slug.lower().strip()
    for key, versions in LANDMARK_REGION_MAP.items():
        if key in slug_lower:
            return versions
    return []

def load_all_location_areas():
    global all_location_areas
    if all_location_areas:
        return all_location_areas

    # 1. Read local cache and ensure "versions" key exists
    if os.path.exists(ROUTES_CACHE_FILE):
        try:
            with open(ROUTES_CACHE_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
                if cached and isinstance(cached, list):
                    # Auto-migrate any cache missing the versions field
                    needs_resave = False
                    for item in cached:
                        if "versions" not in item or not item["versions"]:
                            item["versions"] = infer_versions_from_slug(item.get("slug", ""))
                            needs_resave = True
                    if needs_resave:
                        with open(ROUTES_CACHE_FILE, "w", encoding="utf-8") as wf:
                            json.dump(cached, wf, indent=2)
                    all_location_areas = cached
                    return all_location_areas
        except Exception:
            pass

    # 2. Pokébase fetch fallback
    try:
        resource = pb.APIResourceList("location-area")
        all_location_areas = [
            {
                "slug": slug,
                "name": format_area_name(slug),
                "versions": infer_versions_from_slug(slug)
            }
            for slug in resource.names
        ]

        if all_location_areas:
            with open(ROUTES_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(all_location_areas, f, indent=2)
    except Exception as e:
        print(f"[POKEMON] Error loading locations: {e}")

    return all_location_areas

def parse_location_encounters_by_game(location_area_data):
    """Groups route encounters by game version and updates the location's version cache."""
    global all_location_areas
    games = {}
    found_versions = set()

    for p_enc in location_area_data.get("pokemon_encounters", []):
        p_name = p_enc.get("pokemon", {}).get("name", "").title()

        for v_detail in p_enc.get("version_details", []):
            raw_ver = v_detail.get("version", {}).get("name", "unknown")
            ver_slug = raw_ver.lower().strip()
            version_name = raw_ver.replace("-", " ").title()

            found_versions.add(ver_slug)

            if version_name not in games:
                games[version_name] = {}

            if p_name not in games[version_name]:
                games[version_name][p_name] = {
                    "methods": set(),
                    "min_level": 100,
                    "max_level": 1,
                    "chance": 0,
                }

            # Aggregate methods, levels, and max chances
            for enc in v_detail.get("encounter_details", []):
                method_name = enc.get("method", {}).get("name", "").replace("-", " ")
                if method_name:
                    games[version_name][p_name]["methods"].add(method_name)

                min_lvl = enc.get("min_level", 1)
                max_lvl = enc.get("max_level", 1)
                chance = enc.get("chance", 0)

                games[version_name][p_name]["min_level"] = min(
                    games[version_name][p_name]["min_level"], min_lvl
                )
                games[version_name][p_name]["max_level"] = max(
                    games[version_name][p_name]["max_level"], max_lvl
                )
                games[version_name][p_name]["chance"] += chance

    # Update version tags in the master location list if available
    area_name = location_area_data.get("name")
    if area_name and all_location_areas and found_versions:
        updated = False
        for loc in all_location_areas:
            if loc.get("slug") == area_name:
                loc["versions"] = sorted(list(found_versions))
                updated = True
                break
        if updated:
            try:
                with open(ROUTES_CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump(all_location_areas, f, indent=2)
            except Exception:
                pass

    return games

# --- Persistence Helpers ---

def load_shiny_hunt():
  if os.path.exists(SHINY_HUNT_FILE):
    try:
      with open(SHINY_HUNT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      pass
  return {"target": "None", "count": 0, "method": "Random Encounters"}

def save_shiny_hunt(data):
  with open(SHINY_HUNT_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

def load_team():
    if os.path.exists(TEAM_FILE):
        try:
            with open(TEAM_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_team(team):
    with open(TEAM_FILE, "w", encoding="utf-8") as f:
        json.dump(team, f, indent=2)

def load_active_target(default_pokemon="golem"):
  if os.path.exists(ACTIVE_TARGET_FILE):
    try:
      with open(ACTIVE_TARGET_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

      # Check if cached data is missing 'vg' in level_moves
      needs_rebuild = False
      if data and "level_moves" in data and len(data["level_moves"]) > 0:
        if "vg" not in data["level_moves"][0]:
          needs_rebuild = True

      if needs_rebuild and data.get("slug"):
        print(
            f"[Sync] Upgrading target '{data['slug']}' with version group"
            " tags..."
        )
        return fetch_complete_pokemon_info(data["slug"])

      return data
    except Exception as e:
      print(f"[Warn] Failed reading active target: {e}")

  # If no file or empty, fetch default initial Pokémon
  return fetch_complete_pokemon_info(default_pokemon)


def save_active_target(data):
  with open(ACTIVE_TARGET_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
def fetch_and_build_target_dict(pokemon_name_or_id):
    try:
        slug = str(pokemon_name_or_id).lower().strip()
        headers = {"User-Agent": "Mozilla/5.0"}
        
        # 1. Fetch Main Pokemon JSON
        req = urllib.request.Request(f"https://pokeapi.co/api/v2/pokemon/{slug}", headers=headers)
        with urllib.request.urlopen(req) as resp:
            p = json.loads(resp.read().decode('utf-8'))

        # 2. Fetch Species JSON (for catch rate, growth rate, evolutions)
        species_url = p.get("species", {}).get("url")
        s_raw = {}
        if species_url:
            s_req = urllib.request.Request(species_url, headers=headers)
            with urllib.request.urlopen(s_req) as resp:
                s_raw = json.loads(resp.read().decode('utf-8'))

        # Base Stats
        stats = {s["stat"]["name"]: s["base_stat"] for s in p.get("stats", [])}
        bst = sum(stats.values())
        types = [t["type"]["name"].title() for t in p.get("types", [])]

        # Level-Up Moves with Guaranteed "vg" Slugs
        level_moves = []
        for m in p.get("moves", []):
            move_name = m.get("move", {}).get("name", "").replace("-", " ").title()
            for vgd in m.get("version_group_details", []):
                method = vgd.get("move_learn_method", {}).get("name", "")
                if method == "level-up":
                    lvl = vgd.get("level_learned_at", 0)
                    vg_slug = vgd.get("version_group", {}).get("name", "all")
                    level_moves.append({
                        "move": move_name,
                        "level": int(lvl),
                        "vg": str(vg_slug).lower().replace("_", "-")
                    })

        level_moves.sort(key=lambda x: (x["level"], x["move"]))

        # Weaknesses / Resistances / Immunities
        multipliers = {}
        for t_entry in p.get("types", []):
            t_url = t_entry.get("type", {}).get("url")
            if t_url:
                t_req = urllib.request.Request(t_url, headers=headers)
                with urllib.request.urlopen(t_req) as resp:
                    t_raw = json.loads(resp.read().decode('utf-8'))
                    dmg = t_raw.get("damage_relations", {})
                    for d in dmg.get("double_damage_from", []):
                        multipliers[d["name"]] = multipliers.get(d["name"], 1.0) * 2.0
                    for h in dmg.get("half_damage_from", []):
                        multipliers[h["name"]] = multipliers.get(h["name"], 1.0) * 0.5
                    for n in dmg.get("no_damage_from", []):
                        multipliers[n["name"]] = multipliers.get(n["name"], 1.0) * 0.0

        weaknesses = {k.title(): v for k, v in multipliers.items() if v > 1.0}
        resistances = {k.title(): v for k, v in multipliers.items() if 0.0 < v < 1.0}
        immunities = [k.title() for k, v in multipliers.items() if v == 0.0]

        # Evolutions
        evolutions = [p.get("name", "").title()]
        try:
            evo_url = s_raw.get("evolution_chain", {}).get("url")
            if evo_url:
                e_req = urllib.request.Request(evo_url, headers=headers)
                with urllib.request.urlopen(e_req) as resp:
                    e_raw = json.loads(resp.read().decode('utf-8'))

                def parse_chain(node):
                    name = node.get("species", {}).get("name", "").title()
                    triggers = []
                    for detail in node.get("evolution_details", []):
                        trig = detail.get("trigger", {}).get("name", "").replace("-", " ")
                        if detail.get("min_level"):
                            triggers.append(f"Lv. {detail['min_level']}")
                        elif detail.get("item"):
                            triggers.append(f"Use {detail['item']['name'].replace('-', ' ').title()}")
                        elif detail.get("known_move"):
                            triggers.append(f"Knows {detail['known_move']['name'].replace('-', ' ').title()}")
                        elif detail.get("min_happiness"):
                            triggers.append(f"Happiness >= {detail['min_happiness']}")
                        else:
                            triggers.append(trig.title())

                    trig_str = f" ({', '.join(triggers)})" if triggers else ""
                    evolutions.append(f"{name}{trig_str}")
                    for next_node in node.get("evolves_to", []):
                        parse_chain(next_node)

                evolutions = []
                parse_chain(e_raw.get("chain", {}))
        except Exception:
            evolutions = [p.get("name", "").title()]

        target_data = {
            "name": p.get("name", "").title(),
            "id": p.get("id", 1),
            "slug": p.get("name", "").lower(),
            "sprite": f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{p.get('id', 1)}.png",
            "types": types,
            "bst": bst,
            "stats": stats,
            "weaknesses": weaknesses,
            "resistances": resistances,
            "immunities": immunities,
            "catch_rate": s_raw.get("capture_rate", 0),
            "base_experience": p.get("base_experience", 0) or 0,
            "growth_rate": s_raw.get("growth_rate", {}).get("name", "medium-fast").title().replace("-", " "),
            "evolutions": evolutions,
            "level_moves": level_moves
        }

        save_active_target(target_data)
        return target_data

    except Exception as e:
        print(f"[Error] Direct API fetch failed for '{pokemon_name_or_id}': {e}")
        return {}

def load_tasks_state():
    if os.path.exists(TASKS_DATA_FILE):
        try:
            with open(TASKS_DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"tasks": [], "index": 0}

def save_tasks_state(state):
    with open(TASKS_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    current_task = state["tasks"][state["index"]] if (state.get("tasks") and 0 <= state.get("index", 0) < len(state["tasks"])) else ""
    with open(CURRENT_TASK_FILE, "w", encoding="utf-8") as f:
        f.write(current_task)

def load_pokemon_counters():
    data = {}
    if os.path.exists(CATCH_TARGETS_DATA):
        with open(CATCH_TARGETS_DATA, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "," in line:
                    p = line.rsplit(",", 1)
                    try:
                        data[p[0].strip()] = int(p[1].strip())
                    except ValueError:
                        continue
    return data

def save_pokemon_counters(data):
    with open(CATCH_TARGETS_DATA, "w", encoding="utf-8") as f:
        for name, count in data.items():
            f.write(f"{name.strip()},{count}\n")

def save_active_route(data):
    with open(ACTIVE_ROUTE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)



def fetch_route_encounter_info(slug):
    try:
        # Single network call for the area only
        area = pb.location_area(slug)
    except Exception as e:
        print(f"[ROUTE ERROR] Failed to fetch area '{slug}': {e}")
        return None

    encounters_by_pokemon = []

    for p_enc in getattr(area, "pokemon_encounters", []):
        p_name = p_enc.pokemon.name
        clean_slug = p_name.lower().strip()
        details_list = []

        # Read EV instantly from local map (0 network latency)
        modern_evs = LOCAL_EV_YIELDS.get(clean_slug, {})

        for v_det in getattr(p_enc, "version_details", []):
            version_name = v_det.version.name.replace("-", " ").title()
            enc_details = getattr(v_det, "encounter_details", [])

            # If encounter details list is populated
            if enc_details:
                for enc_det in enc_details:
                    method_name = enc_det.method.name.replace("-", " ").title()
                    min_lvl = enc_det.min_level
                    max_lvl = enc_det.max_level
                    lvl_str = f"Lv. {min_lvl}" if min_lvl == max_lvl else f"Lv. {min_lvl}-{max_lvl}"
                    chance = enc_det.chance

                    details_list.append({
                        "version": version_name,
                        "method": method_name,
                        "level": lvl_str,
                        "chance": chance
                    })
            else:
                # Catch-all so Pokémon with empty sub-details are not discarded
                details_list.append({
                    "version": version_name,
                    "method": "Wild",
                    "level": "Any",
                    "chance": getattr(v_det, "max_chance", 0)
                })

        encounters_by_pokemon.append({
            "name": p_name.title(),
            "slug": clean_slug,
            "ev_yield": modern_evs,
            "details": details_list
        })

    return {
        "slug": slug,
        "name": format_area_name(slug),
        "total_species": len(encounters_by_pokemon),
        "pokemon": encounters_by_pokemon
    }

# --- PokéAPI Comprehensive Lookup ---


def render_ev_training_widget(ev_state, target, is_remote=False):
  total_evs = sum(
      v
      for k, v in ev_state.items()
      if k
      in [
          "hp",
          "attack",
          "defense",
          "special-attack",
          "special-defense",
          "speed",
      ]
  )
  base_url = "/remote" if is_remote else "/"

  stat_config = [
      ("hp", "HP", "bg-emerald-500", "text-emerald-400", "border-emerald-500"),
      ("attack", "ATK", "bg-rose-500", "text-rose-400", "border-rose-500"),
      ("defense", "DEF", "bg-blue-500", "text-blue-400", "border-blue-500"),
      (
          "special-attack",
          "SPA",
          "bg-purple-500",
          "text-purple-400",
          "border-purple-500",
      ),
      (
          "special-defense",
          "SPD",
          "bg-indigo-500",
          "text-indigo-400",
          "border-indigo-500",
      ),
      ("speed", "SPE", "bg-amber-500", "text-amber-400", "border-amber-500"),
  ]

  rows = []
  for stat_key, label, bar_color, text_color, border_color in stat_config:
    val = ev_state.get(stat_key, 0)
    pct = min(100, int((val / 252) * 100))

    rows.append(f"""
        <div class="bg-slate-950/70 border border-slate-800 rounded-xl p-2.5 space-y-1.5">
            <div class="flex items-center justify-between">
                <span class="text-xs font-black {text_color} tracking-wider">{label}</span>
                <span class="font-mono text-xs font-bold text-slate-200">{val} <span class="text-[10px] text-slate-500">/ 252</span></span>
            </div>
            <div class="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                <div class="{bar_color} h-full rounded-full transition-all duration-300" style="width: {pct}%"></div>
            </div>
            <div class="flex items-center justify-between gap-1 pt-1">
                <div class="flex gap-1">
                    <a href="{base_url}?ev_stat={stat_key}&ev_amt=-4" class="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-[10px] rounded transition">-4</a>
                    <a href="{base_url}?ev_stat={stat_key}&ev_amt=-1" class="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-[10px] rounded transition">-1</a>
                </div>
                <div class="flex gap-1">
                    <a href="{base_url}?ev_stat={stat_key}&ev_amt=1" class="px-2.5 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-100 font-bold text-[10px] rounded border border-slate-700 transition">+1</a>
                    <a href="{base_url}?ev_stat={stat_key}&ev_amt=4" class="px-2.5 py-0.5 {bar_color}/20 {text_color} border {border_color}/40 font-bold text-[10px] rounded transition">+4</a>
                    <a href="{base_url}?ev_stat={stat_key}&ev_amt=10" class="px-2 py-0.5 bg-slate-700 hover:bg-slate-600 text-white font-bold text-[10px] rounded transition">+10</a>
                </div>
            </div>
        </div>
        """)

  return f"""
    <div class="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-4 space-y-3">
        <div class="flex items-center justify-between">
            <h3 class="text-xs uppercase font-bold text-emerald-400 flex items-center gap-1.5">
                <span>💪 EV Training Tracker</span>
            </h3>
            <div class="flex items-center gap-2">
                <a href="/obs/evs" target="_blank" class="text-[11px] text-emerald-400/80 hover:underline">OBS Overlay ↗</a>
                <a href="{base_url}?ev_action=reset_all" onclick="return confirm('Reset all EV stats to 0?');" class="text-[10px] text-rose-400 hover:text-rose-300">Reset All</a>
            </div>
        </div>

        <!-- Overall 510 Cap Progress -->
        <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-3">
            <div class="flex justify-between text-xs font-bold mb-1">
                <span class="text-slate-400">Total Investment</span>
                <span class="font-mono text-emerald-400">{total_evs} <span class="text-slate-500">/ 510</span></span>
            </div>
            <div class="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden">
                <div class="bg-emerald-500 h-full rounded-full transition-all duration-300" style="width: {min(100, int((total_evs / 510) * 100))}%"></div>
            </div>
        </div>

        <!-- Individual Stat Counters -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
            {''.join(rows)}
        </div>
    </div>
    """




def handle_common_action(action, params, self=None, set_tasks_raw=None, task_nav=None):
    if action == "team_add":
        name = params.get("name", [""])[0].strip()
        if name:
            team = load_team()
            try:
                p_id = pb.pokemon(name.lower()).id
            except Exception:
                p_id = 1
            team.append({
                "name": name.title(),
                "sprite": f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{p_id}.png"
            })
            save_team(team)

    elif action == "team_remove":
        idx = int(params.get("index", [-1])[0])
        team = load_team()
        if 0 <= idx < len(team):
            team.pop(idx)
            save_team(team)

    elif action == "set_target":
        name = params.get("name", [""])[0].strip()
        if name:
            data = fetch_complete_pokemon_info(name)
            if data:
                save_active_target(data)

    elif action == "set_location":
        slug = params.get("slug", [""])[0].strip()
        if slug:
            route_data = fetch_route_encounter_info(slug)
            if route_data:
                save_active_route(route_data)

    elif action == "set_tasks" or set_tasks_raw:
        raw = set_tasks_raw if set_tasks_raw else params.get("tasks", [""])[0]
        parsed = [t.strip() for t in unquote_plus(raw).split(",") if t.strip()]
        if parsed:
            save_tasks_state({"tasks": parsed, "index": 0})
        
        if set_tasks_raw:
            t_state = load_tasks_state()
            tasks = t_state.get("tasks", [])
            total = len(tasks)
            active_name = tasks[0] if tasks else "None"
            progress_str = f"TASK 1 OF {total}" if total > 0 else "0 TASKS"
            return f"{progress_str}|{active_name}"

    elif action == "task_nav" or task_nav:
        direction = task_nav if task_nav else params.get("step", [""])[0]
        t_state = load_tasks_state()
        if t_state.get("tasks"):
            if direction == "next":
                t_state["index"] = min(t_state["index"] + 1, len(t_state["tasks"]) - 1)
            elif direction == "prev":
                t_state["index"] = max(t_state["index"] - 1, 0)
            save_tasks_state(t_state)
        
        if task_nav:
            idx = t_state.get("index", 0)
            tasks = t_state.get("tasks", [])
            total = len(tasks)
            active_name = tasks[idx] if (tasks and 0 <= idx < total) else "None"
            progress_str = f"TASK {idx + 1} OF {total}" if total > 0 else "0 TASKS"
            return f"{progress_str}|{active_name}"

    elif action == "dec_counter":
        p_name = unquote_plus(params.get("name", [""])[0])
        if p_name:
            c = load_pokemon_counters()
            c[p_name] = c.get(p_name, 0) - 1
            if c[p_name] <= 0:
                del c[p_name]
            save_pokemon_counters(c)

    elif action == "inc_counter":
        p_name = unquote_plus(params.get("name", [""])[0]).strip().title()
        if p_name:
            c = load_pokemon_counters()
            c[p_name] = c.get(p_name, 0) + 1
            save_pokemon_counters(c)

	
    elif action == "add_counters":
        raw = params.get("counter_list", [""])[0]
        raw = unquote_plus(raw)
        if raw:
            c = load_pokemon_counters() or {}
            pkmn_evos = all_pkmn_collection if all_pkmn_collection else load_all_pokemon_names() or {}
            for item in raw.split(","):
                item = item.strip()
                if not item:
                    continue
                parts = item.rsplit(" ", 1)
                if len(parts) == 2 and parts[1].strip().isdigit():
                    name = parts[0].strip().title()
                    amt = int(parts[1].strip())
                else:
                    name = item.title()
                    amt = int(pkmn_evos.get(name, 1))
                if name:
                    c[name] = int(c.get(name, 0)) + max(1, amt)
            save_pokemon_counters(c)

    elif action == "set_counters":
        raw = unquote_plus(params.get("counter_list", [""])[0])
        new_c = {}
        for item in raw.split(","):
            item = item.strip()
            if not item:
                continue
            parts = item.rsplit(" ", 1)
            if len(parts) == 2 and parts[1].isdigit():
                new_c[parts[0].strip().title()] = int(parts[1])
            else:
                new_c[item.title()] = 0
        save_pokemon_counters(new_c)

    elif action == "shiny_inc":
        hunt = load_shiny_hunt()
        hunt["count"] += 1
        save_shiny_hunt(hunt)

    elif action == "shiny_dec":
        hunt = load_shiny_hunt()
        hunt["count"] = max(0, hunt["count"] - 1)
        save_shiny_hunt(hunt)

    elif action == "shiny_reset":
        hunt = load_shiny_hunt()
        hunt["count"] = 0
        save_shiny_hunt(hunt)

    elif action == "set_shiny_target":
        target_name = unquote_plus(params.get("name", [""])[0]).strip().title()
        method = unquote_plus(params.get("method", ["Random Encounters"])[0]).strip().title()
        if target_name:
            hunt = load_shiny_hunt()
            hunt["target"] = target_name
            hunt["method"] = method if method else "Random Encounters"
            save_shiny_hunt(hunt)


    elif action == "sync_catch":
        hp = params.get("hp", ["100"])[0]
        lvl = params.get("lvl", ["50"])[0]
        status = params.get("status", ["1"])[0]
        ball = params.get("ball", ["poke"])[0]
        odds = unquote_plus(params.get("odds", ["--%"])[0])
        target_name = unquote_plus(params.get("target", ["None"])[0])

        state = {
            "hp": hp,
            "lvl": lvl,
            "status": status,
            "ball": ball,
            "odds": odds,
            "target": target_name
        }

        save_catch_state(state)

    # -------------------------------------------------------------
    # EV Tracker Actions
    # -------------------------------------------------------------
    elif action == "ev_add_target":
        ev_state = load_ev_state()
        target = load_active_target()
        
        yields = target.get("ev_yield", {}) if target else {}
        if not yields and target and target.get("name"):
            fresh = fetch_complete_pokemon_info(target.get("name"))
            if fresh and fresh.get("ev_yield"):
                target["ev_yield"] = fresh["ev_yield"]
                save_active_target(target)
                yields = target.get("ev_yield", {})

        stat_map = {
            "hp": "hp", "attack": "attack", "defense": "defense",
            "special-attack": "special-attack", "special-defense": "special-defense", "speed": "speed"
        }

        for raw_k, raw_v in yields.items():
            norm_k = stat_map.get(str(raw_k).lower().replace("_", "-"))
            try:
                val = int(raw_v)
            except (ValueError, TypeError):
                val = 0

            # Removed the `in ev_state` check so it forces creation over legacy files
            if norm_k and val > 0:
                cur = int(ev_state.get(norm_k, 0))
                total = sum(int(ev_state.get(k, 0)) for k in stat_map.values() if str(ev_state.get(k, 0)).lstrip('-').isdigit())
                add = min(val, 252 - cur, 510 - total)
                if add > 0:
                    ev_state[norm_k] = cur + add

        save_ev_state(ev_state)

    elif action == "ev_adjust":
        ev_state = load_ev_state()
        
        raw_stat = params.get("stat", "")
        if isinstance(raw_stat, list):
            raw_stat = raw_stat[0] if raw_stat else ""
        stat = str(raw_stat).strip().lower().replace("_", "-")

        raw_amt = params.get("amt", "1")
        if isinstance(raw_amt, list):
            raw_amt = raw_amt[0] if raw_amt else "1"
        try:
            amt = int(str(raw_amt).replace("+", "").strip())
        except (ValueError, TypeError):
            amt = 1

        # Removed the `in ev_state` check to force auto-creation of valid keys
        if stat in ["hp", "attack", "defense", "special-attack", "special-defense", "speed"]:
            cur = int(ev_state.get(stat, 0))
            total = sum(int(ev_state.get(k, 0)) for k in ["hp", "attack", "defense", "special-attack", "special-defense", "speed"] if str(ev_state.get(k, 0)).lstrip('-').isdigit())
            if amt > 0:
                add = min(amt, 252 - cur, 510 - total)
                ev_state[stat] = cur + max(0, add)
            else:
                ev_state[stat] = max(0, cur + amt)
            save_ev_state(ev_state)

    elif action == "ev_reset":
        ev_state = {
            "hp": 0, "attack": 0, "defense": 0,
            "special-attack": 0, "special-defense": 0, "speed": 0
        }
        save_ev_state(ev_state)

    elif action == "sync_catch":
        # Extract strictly catch-calculator parameters
        hp = params.get("hp", ["100"])[0]
        lvl = params.get("lvl", ["50"])[0]
        status = params.get("status", ["1"])[0]
        ball = params.get("ball", ["poke"])[0]
        odds = params.get("odds", ["--%"])[0]
        target_name = params.get("target", ["None"])[0]

        # Save ONLY catch data — EV state is completely omitted/untouched
        catch_state = {
            "hp": hp,
            "lvl": lvl,
            "status": status,
            "ball": ball,
            "odds": odds,
            "target": target_name
        }

        save_catch_state(catch_state)

        # Return clean 200 OK
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b'{"status": "ok"}')
        return

    elif action == "sync_exp":
        exp_state = {
            "growth_rate": unquote_plus(params.get("growth_rate", ["medium-fast"])[0]),
            "lvl_from": params.get("from", ["1"])[0],
            "lvl_to": params.get("to", ["36"])[0],
            "exp_needed": unquote_plus(params.get("exp", ["0 EXP"])[0]),
            "exp_per_kill": params.get("per_kill", ["120"])[0],
            "kills": unquote_plus(params.get("kills", ["0 kills"])[0]),
            "est_time": unquote_plus(params.get("time", ["~0m"])[0])
        }
        save_exp_state(exp_state)



# --- Router Endpoints ---
def handle_dashboard(params):
    action = params.get("action", [""])[0] if isinstance(params, dict) else ""

    task_nav = params.get("task_nav", [""])[0] if isinstance(params, dict) else ""
    set_tasks_raw = params.get("set_tasks", [""])[0] if isinstance(params, dict) else ""

    # --- Action Handling ---
    handle_common_action(action, params, set_tasks_raw, task_nav)

    # 2. Extract values for HTML template placeholders:
    t_state = load_tasks_state()
    tasks = t_state.get("tasks", [])
    idx = t_state.get("index", 0)
    total = len(tasks)

    active_task = tasks[idx] if (tasks and 0 <= idx < total) else "None"
    task_count_str = f"TASK {idx + 1} OF {total}" if total > 0 else "0 TASKS"

    # --- Load Data Collections AFTER Actions Execute ---
    pkmn_data = all_pkmn_collection if all_pkmn_collection else load_all_pokemon_names()

    # Extract just the list of names for JS
    if isinstance(pkmn_data, dict):
        js_pokemon_array = json.dumps(list(pkmn_data.keys()))
    else:
        js_pokemon_array = json.dumps(pkmn_data or [])

    team = load_team()
    target = load_active_target()
    active_route = load_active_route()
    tasks_state = load_tasks_state()
    counters = load_pokemon_counters()
    hunt = load_shiny_hunt()
    ev_state = load_ev_state()
    state = load_catch_state()
    deselected_pokemon = load_deselected_pokemon()

	
    area_list = load_all_location_areas()
    js_location_array = json.dumps(area_list)
    active_target_json = json.dumps(target if target else {})

    # --- Task Strings ---
    active_task = (
        tasks_state["tasks"][tasks_state["index"]]
        if (tasks_state.get("tasks") and 0 <= tasks_state["index"] < len(tasks_state["tasks"]))
        else "No active task"
    )
    task_count_str = (
        f"{tasks_state['index'] + 1} / {len(tasks_state['tasks'])}"
        if tasks_state.get("tasks") else "0 / 0"
    )

    # --- Party Pills ---
    team_pills = (
        "".join([
            f"""<div class="flex items-center justify-between bg-slate-700/60 border border-slate-600 rounded-lg px-3 py-2">
                <div class="flex items-center gap-2">
                    <span class="text-xs font-bold text-slate-400">#{i+1}</span>
                    <span class="font-semibold text-sm">{m['name']}</span>
                    {f'<span class="text-[10px] bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-1.5 py-0.5 rounded">Active 6</span>' if i < 6 else ''}
                </div>
                <a href="/?action=team_remove&index={i}" class="text-rose-400 hover:text-rose-300 text-xs px-2 py-1">✕</a>
            </div>"""
            for i, m in enumerate(team)
        ])
        or '<div class="text-slate-500 text-sm italic">Party is empty.</div>'
    )

    	# --- Shiny Hunting Card ---
    shiny_card = f"""
    <div class="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-4 space-y-3">
        <div class="flex items-center justify-between">
            <h3 class="text-xs uppercase font-bold text-amber-400 flex items-center gap-1.5">
                <span>✨ Shiny Hunt</span>
            </h3>
            <a href="/obs/shiny" target="_blank" class="text-[11px] text-amber-400/80 hover:underline">OBS Overlay ↗</a>
        </div>
        <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-3 text-center">
            <div class="text-xs text-slate-400 font-medium">{hunt.get('target', 'None')} <span class="text-slate-600">•</span> <span class="text-slate-400 text-[10px]">{hunt.get('method', 'Encounters')}</span></div>
            <div id="shiny-count" class="text-3xl font-black font-mono text-amber-300 my-1">{hunt.get('count', 0)}</div>
            <div class="flex gap-1.5 justify-center mt-2">
                <button type="button" onclick="const ep = window.location.pathname.includes('/remote') ? '/remote' : '/'; fetch(`${{ep}}?action=shiny_dec`).then(() => {{ const el = document.getElementById('shiny-count'); if (el) el.innerText = Math.max(0, parseInt(el.innerText || '0') - 1); }});" class="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs rounded-lg transition active:scale-95">-1</button>
                <button type="button" onclick="const ep = window.location.pathname.includes('/remote') ? '/remote' : '/'; fetch(`${{ep}}?action=shiny_inc`).then(() => {{ const el = document.getElementById('shiny-count'); if (el) el.innerText = parseInt(el.innerText || '0') + 1; }});" class="px-5 py-1 bg-amber-500 hover:bg-amber-400 text-slate-950 font-black text-xs rounded-lg transition active:scale-95">+1 Encounter</button>
                <button type="button" onclick="if (confirm('Reset counter to 0?')) {{ const ep = window.location.pathname.includes('/remote') ? '/remote' : '/'; fetch(`${{ep}}?action=shiny_reset`).then(() => {{ const el = document.getElementById('shiny-count'); if (el) el.innerText = '0'; }}); }}" class="px-2.5 py-1 bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 font-bold text-xs rounded-lg border border-rose-800/40 transition active:scale-95">Reset</button>
            </div>
        </div>
        <form action="/" method="GET" class="flex gap-1.5">
            <input type="hidden" name="action" value="set_shiny_target" />
            <input name="name" placeholder="Target (e.g. Rayquaza)" class="w-1/2 bg-slate-800 text-xs border border-slate-700 rounded-lg p-2 text-white placeholder-slate-500" />
            <input name="method" placeholder="Soft Resets, Masuda..." class="w-1/2 bg-slate-800 text-xs border border-slate-700 rounded-lg p-2 text-white placeholder-slate-500" />
            <button type="submit" class="bg-slate-800 hover:bg-slate-700 font-bold text-xs px-3 rounded-lg transition text-slate-200">Set</button>
        </form>
    </div>
    """

    # Generate EV Card using the freshly modified EV State
    ev_card_html = generate_ev_widget(ev_state, target, is_remote=False)
    
    # --- Catch Targets Pills ---
    counter_pills = (
        "".join([
            f"""<a href="/?action=dec_counter&name={name}" class="flex items-center justify-between bg-slate-700/50 hover:bg-slate-700 border border-slate-600/60 rounded-lg p-2.5 transition">
            <span class="font-bold text-slate-200 text-sm">{name}</span>
            <span class="bg-indigo-600 text-white font-mono px-2.5 py-0.5 rounded-full text-xs font-bold">{count}</span>
        </a>"""
            for name, count in counters.items()
        ])
        or '<div class="text-slate-500 text-sm italic">No catch targets configured.</div>'
    )

    active_gen_slug = target.get("selected_gen", "generation-ix")
    modern_target_evs = target.get("ev_yield", {})
    past_target_evs = target.get("past_ev_yields", {})
    target_slug = target.get("name", "").lower().strip()

    resolved_target_evs = resolve_ev_yield_for_version(
        target_slug, 
        modern_target_evs, 
        past_target_evs, 
        active_gen_slug
    )

    # 2. Format short clean labels (e.g., "1 Sp. Atk", "2 Speed")
    STAT_DISPLAY_MAP = {
        "hp": "HP",
        "attack": "Atk",
        "defense": "Def",
        "special-attack": "Sp. Atk",
        "special-defense": "Sp. Def",
        "speed": "Speed"
    }

    if resolved_target_evs:
        ev_yield_str = ", ".join([
            f"{v} {STAT_DISPLAY_MAP.get(k.lower(), k.replace('special-', 'Sp. ').title())}"
            for k, v in resolved_target_evs.items() if v > 0
        ])
    else:
        ev_yield_str = "None"

    # --- Col 1: Target Scanner View ---
    target_view = '<div class="text-slate-500 text-sm italic py-8 text-center">Search and inspect a Pokémon to load stats.</div>'
    if target:
        growth_rate_slug = target.get("growth_rate", "medium-fast").lower()
        default_sprite = target.get("sprite", "")

        evos_list = "".join([
            f'<li class="text-xs text-slate-300">{evo}</li>'
            for evo in target.get("evolutions", [])
        ])

        moves_list = "".join([
            f"""<div class="target-move-row flex justify-between text-xs py-1 border-b border-slate-700/40" data-vg="{m.get('vg', 'all')}" data-move="{m.get('move', '')}">
            <span class="text-slate-300">{m['move']} <span class="text-[10px] text-slate-500">({m.get('vg', '')})</span></span>
            <span class="font-mono text-amber-400 font-bold">Lv. {m['level']}</span>
        </div>"""
            for m in target.get("level_moves", [])
        ])

        target_view = f"""
        <div class="space-y-4">
            <div class="bg-slate-900/60 p-3 rounded-xl border border-slate-700/50 space-y-3">
                <div class="flex items-center gap-3">
                    <img id="target-sprite-img" src="{default_sprite}" class="w-16 h-16 bg-slate-800 rounded-lg p-1 border border-slate-700 object-contain image-render-pixelated" />
                    <div>
                        <div class="flex items-center gap-2">
                            <h3 class="text-xl font-black text-white">{target['name']}</h3>
                            <span class="text-slate-400 text-xs font-mono">#{target['id']}</span>
                        </div>
                        <div class="flex flex-wrap gap-1.5 mt-1" id="target-type-badges"></div>
                    </div>
                </div>

                <div class="flex items-center justify-between gap-2 pt-2 border-t border-slate-800">
                    <span class="font-bold text-slate-400 uppercase text-[10px] tracking-wider">Inspect Game:</span>
                    <select id="target-gen-select" onchange="updateTargetGenView()" class="w-48 bg-slate-950 border border-slate-700 text-amber-400 font-bold rounded px-2 py-1 text-xs focus:outline-none focus:border-amber-400">
                        <option value="modern">Modern / All</option>
                        <optgroup label="Generation I">
                            <option value="red-blue">Red / Blue</option>
                            <option value="yellow">Yellow</option>
                        </optgroup>
                        <optgroup label="Generation II">
                            <option value="gold-silver">Gold / Silver</option>
                            <option value="crystal">Crystal</option>
                        </optgroup>
                        <optgroup label="Generation III">
                            <option value="ruby-sapphire">Ruby / Sapphire</option>
                            <option value="emerald">Emerald</option>
                            <option value="firered-leafgreen">FireRed / LeafGreen</option>
                            <option value="colosseum">Colosseum / XD</option>
                        </optgroup>
                        <optgroup label="Generation IV">
                            <option value="diamond-pearl">Diamond / Pearl</option>
                            <option value="platinum">Platinum</option>
                            <option value="heartgold-soulsilver">HeartGold / SoulSilver</option>
                        </optgroup>
                        <optgroup label="Generation V">
                            <option value="black-white">Black / White</option>
                            <option value="black-2-white-2">Black 2 / White 2</option>
                        </optgroup>
                        <optgroup label="Generation VI">
                            <option value="x-y">X / Y</option>
                            <option value="omega-ruby-alpha-sapphire">Omega Ruby / Alpha Sapphire</option>
                        </optgroup>
                        <optgroup label="Generation VII">
                            <option value="sun-moon">Sun / Moon</option>
                            <option value="ultra-sun-ultra-moon">Ultra Sun / Ultra Moon</option>
                            <option value="lets-go-pikachu-lets-go-eevee">Let's Go Pikachu / Eevee</option>
                        </optgroup>
                        <optgroup label="Generation VIII">
                            <option value="sword-shield">Sword / Shield</option>
                            <option value="brilliant-diamond-and-shining-pearl">BD / SP</option>
                            <option value="legends-arceus">Legends: Arceus</option>
                        </optgroup>
                        <optgroup label="Generation IX">
                            <option value="scarlet-violet">Scarlet / Violet</option>
                        </optgroup>
                    </select>
                </div>
            </div>

            <div class="grid grid-cols-3 gap-2">
                <div class="bg-slate-900/40 p-2 rounded-lg border border-slate-800">
                    <div class="text-[10px] text-slate-400 uppercase font-semibold">Catch Rate</div>
                    <div class="text-sm font-mono font-bold text-emerald-400">{target.get('catch_rate', 0)}</div>
                </div>
                <div class="bg-slate-900/40 p-2 rounded-lg border border-slate-800">
                    <div class="text-[10px] text-slate-400 uppercase font-semibold">Base EXP</div>
                    <div class="text-sm font-mono font-bold text-sky-400">{target.get('base_experience', 0)}</div>
                </div>
		<div class="bg-slate-900/40 p-2 rounded-lg border border-slate-800">
		    <div class="text-[10px] text-slate-400 uppercase font-semibold">EV Yield</div>
		    <div id="target-ev-yield-display" class="text-xs font-mono font-bold text-amber-400 truncate">
		        {ev_yield_str}
		    </div>
		</div>
	    </div>
            </div>

            <!-- EXP Grind Calculator Row -->
            <div class="bg-slate-900/60 border border-slate-800 rounded-xl p-3 text-xs space-y-2.5">
                <input type="hidden" id="target-growth-rate" value="{growth_rate_slug}" />
                <div class="flex items-center justify-between text-slate-400 font-semibold uppercase text-[10px] tracking-wider">
                    <span>EXP Grind Calc</span>
                    <span class="text-amber-400 font-mono font-bold capitalize">{growth_rate_slug.replace('-', ' ')}</span>
                </div>
                
                <div class="flex items-center gap-2 text-slate-300 font-medium">
                    <span>Lvl</span>
                    <input id="exp-from" type="number" min="1" max="99" value="1" oninput="calcExpGap()" class="w-12 bg-slate-950 border border-slate-700 rounded px-1.5 py-1 text-center text-white font-mono font-bold focus:outline-none focus:border-amber-400" />
                    <span>to</span>
                    <input id="exp-to" type="number" min="2" max="100" value="36" oninput="calcExpGap()" class="w-12 bg-slate-950 border border-slate-700 rounded px-1.5 py-1 text-center text-white font-mono font-bold focus:outline-none focus:border-amber-400" />
                    <span class="text-slate-500 font-bold">=&gt;</span>
                    <span id="exp-output" class="font-mono font-black text-amber-400 text-xs ml-auto">46,656 EXP</span>
                </div>

                <div class="flex items-center justify-between gap-2 pt-2 border-t border-slate-800/80 text-slate-400">
                    <div class="flex items-center gap-1.5">
                        <span class="text-[11px]">Avg EXP/Kill:</span>
                        <input id="exp-per-kill" type="number" min="1" value="120" oninput="calcExpGap()" class="w-16 bg-slate-950 border border-slate-700 rounded px-1.5 py-0.5 text-center text-amber-300 font-mono font-bold text-xs focus:outline-none focus:border-amber-400" />
                    </div>
                    <div class="text-right font-mono text-[11px]">
                        <span id="grind-battles" class="text-slate-300 font-semibold">389 kills</span>
                        <span class="text-slate-600 mx-1">•</span>
                        <span id="grind-time" class="text-emerald-400 font-bold">~1h 37m</span>
                    </div>
                </div>
            </div>

	<!-- Catch Calculator Widget -->
<div class="bg-slate-900/60 border border-slate-800 rounded-xl p-3 text-xs space-y-3">
    <div class="flex items-center justify-between text-slate-400 font-semibold uppercase text-[10px] tracking-wider">
        <span>Live Catch Odds</span>
        <span id="catch-odds-display" class="text-emerald-400 font-mono font-black text-sm">{state.get('odds', '--%')}</span>
    </div>
    
    <div class="grid grid-cols-2 gap-2">
        <div class="space-y-1">
            <div class="flex justify-between text-[10px] text-slate-500 font-bold">
                <span>Target HP</span>
                <span id="catch-hp-display" class="text-amber-400 font-mono">{state.get('hp', '100')}%</span>
            </div>
            <input type="range" id="catch-hp-slider" min="1" max="100" value="{state.get('hp', '100')}" oninput="calculateCatchOdds()" onchange="calculateCatchOdds()" class="w-full accent-emerald-500" />
        </div>
        <div class="space-y-1">
            <div class="flex justify-between text-[10px] text-slate-500 font-bold">
                <span>Target Level</span>
                <span id="catch-lvl-display" class="text-indigo-400 font-mono">{state.get('lvl', '50')}</span>
            </div>
            <input type="number" id="catch-lvl-input" min="1" max="100" value="{state.get('lvl', '50')}" oninput="calculateCatchOdds()" onchange="calculateCatchOdds()" class="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded px-2 py-1 text-center font-mono font-bold focus:outline-none focus:border-indigo-400 h-6" />
        </div>
    </div>
    
    <div class="grid grid-cols-2 gap-2">
        <div>
            <div class="text-[10px] text-slate-500 font-bold mb-1">STATUS</div>
            <select id="catch-status-select" onchange="calculateCatchOdds()" class="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded px-2 py-1 focus:outline-none focus:border-amber-400">
                <option value="1" {"selected" if str(state.get('status')) == '1' else ""}>None</option>
                <option value="2.5" {"selected" if str(state.get('status')) == '2.5' else ""}>Sleep / Freeze</option>
                <option value="1.5" {"selected" if str(state.get('status')) == '1.5' else ""}>Paralyze / Poison / Burn</option>
            </select>
        </div>
        <div>
            <div class="text-[10px] text-slate-500 font-bold mb-1">BALL</div>
            <select id="catch-ball-select" onchange="calculateCatchOdds()" class="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded px-2 py-1 focus:outline-none focus:border-emerald-400">
                <option value="poke" {"selected" if state.get('ball') == 'poke' else ""}>Poké Ball</option>
                <option value="great" {"selected" if state.get('ball') == 'great' else ""}>Great Ball</option>
                <option value="ultra" {"selected" if state.get('ball') == 'ultra' else ""}>Ultra Ball</option>
                <option value="master" {"selected" if state.get('ball') == 'master' else ""}>Master Ball</option>
            </select>
        </div>
    </div>
</div>

            <!-- Base Stats Container -->
            <div>
                <div class="flex items-center justify-between mb-2">
                    <h4 class="text-[11px] uppercase font-bold text-slate-400 tracking-wider">Base Stats</h4>
                    <span id="target-bst-badge" class="text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-500/20 border border-amber-500/30 text-amber-300">BST {target['bst']}</span>
                </div>
                <div id="target-stats-container" class="space-y-1.5 bg-slate-900/40 p-3 rounded-xl border border-slate-800">
                    <!-- Populated dynamically by updateTargetGenView -->
                </div>
            </div>

            <!-- Matchups -->
            <div>
                <h4 class="text-[11px] uppercase font-bold text-slate-400 tracking-wider mb-1.5">Matchups</h4>
                <div class="space-y-2 bg-slate-900/40 p-2.5 rounded-xl border border-slate-800">
                    <div><span class="text-[10px] font-bold text-rose-400 uppercase">Weaknesses:</span> <div id="target-weakness-tags" class="flex flex-wrap gap-1 mt-1"></div></div>
                    <div><span class="text-[10px] font-bold text-emerald-400 uppercase">Resistances:</span> <div id="target-resistance-tags" class="flex flex-wrap gap-1 mt-1"></div></div>
                    <div><span class="text-[10px] font-bold text-purple-400 uppercase">Immunities:</span> <div id="target-immunity-tags" class="flex flex-wrap gap-1 mt-1"></div></div>
                </div>
            </div>

            <div>
                <h4 class="text-[11px] uppercase font-bold text-slate-400 tracking-wider mb-1.5">Evolutions</h4>
                <ul class="bg-slate-900/40 p-2.5 rounded-xl border border-slate-800 space-y-1">{evos_list}</ul>
            </div>

            <div>
                <h4 class="text-[11px] uppercase font-bold text-slate-400 tracking-wider mb-1.5">Level-Up Moves</h4>
                <div class="bg-slate-900/40 p-2.5 rounded-xl border border-slate-800 max-h-48 overflow-y-auto space-y-0.5" id="moves-container">
                    {moves_list or '<span class="text-xs text-slate-500 italic">No level-up moves listed.</span>'}
                </div>
            </div>
        </div>
        """

	# --- Col 2: Route Encounters View ---
    route_view = '<div class="text-slate-500 text-sm italic py-8 text-center">Search and select a Route to load wild encounter tables.</div>'
    if active_route:
        games = {}
        for p in active_route.get("pokemon", []):
            p_name = p.get("name", "Unknown")
            p_slug = p.get("slug", p_name.lower().replace(" ", "-"))
            modern_evs = p.get("ev_yield", {})
            past_evs = p.get("past_ev_yields", {})

            for d in p.get("details", []):
                ver = d.get("version", "Other").title()
                if ver not in games:
                    games[ver] = {}

                if p_name not in games[ver]:
                    if "resolve_ev_yield_for_version" in globals():
                        version_evs = resolve_ev_yield_for_version(p_slug, modern_evs, past_evs, ver)
                    else:
                        version_evs = modern_evs

                    games[ver][p_name] = {
                        "slug": p_slug,
                        "ev_yield": version_evs,
                        "methods": set(),
                        "levels": [],
                        "total_chance": 0,
                    }

                if d.get("method"):
                    games[ver][p_name]["methods"].add(str(d["method"]).title())
                if d.get("level"):
                    games[ver][p_name]["levels"].append(str(d["level"]))
                games[ver][p_name]["total_chance"] += d.get("chance", 0)

        game_options = ['<option value="ALL">All Versions</option>']
        game_sections = []

        STAT_SHORT_MAP = {
            "hp": "HP",
            "attack": "Atk",
            "defense": "Def",
            "special-attack": "SpA",
            "special-defense": "SpD",
            "speed": "Spe"
        }

        for ver_name, species_dict in sorted(games.items()):
            ver_slug = ver_name.lower().replace(" ", "-")
            game_options.append(
                f'<option value="{ver_slug}">{ver_name} ({len(species_dict)})</option>'
            )

            poke_rows = []
            for p_name, data in sorted(species_dict.items()):
                methods_str = ", ".join(sorted(data.get("methods", []))) or "Wild"
                levels_list = data.get("levels", [])
                levels_str = ", ".join(levels_list[:2]) if levels_list else "Any"
                total_chance = data.get("total_chance", 0)
                chance_str = f"{min(100, total_chance)}%" if total_chance > 0 else ""
                p_slug = data.get("slug", p_name.lower().replace(" ", "-"))

                # Safely evaluate EV button
                ev_btn_html = ""
                try:
                    evs = data.get("ev_yield")
                    if isinstance(evs, dict) and evs:
                        valid_evs = {k: v for k, v in evs.items() if isinstance(v, int) and v > 0}
                        if valid_evs:
                            top_stat, top_amt = max(valid_evs.items(), key=lambda item: item[1])
                            stat_clean = str(top_stat).lower()
                            stat_label = STAT_SHORT_MAP.get(stat_clean, stat_clean[:3].upper())
                            btn_text = f"+{top_amt} {stat_label}"
                            ev_link = f"/?action=ev_adjust&stat={stat_clean}&amt={top_amt}"
                            ev_btn_html = f'<a href="{ev_link}" class="text-[10px] bg-rose-600 hover:bg-rose-500 text-white font-bold px-1.5 py-0.5 rounded active:scale-95 transition whitespace-nowrap">{btn_text}</a>'
                except Exception:
                    ev_btn_html = ""

                chance_badge = f'<div class="text-[10px] font-mono font-bold text-emerald-400">{chance_str}</div>' if chance_str else ''

                # Determine if this species should be checked by default
                is_checked = "checked" if p_name not in deselected_pokemon else ""

                poke_rows.append(f"""
                    <div class="flex justify-between items-center bg-slate-950/70 border border-slate-800/80 rounded-lg p-2 hover:border-slate-700 transition">
                        <div class="flex items-center gap-2.5">
                            <input 
                                type="checkbox" 
                                class="route-poke-checkbox w-4 h-4 rounded bg-slate-900 border-slate-700 text-indigo-500 focus:ring-0 focus:ring-offset-0 cursor-pointer" 
                                data-poke-name="{p_name}" 
                                onchange="onPokemonCheckboxChange(this)"
                                {is_checked}
                            />
                            <div>
                                <div class="poke-name font-bold text-white text-xs" data-poke-name="{p_name}">{p_name}</div>
                                <div class="text-[10px] text-slate-400">{methods_str}</div>
                            </div>
                        </div>
                        <div class="flex items-center gap-2">
                            <div class="text-right">
                                <div class="text-[11px] font-mono text-amber-400 font-semibold">{levels_str}</div>
                                {chance_badge}
                            </div>
                            <div class="flex gap-1 ml-1">
                                <a href="/?action=set_target&name={p_slug}" class="text-[10px] bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold px-1.5 py-0.5 rounded active:scale-95 transition">Target</a>
                                {ev_btn_html}
                                <a href="/?action=team_add&name={p_slug}" class="text-[10px] bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-1.5 py-0.5 rounded active:scale-95 transition">+ Party</a>
                                <a href="/?action=inc_counter&name={quote_plus(p_name)}" class="text-[10px] bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-1.5 py-0.5 rounded active:scale-95 transition">+ Track</a>
                            </div>
                        </div>
                    </div>
                    """)

            game_sections.append(f"""
            <div class="game-version-card bg-slate-900/60 border border-slate-800 rounded-xl p-2.5 space-y-2" data-version="{ver_slug}">
                <div class="text-[11px] font-bold uppercase tracking-wider text-indigo-300 bg-indigo-950/50 px-2 py-1 rounded border border-indigo-900/50 flex justify-between">
                    <span>{ver_name}</span>
                    <span class="text-indigo-400 text-[10px]">{len(species_dict)} species</span>
                </div>
                <div class="space-y-1">
                    {''.join(poke_rows)}
                </div>
            </div>
            """)

        route_view = f"""
        <div class="space-y-3">
            <div class="bg-emerald-950/30 border border-emerald-500/30 rounded-xl p-3">
                <div class="text-xs uppercase font-bold text-emerald-400">Current Location</div>
                <div class="text-lg font-black text-white">{active_route['name']}</div>
                <div class="text-xs text-slate-400 mt-0.5">{active_route['total_species']} total species across all versions</div>
            </div>

            <!-- Track All Route Pokemon Button -->
            <button 
                onclick="trackAllRoutePokemon()" 
                class="w-full bg-emerald-600/20 hover:bg-emerald-600/30 active:bg-emerald-600/40 border border-emerald-500/40 hover:border-emerald-400 text-emerald-300 hover:text-emerald-200 font-bold py-2 px-3 rounded-xl text-xs flex items-center justify-center gap-2 transition-colors shadow-sm">
                <span>➕</span>
                <span>Click here to add all Pokémon on the route to tracking</span>
            </button>

            <div class="ev-warning">⚠️ Warning: On route list, only modern EVs are used</div>

            <!-- Game Version Selector Row -->
            <div class="flex items-center justify-between gap-2 bg-slate-900/80 border border-slate-800 rounded-xl px-3 py-2 text-xs">
                <span class="font-bold text-slate-400 uppercase text-[10px] tracking-wider whitespace-nowrap">Filter Game:</span>
                <select id="game-filter-select" onchange="filterGameVersion()" class="w-full bg-slate-950 border border-slate-700 text-amber-400 font-bold rounded px-2 py-1 text-xs focus:outline-none focus:border-amber-400">
                    {''.join(game_options)}
                </select>
            </div>

            <div class="space-y-3 max-h-[700px] overflow-y-auto pr-1">
                {"".join(game_sections) or '<div class="text-slate-500 text-xs italic">No encounter tables for this sub-area.</div>'}
            </div>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stream Director & Pokémon Hub</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        const activeTargetData = {active_target_json};
        const pokemonNames = {js_pokemon_array};
        const locationAreas = {js_location_array};

        {SHARED_POKEMON_JS}

        window.addEventListener('DOMContentLoaded', () => {{
            updateTargetGenView();
            if (typeof calcExpGap === 'function') calcExpGap();
        }});
    </script>
    <style>
         .ev-warning {{
  font-family: monospace;
  font-size: 11px;
  color: #fbbf24; /* soft amber warning */
  background: rgba(0, 0, 0, 0.6);
  padding: 4px 8px;
  border-radius: 4px;
  border-left: 3px solid #f59e0b;
  display: block;
}}
</style>
</head>
<body class="bg-slate-950 text-slate-100 font-sans min-h-screen">
    <!-- Header with Dual Search -->
    <header class="sticky top-0 z-50 bg-slate-900/95 backdrop-blur border-b border-slate-800 p-3">
        <div class="max-w-[1600px] mx-auto grid grid-cols-1 md:grid-cols-2 gap-3">
            <div class="relative">
                <input id="search-input" oninput="filterPokemon()" onkeyup="filterPokemon()" type="text" placeholder="Search Pokémon (e.g. gengar, lucario)..." class="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-sm text-white placeholder-slate-400 focus:outline-none focus:border-amber-400" autocomplete="off" />
                <div id="search-results" style="display: none;" class="absolute left-0 right-0 mt-1 bg-slate-800 border border-slate-700 rounded-xl shadow-2xl max-h-80 overflow-y-auto z-50"></div>
            </div>
            <div class="relative">
                <input id="location-input" oninput="filterLocations()" onkeyup="filterLocations()" type="text" placeholder="Search Route / Area (e.g. route 1, viridian)..." class="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-sm text-white placeholder-slate-400 focus:outline-none focus:border-emerald-400" autocomplete="off" />
                <div id="location-results" style="display: none;" class="absolute left-0 right-0 mt-1 bg-slate-800 border border-slate-700 rounded-xl shadow-2xl max-h-80 overflow-y-auto z-50"></div>
            </div>
        </div>
    </header>

    <!-- 3-Column Responsive Grid -->
    <main class="max-w-[1600px] mx-auto p-4 grid grid-cols-1 lg:grid-cols-12 gap-5">
        
        <!-- Col 1: Active Target Pokémon (4 Cols) -->
        <section class="lg:col-span-4 bg-slate-900/70 border border-slate-800/80 rounded-2xl p-4 shadow-xl">
            <h2 class="text-sm font-black text-white uppercase tracking-wider mb-3 flex items-center justify-between">
                <span>Active Target Scanner</span>
                <span class="text-[10px] font-mono text-slate-400">OBS Linked</span>
            </h2>
            {target_view}
        </section>

        <!-- Col 2: Route Encounters Table (4 Cols) -->
        <section class="lg:col-span-4 bg-slate-900/70 border border-slate-800/80 rounded-2xl p-4 shadow-xl">
            <h2 class="text-sm font-black text-white uppercase tracking-wider mb-3 flex items-center justify-between">
                <span>Route Encounters</span>
                <span class="text-[10px] font-mono text-emerald-400">Wild Spawns</span>
            </h2>
            {route_view}
        </section>

        <!-- Col 3: Stream Management, Queue, & Counters (4 Cols) -->
        <section class="lg:col-span-4 space-y-4">


            <!-- Catch Target Quick Taps -->
            <div class="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-4">
                <h3 class="text-xs uppercase font-bold text-slate-300 mb-2">Catch Targets (-1)</h3>
                <div class="space-y-1.5 mb-3 max-h-80 overflow-y-auto">
                    {counter_pills}
                </div>
                <form action="/" method="GET" class="space-y-1.5">
                    <input type="hidden" name="action" value="set_counters" />
                    <input name="counter_list" placeholder="caterpie 3, rattata 2" class="w-full bg-slate-800 text-xs border border-slate-700 rounded-lg p-2 text-white" />
                    <button type="submit" class="w-full bg-slate-800 hover:bg-slate-700 font-bold text-[11px] py-1.5 rounded-lg transition">Set Target Batches</button>
                </form>
            </div>
            
            {shiny_card}
            {ev_card_html}

            <!-- Party Queue -->
            <div class="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-4">
                <div class="flex items-center justify-between mb-2">
                    <h3 class="text-xs uppercase font-bold text-slate-300">Party Queue ({len(team)})</h3>
                    <a href="/obs/team" target="_blank" class="text-[11px] text-indigo-400 hover:underline">OBS View ↗</a>
                </div>
                <div class="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                    {team_pills}
                </div>
            </div>

	    <!-- Bulbapedia Walkthrough Task Loader -->
<div class="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-4 space-y-3 mb-3">
    <div class="flex justify-between items-center">
        <span class="text-[10px] uppercase font-bold text-slate-400">Bulbapedia Walkthrough</span>
        <span class="text-[10px] font-mono text-indigo-400 font-bold">TASK LOADER</span>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <!-- 1. Game Selection Dropdown -->
        <div>
            <label class="text-[10px] text-slate-400 font-bold uppercase block mb-1">1. Select Game:</label>
            <select id="walkthrough-game-select" onchange="onWalkthroughGameChange()" class="w-full bg-slate-950/80 border border-slate-800 text-slate-200 rounded-lg p-2 text-xs focus:outline-none focus:border-indigo-500">
                <option value="">-- Choose Game --</option>
                <option value="red-blue">Red / Blue</option>
                <option value="yellow">Yellow</option>
                <option value="gold-silver-crystal">Gold / Silver / Crystal</option>
                <option value="ruby-sapphire">Ruby / Sapphire</option>
                <option value="emerald">Emerald</option>
                <option value="firered-leafgreen">FireRed / LeafGreen</option>
                <option value="diamond-pearl-platinum">Diamond / Pearl / Platinum</option>
                <option value="heartgold-soulsilver">HeartGold / SoulSilver</option>
                <option value="black-white">Black / White</option>
                <option value="black-2-white-2">Black 2 / White 2</option>
                <option value="x-y">X / Y</option>
                <option value="omega-ruby-alpha-sapphire">Omega Ruby / Alpha Sapphire</option>
                <option value="sun-moon">Sun / Moon</option>
                <option value="ultra-sun-ultra-moon">Ultra Sun / Ultra Moon</option>
            </select>
        </div>

        <!-- 2. Chapter / Part Dropdown -->
        <div>
            <label class="text-[10px] text-slate-400 font-bold uppercase block mb-1">2. Select Chapter / Part:</label>
            <select id="walkthrough-part-select" onchange="loadSelectedPartTasks()" disabled class="w-full bg-slate-950/80 border border-slate-800 text-slate-200 rounded-lg p-2 text-xs focus:outline-none focus:border-emerald-500 disabled:opacity-40">
                <option value="">-- Select Game First --</option>
            </select>
        </div>
    </div>
</div>

<!-- Task Queue Manager -->
<div class="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-4">
    <div class="flex justify-between items-center mb-1">
        <span id="task-progress-display" class="text-[10px] uppercase font-bold text-slate-400">{task_count_str}</span>
        <span class="text-[10px] font-mono text-emerald-400 font-bold">CURRENT TASK</span>
    </div>
    <div id="task-name-display" class="text-sm font-bold text-white mb-3 bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">{active_task}</div>
    <div class="flex gap-2 mb-3">
        <button type="button" onclick="navigateTask('prev')" class="flex-1 py-1.5 bg-slate-800 hover:bg-slate-700 text-center text-xs font-bold rounded-lg transition active:scale-95 text-slate-200">◀ Prev</button>
        <button type="button" onclick="navigateTask('next')" class="flex-1 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-center text-xs font-bold rounded-lg transition active:scale-95 text-white">Next ▶</button>
    </div>
    <form action="/" method="GET" class="space-y-1.5">
        <input type="hidden" name="action" value="set_tasks" />
        <input name="tasks" placeholder="Task 1, Task 2, Task 3..." class="w-full bg-slate-800 text-xs border border-slate-700 rounded-lg p-2 text-white" />
        <button type="submit" class="w-full bg-slate-800 hover:bg-slate-700 font-bold text-[11px] py-1.5 rounded-lg transition">Update Tasks</button>
    </form>
</div>

            <!-- Video Message -->
            <div class="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-4">
                <h3 class="text-xs uppercase font-bold text-slate-300 mb-2">Video Message Note</h3>
                <form action="/videomessage" method="GET" class="space-y-1.5">
                    <textarea name="notes" placeholder="Update video note..." class="w-full bg-slate-800 text-xs border border-slate-700 rounded-lg p-2 text-white h-16"></textarea>
                    <button type="submit" class="w-full bg-indigo-600 hover:bg-indigo-500 font-bold text-[11px] py-1.5 rounded-lg transition">Overwrite Note</button>
                </form>
            </div>

        </section>
    </main>
</body>
</html>"""
    return html, ("Content-Type", "text/html")#




# --- OBS Views ---


def load_pokemon():
    data = {}
    if os.path.exists(CATCH_TARGETS_DATA):
        with open(CATCH_TARGETS_DATA, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "," in line:
                    parts = line.rsplit(",", 1)
                    try:
                        data[parts[0].strip()] = int(parts[1].strip())
                    except ValueError:
                        continue
    return data



def handle_pokemon_remote(params):
    action = params.get("action", [""])[0] if isinstance(params, dict) else ""

    task_nav = params.get("task_nav", [""])[0] if isinstance(params, dict) else ""
    set_tasks_raw = params.get("set_tasks", [""])[0] if isinstance(params, dict) else ""

    
    handle_common_action(action, params, set_tasks_raw, task_nav)

    # --- Load Session State AFTER Actions Execute ---
    tasks_state = load_tasks_state()
    counters = load_pokemon_counters()
    hunt = load_shiny_hunt()
    target = load_active_target()
    ev_state = load_ev_state()
    state = load_catch_state()
    route_data = load_active_route()

    area_list = load_all_location_areas()
    js_location_array = json.dumps(area_list)

    task_progress = f"Task {tasks_state['index'] + 1} of {len(tasks_state['tasks'])}" if tasks_state.get("tasks") else "No Tasks Set"
    active_task_name = (
        tasks_state["tasks"][tasks_state["index"]]
        if (tasks_state.get("tasks") and 0 <= tasks_state["index"] < len(tasks_state["tasks"]))
        else "All clear / None active"
    )

    buttons_html = "".join([
        f"""<div style="display: flex; justify-content: space-between; align-items: center; background: #1f2937; color: #fff; padding: 12px 16px; border-radius: 8px; margin-bottom: 8px; font-weight: bold; border: 1px solid #374151;">
            <div>
                <div style="font-size: 1.05rem;">{name}</div>
                <div style="font-size: 0.75rem; color: #9ca3af; font-family: monospace;">{count} remaining</div>
            </div>
            <div style="display: flex; gap: 8px; align-items: center;">
                <a href="/remote?action=dec_counter&name={quote_plus(name)}" style="display: flex; align-items: center; justify-content: center; width: 34px; height: 34px; background: #374151; color: #fff; text-decoration: none; border-radius: 6px; font-size: 1.1rem; border: 1px solid #4b5563;">-</a>
                <span style="font-family: monospace; font-size: 1.1rem; min-width: 24px; text-align: center; color: #34d399;">{count}</span>
                <a href="/remote?action=inc_counter&name={quote_plus(name)}" style="display: flex; align-items: center; justify-content: center; width: 34px; height: 34px; background: #059669; color: #fff; text-decoration: none; border-radius: 6px; font-size: 1.1rem;">+</a>
            </div>
        </div>"""
        for name, count in counters.items()
    ]) or '<div style="color: #6b7280; font-style: italic; margin-bottom: 16px;">No catch targets left!</div>'

    ev_card_html = generate_ev_widget(ev_state, target, is_remote=True)

    mobile_target_card = ""
    if target:
        types_badges = "".join([
            f'<span class="text-[10px] font-bold px-2 py-0.5 rounded bg-indigo-500/20 border border-indigo-500/30 text-indigo-300">{t}</span>'
            for t in target.get("types", [])
        ])
        weakness_badges = "".join([
            f'<span class="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30">{k.title()} {v}x</span>'
            for k, v in target.get("weaknesses", {}).items()
        ]) or '<span class="text-xs text-slate-500">None</span>'

        moves_preview = "".join([
            f"""<div class="flex justify-between text-xs py-0.5 border-b border-slate-800 last:border-none">
                <span class="text-slate-300">{m['move']}</span>
                <span class="font-mono text-amber-400 font-bold">Lv. {m['level']}</span>
            </div>"""
            for m in target.get("level_moves", [])[:5]
        ])

        mobile_target_card = f"""
        <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-lg space-y-3">
            <div class="flex items-center justify-between">
                <span class="text-[10px] uppercase font-bold tracking-wider text-amber-400">Active Target</span>
                <span class="text-xs font-mono text-slate-400">#{target.get('id', 0)}</span>
            </div>

            <div class="flex items-center gap-3">
                <img src="{target.get('sprite', '')}" class="w-14 h-14 bg-slate-950 rounded-xl p-1 border border-slate-800 object-contain" />
                <div class="flex-1">
                    <h3 class="text-lg font-black text-white leading-tight">{target.get('name', 'Unknown')}</h3>
                    <div class="flex flex-wrap gap-1 mt-1">
                        {types_badges}
                    </div>
                </div>
                <div class="text-right bg-slate-950/80 px-2.5 py-1.5 rounded-lg border border-slate-800">
                    <div class="text-[9px] uppercase font-bold text-slate-400">Catch Rate</div>
                    <div class="text-sm font-black font-mono text-emerald-400">{target.get('catch_rate', 0)}</div>
                </div>
            </div>

            <div class="bg-slate-950/60 rounded-xl p-2.5 space-y-1 border border-slate-800/60">
                <div class="text-[10px] font-bold uppercase text-rose-400">Weaknesses:</div>
                <div class="flex flex-wrap gap-1">
                    {weakness_badges}
                </div>
            </div>

            <details class="group bg-slate-950/40 rounded-xl border border-slate-800/60">
                <summary class="flex justify-between items-center p-2.5 cursor-pointer text-xs font-bold text-slate-300 select-none">
                    <span>Level-Up Moves ({len(target.get('level_moves', []))})</span>
                    <span class="text-slate-500 group-open:rotate-180 transition-transform">▼</span>
                </summary>
                <div class="p-2.5 pt-0 max-h-40 overflow-y-auto space-y-1">
                    {moves_preview or '<span class="text-xs text-slate-500 italic">No moves recorded.</span>'}
                </div>
            </details>
        </div>
        """

    route_section_html = '<div class="text-slate-500 text-xs italic py-4 text-center">Search and select a Route to load wild encounter tables.</div>'
    if active_route:
        games = {}
        for p in active_route.get("pokemon", []):
            p_name = p.get("name", "Unknown")
            p_slug = p.get("slug", p_name.lower())
            modern_evs = p.get("ev_yield", {})
            past_evs = p.get("past_ev_yields", {})

            for d in p.get("details", []):
                ver = d.get("version", "Other").title()
                if ver not in games:
                    games[ver] = {}

                if p_name not in games[ver]:
                    version_evs = resolve_ev_yield_for_version(p_slug, modern_evs, past_evs, ver)
                    games[ver][p_name] = {
                        "slug": p_slug,
                        "ev_yield": version_evs,
                        "methods": set(),
                        "levels": [],
                        "total_chance": 0,
                    }

                if d.get("method"):
                    games[ver][p_name]["methods"].add(d["method"].title())
                if d.get("level"):
                    games[ver][p_name]["levels"].append(str(d["level"]))
                games[ver][p_name]["total_chance"] += d.get("chance", 0)

        # Selected version dropdown
        game_options = ['<option value="ALL">All Versions</option>']
        game_sections = []

        STAT_SHORT_MAP = {
            "hp": "HP",
            "attack": "Atk",
            "defense": "Def",
            "special-attack": "SpA",
            "special-defense": "SpD",
            "speed": "Spe"
        }

        for ver_name, species_dict in sorted(games.items()):
            ver_slug = ver_name.lower().replace(" ", "-")
            game_options.append(
                f'<option value="{ver_slug}">{ver_name} ({len(species_dict)})</option>'
            )

            poke_rows = []
            for p_name, data in sorted(species_dict.items()):
                methods_str = ", ".join(sorted(data.get("methods", []))) or "Wild"
                levels_list = data.get("levels", [])
                levels_str = ", ".join(levels_list[:2]) if levels_list else "Any"
                total_chance = data.get("total_chance", 0)
                chance_str = f"{min(100, total_chance)}%" if total_chance > 0 else ""
                p_slug = data.get("slug", p_name.lower().replace(" ", "-"))

                # Safely evaluate EV button
                ev_btn_html = ""
                try:
                    evs = data.get("ev_yield")
                    if isinstance(evs, dict) and evs:
                        valid_evs = {k: v for k, v in evs.items() if isinstance(v, int) and v > 0}
                        if valid_evs:
                            top_stat, top_amt = max(valid_evs.items(), key=lambda item: item[1])
                            stat_clean = str(top_stat).lower()
                            stat_label = STAT_SHORT_MAP.get(stat_clean, stat_clean[:3].upper())
                            btn_text = f"+{top_amt} {stat_label}"
                            ev_link = f"/remote?action=ev_adjust&stat={stat_clean}&amt={top_amt}"
                            ev_btn_html = f'<a href="{ev_link}" class="text-[10px] bg-rose-600 hover:bg-rose-500 text-white font-bold px-1.5 py-0.5 rounded active:scale-95 transition whitespace-nowrap">{btn_text}</a>'
                except Exception:
                    ev_btn_html = ""

                chance_badge = f'<div class="text-[10px] font-mono font-bold text-emerald-400">{chance_str}</div>' if chance_str else ''

                poke_rows.append(f"""
                <div class="flex justify-between items-center bg-slate-950/70 border border-slate-800/80 rounded-lg p-2 hover:border-slate-700 transition">
                    <div>
                        <div class="font-bold text-white text-xs">{p_name}</div>
                        <div class="text-[10px] text-slate-400">{methods_str}</div>
                    </div>
                    <div class="flex items-center gap-2">
                        <div class="text-right">
                            <div class="text-[11px] font-mono text-amber-400 font-semibold">{levels_str}</div>
                            {chance_badge}
                        </div>
                        <div class="flex gap-1 ml-1">
                            <a href="/remote?action=set_target&name={p_slug}" class="text-[10px] bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold px-1.5 py-0.5 rounded active:scale-95 transition">Target</a>
                            {ev_btn_html}
                            <a href="/remote?action=team_add&name={p_slug}" class="text-[10px] bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-1.5 py-0.5 rounded active:scale-95 transition">+ Party</a>
                            <a href="/remote?action=inc_counter&name={quote_plus(p_name)}" class="text-[10px] bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-1.5 py-0.5 rounded active:scale-95 transition">+ Track</a>
                        </div>
                    </div>
                </div>
                """)

            game_sections.append(f"""
            <div class="game-version-card bg-slate-900/60 border border-slate-800 rounded-xl p-2.5 space-y-2" data-version="{ver_slug}">
                <div class="text-[11px] font-bold uppercase tracking-wider text-indigo-300 bg-indigo-950/50 px-2 py-1 rounded border border-indigo-900/50 flex justify-between">
                    <span>{ver_name}</span>
                    <span class="text-indigo-400 text-[10px]">{len(species_dict)} species</span>
                </div>
                <div class="space-y-1">
                    {''.join(poke_rows)}
                </div>
            </div>
            """)

        select_html = f"""
        <div class="mb-3 space-y-1.5">
            <div class="flex justify-between items-center">
                <label class="text-[11px] text-slate-400 font-semibold block">Filter by Version:</label>
                <span class="text-[10px] text-amber-400/90 italic font-mono">⚠️ Route list uses modern EVs</span>
            </div>
            <select id="game-filter-select" onchange="filterGameVersion()" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-white focus:outline-none focus:border-indigo-500">
                {''.join(game_options)}
            </select>
        </div>
        """

        route_section_html = f"""
        <div class="space-y-3">
            <div class="relative">
                <input type="text" id="location-input" oninput="filterLocations()" placeholder="Search routes or locations..." class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500" />
                <div id="location-results" class="absolute z-20 left-0 right-0 top-full mt-1 bg-slate-900 border border-slate-700 rounded-lg shadow-xl overflow-hidden hidden max-h-60 overflow-y-auto"></div>
            </div>
            {select_html}
            <div id="route-game-sections" class="space-y-2">
                {''.join(game_sections)}
            </div>
        </div>
        """

    # Format JSON arrays for instant client-side dropdown filtering
    locations_json = json.dumps([
        {
            "name": (loc.get("name") or loc.get("slug", "")).replace("-", " ").title() if isinstance(loc, dict) else str(loc).replace("-", " ").title(),
            "slug": (loc.get("slug") or loc.get("name", "")) if isinstance(loc, dict) else str(loc)
        }
        for loc in all_location_areas
    ])

    pkmn_json = json.dumps([
        {
            "name": (p.get("name") or p.get("slug", "")).replace("-", " ").title() if isinstance(p, dict) else str(p).replace("-", " ").title(),
            "slug": (p.get("slug") or p.get("name", "")) if isinstance(p, dict) else str(p).lower().replace(" ", "-")
        }
        for p in all_pkmn_collection
    ])

    active_target_json = json.dumps(target if target else {})

    return (
        f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>Catch Tracker Remote</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #121212; color: #e0e0e0; padding: 16px; margin: 0; -webkit-tap-highlight-color: transparent; }}
        h3 {{ margin-top: 0; }}
        textarea, input[type="text"] {{ width: 100%; height: 44px; box-sizing: border-box; background: #222; color: #fff; border: 1px solid #444; border-radius: 6px; padding: 8px 12px; margin-bottom: 8px; font-family: inherit; font-size: 1rem; }}
        textarea {{ height: 60px; }}
        button {{ width: 100%; padding: 12px; background: #10b981; color: #fff; border: none; border-radius: 6px; font-weight: bold; font-size: 1rem; cursor: pointer; }}
        button:active {{ opacity: 0.9; transform: scale(0.99); }}
        .card {{ background: #1e1e1e; padding: 14px; border-radius: 10px; margin-top: 20px; }}
        .nav-btn {{ flex: 1; padding: 16px; font-size: 1.1rem; font-weight: bold; border-radius: 8px; text-decoration: none; text-align: center; color: #fff; background: #374151; }}
        .nav-btn:active {{ background: #4b5563; }}
        .shiny-btn {{ display: block; width: 100%; padding: 22px; font-size: 1.4rem; font-weight: 900; text-align: center; color: #0f172a; background: #f59e0b; border-radius: 12px; text-decoration: none; box-sizing: border-box; box-shadow: 0 4px 14px rgba(245, 158, 11, 0.35); }}
        .shiny-btn:active {{ background: #d97706; transform: scale(0.98); }}
    </style>
    <script>
        const activeTargetData = {active_target_json};
	const pokemonNames = {pkmn_json};
        const locationAreas = {locations_json};


        {SHARED_POKEMON_JS}

            </script>
</head>
<body class="p-3 md:p-6 pb-36 bg-[#121212] text-[#e0e0e0] font-sans antialiased min-h-screen selection:bg-indigo-500 selection:text-white" style="padding-bottom: calc(9rem + env(safe-area-inset-bottom));">

    <!-- Responsive Grid Wrapper (1 col portrait, 2 cols landscape/desktop) -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-7xl mx-auto items-start [media(orientation:landscape)]:grid-cols-2">
        
        <!-- COLUMN 1: Target Search -> Target Card -> Counters -> Shiny -> EV -> Catch Odds -->
        <div class="space-y-4 flex flex-col">

            <!-- Search 1: Target Pokémon Search -->
            <div class="card" style="border: 1px solid #f59e0b; margin-top: 0;">
                <h3 style="color: #fbbf24; margin-bottom: 8px;">Search Pokémon Target</h3>
                <input 
                    type="text" 
                    id="pkmn-search-input" 
                    oninput="liveFilterPokemon()" 
                    placeholder="Search Pokémon (e.g. gengar, pikachu)..." 
                    autocomplete="off" 
                    class="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-amber-400"
                />
                <div id="pkmn-live-results" class="bg-slate-900/95 border border-amber-500/40 rounded-xl p-3 space-y-2 mt-2" style="display: none;">
                    <div class="flex justify-between items-center text-[10px] font-bold text-amber-300 uppercase tracking-wider">
                        <span id="pkmn-results-count">0 matching Pokémon</span>
                        <button type="button" onclick="document.getElementById('pkmn-live-results').style.display='none';" class="text-slate-500 hover:text-white text-xs">✕</button>
                    </div>
                    <div id="pkmn-results-list" class="space-y-1.5 max-h-56 overflow-y-auto"></div>
                </div>
            </div>
       
            {mobile_target_card}

            <!-- Active Counters -->
            <div class="card" style="margin-top: 0;">
                <h3 style="margin-bottom: 8px;">Active Tracking Counters</h3>
                <div>
                    {buttons_html}
                </div>
            </div>

            <!-- Shiny Hunt Section -->
            <div class="card" style="border: 2px solid #f59e0b; background: #18150f; margin-top: 0;">
                <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px;">
                    <div style="font-size: 0.85rem; color: #fbbf24; text-transform: uppercase; font-weight: bold;">✨ {hunt.get('target', 'None')}</div>
                    <div style="font-size: 0.75rem; color: #92400e;">{hunt.get('method', 'Encounters')}</div>
                </div>
                <div style="font-size: 2.5rem; font-weight: 900; font-family: monospace; color: #fef3c7; text-align: center; margin: 4px 0 14px 0;">{hunt.get('count', 0)}</div>
                <a href="/remote?shiny_action=inc" class="shiny-btn">+1 SEEN / RESET</a>
                <div style="display: flex; gap: 8px; margin-top: 10px;">
                    <a href="/remote?shiny_action=dec" class="nav-btn" style="padding: 10px; font-size: 0.9rem; background: #292524;">-1 Undo</a>
                    <a href="/remote?shiny_action=reset" onclick="return confirm('Reset shiny hunt counter?');" class="nav-btn" style="padding: 10px; font-size: 0.9rem; background: #450a0a; color: #fca5a5;">Reset 0</a>
                </div>
            </div>

            {ev_card_html}

            <!-- Catch Calculator Widget -->
            <div class="bg-slate-900/60 border border-slate-800 rounded-xl p-3 text-xs space-y-3">
                <div class="flex items-center justify-between text-slate-400 font-semibold uppercase text-[10px] tracking-wider">
                    <span>Live Catch Odds</span>
                    <span id="catch-odds-display" class="text-emerald-400 font-mono font-black text-sm">{state.get('odds', '--%')}</span>
                </div>
                
                <div class="space-y-1">
                    <div class="flex justify-between text-[10px] text-slate-500 font-bold">
                        <span>Target HP</span>
                        <span id="catch-hp-display" class="text-amber-400 font-mono">{state.get('hp', '100')}%</span>
                    </div>
                    <input type="range" id="catch-hp-slider" min="1" max="100" value="{state.get('hp', '100')}" oninput="calculateCatchOdds()" onchange="calculateCatchOdds()" class="w-full accent-emerald-500" />
                </div>

                <div class="flex justify-between items-center bg-slate-950/60 border border-slate-800/80 rounded-lg p-2">
                    <span class="text-[10px] text-slate-400 font-bold uppercase">Target Lvl</span>
                    <input type="number" id="catch-lvl-input" min="1" max="100" value="{state.get('lvl', '50')}" oninput="calculateCatchOdds()" onchange="calculateCatchOdds()" class="w-16 bg-slate-900 border border-slate-700 text-white rounded px-2 py-0.5 text-center font-mono font-bold text-xs focus:outline-none focus:border-indigo-400" />
                </div>
                
                <div class="grid grid-cols-2 gap-2">
                    <div>
                        <div class="text-[10px] text-slate-500 font-bold mb-1">STATUS</div>
                        <select id="catch-status-select" onchange="calculateCatchOdds()" class="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded px-2 py-1 focus:outline-none focus:border-amber-400">
                            <option value="1" {"selected" if state.get('status') == '1' else ""}>None</option>
                            <option value="2.5" {"selected" if state.get('status') == '2.5' else ""}>Sleep / Freeze</option>
                            <option value="1.5" {"selected" if state.get('status') == '1.5' else ""}>Paralyze / Poison / Burn</option>
                        </select>
                    </div>
                    <div>
                        <div class="text-[10px] text-slate-500 font-bold mb-1">BALL</div>
                        <select id="catch-ball-select" onchange="calculateCatchOdds()" class="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded px-2 py-1 focus:outline-none focus:border-emerald-400">
                            <option value="poke" {"selected" if state.get('ball') == 'poke' else ""}>Poké Ball</option>
                            <option value="great" {"selected" if state.get('ball') == 'great' else ""}>Great Ball</option>
                            <option value="ultra" {"selected" if state.get('ball') == 'ultra' else ""}>Ultra Ball</option>
                            <option value="master" {"selected" if state.get('ball') == 'master' else ""}>Master Ball</option>
                        </select>
                    </div>
                </div>
            </div>
        </div>

        <!-- COLUMN 2: Route Search -> Route Info -> Tasks -> Forms -->
        <div class="space-y-4 flex flex-col">

		<!-- Search 2: Route Location Search -->
		<div class="card" style="border: 1px solid #6366f1; margin-top: 0;">
		    <h3 style="color: #a5b4fc; margin-bottom: 8px;">Search Route / Location</h3>
		    <input 
		        type="text" 
		        id="location-input" 
		        oninput="filterLocations()" 
		        placeholder="Search route (e.g. kanto-route-1, viridian)..." 
		        autocomplete="off" 
		        class="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-indigo-400"
		    />
		    <div id="location-results" class="bg-slate-900/95 border border-indigo-500/40 rounded-xl p-3 space-y-2 mt-2" style="display: none;"></div>
		</div>
            
            <!-- Route Encounters Table -->
            <div style="margin-top: 0;">
                {route_section_html}
            </div>

            <!-- Stream Tasks -->
            <div class="card" style="border: 2px solid #3b82f6; margin-top: 0;">
	        <div id="task-progress-display" style="font-size: 0.85rem; color: #9ca3af; text-transform: uppercase; font-weight: bold; margin-bottom: 4px;">{task_progress}</div>
	        <div id="task-name-display" style="font-size: 1.4rem; font-weight: bold; color: #fff; margin-bottom: 14px;">{active_task_name}</div>
	        <div style="display: flex; gap: 10px;">
	            <button type="button" onclick="navigateTask('prev')" class="nav-btn" style="cursor: pointer;">◀ Back</button>
	            <button type="button" onclick="navigateTask('next')" class="nav-btn" style="background: #2563eb; cursor: pointer;">Forward ▶</button>
	        </div>
	    </div>

            <!-- Task Management -->
			    <div class="card space-y-2.5" style="border: 1px solid #6366f1;">
    <div class="flex justify-between items-center">
        <h3 style="color: #a5b4fc;" class="text-xs font-bold uppercase tracking-wider">Bulbapedia Walkthrough Task Loader</h3>
        <span class="text-[10px] text-indigo-400 font-mono">?action=set_tasks</span>
    </div>
    
    <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
        <!-- 1. Game Selection Dropdown -->
        <div>
            <label class="text-[11px] text-slate-400 font-semibold mb-1 block">1. Select Game:</label>
            <select id="walkthrough-game-select" onchange="onWalkthroughGameChange()" class="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg p-2 text-xs focus:outline-none focus:border-indigo-400">
                <option value="">-- Choose Game --</option>
                <option value="red-blue">Red / Blue</option>
                <option value="yellow">Yellow</option>
                <option value="gold-silver-crystal">Gold / Silver / Crystal</option>
                <option value="ruby-sapphire">Ruby / Sapphire</option>
                <option value="emerald">Emerald</option>
                <option value="firered-leafgreen">FireRed / LeafGreen</option>
                <option value="diamond-pearl-platinum">Diamond / Pearl / Platinum</option>
                <option value="heartgold-soulsilver">HeartGold / SoulSilver</option>
                <option value="black-white">Black / White</option>
                <option value="black-2-white-2">Black 2 / White 2</option>
                <option value="x-y">X / Y</option>
                <option value="omega-ruby-alpha-sapphire">Omega Ruby / Alpha Sapphire</option>
                <option value="sun-moon">Sun / Moon</option>
                <option value="ultra-sun-ultra-moon">Ultra Sun / Ultra Moon</option>
            </select>
        </div>

        <!-- 2. Chapter / Part Dropdown -->
        <div>
            <label class="text-[11px] text-slate-400 font-semibold mb-1 block">2. Select Chapter / Part:</label>
            <select id="walkthrough-part-select" onchange="loadSelectedPartTasks()" disabled class="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg p-2 text-xs focus:outline-none focus:border-emerald-400 disabled:opacity-50">
                <option value="">-- Select Game First --</option>
            </select>
        </div>
    </div>
</div>
            <div class="card" style="margin-top: 0;">
                <h3>Set Task Queue</h3>
                <form action="/remote" method="GET">
                    <textarea name="set_tasks" placeholder="Task one, Task two, Task three"></textarea>
                    <button type="submit" style="background: #0ea5e9;">Load Tasks</button>
                </form>
            </div>


            <!-- Bulk Counters -->
            <div class="card" style="margin-top: 0;">
                <h3>Set / Reset Catch Targets</h3>
                <form action="/remote" method="GET">
                    <input type="hidden" name="action" value="set_counters" />
                    <textarea name="counter_list" placeholder="caterpie 3, rattata 2, pikachu 1"></textarea>
                    <button type="submit">Save Targets</button>
                </form>
            </div>

            <!-- Video Message -->
            <div class="card" style="margin-top: 0;">
                <h3>Video Message</h3>
                <form action="/videomessage" method="GET">
                    <textarea name="notes" placeholder="Enter stream note..."></textarea>
                    <button type="submit" style="background: #6366f1;">Update Video Message</button>
                </form>
            </div>
        </div>

    </div>

    <!-- Floating Quick Reload Button -->
    <button onclick="window.location.href=window.location.pathname;" class="fixed bottom-6 right-6 z-[99] bg-slate-800 hover:bg-slate-700 text-slate-200 p-3.5 rounded-full shadow-2xl border border-slate-600 transition-all active:scale-90 flex items-center justify-center cursor-pointer" aria-label="Refresh Page">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
    </button>
</body>
</html>""",
        ("Content-Type", "text/html"),
    )







ROUTES = {
    "/": handle_dashboard,
    "/remote": handle_pokemon_remote,
    "/obs": handle_obs_hub,
    "/obs/target": handle_obs_target_overlay,
    "/obs/team": handle_obs_team_overlay,
    "/obs/tocatch": handle_pokemon_stream,
    "/obs/shiny": handle_obs_shiny,
    "/obs/evs": handle_obs_evs,
    "/obs/catchrate": handle_obs_catch_rate,
    "/obs/exptracker" : handle_obs_exp,
}