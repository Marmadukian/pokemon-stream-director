import os
import json
from datetime import datetime
from urllib.parse import quote_plus, unquote_plus
import pokebase as pb

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

all_location_areas = []
all_pkmn_collection = []

DEFAULT_EV_STATE = {
    "hp": 0,
    "attack": 0,
    "defense": 0,
    "special-attack": 0,
    "special-defense": 0,
    "speed": 0,
}
DEFAULT_CATCH_STATE = {
    "hp": "100",
    "lvl": "50",
    "status": "1", 
    "ball": "poke", 
    "odds": "--%", 
    "target": "None"
}


def load_ev_state():
    state = DEFAULT_EV_STATE.copy()
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                raw = data.get("ev_state", {})
                
                # Check if file has legacy schema (e.g., 'kills' instead of stat keys)
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
    # Ensure only clean integer values for the 6 stats are saved
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
            pass
    data["catch_state"] = state
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

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

SHARED_POKEMON_JS = r"""
// Global mappings & constants
const vgToGenMap = {
    'red-blue': 'gen-1',
    'yellow': 'gen-1',
    'gold-silver': 'gen-2',
    'crystal': 'gen-2',
    'ruby-sapphire': 'gen-3',
    'emerald': 'gen-3',
    'firered-leafgreen': 'gen-3',
    'colosseum': 'gen-3',
    'xd': 'gen-3',
    'diamond-pearl': 'gen-4',
    'platinum': 'gen-4',
    'heartgold-soulsilver': 'gen-4',
    'black-white': 'gen-5',
    'black-2-white-2': 'gen-5',
    'x-y': 'gen-6',
    'omega-ruby-alpha-sapphire': 'gen-6',
    'sun-moon': 'gen-7',
    'ultra-sun-ultra-moon': 'gen-7',
    'lets-go-pikachu-lets-go-eevee': 'gen-7',
    'sword-shield': 'gen-8',
    'brilliant-diamond-and-shining-pearl': 'gen-8',
    'brilliant-diamond-shining-pearl': 'gen-8',
    'legends-arceus': 'gen-8',
    'scarlet-violet': 'gen-9'
};

const BASE_TYPE_CHART = {
    normal:   { rock: 0.5, ghost: 0, steel: 0.5 },
    fire:     { fire: 0.5, water: 0.5, grass: 2, ice: 2, bug: 2, rock: 0.5, dragon: 0.5, steel: 2 },
    water:    { fire: 2, water: 0.5, grass: 0.5, ground: 2, rock: 2, dragon: 0.5 },
    electric: { water: 2, electric: 0.5, grass: 0.5, ground: 0, flying: 2, dragon: 0.5 },
    grass:    { fire: 0.5, water: 2, grass: 0.5, poison: 0.5, ground: 2, flying: 0.5, bug: 0.5, rock: 2, dragon: 0.5, steel: 0.5 },
    ice:      { fire: 0.5, water: 0.5, grass: 2, ice: 0.5, ground: 2, flying: 2, dragon: 2, steel: 0.5 },
    fighting: { normal: 2, ice: 2, poison: 0.5, flying: 0.5, psychic: 0.5, bug: 0.5, rock: 2, ghost: 0, dark: 2, steel: 2, fairy: 0.5 },
    poison:   { grass: 2, poison: 0.5, ground: 0.5, rock: 0.5, ghost: 0.5, steel: 0, fairy: 2 },
    ground:   { fire: 2, electric: 2, grass: 0.5, poison: 2, flying: 0, bug: 0.5, rock: 2, steel: 2 },
    flying:   { electric: 0.5, grass: 2, fighting: 2, bug: 2, rock: 0.5, steel: 0.5 },
    psychic:  { fighting: 2, poison: 2, psychic: 0.5, dark: 0, steel: 0.5 },
    bug:      { fire: 0.5, grass: 2, fighting: 0.5, poison: 0.5, flying: 0.5, psychic: 2, ghost: 0.5, dark: 2, steel: 0.5, fairy: 0.5 },
    rock:     { fire: 2, ice: 2, fighting: 0.5, ground: 0.5, flying: 2, bug: 2, steel: 0.5 },
    ghost:    { normal: 0, psychic: 2, ghost: 2, dark: 0.5, steel: 0.5 },
    dragon:   { dragon: 2, steel: 0.5, fairy: 0 },
    steel:    { fire: 0.5, water: 0.5, electric: 0.5, ice: 2, rock: 2, steel: 0.5, fairy: 2 },
    dark:     { fighting: 0.5, psychic: 2, ghost: 2, dark: 0.5, fairy: 0.5 },
    fairy:    { fire: 0.5, fighting: 2, poison: 0.5, dragon: 2, dark: 2, steel: 0.5 }
};

// 1. Search Autocomplete (Pokemon)
function filterPokemon() {
    const input = document.getElementById('search-input');
    const box = document.getElementById('search-results');
    if (!input || !box || typeof pokemonNames === 'undefined') return;

    const val = input.value.toLowerCase().trim();
    if (!val || val.length < 2) {
        box.style.display = 'none';
        box.innerHTML = '';
        return;
    }
    const matches = pokemonNames.filter(n => n.toLowerCase().includes(val)).slice(0, 10);
    if (matches.length === 0) {
        box.innerHTML = '<div class="px-4 py-3 text-sm text-slate-400 italic">No Pokémon found.</div>';
        box.style.display = 'block';
        return;
    }
    box.innerHTML = '';
    const endpoint = window.location.pathname.includes('/remote') ? '/remote' : '/';
    matches.forEach(m => {
        const item = document.createElement('div');
        item.className = "px-4 py-2 hover:bg-slate-700/80 flex items-center justify-between border-b border-slate-700/40 last:border-none transition";
        item.innerHTML = `
            <span class="font-bold capitalize text-slate-200 text-sm">${m}</span>
            <div class="flex gap-1.5">
                <a href="${endpoint}?action=set_target&name=${encodeURIComponent(m)}" onclick="document.getElementById('search-input').value='';" class="text-xs bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold px-2 py-0.5 rounded">Target</a>
                <a href="${endpoint}?action=team_add&name=${encodeURIComponent(m)}" onclick="document.getElementById('search-input').value='';" class="text-xs bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-2 py-0.5 rounded">+ Party</a>
            </div>
        `;
        box.appendChild(item);
    });
    box.style.display = 'block';
}

function filterRouteVersion() {
            const select = document.getElementById('route-version-filter');
            if (!select || !select.value) return;
            const selected = select.value.toLowerCase().trim();
            
            const cards = document.querySelectorAll('.game-version-card');
            cards.forEach(card => {
                const cardVer = (card.getAttribute('data-version') || '').toLowerCase().trim();
                if (cardVer === selected) {
                    card.style.setProperty('display', 'block', 'important');
                } else {
                    card.style.setProperty('display', 'none', 'important');
                }
            });
        }


// 2. Search Autocomplete (Locations)
function filterLocations() {
    const input = document.getElementById('location-input');
    const box = document.getElementById('location-results');
    if (!input || !box || typeof locationAreas === 'undefined') return;

    const val = input.value.toLowerCase().trim();
    if (!val || val.length < 2) {
        box.style.display = 'none';
        box.innerHTML = '';
        return;
    }
    const matches = locationAreas.filter(loc => loc.name.toLowerCase().includes(val)).slice(0, 10);
    if (matches.length === 0) {
        box.innerHTML = '<div class="px-4 py-3 text-sm text-slate-400 italic">No locations found.</div>';
        box.style.display = 'block';
        return;
    }
    box.innerHTML = '';
    const endpoint = window.location.pathname.includes('/remote') ? '/remote' : '/';
    matches.forEach(loc => {
        const item = document.createElement('div');
        item.className = "px-4 py-2 hover:bg-slate-700/80 flex items-center justify-between border-b border-slate-700/40 last:border-none transition";
        item.innerHTML = `
            <span class="font-bold text-slate-200 text-xs">${loc.name}</span>
            <div class="flex gap-1.5">
                <a href="${endpoint}?action=set_location&slug=${encodeURIComponent(loc.slug)}" onclick="document.getElementById('location-input').value='';" class="text-xs bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold px-2 py-0.5 rounded">View Route</a>
            </div>
        `;
        box.appendChild(item);
    });
    box.style.display = 'block';
}

// 3. Route Filter by Version
function filterGameVersion() {
    const select = document.getElementById('game-filter-select');
    if (!select) return;
    const chosen = select.value;
    const cards = document.querySelectorAll('.game-version-card');

    cards.forEach(card => {
        if (chosen === 'ALL' || card.getAttribute('data-version') === chosen) {
            card.style.display = 'block';
        } else {
            card.style.display = 'none';
        }
    });
}

// 4. Historical Matchup Calculations
function calculateHistoricalMatchups(types, gen) {
    const ALL_TYPES = Object.keys(BASE_TYPE_CHART);
    const validAttackers = ALL_TYPES.filter(t => {
        if (gen === 'gen-1' && (t === 'dark' || t === 'steel' || t === 'fairy')) return false;
        if (['gen-2', 'gen-3', 'gen-4', 'gen-5'].includes(gen) && t === 'fairy') return false;
        return true;
    });

    let multipliers = {};
    validAttackers.forEach(t => multipliers[t] = 1.0);

    types.forEach(defType => {
        const def = defType.toLowerCase();
        validAttackers.forEach(atk => {
            let eff = (BASE_TYPE_CHART[atk] && BASE_TYPE_CHART[atk][def] !== undefined) ? BASE_TYPE_CHART[atk][def] : 1.0;

            if (gen === 'gen-1') {
                if (atk === 'ghost' && def === 'psychic') eff = 0.0;
                else if (atk === 'poison' && def === 'bug') eff = 2.0;
                else if (atk === 'bug' && def === 'poison') eff = 2.0;
                else if (atk === 'ice' && def === 'fire') eff = 1.0;
            }

            if (['gen-2', 'gen-3', 'gen-4', 'gen-5'].includes(gen)) {
                if ((atk === 'dark' || atk === 'ghost') && def === 'steel') eff = 0.5;
            }

            multipliers[atk] = multipliers[atk] * eff;
        });
    });

    return multipliers;
}

// 5. Historical Sprite Getter
function getSpriteForGen(targetId, gen) {
    if (!targetId || targetId <= 0) return '';
    switch (gen) {
        case 'gen-1':
            return `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-i/red-blue/${targetId}.png`;
        case 'gen-2':
            return `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-ii/crystal/${targetId}.png`;
        case 'gen-3':
            return `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-iii/emerald/${targetId}.png`;
        case 'gen-4':
            return `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-iv/platinum/${targetId}.png`;
        case 'gen-5':
            return `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-v/black-white/${targetId}.png`;
        default:
            return `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/${targetId}.png`;
    }
}

// 6. EXP Calculations
function getExpForLevel(growthRate, lvl) {
    if (lvl <= 1) return 0;
    if (lvl > 100) lvl = 100;
    const n = lvl;

    switch (growthRate) {
        case "fast":
            return Math.floor(0.8 * Math.pow(n, 3));
        case "medium-fast":
        case "medium":
            return Math.floor(Math.pow(n, 3));
        case "medium-slow":
            return Math.max(0, Math.floor(1.2 * Math.pow(n, 3) - 15 * Math.pow(n, 2) + 100 * n - 140));
        case "slow":
            return Math.floor(1.25 * Math.pow(n, 3));
        case "erratic":
            if (n <= 50) return Math.floor((Math.pow(n, 3) * (100 - n)) / 50);
            if (n <= 68) return Math.floor((Math.pow(n, 3) * (150 - n)) / 100);
            if (n <= 98) return Math.floor((Math.pow(n, 3) * Math.floor((1911 - 10 * n) / 3)) / 500);
            return Math.floor((Math.pow(n, 3) * (160 - n)) / 100);
        case "fluctuating":
            if (n <= 15) return Math.floor(Math.pow(n, 3) * (Math.floor((n + 1) / 3) + 24) / 50);
            if (n <= 36) return Math.floor(Math.pow(n, 3) * (n + 14) / 50);
            return Math.floor(Math.pow(n, 3) * (Math.floor(n / 2) + 32) / 50);
        default:
            return Math.floor(Math.pow(n, 3));
    }
}

function calcExpGap() {
    const rateElem = document.getElementById('target-growth-rate');
    const rate = rateElem ? rateElem.value : 'medium-fast';
    const fromLvl = parseInt(document.getElementById('exp-from')?.value) || 1;
    const toLvl = parseInt(document.getElementById('exp-to')?.value) || 1;
    const expPerKill = parseInt(document.getElementById('exp-per-kill')?.value) || 1;

    const outElem = document.getElementById('exp-output');
    const battlesElem = document.getElementById('grind-battles');
    const timeElem = document.getElementById('grind-time');

    if (!outElem) return;

    if (toLvl <= fromLvl) {
        outElem.innerText = "0 EXP";
        if (battlesElem) battlesElem.innerText = "0 kills";
        if (timeElem) timeElem.innerText = "~0m";
        return;
    }

    const expFrom = getExpForLevel(rate, fromLvl);
    const expTo = getExpForLevel(rate, toLvl);
    const needed = Math.max(0, expTo - expFrom);

    outElem.innerText = needed.toLocaleString() + " EXP";

    const kills = Math.ceil(needed / Math.max(1, expPerKill));
    const totalSeconds = kills * 15;
    const hours = Math.floor(totalSeconds / 3600);
    const mins = Math.ceil((totalSeconds % 3600) / 60);

    if (battlesElem) battlesElem.innerText = kills.toLocaleString() + " kills";
    if (timeElem) timeElem.innerText = (hours > 0) ? `~${hours}h ${mins}m` : `~${mins}m`;
}

function syncCatchState(hp, lvl, status, ball, odds) {
            const targetName = (window.activeTargetData && activeTargetData.name) ? activeTargetData.name : "None";
            
            fetch(`/sync_catch?hp=${hp}&lvl=${lvl}&status=${status}&ball=${ball}&odds=${encodeURIComponent(odds)}&target=${encodeURIComponent(targetName)}`)
                .catch(err => console.log("Background sync failed", err));
        }

function calculateCatchOdds() {
            if (!activeTargetData || !activeTargetData.catch_rate) return;
            
            const catchRate = activeTargetData.catch_rate;
            const hpPct = parseInt(document.getElementById('catch-hp-slider').value) || 100;
            const lvl = parseInt(document.getElementById('catch-lvl-input').value) || 50;
            const statusVal = parseFloat(document.getElementById('catch-status-select').value) || 1;
            const ball = document.getElementById('catch-ball-select').value;
            
            // Extract Base HP from active target data (fallback to 70 if missing)
            // activeTargetData.stats usually contains objects or a map like {hp: 90, attack: 90, ...}
            let baseHp = 70;
            if (activeTargetData.stats) {
                if (typeof activeTargetData.stats === 'object' && !Array.isArray(activeTargetData.stats)) {
                    baseHp = activeTargetData.stats.hp || activeTargetData.stats.HP || 70;
                } else if (Array.isArray(activeTargetData.stats)) {
                    const hpStatObj = activeTargetData.stats.find(s => s.stat === 'hp' || s.name === 'hp');
                    if (hpStatObj) baseHp = hpStatObj.base || hpStatObj.value || 70;
                }
            }

            // Calculate exact Max HP (0 EVs, neutral nature)
            const maxHp = Math.floor(((2 * baseHp) * lvl) / 100) + lvl + 10;
            const currentHp = Math.max(1, Math.floor((maxHp * hpPct) / 100));

            // Update UI text trackers
            document.getElementById('catch-hp-display').innerText = `${currentHp}/${maxHp} HP (${hpPct}%)`;
            document.getElementById('catch-lvl-display').innerText = lvl;

            // Master Ball shortcut
            if (ball === 'master') {
                document.getElementById('catch-odds-display').innerText = "100%";
                syncCatchState(hpPct, lvl, statusVal, ball, "100%");
                return;
            }

            const genSelect = document.getElementById('target-gen-select');
            const selectedGen = genSelect ? genSelect.value : 'modern';
            const isGen1 = ['red-blue', 'yellow'].includes(selectedGen);

            let chance = 0;

            if (isGen1) {
                // --- Gen 1 Formula ---
                let B = 255;
                let ballDivisor = 12;
                if (ball === 'great') { B = 200; ballDivisor = 8; }
                else if (ball === 'ultra') { B = 150; ballDivisor = 12; }

                let statusMod = 0;
                if (statusVal >= 2.5) statusMod = 25;
                else if (statusVal >= 1.5) statusMod = 12;
                
                const pStatus = statusMod / 256;
                const pCatchRate = Math.min(catchRate, B) / (B + 1);

                // Gen 1 HP check uses MaxHP vs CurrentHP ratio check under the hood
                let f = Math.floor((maxHp * 255) / ballDivisor);
                let hpFactor = Math.floor(currentHp / 4);
                if (hpFactor < 1) hpFactor = 1;
                
                f = Math.min(255, Math.floor(f / hpFactor));
                const pHp = (f + 1) / 256;

                chance = (pStatus + ((1 - pStatus) * pCatchRate * pHp)) * 100;
            } else {
                // --- Modern Formula ---
                let ballMod = 1.0;
                if (ball === 'great') ballMod = 1.5;
                else if (ball === 'ultra') ballMod = 2.0;

                // Modern formula uses actual MaxHP and CurrentHP ratios: ((3 * MaxHP - 2 * CurrentHP) * CatchRate * Ball) / (3 * MaxHP)
                let a = (((3 * maxHp) - (2 * currentHp)) * catchRate * ballMod) / (3 * maxHp);
                a = a * statusVal;

                if (a >= 255) {
                    chance = 100;
                } else {
                    chance = Math.pow(a / 255, 0.75) * 100;
                }
            }

            chance = Math.min(100, Math.max(0.1, chance));
            const oddsStr = chance.toFixed(1) + "%";
            document.getElementById('catch-odds-display').innerText = oddsStr;

            syncCatchState(hpPct, lvl, statusVal, ball, oddsStr);
        }
// 7. Target View Renderer & Game/Gen Switcher
function updateTargetGenView() {
    if (typeof activeTargetData === 'undefined' || !activeTargetData || !activeTargetData.id) return;

    const select = document.getElementById('target-gen-select');
    const chosenGame = select ? select.value : 'modern';
    const chosenGen = vgToGenMap[chosenGame] || 'gen-modern';
    const targetId = activeTargetData.id;

    // A. Update Sprite
    const img = document.getElementById('target-sprite-img');
    if (img) img.src = getSpriteForGen(targetId, chosenGen);

    // B. Resolve Active Types
    let activeTypes = [...(activeTargetData.types || [])];
    const pastTypesMap = activeTargetData.past_types || {};
    if (chosenGen === 'gen-1' && pastTypesMap['generation-i']) {
        activeTypes = pastTypesMap['generation-i'];
    } else if (['gen-1','gen-2','gen-3','gen-4','gen-5'].includes(chosenGen) && pastTypesMap['generation-v']) {
        activeTypes = pastTypesMap['generation-v'];
    }

    const typeContainer = document.getElementById('target-type-badges');
    if (typeContainer) {
        typeContainer.innerHTML = activeTypes.map(t => 
            `<span class="text-[10px] font-bold px-1.5 py-0.5 rounded bg-indigo-500/20 border border-indigo-500/30 text-indigo-300">${t}</span>`
        ).join('');
    }

    // C. Resolve Defensive Matchups
    let weaknesses = {};
    let resistances = {};
    let immunities = [];

    if (chosenGame === 'modern') {
        Object.entries(activeTargetData.weaknesses || {}).forEach(([k, v]) => {
            weaknesses[k.charAt(0).toUpperCase() + k.slice(1).toLowerCase()] = v;
        });
        Object.entries(activeTargetData.resistances || {}).forEach(([k, v]) => {
            resistances[k.charAt(0).toUpperCase() + k.slice(1).toLowerCase()] = v;
        });
        immunities = (activeTargetData.immunities || []).map(t => t.charAt(0).toUpperCase() + t.slice(1).toLowerCase());
    } else {
        const mults = calculateHistoricalMatchups(activeTypes, chosenGen);
        Object.entries(mults).forEach(([k, v]) => {
            const title = k.charAt(0).toUpperCase() + k.slice(1).toLowerCase();
            if (v > 1.0) weaknesses[title] = v;
            else if (v > 0.0 && v < 1.0) resistances[title] = v;
            else if (v === 0.0) immunities.push(title);
        });
    }

    const weakEl = document.getElementById('target-weakness-tags');
    const resEl = document.getElementById('target-resistance-tags');
    const immEl = document.getElementById('target-immunity-tags');

    if (weakEl) {
        const tags = Object.entries(weaknesses).map(([k, v]) => 
            `<span class="px-1.5 py-0.5 rounded text-[11px] font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30">${k} ${v}x</span>`
        ).join('');
        weakEl.innerHTML = tags || '<span class="text-xs text-slate-500 italic">None</span>';
    }

    if (resEl) {
        const tags = Object.entries(resistances).map(([k, v]) => 
            `<span class="px-1.5 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">${k} ${v}x</span>`
        ).join('');
        resEl.innerHTML = tags || '<span class="text-xs text-slate-500 italic">None</span>';
    }

    if (immEl) {
        const tags = immunities.map(t => 
            `<span class="px-1.5 py-0.5 rounded text-[11px] font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/30">${t} 0x</span>`
        ).join('');
        immEl.innerHTML = tags || '<span class="text-xs text-slate-500 italic">None</span>';
    }

    // D. Filter Move Rows
    const moveRows = document.querySelectorAll('.target-move-row');
    const movesContainer = document.getElementById('moves-container');
    const seenMovesInGen = new Set();
    let visibleCount = 0;

    moveRows.forEach(row => {
        let rowVg = (row.getAttribute('data-vg') || '').toLowerCase().trim().replace(/_/g, '-');
        if (rowVg === 'brilliant-diamond-shining-pearl') rowVg = 'brilliant-diamond-and-shining-pearl';
        const moveName = (row.getAttribute('data-move') || '').toLowerCase().trim();

        let isMatch = (chosenGame === 'modern') ||
                      (chosenGame === 'colosseum' && (rowVg === 'colosseum' || rowVg === 'xd')) ||
                      (chosenGame === 'brilliant-diamond-and-shining-pearl' && (rowVg === 'brilliant-diamond-and-shining-pearl' || rowVg === 'brilliant-diamond-shining-pearl')) ||
                      (rowVg === chosenGame);

        if (isMatch) {
            if (!seenMovesInGen.has(moveName)) {
                seenMovesInGen.add(moveName);
                row.style.display = 'flex';
                visibleCount++;
            } else {
                row.style.display = 'none';
            }
        } else {
            row.style.display = 'none';
        }
    });

    // E. Render Base Stats (Gen 1 merged Special)
    const rawStats = activeTargetData.stats || {};
    const statsContainer = document.getElementById('target-stats-container');
    const bstBadge = document.getElementById('target-bst-badge');

    if (statsContainer && Object.keys(rawStats).length > 0) {
        let displayStats = {};
        let calculatedBst = 0;

        if (chosenGen === 'gen-1') {
            displayStats['hp'] = rawStats['hp'] || 0;
            displayStats['attack'] = rawStats['attack'] || 0;
            displayStats['defense'] = rawStats['defense'] || 0;
            displayStats['special'] = rawStats['special-attack'] !== undefined ? rawStats['special-attack'] : (rawStats['special-defense'] || 0);
            displayStats['speed'] = rawStats['speed'] || 0;
        } else {
            displayStats = { ...rawStats };
        }

        let statBarsHtml = '';
        Object.entries(displayStats).forEach(([statName, val]) => {
            calculatedBst += val;
            const pct = Math.min(100, Math.round((val / 255) * 100));
            statBarsHtml += `
                <div>
                    <div class="flex justify-between text-[11px] font-medium mb-1">
                        <span class="text-slate-400 uppercase">${statName.replace('-', ' ')}</span>
                        <span class="font-mono text-slate-200">${val}</span>
                    </div>
                    <div class="w-full bg-slate-700/70 h-1.5 rounded-full overflow-hidden">
                        <div class="bg-amber-400 h-full rounded-full" style="width: ${pct}%"></div>
                    </div>
                </div>
            `;
        });

        statsContainer.innerHTML = statBarsHtml;
        if (bstBadge) bstBadge.innerText = `BST ${calculatedBst}`;
    }

    let emptyMsg = document.getElementById('moves-empty-notice');
    if (visibleCount === 0) {
        if (!emptyMsg && movesContainer) {
            emptyMsg = document.createElement('div');
            emptyMsg.id = 'moves-empty-notice';
            emptyMsg.className = 'text-xs text-slate-500 italic py-2 text-center';
            emptyMsg.innerText = 'No moves learned in this game.';
            movesContainer.appendChild(emptyMsg);
        } else if (emptyMsg) {
            emptyMsg.style.display = 'block';
        }
    } else if (emptyMsg) {
        emptyMsg.style.display = 'none';
    }

    if (typeof calculateCatchOdds === 'function') {
        calculateCatchOdds();
    }
}

window.addEventListener('DOMContentLoaded', () => {
            const genSelect = document.getElementById('target-gen-select');
            if (genSelect) {
                genSelect.addEventListener('change', calculateCatchOdds);
            }
            // Fire immediately on load
            setTimeout(calculateCatchOdds, 200);
        });
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
    
    if os.path.exists(PKMN_NAMES_CACHE):
        try:
            with open(PKMN_NAMES_CACHE, "r", encoding="utf-8") as f:
                all_pkmn_collection = json.load(f)
                if all_pkmn_collection:
                    print(f"[POKEMON] Loaded {len(all_pkmn_collection)} names from cache.")
                    return all_pkmn_collection
        except Exception:
            pass

    print("[POKEMON] Fetching names via pokebase...")
    try:
        # pokebase yields name strings directly
        resource_list = pb.APIResourceList('pokemon')
        all_pkmn_collection = list(resource_list.names)
        
        if all_pkmn_collection:
            with open(PKMN_NAMES_CACHE, "w", encoding="utf-8") as f:
                json.dump(all_pkmn_collection, f)
            print(f"[POKEMON] Cached {len(all_pkmn_collection)} names.")
    except Exception as e:
        print(f"[POKEMON ERROR] {e}")

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

def load_all_location_areas():
    global all_location_areas
    if all_location_areas:
        return all_location_areas

    # 1. Read local cache if present
    if os.path.exists(ROUTES_CACHE_FILE):
        try:
            with open(ROUTES_CACHE_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
                if cached:
                    all_location_areas = cached
                    return all_location_areas
        except Exception:
            pass

    # 2. Pure pokebase fetch
    try:
        resource = pb.APIResourceList("location-area")
        # resource.names is a generator/list of slug strings: ['kanto-route-1-area', ...]
        all_location_areas = [
            {"slug": slug, "name": format_area_name(slug)}
            for slug in resource.names
        ]

        if all_location_areas:
            with open(ROUTES_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(all_location_areas, f, indent=2)
    except Exception as e:
        print(f"[POKEMON] Error loading locations: {e}")

    return all_location_areas

def parse_location_encounters_by_game(location_area_data):
  """Groups route encounters by game version, deduplicating species per version

  and aggregating their encounter methods and levels.
  """
  games = {}

  for p_enc in location_area_data.get("pokemon_encounters", []):
    p_name = p_enc.get("pokemon", {}).get("name", "").title()

    for v_detail in p_enc.get("version_details", []):
      version_name = (
          v_detail.get("version", {}).get("name", "unknown").replace("-", " ")
      )

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
        area = pb.location_area(slug)
    except Exception as e:
        print(f"[ROUTE ERROR] Failed to fetch area '{slug}': {e}")
        return None

    encounters_by_pokemon = []

    for p_enc in getattr(area, "pokemon_encounters", []):
        p_name = p_enc.pokemon.name
        details_list = []

        for v_det in getattr(p_enc, "version_details", []):
            version_name = v_det.version.name.replace("-", " ").title()
            for enc_det in getattr(v_det, "encounter_details", []):
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

        encounters_by_pokemon.append({
            "name": p_name.title(),
            "slug": p_name,
            "details": details_list
        })

    return {
        "slug": slug,
        "name": format_area_name(slug),
        "total_species": len(encounters_by_pokemon),
        "pokemon": encounters_by_pokemon
    }


# --- PokéAPI Comprehensive Lookup ---

def fetch_complete_pokemon_info(name):
  clean_name = name.lower().strip()
  try:
    p = pb.pokemon(clean_name)
    s = pb.pokemon_species(clean_name)
  except Exception as e:
    print(f"Error fetching PokéAPI data for {name}: {e}")
    return None

  # Base Stats
  stats = {}
  bst = 0
  for stat in p.stats:
    s_name = stat.stat.name
    val = stat.base_stat
    stats[s_name] = val
    bst += val

  # Current Types & Weaknesses
  types = [t.type.name for t in p.types]
  damage_multipliers = {}
  past_damage_relations = {}

  for t_entry in p.types:
    t_name = t_entry.type.name
    t_data = pb.type_(t_name)

    # Current Damage Relations
    for dmg in t_data.damage_relations.double_damage_from:
      damage_multipliers[dmg.name] = (
          damage_multipliers.get(dmg.name, 1.0) * 2.0
      )
    for dmg in t_data.damage_relations.half_damage_from:
      damage_multipliers[dmg.name] = (
          damage_multipliers.get(dmg.name, 1.0) * 0.5
      )
    for dmg in t_data.damage_relations.no_damage_from:
      damage_multipliers[dmg.name] = 0.0

    # Historical Damage Relations from PokéAPI
    for past_rel in getattr(t_data, "past_damage_relations", []):
      gen_slug = getattr(
          past_rel.generation, "name", str(past_rel.generation)
      ).lower()
      if gen_slug not in past_damage_relations:
        past_damage_relations[gen_slug] = {}

      rel = getattr(past_rel, "damage_relations", past_rel)
      past_damage_relations[gen_slug][t_name] = {
          "double_damage_from": [
              d.name for d in getattr(rel, "double_damage_from", [])
          ],
          "half_damage_from": [
              h.name for h in getattr(rel, "half_damage_from", [])
          ],
          "no_damage_from": [n.name for n in getattr(rel, "no_damage_from", [])],
      }

  weaknesses = {k: v for k, v in damage_multipliers.items() if v > 1.0}
  resistances = {k: v for k, v in damage_multipliers.items() if 0.0 < v < 1.0}
  immunities = [k for k, v in damage_multipliers.items() if v == 0.0]

  # Base Stats & EV Yields
  ev_yield = {}

  for stat in getattr(p, "stats", []):
    # Extract stat name
    s_name = ""
    if hasattr(stat, "stat"):
      s_name = getattr(stat.stat, "name", str(stat.stat))
    elif isinstance(stat, dict):
      s_name = stat.get("stat", {}).get("name", "")

    # Extract base stat value
    val = getattr(stat, "base_stat", 0)
    if isinstance(stat, dict):
      val = stat.get("base_stat", 0)

    # Extract EV effort yield
    effort = getattr(stat, "effort", 0)
    if isinstance(stat, dict):
      effort = stat.get("effort", 0)
    if s_name:
      stats[s_name] = int(val)
      bst += int(val)
      if int(effort) > 0:
        ev_yield[s_name] = int(effort)

  # Historical Pokémon Typings (e.g. Clefairy Normal -> Fairy, Magnemite Electric -> Electric/Steel)
  past_types = {}
  for past_t in getattr(p, "past_types", []):
    gen_slug = getattr(
        past_t.generation, "name", str(past_t.generation)
    ).lower()
    past_types[gen_slug] = [
        getattr(entry.type, "name", str(entry.type)).title()
        for entry in getattr(past_t, "types", [])
    ]

  # Evolution Chain (Levels / Methods)
  evo_details = []
  try:
    evo_chain_res = s.evolution_chain
    if hasattr(evo_chain_res, "id"):
      chain_id = evo_chain_res.id
    elif hasattr(evo_chain_res, "url"):
      chain_id = int(evo_chain_res.url.strip("/").split("/")[-1])
    else:
      chain_id = int(str(evo_chain_res).strip("/").split("/")[-1])

    chain_data = pb.evolution_chain(chain_id)

    def parse_chain(node):
      species_name = node.species.name.title()
      evolves_to = getattr(node, "evolves_to", [])
      for evo in evolves_to:
        target_name = evo.species.name.title()
        methods = []
        evo_details_list = getattr(evo, "evolution_details", [])

        for det in evo_details_list:
          min_lvl = getattr(det, "min_level", None)
          if min_lvl:
            methods.append(f"Level {min_lvl}")

          item = getattr(det, "item", None)
          if item:
            item_name = (
                getattr(item, "name", str(item)).replace("-", " ").title()
            )
            methods.append(f"Use {item_name}")

          trigger = getattr(det, "trigger", None)
          trigger_name = getattr(trigger, "name", "") if trigger else ""
          if trigger_name == "trade":
            held = getattr(det, "held_item", None)
            held_name = f" holding {held.name.title()}" if held else ""
            methods.append(f"Trade{held_name}")

          min_happy = getattr(det, "min_happiness", None)
          if min_happy:
            methods.append(f"Happiness {min_happy}")

          time_of_day = getattr(det, "time_of_day", "")
          if time_of_day:
            methods.append("Daytime" if time_of_day == "day" else "Night")

        method_str = ", ".join(methods) if methods else "Level up / Special"
        evo_details.append(f"{species_name} ➔ {target_name} ({method_str})")
        parse_chain(evo)

    parse_chain(chain_data.chain)
    if not evo_details:
      evo_details = ["Does not evolve"]
  except Exception as e:
    print(f"[EVO ERROR] Failed parsing evolution chain: {e}")
    evo_details = ["No evolution data available"]

  # TM Moves
  tm_moves = []
  for m in getattr(p, "moves", []):
    m_name = getattr(m.move, "name", "").replace("-", " ").title()
    for vgd in getattr(m, "version_group_details", []):
      method = getattr(vgd.move_learn_method, "name", "")
      if method == "machine":
        tm_moves.append(m_name)
        break
  tm_moves = sorted(list(set(tm_moves)))

  # Level-Up Moves (Version Group Tagged)
  level_moves = []
  for m in getattr(p, "moves", []):
    m_name = getattr(m.move, "name", "").replace("-", " ").title()

    for vgd in getattr(m, "version_group_details", []):
      method = ""
      if hasattr(vgd, "move_learn_method"):
        method = getattr(
            vgd.move_learn_method, "name", str(vgd.move_learn_method)
        )
      elif isinstance(vgd, dict):
        method = vgd.get("move_learn_method", {}).get("name", "")

      if "level-up" in str(method).lower():
        lvl = getattr(vgd, "level_learned_at", 0)
        if isinstance(vgd, dict):
          lvl = vgd.get("level_learned_at", 0)

        vg_slug = "all"
        if hasattr(vgd, "version_group"):
          vg_slug = getattr(vgd.version_group, "name", str(vgd.version_group))
        elif isinstance(vgd, dict):
          vg_slug = vgd.get("version_group", {}).get("name", "all")

        level_moves.append({
            "move": m_name,
            "level": int(lvl),
            "vg": str(vg_slug).lower().replace("_", "-"),
        })

  level_moves.sort(key=lambda x: (x["level"], x["move"]))
  sprite_url = p.sprites.front_default or ""

  return {
      "name": p.name.title(),
      "id": p.id,
      "sprite": sprite_url,
      "types": [t.title() for t in types],
      "past_types": past_types,
      "past_damage_relations": past_damage_relations,
      "bst": bst,
      "stats": stats,
      "ev_yield": ev_yield,
      "weaknesses": weaknesses,
      "resistances": resistances,
      "immunities": immunities,
      "catch_rate": s.capture_rate,
      "base_experience": p.base_experience,
      "growth_rate": (
          s.growth_rate.name.replace("-", " ").title()
          if s.growth_rate
          else "Unknown"
      ),
      "egg_groups": [g.name.replace("-", " ").title() for g in s.egg_groups],
      "hatch_steps": (s.hatch_counter + 1) * 255 if s.hatch_counter else 0,
      "evolutions": evo_details,
      "level_moves": level_moves,
      "tm_moves": tm_moves,
  }

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

# --- Router Endpoints ---
def handle_dashboard(params):
    action = params.get("action", [""])[0] if isinstance(params, dict) else ""

    # --- Action Handling ---
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


    elif action == "set_tasks":
        raw = params.get("tasks", [""])[0]
        parsed = [t.strip() for t in unquote_plus(raw).split(",") if t.strip()]
        if parsed:
            save_tasks_state({"tasks": parsed, "index": 0})

    elif action == "task_nav":
        step = params.get("step", [""])[0]
        state = load_tasks_state()
        if state["tasks"]:
            if step == "next":
                state["index"] = min(state["index"] + 1, len(state["tasks"]) - 1)
            elif step == "prev":
                state["index"] = max(state["index"] - 1, 0)
            save_tasks_state(state)

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
        query_params = urllib.parse.parse_qs(parsed_path.query)
        save_catch_state({
            "hp": params.get("hp", ["100"])[0],
            "lvl": params.get("lvl", ["50"])[0],
            "status": params.get("status", ["1"])[0],
            "ball": params.get("ball", ["poke"])[0],
            "odds": params.get("odds", ["--%"])[0],
            "target": params.get("target", ["None"])[0]
        })
        return "", ("Content-Type", "text/plain")

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
        save_catch_state({
            "hp": params.get("hp", ["100"])[0],
            "lvl": params.get("lvl", ["50"])[0],
            "status": params.get("status", ["1"])[0],
            "ball": params.get("ball", ["poke"])[0],
            "odds": params.get("odds", ["--%"])[0],
            "target": params.get("target", ["None"])[0]
        })
        return "", ("Content-Type", "text/plain")

    # --- Load Data Collections AFTER Actions Execute ---
    pkmn_list = all_pkmn_collection if all_pkmn_collection else load_all_pokemon_names()
    area_list = load_all_location_areas()
    team = load_team()
    target = load_active_target()
    active_route = load_active_route()
    tasks_state = load_tasks_state()
    counters = load_pokemon_counters()
    hunt = load_shiny_hunt()
    ev_state = load_ev_state()
    state = load_catch_state()


    js_pokemon_array = json.dumps(pkmn_list)
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
            <div class="text-3xl font-black font-mono text-amber-300 my-1">{hunt.get('count', 0)}</div>
            <div class="flex gap-1.5 justify-center mt-2">
                <a href="/?action=shiny_dec" class="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs rounded-lg transition">-1</a>
                <a href="/?action=shiny_inc" class="px-5 py-1 bg-amber-500 hover:bg-amber-400 text-slate-950 font-black text-xs rounded-lg transition">+1 Encounter</a>
                <a href="/?action=shiny_reset" onclick="return confirm('Reset counter to 0?');" class="px-2.5 py-1 bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 font-bold text-xs rounded-lg border border-rose-800/40 transition">Reset</a>
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
                    <div class="text-xs font-mono font-bold text-amber-400 truncate">
                        {" +".join([f"{v} {k.replace('special-', 'Sp.').title()}" for k, v in target.get('ev_yield', {}).items()]) or 'None'}
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
            p_slug = p.get("slug", p_name.lower())

            for d in p.get("details", []):
                ver = d.get("version", "Other").title()
                if ver not in games:
                    games[ver] = {}

                if p_name not in games[ver]:
                    games[ver][p_name] = {
                        "slug": p_slug,
                        "methods": set(),
                        "levels": [],
                        "total_chance": 0,
                    }

                if d.get("method"):
                    games[ver][p_name]["methods"].add(d["method"].title())
                if d.get("level"):
                    games[ver][p_name]["levels"].append(str(d["level"]))
                games[ver][p_name]["total_chance"] += d.get("chance", 0)

        game_options = ['<option value="ALL">All Versions</option>']
        game_sections = []

        for ver_name, species_dict in sorted(games.items()):
            ver_slug = ver_name.lower().replace(" ", "-")
            game_options.append(
                f'<option value="{ver_slug}">{ver_name}'
                f" ({len(species_dict)})</option>"
            )

            poke_rows = []
            for p_name, data in sorted(species_dict.items()):
                methods_str = ", ".join(sorted(data["methods"])) or "Wild"
                levels_str = ", ".join(data["levels"][:2]) if data["levels"] else "Any"
                chance_str = (
                    f"{min(100, data['total_chance'])}%"
                    if data["total_chance"] > 0
                    else ""
                )

                poke_rows.append(f"""
                <div class="flex justify-between items-center bg-slate-950/70 border border-slate-800/80 rounded-lg p-2 hover:border-slate-700 transition">
                    <div>
                        <div class="font-bold text-white text-xs">{p_name}</div>
                        <div class="text-[10px] text-slate-400">{methods_str}</div>
                    </div>
                    <div class="flex items-center gap-2">
                        <div class="text-right">
                            <div class="text-[11px] font-mono text-amber-400 font-semibold">{levels_str}</div>
                            {f'<div class="text-[10px] font-mono font-bold text-emerald-400">{chance_str}</div>' if chance_str else ''}
                        </div>
                        <div class="flex gap-1 ml-1">
                            <a href="/?action=set_target&name={data['slug']}" class="text-[10px] bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold px-1.5 py-0.5 rounded">Target</a>
                            <a href="/?action=team_add&name={data['slug']}" class="text-[10px] bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-1.5 py-0.5 rounded">+ Party</a>
                            <a href="/?action=inc_counter&name={quote_plus(p_name)}" class="text-[10px] bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-1.5 py-0.5 rounded">+ Track</a>
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

            <!-- Task Queue Manager -->
            <div class="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-4">
                <div class="flex justify-between items-center mb-1">
                    <span class="text-[10px] uppercase font-bold text-slate-400">{task_count_str}</span>
                    <span class="text-[10px] font-mono text-emerald-400 font-bold">CURRENT TASK</span>
                </div>
                <div class="text-sm font-bold text-white mb-3 bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">{active_task}</div>
                <div class="flex gap-2 mb-3">
                    <a href="/?action=task_nav&step=prev" class="flex-1 py-1.5 bg-slate-800 hover:bg-slate-700 text-center text-xs font-bold rounded-lg transition">◀ Prev</a>
                    <a href="/?action=task_nav&step=next" class="flex-1 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-center text-xs font-bold rounded-lg transition">Next ▶</a>
                </div>
                <form action="/" method="GET" class="space-y-1.5">
                    <input type="hidden" name="action" value="set_tasks" />
                    <input name="tasks" placeholder="Task 1, Task 2, Task 3..." class="w-full bg-slate-800 text-xs border border-slate-700 rounded-lg p-2 text-white" />
                    <button type="submit" class="w-full bg-slate-800 hover:bg-slate-700 font-bold text-[11px] py-1.5 rounded-lg transition">Update Tasks</button>
                </form>
            </div>

            <!-- Catch Target Quick Taps -->
            <div class="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-4">
                <h3 class="text-xs uppercase font-bold text-slate-300 mb-2">Catch Targets (-1)</h3>
                <div class="space-y-1.5 mb-3 max-h-40 overflow-y-auto">
                    {counter_pills}
                </div>
                <form action="/" method="GET" class="space-y-1.5">
                    <input type="hidden" name="action" value="set_counters" />
                    <input name="counter_list" placeholder="caterpie 3, rattata 2" class="w-full bg-slate-800 text-xs border border-slate-700 rounded-lg p-2 text-white" />
                    <button type="submit" class="w-full bg-slate-800 hover:bg-slate-700 font-bold text-[11px] py-1.5 rounded-lg transition">Set Target Batches</button>
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

