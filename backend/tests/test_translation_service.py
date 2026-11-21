import contextlib
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.app.services.translation_service import TranslationService, TranslationServiceError


def fake_load(service):
    service._english, service._turkish = "en", "tr"
    service.detector = MagicMock()
    service.detector.compute_language_confidence.return_value = 0.9
    service._torch = SimpleNamespace(inference_mode=contextlib.nullcontext)
    service.tokenizer = MagicMock()
    service.tokenizer.model_max_length = 512
    service.tokenizer.return_value = {"input_ids": SimpleNamespace(shape=(1, 12))}
    service.model = MagicMock()
    service.model.generate.return_value = [[1, 2, 3]]


class TranslationServiceTests(unittest.TestCase):
    def setUp(self):
        with patch.object(TranslationService, "_load_resources", fake_load):
            self.service = TranslationService()

    def test_turkish_queries_use_model_outputs(self):
        # Sözlük dışı ifadeler model yolundan geçer; sözlük burada kapatılır.
        lexicon_off = patch("backend.app.services.object_lexicon.lookup", return_value=None)
        self.addCleanup(lexicon_off.stop)
        lexicon_off.start()
        examples = {"halı": "rug", "yastık": "pillow", "laptop çantası": "laptop bag",
                    "masa lambası": "table lamp", "saksıdaki bitki": "potted plant",
                    "kahve fincanı": "coffee cup", "kırmızı spor ayakkabı": "red sneakers"}
        for query, translation in examples.items():
            with self.subTest(query=query):
                self.service.tokenizer.decode.return_value = translation
                result = self.service.prepare_query(query)
                self.assertEqual(result["detected_language"], "tr")
                self.assertEqual(result["translated_query"], translation)
                self.assertEqual(result["primary_query"], translation)
                self.assertEqual(result["original_query"], query)
        self.assertEqual(self.service.model.generate.call_count, len(examples))

    def test_english_bypasses_translation(self):
        for query in ["bag", "rug", "person", "red sneakers"]:
            with self.subTest(query=query):
                result = self.service.prepare_query(query)
                self.assertEqual(result["detected_language"], "en")
                self.assertIsNone(result["translated_query"])
                self.assertEqual(result["primary_query"], query)
        self.service.model.generate.assert_not_called()

    def test_ascii_turkish_uses_detector(self):
        self.service.detector.compute_language_confidence.return_value = 0.2
        self.service.tokenizer.decode.return_value = "table lamp"
        self.assertEqual(self.service.prepare_query("masa lambasi")["primary_query"], "table lamp")

    def test_lexicon_resolves_ambiguous_and_ascii_turkish_without_model(self):
        examples = {"kravat": "tie", "fare": "mouse", "yüz": "face", "insan": "person",
                    "Kravatlar": "tie", "canta": "bag", "kırmızı araba": "red car",
                    "kirmizi spor ayakkabi": "red sneakers", "güneş gözlüğü": "sunglasses",
                    "IŞIK": None}
        for query, expected in examples.items():
            with self.subTest(query=query):
                self.service.tokenizer.decode.return_value = "light"
                result = self.service.prepare_query(query)
                self.assertEqual(result["detected_language"], "tr")
                if expected is None:
                    self.assertEqual(result["translation_source"], "model")
                    continue
                self.assertEqual(result["translated_query"], expected)
                self.assertEqual(result["primary_query"], expected)
                self.assertEqual(result["translation_source"], "lexicon")
        self.assertEqual(self.service.model.generate.call_count, 1)

    def test_uncertain_short_words_default_to_turkish(self):
        # Lingua "kravat" için EN 0.55 verir; 0.60 altı Türkçe sayılır.
        self.service.detector.compute_language_confidence.return_value = 0.55
        self.assertEqual(self.service.detect_language("sehpa"), "tr")
        self.service.detector.compute_language_confidence.return_value = 0.9
        self.assertEqual(self.service.detect_language("stapler"), "en")
        # Sözlükteki İngilizce karşılıklar güvenden bağımsız İngilizcedir.
        self.service.detector.compute_language_confidence.return_value = 0.1
        for query in ["car", "tie", "red car", "TIE", "wine glass"]:
            with self.subTest(query=query):
                self.assertEqual(self.service.detect_language(query), "en")
                self.assertIsNone(self.service.prepare_query(query)["translated_query"])

    def test_original_and_translation_plural_are_preserved(self):
        self.service.tokenizer.decode.return_value = "red sneakers"
        original = "  kırmızı   spor ayakkabı  "
        result = self.service.prepare_query(original)
        self.assertEqual(result["original_query"], original)
        self.assertEqual(result["primary_query"], "red sneakers")

    def test_resources_loaded_only_once(self):
        with patch.object(TranslationService, "_load_resources", autospec=True, side_effect=fake_load) as loader:
            service = TranslationService()
            service.tokenizer.decode.return_value = "rug"
            service.prepare_query("halı")
            service.prepare_query("halı")
            service.prepare_query("bag")
            loader.assert_called_once()

    def test_model_load_failure_is_explained(self):
        with patch.object(TranslationService, "_load_resources", side_effect=OSError("offline")):
            with self.assertLogs("backend.app.services.translation_service", level="ERROR"):
                service = TranslationService()
        with self.assertRaises(TranslationServiceError) as error:
            service.translate("halı")
        self.assertEqual(error.exception.status_code, 503)
        self.assertIn("yüklenemedi", str(error.exception))
        self.assertEqual(service.prepare_query("bag")["primary_query"], "bag")

    def test_failed_generation_and_empty_output_are_explained(self):
        self.service.tokenizer.decode.return_value = ""
        with self.assertRaisesRegex(TranslationServiceError, "boş sonuç"):
            self.service.translate("halı")
        self.service.model.generate.side_effect = RuntimeError("model error")
        with self.assertLogs("backend.app.services.translation_service", level="ERROR"):
            with self.assertRaisesRegex(TranslationServiceError, "çevrilemedi"):
                self.service.translate("halı")

    def test_empty_or_overlong_queries_are_rejected(self):
        with self.assertRaises(TranslationServiceError) as error:
            self.service.prepare_query("  ")
        self.assertEqual(error.exception.status_code, 422)
        self.service.tokenizer.return_value = {"input_ids": SimpleNamespace(shape=(1, 513))}
        with self.assertRaisesRegex(TranslationServiceError, "çok uzun"):
            self.service.translate("halı")
        self.service.model.generate.assert_not_called()


