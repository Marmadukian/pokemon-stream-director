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

const MASTER_GAME_OPTIONS = [
    { value: "modern", label: "Modern / All Games" },
    { value: "red-blue", label: "Red / Blue" },
    { value: "yellow", label: "Yellow" },
    { value: "gold-silver", label: "Gold / Silver" },
    { value: "crystal", label: "Crystal" },
    { value: "ruby-sapphire", label: "Ruby / Sapphire" },
    { value: "emerald", label: "Emerald" },
    { value: "firered-leafgreen", label: "FireRed / LeafGreen" },
    { value: "colosseum", label: "Colosseum / XD" },
    { value: "diamond-pearl", label: "Diamond / Pearl" },
    { value: "platinum", label: "Platinum" },
    { value: "heartgold-soulsilver", label: "HeartGold / SoulSilver" },
    { value: "black-white", label: "Black / White" },
    { value: "black-2-white-2", label: "Black 2 / White 2" },
    { value: "x-y", label: "X / Y" },
    { value: "omega-ruby-alpha-sapphire", label: "OR / AS" },
    { value: "sun-moon", label: "Sun / Moon" },
    { value: "ultra-sun-ultra-moon", label: "US / UM" },
    { value: "lets-go-pikachu-lets-go-eevee", label: "Let's Go Pikachu / Eevee" },
    { value: "sword-shield", label: "Sword / Shield" },
    { value: "brilliant-diamond-and-shining-pearl", label: "BD / SP" },
    { value: "legends-arceus", label: "Legends: Arceus" },
    { value: "scarlet-violet", label: "Scarlet / Violet" }
];

/**
 * Helper to populate a select element safely while avoiding duplicate options.
 */
function fillSelectOptions(selectEl, optionsList, defaultPrefixOption = null) {
    if (!selectEl) return;

    // Save current selection if one was already active
    const previousVal = selectEl.value;
    selectEl.innerHTML = '';

    if (defaultPrefixOption) {
        const defaultOpt = document.createElement('option');
        defaultOpt.value = defaultPrefixOption.value;
        defaultOpt.textContent = defaultPrefixOption.label;
        selectEl.appendChild(defaultOpt);
    }

    optionsList.forEach(optData => {
        const opt = document.createElement('option');
        opt.value = optData.value;
        opt.textContent = optData.label;
        selectEl.appendChild(opt);
    });

    if (previousVal) {
        selectEl.value = previousVal;
    }
}

/**
 * Populates walkthrough-game-select, game-filter-select, and target-gen-select.
 * Binds their change events directly to the central version coordinator.
 */
function populateAllVersionDropdowns() {
    // 1. Walkthrough Game Select
    const walkthroughSelect = document.getElementById('walkthrough-game-select');
    fillSelectOptions(
        walkthroughSelect,
        MASTER_GAME_OPTIONS,
        { value: "", label: "-- Choose Walkthrough Game --" }
    );
    if (walkthroughSelect) {
        walkthroughSelect.onchange = onWalkthroughGameChange;
    }

    // 2. Game / Route Filter Select (Supports "ALL")
    const routeFilterSelect = document.getElementById('game-filter-select') || document.getElementById('route-version-filter');
    fillSelectOptions(
        routeFilterSelect,
        MASTER_GAME_OPTIONS,
        { value: "ALL", label: "-- All Versions --" }
    );
    if (routeFilterSelect) {
        routeFilterSelect.onchange = () => filterGameVersion();
    }

    // 3. Target Inspector Gen Select
    const targetGenSelect = document.getElementById('target-gen-select');
    fillSelectOptions(targetGenSelect, MASTER_GAME_OPTIONS);
    if (targetGenSelect) {
        targetGenSelect.onchange = () => {
            if (typeof setGlobalGameVersion === 'function') {
                setGlobalGameVersion(targetGenSelect.value);
            }
        };
    }
}

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
const VERSION_TO_GEN_JS = {
    // Individual versions
    "red": "generation-i", "blue": "generation-i", "yellow": "generation-i",
    "gold": "generation-ii", "silver": "generation-ii", "crystal": "generation-ii",
    "ruby": "generation-iii", "sapphire": "generation-iii", "emerald": "generation-iii",
    "firered": "generation-iii", "leafgreen": "generation-iii", "colosseum": "generation-iii", "xd": "generation-iii",
    "diamond": "generation-iv", "pearl": "generation-iv", "platinum": "generation-iv",
    "heartgold": "generation-iv", "soulsilver": "generation-iv",
    "black": "generation-v", "white": "generation-v", "black-2": "generation-v", "white-2": "generation-v",
    "x": "generation-vi", "y": "generation-vi", "omega-ruby": "generation-vi", "alpha-sapphire": "generation-vi",
    "sun": "generation-vii", "moon": "generation-vii", "ultra-sun": "generation-vii", "ultra-moon": "generation-vii",
    "lets-go-pikachu": "generation-vii", "lets-go-eevee": "generation-vii",
    "sword": "generation-viii", "shield": "generation-viii", "brilliant-diamond": "generation-viii", "shining-pearl": "generation-viii", "legends-arceus": "generation-viii",
    "scarlet": "generation-ix", "violet": "generation-ix",

    // MASTER_GAME_OPTIONS group keys
    "red-blue": "generation-i",
    "gold-silver": "generation-ii",
    "gold-silver-crystal": "generation-ii",
    "ruby-sapphire": "generation-iii",
    "firered-leafgreen": "generation-iii",
    "diamond-pearl": "generation-iv",
    "diamond-pearl-platinum": "generation-iv",
    "heartgold-soulsilver": "generation-iv",
    "black-white": "generation-v",
    "black-2-white-2": "generation-v",
    "omega-ruby-alpha-sapphire": "generation-vi",
    "sun-moon": "generation-vii",
    "ultra-sun-ultra-moon": "generation-vii",
    "lets-go-pikachu-lets-go-eevee": "generation-vii",
    "sword-shield": "generation-viii",
    "brilliant-diamond-and-shining-pearl": "generation-viii",
    "scarlet-violet": "generation-ix",
    "modern": "generation-ix"
};
        const HISTORICAL_EV_OVERRIDES = {
            "roselia": { "generation-iii": "1 Sp. Atk" },
            "feebas": { "generation-iii": "1 Speed" },
            "chimecho": { "generation-iii": "1 Sp. Atk" },
            "porygon": { "generation-iii": "1 Atk" },
            "volbeat": { "generation-iii": "1 Atk" },
            "illumise": { "generation-iii": "1 Sp. Atk" },
            "ralts": { "generation-iii": "1 Sp. Atk" }
        };

        const GEN_ORDER_LIST = [
            "generation-i", "generation-ii", "generation-iii", "generation-iv",
            "generation-v", "generation-vi", "generation-vii", "generation-viii", "generation-ix"
        ];