def handle_obs_target_overlay(params=None):
    target = load_active_target()
    if not target:
        content = '<div style="color: #94a3b8; font-family: sans-serif; font-weight: bold;">No target selected.</div>'
    else:
        stats_rows = "".join([
            f"""<div style="display:flex; justify-content:space-between; margin-bottom:4px; font-size:14px;">
                <span style="color:#94a3b8; text-transform:uppercase;">{k}</span>
                <span style="font-weight:bold; color:#fff;">{v}</span>
            </div>""" for k, v in target.get("stats", {}).items()
        ])
        weaknesses_str = ", ".join([f"{k.title()} ({v}x)" for k, v in target.get("weaknesses", {}).items()]) or "None"
        evos_str = " | ".join(target.get("evolutions", [])) or "None"

        content = f"""
        <div style="display:flex; gap:16px; background:rgba(15,23,42,0.85); border:2px solid #334155; padding:16px; border-radius:12px; color:#fff; width:340px; box-shadow:0 8px 16px rgba(0,0,0,0.5);">
            <div style="flex-shrink:0; text-align:center;">
                <img src="{target.get('sprite', '')}" style="width:84px; height:84px; background:#1e293b; border-radius:8px;" />
                <div style="font-weight:bold; font-size:18px; margin-top:4px;">{target['name']}</div>
                <div style="font-size:12px; color:#f59e0b; font-weight:bold;">BST {target['bst']}</div>
            </div>
            <div style="flex-grow:1;">
                {stats_rows}
                <div style="margin-top:8px; padding-top:8px; border-top:1px solid #334155; font-size:12px;">
                    <div style="color:#f87171; font-weight:bold;">Weak: <span style="color:#cbd5e1; font-weight:normal;">{weaknesses_str}</span></div>
                    <div style="color:#34d399; font-weight:bold; margin-top:2px;">Catch Rate: <span style="color:#cbd5e1; font-weight:normal;">{target.get('catch_rate', 0)}</span></div>
                    <div style="color:#38bdf8; font-weight:bold; margin-top:2px;">Evo: <span style="color:#cbd5e1; font-weight:normal;">{evos_str}</span></div>
                </div>
            </div>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="2">
    <style>body {{ margin:0; padding:16px; font-family:'Segoe UI', sans-serif; background:transparent; }}</style>
</head>
<body>
    {content}
</body>
</html>"""
    return html, ("Content-Type", "text/html")


