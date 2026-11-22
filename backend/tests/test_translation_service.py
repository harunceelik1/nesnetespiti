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
    """Eski "lexicon" yolu: sözlük + düz Marian. Geri dönüş seçeneği olarak korunur."""

    def setUp(self):
        with patch.object(TranslationService, "_load_resources", fake_load):
            self.service = TranslationService(strategy="lexicon")

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

    def test_compound_nouns_are_built_from_lexicon(self):
        from backend.app.services.object_lexicon import lookup
        examples = {"ilaç kutusu": "medicine box", "gözlük kutusu": "glasses case",
                    "kırmızı ilaç kutusu": "red medicine box", "çay paketi": "tea package",
                    "şampuan şişesi": "shampoo bottle", "gozluk kutusu": "glasses case",
                    "kitap kutusu": "book box", "bilinmeyen kutusu": None, "kutusu": None}
        for query, expected in examples.items():
            with self.subTest(query=query):
                self.assertEqual(lookup(query), expected)

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


class ContextTranslationTests(unittest.TestCase):
    """Varsayılan "context" yolu: sözlük kullanılmaz, sorgu bağlam cümlesi içinde çevrilir."""

    def setUp(self):
        with patch.object(TranslationService, "_load_resources", fake_load):
            self.service = TranslationService(strategy="context")
        self.sources = []
        self.outputs = {}

        def translate(text):
            self.sources.append(text)
            return self.outputs[text]
        self.service.translate = translate

    def test_default_strategy_is_context(self):
        self.assertEqual(TranslationService.strategy, "context")
        with patch.object(TranslationService, "_load_resources", fake_load):
            self.assertEqual(TranslationService().strategy, "context")
        with self.assertRaises(ValueError):
            TranslationService(strategy="llm")

    def test_query_is_translated_inside_context_sentence(self):
        self.outputs = {"Fotoğrafta yüz var.": "There's a face in the photo.",
                        "Fotoğrafta şişeler var.": "There are bottles in the picture.",
                        "Fotoğrafta kırmızı spor ayakkabı var.": "There are red sneakers in the photo."}
        for query, expected in {"yüz": "face", "şişeler": "bottles", "kırmızı spor ayakkabı": "red sneakers"}.items():
            with self.subTest(query=query):
                result = self.service.prepare_query(query)
                self.assertEqual(result["detected_language"], "tr")
                self.assertEqual(result["translation_source"], "context")
                self.assertEqual(result["primary_query"], expected)
        self.assertEqual(self.sources, list(self.outputs))

    def test_lexicon_is_not_used(self):
        # "kravat" sözlükte "tie"; context yolunda yine de modelden geçer.
        self.service.detector.compute_language_confidence.return_value = 0.55
        self.outputs = {"Fotoğrafta kravat var.": "There's a necktie in the photo."}
        with patch("backend.app.services.object_lexicon.lookup") as lookup:
            result = self.service.prepare_query("kravat")
        lookup.assert_not_called()
        self.assertEqual(result["primary_query"], "necktie")

    def test_unexpected_sentence_falls_back_to_plain_translation(self):
        self.service.detector.compute_language_confidence.return_value = 0.2
        self.outputs = {"Fotoğrafta palet var.": "Palette in the photo.", "palet": "pallet"}
        result = self.service.prepare_query("palet")
        self.assertEqual(result["translation_source"], "model")
        self.assertEqual(result["primary_query"], "pallet")

    def test_english_queries_are_not_translated(self):
        self.service.detector.compute_language_confidence.return_value = 0.9
        for query in ["bag", "stapler", "red sneakers"]:
            with self.subTest(query=query):
                result = self.service.prepare_query(query)
                self.assertEqual(result["detected_language"], "en")
                self.assertIsNone(result["translated_query"])
        self.assertEqual(self.sources, [])

    def test_extract_object(self):
        from backend.app.services.translation_service import extract_object
        cases = {"There is a remote in the photo.": "remote", "There's a hard hat in the picture.": "hard hat",
                 "In the photo, there are bottles.": "bottles", "The photo has a cat.": "cat",
                 "Remote in photo.": None, "There is a in the photo.": None}
        for sentence, expected in cases.items():
            with self.subTest(sentence=sentence):
                self.assertEqual(extract_object(sentence), expected)


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
