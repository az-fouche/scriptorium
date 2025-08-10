#!/usr/bin/env python3
"""
Improve French Genre Keywords

This script adds a Romance genre and improves existing French genre keywords
to make the annotation system more accurate.
"""

import json
from pathlib import Path

def improve_french_genres():
    """Improve French genre keywords"""
    
    # Load current French genres
    genres_file = Path("data/genres/french_genres.json")
    
    with open(genres_file, 'r', encoding='utf-8') as f:
        current_genres = json.load(f)
    
    # Create improved genres
    improved_genres = {
        "Roman": [
            # Keep existing keywords but add more specific ones
            "roman", "histoire", "narratif", "fiction", "récit", "littérature",
            "prose", "écriture", "auteur", "écrivain", "livre", "volume", "tome",
            "chapitre", "paragraphe", "phrase", "mot", "texte", "narrateur",
            "personnage", "héros", "héroïne", "protagoniste", "antagoniste",
            "intrigue", "scénario", "développement", "conflit", "résolution",
            "dénouement", "climax", "exposition", "dialogue", "monologue",
            "description", "paysage", "atmosphère", "ambiance", "ton", "style",
            "registre", "langue", "vocabulaire", "syntaxe", "rhétorique",
            "figure", "métaphore", "comparaison", "allégorie", "symbole",
            "thème", "motif", "leitmotiv", "récurrence", "écho", "résonance",
            "harmonie", "rythme", "cadence",
            # Add more specific novel keywords
            "aventure", "drame", "comédie", "tragédie", "mélodrame",
            "réalisme", "naturalisme", "symbolisme", "surréalisme",
            "nouveau roman", "roman policier", "roman historique",
            "roman d'amour", "roman d'aventures", "roman psychologique"
        ],
        
        "Romance": [
            # New Romance genre keywords
            "romance", "amour", "passion", "sentiment", "affection",
            "tendresse", "désir", "attirance", "séduction", "flirt",
            "couple", "mariage", "fiançailles", "divorce", "séparation",
            "reconciliation", "infidélité", "jalousie", "possessif",
            "romantique", "romantisme", "idylle", "idylle", "idylle",
            "coup de foudre", "amour fou", "passion dévorante",
            "histoire d'amour", "relation amoureuse", "partenaire",
            "amoureux", "amoureuse", "bien-aimé", "bien-aimée",
            "chéri", "chérie", "mon amour", "mon cœur", "mon ange",
            "baiser", "embrasser", "étreinte", "câlin", "caresser",
            "intimité", "privacy", "nuit de noces", "lune de miel",
            "anniversaire", "cadeau", "surprise", "déclaration",
            "demande en mariage", "bague de fiançailles", "alliance",
            "mariage", "cérémonie", "réception", "voyage de noces",
            "bl", "boys love", "yaoi", "shounen ai", "gl", "girls love",
            "yuri", "shoujo ai", "lgbt", "lgbtq", "gay", "lesbien",
            "homosexuel", "homosexuelle", "bisexuel", "bisexuelle",
            "transgenre", "non-binaire", "queer"
        ],
        
        "Fantasy": [
            # Keep existing fantasy keywords but improve them
            "fantasy", "fantastique", "magie", "sorcier", "dragon",
            "royaume", "enchanteur", "légende", "mythique", "sorcellerie",
            "enchantement", "sort", "incantation", "rituel", "cérémonie",
            "sacrifice", "offrande", "prière", "invocation", "conjuration",
            "évocation", "appel", "pouvoir", "force", "énergie", "mana",
            "essence", "esprit", "âme", "conscience", "créature", "monstre",
            "bête", "animal", "félin", "canin", "équidé", "bovin", "ovin",
            "caprin", "suidé", "volatile", "oiseau", "rapace", "nocturne",
            "diurne", "terrestre", "aquatique", "aérien", "souterrain",
            "cavernicole", "forestier", "montagnard", "désertique", "glacial",
            "tropical", "tempéré", "méditerranéen", "continental", "océanique",
            "maritime", "fluvial", "lacustre", "paludéen", "marais", "mangrove",
            "récif", "atoll", "île", "archipel", "continent", "péninsule",
            "isthme", "détroit", "golfe", "baie", "crique", "anse", "calanque",
            "fjord", "estuaire", "delta", "embouchure", "source", "cascade",
            "chute", "rapide", "méandre", "boucle", "courbe", "sinuosité",
            "ligne", "droite", "courbe", "spirale", "cercle", "ovale",
            "ellipse", "parabole", "hyperbole", "géométrie", "mathématique",
            "calcul", "computation", "algorithme", "logique", "raisonnement",
            "déduction", "induction",
            # Add more specific fantasy keywords
            "voleur", "magicien", "magicienne", "enchanteur", "enchanteuse",
            "sorcière", "mage", "druide", "druidesse", "prêtre", "prêtresse",
            "paladin", "guerrier", "guerrière", "archer", "archère",
            "chevalier", "chevalière", "noble", "noblesse", "roi", "reine",
            "prince", "princesse", "duc", "duchesse", "comte", "comtesse",
            "baron", "baronne", "seigneur", "dame", "vassal", "suzerain",
            "château", "forteresse", "citadelle", "tour", "donjon", "rempart",
            "fossé", "pont-levis", "herse", "mâchicoulis", "créneau",
            "échauguette", "barbacane", "bastion", "redoute", "casemate"
        ],
        
        "Science-Fiction": [
            # Keep existing science fiction keywords
            "science-fiction", "sf", "futur", "espace", "robot", "vaisseau",
            "planète", "extraterrestre", "technologie", "cyber", "dystopie",
            "spatial", "cosmique", "galactique", "interstellaire", "interplanétaire",
            "astronautique", "astronomie", "astrophysique", "quantique", "nanotechnologie",
            "biotechnologie", "génétique", "clonage", "cyborg", "android", "artificiel",
            "intelligence", "algorithmique", "virtuel", "réalité", "simulation",
            "hologramme", "téléportation", "voyage", "temporel", "paradoxe", "multivers",
            "dimension", "portail", "hyperespace", "warp", "impulsion", "propulsion",
            "antimatière", "énergie", "plasma", "fusion", "fission", "réacteur",
            "générateur", "batterie", "circuit", "processeur", "mémoire", "données",
            "information", "réseau", "système", "programme", "code", "hacker", "pirate",
            "virus", "firewall", "sécurité", "surveillance", "contrôle", "autorité",
            "régime", "totalitaire", "oppression", "rébellion", "résistance", "révolution",
            "liberté", "égalité", "justice", "démocratie", "dictature", "tyrannie",
            "esclavage", "exploitation", "pauvreté", "richesse", "classe", "hiérarchie",
            "élite", "masse", "population", "société", "civilisation", "culture"
        ],
        
        "Philosophie": [
            # Refined philosophy keywords - remove overly broad ones
            "philosophie", "éthique", "morale", "pensée", "réflexion", "existence",
            "absurde", "humanité", "liberté", "conscience", "esprit", "âme",
            "corps", "matière", "énergie", "causalité", "déterminisme", "hasard",
            "nécessité", "possibilité", "actualité", "potentialité", "virtuel",
            "réel", "idéal", "concret", "abstrait", "universel", "particulier",
            "général", "spécifique", "essence", "existence", "néant", "métaphysique",
            "ontologie", "épistémologie", "logique", "dialectique", "sophisme",
            "paradoxe", "contradiction", "vérité", "fausseté", "objectivité",
            "subjectivité", "relativisme", "absolutisme", "empirisme", "rationalisme",
            "idéalisme", "matérialisme", "stoïcisme", "épicurisme", "cynisme",
            "scepticisme", "dogmatisme", "criticisme", "pragmatisme", "existentialisme",
            "structuralisme", "postmodernisme", "herméneutique", "phénoménologie",
            "déconstruction", "analytique", "continentale",
            # Add more specific philosophy keywords
            "sagesse", "savoir", "connaissance", "compréhension", "entendement",
            "raison", "rationalité", "irrationalité", "intuition", "perception",
            "sensibilité", "émotion", "sentiment", "passion", "volonté", "désir",
            "besoin", "intérêt", "motivation", "intention", "but", "fin", "objectif",
            "projet", "plan", "stratégie", "méthode", "procédure", "technique",
            "art", "science", "discipline", "domaine", "champ", "secteur",
            "branche", "spécialité", "expertise", "compétence", "maîtrise",
            "doctrine", "théorie", "principe", "loi", "règle", "norme", "critère",
            "standard", "modèle", "paradigme", "cadre", "contexte", "environnement",
            "situation", "condition", "état", "mode", "forme", "structure",
            "organisation", "système", "ensemble", "totalité", "unité", "pluralité",
            "diversité", "variété", "multiplicité", "complexité", "simplicité"
        ]
    }
    
    # Save improved genres
    backup_file = Path("data/backups/french_genres_backup_v2.json")
    backup_file.parent.mkdir(exist_ok=True)
    
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(current_genres, f, indent=2, ensure_ascii=False)
    
    print(f"Backed up current genres to {backup_file}")
    
    # Save improved genres
    with open(genres_file, 'w', encoding='utf-8') as f:
        json.dump(improved_genres, f, indent=2, ensure_ascii=False)
    
    print(f"Updated {genres_file} with improved genres")
    print(f"Added Romance genre with {len(improved_genres['Romance'])} keywords")
    print(f"Improved existing genres:")
    for genre, keywords in improved_genres.items():
        print(f"  {genre}: {len(keywords)} keywords")

if __name__ == "__main__":
    improve_french_genres()
