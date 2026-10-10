#!/bin/bash
# =============================================================================
#  Compile Fantasy Renamer en application macOS autonome (.app) avec PyInstaller.
#
#  Usage (dans le Terminal, depuis ce dossier) :
#     ./build_app.sh            -> app pour la puce de CE Mac (arm64 sur M4, x86_64 sur Intel)
#     ./build_app.sh intel      -> depuis un Mac Apple Silicon : app Intel (x86_64) via Rosetta 2
#
#  Pré-requis : Python 3.12 de python.org (installeur "universal2").
#  Résultat   : dist/Fantasy Renamer-<arch>.app  +  dist/FantasyRenamer-<arch>.zip
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")"

PYORG="/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
MODE="${1:-native}"

if [ "$MODE" = "intel" ]; then
  # Python universal2 forcé en x86_64 : pip installera alors les paquets Intel
  # (dont torch 2.2.2) grâce aux marqueurs du requirements.txt.
  [ -x "$PYORG" ] || { echo "Installez Python 3.12 universal2 depuis python.org"; exit 1; }
  /usr/bin/pgrep -q oahd || { echo "Rosetta 2 absent : softwareupdate --install-rosetta"; exit 1; }
  VENV=".venv-build-x86_64"
  RUN=(arch -x86_64 "$VENV/bin/python")
  [ -x "$VENV/bin/python" ] || arch -x86_64 "$PYORG" -m venv "$VENV"
else
  VENV=".venv-build"
  RUN=("$VENV/bin/python")
  if [ ! -x "$VENV/bin/python" ]; then
    BASE="$PYORG"; [ -x "$BASE" ] || BASE="$(command -v python3.12 || command -v python3)"
    "$BASE" -m venv "$VENV"
  fi
fi

ARCH="$("${RUN[@]}" -c 'import platform; print(platform.machine())')"
echo "==> Compilation pour l'architecture : $ARCH"

"${RUN[@]}" -m pip install --upgrade pip --quiet
"${RUN[@]}" -m pip install -r requirements.txt --quiet
"${RUN[@]}" -m pip install "pyinstaller>=6.6" "pyinstaller-hooks-contrib>=2024.6" --quiet

APP_NAME="Fantasy Renamer"
rm -rf build "dist/$APP_NAME.app" "dist/$APP_NAME-$ARCH.app"

# Options importantes :
#  --windowed               : vraie app macOS (pas de Terminal)
#  --target-arch            : UNE seule architecture (torch n'existe pas en universal2)
#  --add-data data:data     : listes de noms embarquées
#  --collect-data           : thèmes/polices de customtkinter
#  --copy-metadata          : transformers vérifie les versions de ses dépendances au démarrage
#  --exclude-module         : évite d'embarquer TensorFlow/JAX s'ils traînent sur la machine
"${RUN[@]}" -m PyInstaller --noconfirm --clean --windowed \
  --name "$APP_NAME" \
  --osx-bundle-identifier "io.github.fantasyrenamer" \
  --target-arch "$ARCH" \
  --add-data "data:data" \
  --collect-data customtkinter \
  --collect-submodules transformers.models.clip \
  --copy-metadata torch --copy-metadata transformers --copy-metadata tokenizers \
  --copy-metadata huggingface_hub --copy-metadata safetensors --copy-metadata tqdm \
  --copy-metadata regex --copy-metadata requests --copy-metadata packaging \
  --copy-metadata filelock --copy-metadata numpy --copy-metadata pyyaml \
  --exclude-module tensorflow --exclude-module jax --exclude-module flax \
  --exclude-module matplotlib --exclude-module IPython --exclude-module pytest \
  main.py

mv "dist/$APP_NAME.app" "dist/$APP_NAME-$ARCH.app"
# Signature "ad hoc" (obligatoire pour lancer une app sur puce Apple)
codesign --force --deep --sign - "dist/$APP_NAME-$ARCH.app" 2>/dev/null || true
# Contenu du ZIP : l'app + le script « 1 clic » qui retire le blocage macOS.
# On copie l'app sous son nom simple « Fantasy Renamer.app » (le script la cherche
# sous ce nom), à côté de OUVREZ-MOI_D-ABORD.applescript. L'app -$ARCH.app d'origine
# est conservée pour l'étape de test du workflow.
STAGE="dist/stage-$ARCH"
rm -rf "$STAGE"
mkdir -p "$STAGE"
ditto "dist/$APP_NAME-$ARCH.app" "$STAGE/$APP_NAME.app"
cp "OUVREZ-MOI_D-ABORD.applescript" "$STAGE/OUVREZ-MOI_D-ABORD.applescript"
# -c -k sans --keepParent : le ZIP contient directement les deux éléments.
ditto -c -k "$STAGE" "dist/FantasyRenamer-$ARCH.zip"
rm -rf "$STAGE"

echo ""
echo "✅ Terminé : dist/$APP_NAME-$ARCH.app"
echo "   Archive  : dist/FantasyRenamer-$ARCH.zip"
