# Pokémon Stream Director & Remote Hub

Built to remove friction when doing pokemon streams and allow me to EASILY display a pokemon core stats. I am not a front end developer and kind of hate html, so I used AI to write the vast majority of the front end, I just hand tweaked some stuff to fit better.

A lightweight, self-hosted dashboard for Pokémon streamers and challenge runners. 
	built with standard Python and PokéAPI (`pokebase`), 
	it lets you inspect Pokémon stats/weaknesses on the fly, 
	manage your live party, track task queues, track shinies seen
	and control catch counters right from your phone.

Includes ready-to-use browser source overlays for showing a target pokemon, the list youre aiming to catch, or hell whatever task youre working on. 

---

## Features

* **Quick Scanner:** Fuzzy search any Pokémon to pull live base stats, BST, type weaknesses, catch rates, evolutions, and level-up / TM movepools.
* **OBS Browser Overlays:** Dedicated transparent overlays for your active inspected Pokémon and current 6-member party.
* **Mobile Remote (`/remote`):** Tap-to-decrement catch counters, and tap-to=increment shiny counters, and navigate your stream task queue from your phone.
* **Persistent Local Files:** Saves party rosters, catch targets, video messages, and tasks directly to simple local files (`.txt` and `.json`).

---

## Requirements

* Python 3.10+
* pokebase
* urllib
* The ability to troubleshoot

---

## Installation & Setup

1. Clone or download this repo:
	```
	git clone https://github.com/marmadukian/pokemon-stream-director.git
	cd pokemon-stream-director
	```

2. Install dependencies:
	pip install pokebase, urllib

3. Run the server:
	python pkmn_server.py

4. READ THE ENDPOINTS PRINTED:
	I assume that you are technically adept enough to parse a url. 

4. Use the provided ip address on your phone's browser, your pc browser, or into a browser source in obs:
	http://[The compter's IP address]:1350
	