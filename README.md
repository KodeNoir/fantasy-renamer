# ✨ Fantasy Renamer

**Renomme automatiquement des lots d'images avec des noms de Fantasy uniques, grâce à une IA qui tourne 100 % en local sur ton Mac.**

Fantasy Renamer regarde chaque image, détermine s'il s'agit d'un **homme**, d'une **femme** ou d'un **lieu / paysage**, puis lui donne un nom adapté (`Aldric.jpg`, `Elowen.png`, `Ravencrest.jpg`…). Les originaux ne sont jamais modifiés : les images renommées sont **copiées** dans le dossier de ton choix.

- 🧠 **IA locale et gratuite** : modèle CLIP d'OpenAI via `transformers`. Pas d'API payante ni de compte, et aucune image n'est envoyée sur Internet.
- ⚡ **S'adapte au Mac** : accélération GPU **Metal (MPS)** sur puce Apple (M1 à M4), **CPU** sur Mac Intel, avec bascule automatique et sans erreur.
- 🗓️ **Mémoire de 30 jours** : un nom déjà donné n'est pas réutilisé pendant 30 jours.
- 📦 **Traitement par lot** : 50, 100, 500 images d'un coup. Les fichiers corrompus ou non pris en charge sont ignorés sans planter.
- 🇫🇷 **Interface en français**, simple, avec barre de progression.

---

## Sommaire

