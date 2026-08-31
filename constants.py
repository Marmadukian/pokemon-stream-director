GLOBAL_EVO_CACHE = {}

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


DEFAULT_EXP_STATE = {
    "growth_rate": "medium-fast",
    "lvl_from": "1",
    "lvl_to": "36",
    "exp_needed": "46,656 EXP",
    "exp_per_kill": "120",
    "kills": "389 kills",
    "est_time": "~1h 37m"
}

# Region prefix -> Default Game Versions mapping
# Game lists
GEN1_VERSIONS = ["red", "blue", "yellow", "firered", "leafgreen", "lets-go-pikachu", "lets-go-eevee"]
GEN2_VERSIONS = ["gold", "silver", "crystal", "heartgold", "soulsilver"]
GEN3_VERSIONS = ["ruby", "sapphire", "emerald", "omega-ruby", "alpha-sapphire"]
GEN4_VERSIONS = ["diamond", "pearl", "platinum", "brilliant-diamond", "shining-pearl", "legends-arceus"]
GEN5_VERSIONS = ["black", "white", "black-2", "white-2"]
GEN6_VERSIONS = ["x", "y"]
GEN7_VERSIONS = ["sun", "moon", "ultra-sun", "ultra-moon"]
GEN8_VERSIONS = ["sword", "shield"]
GEN9_VERSIONS = ["scarlet", "violet"]

LANDMARK_REGION_MAP = {
    # Kanto landmarks / cities
    "kanto": GEN1_VERSIONS, "pallet": GEN1_VERSIONS, "viridian": GEN1_VERSIONS, "pewter": GEN1_VERSIONS,
    "cerulean": GEN1_VERSIONS, "vermilion": GEN1_VERSIONS, "lavender": GEN1_VERSIONS, "celadon": GEN1_VERSIONS,
    "fuchsia": GEN1_VERSIONS, "saffron": GEN1_VERSIONS, "cinnabar": GEN1_VERSIONS, "indigo": GEN1_VERSIONS,
    "mt-moon": GEN1_VERSIONS, "rock-tunnel": GEN1_VERSIONS, "seafoam": GEN1_VERSIONS, "power-plant": GEN1_VERSIONS,
    "victory-road-kanto": GEN1_VERSIONS, "pokemon-tower": GEN1_VERSIONS, "digletts-cave": GEN1_VERSIONS, "ss-anne": GEN1_VERSIONS, "s-s-anne": GEN1_VERSIONS,
    
    # Johto landmarks / cities
    "johto": GEN2_VERSIONS, "new-bark": GEN2_VERSIONS, "cherrygrove": GEN2_VERSIONS, "violet-city": GEN2_VERSIONS,
    "azalea": GEN2_VERSIONS, "goldenrod": GEN2_VERSIONS, "ecruteak": GEN2_VERSIONS, "olivine": GEN2_VERSIONS,
    "cianwood": GEN2_VERSIONS, "mahogany": GEN2_VERSIONS, "blackthorn": GEN2_VERSIONS, "sprout-tower": GEN2_VERSIONS,
    "slowpoke-well": GEN2_VERSIONS, "burned-tower": GEN2_VERSIONS, "tin-tower": GEN2_VERSIONS, "bell-tower": GEN2_VERSIONS,
    "whirl-islands": GEN2_VERSIONS, "mt-silver": GEN2_VERSIONS, "dark-cave": GEN2_VERSIONS, "ice-path": GEN2_VERSIONS,

    # Hoenn landmarks / cities
    "hoenn": GEN3_VERSIONS, "littleroot": GEN3_VERSIONS, "oldale": GEN3_VERSIONS, "petalburg": GEN3_VERSIONS,
    "rustboro": GEN3_VERSIONS, "dewford": GEN3_VERSIONS, "slateport": GEN3_VERSIONS, "mauville": GEN3_VERSIONS,
    "verdanturf": GEN3_VERSIONS, "fallarbor": GEN3_VERSIONS, "lavaridge": GEN3_VERSIONS, "fortree": GEN3_VERSIONS,
    "lilycove": GEN3_VERSIONS, "mossdeep": GEN3_VERSIONS, "sootopolis": GEN3_VERSIONS, "pacifidlog": GEN3_VERSIONS,
    "ever-grande": GEN3_VERSIONS, "granite-cave": GEN3_VERSIONS, "fiery-path": GEN3_VERSIONS, "meteor-falls": GEN3_VERSIONS,
    "mt-pyre": GEN3_VERSIONS, "shoal-cave": GEN3_VERSIONS, "seafloor-cavern": GEN3_VERSIONS, "cave-of-origin": GEN3_VERSIONS,
    "sky-pillar": GEN3_VERSIONS, "jagged-pass": GEN3_VERSIONS, "mirage-tower": GEN3_VERSIONS, "desert-underpass": GEN3_VERSIONS,

    # Sinnoh landmarks / cities
    "sinnoh": GEN4_VERSIONS, "twinleaf": GEN4_VERSIONS, "sandgem": GEN4_VERSIONS, "jubilife": GEN4_VERSIONS,
    "oreburgh": GEN4_VERSIONS, "floaroma": GEN4_VERSIONS, "eterna": GEN4_VERSIONS, "hearthome": GEN4_VERSIONS,
    "solaceon": GEN4_VERSIONS, "veilstone": GEN4_VERSIONS, "pastoria": GEN4_VERSIONS, "celestic": GEN4_VERSIONS,
    "canalave": GEN4_VERSIONS, "snowpoint": GEN4_VERSIONS, "sunyshore": GEN4_VERSIONS, "mt-coronet": GEN4_VERSIONS,
    "great-marsh": GEN4_VERSIONS, "trophy-garden": GEN4_VERSIONS, "turnback-cave": GEN4_VERSIONS, "iron-island": GEN4_VERSIONS,
}


