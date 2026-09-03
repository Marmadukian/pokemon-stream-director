from utils import *


def handle_obs_catch_rate(params):
    state = load_catch_state()
    
    # Format labels
    ball_map = {
        "poke": "Poké Ball",
        "great": "Great Ball",
        "ultra": "Ultra Ball",
        "master": "Master Ball",
        "safari": "Safari Ball",
        "net": "Net Ball",
        "nest": "Nest Ball",
        "repeat": "Repeat Ball",
        "timer": "Timer Ball",
        "dusk": "Dusk Ball",
        "quick": "Quick Ball"
    }
    status_map = {
        "1": "No Status",
        "1.5": "PAR / PSN / BRN",
        "2": "PAR / PSN / BRN",
        "2.5": "SLP / FRZ"
    }
    
    ball_name = ball_map.get(str(state.get("ball", "poke")).lower(), "Poké Ball")
    status_name = status_map.get(str(state.get("status", "1")), "No Status")
    odds_str = state.get("odds", "--%")
    hp_val = state.get("hp", "100")
    lvl_val = state.get("lvl", "50")
    target_name = state.get("target", "Target")
    
    # Set status badge color dynamically
    status_color = "text-slate-400"
    if "SLP" in status_name:
        status_color = "text-sky-400"
    elif "PAR" in status_name or "PSN" in status_name or "BRN" in status_name:
        status_color = "text-amber-400"

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="2">
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-transparent font-sans overflow-hidden p-4">
    <div class="bg-slate-900/90 border-2 border-slate-700/80 rounded-xl p-3 inline-block shadow-2xl backdrop-blur-sm min-w-[240px]">
        <!-- Target / Meta Header -->
        <div class="flex items-center justify-between border-b border-slate-800 pb-1 mb-2">
            <span class="text-[10px] uppercase tracking-wider font-bold text-slate-400">{target_name}</span>
            <span class="text-[10px] font-mono text-indigo-400 font-bold">LVL {lvl_val}</span>
        </div>

        <!-- Main Odds & Conditions -->
        <div class="flex items-center justify-between gap-4 mb-2">
            <div class="text-3xl font-black font-mono text-emerald-400 tracking-tighter">
                {odds_str}
            </div>
            <div class="text-right">
                <div class="text-[11px] font-bold text-rose-400 uppercase leading-tight">HP {hp_val}%</div>
                <div class="text-[10px] font-bold {status_color} uppercase leading-tight mt-0.5">{status_name}</div>
            </div>
        </div>
        
        <!-- Ball Used -->
        <div class="bg-slate-950/70 border border-slate-800 rounded px-2 py-1 text-center">
            <span class="text-[11px] font-bold text-slate-200 tracking-wide">{ball_name}</span>
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

def handle_obs_exp(params):
    state = load_exp_state()

    growth = state.get("growth_rate", "Medium Fast").replace("-", " ").title()
    lvl_from = state.get("lvl_from", "1")
    lvl_to = state.get("lvl_to", "36")
    exp_needed = state.get("exp_needed", "0 EXP")
    exp_per_kill = state.get("exp_per_kill", "120")
    kills = state.get("kills", "0 kills")
    est_time = state.get("est_time", "~0m")

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        setInterval(() => {{
            fetch(window.location.pathname + '?t=' + Date.now())
                .then(res => res.text())
                .then(html => {{
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    const newRoot = doc.getElementById('exp-overlay-root');
                    const curRoot = document.getElementById('exp-overlay-root');
                    if (newRoot && curRoot && newRoot.innerHTML !== curRoot.innerHTML) {{
                        curRoot.innerHTML = newRoot.innerHTML;
                    }}
                }})
                .catch(() => {{}});
        }}, 1000);
    </script>
</head>
<body class="bg-transparent font-sans overflow-hidden p-4">
    <div id="exp-overlay-root" class="bg-slate-900/90 border-2 border-slate-700/80 rounded-xl p-3 inline-block shadow-2xl backdrop-blur-sm min-w-[260px]">
        <!-- Header -->
        <div class="flex items-center justify-between border-b border-slate-800 pb-1 mb-2">
            <span class="text-[10px] uppercase tracking-wider font-bold text-slate-400">EXP GRIND</span>
            <span class="text-[10px] font-mono text-amber-400 font-bold">{growth}</span>
        </div>

        <!-- Level Range & Total EXP -->
        <div class="flex items-center justify-between gap-4 mb-2">
            <div>
                <span class="text-[11px] font-bold text-slate-400">LVL</span>
                <span class="text-sm font-black font-mono text-indigo-400">{lvl_from}</span>
                <span class="text-[10px] text-slate-500 font-bold">➔</span>
                <span class="text-sm font-black font-mono text-indigo-400">{lvl_to}</span>
            </div>
            <div class="text-right">
                <div class="text-base font-black font-mono text-amber-300 tracking-tight leading-none">{exp_needed}</div>
            </div>
        </div>

        <!-- Grind Stats Footer -->
        <div class="bg-slate-950/70 border border-slate-800 rounded px-2 py-1.5 flex items-center justify-between font-mono text-[11px]">
            <span class="text-slate-400">{kills} <span class="text-[9px] text-slate-600">(@{exp_per_kill})</span></span>
            <span class="text-emerald-400 font-bold">{est_time}</span>
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