1. [Installation (pour les non-développeurs)](#1-installation-pour-les-non-développeurs)
2. [Utilisation](#2-utilisation)
3. [Comment ça marche](#3-comment-ça-marche)
4. [Personnaliser les noms](#4-personnaliser-les-noms)
5. [Où sont stockées mes données ?](#5-où-sont-stockées-mes-données-)
6. [Compiler une application macOS autonome (.app)](#6-compiler-une-application-macos-autonome-app)
7. [Dépannage](#7-dépannage)
8. [Pour les développeurs](#8-pour-les-développeurs)

---

## 1. Installation (pour les non-développeurs)

### ⭐ Le plus simple : l'installateur en une ligne

1. Ouvre l'app **Terminal** (Launchpad → Autres → Terminal, ou ⌘ Espace puis tape « Terminal »).
2. Colle cette ligne puis appuie sur **Entrée** :

   ```bash
   curl -fsSL https://raw.githubusercontent.com/KodeNoir/fantasy-renamer/main/install.sh | bash
   ```

3. C'est tout. Le script :
   - détecte la puce du Mac (Intel ou Apple Silicon) et télécharge la bonne version ;
   - installe **Fantasy Renamer** dans le dossier **Applications** ;
   - retire le blocage de macOS (« Apple n'a pas pu confirmer que… ne contenait pas de logiciel malveillant ») ;
   - lance l'application.

Pour mettre à jour plus tard, il suffit de relancer la même ligne.

> **Pourquoi ce message de macOS ?** Une app téléchargée avec un navigateur est marquée « venant d'Internet », et macOS la bloque si elle n'est pas signée avec un compte Apple Developer (99 $/an). L'installateur télécharge l'app avec `curl` puis retire ce marquage (`xattr -dr com.apple.quarantine`). Le code de l'installateur est lisible dans [`install.sh`](install.sh).

### Installation manuelle (sans Terminal)

1. Ouvre l'onglet **[Releases](../../releases/latest)** et télécharge le bon fichier :
   - Mac à **puce Apple** (M1, M2, M3, M4) → `FantasyRenamer-arm64.zip`
   - Mac **Intel** → `FantasyRenamer-x86_64.zip`
   *(Pour savoir quelle puce a ton Mac : menu  → À propos de ce Mac.)*
2. Double-clique sur le ZIP, puis glisse l'app dans **Applications**.
3. Ouvre l'app. Si macOS affiche « Apple n'a pas pu confirmer… » : clique sur **Terminé**, puis va dans **Réglages Système → Confidentialité et sécurité**, descends et clique sur **Ouvrir quand même**.

### Autre méthode : lancer depuis le code source

#### Étape 1 : installer Python 3.12 (une seule fois)

1. Va sur **https://www.python.org/downloads/macos/**
2. Choisis la dernière version **Python 3.12.x** puis **« macOS 64-bit universal2 installer »**.
   Cet installeur fonctionne sur Mac Intel **et** sur puce Apple.
3. Ouvre le fichier `.pkg` téléchargé et clique sur *Continuer* jusqu'au bout.

> ⚠️ **Pourquoi 3.12 et pas 3.13 ou plus ?** PyTorch (le moteur d'IA) n'est plus publié pour les Mac Intel depuis sa version 2.2.2, qui ne fonctionne qu'avec Python 3.12 au maximum. Sur un Mac à puce Apple, Python 3.13 marche aussi, mais 3.12 convient partout.

### Étape 2 : télécharger Fantasy Renamer

Sur la page GitHub du projet : bouton vert **Code → Download ZIP**, puis double-clique sur le ZIP pour le décompresser. Range le dossier où tu veux (Documents, Applications…).

### Étape 3 : lancer l'application

Double-clique sur **`Lancer Fantasy Renamer.command`**.

**Au tout premier lancement**, macOS peut bloquer le fichier car il vient d'Internet :
- **macOS 14 Sonoma ou plus ancien** : clic droit (ou Ctrl + clic) sur le fichier → **Ouvrir** → **Ouvrir**.
- **macOS 15 Sequoia ou plus récent** : double-clique une fois (macOS refuse), puis va dans **Réglages Système → Confidentialité et sécurité**, descends et clique sur **« Ouvrir quand même »**.

Une fenêtre Terminal s'ouvre et installe automatiquement tout le nécessaire. **Cela prend 5 à 10 minutes la première fois** (téléchargement de PyTorch). Les lancements suivants ne prennent que quelques secondes.

> 💡 Laisse la fenêtre Terminal ouverte pendant l'utilisation (tu peux la réduire dans le Dock).

---

## 2. Utilisation

1. **📂 Dossier source** : choisis le dossier qui contient tes images.
2. **📁 Dossier destination** : choisis (ou crée) le dossier où seront copiées les images renommées.
3. Clique sur **Démarrer**.

**Au premier traitement**, le modèle d'IA (≈ 600 Mo) est téléchargé. Le message *« Téléchargement du modèle IA en cours… Cela peut prendre quelques minutes. »* s'affiche avec une barre animée : c'est normal, l'application n'est pas plantée. Ensuite, tout fonctionne **hors-ligne**.

À la fin, un fichier **`rapport_fantasy_renamer_<date>.csv`** est créé dans le dossier destination. Il s'ouvre dans Numbers ou Excel et donne pour chaque image son nom d'origine, son nouveau nom, sa catégorie et le niveau de confiance de l'IA.

Le bouton **Démarrer** devient **Arrêter** pendant le traitement : l'arrêt se fait proprement après l'image en cours, et les images déjà copiées sont conservées. Les dossiers choisis sont mémorisés pour la fois suivante.

**Formats acceptés** : `.jpg .jpeg .png .webp .bmp .gif .tif .tiff`. Les autres fichiers sont ignorés et signalés dans le journal.

> **Photos d'iPhone (.HEIC)** : elles ne sont pas prises en charge par défaut. Pour les convertir en JPEG, sélectionne-les dans le Finder, puis clic droit → *Actions rapides* → *Convertir l'image*.

**Vitesse indicative** : sur Mac M4 (Metal), une image est analysée en une fraction de seconde. Sur un iMac Intel (CPU), compte environ 0,3 à 1 seconde par image, donc 50 images en moins d'une minute.

---

## 3. Comment ça marche

### Analyse de l'image : CLIP en « zero-shot »

[CLIP](https://huggingface.co/openai/clip-vit-base-patch32) est un modèle qui sait comparer une **image** et une **phrase**. On lui présente plusieurs descriptions par catégorie (« a portrait of a man », « a photo of a landscape », « a painting of a woman »…). Leurs vecteurs sont moyennés (*prompt ensembling*) et la catégorie la plus proche de l'image l'emporte. Il n'y a aucun entraînement à faire : c'est le principe du *zero-shot*.

Ces descriptions se trouvent dans `fantasy_renamer/config.py` (`CATEGORY_PROMPTS`). Tu peux en ajouter si certaines images sont mal classées, par exemple `"a photo of an elf"` pour la catégorie femme.

### Détection automatique du matériel

`fantasy_renamer/device.py` s'en charge au démarrage du traitement :

| Machine | Moteur utilisé | Détail |
|---|---|---|
| Mac Apple Silicon (M1 à M4) | **MPS (Metal)** ⚡ | Un vrai petit calcul de test est fait sur le GPU avant de l'activer. |
| Mac Intel | **CPU** | Tous les cœurs physiques sont utilisés. |
| Python Intel lancé sur puce Apple (Rosetta) | CPU | Un avertissement s'affiche, car Metal n'est pas accessible via Rosetta. |
| Linux / Windows + NVIDIA | CUDA | Bonus pour les contributeurs. |

Si le GPU refuse de charger le modèle pour une raison quelconque, le programme **retombe automatiquement sur le CPU** au lieu de planter. `PYTORCH_ENABLE_MPS_FALLBACK=1` est aussi activé : une opération pas encore disponible sur Metal est alors calculée sur le CPU.

Le moteur détecté s'affiche en bas de la fenêtre.

### Économie de mémoire (important pour l'iMac Intel)

- Les photos sont décodées directement en **basse résolution** (512 px max). Une photo de 24 Mpx n'occupe donc que quelques Mo au lieu de ~100 Mo.
- Après chaque image, les tenseurs sont supprimés, puis `gc.collect()` et `torch.mps.empty_cache()` libèrent la mémoire.
- Le modèle n'est chargé **qu'une fois** et reste en mémoire entre deux lots.

### Noms et mémoire de 30 jours

1. Selon la catégorie, un nom est tiré au hasard dans `data/names_homme.txt`, `names_femme.txt` ou `names_lieu.txt` (près de 500 noms au total).
2. Les noms attribués il y a moins de **30 jours** sont exclus, quelle que soit la catégorie. Les noms déjà présents dans le dossier destination sont aussi évités, ce qui empêche tout écrasement de fichier.
3. Si une liste est épuisée, un **générateur procédural de syllabes** prend le relais (`Kaelmir`, `Syllana`, `Drakholm`…), avec une réserve quasi infinie.
4. Chaque nom est enregistré **immédiatement** dans `history.json` avec sa date. Même en cas de coupure au milieu d'un lot, rien n'est perdu. Les entrées de plus de 30 jours sont purgées automatiquement.

Tous les noms font **un seul mot, uniquement composé de lettres** : jamais d'espace, de tiret ni de nom composé.

---

## 4. Personnaliser les noms

Ouvre les fichiers du dossier `data/` avec TextEdit :

```
data/names_homme.txt
data/names_femme.txt
data/names_lieu.txt
```

Un nom par ligne. Les lignes commençant par `#` sont ignorées. Les noms invalides (avec espace, tiret, chiffre…) sont ignorés automatiquement.

La durée de mémoire (30 jours) se règle dans `fantasy_renamer/config.py` → `NAME_MEMORY_DAYS`.

---

## 5. Où sont stockées mes données ?

| Quoi | Où |
|---|---|
| Historique des noms (30 jours) | `~/Library/Application Support/FantasyRenamer/history.json` |
| Derniers dossiers choisis | `~/Library/Application Support/FantasyRenamer/settings.json` |
| Modèle d'IA (≈ 600 Mo) | `~/.cache/huggingface/hub/models--openai--clip-vit-base-patch32` |
| Environnement Python | dossier `.venv` caché, à côté du lanceur |

Pour y accéder dans le Finder : menu **Aller → Aller au dossier…** (⇧⌘G), puis colle le chemin.

Pour **tout remettre à zéro**, supprime ces dossiers. Le modèle et les composants seront retéléchargés au lancement suivant.

---

## 6. Compiler une application macOS autonome (.app)

Le lanceur `.command` suffit pour un usage quotidien. Une vraie application `.app` évite en plus d'installer Python sur le Mac de destination et s'ouvre d'un double-clic, sans Terminal.

### ⚠️ La règle d'or : une compilation par architecture

| Question | Réponse |
|---|---|
| Une app compilée sur Mac **M4** marche-t-elle sur Mac **Intel** ? | ❌ **Non.** Elle contient du code ARM64 qu'un processeur Intel ne sait pas exécuter. |
| Une app compilée sur Mac **Intel** marche-t-elle sur Mac **M4** ? | ✅ **Oui**, via Rosetta 2 (installé automatiquement par macOS au besoin), mais **sans accélération Metal** : l'IA tourne en mode CPU, donc plus lentement. |
| Peut-on faire une seule app « Universal 2 » (Intel + ARM) ? | ❌ **Pas en pratique.** PyInstaller ne peut fusionner que des bibliothèques déjà universelles. Or PyTorch n'est publié **qu'en versions séparées** x86_64 et arm64, et pas dans la même version (2.2.2 maximum sur Intel). `--target-arch universal2` échoue donc. |

**Recommandation : compiler deux apps**, une par architecture :

- `Fantasy Renamer-arm64.app` → pour ton MacBook Air M4 (rapide, Metal)
- `Fantasy Renamer-x86_64.app` → pour l'iMac Intel

### Méthode A : compiler sur chaque Mac (la plus simple)

Sur **chaque** Mac, avec Python 3.12 de python.org installé, ouvre le Terminal dans le dossier du projet et lance :

```bash
./build_app.sh
```

Le script crée un environnement dédié, installe PyInstaller et compile pour la puce de la machine. Résultat : `dist/Fantasy Renamer-arm64.app` sur le M4, `dist/Fantasy Renamer-x86_64.app` sur l'iMac.

### Méthode B : compiler les deux versions depuis le Mac M4

Python.org fournit un Python *universal2* qu'on peut forcer en mode Intel grâce à Rosetta 2 :

```bash
softwareupdate --install-rosetta --agree-to-license   # une seule fois
./build_app.sh          # → version arm64 (Apple Silicon)
./build_app.sh intel    # → version x86_64 (Intel), via « arch -x86_64 »
```

En mode `intel`, le script crée un environnement séparé (`.venv-build-x86_64`) et exécute tout avec `arch -x86_64`. pip installe alors automatiquement les paquets Intel, dont `torch==2.2.2` et `numpy<2`, grâce aux marqueurs de `requirements.txt`. Teste quand même l'app finale sur l'iMac.

> Attention : il faut toujours préfixer par `arch -x86_64` les commandes qui utilisent `.venv-build-x86_64`. Sinon, le Python universal2 démarre en mode ARM et installe les mauvais paquets. Le script le fait pour toi.

### Ce que fait `build_app.sh` (options PyInstaller expliquées)

```bash
pyinstaller --windowed --name "Fantasy Renamer" \
  --target-arch arm64|x86_64 \          # une seule architecture
  --add-data "data:data" \              # listes de noms embarquées
  --collect-data customtkinter \        # thèmes de l'interface
  --collect-submodules transformers.models.clip \
  --copy-metadata torch --copy-metadata transformers ... \  # transformers vérifie ses dépendances au démarrage
  --exclude-module tensorflow ... \
  main.py
```

Le script applique ensuite une signature *ad hoc* (`codesign --sign -`), obligatoire pour lancer une app sur puce Apple, puis crée un ZIP avec `ditto`. Ce ZIP préserve la structure du `.app` : c'est lui qu'il faut envoyer ou publier dans les *Releases* GitHub.

**Bon à savoir :**
- L'app pèse **environ 600 Mo à 1 Go** (PyTorch est volumineux). C'est normal.
- Le **modèle CLIP n'est pas inclus** dans l'app : il se télécharge au premier traitement, avec le même message rassurant.
- `history.json` est stocké dans `~/Library/Application Support/`, jamais dans le `.app`. La mémoire des 30 jours est donc **partagée** entre la version `.command` et la version `.app` d'un même Mac.
- **py2app** fonctionne aussi en théorie, mais il gère moins bien PyTorch et transformers. PyInstaller est recommandé ici.

### Installer l'app sur l'iMac

1. Copie `FantasyRenamer-x86_64.zip` sur l'iMac (clé USB, AirDrop…) et double-clique dessus.
2. Glisse `Fantasy Renamer-x86_64.app` dans le dossier **Applications**. Ne la lance pas depuis Téléchargements : macOS peut alors l'exécuter depuis un emplacement temporaire en lecture seule.
3. Premier lancement : l'app n'est pas signée par un développeur Apple payant, macOS va donc la bloquer.
   - Sonoma ou plus ancien : **clic droit → Ouvrir → Ouvrir**.
   - Sequoia ou plus récent : **Réglages Système → Confidentialité et sécurité → Ouvrir quand même**.
   - Alternative dans le Terminal : `xattr -dr com.apple.quarantine "/Applications/Fantasy Renamer-x86_64.app"`

> Pour une distribution publique sans aucun avertissement, il faudrait un compte Apple Developer (99 $/an), une signature « Developer ID » et la notarisation (`xcrun notarytool`). Ce n'est pas nécessaire pour un usage personnel.

---

## 7. Dépannage

| Problème | Solution |
|---|---|
| « Apple n'a pas pu confirmer que… ne contenait pas de logiciel malveillant » | Utilise l'installateur en une ligne (section 1), ou Réglages Système → Confidentialité et sécurité → **Ouvrir quand même**. |
| « Python 3.12 est nécessaire » | Installe Python 3.12 *universal2* depuis python.org (voir étape 1). |
| Le `.command` ne s'ouvre pas / « permission refusée » | Dans le Terminal : `chmod +x "Lancer Fantasy Renamer.command"`, puis réessaie. |
| L'installation échoue (pip) | Vérifie la connexion Internet. Supprime le dossier caché `.venv` (dans le Finder, ⇧⌘. affiche les fichiers cachés) et relance. |
| Le téléchargement du modèle échoue | Il faut Internet au **premier** traitement seulement. Relance : le téléchargement reprend où il s'était arrêté. |
| Dossier copié du Mac M4 vers l'iMac | Pas de souci : le lanceur détecte que `.venv` vient d'une autre puce et le reconstruit automatiquement. |
| Une image est mal classée | Ajoute des descriptions dans `CATEGORY_PROMPTS` (`config.py`), ou renomme le fichier à la main. Le rapport CSV indique la confiance de l'IA. |
| Interface floue ou bizarre | Tu utilises sans doute le Python d'Apple (Tk 8.5). Installe celui de python.org. |
| Vérifier quel moteur est utilisé | `.venv/bin/python main.py --device` |

---

## 8. Pour les développeurs

### Structure du projet

```
FantasyRenamer/
├── Lancer Fantasy Renamer.command   # lanceur double-clic (venv + dépendances + app)
├── build_app.sh                     # compilation .app (PyInstaller), arm64 ou x86_64
├── main.py                          # point d'entrée (interface ou --cli)
├── requirements.txt                 # dépendances avec marqueurs Intel / Apple Silicon
├── data/
│   ├── names_homme.txt
│   ├── names_femme.txt
│   └── names_lieu.txt
├── fantasy_renamer/
│   ├── config.py        # réglages : modèle, prompts, formats, 30 jours, chemins
│   ├── device.py        # détection MPS / CUDA / CPU, Rosetta, vidage du cache
│   ├── classifier.py    # CLIP zero-shot, téléchargement, chargement d'image robuste
│   ├── names.py         # listes de noms + générateur procédural
│   ├── history.py       # mémoire des noms sur 30 jours (JSON atomique)
│   ├── processor.py     # traitement par lot, gestion d'erreurs, rapport CSV
│   └── gui.py           # interface customtkinter (thread + file d'événements)
└── tests/
    └── test_core.py     # tests sans IA (faux classifieur)
```

### Installation manuelle

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py                          # interface graphique
python main.py --cli ~/Images/in ~/Images/out   # sans interface
python main.py --device                 # affiche MPS / CPU
python -m unittest discover tests       # tests
```

### Choix techniques et versions figées

- **`torch==2.2.2` sur Intel** : c'est la dernière version publiée pour macOS x86_64. Sur arm64, une version récente est installée.
- **`numpy<2` sur Intel** : torch 2.2.2 a été compilé avec NumPy 1.x et plante avec NumPy 2.
- **`transformers==4.46.3`** : le dépôt `openai/clip-vit-base-patch32` ne fournit le modèle qu'au format `pytorch_model.bin`. Les versions récentes de transformers refusent de charger ce format avec un torch antérieur à 2.6. La 4.46.3 fonctionne avec torch 2.2.2 comme avec les versions récentes.
- Seuls les fichiers PyTorch du modèle sont téléchargés (`allow_patterns`). Les poids TensorFlow et Flax ne sont pas récupérés, soit 1,2 Go économisés.
- `processor.py` ne dépend pas de l'interface : il communique par événements (`on_event`), ce qui le rend testable et réutilisable.

### Publication automatique (GitHub Actions)

Le fichier `.github/workflows/build-macos.yml` compile l'app sur les Mac hébergés par GitHub, gratuitement pour un dépôt public. Deux machines travaillent en parallèle :

| Machine GitHub | Résultat |
|---|---|
| `macos-15` (Apple Silicon) | `FantasyRenamer-arm64.zip` |
| `macos-15-intel` (Intel) | `FantasyRenamer-x86_64.zip` |

Sur chaque machine, le workflow lance les tests, télécharge CLIP et classe de vraies images, compile le `.app`, puis **teste l'app compilée** avant de la publier.

**Publier une nouvelle version :**

```bash
git tag v1.0.0
git push origin v1.0.0
```

Tu peux aussi publier sans Terminal : onglet **Actions** → *Compiler les apps macOS* → **Run workflow**, puis saisis le numéro de version (ex. `v1.0.1`).

Environ 15 minutes plus tard, les deux ZIP apparaissent dans l'onglet **Releases**. Pour un simple essai sans publication : onglet **Actions** → *Compiler les apps macOS* → **Run workflow** en laissant le numéro de version vide. Les ZIP sont alors dans la section *Artifacts* du run.

> Les Mac de GitHub sont des machines virtuelles sans GPU : les tests y tournent en mode CPU. Ça vérifie au passage que la bascule automatique vers le CPU fonctionne.

### Publier sur GitHub

Pense à conserver le bit exécutable des scripts :

```bash
git add .
git update-index --chmod=+x "Lancer Fantasy Renamer.command" build_app.sh
git commit -m "Fantasy Renamer 1.0"
```

Publie les apps compilées (`FantasyRenamer-arm64.zip`, `FantasyRenamer-x86_64.zip`) dans les **Releases** plutôt que dans le dépôt : elles sont trop lourdes pour Git.

---

## Licence

[MIT](LICENSE) : libre d'utilisation, de modification et de partage.

Modèle CLIP © OpenAI (licence MIT), distribué via Hugging Face.