// Global walkthrough task data (can also be loaded via fetch('/walkthrough_tasks.json'))
const walkthroughData = {
  "red-blue": {
    "Part 1: Pallet Town to Pewter City": "Pallet Town, Route 1, Viridian City, Route 22, Route 2, Viridian Forest, Pewter City, Pewter Gym",
    "Part 2: Pewter City to Cerulean City": "Route 3, Mt. Moon, Route 4, Cerulean City, Cerulean Gym",
    "Part 3: Cerulean City to Vermilion City": "Route 24, Route 25, Sea Cottage, Route 5, Underground Path, Route 6, Vermilion City, S.S. Anne, Vermilion Gym",
    "Part 4: Vermilion City to Celadon City": "Route 11, Diglett's Cave, Route 2, Route 9, Route 10, Rock Tunnel, Lavender Town, Route 8, Route 7, Celadon City, Celadon Gym, Rocket Hideout, Pokémon Tower",
    "Part 5: Celadon City to Fuchsia City": "Route 16, Route 17, Route 18, Fuchsia City, Fuchsia Gym, Safari Zone, Route 12, Route 13, Route 14, Route 15",
    "Part 6: Saffron City & Silph Co": "Saffron City, Silph Co., Saffron Gym, Fighting Dojo",
    "Part 7: Cinnabar Island & Viridian Gym": "Route 19, Seafoam Islands, Route 20, Cinnabar Island, Pokémon Mansion, Cinnabar Gym, Power Plant, Route 21, Viridian Gym",
    "Part 8: Indigo Plateau": "Route 23, Victory Road, Indigo Plateau, Lorelei, Bruno, Agatha, Lance, Champion Rival, Cerulean Cave"
  },
  "yellow": {
    "Part 1: Pallet Town to Pewter City": "Pallet Town, Starter Pikachu, Route 1, Viridian City, Route 22, Route 2, Viridian Forest, Pewter City, Pewter Gym",
    "Part 2: Pewter City to Cerulean City": "Route 3, Mt. Moon, Route 4, Cerulean City, Cerulean Gym, Bulbasaur Gift",
    "Part 3: Cerulean City to Vermilion City": "Route 24, Charmander Gift, Route 25, Sea Cottage, Route 5, Route 6, Vermilion City, Squirtle Gift, S.S. Anne, Vermilion Gym",
    "Part 4: Vermilion City to Celadon City": "Route 11, Diglett's Cave, Route 9, Route 10, Rock Tunnel, Lavender Town, Route 8, Celadon City, Celadon Gym, Rocket Hideout, Pokémon Tower",
    "Part 5: Celadon City to Fuchsia City": "Route 16, Route 17, Route 18, Fuchsia City, Fuchsia Gym, Safari Zone, Route 12, Route 13, Route 14, Route 15",
    "Part 6: Saffron City & Silph Co": "Silph Co., Saffron Gym, Fighting Dojo, Lapras Gift",
    "Part 7: Cinnabar Island & Viridian Gym": "Route 19, Seafoam Islands, Route 20, Cinnabar Island, Pokémon Mansion, Cinnabar Gym, Power Plant, Route 21, Viridian Gym",
    "Part 8: Indigo Plateau": "Route 23, Victory Road, Indigo Plateau, Elite Four, Champion Rival, Cerulean Cave"
  },
  "gold-silver-crystal": {
    "Part 1: New Bark Town to Violet City": "New Bark Town, Route 29, Cherrygrove City, Route 30, Route 31, Violet City, Sprout Tower, Violet Gym",
    "Part 2: Violet City to Goldenrod City": "Route 32, Ruins of Alph, Union Cave, Route 33, Azalea Town, Slowpoke Well, Azalea Gym, Ilex Forest, Route 34, Goldenrod City, Goldenrod Gym",
    "Part 3: Goldenrod City to Ecruteak City": "National Park, Route 35, Route 36, Route 37, Ecruteak City, Burned Tower, Ecruteak Gym, Tin Tower",
    "Part 4: Ecruteak City to Cianwood City": "Route 38, Route 39, Olivine City, Route 40, Route 41, Whirl Islands, Cianwood City, Cianwood Gym",
    "Part 5: Olivine Gym to Mahogany Town": "Glitter Lighthouse, Olivine Gym, Route 42, Mt. Mortar, Mahogany Town, Route 43, Lake of Rage, Team Rocket HQ, Mahogany Gym",
    "Part 6: Goldenrod Underground & Blackthorn": "Goldenrod Radio Tower, Underground Warehouse, Route 44, Ice Path, Blackthorn City, Blackthorn Gym, Dragon's Den",
    "Part 7: Johto Pokémon League": "Route 45, Route 46, Route 27, Tohjo Falls, Route 26, Victory Road, Indigo Plateau, Will, Koga, Bruno, Karen, Lance",
    "Part 8: Kanto Badges 1-4": "Vermilion City, Vermilion Gym, Saffron City, Saffron Gym, Cerulean City, Power Plant, Route 24, Route 25, Cerulean Gym, Route 9, Route 10, Rock Tunnel, Lavender Town, Celadon City, Celadon Gym",
    "Part 9: Kanto Badges 5-8 & Mt. Silver": "Route 16, Route 17, Route 18, Fuchsia City, Fuchsia Gym, Route 19, Route 20, Seafoam Islands, Blaine, Route 21, Cinnabar Island, Route 1, Pallet Town, Viridian City, Pewter City, Pewter Gym, Route 28, Mt. Silver, Red"
  },
  "ruby-sapphire": {
    "Part 1: Littleroot Town to Rustboro City": "Littleroot Town, Route 101, Oldale Town, Route 103, Route 102, Petalburg City, Route 104, Petalburg Woods, Rustboro City, Rustboro Gym",
    "Part 2: Rustboro City to Dewford Town": "Route 116, Rusturf Tunnel, Route 104, Route 105, Route 106, Dewford Town, Dewford Gym, Granite Cave",
    "Part 3: Dewford Town to Mauville City": "Route 107, Route 108, Route 109, Slateport City, Oceanic Museum, Route 110, Mauville City, Mauville Gym, Cycling Road",
    "Part 4: Mauville City to Fallarbor Town": "Route 117, Verdanturf Town, Rusturf Tunnel shortcut, Route 111, Route 112, Fiery Path, Route 113, Fallarbor Town",
    "Part 5: Fallarbor Town to Lavaridge Town": "Route 114, Meteor Falls, Route 115, Mt. Chimney, Jagged Pass, Lavaridge Town, Lavaridge Gym",
    "Part 6: Lavaridge Town to Fortree City": "Petalburg Gym, Route 118, Route 119, Weather Institute, Fortree City, Route 120, Fortree Gym",
    "Part 7: Fortree City to Mossdeep City": "Route 121, Safari Zone, Lilycove City, Mt. Pyre, Team Hideout, Route 124, Mossdeep City, Mossdeep Gym, Space Center",
    "Part 8: Mossdeep City to Sootopolis City": "Route 125, Shoal Cave, Route 126, Route 127, Route 128, Seafloor Cavern, Route 126 Underwater, Sootopolis City, Cave of Origin, Sootopolis Gym",
    "Part 9: Ever Grande City & League": "Route 129, Route 130, Route 131, Pacifidlog Town, Route 132, Route 133, Route 134, Ever Grande City, Victory Road, Sidney, Phoebe, Glacia, Drake, Steven"
  },
  "emerald": {
    "Part 1: Littleroot Town to Rustboro City": "Littleroot Town, Route 101, Oldale Town, Route 103, Route 102, Petalburg City, Route 104, Petalburg Woods, Rustboro City, Rustboro Gym",
    "Part 2: Rustboro City to Dewford Town": "Route 116, Rusturf Tunnel, Devon Corp, Dewford Town, Dewford Gym, Granite Cave",
    "Part 3: Dewford Town to Mauville City": "Route 109, Slateport City, Museum, Route 110, Mauville City, Mauville Gym",
    "Part 4: Mauville City to Lavaridge Town": "Route 117, Verdanturf Town, Route 111, Route 112, Fiery Path, Route 113, Fallarbor Town, Route 114, Meteor Falls, Mt. Chimney, Jagged Pass, Lavaridge City, Lavaridge Gym",
    "Part 5: Lavaridge Town to Fortree City": "Desert Ruins, Petalburg Gym, Route 118, Route 119, Weather Institute, Fortree City, Route 120, Devon Scope, Fortree Gym",
    "Part 6: Fortree City to Mossdeep City": "Route 121, Safari Zone, Lilycove City, Mt. Pyre, Magma Hideout, Aqua Hideout, Route 124, Mossdeep City, Mossdeep Gym, Space Center",
    "Part 7: Awakening the Legends": "Route 127, Route 128, Seafloor Cavern, Sootopolis City, Route 129, Route 130, Route 131, Sky Pillar, Rayquaza Awakening, Sootopolis Gym",
    "Part 8: Ever Grande City & Frontier": "Ever Grande City, Victory Road, Sidney, Phoebe, Glacia, Drake, Wallace, Battle Frontier"
  },
  "firered-leafgreen": {
    "Part 1: Pallet Town to Pewter City": "Pallet Town, Route 1, Viridian City, Oak's Parcel, Route 22, Route 2, Viridian Forest, Pewter City, Pewter Gym",
    "Part 2: Pewter City to Cerulean City": "Route 3, Mt. Moon, Route 4, Cerulean City, Cerulean Gym",
    "Part 3: Cerulean City to Vermilion City": "Route 24, Route 25, Bill's Cottage, Route 5, Route 6, Vermilion City, S.S. Anne, Vermilion Gym",
    "Part 4: Vermilion City to Celadon City": "Route 11, Diglett's Cave, Route 9, Route 10, Rock Tunnel, Lavender Town, Route 8, Celadon City, Celadon Gym, Rocket Hideout, Pokémon Tower",
    "Part 5: Celadon City to Fuchsia City": "Route 16, Cycling Road, Route 18, Fuchsia City, Fuchsia Gym, Safari Zone, Route 12, Route 13, Route 14, Route 15",
    "Part 6: Saffron City & Sevii Islands 1-3": "Silph Co., Saffron Gym, One Island, Treasure Beach, Two Island, Cape Brink, Three Island, Berry Forest",
    "Part 7: Cinnabar Island to Viridian Gym": "Route 19, Seafoam Islands, Route 20, Cinnabar Island, Pokémon Mansion, Cinnabar Gym, Power Plant, Viridian Gym",
    "Part 8: Indigo Plateau & Post-Game": "Route 23, Victory Road, Lorelei, Bruno, Agatha, Lance, Blue, Four Island, Icefall Cave, Five Island, Rocket Warehouse, Six Island, Ruin Valley, Dotted Hole, Seven Island, Cerulean Cave, Mewtwo"
  },
  "diamond-pearl-platinum": {
    "Part 1: Twinleaf Town to Oreburgh City": "Twinleaf Town, Lake Verity, Route 201, Sandgem Town, Route 202, Jubilife City, Route 204, Ravaged Path, Route 203, Oreburgh Gate, Oreburgh City, Oreburgh Mine, Oreburgh Gym",
    "Part 2: Oreburgh City to Eterna City": "Route 204, Floaroma Town, Valley Windworks, Route 205, Eterna Forest, Eterna City, Eterna Gym, Team Galactic Eterna Building",
    "Part 3: Eterna City to Hearthome City": "Route 206 Cycling Road, Route 207, Mt. Coronet, Route 208, Hearthome City, Amity Square, Route 209, Lost Tower, Solaceon Town, Solaceon Ruins",
    "Part 4: Solaceon Town to Veilstone City": "Route 210, Route 215, Veilstone City, Veilstone Gym, Galactic Warehouse",
    "Part 5: Veilstone City to Pastoria City": "Route 214, Valor Lakefront, Route 213, Pastoria City, Great Marsh, Pastoria Gym",
    "Part 6: Pastoria City to Canalave City": "Route 212, Pokémon Mansion, Route 210 North, Celestic Town, Fuego Ironworks, Route 218, Canalave City, Canalave Gym, Iron Island",
    "Part 7: Canalave City to Snowpoint City": "Lake Valor, Lake Verity, Mt. Coronet North, Route 216, Route 217, Acuity Lakefront, Snowpoint City, Snowpoint Gym, Lake Acuity",
    "Part 8: Galactic HQ & Spear Pillar": "Veilstone Galactic HQ, Mt. Coronet Peak, Spear Pillar, Distortion World, Sunyshore City, Sunyshore Gym",
    "Part 9: Sinnoh Pokémon League": "Route 222, Route 223, Victory Road, Aaron, Bertha, Flint, Lucian, Cynthia"
  },
  "heartgold-soulsilver": {
    "Part 1: New Bark Town to Violet City": "New Bark Town, Route 29, Cherrygrove City, Route 30, Mr. Pokémon, Route 31, Violet City, Sprout Tower, Violet Gym",
    "Part 2: Violet City to Goldenrod City": "Route 32, Ruins of Alph, Union Cave, Route 33, Azalea Town, Slowpoke Well, Azalea Gym, Ilex Forest, Route 34, Goldenrod City, Goldenrod Gym, Pokéathlon Dome",
    "Part 3: Goldenrod City to Ecruteak City": "Route 35, National Park, Route 36, Route 37, Ecruteak City, Burned Tower, Ecruteak Gym, Bell Tower",
    "Part 4: Ecruteak City to Cianwood City": "Route 38, Route 39, Olivine City, Route 40, Route 41, Whirl Islands, Cianwood City, Cianwood Gym, Safari Zone Gate",
    "Part 5: Olivine Gym to Mahogany Town": "Glitter Lighthouse, Olivine Gym, Route 42, Mt. Mortar, Mahogany Town, Route 43, Lake of Rage, Rocket Hideout, Mahogany Gym",
    "Part 6: Goldenrod Radio Tower to Blackthorn": "Goldenrod Radio Tower, Underground Warehouse, Route 44, Ice Path, Blackthorn City, Blackthorn Gym, Dragon's Den, Whirl Islands / Bell Tower Legendaries",
    "Part 7: Johto Pokémon League": "Route 45, Route 46, Route 27, Tohjo Falls, Route 26, Victory Road, Indigo Plateau, Will, Koga, Bruno, Karen, Lance",
    "Part 8: Kanto Badges 1-4": "S.S. Aqua, Vermilion City, Vermilion Gym, Saffron City, Saffron Gym, Cerulean City, Route 24, Route 25, Power Plant, Cerulean Gym, Route 9, Route 10, Rock Tunnel, Lavender Town, Celadon City, Celadon Gym",
    "Part 9: Kanto Badges 5-8 & Mt. Silver": "Route 16, Route 17, Route 18, Fuchsia City, Fuchsia Gym, Route 19, Route 20, Seafoam Islands, Blaine, Route 21, Cinnabar Island, Route 1, Pallet Town, Viridian City, Pewter City, Pewter Gym, Route 22, Route 28, Mt. Silver, Red"
  },
  "black-white": {
    "Part 1: Nuvema Town to Striaton City": "Nuvema Town, Route 1, Accumula Town, Route 2, Striaton City, Dreamyard, Striaton Gym",
    "Part 2: Striaton City to Nacrene City": "Route 3, Wellspring Cave, Nacrene City, Nacrene Gym, Pinwheel Forest",
    "Part 3: Nacrene City to Castelia City": "Skyarrow Bridge, Castelia City, Castelia Gym, Route 4, Desert Resort, Relic Castle",
    "Part 4: Castelia City to Nimbasa City": "Nimbasa City, Nimbasa Gym, Battle Subway, Route 5, Route 16, Lostlorn Forest",
    "Part 5: Nimbasa City to Driftveil City": "Driftveil Drawbridge, Driftveil City, Cold Storage, Driftveil Gym",
    "Part 6: Driftveil City to Mistralton City": "Route 6, Chargestone Cave, Mistralton City, Route 7, Celestial Tower, Mistralton Gym",
    "Part 7: Mistralton City to Icirrus City": "Twist Mountain, Icirrus City, Dragonspiral Tower, Route 8, Moor of Icirrus, Icirrus Gym",
    "Part 8: Icirrus City to Opelucid City": "Route 9, Tubeline Bridge, Shopping Mall Nine, Route 10, Opelucid City, Opelucid Gym",
    "Part 9: Unova League & N's Castle": "Victory Road, Shauntal, Grimsley, Caitlin, Marshal, N's Castle, Reshiram / Zekrom, N, Ghetsis"
  },
  "black-2-white-2": {
    "Part 1: Aspertia City to Virbank City": "Aspertia City, Route 19, Floccesy Town, Route 20, Floccesy Ranch, Aspertia Gym, Virbank City, Virbank Complex, Virbank Gym",
    "Part 2: Virbank City to Castelia City": "Pokéstar Studios, Castelia City, Castelia Sewers, Castelia Gym, Route 4, Desert Resort, Relic Castle",
    "Part 3: Castelia City to Nimbasa City": "Join Avenue, Nimbasa City, Nimbasa Gym, Anville Town, Route 5, Driftveil Drawbridge",
    "Part 4: Nimbasa City to Driftveil City": "Driftveil City, Driftveil Gym, Pokémon World Tournament, Plasma Frigate, Relic Passage",
    "Part 5: Driftveil City to Mistralton City": "Route 6, Chargestone Cave, Mistralton City, Route 7, Celestial Tower, Mistralton Gym",
    "Part 6: Mistralton City to Opelucid City": "Lentimas Town, Reversal Mountain, Undella Town, Route 13, Lacunosa Town, Route 12, Village Bridge, Route 11, Opelucid City, Opelucid Gym",
    "Part 7: Opelucid City to Humilau City": "Frozen Opelucid, Marine Tube, Humilau City, Humilau Gym, Route 21, Seaside Cave",
    "Part 8: Giant Chasm & Plasma Frigate": "Route 22, Giant Chasm, Plasma Frigate, Colress, Kyurem, Ghetsis",
    "Part 9: Victory Road & League": "Route 23, Victory Road, Shauntal, Grimsley, Caitlin, Marshal, Champion Iris"
  },
  "x-y": {
    "Part 1: Vaniville Town to Santalune City": "Vaniville Town, Route 1, Aquacorde Town, Route 2, Santalune Forest, Route 3, Santalune City, Santalune Gym",
    "Part 2: Santalune City to Lumiose City": "Route 4, Lumiose City, Sycamore Lab, Route 5, Camphrier Town, Route 7, Route 6, Parfum Palace",
    "Part 3: Camphrier Town to Cyllage City": "Connecting Cave, Route 8, Ambrette Town, Route 9, Glittering Cave, Cyllage City, Cyllage Gym",
    "Part 4: Cyllage City to Shalour City": "Route 10, Geosenge Town, Route 11, Reflection Cave, Shalour City, Tower of Mastery, Shalour Gym",
    "Part 5: Shalour City to Coumarine City": "Route 12, Azure Bay, Coumarine City, Coumarine Gym",
    "Part 6: Coumarine City to Laverre City": "Route 13, Kalos Power Plant, Lumiose City Gym, Route 14, Laverre City, Poké Ball Factory, Laverre Gym",
    "Part 7: Laverre City to Anistar City": "Route 15, Dendemille Town, Frost Cavern, Route 16, Route 17, Anistar City, Anistar Gym",
    "Part 8: Team Flare Secret HQ": "Lysandre Labs, Geosenge Team Flare HQ, Xerneas / Yveltal, Route 18, Couriway Town, Route 19, Snowbelle City, Winding Woods, Pokémon Village, Snowbelle Gym",
    "Part 9: Victory Road & Kalos League": "Route 21, Victory Road, Malva, Wikstrom, Drasna, Siebold, Champion Diantha, Kiloude City"
  },
  "omega-ruby-alpha-sapphire": {
    "Part 1: Littleroot Town to Rustboro City": "Littleroot Town, Route 101, Oldale Town, Route 103, Route 102, Petalburg City, Route 104, Petalburg Woods, Rustboro City, Rustboro Gym",
    "Part 2: Rustboro City to Dewford Town": "Route 116, Rusturf Tunnel, Devon Corporation, Dewford Town, Dewford Gym, Granite Cave",
    "Part 3: Dewford Town to Mauville City": "Route 107, Route 108, Route 109, Slateport City, Oceanic Museum, Route 110, Mauville City, Mauville Gym",
    "Part 4: Mauville City to Lavaridge Town": "Route 117, Verdanturf Town, Route 111, Route 112, Fiery Path, Route 113, Fallarbor Town, Route 114, Meteor Falls, Mt. Chimney, Jagged Pass, Lavaridge Town, Lavaridge Gym",
    "Part 5: Lavaridge Town to Fortree City": "Petalburg Gym, Route 118, Southern Island, Latios / Latias, Route 119, Weather Institute, Fortree City, Route 120, Fortree Gym",
    "Part 6: Fortree City to Mossdeep City": "Route 121, Safari Zone, Lilycove City, Mt. Pyre, Team Hideout, Route 124, Mossdeep City, Mossdeep Gym, Space Center",
    "Part 7: Mossdeep City to Sootopolis City": "Route 127, Route 128, Seafloor Cavern, Route 126, Sootopolis City, Cave of Origin, Primal Reversion, Sootopolis Gym",
    "Part 8: Ever Grande City & Delta Episode": "Route 129, Route 130, Route 131, Sky Pillar, Ever Grande City, Victory Road, Sidney, Phoebe, Glacia, Drake, Steven, Delta Episode, Rayquaza, Deoxys"
  },
  "sun-moon": {
    "Part 1: Melemele Island Trials": "Iki Town, Mahalo Trail, Route 1, Trainers' School, Hau'oli City, Route 2, Hau'oli Cemetery, Verdant Cavern, Melemele Trial, Route 3, Melemele Meadow, Iki Town Grand Trial",
    "Part 2: Akala Island - Brooklet Hill": "Heahea City, Route 4, Paniola Town, Paniola Ranch, Route 5, Brooklet Hill, Water Trial",
    "Part 3: Akala Island - Fire & Grass Trials": "Route 6, Royal Avenue, Battle Royal Dome, Route 7, Wela Volcano Park, Fire Trial, Route 8, Lush Jungle, Grass Trial",
    "Part 4: Akala Grand Trial & Aether Paradise": "Diglett's Tunnel, Route 9, Konikoni City, Memorial Hill, Akala Outskirts, Ruins of Life, Akala Grand Trial, Aether Paradise",
    "Part 5: Ula'ula Island - Electric & Ghost Trials": "Malie City, Malie Garden, Route 10, Mount Hokulani, Electric Trial, Route 11, Route 12, Blush Mountain, Route 13, Haina Desert, Tapu Village, Route 14, Abandoned Thrifty Megamart, Ghost Trial",
    "Part 6: Ula'ula Island - Po Town & Grand Trial": "Route 15, Aether House, Route 16, Ula'ula Meadow, Route 17, Po Town, Shady House, Malie Port Grand Trial",
    "Part 7: Aether Paradise Infiltration": "Aether Paradise B1F, Secret Labs, Master Docks, Lusamine, Ultra Beast Nihilego",
    "Part 8: Poni Island & Altar of the Sunne / Moone": "Seafolk Village, Poni Wilds, Ancient Poni Path, Vast Poni Canyon, Poni Grand Trial, Altar of Sunne/Moone, Ultra Space, Solgaleo / Lunala",
    "Part 9: Mount Lanakila & Pokémon League": "Mount Lanakila, Hala, Olivia, Acerola, Kahili, Professor Kukui"
  },
  "ultra-sun-ultra-moon": {
    "Part 1: Melemele Island Trials": "Iki Town, Mahalo Trail, Route 1, Trainers' School, Hau'oli City, Route 2, Hau'oli Cemetery, Big Wave Beach, Verdant Cavern, Melemele Trial, Route 3, Melemele Meadow, Iki Town Grand Trial",
    "Part 2: Akala Island - Brooklet Hill & Volcano": "Heahea City, Route 4, Paniola Town, Paniola Ranch, Route 5, Brooklet Hill, Water Trial, Route 6, Royal Avenue, Route 7, Wela Volcano Park, Fire Trial",
    "Part 3: Akala Island - Grass Trial & Grand Trial": "Route 8, Lush Jungle, Grass Trial, Diglett's Tunnel, Route 9, Konikoni City, Memorial Hill, Ruins of Life, Akala Grand Trial, Hano Grand Resort, Aether Paradise",
    "Part 4: Ula'ula Island - Electric & Ghost Trials": "Malie City, Malie Garden, Route 10, Mount Hokulani, Electric Trial, Route 11, Route 12, Blush Mountain, Route 13, Tapu Village, Route 14, Abandoned Thrifty Megamart, Ghost Trial",
    "Part 5: Ula'ula Island - Po Town & Grand Trial": "Route 15, Aether House, Route 16, Ula'ula Meadow, Route 17, Po Town, Shady House, Malie Port Grand Trial",
    "Part 6: Aether Paradise & Ultra Recon Squad": "Aether Paradise Labs, Docks, President's Room, Nihilego, Ultra Recon Squad",
    "Part 7: Poni Island Trials & Ultra Megalopolis": "Seafolk Village, Poni Wilds, Ancient Poni Path, Exeggutor Island, Vast Poni Canyon, Dragon Trial, Altar of Sunne/Moone, Ultra Warp Ride, Ultra Megalopolis, Megalo Tower, Ultra Necrozma",
    "Part 8: Mount Lanakila & Pokémon League": "Mina's Fairy Trial, Mount Lanakila, Molayne, Olivia, Acerola, Kahili, Hau, Episode RR"
  }
};

