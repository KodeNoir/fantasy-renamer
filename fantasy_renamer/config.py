"""
Configuration centrale de Fantasy Renamer.

Tout ce qui est "réglable" se trouve ici : modèle IA, catégories,
formats d'image acceptés, durée de mémoire des noms, emplacements des fichiers.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "Fantasy Renamer"
APP_ID = "FantasyRenamer"
APP_VERSION = "1.0.0"

# --------------------------------------------------------------------------- #
# Modèle IA
# --------------------------------------------------------------------------- #
# CLIP ViT-B/32 : ~600 Mo, rapide, excellent compromis pour un iMac Intel.
MODEL_ID = "openai/clip-vit-base-patch32"
MODEL_SIZE_HINT = "≈ 600 Mo"

# On ne télécharge QUE les fichiers utiles (le dépôt contient aussi des
# versions TensorFlow et Flax, inutiles ici : 1,2 Go économisés).
MODEL_ALLOW_PATTERNS = [
    "config.json",
    "preprocessor_config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "vocab.json",
    "merges.txt",
    "pytorch_model.bin",
]

# --------------------------------------------------------------------------- #
# Catégories et "prompts" de classification zero-shot
# --------------------------------------------------------------------------- #
# Pour chaque catégorie, plusieurs descriptions en anglais (CLIP a été entraîné
# en anglais). Leurs vecteurs sont moyennés ("prompt ensembling"), ce qui rend
# la classification nettement plus robuste qu'une seule phrase.
CATEGORY_MALE = "homme"
CATEGORY_FEMALE = "femme"
CATEGORY_PLACE = "lieu"
CATEGORY_CREATURE = "creature"

CATEGORIES = [CATEGORY_MALE, CATEGORY_FEMALE, CATEGORY_PLACE, CATEGORY_CREATURE]

CATEGORY_LABELS_FR = {
    CATEGORY_MALE: "Homme",
    CATEGORY_FEMALE: "Femme",
    CATEGORY_PLACE: "Lieu",
    CATEGORY_CREATURE: "Créature",
}

CATEGORY_PROMPTS = {
    CATEGORY_MALE: [
        "a photo of a man",
        "a portrait of a man",
        "a close-up photo of a man's face",
        "a photo of a male person",
        "a painting of a man",
        "a digital illustration of a male character",
        "a photo of a bearded man",
    ],
    CATEGORY_FEMALE: [
        "a photo of a woman",
        "a portrait of a woman",
        "a close-up photo of a woman's face",
        "a photo of a female person",
        "a painting of a woman",
        "a digital illustration of a female character",
        "a photo of a woman with long hair",
    ],
    CATEGORY_PLACE: [
        "a photo of a landscape",
        "a photo of a place with no people",
        "a photo of nature, mountains and forests",
        "a photo of a city or a village",
        "a photo of a building or a castle",
        "a photo of a room interior",
        "a painting of a fantasy landscape",
    ],
}

# En dessous de ce niveau de confiance, l'image est signalée « à vérifier »
# dans le journal et le rapport (ex. créature, silhouette encapuchonnée…).
LOW_CONFIDENCE = 0.75

# Catégories départagées par la 2e étape (homme / femme / lieu)
MAIN_CATEGORIES = [CATEGORY_MALE, CATEGORY_FEMALE, CATEGORY_PLACE]

# 1re étape : « porte » qui détecte les créatures NON humaines.
# Un personnage avec des cornes, des oreilles d'elfe ou de renard reste un
# humanoïde (donc homme/femme) : seules les vraies bêtes deviennent « créature ».
GATE_HUMANOID = "humanoide"
GATE_BEAST = "bete"
GATE_SCENERY = "decor"
GATE_PROMPTS = {
    GATE_HUMANOID: [
        "a portrait of a person",
        "a woman with horns",
        "a man with horns",
        "an elf with pointed ears",
        "a woman with fox ears",
        "a fantasy character with a human face and body",
        "a demon girl",
        "a hooded figure",
    ],
    GATE_BEAST: [
        "a dragon",
        "a wolf",
        "a four-legged beast",
        "a monster with an animal head",
        "a wild animal",
        "a giant reptile",
        "a creature with no human face",
    ],
    GATE_SCENERY: [
        "a landscape with no people or animals",
        "a castle",
        "a city",
        "a forest",
        "a room interior",
    ],
}
# La créature est retenue si « bête » gagne avec au moins cette probabilité.
CREATURE_MIN_PROB = 0.5

# --------------------------------------------------------------------------- #
# Fichiers images
# --------------------------------------------------------------------------- #
SUPPORTED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff",
}
# Les images sont réduites à cette taille max AVANT analyse (CLIP travaille de
# toute façon en 224x224) : énorme gain de RAM sur les photos de 24+ Mpx.
MAX_ANALYSIS_SIDE = 512

# --------------------------------------------------------------------------- #
# Mémoire des noms
# --------------------------------------------------------------------------- #
NAME_MEMORY_DAYS = 30


# --------------------------------------------------------------------------- #
# Emplacements
# --------------------------------------------------------------------------- #
def app_support_dir() -> Path:
    """
    Dossier où l'on stocke l'historique et les réglages.

    - macOS : ~/Library/Application Support/FantasyRenamer
      (indispensable pour l'app compilée : le .app lui-même ne doit pas être
      modifié, et macOS peut le lancer depuis un emplacement en lecture seule).
    - Autres systèmes : ~/.fantasy_renamer

    Peut être forcé avec la variable d'environnement FANTASY_RENAMER_HOME.
    """
    override = os.environ.get("FANTASY_RENAMER_HOME")
    if override:
        path = Path(override).expanduser()
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / APP_ID
    else:
        path = Path.home() / ".fantasy_renamer"
    path.mkdir(parents=True, exist_ok=True)
    return path


def resource_dir() -> Path:
    """
    Dossier contenant les ressources livrées avec le logiciel (listes de noms).

    Fonctionne en mode script ET dans une app compilée avec PyInstaller
    (qui décompresse les ressources dans sys._MEIPASS).
    """
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / "data"
    return Path(__file__).resolve().parent.parent / "data"


def history_file() -> Path:
    return app_support_dir() / "history.json"


def settings_file() -> Path:
    return app_support_dir() / "settings.json"