# Initial seed data for the EV yield file
INITIAL_LOCAL_EV_YIELDS = {
    "caterpie": {"hp": 1},
    "metapod": {"defense": 2},
    "butterfree": {"special-attack": 2, "special-defense": 1},
    "weedle": {"speed": 1},
    "kakuna": {"defense": 2},
    "beedrill": {"attack": 2, "special-defense": 1},
    "pidgey": {"speed": 1},
    "pidgeotto": {"speed": 2},
    "rattata": {"speed": 1},
    "raticate": {"speed": 2},
    "spearow": {"speed": 1},
    "ekans": {"attack": 1},
    "pikachu": {"speed": 2},
    "zubat": {"speed": 1},
    "golbat": {"speed": 2},
    "oddish": {"special-attack": 1},
    "gloom": {"special-attack": 2},
    "meowth": {"speed": 1},
    "psyduck": {"special-attack": 1},
    "poliwag": {"speed": 1},
    "machop": {"attack": 1},
    "bellsprout": {"attack": 1},
    "geodude": {"defense": 1},
    "graveler": {"defense": 2},
    "magnemite": {"special-attack": 1},
    "gastly": {"special-attack": 1},
    "haunter": {"special-attack": 2},
    "magikarp": {"speed": 1},
    "gyarados": {"attack": 2},
    "ditto": {"hp": 1},
    "roselia": {"special-attack": 2},
    "feebas": {"special-defense": 1},
    "chimecho": {"special-attack": 1, "special-defense": 1},
    "poochyena": {"attack": 1},
    "zigzagoon": {"speed": 1},
    "wurmple": {"hp": 1},
    "silcoon": {"defense": 2},
    "cascoon": {"defense": 2},
    "taillow": {"speed": 1},
    "wingull": {"speed": 1},
    "ralts": {"special-attack": 1},
    "shroomish": {"hp": 1},
    "slakoth": {"hp": 1},
    "whismur": {"hp": 1},
    "makuhita": {"hp": 1},
    "aron": {"defense": 1},
    "electrike": {"speed": 1},
    "numel": {"special-attack": 1},
    "spoink": {"special-defense": 1},
    "spinda": {"special-attack": 1},
    "swablu": {"special-defense": 1},
    "zangoose": {"attack": 2},
    "seviper": {"attack": 1, "special-attack": 1},
    "corphish": {"attack": 1},
    "duskull": {"defense": 1, "special-defense": 1},
    "snorunt": {"hp": 1},
    "spheal": {"hp": 1},
    "bagon": {"attack": 1}
}
VERSION_TO_GEN = {
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
    "scarlet": "generation-ix", "violet": "generation-ix"
}