walkthroughData["gold-silver"] = walkthroughData["gold-silver-crystal"];
walkthroughData["crystal"] = walkthroughData["gold-silver-crystal"];
walkthroughData["diamond-pearl"] = walkthroughData["diamond-pearl-platinum"];
walkthroughData["platinum"] = walkthroughData["diamond-pearl-platinum"];

const VERSION_STORAGE_KEY = 'marmamon_active_version';

function setGlobalGameVersion(newGame, skipBackendSync = false) {
    if (!newGame) return;
    const cleanGame = newGame.toLowerCase().trim();

    // 1. Sync all select inputs across modules
    const selectors = [
        '#target-gen-select',
        '#walkthrough-game-select',
        '#global-game-select',
        '#game-filter-select',
        '#route-version-filter'
    ];
    selectors.forEach(sel => {
        const el = document.querySelector(sel);
        if (el && el.value.toLowerCase() !== cleanGame) {
            el.value = cleanGame;
        }
    });

    // 2. Persist to central storage
    localStorage.setItem(VERSION_STORAGE_KEY, cleanGame);

    // 3. Persist to Python backend
    if (!skipBackendSync) {
        const endpoint = window.location.pathname.includes('/remote') ? '/remote' : '/';
        fetch(`${endpoint}?action=set_game_version&version=${encodeURIComponent(cleanGame)}`)
            .catch(() => {});
    }

    // 4. Update all downstream views
    if (typeof syncWalkthroughParts === 'function') syncWalkthroughParts(cleanGame);
    if (typeof updateTargetGenView === 'function') updateTargetGenView(cleanGame);
    if (typeof filterGameVersion === 'function') filterGameVersion(cleanGame);
}

