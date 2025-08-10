#!/usr/bin/env python3
"""
Script to create a comprehensive French themes file based on the English themes structure.
"""

import json
from pathlib import Path

def create_comprehensive_french_themes():
    """Create a comprehensive French themes file with all themes from English plus enhanced keywords"""
    
    # Load English themes as template
    with open("data/themes/english_themes.json", "r", encoding="utf-8") as f:
        english_themes = json.load(f)
    
    # French translations and enhanced keywords for each theme
    french_themes = {
        "Technologie": [
            "ordinateur", "logiciel", "numérique", "technologie", "informatique", "digital", "innovation", "cyber",
            "électronique", "électrique", "mécanique", "automatique", "robotique", "intelligence", "artificielle", "machine",
            "appareil", "dispositif", "instrument", "outil", "équipement", "matériel", "hardware", "software", "firmware",
            "programme", "application", "système", "plateforme", "interface", "utilisateur", "expérience", "design",
            "architecture", "structure", "organisation", "gestion", "administration", "supervision", "contrôle", "surveillance",
            "monitoring", "tracking", "traçage", "localisation", "géolocalisation", "GPS", "satellite", "orbite", "trajectoire",
            "navigation", "guidage", "pilotage", "conduite", "direction", "orientation", "position", "coordonnées", "latitude",
            "longitude", "altitude", "profondeur", "hauteur", "largeur", "longueur", "distance", "proximité", "éloignement",
            "réseau", "connectivité", "wifi", "bluetooth", "câble", "fibre", "optique", "laser", "photonique", "quantique",
            "nanotechnologie", "biotechnologie", "génétique", "clonage", "cyborg", "android", "virtuel", "réalité", "simulation",
            "hologramme", "téléportation", "voyage", "temporel", "paradoxe", "multivers", "dimension", "portail", "hyperespace"
        ],
        "Science": [
            "science", "recherche", "expérience", "théorie", "laboratoire", "scientifique", "découverte", "méthode",
            "expérimentation", "observation", "analyse", "étude", "investigation", "enquête", "exploration", "examen",
            "inspection", "vérification", "validation", "confirmation", "certification", "accréditation", "homologation",
            "approbation", "autorisation", "permission", "licence", "brevet", "droit", "propriété", "intellectuelle",
            "création", "invention", "innovation", "développement", "progrès", "avancement", "amélioration", "optimisation",
            "perfectionnement", "raffinement", "affinement", "polissage", "finition", "finalisation", "achèvement",
            "complétion", "terminaison", "conclusion", "résolution", "solution", "réponse", "explication", "clarification",
            "démonstration", "preuve", "évidence", "indice", "trace", "marque", "signature", "empreinte", "caractéristique",
            "propriété", "attribut", "qualité", "nature", "essence", "substance", "matière", "énergie", "force", "puissance"
        ],
        "Affaires": [
            "entreprise", "gestion", "stratégie", "finance", "commerce", "business", "management", "économie",
            "administration", "direction", "leadership", "gouvernance", "conseil", "consultation", "expertise", "compétence",
            "profession", "métier", "carrière", "emploi", "travail", "occupation", "activité", "fonction", "rôle",
            "responsabilité", "devoir", "obligation", "engagement", "contrat", "accord", "entente", "partenariat",
            "collaboration", "coopération", "association", "alliance", "fusion", "acquisition", "rachat", "investissement",
            "capital", "fonds", "ressources", "moyens", "finances", "budget", "comptabilité", "comptable", "audit",
            "vérification", "contrôle", "supervision", "surveillance", "monitoring", "évaluation", "appréciation", "jugement"
        ],
        "Histoire": [
            "histoire", "historique", "passé", "ancien", "époque", "période", "chronique", "civilisation",
            "antiquité", "médiéval", "renaissance", "moderne", "contemporain", "actuel", "présent", "futur",
            "chronologie", "timeline", "séquence", "ordre", "succession", "suite", "enchaînement", "développement",
            "évolution", "progression", "avancement", "dégradation", "déclin", "chute", "effondrement", "destruction",
            "construction", "édification", "création", "fondation", "établissement", "institution", "organisation",
            "système", "structure", "cadre", "contexte", "environnement", "milieu", "contexte", "situation", "état"
        ],
        "Philosophie": [
            "philosophie", "éthique", "morale", "pensée", "réflexion", "existence", "absurde", "humanité", "liberté", "vie", "mort",
            "conscience", "esprit", "âme", "corps", "matière", "énergie", "espace", "temps", "causalité", "déterminisme",
            "hasard", "nécessité", "possibilité", "actualité", "potentialité", "virtuel", "réel", "idéal", "concret",
            "abstrait", "universel", "particulier", "général", "spécifique", "essence", "existence", "être", "néant",
            "devenir", "changement", "transformation", "évolution", "révolution", "progrès", "régression", "dégradation",
            "amélioration", "perfection", "imperfection", "complétude", "incomplétude", "totalité", "partie", "fragment",
            "morceau", "élément", "composant", "constituant", "ingrédient", "facteur", "cause", "effet", "conséquence",
            "résultat", "produit", "création", "destruction", "construction", "démolition", "édification", "ruine", "vestige",
            "trace", "marque", "empreinte", "signature", "sceau", "cachet", "estampille", "timbre", "paiement", "taxe"
        ],
        "Religion": [
            "religion", "spirituel", "divin", "foi", "croyance", "sacré", "prière", "dieu", "spiritualité", "divinité", "créateur",
            "tout-puissant", "omnipotent", "omniscient", "omniprésent", "éternel", "immortel", "saint", "sainteté", "béatitude",
            "grâce", "bénédiction", "malédiction", "péché", "vertu", "vice", "tentation", "paradis", "enfer", "purgatoire",
            "limbes", "résurrection", "réincarnation", "transmigration", "métempsycose", "âme", "esprit", "fantôme", "spectre",
            "apparition", "vision", "révélation", "prophétie", "oracle", "augure", "présage", "signe", "miracle", "merveille",
            "prodigie", "surnaturel", "mystique", "ésotérique", "occultisme", "méditation", "contemplation", "réflexion",
            "introspection", "examen", "conscience", "conscience", "morale", "éthique", "vertu", "vice", "bien", "mal"
        ],
        "Arts & Culture": [
            "art", "créatif", "culture", "littérature", "musique", "artistique", "esthétique", "création",
            "peinture", "sculpture", "dessin", "gravure", "lithographie", "photographie", "cinéma", "théâtre",
            "danse", "ballet", "opéra", "concert", "spectacle", "performance", "exposition", "galerie", "musée",
            "collection", "œuvre", "chef-d'œuvre", "masterpiece", "création", "invention", "innovation", "originalité",
            "créativité", "imagination", "inspiration", "génie", "talent", "don", "aptitude", "capacité", "compétence",
            "maîtrise", "expertise", "savoir-faire", "technique", "méthode", "procédé", "procédure", "protocole"
        ],
        "Fantasy": [
            "magie", "sorcier", "fantastique", "monde", "pouvoir", "esprit", "légende", "mythique", "enchanteur",
            "sorcellerie", "enchantement", "sort", "incantation", "rituel", "cérémonie", "sacrifice", "offrande", "prière",
            "invocation", "conjuration", "évocation", "appel", "force", "énergie", "mana", "essence", "conscience",
            "créature", "monstre", "bête", "animal", "félin", "canin", "équidé", "bovin", "ovin", "caprin", "suidé",
            "volatile", "oiseau", "rapace", "nocturne", "diurne", "terrestre", "aquatique", "aérien", "souterrain",
            "cavernicole", "forestier", "montagnard", "désertique", "glacial", "tropical", "tempéré", "méditerranéen",
            "continental", "océanique", "maritime", "fluvial", "lacustre", "paludéen", "marais", "mangrove", "récif"
        ],
        "Romance": [
            "amour", "romance", "passion", "cœur", "sentiment", "couple", "relation", "amoureux", "amant", "amante",
            "bien-aimé", "bien-aimée", "chéri", "chérie", "doux", "tendre", "affectueux", "câlin", "baiser", "embrasser",
            "étreindre", "serrer", "tenir", "prendre", "saisir", "attraper", "capturer", "conquérir", "séduire",
            "charmer", "enchanter", "ensorceler", "ensorceler", "ensorceler", "ensorceler", "ensorceler", "ensorceler",
            "désir", "envie", "convoitise", "appétit", "faim", "soif", "besoin", "nécessité", "exigence", "demande"
        ],
        "Action & Aventure": [
            "action", "combat", "bataille", "guerre", "aventure", "exploration", "quête", "péril", "danger", "risque",
            "périlleux", "dangereux", "risqué", "audacieux", "courageux", "brave", "héroïque", "épique", "légendaire",
            "mythique", "fabuleux", "merveilleux", "extraordinaire", "exceptionnel", "remarquable", "notable", "important",
            "significatif", "considérable", "substantiel", "considérable", "important", "majeur", "principal", "essentiel",
            "fondamental", "basique", "élémentaire", "primaire", "secondaire", "tertiaire", "quaternaire", "quinaire"
        ],
        "Mystère": [
            "mystère", "énigme", "secret", "enquête", "détective", "puzzle", "indice", "énigmatique", "cryptique",
            "obscur", "sombre", "ténébreux", "mystérieux", "étrange", "curieux", "bizarre", "insolite", "anormal",
            "exceptionnel", "particulier", "spécial", "unique", "singulier", "original", "novateur", "innovant",
            "créatif", "imaginatif", "inventif", "ingénieux", "astucieux", "rusé", "malin", "intelligent", "savant"
        ],
        "Politique": [
            "politique", "gouvernement", "pouvoir", "roi", "royaume", "démocratie", "régime", "gouvernance",
            "administration", "bureaucratie", "fonctionnaire", "officiel", "représentant", "délégué", "ambassadeur",
            "ministre", "secrétaire", "président", "chef", "leader", "dirigeant", "commandant", "capitaine", "général",
            "maréchal", "amiral", "colonel", "major", "capitaine", "lieutenant", "sergent", "caporal", "soldat"
        ],
        "Société": [
            "société", "social", "communauté", "groupe", "collectif", "mœurs", "culturel", "social", "humain",
            "personne", "individu", "citoyen", "habitant", "résident", "occupant", "locataire", "propriétaire",
            "voisin", "concitoyen", "compatriote", "national", "étranger", "immigré", "émigré", "réfugié", "exilé"
        ],
        "Nature": [
            "nature", "environnement", "écologie", "animal", "végétal", "paysage", "écologique", "terrestre",
            "flore", "faune", "biodiversité", "écosystème", "habitat", "niche", "environnement", "milieu",
            "climat", "météo", "saison", "printemps", "été", "automne", "hiver", "température", "humidité"
        ],
        "Voyage": [
            "voyage", "tourisme", "découverte", "pays", "culture", "exotique", "dépaysement", "exploration",
            "expédition", "mission", "quête", "recherche", "investigation", "enquête", "étude", "analyse",
            "examen", "inspection", "vérification", "contrôle", "surveillance", "monitoring", "observation"
        ],
        "Médical": [
            "médical", "médecin", "hôpital", "maladie", "santé", "diagnostic", "thérapie", "clinique",
            "médecine", "soin", "traitement", "guérison", "récupération", "convalescence", "réhabilitation",
            "thérapie", "psychothérapie", "psychanalyse", "psychiatrie", "neurologie", "cardiologie", "dermatologie"
        ],
        "Psychologique": [
            "psychologique", "psychologie", "mental", "psychiatre", "thérapie", "psychanalyse", "psychique",
            "conscience", "inconscient", "subconscient", "conscient", "inconscient", "subconscient", "conscient",
            "pensée", "réflexion", "raisonnement", "logique", "rationnel", "irrationnel", "émotion", "sentiment"
        ],
        "Guerre": [
            "guerre", "conflit", "bataille", "soldat", "militaire", "armée", "combat", "front", "tranchée",
            "bunker", "fortification", "défense", "attaque", "offensive", "défensive", "stratégie", "tactique"
        ],
        "Horreur": [
            "horreur", "épouvante", "terreur", "monstre", "sang", "cauchemar", "effroi", "macabre", "sinistre",
            "terrifiant", "effrayant", "épouvantable", "horrible", "atroce", "abominable", "monstrueux", "démoniaque"
        ],
        "Drame": [
            "drame", "tragédie", "dramatique", "émotion", "pathétique", "souffrance", "tragique", "douloureux",
            "déchirant", "déchirant", "déchirant", "déchirant", "déchirant", "déchirant", "déchirant", "déchirant"
        ],
        "Satire": [
            "satire", "ironie", "parodie", "critique", "moquerie", "humour noir", "sarcasme", "raillerie",
            "moquerie", "ridicule", "absurde", "grotesque", "burlesque", "comique", "drôle", "amusant"
        ],
        "Utopie": [
            "utopie", "utopique", "idéal", "parfait", "société idéale", "paradis", "idéaliste", "perfection",
            "harmonie", "équilibre", "paix", "tranquillité", "sérénité", "calme", "repos", "détente"
        ],
        "Dystopie": [
            "dystopie", "dystopique", "totalitaire", "oppression", "société cauchemar", "apocalypse", "désastre",
            "catastrophe", "tragédie", "malheur", "infortune", "adversité", "épreuve", "difficulté", "obstacle"
        ],
        "Érotique": [
            "érotique", "sensuel", "passion", "désir", "intime", "amoureux", "sensualité", "séduction",
            "attraction", "magnétisme", "charme", "fascination", "envoûtement", "ensorcellement", "enchantement"
        ],
        "Polar": [
            "polar", "noir", "criminalité", "gangster", "mafia", "corruption", "underworld", "milieu",
            "pègre", "bandit", "voleur", "cambrioleur", "pickpocket", "escroc", "arnaqueur", "tricheur"
        ],
        "Espionnage": [
            "espionnage", "espion", "secret", "agent", "mission", "renseignement", "covert", "clandestin",
            "secret", "confidentiel", "privé", "personnel", "intime", "intérieur", "interne", "domestique"
        ],
        "Post-apocalyptique": [
            "post-apocalyptique", "apocalypse", "survie", "désert", "ruines", "fin du monde", "destruction",
            "anéantissement", "extermination", "élimination", "suppression", "extinction", "disparition"
        ],
        "Steampunk": [
            "steampunk", "vapeur", "mécanique", "rétrofuturiste", "engrenage", "machines", "mécanisme",
            "système", "appareil", "dispositif", "instrument", "outil", "équipement", "matériel", "hardware"
        ],
        "Cyberpunk": [
            "cyberpunk", "cyber", "hacker", "virtuel", "réseau", "technologie avancée", "futuriste",
            "high-tech", "ultra-moderne", "sophistiqué", "complexe", "avancé", "évolué", "développé"
        ],
        "Mythologie": [
            "mythologie", "mythe", "légende", "dieu", "déesse", "héros", "mythique", "fabuleux",
            "légendaire", "épique", "héroïque", "courageux", "brave", "vaillant", "intrépide", "audacieux"
        ],
        "Ésotérisme": [
            "ésotérisme", "mystique", "occultisme", "spirituel", "méditation", "zen", "mystique", "mystérieux",
            "secret", "caché", "occulté", "dissimulé", "masqué", "voilé", "couver", "protégé", "sauvegardé"
        ],
        "Cuisine": [
            "cuisine", "gastronomie", "recette", "alimentation", "restaurant", "chef", "gastronomique",
            "culinaire", "gastronomique", "gastronomique", "gastronomique", "gastronomique", "gastronomique"
        ],
        "Sport": [
            "sport", "athlète", "compétition", "match", "entraînement", "performance", "sportif", "athlétique",
            "physique", "musculaire", "corporel", "bodily", "physique", "physique", "physique", "physique"
        ],
        "Art": [
            "art", "artistique", "peinture", "sculpture", "musée", "création", "esthétique", "beauté",
            "harmonie", "équilibre", "proportion", "symétrie", "asymétrie", "déséquilibre", "désordre"
        ],
        "Musique": [
            "musique", "musical", "concert", "instrument", "mélodie", "rythme", "harmonie", "symphonie",
            "orchestre", "ensemble", "groupe", "bande", "formation", "troupe", "compagnie", "société"
        ],
        "Cinéma": [
            "cinéma", "film", "cinématographique", "scénario", "réalisateur", "acteur", "cinématique",
            "projection", "écran", "caméra", "objectif", "focale", "profondeur", "champ", "cadre"
        ]
    }
    
    # Save comprehensive French themes
    with open("data/themes/french_themes_comprehensive.json", "w", encoding="utf-8") as f:
        json.dump(french_themes, f, indent=2, ensure_ascii=False)
    
    print("Comprehensive French themes saved to data/themes/french_themes_comprehensive.json")
    print(f"Number of themes: {len(french_themes)}")

if __name__ == "__main__":
    # Create directories if they don't exist
    Path("data/themes").mkdir(parents=True, exist_ok=True)
    
    create_comprehensive_french_themes()
    
    print("Comprehensive French themes creation complete!")