@unittest.skipUnless(os.environ.get("RUN_TRANSLATION_SMOKE") == "1", "Gerçek model testi isteğe bağlıdır.")
class RealTranslationTests(unittest.TestCase):
    def test_real_translation_bag_and_canta_have_same_primary(self):
        from backend.app.services.query_processor import process_query
        service = TranslationService()
        self.assertIsNone(service._load_error, str(service._load_error))
        english = process_query("bag", service)
        turkish = process_query("çanta", service)
        self.assertEqual(english["primary_query"], "bag")
        self.assertEqual(turkish["primary_query"], english["primary_query"])
        self.assertEqual(turkish["original_query"], "çanta")
        self.assertEqual(turkish["detected_language"], "tr")

    def test_real_model_translates_examples(self):
        service = TranslationService()
        self.assertIsNone(service._load_error, str(service._load_error))
        expected_words = {
            "halı": {"rug", "carpet"},
            "yastık": {"pillow", "cushion"},
            "laptop çantası": {"bag", "case"},
            "masa lambası": {"lamp"},
        }
        for query, alternatives in expected_words.items():
            with self.subTest(query=query):
                result = service.prepare_query(query)
                self.assertEqual(result["detected_language"], "tr")
                self.assertTrue(result["translated_query"])
                self.assertNotEqual(result["primary_query"].casefold(), query.casefold())
                words = set(result["primary_query"].casefold().strip(".").split())
                self.assertTrue(words & alternatives, result["primary_query"])
        for query in ["bag", "rug"]:
            self.assertEqual(service.prepare_query(query)["primary_query"], query)
            self.assertIsNone(service.prepare_query(query)["translated_query"])


if __name__ == "__main__":
    unittest.main()
