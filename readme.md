# Pokémon Stream Director & Remote Hub

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Built to remove friction during Pokémon streams and challenge runs. I'm not a front-end dev and mostly hate writing HTML, so AI wrote the majority of the UI and I hand-tweaked it to fit my stream workflow.

A lightweight, self-hosted dashboard built with Python and PokéAPI (`pokebase`). Inspect Pokémon base stats, historical generation data, and wild encounter rates on the fly; manage your live party; run shiny counters; and tap through stream tasks right from your phone.

Includes transparent OBS browser sources for active Pokémon targets, current routes, and party rosters.

---

## Features

* **Live Target Scanner:** Inspect base stats, BST, type matchups, historical past-gen mechanics, catch odds, and level-up/TM movepools.
* **Wild Encounter Tables:** Route search with deduplicated wild encounter rates, methods, and levels mapped per game version.
* **OBS Browser Overlays:** Dedicated transparent overlays (`/obs/target_overlay`, `/obs/team`, `/obs/shiny`) with auto-refresh and version sync.
* **Mobile Remote (`/remote`):** Touch-friendly dashboard scaled for phones. Increment shiny encounters, decrement catch targets, track EV yields, and step through tasks with one-handed controls.
* **Modular UI Toggles:** Show or hide any card/section on the dashboard and remote independently (states save automatically to local storage).
* **Flat File Persistence:** Saves party rosters, catch targets, video notes, and task queues to simple local `.txt` and `.json` files.

---

## Requirements

* Python 3.10+
* `pokebase`
* Basic ability to read terminal output and troubleshoot your local network

---

## 🚀 Installation & Running

Choose whichever setup option fits your system:

### Option 1: Installer (Recommended)
1. Download **`PokemonHuntingTool.zip`**.
2. Run the installer and follow the setup prompts.
   * *If Windows SmartScreen prompts you, click **More info** -> **Run anyway**.*
3. Launch the application from the desktop shortcut.

---

### Option 2: Portable ZIP (Zero-Install / For Smart App Control)
If Windows 11 Smart App Control (SAC) blocks the installer, use this standalone version:
1. Download **`Pokemon Stream Director v1.0.zip`**.
2. **Important:** Right-click the `.zip` file -> select **Properties** -> check **Unblock** at the bottom -> click **Apply**.
3. Extract the folder anywhere (e.g., Desktop or Downloads).
4. Run **`RunServer.bat`** to verify dependencies and start the local server.

1. Download **`Pokemon Stream Director v1.0.zip`**.
2. **Important:** Right-click the `.zip` file -> select **Properties** -> check **Unblock** at the bottom -> click **Apply**.
3. Extract the folder anywhere (e.g., Desktop or Downloads).
4. Run **`RunServer.bat`** to verify dependencies and start the local server.
---

## Automation & Stream Deck API

All actions can be triggered via either **GET** or **POST** requests to the base dashboard (`http://<YOUR-PC-IP>:1350/`). The IP is printed on server startup 

For GET requests, append parameters to the query string. For POST requests, send them as either URL-encoded form data (`action=...`) or a JSON payload (`{"action": "..."}`). If you trigger an action externally (like via Stream Deck or curl), refresh the dashboard window to reflect the updated state.

### Shiny Hunting
* `/?action=shiny_inc` - Increment count (+1)
* `/?action=shiny_dec` - Decrement count (-1)
* `/?action=shiny_reset` - Reset count to 0
* `/?action=set_shiny_target&name=Rayquaza&method=Soft+Resets` - Set hunting target & method

### Task Queue Management
* `/?action=task_nav&step=next` - Advance to next task
* `/?action=task_nav&step=prev` - Step back to previous task
* `/?action=set_tasks&tasks=Beat+Brock,Get+Running+Shoes,Clear+Mt+Moon` - Overwrite entire task list

### Party Management
* `/?action=team_add&name=charizard` - Add Pokémon to party
* `/?action=team_remove&index=0` - Remove Pokémon from party by 0-based index (0-5)

### Catch Counters
* `/?action=inc_counter&name=Pidgey` - Increment catch target (+1)
* `/?action=dec_counter&name=Pidgey` - Decrement catch target (-1, auto-removes at 0)
* `/?action=add_counters&counter_list=Caterpie+3,Rattata+2` - Add amounts to multiple targets
* `/?action=set_counters&counter_list=Abra+1,Gastly+2` - Overwrite entire catch targets list

### EV Training Tracker
* `/?action=ev_add_target` - Add active target Pokémon's EV yield to current tally
* `/?action=ev_adjust&stat=speed&amt=2` - Adjust specific EV stat (stats: hp, attack, defense, special-attack, special-defense, speed; negative values allowed)
* `/?action=ev_reset` - Reset all EV stats to 0

---

## License

This project is licensed under the [MIT License](LICENSE).