def handle_obs_target_overlay(params=None):
    target = load_active_target()
    if not target:
        content = '<div style="color: #94a3b8; font-family: sans-serif; font-weight: bold;">No target selected.</div>'
    else:
        stats_rows = "".join([
            f"""<div style="display:flex; justify-content:space-between; margin-bottom:3px; font-size:13px;">
                <span style="color:#94a3b8; text-transform:uppercase;">{k}</span>
                <span style="font-weight:bold; color:#fff;">{v}</span>
            </div>""" for k, v in target.get("stats", {}).items()
        ])

        # Weaknesses, Resistances, Immunities
        def format_matchups(data):
            if isinstance(data, dict):
                entries = [f"{k.title()}{f' ({v}x)' if v != 1 else ''}" for k, v in data.items()]
            elif isinstance(data, (list, set, tuple)):
                entries = [str(x).title() for x in data if x]
            else:
                entries = []
            return ", ".join(entries) or "None"

        weaknesses_str = format_matchups(target.get("weaknesses", {}))
        resistances_str = format_matchups(target.get("resistances", {}))
        immunities_str = format_matchups(target.get("immunities", {}))

        # Evolutions
        raw_evos = target.get("evolutions", [])
        evos_str = " ➔ ".join(raw_evos) if raw_evos else "None"

        # --- Parse Selected Version Directly in Overlay ---
        raw_ver = get_current_game_version() if "get_current_game_version" in globals() else ""
        if isinstance(raw_ver, (list, tuple)):
            raw_ver = raw_ver[0] if raw_ver else "red-blue"

        # Strip accidental stringified representations like "['red-blue']"
        target_selected_version = (
            str(raw_ver or target.get("selected_gen") or "red-blue")
            .strip("[]'\" ")
            .lower()
        )

        all_target_encounters = target.get("encounters", {}) or {}

        # Fallback to target_cache if active target object didn't have encounters loaded
        if not all_target_encounters:
            t_slug = target.get("slug") or str(target.get("name", "")).lower().replace(" ", "-")
            cache_dir = getattr(handlers, "TARGET_CACHE_DIR", "target_cache") if "handlers" in globals() else "target_cache"
            c_file = os.path.join(cache_dir, f"{t_slug}.json")
            if os.path.exists(c_file):
                try:
                    with open(c_file, "r", encoding="utf-8") as f:
                        cached_data = json.load(f)
                        all_target_encounters = cached_data.get("encounters", {}) or {}
                except Exception:
                    pass

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

            # If selected version yields 0 encounters (e.g., Pikachu in Yellow), fallback across versions
            if not raw_version_encounters:
                for v_list in all_target_encounters.values():
                    if isinstance(v_list, list):
                        raw_version_encounters.extend(v_list)

        # Deduplicate identical spawns (same location, levels, methods)
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
            top_enc = max(target_version_encounters, key=lambda x: x.get("chance", 0), default={})
            loc = top_enc.get("location", "Unknown Area")
            min_l = top_enc.get("min_level", 1)
            max_l = top_enc.get("max_level", 1)
            lvl_str = f"Lv. {min_l}" if min_l == max_l else f"Lv. {min_l}-{max_l}"
            chance_val = top_enc.get("chance", 0)
            chance_str = f" ({chance_val}%)" if chance_val > 0 else ""
            current_location = f"{loc} [{lvl_str}]{chance_str}"
        elif "load_active_route" in globals() and load_active_route():
            current_location = load_active_route().get("name", "None Listed")
        else:
            current_location = "None Listed"

        # Types Badges
        types = target.get("types", [])
        types_html = "".join([
            f'<span style="background:#334155; color:#cbd5e1; font-size:10px; font-weight:bold; padding:2px 6px; border-radius:4px; margin-right:4px;">{t.upper()}</span>'
            for t in types
        ])

        content = f"""
        <div style="display:flex; gap:16px; background:rgba(15,23,42,0.92); border:2px solid #334155; padding:16px; border-radius:12px; color:#fff; width:390px; box-shadow:0 8px 16px rgba(0,0,0,0.5);">
            <div style="flex-shrink:0; text-align:center; width:95px;">
                <img src="{target.get('sprite', '')}" style="width:84px; height:84px; background:#1e293b; border-radius:8px; object-fit:contain;" />
                <div style="font-weight:bold; font-size:16px; margin-top:4px; word-break:break-word;">{target.get('name', 'Unknown')}</div>
                <div style="font-size:11px; color:#f59e0b; font-weight:bold; margin-bottom:4px;">BST {target.get('bst', 0)}</div>
                <div>{types_html}</div>
            </div>
            <div style="flex-grow:1; min-width:0;">
                {stats_rows}
                <div style="margin-top:6px; padding-top:6px; border-top:1px solid #334155; font-size:11px; line-height:1.4;">
                    <div style="color:#f87171; font-weight:bold;">Weak: <span style="color:#cbd5e1; font-weight:normal;">{weaknesses_str}</span></div>
                    <div style="color:#60a5fa; font-weight:bold; margin-top:1px;">Resist: <span style="color:#cbd5e1; font-weight:normal;">{resistances_str}</span></div>
                    <div style="color:#a78bfa; font-weight:bold; margin-top:1px;">Immune: <span style="color:#cbd5e1; font-weight:normal;">{immunities_str}</span></div>
                    <div style="color:#38bdf8; font-weight:bold; margin-top:3px;">Evo: <span style="color:#cbd5e1; font-weight:normal;">{evos_str}</span></div>
                    <div style="color:#34d399; font-weight:bold; margin-top:3px;">Encounter: <span style="color:#fcd34d; font-weight:normal;">{current_location}</span></div>
                </div>
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
            margin: 0;
            padding: 16px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: transparent;
            overflow: hidden;
        }}
    </style>
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

