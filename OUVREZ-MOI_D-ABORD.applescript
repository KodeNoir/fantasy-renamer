-- =============================================================================
--  Fantasy Renamer – Autoriser l'app sur macOS (1 clic)
--
--  Pourquoi ce fichier ?
--  macOS bloque par sécurité les apps téléchargées qui ne sont pas signées
--  par un compte Apple payant (le message « Apple n'a pas pu confirmer que… »).
--  Ce petit script retire ce blocage sur l'app située À CÔTÉ de lui, puis la
--  lance. Il ne touche à rien d'autre sur ton Mac.
--
--  COMMENT FAIRE :
--     Clique sur le bouton « ▶︎  Exécuter » en haut à droite de cette fenêtre.
--     C'est tout. Tu peux ensuite fermer cette fenêtre.
--
--  Tu peux lire ci-dessous exactement ce que fait le script.
-- =============================================================================

-- Mode test automatique (GitHub Actions) : pas de fenêtres de dialogue
set modeTest to (do shell script "printf %s \"${FR_CI:-}\"") is "1"

-- 1) Dossier dans lequel se trouve ce script
set scriptPosix to POSIX path of (path to me)
if scriptPosix contains "Script Editor.app" or scriptPosix contains "Éditeur de script.app" then
	-- Certaines versions de l'Éditeur de script renvoient leur propre chemin :
	-- on demande alors le fichier du document ouvert.
	try
		tell application id "com.apple.ScriptEditor2" to set scriptPosix to POSIX path of (file of front document as alias)
	end try
end if
set scriptDir to do shell script "dirname " & quoted form of scriptPosix

-- 2) L'app Fantasy Renamer, juste à côté de ce script
set appPath to scriptDir & "/Fantasy Renamer.app"

-- 3) Vérifier que l'app est bien là
try
	do shell script "test -d " & quoted form of appPath
on error
	if not modeTest then display dialog "« Fantasy Renamer.app » est introuvable à côté de ce script.

Garde ce fichier dans le MÊME dossier que l'app, puis réessaie." buttons {"OK"} default button 1 with icon stop with title "Fantasy Renamer"
	error "App introuvable : " & appPath
end try

-- 4) Retirer le blocage « téléchargé depuis Internet » (quarantaine), sur l'app
--    et sur tous les fichiers qu'elle contient. « || true » : ne pas échouer si
--    certains fichiers n'avaient pas ce marquage.
do shell script "xattr -r -d com.apple.quarantine " & quoted form of appPath & " 2>/dev/null || true"
do shell script "xattr -d com.apple.quarantine " & quoted form of appPath & " 2>/dev/null || true"

-- 5) S'assurer que le programme interne reste exécutable
do shell script "chmod +x " & quoted form of (appPath & "/Contents/MacOS/Fantasy Renamer")

-- 6) Lancer l'application
do shell script "open " & quoted form of appPath

-- 7) Message de fin
if not modeTest then display dialog "C'est bon ✨

Fantasy Renamer est autorisé et va s'ouvrir.
Tu peux fermer cette fenêtre.

Au tout premier lancement, l'app télécharge une seule fois son modèle d'IA (≈ 600 Mo) : c'est normal si elle met quelques minutes." buttons {"Parfait"} default button 1 with title "Fantasy Renamer"
