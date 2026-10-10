"""
Classification d'images en local avec CLIP (zero-shot).

Aucune API, aucun abonnement : le modèle est téléchargé une seule fois depuis
Hugging Face (≈ 600 Mo), puis tout tourne hors-ligne sur la machine.

Principe : CLIP transforme une image ET une phrase en vecteurs comparables.
On compare l'image aux descriptions "un homme", "une femme", "un paysage"...
et la catégorie la plus proche l'emporte.
"""

from __future__ import annotations

import gc
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Optional

from PIL import Image, ImageOps

from . import config
from .device import DeviceInfo, detect_device, empty_device_cache

# Réglages de confort pour Hugging Face / tokenizers
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


class ImageLoadError(Exception):
    """L'image est corrompue, tronquée ou dans un format illisible."""


@dataclass
class ClassificationResult:
    category: str                       # "homme", "femme" ou "lieu"
    confidence: float                   # 0.0 -> 1.0
    scores: Dict[str, float] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Téléchargement / cache du modèle
# --------------------------------------------------------------------------- #
def find_cached_model() -> Optional[str]:
    """Renvoie le chemin local du modèle s'il est déjà téléchargé, sinon None."""
    from huggingface_hub import snapshot_download

    try:
        path = snapshot_download(
            config.MODEL_ID,
            allow_patterns=config.MODEL_ALLOW_PATTERNS,
            local_files_only=True,
        )
        if (Path(path) / "pytorch_model.bin").exists():
            return path
    except Exception:
        pass
    return None


def download_model() -> str:
    """Télécharge le modèle (uniquement les fichiers utiles) et renvoie son chemin."""
    from huggingface_hub import snapshot_download

    return snapshot_download(
        config.MODEL_ID,
        allow_patterns=config.MODEL_ALLOW_PATTERNS,
    )


# --------------------------------------------------------------------------- #
# Chargement d'image robuste et économe en mémoire
# --------------------------------------------------------------------------- #
def load_image_for_analysis(path: Path, max_side: int = config.MAX_ANALYSIS_SIDE) -> Image.Image:
    """
    Ouvre une image, la vérifie et la réduit pour l'analyse.

    Lève ImageLoadError si le fichier est corrompu ou n'est pas une image.
    """
    try:
        with Image.open(path) as img:
            # Pour les JPEG, `draft` décode directement en basse résolution :
            # une photo de 6000x4000 ne coûte alors que quelques Mo de RAM.
            try:
                img.draft("RGB", (max_side, max_side))
            except Exception:
                pass

            img.seek(0)                      # 1re image d'un GIF animé
            img.load()                       # force le décodage -> détecte la corruption
            img = ImageOps.exif_transpose(img)  # respecte l'orientation de l'appareil photo

            # Transparence -> fond blanc (sinon le fond devient noir)
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                rgba = img.convert("RGBA")
                background = Image.new("RGB", rgba.size, (255, 255, 255))
                background.paste(rgba, mask=rgba.getchannel("A"))
                img = background
            else:
                img = img.convert("RGB")

            img.thumbnail((max_side, max_side), Image.BICUBIC)
            return img.copy()               # détaché du fichier, qui peut être fermé
    except Exception as exc:  # UnidentifiedImageError, OSError, DecompressionBombError...
        raise ImageLoadError(f"{type(exc).__name__}: {exc}") from exc