GEN_ORDER = [
    "generation-i", "generation-ii", "generation-iii", "generation-iv",
    "generation-v", "generation-vi", "generation-vii", "generation-viii", "generation-ix"
]

# Format: { species_slug: { max_gen_slug_where_old_ev_applied: { stat: amt } } }
HISTORICAL_EV_OVERRIDES = {
    # Roselia gave 1 Sp. Atk in Gen 3 (Ruby/Sapphire/Emerald/FireRed/LeafGreen).
    # Changed to 2 Sp. Atk in Gen 4 when Budew/Roserade were added.
    "roselia": {
        "generation-iii": {"special-attack": 1}
    },
    # Feebas gave 1 Speed in Gen 3; changed to 1 Sp. Def in Gen 4
    "feebas": {
        "generation-iii": {"speed": 1}
    },
    # Chimecho gave 1 Sp. Atk in Gen 3; changed to 1 Sp. Atk + 1 Sp. Def in Gen 4 (Chingling)
    "chimecho": {
        "generation-iii": {"special-attack": 1}
    },
    # Porygon gave 1 Attack in Gen 3; changed to 1 Sp. Atk in Gen 4
    "porygon": {
        "generation-iii": {"attack": 1}
    },
    # Magnemite gave 1 Sp. Atk in Gen 3; changed to 1 Sp. Atk in Gen 4 (Magnezone)
    # Volbeat gave 1 Attack in Gen 3; changed to 1 Speed in Gen 4
    "volbeat": {
        "generation-iii": {"attack": 1}
    },
    # Illumise gave 1 Sp. Atk in Gen 3; changed to 1 Speed in Gen 4
    "illumise": {
        "generation-iii": {"special-attack": 1}
    },
    # Ralts / Kirlia adjustments
    "ralts": {
        "generation-iii": {"special-attack": 1}
    }
}

BASE_TYPE_CHART = {
    "normal":   {"rock": 0.5, "ghost": 0.0, "steel": 0.5},
    "fire":     {"fire": 0.5, "water": 0.5, "grass": 2.0, "ice": 2.0, "bug": 2.0, "rock": 0.5, "dragon": 0.5, "steel": 2.0},
    "water":    {"fire": 2.0, "water": 0.5, "grass": 0.5, "ground": 2.0, "rock": 2.0, "dragon": 0.5},
    "electric": {"water": 2.0, "electric": 0.5, "grass": 0.5, "ground": 0.0, "flying": 2.0, "dragon": 0.5},
    "grass":    {"fire": 0.5, "water": 2.0, "grass": 0.5, "poison": 0.5, "ground": 2.0, "flying": 0.5, "bug": 0.5, "rock": 2.0, "dragon": 0.5, "steel": 0.5},
    "ice":      {"fire": 0.5, "water": 0.5, "grass": 2.0, "ice": 0.5, "ground": 2.0, "flying": 2.0, "dragon": 2.0, "steel": 0.5},
    "fighting": {"normal": 2.0, "ice": 2.0, "poison": 0.5, "flying": 0.5, "psychic": 0.5, "bug": 0.5, "rock": 2.0, "ghost": 0.0, "dark": 2.0, "steel": 2.0, "fairy": 0.5},
    "poison":   {"grass": 2.0, "poison": 0.5, "ground": 0.5, "rock": 0.5, "ghost": 0.5, "steel": 0.0, "fairy": 2.0},
    "ground":   {"fire": 2.0, "electric": 2.0, "grass": 0.5, "poison": 2.0, "flying": 0.0, "bug": 0.5, "rock": 2.0, "steel": 2.0},
    "flying":   {"electric": 0.5, "grass": 2.0, "fighting": 2.0, "bug": 2.0, "rock": 0.5, "steel": 0.5},
    "psychic":  {"fighting": 2.0, "poison": 2.0, "psychic": 0.5, "dark": 0.0, "steel": 0.5},
    "bug":      {"fire": 0.5, "grass": 2.0, "fighting": 0.5, "poison": 0.5, "flying": 0.5, "psychic": 2.0, "ghost": 0.5, "dark": 2.0, "steel": 0.5, "fairy": 0.5},
    "rock":     {"fire": 2.0, "ice": 2.0, "fighting": 0.5, "ground": 0.5, "flying": 2.0, "bug": 2.0, "steel": 0.5},
    "ghost":    {"normal": 0.0, "psychic": 2.0, "ghost": 2.0, "dark": 0.5, "steel": 0.5},
    "dragon":   {"dragon": 2.0, "steel": 0.5, "fairy": 0.0},
    "steel":    {"fire": 0.5, "water": 0.5, "electric": 0.5, "ice": 2.0, "rock": 2.0, "steel": 0.5, "fairy": 2.0},
    "dark":     {"fighting": 0.5, "psychic": 2.0, "ghost": 2.0, "dark": 0.5, "fairy": 0.5},
    "fairy":    {"fire": 0.5, "fighting": 2.0, "poison": 0.5, "dragon": 2.0, "dark": 2.0, "steel": 0.5}
}