/**
 * Call on page boot to align UI with Python backend / localStorage
 */
function initGlobalVersion(backendVersion) {
    const saved = backendVersion || localStorage.getItem(VERSION_STORAGE_KEY) || 'modern';
    setGlobalGameVersion(saved, true);
}

// Updates local storage / track state when manually unchecked
function onPokemonCheckboxChange(checkbox) {
    const rawName = checkbox.getAttribute('data-poke-name') || '';
    const name = rawName.split('(')[0].trim();
    if (!name) return;

    let deselected = JSON.parse(localStorage.getItem('deselected_pokemon') || '[]');
    if (!checkbox.checked) {
        if (!deselected.includes(name)) deselected.push(name);
    } else {
        deselected = deselected.filter(n => n !== name);
    }
    localStorage.setItem('deselected_pokemon', JSON.stringify(deselected));
}

// Gathers only CHECKED pokemon on the route and sends to add_counters
function trackAllRoutePokemon(e) {
    if (e && e.preventDefault) e.preventDefault();

    // Map: baseName (TitleCase) -> Set of ONLY what it evolves INTO (strictly downstream targets)
    const candidates = new Map();
    const activeContainer = document.querySelector('.tab-pane.active, .route-version-active, #active-route-content') || document;

    function registerCandidate(el) {
        if (el.offsetParent === null) return;

        const rawName = el.getAttribute('data-poke-name') || el.innerText.trim();
        if (!rawName) return;

        const cleanName = rawName.split('(')[0].trim();
        if (!cleanName || candidates.has(cleanName)) return;

        const card = el.closest('[data-evolutions], .pokemon-card, .route-row') || el;
        const rawEvoAttr = card.getAttribute('data-evolutions') || '[]';

        const downstreamEvos = new Set();
        try {
            const parsed = JSON.parse(rawEvoAttr);
            if (Array.isArray(parsed)) {
                // If it's a linear chain like ["Ekans", "Arbok (Lv. 22)"]
                // Find where the current pokemon sits in the chain
                const selfIndex = parsed.findIndex(item => {
                    const itemName = (item.includes('➔') ? item.split('➔')[0] : item).split('(')[0].trim().toLowerCase();
                    return itemName === cleanName.toLowerCase();
                });

                parsed.forEach((item, idx) => {
                    // Extract the target species name
                    const targetPart = item.includes('➔') ? item.split('➔').pop() : item;
                    const evoClean = targetPart.split('(')[0].trim().toLowerCase();

                    // Only count as downstream if it's strictly AFTER self, or has an explicit trigger/arrow
                    if (selfIndex !== -1) {
                        if (idx > selfIndex && evoClean !== cleanName.toLowerCase()) {
                            downstreamEvos.add(evoClean);
                        }
                    } else {
                        // Fallback: don't include self
                        if (evoClean && evoClean !== cleanName.toLowerCase()) {
                            downstreamEvos.add(evoClean);
                        }
                    }
                });
            }
        } catch (err) {
            console.warn(`Could not parse evolutions for ${cleanName}:`, rawEvoAttr);
        }

        candidates.set(cleanName, downstreamEvos);
    }

    // 1. Gather all candidates
    const allBoxes = activeContainer.querySelectorAll('.route-poke-checkbox');
    if (allBoxes.length > 0) {
        const checkedBoxes = activeContainer.querySelectorAll('.route-poke-checkbox:checked');
        checkedBoxes.forEach(cb => registerCandidate(cb));
    } else {
        // Only use text/attribute fallback if no checkboxes exist in this view
        activeContainer.querySelectorAll('.poke-name, [data-poke-name]').forEach(el => registerCandidate(el));
    }

    if (candidates.size === 0) return;

    // 2. Collect ALL evolved forms that are descendants of candidate base forms
    const evolvedTargets = new Set();
    candidates.forEach((downstreamSet) => {
        downstreamSet.forEach(evo => evolvedTargets.add(evo));
    });

    // 3. Keep candidates unless they are a known descendant of an earlier stage present
    const finalNames = [];
    const skippedNames = [];
    candidates.forEach((_, name) => {
        if (evolvedTargets.has(name.toLowerCase())) {
            skippedNames.push(name);
        } else {
            finalNames.push(name);
        }
    });

    console.log("[TRACK ROUTE] Final Keep:", finalNames);
    console.log("[TRACK ROUTE] Skipped Evolved Stages:", skippedNames);

    if (finalNames.length === 0) return;

    const formattedList = finalNames.join(',');
    const listParam = encodeURIComponent(formattedList);
    const endpoint = window.location.pathname.includes('/remote') ? '/remote' : '/';

    fetch(`${endpoint}?action=add_counters&counter_list=${listParam}`)
        .then(() => {
            if (typeof renderCounters === 'function') renderCounters();
            else if (typeof loadCounters === 'function') loadCounters();
            else window.location.reload();
        })
        .catch(err => console.error("Error adding checked counters:", err));
}

