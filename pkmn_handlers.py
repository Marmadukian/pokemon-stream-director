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



# In-memory session cache for shared evolution chains

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


def generate_tools_dropdown_widget():
    """Returns an HTML widget with actual RNG, seed-dependent, and mechanic-specific

    calculators used by challenge runners and dex collectors.
    """
    tools = [
        # --- Route & Encounter Calculators ---
        {
            "name": "Gen 3 Feebas Tile Seed Finder",
            "url": "https://mkwrs.com/feebas/",
        },
        {
            "name": "Gen 4 Route 222 / Great Marsh Seed Calc",
            "url": "https://www.smogon.com/ingame/rng/dpp_rng_part4",
        },
        {
            "name": "Gen 2 / HGSS Headbutt Tree Calculator",
            "url": "https://pokerng.forumcommunity.net/?t=56453272",
        },
        {
            "name": "Gen 4 Honey Tree Predictor (Trainer ID)",
            "url": "https://www.dragonflycave.com/sinnoh/honey-trees",
        },
        # --- Math, Mechanics & Rates ---
        {
            "name": "Cave of Dragonflies Comprehensive Catch Calc",
            "url": "https://www.dragonflycave.com/calculators/gen-iii-iv-catch-rate",
        },
        {
            "name": "Gen 1–9 Wild Encounter Odds & Slots (Glitch City)",
            "url": "https://glitchcity.wiki/wiki/Wild_Pok%C3%A9mon_data",
        },
        {
            "name": "Exp / Growth Curve Exact Calc (Dragonfly Cave)",
            "url": "https://www.dragonflycave.com/mechanics/experience",
        },
        {
            "name": "Gen 3/4 Safari Zone Catch/Flee Rate Calculator",
            "url": "https://www.dragonflycave.com/mechanics/safari-zone",
        },
        # --- Collection, Tracking & RNG ---
        {
            "name": "PokéOS Origin Mark & Living Dex Tracker",
            "url": "https://pokeos.com/",
        },
        {
            "name": "Pokéarth (Exact Serebii Wild Tables by Map)",
            "url": "https://www.serebii.net/pokearth/",
        },
        {
            "name": "Smogon In-Game RNG Mechanics Compendium",
            "url": "https://www.smogon.com/ingame/rng/",
        },
    ]

    options_html = "".join(
        [f'<option value="{t["url"]}">{t["name"]}</option>' for t in tools]
    )

    html = f"""
    <div class="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-3">
        <div class="flex items-center justify-between gap-2">
            <span class="font-bold text-amber-400 uppercase text-[10px] tracking-wider whitespace-nowrap">🛠️ Runner Tools:</span>
            <select 
                onchange="if(this.value){{ window.open(this.value, '_blank'); this.selectedIndex = 0; }}" 
                class="w-full bg-slate-950 border border-slate-700 text-amber-300 font-bold rounded-lg px-2.5 py-1.5 text-xs focus:outline-none focus:border-amber-400 cursor-pointer">
                <option value="">-- Seed & Tile Calculators ↗ --</option>
                {options_html}
            </select>
        </div>
    </div>
    """
    return html


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
                req_headers = headers if headers else {"User-Agent": "PokeApp/1.0"}
                e_req = urllib.request.Request(evo_url, headers=req_headers)
                with urllib.request.urlopen(e_req) as resp:
                    e_raw = json.loads(resp.read().decode('utf-8'))

                chain_list = []

                def parse_chain(node):
                    name = node.get("species", {}).get("name", "").title()
                    triggers = []

                    for detail in node.get("evolution_details", []):
                        min_lvl = detail.get("min_level")
                        item = detail.get("item")
                        move = detail.get("known_move")
                        happy = detail.get("min_happiness")
                        trig_raw = detail.get("trigger", {})
                        trig_name = trig_raw.get("name", "").replace("-", " ") if isinstance(trig_raw, dict) else ""

                        if min_lvl:
                            triggers.append(f"Lv. {min_lvl}")
                        elif item and isinstance(item, dict):
                            triggers.append(f"Use {item.get('name', '').replace('-', ' ').title()}")
                        elif move and isinstance(move, dict):
                            triggers.append(f"Knows {move.get('name', '').replace('-', ' ').title()}")
                        elif happy:
                            triggers.append(f"Happiness >= {happy}")
                        elif trig_name:
                            triggers.append(trig_name.title())

                    trig_str = f" ({', '.join(triggers)})" if triggers else ""
                    chain_list.append(f"{name}{trig_str}")

                    for next_node in node.get("evolves_to", []):
                        parse_chain(next_node)

                parse_chain(e_raw.get("chain", {}))
                if chain_list:
                    evolutions = chain_list

        except Exception as e:
            print(f"[EVO CHAIN ERROR] {p.get('name')}: {e}")
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

    elif action == "set_game_version":
        ver = params.get("version", "modern")
        set_current_game_version(ver)
        # Return 200 OK or empty JSON

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
    action = params.get("action", [""])[0] if isinstance(params, dict) and isinstance(params.get("action"), list) else (params.get("action", "") if isinstance(params, dict) else "")

    task_nav = params.get("task_nav", [""])[0] if isinstance(params, dict) and isinstance(params.get("task_nav"), list) else (params.get("task_nav", "") if isinstance(params, dict) else "")
    set_tasks_raw = params.get("set_tasks", [""])[0] if isinstance(params, dict) and isinstance(params.get("set_tasks"), list) else (params.get("set_tasks", "") if isinstance(params, dict) else "")

    # --- Action Handling ---
    if "handle_common_action" in globals():
        handle_common_action(action, params, set_tasks_raw, task_nav)

    # 2. Extract values for HTML template placeholders:
    t_state = load_tasks_state() if "load_tasks_state" in globals() else {}
    tasks = t_state.get("tasks", [])
    idx = t_state.get("index", 0)
    total = len(tasks)

    active_task = tasks[idx] if (tasks and 0 <= idx < total) else "No active task"
    task_count_str = f"{idx + 1} / {total}" if total > 0 else "0 / 0"

    # --- Load Data Collections AFTER Actions Execute ---
    pkmn_data = all_pkmn_collection if "all_pkmn_collection" in globals() and all_pkmn_collection else (load_all_pokemon_names() if "load_all_pokemon_names" in globals() else [])

    # Extract just the list of names for JS
    if isinstance(pkmn_data, dict):
        js_pokemon_array = json.dumps(list(pkmn_data.keys()))
    else:
        js_pokemon_array = json.dumps(pkmn_data or [])

    team = load_team() if "load_team" in globals() else []
    target = load_active_target() if "load_active_target" in globals() else {}
    active_route = load_active_route() if "load_active_route" in globals() else {}
    counters = load_pokemon_counters() if "load_pokemon_counters" in globals() else {}
    hunt = load_shiny_hunt() if "load_shiny_hunt" in globals() else {}
    ev_state = load_ev_state() if "load_ev_state" in globals() else {}
    state = load_catch_state() if "load_catch_state" in globals() else {}
    deselected_pokemon = load_deselected_pokemon() if "load_deselected_pokemon" in globals() else []

    area_list = load_all_location_areas() if "load_all_location_areas" in globals() else []
    js_location_array = json.dumps(area_list)
    active_target_json = json.dumps(target if target else {})

    # --- Party Pills ---
    team_pills = (
        "".join([
            f"""<div class="flex items-center justify-between bg-slate-700/60 border border-slate-600 rounded-lg px-3 py-2">
            <div class="flex items-center gap-2">
                <span class="text-xs font-bold text-slate-400">#{i + 1}</span>
                <span class="font-semibold text-sm">{m.get('name', 'Unknown')}</span>
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

    # Generate EV Card
    ev_card_html = generate_ev_widget(ev_state, target, is_remote=False) if "generate_ev_widget" in globals() else ""

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

    active_gen_slug = target.get("selected_gen", "generation-ix") if target else "generation-ix"
    modern_target_evs = target.get("ev_yield", {}) if target else {}
    past_target_evs = target.get("past_ev_yields", {}) if target else {}
    target_slug = target.get("name", "").lower().strip() if target else ""

    if "resolve_ev_yield_for_version" in globals():
        resolved_target_evs = resolve_ev_yield_for_version(
            target_slug,
            modern_target_evs,
            past_target_evs,
            active_gen_slug
        )
    else:
        resolved_target_evs = modern_target_evs

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

        # Selected Version Encounters
        target_selected_version = str(target.get("selected_gen") or "yellow").lower().strip()
        all_target_encounters = target.get("encounters", {})

        raw_version_encounters = []
        if target_selected_version == "modern":
            for v_list in all_target_encounters.values():
                if isinstance(v_list, list):
                    raw_version_encounters.extend(v_list)
        else:
            if target_selected_version in all_target_encounters:
                raw_version_encounters.extend(all_target_encounters[target_selected_version])

            sub_versions = target_selected_version.split("-")
            for sub_v in sub_versions:
                if sub_v in all_target_encounters:
                    raw_version_encounters.extend(all_target_encounters[sub_v])

        dedup_encounters = {}
        for enc in raw_version_encounters:
            loc = enc.get("location", "Unknown Area")
            min_l = enc.get("min_level", 1)
            max_l = enc.get("max_level", 1)
            methods_tuple = tuple(sorted(enc.get("methods", [])))
            dedup_key = (loc, min_l, max_l, methods_tuple)

            if dedup_key not in dedup_encounters:
                dedup_encounters[dedup_key] = dict(enc)
            else:
                if enc.get("chance", 0) > dedup_encounters[dedup_key].get("chance", 0):
                    dedup_encounters[dedup_key]["chance"] = enc.get("chance", 0)

        target_version_encounters = list(dedup_encounters.values())

        if target_version_encounters:
            enc_rows = []
            for enc in target_version_encounters:
                methods_str = ", ".join(enc.get("methods", [])) or "Wild"
                min_l = enc.get("min_level", 1)
                max_l = enc.get("max_level", 1)
                lvl_str = f"Lv. {min_l}" if min_l == max_l else f"Lv. {min_l}-{max_l}"
                chance_val = enc.get("chance", 0)
                chance_badge = f'<span class="text-[10px] font-mono font-bold text-emerald-400">{chance_val}%</span>' if chance_val > 0 else ""

                enc_rows.append(f"""
                    <div class="flex justify-between items-center bg-slate-950/70 border border-slate-800/80 rounded-lg p-2 text-xs">
                        <div>
                            <div class="font-bold text-slate-200">{enc.get('location', 'Unknown Area')}</div>
                            <div class="text-[10px] text-slate-400">{methods_str}</div>
                        </div>
                        <div class="text-right">
                            <div class="font-mono text-amber-400 font-semibold">{lvl_str}</div>
                            {chance_badge}
                        </div>
                    </div>
                """)
            target_encounters_html = "".join(enc_rows)
        else:
            target_encounters_html = f'<div class="text-slate-500 text-xs italic p-2">No wild encounters listed for version "{target_selected_version}".</div>'

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

            <!-- Target Wild Encounters -->
            <div>
                <div class="flex items-center justify-between mb-1.5">
                    <h4 class="text-[11px] uppercase font-bold text-slate-400 tracking-wider">Wild Encounters</h4>
                    <span id="target-encounters-version-badge" class="text-[10px] font-mono font-bold text-amber-400 uppercase">{target_selected_version}</span>
                </div>
                <div id="target-encounters-list" class="space-y-1.5 bg-slate-900/40 p-2.5 rounded-xl border border-slate-800 max-h-48 overflow-y-auto">
                    {target_encounters_html}
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
            raw_evos = p.get("evolutions", [])

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
                        "evolutions": raw_evos,
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

                evos_data = data.get("evolutions", [])
                if not evos_data:
                    cache_dir = getattr(handlers, "TARGET_CACHE_DIR", "target_cache") if "handlers" in globals() else "target_cache"
                    slug_candidates = [p_slug]
                    if "handlers" in globals() and hasattr(handlers, "resolve_pokemon_endpoint_slug"):
                        slug_candidates.append(handlers.resolve_pokemon_endpoint_slug(p_slug))

                    for s in slug_candidates:
                        c_path = os.path.join(cache_dir, f"{s}.json")
                        if os.path.exists(c_path):
                            try:
                                with open(c_path, "r", encoding="utf-8") as f:
                                    c_json = json.load(f)
                                    evos_data = c_json.get("evolutions", [])
                                    if evos_data:
                                        break
                            except Exception:
                                pass

                if not evos_data:
                    all_pk = getattr(handlers, "all_pkmn_collection", {}) if "handlers" in globals() else globals().get("all_pkmn_collection", {})
                    if isinstance(all_pk, dict) and p_slug in all_pk:
                        evos_data = all_pk[p_slug].get("evolutions", [])

                evos_json_attr = json.dumps(evos_data).replace('"', '&quot;')

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

                is_checked = "checked" if "deselected_pokemon" not in globals() or p_name not in deselected_pokemon else ""

                poke_rows.append(f"""
                    <div class="route-row flex justify-between items-center bg-slate-950/70 border border-slate-800/80 rounded-lg p-2 hover:border-slate-700 transition" data-evolutions="{evos_json_attr}">
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
                                <a href="/?action=inc_counter&name={quote_plus(p_name) if 'quote_plus' in globals() else p_name}" class="text-[10px] bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-1.5 py-0.5 rounded active:scale-95 transition">+ Track</a>
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

        tools_dropdown_html = generate_tools_dropdown_widget() if "generate_tools_dropdown_widget" in globals() else ""

        route_view = f"""
        <div class="space-y-3">
            <div class="mb-1">
                {tools_dropdown_html}
            </div>

            <div class="bg-emerald-950/30 border border-emerald-500/30 rounded-xl p-3">
                <div class="text-xs uppercase font-bold text-emerald-400">Current Location</div>
                <div class="text-lg font-black text-white">{active_route['name']}</div>
                <div class="text-xs text-slate-400 mt-0.5">{active_route['total_species']} total species across all versions</div>
            </div>

            <button 
                onclick="trackAllRoutePokemon(event)" 
                class="w-full bg-emerald-600/20 hover:bg-emerald-600/30 active:bg-emerald-600/40 border border-emerald-500/40 hover:border-emerald-400 text-emerald-300 hover:text-emerald-200 font-bold py-2 px-3 rounded-xl text-xs flex items-center justify-center gap-2 transition-colors shadow-sm">
                <span>➕</span>
                <span>Click here to add all Pokémon on the route to tracking</span>
            </button>

            <div class="ev-warning">⚠️ Warning: On route list, only modern EVs are used</div>

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

        {SHARED_POKEMON_JS if "SHARED_POKEMON_JS" in globals() else ""}

        window.addEventListener('DOMContentLoaded', () => {{
            if (typeof updateTargetGenView === 'function') updateTargetGenView();
            if (typeof calcExpGap === 'function') calcExpGap();
            initDashboardSectionToggles();
        }});
    </script>
    <style>
        .ev-warning {{
            font-family: monospace;
            font-size: 11px;
            color: #fbbf24;
            background: rgba(0, 0, 0, 0.6);
            padding: 4px 8px;
            border-radius: 4px;
            border-left: 3px solid #f59e0b;
            display: block;
        }}
        .dash-toggle-btn-off {{
            opacity: 0.35 !important;
            border-color: #334155 !important;
            color: #64748b !important;
            background: #0f172a !important;
        }}
    </style>
</head>
<body class="bg-slate-950 text-slate-100 font-sans min-h-screen">
    <!-- Header with Dual Search and Section Toggles -->
    <header class="sticky top-0 z-50 bg-slate-900/95 backdrop-blur border-b border-slate-800 p-3 space-y-2.5">
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

        <!-- Section Toggles Toolbar -->
        <div class="max-w-[1600px] mx-auto flex items-center gap-1.5 overflow-x-auto text-[11px] font-bold pt-0.5 whitespace-nowrap min-w-max">
            <span class="text-[10px] uppercase font-bold text-slate-400 mr-1 tracking-wider">Toggles:</span>
            <button id="btn-sec-target" onclick="toggleDashSec('sec-target')" class="px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-amber-400 transition hover:bg-slate-700">Target Pokemon View</button>
            <button id="btn-sec-route" onclick="toggleDashSec('sec-route')" class="px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-emerald-400 transition hover:bg-slate-700">Route</button>
            <button id="btn-sec-counters" onclick="toggleDashSec('sec-counters')" class="px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-indigo-400 transition hover:bg-slate-700">Hunt List</button>
            <button id="btn-sec-shiny" onclick="toggleDashSec('sec-shiny')" class="px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-amber-300 transition hover:bg-slate-700">Shiny</button>
            <button id="btn-sec-ev" onclick="toggleDashSec('sec-ev')" class="px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-rose-400 transition hover:bg-slate-700">EVs</button>
            <button id="btn-sec-party" onclick="toggleDashSec('sec-party')" class="px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-purple-400 transition hover:bg-slate-700">Party</button>
            <button id="btn-sec-walkthrough" onclick="toggleDashSec('sec-walkthrough')" class="px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-teal-400 transition hover:bg-slate-700">Walkthrough</button>
            <button id="btn-sec-tasks" onclick="toggleDashSec('sec-tasks')" class="px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-sky-400 transition hover:bg-slate-700">Tasks</button>
            <button id="btn-sec-note" onclick="toggleDashSec('sec-note')" class="px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 transition hover:bg-slate-700">Note</button>
        </div>
    </header>

    <!-- 3-Column Responsive Grid -->
    <main class="max-w-[1600px] mx-auto p-4 grid grid-cols-1 lg:grid-cols-12 gap-5">

        <!-- Col 1: Active Target Pokémon (4 Cols) -->
        <section id="sec-target" class="lg:col-span-4 bg-slate-900/70 border border-slate-800/80 rounded-2xl p-4 shadow-xl">
            <h2 class="text-sm font-black text-white uppercase tracking-wider mb-3 flex items-center justify-between">
                <span>Active Target Scanner</span>
                <span class="text-[10px] font-mono text-slate-400">OBS Linked</span>
            </h2>
            {target_view}
        </section>

        <!-- Col 2: Route Encounters Table (4 Cols) -->
        <section id="sec-route" class="lg:col-span-4 bg-slate-900/70 border border-slate-800/80 rounded-2xl p-4 shadow-xl">
            <h2 class="text-sm font-black text-white uppercase tracking-wider mb-3 flex items-center justify-between">
                <span>Route Encounters</span>
                <span class="text-[10px] font-mono text-emerald-400">Wild Spawns</span>
            </h2>
            {route_view}
        </section>

        <!-- Col 3: Stream Management, Queue, & Counters (4 Cols) -->
        <section class="lg:col-span-4 space-y-4">

            <!-- Catch Target Quick Taps -->
            <div id="sec-counters" class="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-4">
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

            <!-- Shiny Hunt -->
            <div id="sec-shiny">
                {shiny_card}
            </div>

            <!-- EV Card -->
            <div id="sec-ev">
                {ev_card_html}
            </div>

            <!-- Party Queue -->
            <div id="sec-party" class="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-4">
                <div class="flex items-center justify-between mb-2">
                    <h3 class="text-xs uppercase font-bold text-slate-300">Party Queue ({len(team)})</h3>
                    <a href="/obs/team" target="_blank" class="text-[11px] text-indigo-400 hover:underline">OBS View ↗</a>
                </div>
                <div class="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                    {team_pills}
                </div>
            </div>

            <!-- Bulbapedia Walkthrough Task Loader -->
            <div id="sec-walkthrough" class="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-4 space-y-3">
                <div class="flex justify-between items-center">
                    <span class="text-[10px] uppercase font-bold text-slate-400">Bulbapedia Walkthrough</span>
                    <span class="text-[10px] font-mono text-indigo-400 font-bold">TASK LOADER</span>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
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

                    <div>
                        <label class="text-[10px] text-slate-400 font-bold uppercase block mb-1">2. Select Chapter / Part:</label>
                        <select id="walkthrough-part-select" onchange="loadSelectedPartTasks()" disabled class="w-full bg-slate-950/80 border border-slate-800 text-slate-200 rounded-lg p-2 text-xs focus:outline-none focus:border-emerald-500 disabled:opacity-40">
                            <option value="">-- Select Game First --</option>
                        </select>
                    </div>
                </div>
            </div>

            <!-- Task Queue Manager -->
            <div id="sec-tasks" class="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-4">
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
            <div id="sec-note" class="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-4">
                <h3 class="text-xs uppercase font-bold text-slate-300 mb-2">Video Message Note</h3>
                <form action="/videomessage" method="GET" class="space-y-1.5">
                    <textarea name="notes" placeholder="Update video note..." class="w-full bg-slate-800 text-xs border border-slate-700 rounded-lg p-2 text-white h-16"></textarea>
                    <button type="submit" class="w-full bg-indigo-600 hover:bg-indigo-500 font-bold text-[11px] py-1.5 rounded-lg transition">Overwrite Note</button>
                </form>
            </div>

        </section>
    </main>

    <!-- Client-side Dashboard Section Toggle Logic -->
    <script>
        const dashSections = [
            'sec-target', 'sec-route', 'sec-counters', 'sec-shiny',
            'sec-ev', 'sec-party', 'sec-walkthrough', 'sec-tasks', 'sec-note'
        ];

        function applyDashSecDisplay(secId, visible) {{
            const el = document.getElementById(secId);
            const btn = document.getElementById('btn-' + secId);
            if (el) el.style.display = visible ? '' : 'none';
            if (btn) {{
                if (visible) btn.classList.remove('dash-toggle-btn-off');
                else btn.classList.add('dash-toggle-btn-off');
            }}
        }}

        function toggleDashSec(secId) {{
            const current = localStorage.getItem('dashboard_show_' + secId) !== 'false';
            const next = !current;
            localStorage.setItem('dashboard_show_' + secId, next);
            applyDashSecDisplay(secId, next);
        }}

        function initDashboardSectionToggles() {{
            dashSections.forEach(secId => {{
                const saved = localStorage.getItem('dashboard_show_' + secId);
                const isVisible = saved !== 'false';
                applyDashSecDisplay(secId, isVisible);
            }});
        }}
    </script>
</body>
</html>"""
    return html, ("Content-Type", "text/html")



# --- OBS Views ---



def handle_pokemon_remote(params=None):
    action = params.get("action", [""])[0] if isinstance(params, dict) and isinstance(params.get("action"), list) else (params.get("action", "") if isinstance(params, dict) else "")
    task_nav = params.get("task_nav", [""])[0] if isinstance(params, dict) and isinstance(params.get("task_nav"), list) else (params.get("task_nav", "") if isinstance(params, dict) else "")
    set_tasks_raw = params.get("set_tasks", [""])[0] if isinstance(params, dict) and isinstance(params.get("set_tasks"), list) else (params.get("set_tasks", "") if isinstance(params, dict) else "")

    if "handle_common_action" in globals():
        handle_common_action(action, params, set_tasks_raw, task_nav)

    # 1. Load Data State
    pkmn_data = all_pkmn_collection if "all_pkmn_collection" in globals() and all_pkmn_collection else (load_all_pokemon_names() if "load_all_pokemon_names" in globals() else [])
    if isinstance(pkmn_data, dict):
        js_pokemon_array = json.dumps(list(pkmn_data.keys()))
    else:
        js_pokemon_array = json.dumps(pkmn_data or [])

    team = load_team() if "load_team" in globals() else []
    target = load_active_target() if "load_active_target" in globals() else {}
    active_route = load_active_route() if "load_active_route" in globals() else {}
    tasks_state = load_tasks_state() if "load_tasks_state" in globals() else {}
    counters = load_pokemon_counters() if "load_pokemon_counters" in globals() else {}
    hunt = load_shiny_hunt() if "load_shiny_hunt" in globals() else {}
    ev_state = load_ev_state() if "load_ev_state" in globals() else {}
    state = load_catch_state() if "load_catch_state" in globals() else {}
    deselected_pokemon = load_deselected_pokemon() if "load_deselected_pokemon" in globals() else []

    area_list = load_all_location_areas() if "load_all_location_areas" in globals() else []
    js_location_array = json.dumps(area_list)
    active_target_json = json.dumps(target if target else {})

    # 2. Task Strings
    active_task = (
        tasks_state["tasks"][tasks_state["index"]]
        if (tasks_state.get("tasks") and 0 <= tasks_state.get("index", 0) < len(tasks_state["tasks"]))
        else "No active task"
    )
    task_count_str = (
        f"{tasks_state.get('index', 0) + 1} / {len(tasks_state['tasks'])}"
        if tasks_state.get("tasks") else "0 / 0"
    )

    # 3. Party Pills
    team_pills = (
        "".join([
            f"""<div class="flex items-center justify-between bg-slate-800/80 border border-slate-700/80 rounded-xl px-4 py-3 text-base">
                <div class="flex items-center gap-3">
                    <span class="font-bold text-slate-400 text-lg">#{i + 1}</span>
                    <span class="font-bold text-white text-lg">{m.get('name', 'Unknown')}</span>
                    {f'<span class="text-xs bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-md font-bold">Active 6</span>' if i < 6 else ''}
                </div>
                <a href="/remote?action=team_remove&index={i}" class="text-rose-400 hover:text-rose-300 font-extrabold text-lg px-3 py-2">✕</a>
            </div>"""
            for i, m in enumerate(team)
        ])
        or '<div class="text-slate-500 text-base italic py-3 text-center">Party is empty.</div>'
    )

    # 4. Shiny Hunt Card
    shiny_card = f"""
    <div class="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-4 space-y-3.5">
        <div class="flex items-center justify-between">
            <h3 class="text-base uppercase font-black text-amber-400 flex items-center gap-2 tracking-wide">
                <span>✨ Shiny Hunt</span>
            </h3>
            <a href="/obs/shiny" target="_blank" class="text-sm font-bold text-amber-400/80 hover:underline">OBS Overlay ↗</a>
        </div>
        <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-4 text-center">
            <div class="text-sm text-slate-300 font-bold">{hunt.get('target', 'None')} <span class="text-slate-600 mx-1">•</span> <span class="text-slate-400 text-xs">{hunt.get('method', 'Encounters')}</span></div>
            <div id="shiny-count" class="text-5xl font-black font-mono text-amber-300 my-2">{hunt.get('count', 0)}</div>
            <div class="flex gap-2 justify-center mt-3">
                <button type="button" onclick="fetch('/remote?action=shiny_dec').then(() => {{ const el = document.getElementById('shiny-count'); if (el) el.innerText = Math.max(0, parseInt(el.innerText || '0') - 1); }});" class="h-12 px-5 bg-slate-800 hover:bg-slate-700 text-slate-200 font-black text-base rounded-xl transition active:scale-95">-1</button>
                <button type="button" onclick="fetch('/remote?action=shiny_inc').then(() => {{ const el = document.getElementById('shiny-count'); if (el) el.innerText = parseInt(el.innerText || '0') + 1; }});" class="h-12 px-7 bg-amber-500 hover:bg-amber-400 text-slate-950 font-black text-base rounded-xl transition active:scale-95">+1 Encounter</button>
                <button type="button" onclick="if (confirm('Reset counter to 0?')) {{ fetch('/remote?action=shiny_reset').then(() => {{ const el = document.getElementById('shiny-count'); if (el) el.innerText = '0'; }}); }}" class="h-12 px-4 bg-rose-950/50 hover:bg-rose-900 text-rose-300 font-black text-sm rounded-xl border border-rose-800/40 transition active:scale-95">Reset</button>
            </div>
        </div>
        <form action="/remote" method="GET" class="flex gap-2">
            <input type="hidden" name="action" value="set_shiny_target" />
            <input name="name" placeholder="Target..." class="w-1/2 bg-slate-800 text-sm border border-slate-700 rounded-xl px-3 py-2.5 text-white placeholder-slate-400" />
            <input name="method" placeholder="Method..." class="w-1/2 bg-slate-800 text-sm border border-slate-700 rounded-xl px-3 py-2.5 text-white placeholder-slate-400" />
            <button type="submit" class="bg-slate-800 hover:bg-slate-700 font-bold text-sm px-4 rounded-xl transition text-slate-200">Set</button>
        </form>
    </div>
    """

    # 5. EV Card
    ev_card_html = generate_ev_widget(ev_state, target, is_remote=True) if "generate_ev_widget" in globals() else ""

    # 6. Catch Targets Pills
    counter_pills = (
        "".join([
            f"""<a href="/remote?action=dec_counter&name={quote_plus(name) if 'quote_plus' in globals() else name}" class="flex items-center justify-between bg-slate-800/70 hover:bg-slate-800 border border-slate-700/70 rounded-xl p-3 text-base transition">
                <span class="font-bold text-slate-100 text-base">{name}</span>
                <span class="bg-indigo-600 text-white font-mono px-3 py-1 rounded-full text-sm font-black">{count}</span>
            </a>"""
            for name, count in counters.items()
        ])
        or '<div class="text-slate-500 text-base italic py-3 text-center">No catch targets configured.</div>'
    )

    # 7. EV Yield Label Resolution
    active_gen_slug = target.get("selected_gen", "generation-ix") if target else "generation-ix"
    modern_target_evs = target.get("ev_yield", {}) if target else {}
    past_target_evs = target.get("past_ev_yields", {}) if target else {}
    target_slug = target.get("name", "").lower().strip() if target else ""

    if "resolve_ev_yield_for_version" in globals():
        resolved_target_evs = resolve_ev_yield_for_version(target_slug, modern_target_evs, past_target_evs, active_gen_slug)
    else:
        resolved_target_evs = modern_target_evs

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

    # 8. Target View
    target_view = '<div class="text-slate-500 text-base italic py-8 text-center">Search and inspect a Pokémon to load stats.</div>'
    if target:
        growth_rate_slug = target.get("growth_rate", "medium-fast").lower()
        default_sprite = target.get("sprite", "")

        evos_list = "".join([
            f'<li class="text-sm font-semibold text-slate-200 py-0.5">{evo}</li>'
            for evo in target.get("evolutions", [])
        ])

        moves_list = "".join([
            f"""<div class="target-move-row flex justify-between text-sm py-1.5 border-b border-slate-700/40" data-vg="{m.get('vg', 'all')}" data-move="{m.get('move', '')}">
                <span class="text-slate-200 font-medium">{m['move']} <span class="text-xs text-slate-500">({m.get('vg', '')})</span></span>
                <span class="font-mono text-amber-400 font-bold">Lv. {m['level']}</span>
            </div>"""
            for m in target.get("level_moves", [])
        ])

        target_selected_version = str(
            (get_current_game_version() if "get_current_game_version" in globals() else "")
            or target.get("selected_gen")
            or "yellow"
        ).strip("[]'\" ").lower()

        all_target_encounters = target.get("encounters", {}) or {}

        raw_version_encounters = []
        if target_selected_version == "modern":
            for v_list in all_target_encounters.values():
                if isinstance(v_list, list):
                    raw_version_encounters.extend(v_list)
        else:
            if target_selected_version in all_target_encounters:
                raw_version_encounters.extend(all_target_encounters[target_selected_version])
            sub_versions = target_selected_version.split("-")
            for sub_v in sub_versions:
                if sub_v in all_target_encounters:
                    raw_version_encounters.extend(all_target_encounters[sub_v])

        dedup_encounters = {}
        for enc in raw_version_encounters:
            loc = enc.get("location", "Unknown Area")
            min_l = enc.get("min_level", 1)
            max_l = enc.get("max_level", 1)
            methods_tuple = tuple(sorted(enc.get("methods", [])))
            dedup_key = (loc, min_l, max_l, methods_tuple)
            if dedup_key not in dedup_encounters:
                dedup_encounters[dedup_key] = dict(enc)
            else:
                if enc.get("chance", 0) > dedup_encounters[dedup_key].get("chance", 0):
                    dedup_encounters[dedup_key]["chance"] = enc.get("chance", 0)

        target_version_encounters = list(dedup_encounters.values())

        if target_version_encounters:
            enc_rows = []
            for enc in target_version_encounters:
                methods_str = ", ".join(enc.get("methods", [])) or "Wild"
                min_l = enc.get("min_level", 1)
                max_l = enc.get("max_level", 1)
                lvl_str = f"Lv. {min_l}" if min_l == max_l else f"Lv. {min_l}-{max_l}"
                chance_val = enc.get("chance", 0)
                chance_badge = f'<span class="text-xs font-mono font-black text-emerald-400">{chance_val}%</span>' if chance_val > 0 else ""
                enc_rows.append(f"""
                    <div class="flex justify-between items-center bg-slate-950/70 border border-slate-800/80 rounded-xl p-2.5 text-sm">
                        <div>
                            <div class="font-bold text-slate-100 text-sm">{enc.get('location', 'Unknown Area')}</div>
                            <div class="text-xs text-slate-400 font-medium">{methods_str}</div>
                        </div>
                        <div class="text-right">
                            <div class="font-mono text-amber-400 font-bold text-sm">{lvl_str}</div>
                            {chance_badge}
                        </div>
                    </div>
                """)
            target_encounters_html = "".join(enc_rows)
        else:
            target_encounters_html = f'<div class="text-slate-500 text-sm italic p-3 text-center">No wild encounters listed for version "{target_selected_version}".</div>'

        target_view = f"""
        <div class="space-y-4">
            <div class="bg-slate-900/60 p-4 rounded-2xl border border-slate-700/50 space-y-3.5">
                <div class="flex items-center gap-3.5">
                    <img id="target-sprite-img" src="{default_sprite}" class="w-20 h-20 bg-slate-800 rounded-xl p-1.5 border border-slate-700 object-contain image-render-pixelated" />
                    <div class="flex-grow">
                        <div class="flex items-center gap-2">
                            <h3 class="text-2xl font-black text-white">{target['name']}</h3>
                            <span class="text-slate-400 text-sm font-mono font-bold">#{target['id']}</span>
                        </div>
                        <div class="flex flex-wrap gap-1.5 mt-1.5" id="target-type-badges"></div>
                    </div>
                </div>

                <div class="flex items-center justify-between gap-3 pt-2.5 border-t border-slate-800">
                    <span class="font-extrabold text-slate-300 uppercase text-xs tracking-wider">Inspect Game:</span>
                    <select id="target-gen-select" onchange="updateTargetGenView()" class="w-56 bg-slate-950 border border-slate-700 text-amber-400 font-black rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-amber-400">
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

            <div class="grid grid-cols-3 gap-2.5">
                <div class="bg-slate-900/40 p-2.5 rounded-xl border border-slate-800 text-center">
                    <div class="text-xs text-slate-400 uppercase font-black">Catch Rate</div>
                    <div class="text-base font-mono font-black text-emerald-400 mt-0.5">{target.get('catch_rate', 0)}</div>
                </div>
                <div class="bg-slate-900/40 p-2.5 rounded-xl border border-slate-800 text-center">
                    <div class="text-xs text-slate-400 uppercase font-black">Base EXP</div>
                    <div class="text-base font-mono font-black text-sky-400 mt-0.5">{target.get('base_experience', 0)}</div>
                </div>
                <div class="bg-slate-900/40 p-2.5 rounded-xl border border-slate-800 text-center">
                    <div class="text-xs text-slate-400 uppercase font-black">EV Yield</div>
                    <div id="target-ev-yield-display" class="text-xs font-mono font-black text-amber-400 truncate mt-0.5">
                        {ev_yield_str}
                    </div>
                </div>
            </div>

           <div class="bg-slate-900/60 border border-slate-800 rounded-2xl p-4 text-sm space-y-3">
            <input type="hidden" id="target-growth-rate" value="{growth_rate_slug}" />
            <div class="flex items-center justify-between text-slate-300 font-extrabold uppercase text-xs tracking-wider">
                <span>EXP Grind Calc</span>
                <span class="text-amber-400 font-mono font-black capitalize text-sm">{growth_rate_slug.replace('-', ' ')}</span>
            </div>
            <div class="flex items-center gap-2 text-slate-200 font-bold text-base">
                <span>Lvl</span>
                <input id="exp-from" type="number" min="1" max="99" value="1" oninput="calcExpGap()" class="w-16 h-10 bg-slate-950 border border-slate-700 rounded-xl px-2 text-center text-white font-mono font-black text-base focus:outline-none focus:border-amber-400" />
                <span>to</span>
                <input id="exp-to" type="number" min="2" max="100" value="36" oninput="calcExpGap()" class="w-16 h-10 bg-slate-950 border border-slate-700 rounded-xl px-2 text-center text-white font-mono font-black text-base focus:outline-none focus:border-amber-400" />
                <span class="text-slate-500 font-black">=&gt;</span>
                <span id="exp-output" class="font-mono font-black text-amber-400 text-sm ml-auto">46,656 EXP</span>
            </div>
            <div class="flex items-center justify-between gap-2 pt-2.5 border-t border-slate-800/80 text-slate-300">
                <div class="flex items-center gap-2">
                    <span class="text-xs font-extrabold uppercase text-slate-400">Avg EXP/Kill:</span>
                    <input id="exp-per-kill" type="number" min="1" value="120" oninput="calcExpGap()" class="w-16 h-9 bg-slate-950 border border-slate-700 rounded-xl px-2 text-center text-amber-300 font-mono font-black text-sm focus:outline-none focus:border-amber-400" />
                </div>
                <div class="text-right font-mono text-xs">
                    <span id="grind-battles" class="text-slate-200 font-bold">389 kills</span>
                    <span class="text-slate-600 mx-1">•</span>
                    <span id="grind-time" class="text-emerald-400 font-black">~1h 37m</span>
                </div>
            </div>
            <div class="bg-slate-900/60 border border-slate-800 rounded-2xl p-4 text-sm space-y-3.5">
                <div class="flex items-center justify-between text-slate-300 font-black uppercase text-xs tracking-wider">
                    <span>Live Catch Odds</span>
                    <span id="catch-odds-display" class="text-emerald-400 font-mono font-black text-base">{state.get('odds', '--%')}</span>
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div class="space-y-1.5">
                        <div class="flex justify-between text-xs text-slate-400 font-bold">
                            <span>Target HP</span>
                            <span id="catch-hp-display" class="text-amber-400 font-mono font-black text-sm">{state.get('hp', '100')}%</span>
                        </div>
                        <input type="range" id="catch-hp-slider" min="1" max="100" value="{state.get('hp', '100')}" oninput="calculateCatchOdds()" class="w-full h-3 bg-slate-800 rounded-lg accent-emerald-500 cursor-pointer" />
                    </div>
                    <div class="space-y-1.5">
                        <div class="flex justify-between text-xs text-slate-400 font-bold">
                            <span>Target Level</span>
                            <span id="catch-lvl-display" class="text-indigo-400 font-mono font-black text-sm">{state.get('lvl', '50')}</span>
                        </div>
                        <input type="number" id="catch-lvl-input" min="1" max="100" value="{state.get('lvl', '50')}" oninput="calculateCatchOdds()" class="w-full h-10 bg-slate-950 border border-slate-700 text-slate-200 rounded-xl px-2.5 text-center font-mono font-black text-base focus:outline-none focus:border-indigo-400" />
                    </div>
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <div class="text-xs text-slate-400 font-black uppercase mb-1">STATUS</div>
                        <select id="catch-status-select" onchange="calculateCatchOdds()" class="w-full h-11 bg-slate-950 border border-slate-700 text-slate-200 font-bold rounded-xl px-3 text-sm focus:outline-none focus:border-amber-400">
                            <option value="1" {"selected" if str(state.get('status')) == '1' else ""}>None</option>
                            <option value="2.5" {"selected" if str(state.get('status')) == '2.5' else ""}>Sleep / Freeze</option>
                            <option value="1.5" {"selected" if str(state.get('status')) == '1.5' else ""}>Paralyze / Poison / Burn</option>
                        </select>
                    </div>
                    <div>
                        <div class="text-xs text-slate-400 font-black uppercase mb-1">BALL</div>
                        <select id="catch-ball-select" onchange="calculateCatchOdds()" class="w-full h-11 bg-slate-950 border border-slate-700 text-slate-200 font-bold rounded-xl px-3 text-sm focus:outline-none focus:border-emerald-400">
                            <option value="poke" {"selected" if state.get('ball') == 'poke' else ""}>Poké Ball</option>
                            <option value="great" {"selected" if state.get('ball') == 'great' else ""}>Great Ball</option>
                            <option value="ultra" {"selected" if state.get('ball') == 'ultra' else ""}>Ultra Ball</option>
                            <option value="master" {"selected" if state.get('ball') == 'master' else ""}>Master Ball</option>
                        </select>
                    </div>
                </div>
            </div>

            <div>
                <div class="flex items-center justify-between mb-2">
                    <h4 class="text-xs uppercase font-black text-slate-400 tracking-wider">Wild Encounters</h4>
                    <span id="target-encounters-version-badge" class="text-xs font-mono font-black text-amber-400 uppercase">{target_selected_version}</span>
                </div>
                <div id="target-encounters-list" class="space-y-2 bg-slate-900/40 p-3 rounded-2xl border border-slate-800 max-h-56 overflow-y-auto">
                    {target_encounters_html}
                </div>
            </div>

            <div>
                <div class="flex items-center justify-between mb-2">
                    <h4 class="text-xs uppercase font-black text-slate-400 tracking-wider">Base Stats</h4>
                    <span id="target-bst-badge" class="text-xs font-black px-2 py-0.5 rounded-md bg-amber-500/20 border border-amber-500/30 text-amber-300">BST {target['bst']}</span>
                </div>
                <div id="target-stats-container" class="space-y-2 bg-slate-900/40 p-3.5 rounded-2xl border border-slate-800"></div>
            </div>

            <div>
                <h4 class="text-xs uppercase font-black text-slate-400 tracking-wider mb-2">Matchups</h4>
                <div class="space-y-2.5 bg-slate-900/40 p-3 rounded-2xl border border-slate-800 text-sm">
                    <div><span class="text-xs font-black text-rose-400 uppercase tracking-wide">Weaknesses:</span> <div id="target-weakness-tags" class="flex flex-wrap gap-1.5 mt-1.5"></div></div>
                    <div><span class="text-xs font-black text-emerald-400 uppercase tracking-wide">Resistances:</span> <div id="target-resistance-tags" class="flex flex-wrap gap-1.5 mt-1.5"></div></div>
                    <div><span class="text-xs font-black text-purple-400 uppercase tracking-wide">Immunities:</span> <div id="target-immunity-tags" class="flex flex-wrap gap-1.5 mt-1.5"></div></div>
                </div>
            </div>

            <div>
                <h4 class="text-xs uppercase font-black text-slate-400 tracking-wider mb-2">Evolutions</h4>
                <ul class="bg-slate-900/40 p-3 rounded-2xl border border-slate-800 space-y-1.5">{evos_list}</ul>
            </div>

            <div>
                <h4 class="text-xs uppercase font-black text-slate-400 tracking-wider mb-2">Level-Up Moves</h4>
                <div class="bg-slate-900/40 p-3 rounded-2xl border border-slate-800 max-h-56 overflow-y-auto space-y-1" id="moves-container">
                    {moves_list or '<span class="text-sm text-slate-500 italic">No level-up moves listed.</span>'}
                </div>
            </div>
        </div>
        """

    # 9. Route View
    route_view = '<div class="text-slate-500 text-base italic py-8 text-center">Search and select a Route to load wild encounter tables.</div>'
    if active_route:
        games = {}
        for p in active_route.get("pokemon", []):
            p_name = p.get("name", "Unknown")
            p_slug = p.get("slug", p_name.lower().replace(" ", "-"))
            modern_evs = p.get("ev_yield", {})
            past_evs = p.get("past_ev_yields", {})
            raw_evos = p.get("evolutions", [])

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
                        "evolutions": raw_evos,
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

                evos_data = data.get("evolutions", [])
                if not evos_data:
                    cache_dir = getattr(handlers, "TARGET_CACHE_DIR", "target_cache") if "handlers" in globals() else "target_cache"
                    slug_candidates = [p_slug]
                    if "handlers" in globals() and hasattr(handlers, "resolve_pokemon_endpoint_slug"):
                        slug_candidates.append(handlers.resolve_pokemon_endpoint_slug(p_slug))

                    for s in slug_candidates:
                        c_path = os.path.join(cache_dir, f"{s}.json")
                        if os.path.exists(c_path):
                            try:
                                with open(c_path, "r", encoding="utf-8") as f:
                                    c_json = json.load(f)
                                    evos_data = c_json.get("evolutions", [])
                                    if evos_data:
                                        break
                            except Exception:
                                pass

                if not evos_data:
                    all_pk = getattr(handlers, "all_pkmn_collection", {}) if "handlers" in globals() else globals().get("all_pkmn_collection", {})
                    if isinstance(all_pk, dict) and p_slug in all_pk:
                        evos_data = all_pk[p_slug].get("evolutions", [])

                evos_json_attr = json.dumps(evos_data).replace('"', '&quot;')

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
                            ev_btn_html = f'<a href="{ev_link}" class="h-9 flex items-center text-xs bg-rose-600 hover:bg-rose-500 text-white font-black px-2.5 py-1 rounded-xl active:scale-95 transition whitespace-nowrap shadow-sm">{btn_text}</a>'
                except Exception:
                    ev_btn_html = ""

                chance_badge = f'<div class="text-xs font-mono font-black text-emerald-400">{chance_str}</div>' if chance_str else ''
                is_checked = "checked" if "deselected_pokemon" not in globals() or p_name not in deselected_pokemon else ""

                poke_rows.append(f"""
                    <div class="route-row flex justify-between items-center bg-slate-950/70 border border-slate-800/80 rounded-xl p-2.5 hover:border-slate-700 transition" data-evolutions="{evos_json_attr}">
                        <div class="flex items-center gap-3">
                            <input 
                                type="checkbox" 
                                class="route-poke-checkbox w-6 h-6 rounded-lg bg-slate-900 border-slate-700 text-indigo-500 focus:ring-0 cursor-pointer" 
                                data-poke-name="{p_name}" 
                                onchange="onPokemonCheckboxChange(this)"
                                {is_checked}
                            />
                            <div>
                                <div class="poke-name font-bold text-white text-base leading-snug" data-poke-name="{p_name}">{p_name}</div>
                                <div class="text-xs text-slate-400 font-medium">{methods_str}</div>
                            </div>
                        </div>
                        <div class="flex items-center gap-2">
                            <div class="text-right mr-1">
                                <div class="text-xs font-mono text-amber-400 font-bold">{levels_str}</div>
                                {chance_badge}
                            </div>
                            <div class="flex gap-1.5">
                                <a href="/remote?action=set_target&name={p_slug}" class="h-9 flex items-center text-xs bg-amber-500 hover:bg-amber-400 text-slate-950 font-black px-2.5 py-1 rounded-xl active:scale-95 transition shadow-sm">Target</a>
                                {ev_btn_html}
                                <a href="/remote?action=team_add&name={p_slug}" class="h-9 flex items-center text-xs bg-indigo-600 hover:bg-indigo-500 text-white font-black px-2.5 py-1 rounded-xl active:scale-95 transition shadow-sm">+ Party</a>
                                <a href="/remote?action=inc_counter&name={quote_plus(p_name) if 'quote_plus' in globals() else p_name}" class="h-9 flex items-center text-xs bg-emerald-600 hover:bg-emerald-500 text-white font-black px-2.5 py-1 rounded-xl active:scale-95 transition shadow-sm">+ Track</a>
                            </div>
                        </div>
                    </div>
                """)

            game_sections.append(f"""
            <div class="game-version-card bg-slate-900/60 border border-slate-800 rounded-2xl p-3 space-y-2" data-version="{ver_slug}">
                <div class="text-xs font-black uppercase tracking-wider text-indigo-300 bg-indigo-950/50 px-3 py-1.5 rounded-xl border border-indigo-900/50 flex justify-between items-center">
                    <span>{ver_name}</span>
                    <span class="text-indigo-400 font-bold">{len(species_dict)} species</span>
                </div>
                <div class="space-y-1.5">
                    {''.join(poke_rows)}
                </div>
            </div>
            """)

        tools_dropdown_html = generate_tools_dropdown_widget() if "generate_tools_dropdown_widget" in globals() else ""

        route_view = f"""
        <div class="space-y-3.5">
            <div class="mb-1">
                {tools_dropdown_html}
            </div>

            <div class="bg-emerald-950/30 border border-emerald-500/30 rounded-2xl p-4">
                <div class="text-xs uppercase font-black text-emerald-400 tracking-wider">Current Location</div>
                <div class="text-xl font-black text-white mt-0.5">{active_route['name']}</div>
                <div class="text-xs text-slate-300 mt-1 font-medium">{active_route['total_species']} species across all versions</div>
            </div>

            <button 
                onclick="trackAllRoutePokemon(event)" 
                class="w-full h-12 bg-emerald-600/25 hover:bg-emerald-600/35 active:bg-emerald-600/45 border border-emerald-500/40 hover:border-emerald-400 text-emerald-300 font-black py-2.5 px-4 rounded-xl text-sm flex items-center justify-center gap-2 transition-colors shadow-sm">
                <span class="text-base">➕</span>
                <span>Track All Route Pokémon</span>
            </button>

            <div class="ev-warning text-xs">⚠️ Warning: On route list, only modern EVs are used</div>

            <div class="flex items-center justify-between gap-3 bg-slate-900/80 border border-slate-800 rounded-xl px-3 py-2 text-sm">
                <span class="font-extrabold text-slate-300 uppercase text-xs tracking-wider whitespace-nowrap">Filter Game:</span>
                <select id="game-filter-select" onchange="filterGameVersion()" class="w-full h-10 bg-slate-950 border border-slate-700 text-amber-400 font-black rounded-xl px-3 text-sm focus:outline-none focus:border-amber-400">
                    {''.join(game_options)}
                </select>
            </div>

            <div class="space-y-2.5 max-h-[550px] overflow-y-auto pr-1">
                {"".join(game_sections) or '<div class="text-slate-500 text-sm italic py-4 text-center">No encounter tables for this sub-area.</div>'}
            </div>
        </div>
        """

    # 10. Assemble Mobile Template with Toggle Controls
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Stream Mobile Remote</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        const activeTargetData = {active_target_json};
        const pokemonNames = {js_pokemon_array};
        const locationAreas = {js_location_array};

        {SHARED_POKEMON_JS if "SHARED_POKEMON_JS" in globals() else ""}

        window.addEventListener('DOMContentLoaded', () => {{
            if (typeof updateTargetGenView === 'function') updateTargetGenView();
            if (typeof calcExpGap === 'function') calcExpGap();
            initSectionToggles();
        }});
    </script>
    <style>
        .ev-warning {{
            font-family: monospace;
            font-size: 11px;
            color: #fbbf24;
            background: rgba(0, 0, 0, 0.6);
            padding: 4px 8px;
            border-radius: 6px;
            border-left: 3px solid #f59e0b;
            display: block;
        }}
        .toggle-btn-off {{
            opacity: 0.35 !important;
            border-color: #334155 !important;
            color: #64748b !important;
            background: #0f172a !important;
        }}
    </style>
</head>
<body class="bg-slate-950 text-slate-100 font-sans min-h-screen pb-20">

    <!-- Sticky Header: Search Inputs -->
    <header class="sticky top-0 z-40 bg-slate-900/95 backdrop-blur border-b border-slate-800 p-3 space-y-2.5">
        <div class="relative">
            <input id="search-input" oninput="filterPokemon()" onkeyup="filterPokemon()" type="text" placeholder="Search Pokémon..." class="w-full h-11 bg-slate-800 border border-slate-700 rounded-xl px-4 text-base text-white placeholder-slate-400 focus:outline-none focus:border-amber-400 font-medium" autocomplete="off" />
            <div id="search-results" style="display: none;" class="absolute left-0 right-0 mt-1.5 bg-slate-800 border border-slate-700 rounded-2xl shadow-2xl max-h-72 overflow-y-auto z-50"></div>
        </div>
        <div class="relative">
            <input id="location-input" oninput="filterLocations()" onkeyup="filterLocations()" type="text" placeholder="Search Route / Area..." class="w-full h-11 bg-slate-800 border border-slate-700 rounded-xl px-4 text-base text-white placeholder-slate-400 focus:outline-none focus:border-emerald-400 font-medium" autocomplete="off" />
            <div id="location-results" style="display: none;" class="absolute left-0 right-0 mt-1.5 bg-slate-800 border border-slate-700 rounded-2xl shadow-2xl max-h-72 overflow-y-auto z-50"></div>
        </div>
    </header>

    <!-- Sticky Section Toggles Bar -->
    <div class="sticky top-[108px] z-30 bg-slate-950/95 backdrop-blur border-b border-slate-800/80 px-3 py-2 overflow-x-auto">
        <div class="flex items-center gap-2 text-xs font-black whitespace-nowrap min-w-max">
            <button id="btn-sec-target" onclick="toggleSec('sec-target')" class="h-9 px-3 rounded-xl bg-slate-800 border border-slate-700 text-amber-400 transition flex items-center">Target Pokemon View</button>
            <button id="btn-sec-route" onclick="toggleSec('sec-route')" class="h-9 px-3 rounded-xl bg-slate-800 border border-slate-700 text-emerald-400 transition flex items-center">Route</button>
            <button id="btn-sec-counters" onclick="toggleSec('sec-counters')" class="h-9 px-3 rounded-xl bg-slate-800 border border-slate-700 text-indigo-400 transition flex items-center">Hunt List</button>
            <button id="btn-sec-shiny" onclick="toggleSec('sec-shiny')" class="h-9 px-3 rounded-xl bg-slate-800 border border-slate-700 text-amber-300 transition flex items-center">Shiny</button>
            <button id="btn-sec-ev" onclick="toggleSec('sec-ev')" class="h-9 px-3 rounded-xl bg-slate-800 border border-slate-700 text-rose-400 transition flex items-center">EVs</button>
            <button id="btn-sec-party" onclick="toggleSec('sec-party')" class="h-9 px-3 rounded-xl bg-slate-800 border border-slate-700 text-purple-400 transition flex items-center">Party</button>
            <button id="btn-sec-tasks" onclick="toggleSec('sec-tasks')" class="h-9 px-3 rounded-xl bg-slate-800 border border-slate-700 text-sky-400 transition flex items-center">Tasks</button>
            <button id="btn-sec-note" onclick="toggleSec('sec-note')" class="h-9 px-3 rounded-xl bg-slate-800 border border-slate-700 text-slate-300 transition flex items-center">Note</button>
        </div>
    </div>

    <!-- Stacked Sections Container -->
    <main class="p-3 max-w-xl mx-auto space-y-4">

        <!-- 1. Active Target Pokémon Scanner -->
        <section id="sec-target" class="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-4 shadow-lg space-y-3.5">
            <h2 class="text-sm font-black text-white uppercase tracking-wider flex items-center justify-between">
                <span>Active Target Scanner</span>
                <span class="text-xs font-mono text-slate-400 font-bold">OBS Linked</span>
            </h2>
            {target_view}
        </section>

        <!-- 2. Route Encounters Table -->
        <section id="sec-route" class="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-4 shadow-lg space-y-3.5">
            <h2 class="text-sm font-black text-white uppercase tracking-wider flex items-center justify-between">
                <span>Route Encounters</span>
                <span class="text-xs font-mono text-emerald-400 font-bold">Wild Spawns</span>
            </h2>
            {route_view}
        </section>

        <!-- 3. Catch Targets Quick Taps -->
        <section id="sec-counters" class="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-4 shadow-lg space-y-3">
            <h3 class="text-sm uppercase font-black text-slate-300 tracking-wide">Catch Targets (-1)</h3>
            <div class="space-y-2 max-h-64 overflow-y-auto">
                {counter_pills}
            </div>
            <form action="/remote" method="GET" class="space-y-2 pt-1">
                <input type="hidden" name="action" value="set_counters" />
                <input name="counter_list" placeholder="caterpie 3, rattata 2" class="w-full h-11 bg-slate-800 text-sm border border-slate-700 rounded-xl px-3.5 text-white font-medium" />
                <button type="submit" class="w-full h-11 bg-slate-800 hover:bg-slate-700 font-black text-xs py-2 rounded-xl transition">Set Target Batches</button>
            </form>
        </section>

        <!-- 4. Shiny Hunting -->
        <section id="sec-shiny">
            {shiny_card}
        </section>

        <!-- 5. EV Widget -->
        <section id="sec-ev">
            {ev_card_html}
        </section>

        <!-- 6. Party Queue -->
        <section id="sec-party" class="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-4 shadow-lg space-y-3">
            <div class="flex items-center justify-between">
                <h3 class="text-sm uppercase font-black text-slate-300 tracking-wide">Party Queue ({len(team)})</h3>
                <a href="/obs/team" target="_blank" class="text-xs font-bold text-indigo-400 hover:underline">OBS View ↗</a>
            </div>
            <div class="space-y-2 max-h-56 overflow-y-auto pr-1">
                {team_pills}
            </div>
        </section>

        <!-- 7. Bulbapedia Walkthrough & Task Queue -->
        <section id="sec-tasks" class="space-y-3.5">
            <div class="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-4 space-y-3">
                <div class="flex justify-between items-center">
                    <span class="text-xs uppercase font-black text-slate-400 tracking-wide">Bulbapedia Walkthrough</span>
                    <span class="text-xs font-mono text-indigo-400 font-black">TASK LOADER</span>
                </div>
                <div class="grid grid-cols-1 gap-2.5">
                    <div>
                        <label class="text-xs text-slate-300 font-extrabold uppercase block mb-1">1. Select Game:</label>
                        <select id="walkthrough-game-select" onchange="onWalkthroughGameChange()" class="w-full h-11 bg-slate-950/80 border border-slate-800 text-slate-200 font-bold rounded-xl px-3 text-sm focus:outline-none focus:border-indigo-500">
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
                    <div>
                        <label class="text-xs text-slate-300 font-extrabold uppercase block mb-1">2. Select Chapter / Part:</label>
                        <select id="walkthrough-part-select" onchange="loadSelectedPartTasks()" disabled class="w-full h-11 bg-slate-950/80 border border-slate-800 text-slate-200 font-bold rounded-xl px-3 text-sm focus:outline-none focus:border-emerald-500 disabled:opacity-40">
                            <option value="">-- Select Game First --</option>
                        </select>
                    </div>
                </div>
            </div>

            <div class="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-4 space-y-3">
                <div class="flex justify-between items-center mb-1">
                    <span id="task-progress-display" class="text-xs uppercase font-black text-slate-400">{task_count_str}</span>
                    <span class="text-xs font-mono text-emerald-400 font-black">CURRENT TASK</span>
                </div>
                <div id="task-name-display" class="text-sm font-black text-white mb-2 bg-slate-950/80 p-3 rounded-xl border border-slate-800">{active_task}</div>
                <div class="flex gap-2.5">
                    <button type="button" onclick="navigateTask('prev')" class="flex-1 h-12 bg-slate-800 hover:bg-slate-700 text-center text-sm font-black rounded-xl transition active:scale-95 text-slate-200">◀ Prev</button>
                    <button type="button" onclick="navigateTask('next')" class="flex-1 h-12 bg-indigo-600 hover:bg-indigo-500 text-center text-sm font-black rounded-xl transition active:scale-95 text-white">Next ▶</button>
                </div>
                <form action="/remote" method="GET" class="space-y-2 pt-1">
                    <input type="hidden" name="action" value="set_tasks" />
                    <input name="tasks" placeholder="Task 1, Task 2, Task 3..." class="w-full h-11 bg-slate-800 text-sm border border-slate-700 rounded-xl px-3 text-white font-medium" />
                    <button type="submit" class="w-full h-11 bg-slate-800 hover:bg-slate-700 font-black text-xs py-2 rounded-xl transition">Update Tasks</button>
                </form>
            </div>
        </section>

        <!-- 8. Video Note -->
        <section id="sec-note" class="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-4 shadow-lg space-y-2.5">
            <h3 class="text-sm uppercase font-black text-slate-300 tracking-wide">Video Message Note</h3>
            <form action="/videomessage" method="GET" class="space-y-2">
                <textarea name="notes" placeholder="Update video note..." class="w-full bg-slate-800 text-sm border border-slate-700 rounded-xl p-3 text-white h-20 font-medium"></textarea>
                <button type="submit" class="w-full h-11 bg-indigo-600 hover:bg-indigo-500 font-black text-xs py-2 rounded-xl transition">Overwrite Note</button>
            </form>
        </section>

    </main>

    <!-- Client-side Section Toggle Logic -->
    <script>
        const remoteSections = [
            'sec-target', 'sec-route', 'sec-counters', 'sec-shiny',
            'sec-ev', 'sec-party', 'sec-tasks', 'sec-note'
        ];

        function applySecDisplay(secId, visible) {{
            const el = document.getElementById(secId);
            const btn = document.getElementById('btn-' + secId);
            if (el) el.style.display = visible ? '' : 'none';
            if (btn) {{
                if (visible) btn.classList.remove('toggle-btn-off');
                else btn.classList.add('toggle-btn-off');
            }}
        }}

        function toggleSec(secId) {{
            const current = localStorage.getItem('mobile_show_' + secId) !== 'false';
            const next = !current;
            localStorage.setItem('mobile_show_' + secId, next);
            applySecDisplay(secId, next);
        }}

        function initSectionToggles() {{
            remoteSections.forEach(secId => {{
                const saved = localStorage.getItem('mobile_show_' + secId);
                const isVisible = saved !== 'false';
                applySecDisplay(secId, isVisible);
            }});
        }}
    </script>
</body>
</html>"""
    return html, ("Content-Type", "text/html")






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