STAT_SHORT_NAMES = {
    "hp": "HP",
    "attack": "Atk",
    "defense": "Def",
    "special-attack": "SpA",
    "special-defense": "SpD",
    "speed": "Spe"
}


DEFAULT_FORM_ALIASES = {
    # Species that require a default form suffix in PokéAPI /pokemon/
    "deoxys": "deoxys-normal",
    "wormadam": "wormadam-plant",
    "giratina": "giratina-altered",
    "shaymin": "shaymin-land",
    "basculin": "basculin-red-striped",
    "darmanitan": "darmanitan-standard",
    "tornadus": "tornadus-incarnate",
    "thundurus": "thundurus-incarnate",
    "landorus": "landorus-incarnate",
    "keldeo": "keldeo-ordinary",
    "meloetta": "meloetta-aria",
    "meowstic": "meowstic-male",
    "aegislash": "aegislash-shield",
    "pumpkaboo": "pumpkaboo-average",
    "gourgeist": "gourgeist-average",
    "zygarde": "zygarde-50",
    "oricorio": "oricorio-baile",
    "lycanroc": "lycanroc-midday",
    "wishiwashi": "wishiwashi-solo",
    "minior": "minior-red-meteor",
    "mimikyu": "mimikyu-disguised",
    "toxtricity": "toxtricity-amped",
    "eiscue": "eiscue-ice",
    "indeedee": "indeedee-male",
    "morpeko": "morpeko-full-belly",
    "urshifu": "urshifu-single-strike",
    "enamorus": "enamorus-incarnate",
    "ogerpon": "ogerpon-teal-mask",
    "terapagos": "terapagos-normal",
    
    # Special punctuation cases
    "mr-mime": "mr-mime",
    "mime-jr": "mime-jr",
    "mr-rime": "mr-rime",
    "farfetchd": "farfetchd",
    "sirfetchd": "sirfetchd",
    "type-null": "type-null",
    "flabebe": "flabebe",
    "nidoran-f": "nidoran-f",
    "nidoran-m": "nidoran-m",

    # Gender-differentiated default forms
    "frillish": "frillish-male",
    "jellicent": "jellicent-male",
    "unfezant": "unfezant-male",
    "pyroar": "pyroar-male",
    "basculegion": "basculegion-male",
    "oinkologne": "oinkologne-male",
    "meowstic": "meowstic-male",
    "indeedee": "indeedee-male",
    

    # Gen 9 Form Defaults
    "maushold": "maushold-family-of-four",
    "squawkabilly": "squawkabilly-green-plumage",
    "palafin": "palafin-zero",
    "tatsugiri": "tatsugiri-curly",
    "dudunsparce": "dudunsparce-two-segment",
    "gimmighoul": "gimmighoul-chest",
    "koraidon": "koraidon-apex-build",
    "miraidon": "miraidon-ultimate-mode",

    # Gen 8 Form Defaults
    "sinistea": "sinistea-phony",
    "polteageist": "polteageist-phony",
    "poltchageist": "poltchageist-counterfeit",
    "sinistcha": "sinistcha-unremarkable",
    "morpeko": "morpeko-full-belly",
    "urshifu": "urshifu-single-strike",
    "eiscue": "eiscue-ice",
    "indeedee": "indeedee-male",
    "basculegion": "basculegion-male",
    "oinkologne": "oinkologne-male"
}