// 1. Update UI Elements In-Place
function updateTaskCardUI(progress, name) {
    const progEl = document.getElementById('task-progress-display');
    const nameEl = document.getElementById('task-name-display');
    if (progEl) progEl.innerText = progress;
    if (nameEl) nameEl.innerText = name;
}

function syncExpState() {
    const growthRate = document.getElementById('target-growth-rate')?.value || 'medium-fast';
    const lvlFrom = document.getElementById('exp-from')?.value || '1';
    const lvlTo = document.getElementById('exp-to')?.value || '36';
    const expOutput = document.getElementById('exp-output')?.innerText || '0 EXP';
    const expPerKill = document.getElementById('exp-per-kill')?.value || '120';
    const kills = document.getElementById('grind-battles')?.innerText || '0 kills';
    const estTime = document.getElementById('grind-time')?.innerText || '~0m';

    const endpoint = window.location.pathname.includes('/remote') ? '/remote' : '/';
    fetch(`${endpoint}?action=sync_exp&growth_rate=${encodeURIComponent(growthRate)}&from=${encodeURIComponent(lvlFrom)}&to=${encodeURIComponent(lvlTo)}&exp=${encodeURIComponent(expOutput)}&per_kill=${encodeURIComponent(expPerKill)}&kills=${encodeURIComponent(kills)}&time=${encodeURIComponent(estTime)}`)
        .catch(err => console.error("EXP sync failed", err));
}

// 2. Bulbapedia Game Selection -> Populate Part Dropdown
function onWalkthroughGameChange() {
    const gameSelect = document.getElementById('walkthrough-game-select');
    if (!gameSelect) return;
    setGlobalGameVersion(gameSelect.value);
}

// Extracted so any game-change event can populate the parts list cleanly
function syncWalkthroughParts(chosenGame) {
    const partSelect = document.getElementById('walkthrough-part-select');
    if (!partSelect) return;

    partSelect.innerHTML = '<option value="">-- Choose Chapter Part --</option>';

    if (!chosenGame || typeof walkthroughData === 'undefined' || !walkthroughData[chosenGame]) {
        partSelect.disabled = true;
        return;
    }

    const parts = walkthroughData[chosenGame];
    Object.keys(parts).forEach(partTitle => {
        const opt = document.createElement('option');
        opt.value = partTitle;
        opt.textContent = partTitle;
        partSelect.appendChild(opt);
    });

    partSelect.disabled = false;
}

