#!/bin/bash
# =============================================================================
#  Installateur Fantasy Renamer pour macOS
#
#  Usage (coller dans le Terminal) :
#    curl -fsSL https://raw.githubusercontent.com/KodeNoir/fantasy-renamer/main/install.sh | bash
#
#  Ce que fait ce script :
#    1. détecte la puce du Mac (Apple Silicon ou Intel)
#    2. télécharge la bonne version de l'app depuis la dernière Release GitHub
#    3. l'installe dans le dossier Applications
#    4. retire le marquage « téléchargé depuis Internet » (quarantaine), ce qui
#       évite le message « Apple n'a pas pu confirmer que… ne contenait pas de
#       logiciel malveillant » (l'app n'est pas signée par un compte Apple payant)
#    5. lance l'application
#
#  Variables optionnelles : FR_INSTALL_DIR (dossier d'installation),
#  FR_NO_OPEN=1 (ne pas lancer l'app à la fin, utile pour les tests).
# =============================================================================
set -euo pipefail

REPO="KodeNoir/fantasy-renamer"
APP_NAME="Fantasy Renamer"

say()  { printf "\033[1;35m✨ %s\033[0m\n" "$*"; }
fail() { printf "\033[1;31m❌ %s\033[0m\n" "$*" >&2; exit 1; }

[ "$(uname -s)" = "Darwin" ] || fail "Ce programme fonctionne uniquement sur Mac."

# 1) Puce du Mac (fiable même si le Terminal tourne sous Rosetta)
if [ "$(sysctl -n hw.optional.arm64 2>/dev/null || echo 0)" = "1" ]; then
  ARCH="arm64";  LABEL="puce Apple"
else
  ARCH="x86_64"; LABEL="processeur Intel"
fi
say "Mac détecté : $LABEL ($ARCH)"

# 2) Téléchargement
URL="https://github.com/$REPO/releases/latest/download/FantasyRenamer-$ARCH.zip"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

say "Téléchargement de Fantasy Renamer (≈ 200 Mo)…"
curl -fL --progress-bar "$URL" -o "$TMP/app.zip" \
  || fail "Téléchargement impossible. Vérifie ta connexion Internet."

say "Décompression…"
ditto -x -k "$TMP/app.zip" "$TMP/extrait"
SRC="$(find "$TMP/extrait" -maxdepth 1 -name '*.app' -print -quit)"
[ -n "$SRC" ] || fail "Archive inattendue : application introuvable."

# 3) Installation (Applications, ou ~/Applications si pas les droits)
DEST_DIR="${FR_INSTALL_DIR:-/Applications}"
if [ ! -w "$DEST_DIR" ]; then
  DEST_DIR="$HOME/Applications"
  mkdir -p "$DEST_DIR"
fi
DEST="$DEST_DIR/$APP_NAME.app"

# Ferme une ancienne version ouverte, puis remplace-la
osascript -e 'tell application id "io.github.fantasyrenamer" to quit' >/dev/null 2>&1 || true
sleep 1
rm -rf "$DEST"
mv "$SRC" "$DEST"

# 4) Retrait de la quarantaine (et des anciennes copies téléchargées par le navigateur)
xattr -dr com.apple.quarantine "$DEST" 2>/dev/null || true
for old in "$HOME/Downloads/$APP_NAME-arm64.app" "$HOME/Downloads/$APP_NAME-x86_64.app"; do
  [ -d "$old" ] && xattr -dr com.apple.quarantine "$old" 2>/dev/null || true
done

say "Installé dans : $DEST"

# 5) Lancement
if [ "${FR_NO_OPEN:-0}" != "1" ]; then
  say "Ouverture de l'application…"
  open "$DEST"
fi

say "Terminé ! Tu trouveras Fantasy Renamer dans le dossier Applications (ou via Launchpad)."
