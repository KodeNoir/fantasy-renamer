#!/bin/bash
# =============================================================================
#  Fantasy Renamer – lanceur pour macOS (double-clic)
#
#  Au premier lancement :
#    1. trouve une version de Python compatible (3.10 à 3.12 ; 3.13 accepté sur puce Apple)
#    2. crée un environnement isolé (.venv) dans ce dossier
#    3. installe les dépendances (PyTorch, CLIP…) – environ 5 à 10 minutes
#  Les fois suivantes : démarrage direct en quelques secondes.
# =============================================================================

cd "$(dirname "$0")" || exit 1
APP_DIR="$(pwd)"
VENV="$APP_DIR/.venv"

title()  { printf "\n\033[1;35m✨ %s\033[0m\n" "$*"; }
info()   { printf "   %s\n" "$*"; }
alert()  {
  # Fenêtre d'alerte macOS (visible même si le Terminal est caché)
  osascript -e "display dialog \"$1\" buttons {\"OK\"} default button 1 with title \"Fantasy Renamer\" with icon caution" >/dev/null 2>&1
}

title "Fantasy Renamer – démarrage"

# ----------------------------------------------------------------------------
# 1) Trouver un Python compatible
# ----------------------------------------------------------------------------
is_compatible() {
  "$1" - <<'PY' 2>/dev/null
import sys, platform
v = sys.version_info[:2]
arch = platform.machine()
# PyTorch pour Mac Intel s'arrête à la version 2.2.2, qui ne supporte que Python <= 3.12
ok = (3, 10) <= v <= (3, 12) or (v == (3, 13) and arch == "arm64")
if ok:
    try:
        import tkinter, venv
        ok = tkinter.TkVersion >= 8.6       # Tk 8.5 (ancien Python d'Apple) affiche mal l'interface
    except Exception:
        ok = False
sys.exit(0 if ok else 1)
PY
}

PY=""
for cand in \
    /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/3.11/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 \
    python3.12 python3.11 python3.10 \
    /opt/homebrew/bin/python3.12 /usr/local/bin/python3.12 \
    python3 \
    /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 python3.13 ; do
  p="$(command -v "$cand" 2>/dev/null)" || continue
  # /usr/bin/python3 = Python d'Apple (3.9, Tk 8.5) : il ouvre parfois une fenêtre
  # d'installation des outils Xcode, on l'évite.
  [ "$p" = "/usr/bin/python3" ] && continue
  if is_compatible "$p"; then PY="$p"; break; fi
done

if [ -z "$PY" ]; then
  info "Aucune version compatible de Python n'a été trouvée."
  alert "Python 3.12 est nécessaire.\n\nLa page de téléchargement va s'ouvrir : choisissez « Python 3.12.x » puis « macOS 64-bit universal2 installer », installez-le, et relancez Fantasy Renamer."
  open "https://www.python.org/downloads/macos/"
  exit 1
fi

PY_TAG="$("$PY" -c 'import sys,platform;print(f"{platform.machine()}-py{sys.version_info[0]}.{sys.version_info[1]}")')"
info "Python utilisé : $PY ($PY_TAG)"

# ----------------------------------------------------------------------------
# 2) Environnement virtuel (recréé s'il vient d'un autre Mac / autre puce)
# ----------------------------------------------------------------------------
if [ -d "$VENV" ] && [ "$(cat "$VENV/.fr_python_tag" 2>/dev/null)" != "$PY_TAG" ]; then
  info "Environnement créé sur une autre machine ou un autre Python : reconstruction…"
  rm -rf "$VENV"
fi

if [ ! -x "$VENV/bin/python" ]; then
  title "Première installation (une seule fois, 5 à 10 minutes)…"
  "$PY" -m venv "$VENV" || { alert "Impossible de créer l'environnement Python."; exit 1; }
  echo "$PY_TAG" > "$VENV/.fr_python_tag"
fi

# ----------------------------------------------------------------------------
# 3) Dépendances (réinstallées seulement si requirements.txt a changé)
# ----------------------------------------------------------------------------
REQ_HASH="$(shasum -a 256 requirements.txt | cut -d' ' -f1)"
if [ "$(cat "$VENV/.requirements.sha" 2>/dev/null)" != "$REQ_HASH" ]; then
  title "Installation des composants (PyTorch, CLIP, interface)…"
  info "Ne fermez pas cette fenêtre, cela peut prendre plusieurs minutes."
  "$VENV/bin/python" -m pip install --upgrade pip --quiet --disable-pip-version-check
  if "$VENV/bin/python" -m pip install -r requirements.txt --disable-pip-version-check; then
    echo "$REQ_HASH" > "$VENV/.requirements.sha"
  else
    alert "L'installation des composants a échoué.\n\nVérifiez votre connexion Internet puis relancez. Le détail de l'erreur est affiché dans la fenêtre Terminal."
    exit 1
  fi
fi

# ----------------------------------------------------------------------------
# 4) Lancement
# ----------------------------------------------------------------------------
title "Ouverture de l'application…"
info "(Vous pouvez réduire cette fenêtre Terminal, mais ne la fermez pas pendant l'utilisation.)"
"$VENV/bin/python" main.py
STATUS=$?
if [ $STATUS -ne 0 ]; then
  alert "Fantasy Renamer s'est arrêté de façon inattendue (code $STATUS). Le détail est affiché dans la fenêtre Terminal."
fi
info "Application fermée. Vous pouvez fermer cette fenêtre."
exit $STATUS