function calculateCatchOdds() {
    const hpSlider = document.getElementById('catch-hp-slider');
    const lvlInput = document.getElementById('catch-lvl-input');
    const statusSelect = document.getElementById('catch-status-select');
    const ballSelect = document.getElementById('catch-ball-select');

    const hp = hpSlider ? hpSlider.value : "100";
    const lvl = lvlInput ? lvlInput.value : "50";
    const status = statusSelect ? statusSelect.value : "1";
    const ball = ballSelect ? ballSelect.value : "poke";

    const hpDisp = document.getElementById('catch-hp-display');
    if (hpDisp) hpDisp.innerText = hp + '%';

    const lvlDisp = document.getElementById('catch-lvl-display');
    if (lvlDisp) lvlDisp.innerText = lvl;

    // Compute math
    let oddsStr = '--%';
    const catchRate = (window.activeTargetData && activeTargetData.catch_rate) ? activeTargetData.catch_rate : 45;
    const ballMultipliers = { 'poke': 1, 'great': 1.5, 'ultra': 2, 'master': 255 };
    const ballMod = ballMultipliers[ball] || 1;

    if (ball === 'master') {
        oddsStr = '100%';
    } else {
        const maxHp = 100;
        const curHp = Math.max(1, parseFloat(hp));
        const a = (((3 * maxHp - 2 * curHp) * catchRate * ballMod) / (3 * maxHp)) * parseFloat(status);
        
        if (a >= 255) {
            oddsStr = '100%';
        } else {
            const b = 65536 / Math.pow(255 / a, 0.1875);
            const p = Math.pow(b / 65536, 4) * 100;
            oddsStr = Math.min(100, Math.max(0.1, p)).toFixed(1) + '%';
        }
    }

    const oddsDisplay = document.getElementById('catch-odds-display');
    if (oddsDisplay) oddsDisplay.innerText = oddsStr;

    syncCatchState(hp, lvl, status, ball, oddsStr);
}

function syncCatchState(hp, lvl, status, ball, odds) {
    const targetName = (window.activeTargetData && activeTargetData.name) ? activeTargetData.name : "None";
    const endpoint = window.location.pathname.includes('/remote') ? '/remote' : '/';
    
    fetch(`${endpoint}?action=sync_catch&hp=${encodeURIComponent(hp)}&lvl=${encodeURIComponent(lvl)}&status=${encodeURIComponent(status)}&ball=${encodeURIComponent(ball)}&odds=${encodeURIComponent(odds)}&target=${encodeURIComponent(targetName)}`)
        .catch(err => console.error("Catch sync failed", err));
}


// 3. Load Selected Walkthrough Chapter into Server & DOM (In-Place)
function loadSelectedPartTasks() {
    const gameSelect = document.getElementById('walkthrough-game-select');
    const partSelect = document.getElementById('walkthrough-part-select');
    if (!gameSelect || !partSelect) return;

    const game = gameSelect.value;
    const part = partSelect.value;
    if (!game || !part || !walkthroughData[game] || !walkthroughData[game][part]) return;

    localStorage.setItem('selected_pokemon_part', part);

    // Grab the string directly from your object
    const taskString = walkthroughData[game][part];
    if (!taskString || typeof taskString !== 'string') return;

    // Populate the input and submit the form
    const input = document.querySelector('input[name="tasks"]');
    if (input) {
        input.value = taskString;
        input.form.submit();
    } else {
        window.location.href = `/?action=set_tasks&tasks=${encodeURIComponent(taskString)}`;
    }
}

// 4. Step Prev / Next (In-Place)
async function navigateTask(direction) {
    try {
        const res = await fetch(`/?action=task_nav&step=${direction}`);
        const data = await res.json(); // if your endpoint returns the new state
        // OR simply reload only if needed, but the Python guard above will prevent the wipe regardless!
    } catch (err) {
        console.error(err);
    }
    window.location.href = window.location.pathname.includes('/remote') ? '/remote' : '/';
}

// 5. Restore Saved Version on Page Load
document.addEventListener('DOMContentLoaded', () => {
    window.history.replaceState({}, document.title, window.location.pathname);
    const savedVer = localStorage.getItem('selected_pokemon_version');
    const gameSelect = document.getElementById('walkthrough-game-select');
    if (gameSelect && savedVer) {
        const exists = Array.from(gameSelect.options).some(opt => opt.value === savedVer);
        if (exists) {
            gameSelect.value = savedVer;
            onWalkthroughGameChange();
        }
    }
    const deselected = JSON.parse(localStorage.getItem('deselected_pokemon') || '[]');
document.querySelectorAll('.route-poke-checkbox').forEach(cb => {
    const name = (cb.getAttribute('data-poke-name') || '').split('(')[0].trim();
    if (deselected.includes(name)) {
        cb.checked = false;
    }
});
});       function updateTargetEVDisplay(selectedVer) {
            const evDisplay = document.getElementById('target-ev-yield-display');
            if (!evDisplay) return;

            // Target slug
            let targetSlug = "";
            if (window.activeTargetData && activeTargetData.slug) {
                targetSlug = activeTargetData.slug.toLowerCase().trim();
            } else if (window.activeTargetData && activeTargetData.name) {
                targetSlug = activeTargetData.name.toLowerCase().trim();
            } else {
                const nameEl = document.querySelector('h3');
                if (nameEl) targetSlug = nameEl.innerText.toLowerCase().trim();
            }

            // Normalize version string to simple alphanumeric/hyphen
            const verSlug = (selectedVer || "").toLowerCase().trim();

            // Match any Gen 3 keyword (covers "ruby", "sapphire", "ruby-sapphire", "ruby / sapphire", etc.)
            const isGen3 = /ruby|sapphire|emerald|firered|leafgreen|colosseum|xd|generation-iii/i.test(verSlug);

            // 1. Roselia Check
            if (targetSlug === "roselia") {
                evDisplay.innerText = isGen3 ? "1 Sp. Atk" : "2 Sp. Atk";
                return;
            }

            // 2. Other Historical EV Slugs
            const HISTORICAL_SLUGS = {
                "feebas": { gen3: "1 Speed", modern: "1 Sp. Def" },
                "chimecho": { gen3: "1 Sp. Atk", modern: "1 Sp. Atk, 1 Sp. Def" },
                "porygon": { gen3: "1 Atk", modern: "1 Sp. Atk" },
                "volbeat": { gen3: "1 Atk", modern: "1 Speed" },
                "illumise": { gen3: "1 Sp. Atk", modern: "1 Speed" },
                "ralts": { gen3: "1 Sp. Atk", modern: "1 Sp. Atk" }
            };

            if (HISTORICAL_SLUGS[targetSlug]) {
                evDisplay.innerText = isGen3 ? HISTORICAL_SLUGS[targetSlug].gen3 : HISTORICAL_SLUGS[targetSlug].modern;
                return;
            }

            // 3. Fallback to Modern Yield
            if (window.activeTargetData && activeTargetData.ev_yield) {
                const parts = [];
                for (const [stat, amt] of Object.entries(activeTargetData.ev_yield)) {
                    if (amt > 0) {
                        const cleanStat = stat.replace('special-attack', 'Sp. Atk')
                                              .replace('special-defense', 'Sp. Def')
                                              .replace('attack', 'Atk')
                                              .replace('defense', 'Def')
                                              .replace('speed', 'Speed')
                                              .replace('hp', 'HP');
                        parts.push(`${amt} ${cleanStat}`);
                    }
                }
                evDisplay.innerText = parts.length > 0 ? parts.join(', ') : 'None';
            }
        }

function applyVersionFilter(chosenVersion) {
    const selected = (chosenVersion || 'ALL').toLowerCase().trim();
    const cards = document.querySelectorAll('.game-version-card');

    cards.forEach(card => {
        const cardVer = (card.getAttribute('data-version') || '').toLowerCase().trim();
        if (selected === 'all' || cardVer === selected) {
            card.style.display = 'block';
        } else {
            card.style.display = 'none';
        }
    });
}

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

