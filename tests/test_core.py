"""
Tests de la logique hors IA (noms, mémoire 30 jours, traitement par lot).
Lancer :  python -m unittest discover tests
Aucun téléchargement : un faux classifieur remplace CLIP.
"""

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image

from fantasy_renamer import config
from fantasy_renamer.classifier import ClassificationResult, load_image_for_analysis, ImageLoadError
from fantasy_renamer.history import NameHistory
from fantasy_renamer.names import FantasyNameGenerator, generate_procedural, is_valid_name
from fantasy_renamer.processor import BatchProcessor


class FakeClassifier:
    """Classe selon le nom du fichier : 'h' -> homme, 'f' -> femme, sinon lieu."""
    is_loaded = False

    def load(self, on_status):
        on_status("device", "Faux moteur de test")
        self.is_loaded = True

    def classify(self, path):
        load_image_for_analysis(path)          # vraie vérification de l'image
        cat = {"h": "homme", "f": "femme", "c": "creature"}.get(path.name[0], "lieu")
        return ClassificationResult(cat, 0.9, {cat: 0.9})


class TestNames(unittest.TestCase):
    def test_lists_are_single_words(self):
        gen = FantasyNameGenerator()
        for cat in config.CATEGORIES:
            self.assertGreater(gen.list_size(cat), 100)
            for n in gen.lists[cat]:
                self.assertTrue(is_valid_name(n), n)

    def test_procedural_names_valid(self):
        import random
        rng = random.Random(1)
        for cat in config.CATEGORIES:
            for _ in range(500):
                n = generate_procedural(cat, rng)
                self.assertTrue(is_valid_name(n), n)

    def test_fallback_when_list_exhausted(self):
        gen = FantasyNameGenerator(seed=3)
        forbidden = set(gen.lists["femme"])
        name = gen.pick("femme", forbidden)
        self.assertNotIn(name.casefold(), {n.casefold() for n in forbidden})
        self.assertTrue(is_valid_name(name))


class TestHistory(unittest.TestCase):
    def test_30_day_memory(self):
        with tempfile.TemporaryDirectory() as d:
            h = NameHistory(Path(d) / "history.json")
            now = datetime.now()
            h.add("Aldric", "homme", now=now - timedelta(days=31))
            h.add("Elara", "femme", now=now - timedelta(days=29))
            h2 = NameHistory(Path(d) / "history.json")      # relecture depuis le disque
            self.assertFalse(h2.is_recent("aldric"))
            self.assertTrue(h2.is_recent("ELARA"))
            self.assertEqual(len(h2), 1)                     # l'entrée > 30 j a été purgée

    def test_corrupted_file_does_not_crash(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "history.json"
            p.write_text("{pas du json")
            h = NameHistory(p)
            self.assertEqual(len(h), 0)
            h.add("Lyra", "femme")
            self.assertTrue(NameHistory(p).is_recent("Lyra"))


class TestBatch(unittest.TestCase):
    def _make_source(self, d: Path, n_images=60):
        src = d / "source"; src.mkdir()
        for i in range(n_images):
            prefix = "hflc"[i % 4]
            Image.new("RGB", (800, 600), (i * 4 % 255, 80, 120)).save(src / f"{prefix}_{i:03}.jpg")
        Image.new("RGBA", (300, 300), (0, 0, 0, 0)).save(src / "f_transparent.png")
        (src / "l_corrompue.jpg").write_bytes(b"\xff\xd8\xff\xe0 pas une vraie image")
        (src / "notes.txt").write_text("hello")
        (src / ".DS_Store").write_bytes(b"\0")
        return src

    def test_full_batch(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            src = self._make_source(d)
            dst = d / "dest"
            history = NameHistory(d / "history.json")
            events = []
            s = BatchProcessor(FakeClassifier(), history, FantasyNameGenerator(seed=0)).run(
                src, dst, on_event=events.append)

            self.assertEqual(s.renamed, 61)
            self.assertEqual(s.skipped, 2)           # corrompue + .txt
            self.assertEqual(s.errors, 0)
            out = [p for p in dst.iterdir() if p.suffix != ".csv"]
            self.assertEqual(len(out), 61)
            stems = [p.stem.casefold() for p in out]
            self.assertEqual(len(stems), len(set(stems)))        # tous uniques
            self.assertTrue(all(is_valid_name(p.stem) for p in out))
            self.assertEqual(len(list(src.iterdir())), 64)        # originaux intacts
            self.assertIsNotNone(s.report_path)
            self.assertTrue(any(e.kind == "done" for e in events))

            # 2e passage le même jour : aucun nom ne doit être réutilisé
            dst2 = d / "dest2"
            BatchProcessor(FakeClassifier(), history, FantasyNameGenerator(seed=0)).run(src, dst2)
            second = {p.stem.casefold() for p in dst2.iterdir() if p.suffix != ".csv"}
            self.assertEqual(len(second), 61)
            self.assertFalse(second & set(stems))

    def test_stop_request(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            src = self._make_source(d, 10)
            calls = {"n": 0}
            def stop():
                calls["n"] += 1
                return calls["n"] > 3
            s = BatchProcessor(FakeClassifier(), NameHistory(d / "h.json")).run(src, d / "o", should_stop=stop)
            self.assertTrue(s.cancelled)
            self.assertEqual(len(s.outcomes), 3)

    def test_same_folder_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                BatchProcessor(FakeClassifier(), NameHistory(Path(d) / "h.json")).run(Path(d), Path(d))

    def test_corrupt_image_detected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.png"; p.write_bytes(b"\x89PNG\r\n\x1a\n garbage")
            with self.assertRaises(ImageLoadError):
                load_image_for_analysis(p)


class LowConfidenceClassifier(FakeClassifier):
    def classify(self, path):
        load_image_for_analysis(path)
        return ClassificationResult("homme", 0.6, {"homme": 0.6})


class TestLowConfidence(unittest.TestCase):
    def test_flagged_in_log_and_report(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); src = d / "src"; src.mkdir()
            Image.new("RGB", (100, 100)).save(src / "a.jpg")
            events = []
            s = BatchProcessor(LowConfidenceClassifier(), NameHistory(d / "h.json")).run(src, d / "out", on_event=events.append)
            self.assertIn("à vérifier", [e for e in events if e.kind == "file"][0].message)
            self.assertIn("à vérifier", s.report_path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    unittest.main()