def handle_obs_team_overlay(params=None):
    team = load_team()[:6]
    cards = "".join([
        f"""<div style="display:flex; flex-direction:column; align-items:center; background:rgba(15,23,42,0.85); border:2px solid #334155; border-radius:10px; padding:8px 12px; min-width:80px;">
            <img src="{m['sprite']}" style="width:56px; height:56px;" />
            <span style="color:#fff; font-weight:bold; font-size:13px; margin-top:2px;">{m['name']}</span>
        </div>""" for m in team
    ])

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="2">
    <style>body {{ margin:0; padding:12px; font-family:'Segoe UI', sans-serif; background:transparent; display:flex; gap:10px; }}</style>
</head>
<body>
    {cards}
</body>
</html>"""
    return html, ("Content-Type", "text/html")


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

def handle_pokemon_stream(params=None):
    data = load_pokemon()
    
    # Build list HTML
    rows_html = ""
    for name, count in data.items():
        rows_html += f"""
        <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(0,0,0,0.7); padding: 8px 16px; border-radius: 8px; font-size: 22px; font-weight: bold; min-width: 220px; border-left: 4px solid #ffcb05; margin-bottom: 8px; margin-right: 8px;">
            <span>{name}</span>
            <span style="color: #ffcb05; font-size: 24px;">{count}</span>
        </div>
        """

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <!-- Auto-refreshes OBS overlay every 2 seconds without JS API calls -->
    <meta http-equiv="refresh" content="2">
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: transparent; color: #fff; margin: 0; padding: 16px; text-shadow: 2px 2px 4px #000; }}
        .container {{ display: flex; flex-direction: row; width: fit-content; flex-wrap: wrap; }}
    </style>
</head>
<body>
    <div class="container">
        {rows_html}
    </div>
</body>
</html>""", ("Content-Type", "text/html")