// --- 1. Version Filter & Persistence ---
function filterGameVersion(forcedGame) {
    const select = document.getElementById('game-filter-select') || document.getElementById('route-version-filter');
    const chosenRaw = (forcedGame || (select ? select.value : null) || localStorage.getItem(VERSION_STORAGE_KEY) || 'ALL').trim();
    const chosenLower = chosenRaw.toLowerCase();

    // 1. Sync global state if triggered directly from an onchange event
    if (!forcedGame && typeof setGlobalGameVersion === 'function' && chosenRaw !== 'ALL') {
        setGlobalGameVersion(chosenLower);
        return;
    }

    // 2. Break down grouped version keys (e.g. "red-blue" -> ["red", "blue"])
    // Handles compound names like "firered-leafgreen" or "black-2-white-2"
    let allowedVersions = [chosenLower];
    if (chosenLower.includes('-')) {
        allowedVersions = chosenLower.split('-');
        // Re-combine hyphenated pairs (e.g. "omega-ruby-alpha-sapphire" -> "omega-ruby", "alpha-sapphire")
        if (chosenLower === 'firered-leafgreen') allowedVersions = ['firered', 'leafgreen'];
        else if (chosenLower === 'heartgold-soulsilver') allowedVersions = ['heartgold', 'soulsilver'];
        else if (chosenLower === 'black-white') allowedVersions = ['black', 'white'];
        else if (chosenLower === 'black-2-white-2') allowedVersions = ['black-2', 'white-2'];
        else if (chosenLower === 'omega-ruby-alpha-sapphire') allowedVersions = ['omega-ruby', 'alpha-sapphire'];
        else if (chosenLower === 'ultra-sun-ultra-moon') allowedVersions = ['ultra-sun', 'ultra-moon'];
        else if (chosenLower === 'lets-go-pikachu-lets-go-eevee') allowedVersions = ['lets-go-pikachu', 'lets-go-eevee'];
        else if (chosenLower === 'brilliant-diamond-and-shining-pearl') allowedVersions = ['brilliant-diamond', 'shining-pearl'];
        else if (chosenLower === 'colosseum') allowedVersions = ['colosseum', 'xd'];
    }

    // 3. Filter cards
    const cards = document.querySelectorAll('.game-version-card');
    cards.forEach(card => {
        const cardVer = (card.getAttribute('data-version') || '').trim().toLowerCase();

        const isMatch = (chosenRaw === 'ALL' || chosenLower === 'modern') ||
                        (cardVer === chosenLower) ||
                        allowedVersions.includes(cardVer);

        if (isMatch) {
            card.style.setProperty('display', 'block', 'important');
        } else {
            card.style.setProperty('display', 'none', 'important');
        }
    });

    // 4. Update EV yield display if defined
    if (chosenRaw !== 'ALL' && typeof updateTargetEVDisplay === 'function') {
        updateTargetEVDisplay(chosenLower);
    }
}

/**
 * Call this whenever a route's encounter cards are rendered.
 * It hides or disables versions that have zero encounter data for the current route.
 */
function syncRouteFilterDropdownWithDOM() {
    const filterSelect = document.getElementById('game-filter-select') || document.getElementById('route-version-filter');
    if (!filterSelect) return;

    // 1. Gather every unique data-version currently rendered on the page
    const renderedCards = document.querySelectorAll('.game-version-card');
    const presentVersions = new Set();
    renderedCards.forEach(card => {
        const v = (card.getAttribute('data-version') || '').trim().toLowerCase();
        if (v) presentVersions.add(v);
    });

    // 2. Loop through the dropdown options and toggle visibility
    Array.from(filterSelect.options).forEach(opt => {
        const val = opt.value.toLowerCase();
        if (val === 'all' || val === 'modern' || val === '') {
            opt.style.display = 'block';
            return;
        }

        // Check if this option (or any of its split versions) exists in the rendered cards
        const parts = val.split('-');
        const isPresent = presentVersions.has(val) || parts.some(p => presentVersions.has(p));

        if (isPresent) {
            opt.style.display = 'block';
            opt.disabled = false;
        } else {
            opt.style.display = 'none';
            opt.disabled = true;
        }
    });

    // 3. If currently selected option is now hidden, fallback to "ALL"
    if (filterSelect.selectedOptions[0] && filterSelect.selectedOptions[0].disabled) {
        filterSelect.value = 'ALL';
        filterGameVersion('ALL');
    }
}

function syncPokemonFilterDropdownWithData() {
    const targetSelect = document.getElementById('target-gen-select');
    if (!targetSelect) return;

    // 1. Gather all versions represented in moves or encounters
    const validVersions = new Set();

    // From rendered move rows (data-vg attribute)
    const moveRows = document.querySelectorAll('.target-move-row');
    moveRows.forEach(row => {
        let vg = (row.getAttribute('data-vg') || '').toLowerCase().trim().replace(/_/g, '-');
        if (vg) validVersions.add(vg);
    });

    // Also check activeTargetData.encounters if available in memory
    if (typeof activeTargetData !== 'undefined' && activeTargetData && activeTargetData.encounters) {
        Object.keys(activeTargetData.encounters).forEach(k => {
            validVersions.add(k.toLowerCase().trim());
        });
    }

    // If no moves or encounters found (empty page or minimal data), do nothing
    if (validVersions.size === 0) return;

    // 2. Filter target-gen-select options
    Array.from(targetSelect.options).forEach(opt => {
        const val = opt.value.toLowerCase().trim();

        // Always allow modern/default
        if (val === 'modern' || val === '') {
            opt.style.display = 'block';
            opt.disabled = false;
            return;
        }

        // Check exact match or compound splits (e.g. red-blue -> red, blue)
        const parts = val.split('-');
        const isPresent = validVersions.has(val) || parts.some(p => validVersions.has(p));

        if (isPresent) {
            opt.style.display = 'block';
            opt.disabled = false;
        } else {
            opt.style.display = 'none';
            opt.disabled = true;
        }
    });

    // 3. If currently selected option got pruned, fallback to 'modern'
    if (targetSelect.selectedOptions[0] && targetSelect.selectedOptions[0].disabled) {
        targetSelect.value = 'modern';
        if (typeof updateTargetGenView === 'function') {
            updateTargetGenView('modern');
        }
    }
}

function updateRouteDropdownForArea(areaSlug) {
    const filterSelect = document.getElementById('game-filter-select') || document.getElementById('route-version-filter');
    if (!filterSelect || !window.locationAreas) return;

    const area = window.locationAreas.find(a => a.slug === areaSlug);
    const validVersions = new Set(area ? (area.versions || []) : []);

    Array.from(filterSelect.options).forEach(opt => {
        const val = opt.value.toLowerCase();
        if (val === 'all' || val === 'modern' || val === '') {
            opt.style.display = 'block';
            return;
        }

        const isMatch = validVersions.has(val) || val.split('-').some(v => validVersions.has(v));
        opt.style.display = isMatch ? 'block' : 'none';
        opt.disabled = !isMatch;
    });
}
// Restore saved version filter on load
document.addEventListener('DOMContentLoaded', () => {
    const select = document.getElementById('game-filter-select') || document.getElementById('route-version-filter');
    const saved = localStorage.getItem('selected_pokemon_version');
    if (select && saved) {
        const exists = Array.from(select.options).some(opt => opt.value.toLowerCase() === saved.toLowerCase());
        if (exists) {
            select.value = saved;
        }
    }
    const gameSelect = document.getElementById('walkthrough-game-select');
    const partSelect = document.getElementById('walkthrough-part-select');

    if (gameSelect) {
        gameSelect.selectedIndex = 0; // Resets to "-- Choose Game --"
    }
    if (partSelect) {
        partSelect.innerHTML = '<option value="">-- Select Game First --</option>';
        partSelect.disabled = true;
    }
    filterGameVersion();
});

// --- 2. Search Autocomplete (Locations) ---
function cleanStr(str) {
    return (str || '').toLowerCase().replace(/[^a-z0-9]/g, '');
}