# --------------------------------------------------------------------------- #
# Classifieur
# --------------------------------------------------------------------------- #
class ImageClassifier:
    """
    Enveloppe autour de CLIP.

    Usage :
        clf = ImageClassifier()
        clf.load(on_status=print)
        result = clf.classify(Path("photo.jpg"))
    """

    def __init__(self) -> None:
        self.device_info: Optional[DeviceInfo] = None
        self._torch = None
        self._model = None
        self._processor = None
        self._class_embeddings = None  # tenseur [nb_catégories, dim]
        self._logit_scale = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def load(self, on_status: Callable[[str, str], None] = lambda kind, msg: None) -> None:
        """
        Prépare le modèle. `on_status(kind, message)` informe l'interface :
        kind = "download" (long, la barre passe en mode attente) ou "info".
        """
        on_status("info", "Démarrage du moteur IA (PyTorch)…")
        import torch
        from transformers import CLIPModel, CLIPProcessor

        self._torch = torch
        self.device_info = detect_device()
        on_status("device", self.device_info.label_fr)

        model_path = find_cached_model()
        if model_path is None:
            on_status(
                "download",
                "Téléchargement du modèle IA en cours… Cela peut prendre quelques minutes "
                f"({config.MODEL_SIZE_HINT}, uniquement au premier lancement).",
            )
            try:
                model_path = download_model()
            except Exception as exc:
                raise RuntimeError(
                    "Impossible de télécharger le modèle IA. Vérifiez la connexion "
                    f"Internet puis relancez.\nDétail : {exc}"
                ) from exc

        on_status("info", "Chargement du modèle IA en mémoire…")
        device = self.device_info.torch_device
        self._processor = CLIPProcessor.from_pretrained(model_path)
        model = CLIPModel.from_pretrained(model_path, torch_dtype=torch.float32)
        model.eval()
        try:
            model.to(device)
        except Exception:
            # Filet de sécurité absolu : si le GPU refuse, on reste sur CPU.
            device = "cpu"
            self.device_info.torch_device = "cpu"
            self.device_info.label_fr = f"Processeur ({self.device_info.cpu_name}) – mode CPU (secours)"
            model.to("cpu")
            on_status("device", self.device_info.label_fr)
        self._model = model
        self._logit_scale = model.logit_scale.exp().item()

        self._prepare_text_embeddings()
        on_status("info", "Modèle IA prêt.")

    def _prepare_text_embeddings(self) -> None:
        """Calcule UNE SEULE FOIS le vecteur moyen de chaque catégorie."""
        torch = self._torch
        device = self.device_info.torch_device
        class_vectors = []
        with torch.inference_mode():
            for category in config.CATEGORIES:
                prompts = config.CATEGORY_PROMPTS[category]
                tokens = self._processor(text=prompts, return_tensors="pt", padding=True)
                tokens = {k: v.to(device) for k, v in tokens.items()}
                feats = self._model.get_text_features(**tokens)
                feats = feats / feats.norm(dim=-1, keepdim=True)
                mean = feats.mean(dim=0)
                class_vectors.append(mean / mean.norm())
        self._class_embeddings = torch.stack(class_vectors)  # [3, dim]

    def classify_pil(self, image: Image.Image) -> ClassificationResult:
        torch = self._torch
        device = self.device_info.torch_device
        inputs = outputs = img_feats = logits = probs = None
        try:
            with torch.inference_mode():
                inputs = self._processor(images=image, return_tensors="pt")
                pixel_values = inputs["pixel_values"].to(device)
                img_feats = self._model.get_image_features(pixel_values=pixel_values)
                img_feats = img_feats / img_feats.norm(dim=-1, keepdim=True)
                logits = self._logit_scale * img_feats @ self._class_embeddings.T
                probs = logits.softmax(dim=-1)[0].float().cpu().tolist()
            scores = {cat: float(p) for cat, p in zip(config.CATEGORIES, probs)}
            best = max(scores, key=scores.get)
            return ClassificationResult(best, scores[best], scores)
        finally:
            # Nettoyage explicite entre chaque image (RAM de l'iMac Intel !)
            del inputs, outputs, img_feats, logits, probs
            gc.collect()
            empty_device_cache(device)

    def classify(self, path: Path) -> ClassificationResult:
        """Analyse un fichier. Lève ImageLoadError si l'image est illisible."""
        image = load_image_for_analysis(path)
        try:
            return self.classify_pil(image)
        finally:
            image.close()
            del image

    def unload(self) -> None:
        """Libère complètement le modèle (fin de traitement)."""
        device = self.device_info.torch_device if self.device_info else "cpu"
        self._model = self._processor = self._class_embeddings = None
        gc.collect()
        empty_device_cache(device)