def handle_pokemon_remote(params):
    action = params.get("action", [""])[0] if isinstance(params, dict) else ""

    # 1. Base / Shared Action Dispatcher
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
                "sprite": f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{p_id}.png",
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
        slug = params.get("slug", [""])[0].strip().lower().replace(" ", "-")
        if slug:
            route_data = fetch_route_encounter_info(slug)
            if route_data:
                save_active_route(route_data)

    elif action == "inc_counter":
        p_name = unquote_plus(params.get("name", [""])[0]).strip().title()
        if p_name:
            c = load_pokemon_counters()
            c[p_name] = c.get(p_name, 0) + 1
            save_pokemon_counters(c)

    elif action == "dec_counter":
        p_name = unquote_plus(params.get("name", [""])[0]).strip().title()
        if p_name:
            c = load_pokemon_counters()
            c[p_name] = c.get(p_name, 0) - 1
            if c[p_name] <= 0:
                del c[p_name]
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
        save_catch_state({
            "hp": params.get("hp", ["100"])[0],
            "lvl": params.get("lvl", ["50"])[0],
            "status": params.get("status", ["1"])[0],
            "ball": params.get("ball", ["poke"])[0],
            "odds": params.get("odds", ["--%"])[0],
            "target": params.get("target", ["None"])[0]
        })
        return "", ("Content-Type", "text/plain")

    # 2. Remote-Specific Shortcuts
    task_action = params.get("task_action", [""])[0] if isinstance(params, dict) else ""
    if task_action:
        t_state = load_tasks_state()
        if t_state.get("tasks"):
            if task_action == "next":
                t_state["index"] = min(t_state["index"] + 1, len(t_state["tasks"]) - 1)
            elif task_action == "prev":
                t_state["index"] = max(t_state["index"] - 1, 0)
            save_tasks_state(t_state)

    set_tasks_raw = params.get("set_tasks", [""])[0] if isinstance(params, dict) else ""
    if set_tasks_raw:
        parsed = [t.strip() for t in unquote_plus(set_tasks_raw).split(",") if t.strip()]
        if parsed:
            save_tasks_state({"tasks": parsed, "index": 0})

    inc_counter_name = params.get("inc_counter", [""])[0] if isinstance(params, dict) else ""
    if inc_counter_name:
        p_name = unquote_plus(inc_counter_name).strip().title()
        c = load_pokemon_counters()
        c[p_name] = c.get(p_name, 0) + 1
        save_pokemon_counters(c)

    dec_counter_name = params.get("dec_counter", [""])[0] if isinstance(params, dict) else ""
    if dec_counter_name:
        p_name = unquote_plus(dec_counter_name).strip().title()
        c = load_pokemon_counters()
        if p_name in c:
            c[p_name] -= 1
            if c[p_name] <= 0:
                del c[p_name]
            save_pokemon_counters(c)

    set_list_raw = params.get("set_list", [""])[0] if isinstance(params, dict) else ""
    if set_list_raw:
        raw = unquote_plus(set_list_raw)
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

    # 3. Shiny Hunting Actions
    shiny_action = params.get("shiny_action", [""])[0] if isinstance(params, dict) else ""
    if shiny_action:
        hunt = load_shiny_hunt()
        if shiny_action == "inc":
            hunt["count"] += 1
        elif shiny_action == "dec":
            hunt["count"] = max(0, hunt["count"] - 1)
        elif shiny_action == "reset":
            hunt["count"] = 0
        save_shiny_hunt(hunt)

    # --- Load Session State AFTER Actions Execute ---
    tasks_state = load_tasks_state()
    counters = load_pokemon_counters()
    hunt = load_shiny_hunt()
    target = load_active_target()
    ev_state = load_ev_state()
    state = load_catch_state()
    route_data = load_active_route()
    active_route = load_active_route()

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

            for d in p.get("details", []):
                ver = d.get("version", "Other").title()
                if ver not in games:
                    games[ver] = {}

                if p_name not in games[ver]:
                    games[ver][p_name] = {
                        "slug": p_slug,
                        "methods": set(),
                        "levels": [],
                        "total_chance": 0,
                    }

                if d.get("method"):
                    games[ver][p_name]["methods"].add(d["method"].title())
                if d.get("level"):
                    games[ver][p_name]["levels"].append(str(d["level"]))
                games[ver][p_name]["total_chance"] += d.get("chance", 0)

        game_options = ['<option value="ALL">All Versions</option>']
        game_sections = []

        for ver_name, species_dict in sorted(games.items()):
            ver_slug = ver_name.lower().replace(" ", "-")
            game_options.append(
                f'<option value="{ver_slug}">{ver_name}'
                f" ({len(species_dict)})</option>"
            )

            poke_rows = []
            for p_name, data in sorted(species_dict.items()):
                methods_str = ", ".join(sorted(data["methods"])) or "Wild"
                levels_str = ", ".join(data["levels"][:2]) if data["levels"] else "Any"
                chance_str = (
                    f"{min(100, data['total_chance'])}%"
                    if data["total_chance"] > 0
                    else ""
                )

                poke_rows.append(f"""
                <div class="flex justify-between items-center bg-slate-950/70 border border-slate-800/80 rounded-lg p-2 hover:border-slate-700 transition">
                    <div>
                        <div class="font-bold text-white text-xs">{p_name}</div>
                        <div class="text-[10px] text-slate-400">{methods_str}</div>
                    </div>
                    <div class="flex items-center gap-2">
                        <div class="text-right">
                            <div class="text-[11px] font-mono text-amber-400 font-semibold">Lv {levels_str}</div>
                            {f'<div class="text-[10px] font-mono font-bold text-emerald-400">{chance_str}</div>' if chance_str else ''}
                        </div>
                        <div class="flex gap-1 ml-1">
                            <a href="/remote?action=set_target&name={data['slug']}" class="text-[10px] bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold px-1.5 py-0.5 rounded active:scale-95 transition">Target</a>
                            <a href="/remote?action=team_add&name={data['slug']}" class="text-[10px] bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-1.5 py-0.5 rounded active:scale-95 transition">+ Party</a>
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

        route_section_html = f"""
        <div class="bg-slate-900/80 border border-slate-800 rounded-2xl p-3.5 space-y-3 shadow-md mt-4">
            <div class="bg-emerald-950/30 border border-emerald-500/30 rounded-xl p-3">
                <div class="text-[10px] uppercase font-bold text-emerald-400">Current Location</div>
                <div class="text-base font-black text-white">{active_route.get('name', 'Unknown Route')}</div>
                <div class="text-xs text-slate-400 mt-0.5">{active_route.get('total_species', len(active_route.get('pokemon', [])))} total species</div>
            </div>

            <!-- Game Version Selector Row -->
            <div class="flex items-center justify-between gap-2 bg-slate-900/80 border border-slate-800 rounded-xl px-3 py-2 text-xs">
                <span class="font-bold text-slate-400 uppercase text-[10px] tracking-wider whitespace-nowrap">Filter Game:</span>
                <select id="game-filter-select" onchange="filterGameVersion()" class="w-full bg-slate-950 border border-slate-700 text-amber-400 font-bold rounded px-2 py-1 text-xs focus:outline-none focus:border-amber-400">
                    {''.join(game_options)}
                </select>
            </div>

            <div class="space-y-2 max-h-[500px] overflow-y-auto pr-1">
                {"".join(game_sections) or '<div class="text-slate-500 text-xs italic">No encounter tables for this sub-area.</div>'}
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
        const allLocations = {locations_json};
        const allPokemon = {pkmn_json};

        {SHARED_POKEMON_JS}

        function calculateCatchOdds() {{
            const hp = document.getElementById('catch-hp-slider')?.value || 100;
            const lvl = document.getElementById('catch-lvl-input')?.value || 50;
            const status = document.getElementById('catch-status-select')?.value || 1;
            const ball = document.getElementById('catch-ball-select')?.value || 'poke';

            const hpDisp = document.getElementById('catch-hp-display');
            if (hpDisp) hpDisp.innerText = hp + '%';

            const oddsDisplay = document.getElementById('catch-odds-display');
            let odds = oddsDisplay ? oddsDisplay.innerText : '--%';

            syncCatchState(hp, lvl, status, ball, odds);
        }}

        function syncCatchState(hp, lvl, status, ball, odds) {{
            const targetName = (window.activeTargetData && activeTargetData.name) ? activeTargetData.name : "None";
            fetch(`/sync_catch?hp=${{hp}}&lvl=${{lvl}}&status=${{status}}&ball=${{ball}}&odds=${{encodeURIComponent(odds)}}&target=${{encodeURIComponent(targetName)}}`)
                .catch(err => console.log("Background sync failed", err));
        }}

        function filterRouteVersion() {{
            const select = document.getElementById('route-version-filter');
            if (!select) return;
            const selected = select.value;
            document.querySelectorAll('.game-version-card').forEach(card => {{
                if (card.getAttribute('data-version') === selected) {{
                    card.style.display = 'block';
                }} else {{
                    card.style.display = 'none';
                }}
            }});
        }}

        // Dynamic Instant Dropdown Filter for Routes
        function liveFilterRoutes() {{
            const query = document.getElementById('route-search-input').value.trim().toLowerCase();
            const resultsContainer = document.getElementById('route-live-results');
            const listContainer = document.getElementById('route-results-list');
            const countLabel = document.getElementById('route-results-count');

            if (!query || query.length < 1) {{
                resultsContainer.style.display = 'none';
                listContainer.innerHTML = '';
                return;
            }}

            const tokens = query.split(/\s+/);
            const matches = allLocations.filter(loc => {{
                const name = loc.name.toLowerCase();
                const slug = loc.slug.toLowerCase();
                return tokens.every(token => name.includes(token) || slug.includes(token));
            }}).slice(0, 15);

            if (matches.length === 0) {{
                countLabel.innerText = "0 matches found";
                listContainer.innerHTML = '<div class="text-xs text-slate-500 italic p-2">No matching routes</div>';
                resultsContainer.style.display = 'block';
                return;
            }}

            countLabel.innerText = `${{matches.length}} matching locations`;
            listContainer.innerHTML = matches.map(m => `
                <a href="/remote?action=set_location&slug=${{encodeURIComponent(m.slug)}}" class="flex justify-between items-center bg-slate-950/80 hover:bg-indigo-950/60 border border-slate-800 hover:border-indigo-500 rounded-lg p-2.5 text-xs text-slate-200 transition active:scale-98">
                    <span class="font-bold text-white">${{m.name}}</span>
                    <span class="font-mono text-[10px] text-indigo-400 font-semibold">${{m.slug}}</span>
                </a>
            `).join('');

            resultsContainer.style.display = 'block';
        }}

        // Dynamic Instant Dropdown Filter for Pokémon Targets
        function liveFilterPokemon() {{
            const query = document.getElementById('pkmn-search-input').value.trim().toLowerCase();
            const resultsContainer = document.getElementById('pkmn-live-results');
            const listContainer = document.getElementById('pkmn-results-list');
            const countLabel = document.getElementById('pkmn-results-count');

            if (!query || query.length < 1) {{
                resultsContainer.style.display = 'none';
                listContainer.innerHTML = '';
                return;
            }}

            const tokens = query.split(/\s+/);
            const matches = allPokemon.filter(p => {{
                const name = p.name.toLowerCase();
                const slug = p.slug.toLowerCase();
                return tokens.every(token => name.includes(token) || slug.includes(token));
            }}).slice(0, 15);

            if (matches.length === 0) {{
                countLabel.innerText = "0 matches found";
                listContainer.innerHTML = '<div class="text-xs text-slate-500 italic p-2">No matching Pokémon</div>';
                resultsContainer.style.display = 'block';
                return;
            }}

            countLabel.innerText = `${{matches.length}} matching Pokémon`;
            listContainer.innerHTML = matches.map(p => `
                <div class="flex justify-between items-center bg-slate-950/80 hover:bg-amber-950/30 border border-slate-800 hover:border-amber-500 rounded-lg p-2 text-xs text-slate-200 transition">
                    <span class="font-bold text-white">${{p.name}}</span>
                    <div class="flex gap-1.5">
                        <a href="/remote?action=set_target&name=${{encodeURIComponent(p.slug)}}" class="text-[10px] bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold px-2 py-1 rounded active:scale-95 transition">Target</a>
                        <a href="/remote?action=team_add&name=${{encodeURIComponent(p.slug)}}" class="text-[10px] bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-2 py-1 rounded active:scale-95 transition">+Party</a>
                        <a href="/remote?action=inc_counter&name=${{encodeURIComponent(p.name)}}" class="text-[10px] bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-2 py-1 rounded active:scale-95 transition">+Track</a>
                    </div>
                </div>
            `).join('');

            resultsContainer.style.display = 'block';
        }}

        window.addEventListener('DOMContentLoaded', () => {{
            updateTargetGenView();
            filterRouteVersion();
        }});
        window.addEventListener('DOMContentLoaded', () => {{
            if (typeof updateTargetGenView === "function") updateTargetGenView();
            setTimeout(filterRouteVersion, 50);
        }});
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
                    id="route-search-input" 
                    oninput="liveFilterRoutes()" 
                    placeholder="Search route (e.g. kanto-route-1, viridian)..." 
                    autocomplete="off" 
                    class="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-indigo-400"
                />
                <div id="route-live-results" class="bg-slate-900/95 border border-indigo-500/40 rounded-xl p-3 space-y-2 mt-2" style="display: none;">
                    <div class="flex justify-between items-center text-[10px] font-bold text-indigo-300 uppercase tracking-wider">
                        <span id="route-results-count">0 matching locations</span>
                        <button type="button" onclick="document.getElementById('route-live-results').style.display='none';" class="text-slate-500 hover:text-white text-xs">✕</button>
                    </div>
                    <div id="route-results-list" class="space-y-1.5 max-h-56 overflow-y-auto"></div>
                </div>
            </div>
            
            <!-- Route Encounters Table -->
            <div style="margin-top: 0;">
                {route_section_html}
            </div>

            <!-- Stream Tasks -->
            <div class="card" style="border: 2px solid #3b82f6; margin-top: 0;">
                <div style="font-size: 0.85rem; color: #9ca3af; text-transform: uppercase; font-weight: bold; margin-bottom: 4px;">{task_progress}</div>
                <div style="font-size: 1.4rem; font-weight: bold; color: #fff; margin-bottom: 14px;">{active_task_name}</div>
                <div style="display: flex; gap: 10px;">
                    <a href="/remote?task_action=prev" class="nav-btn">◀ Back</a>
                    <a href="/remote?task_action=next" class="nav-btn" style="background: #2563eb;">Forward ▶</a>
                </div>
            </div>

            <!-- Task Management -->
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


def handle_obs_shiny(params):
  hunt = load_shiny_hunt()
  html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="2">
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-transparent text-white font-sans p-2 select-none">
    <div class="inline-flex items-center gap-3 bg-slate-950/85 border border-amber-500/40 rounded-2xl px-4 py-2.5 shadow-2xl backdrop-blur-md">
        <div class="text-2xl animate-pulse">✨</div>
        <div>
            <div class="text-[11px] font-bold uppercase tracking-wider text-amber-400">{hunt.get('target', 'None')} <span class="text-slate-400 normal-case font-normal text-[10px]">({hunt.get('method', 'Encounters')})</span></div>
            <div class="text-2xl font-black font-mono leading-none tracking-tight text-white mt-0.5">{hunt.get('count', 0)} <span class="text-xs text-slate-400 font-normal">seen</span></div>
        </div>
    </div>
</body>
</html>"""
  return html, ("Content-Type", "text/html")


def handle_obs_evs(params):
  ev_state = load_ev_state()
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

  stat_config = [
      ("hp", "HP", "#10b981"),
      ("attack", "ATK", "#f43f5e"),
      ("defense", "DEF", "#3b82f6"),
      ("special-attack", "SPA", "#a855f7"),
      ("special-defense", "SPD", "#6366f1"),
      ("speed", "SPE", "#f59e0b"),
  ]

  bars_html = ""
  for stat_key, label, color in stat_config:
    val = ev_state.get(stat_key, 0)
    pct = min(100, int((val / 252) * 100))
    bars_html += f"""
        <div style="margin-bottom: 8px;">
            <div style="display: flex; justify-content: space-between; font-size: 11px; font-weight: bold; margin-bottom: 2px;">
                <span style="color: {color};">{label}</span>
                <span style="font-family: monospace; color: #fff;">{val}</span>
            </div>
            <div style="background: rgba(255,255,255,0.1); height: 6px; border-radius: 3px; overflow: hidden;">
                <div style="background: {color}; width: {pct}%; height: 100%; border-radius: 3px;"></div>
            </div>
        </div>
        """

  html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="2">
    <style>
        body {{
            background: transparent;
            margin: 0;
            padding: 12px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #fff;
        }}
        .ev-card {{
            background: rgba(15, 23, 42, 0.85);
            border: 1px solid rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(8px);
            border-radius: 12px;
            padding: 12px;
            width: 220px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.5);
        }}
    </style>
</head>
<body>
    <div class="ev-card">
        <div style="display: flex; justify-content: space-between; font-size: 11px; text-transform: uppercase; font-weight: 800; color: #10b981; margin-bottom: 8px;">
            <span>EV Tracker</span>
            <span style="font-family: monospace;">{total_evs}/510</span>
        </div>
        {bars_html}
    </div>
</body>
</html>"""
  return html, ("Content-Type", "text/html")

def handle_obs_catch_rate(params):
    state = load_catch_state()
    
    # Format labels
    ball_map = {"poke": "Poké Ball", "great": "Great Ball", "ultra": "Ultra Ball", "master": "Master Ball"}
    status_map = {"1": "None", "1.5": "PAR/PSN/BRN", "2.5": "SLP/FRZ"}
    
    ball_name = ball_map.get(state.get("ball", "poke"), "Poké Ball")
    status_name = status_map.get(str(state.get("status", "1")), "None")
    
    html = f"""<!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta http-equiv="refresh" content="2">
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-transparent font-sans overflow-hidden p-4">
        <div class="bg-slate-900/90 border-2 border-slate-700/80 rounded-xl p-3 inline-block shadow-2xl backdrop-blur-sm min-w-[240px]">
            <div class="flex items-center justify-between gap-4 mb-2">
                <div class="text-3xl font-black font-mono text-emerald-400 tracking-tighter">
                    {state.get('odds', '--%')}
                </div>
                <div class="text-right">
                    <div class="text-[10px] font-bold text-indigo-400 uppercase leading-tight">Lvl {state.get('lvl', '50')} • HP {state.get('hp', '100')}%</div>
                    <div class="text-[10px] font-bold text-slate-300 uppercase leading-tight">{status_name}</div>
                </div>
            </div>
            
            <div class="flex items-center justify-between gap-4 mb-2">
                <div class="text-3xl font-black font-mono text-emerald-400 tracking-tighter">
                    {state.get('odds', '--%')}
                </div>
                <div class="text-right">
                    <div class="text-[10px] font-bold text-rose-400 uppercase leading-tight">HP {state.get('hp', '100')}%</div>
                    <div class="text-[10px] font-bold text-indigo-300 uppercase leading-tight">{status_name}</div>
                </div>
            </div>
            
            <div class="bg-slate-950/60 border border-slate-800 rounded px-2 py-1 text-center">
                <span class="text-[11px] font-bold text-slate-300 tracking-wide">{ball_name}</span>
            </div>
        </div>
    </body>
    </html>"""
    
    return html, ("Content-Type", "text/html")

def handle_obs_hub(params):
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OBS Overlays Hub</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 font-sans min-h-screen flex flex-col items-center justify-center p-6">
    
    <div class="max-w-2xl w-full bg-slate-900/80 border border-slate-800 rounded-3xl p-8 shadow-2xl">
        <div class="text-center mb-8">
            <h1 class="text-2xl font-black uppercase tracking-wider text-emerald-400 mb-2">OBS Overlays Hub</h1>
            <p class="text-slate-400 text-sm">Select an overlay to view it in this window.</p>
        </div>
        
        <!-- Overlay Buttons Grid -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <a href="/obs/target" class="flex flex-col items-center justify-center bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-indigo-500 text-slate-200 hover:text-white py-5 rounded-2xl font-bold transition-all shadow-lg active:scale-95">
                <span class="text-2xl mb-1">🎯</span>
                <span>Active Target</span>
            </a>
            
            <a href="/obs/team" class="flex flex-col items-center justify-center bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-emerald-500 text-slate-200 hover:text-white py-5 rounded-2xl font-bold transition-all shadow-lg active:scale-95">
                <span class="text-2xl mb-1">🛡️</span>
                <span>Party Team</span>
            </a>
            
            <a href="/obs/tocatch" class="flex flex-col items-center justify-center bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-sky-500 text-slate-200 hover:text-white py-5 rounded-2xl font-bold transition-all shadow-lg active:scale-95">
                <span class="text-2xl mb-1">📋</span>
                <span>To Catch List</span>
            </a>
            
            <a href="/obs/shiny" class="flex flex-col items-center justify-center bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-amber-500 text-slate-200 hover:text-white py-5 rounded-2xl font-bold transition-all shadow-lg active:scale-95">
                <span class="text-2xl mb-1">✨</span>
                <span>Shiny Hunt</span>
            </a>
            
            <a href="/obs/evs" class="flex flex-col items-center justify-center bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-rose-500 text-slate-200 hover:text-white py-5 rounded-2xl font-bold transition-all shadow-lg active:scale-95">
                <span class="text-2xl mb-1">💪</span>
                <span>EV Tracker</span>
            </a>
            
            <a href="/obs/catchrate" class="flex flex-col items-center justify-center bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-purple-500 text-slate-200 hover:text-white py-5 rounded-2xl font-bold transition-all shadow-lg active:scale-95">
                <span class="text-2xl mb-1">🧮</span>
                <span>Catch Odds</span>
            </a>
        </div>
        
        <!-- Navigation Footer -->
        <div class="mt-8 text-center pt-6 border-t border-slate-800/80">
            <a href="/" class="text-slate-500 hover:text-white font-bold text-xs uppercase tracking-wider transition-colors px-4 py-2">
                ← Back to Dashboard
            </a>
            <span class="text-slate-700 mx-2">|</span>
            <a href="/remote" class="text-slate-500 hover:text-white font-bold text-xs uppercase tracking-wider transition-colors px-4 py-2">
                Mobile Remote →
            </a>
        </div>
    </div>

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
}