// --- 2. Location Search Autocomplete ---
function filterLocations() {
    const input = document.getElementById('location-input') || document.getElementById('route-search-input');
    const box = document.getElementById('location-results') || document.getElementById('route-live-results');
    const locationsList = (typeof locationAreas !== 'undefined') ? locationAreas : ((typeof allLocations !== 'undefined') ? allLocations : []);

    if (!input || !box || locationsList.length === 0) return;

    const val = input.value.toLowerCase().trim();
    if (!val || val.length < 2) {
        box.style.display = 'none';
        box.innerHTML = '';
        return;
    }

    const tokens = val.split(/\s+/).filter(Boolean);
    const matches = locationsList.filter(loc => {
        const name = (loc.name || '').toLowerCase();
        const slug = (loc.slug || '').toLowerCase();
        return tokens.every(token => name.includes(token) || slug.includes(token));
    }).slice(0, 10);

    if (matches.length === 0) {
        box.innerHTML = '<div class="px-4 py-3 text-sm text-slate-400 italic">No locations found.</div>';
        box.style.display = 'block';
        return;
    }

    box.innerHTML = '';
    const endpoint = window.location.pathname.includes('/remote') ? '/remote' : '/';
    const currentVer = localStorage.getItem('selected_pokemon_version') || 'ALL';

    matches.forEach(loc => {
        const item = document.createElement('div');
        item.className = "px-4 py-2 hover:bg-slate-700/80 flex items-center justify-between border-b border-slate-700/40 last:border-none transition";
        item.innerHTML = `
            <div>
                <span class="font-bold text-slate-200 text-xs">${loc.name}</span>
                <span class="font-mono text-[10px] text-indigo-400 block">${loc.slug}</span>
            </div>
            <div class="flex gap-1.5">
                <a href="${endpoint}?action=set_location&slug=${encodeURIComponent(loc.slug)}&ver=${encodeURIComponent(currentVer)}" onclick="document.getElementById('location-input').value='';" class="text-xs bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold px-2 py-0.5 rounded">View Route</a>
            </div>
        `;
        box.appendChild(item);
    });
    box.style.display = 'block';
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

let syncExpTimer = null;

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

    let needed = 0;
    let kills = 0;
    let hours = 0;
    let mins = 0;

    if (toLvl <= fromLvl) {
        outElem.innerText = "0 EXP";
        if (battlesElem) battlesElem.innerText = "0 kills";
        if (timeElem) timeElem.innerText = "~0m";
    } else {
        const expFrom = getExpForLevel(rate, fromLvl);
        const expTo = getExpForLevel(rate, toLvl);
        needed = Math.max(0, expTo - expFrom);

        outElem.innerText = needed.toLocaleString() + " EXP";

        kills = Math.ceil(needed / Math.max(1, expPerKill));
        const totalSeconds = kills * 15;
        hours = Math.floor(totalSeconds / 3600);
        mins = Math.ceil((totalSeconds % 3600) / 60);

        if (battlesElem) battlesElem.innerText = kills.toLocaleString() + " kills";
        if (timeElem) timeElem.innerText = (hours > 0) ? `~${hours}h ${mins}m` : `~${mins}m`;
    }

    // Debounce the fetch by 250ms so typing multiple digits doesn't spam the server
    clearTimeout(syncExpTimer);
    syncExpTimer = setTimeout(() => {
        const query = new URLSearchParams({
            action: 'sync_exp',
            growth_rate: rate,
            from: fromLvl.toString(),
            to: toLvl.toString(),
            exp: outElem.innerText,
            per_kill: expPerKill.toString(),
            kills: battlesElem ? battlesElem.innerText : `${kills.toLocaleString()} kills`,
            time: timeElem ? timeElem.innerText : (hours > 0 ? `~${hours}h ${mins}m` : `~${mins}m`),
            t: Date.now()
        });

        fetch(`/?${query.toString()}`).catch(() => {});
    }, 250);
}

function syncCatchState(hp, lvl, status, ball, odds) {
    const targetName = (window.activeTargetData && activeTargetData.name) ? activeTargetData.name : "None";
    const endpoint = window.location.pathname.includes('/remote') ? '/remote' : '/';
    
    fetch(`${endpoint}?action=sync_catch&hp=${encodeURIComponent(hp)}&lvl=${encodeURIComponent(lvl)}&status=${encodeURIComponent(status)}&ball=${encodeURIComponent(ball)}&odds=${encodeURIComponent(odds)}&target=${encodeURIComponent(targetName)}`)
        .catch(err => console.error("Catch sync failed", err));
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
function updateTargetGenView(forcedGame) {
    if (typeof activeTargetData === 'undefined' || !activeTargetData || !activeTargetData.id) return;

    // Use passed game, or read select, or read central storage
    const select = document.getElementById('target-gen-select');
    const chosenGame = (forcedGame || (select ? select.value : null) || localStorage.getItem(VERSION_STORAGE_KEY) || 'modern').toLowerCase().trim();
    const chosenGen = (typeof vgToGenMap !== 'undefined' && vgToGenMap[chosenGame]) ? vgToGenMap[chosenGame] : 'gen-modern';
    const targetId = activeTargetData.id;

    // A. Update Sprite
    const img = document.getElementById('target-sprite-img');
    if (img && typeof getSpriteForGen === 'function') {
        img.src = getSpriteForGen(targetId, chosenGen);
    }

    // B. Resolve Active Types (Historical overrides)
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
    } else if (typeof calculateHistoricalMatchups === 'function') {
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
                      (chosenGame === 'brilliant-diamond-and-shining-pearl' && rowVg === 'brilliant-diamond-and-shining-pearl') ||
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

    // E. Dynamic Wild Encounters List (Deduplicated)
    const encountersContainer = document.querySelector('#target-encounters-list') || document.querySelector('#target-encounters-container');
    const encountersBadge = document.querySelector('#target-encounters-version-badge');
    if (encountersBadge) encountersBadge.innerText = chosenGame;

    if (encountersContainer) {
        const allEncounters = activeTargetData.encounters || {};
        let rawMatches = [];

        if (chosenGame === 'modern') {
            Object.values(allEncounters).forEach(versionList => {
                if (Array.isArray(versionList)) rawMatches.push(...versionList);
            });
        } else {
            if (allEncounters[chosenGame]) {
                rawMatches.push(...allEncounters[chosenGame]);
            }
            // Check paired sub-versions (e.g. 'red-blue' -> 'red', 'blue')
            chosenGame.split('-').forEach(v => {
                if (allEncounters[v]) {
                    rawMatches.push(...allEncounters[v]);
                }
            });
        }

        const dedupMap = new Map();
        rawMatches.forEach(enc => {
            const loc = enc.location || 'Unknown Area';
            const minL = enc.min_level || 1;
            const maxL = enc.max_level || 1;
            const methods = (enc.methods || []).slice().sort().join(',');
            const dedupKey = `${loc}|${minL}|${maxL}|${methods}`;

            if (!dedupMap.has(dedupKey)) {
                dedupMap.set(dedupKey, { ...enc });
            } else {
                const existing = dedupMap.get(dedupKey);
                if ((enc.chance || 0) > (existing.chance || 0)) {
                    existing.chance = enc.chance;
                }
            }
        });

        const targetEncounters = Array.from(dedupMap.values());

        if (targetEncounters.length > 0) {
            encountersContainer.innerHTML = targetEncounters.map(enc => {
                const methodsStr = (enc.methods || []).join(', ') || 'Wild';
                const minL = enc.min_level || 1;
                const maxL = enc.max_level || 1;
                const lvlStr = minL === maxL ? `Lv. ${minL}` : `Lv. ${minL}-${maxL}`;
                const chanceVal = enc.chance || 0;
                const chanceBadge = chanceVal > 0 ? `<span class="text-[10px] font-mono font-bold text-emerald-400">${chanceVal}%</span>` : '';

                return `
                    <div class="flex justify-between items-center bg-slate-950/70 border border-slate-800/80 rounded-lg p-2 text-xs">
                        <div>
                            <div class="font-bold text-slate-200">${enc.location || 'Unknown Area'}</div>
                            <div class="text-[10px] text-slate-400">${methodsStr}</div>
                        </div>
                        <div class="text-right">
                            <div class="font-mono text-amber-400 font-semibold">${lvlStr}</div>
                            ${chanceBadge}
                        </div>
                    </div>
                `;
            }).join('');
        } else {
            encountersContainer.innerHTML = `<div class="text-slate-500 text-xs italic p-2">No wild encounters listed for "${chosenGame}".</div>`;
        }
    }

    // F. Render Base Stats (Gen 1 Special split/merge handled)
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

    if (typeof calculateCatchOdds === 'function') {
        calculateCatchOdds();
    }

    if (typeof updateTargetEVDisplay === 'function') {
        updateTargetEVDisplay(chosenGame);
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


