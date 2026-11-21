import unittest
from unittest.mock import MagicMock, patch

from backend.app.services.query_processor import normalize_primary_query, process_query


class QueryProcessorTests(unittest.TestCase):
    def make_translator(self, original, english, language="tr"):
        translator = MagicMock()
        translator.prepare_query.return_value = {
            "original_query": original,
            "detected_language": language,
            "translated_query": english if language == "tr" else None,
            "primary_query": english,
        }
        return translator

    def test_model_translation_preserves_specificity(self):
        for original, translated in [("halı", "rug"), ("yastık", "pillow"),
                                     ("laptop çantası", "laptop bag"), ("masa lambası", "table lamp"),
                                     ("kırmızı spor ayakkabı", "red sneakers")]:
            with self.subTest(query=original):
                translator = self.make_translator(original, translated)
                result = process_query(original, translator)
                self.assertEqual(result["primary_query"], translated)
                self.assertEqual(result["translated_query"], translated)
                self.assertEqual(result["original_query"], original)
                translator.prepare_query.assert_called_once_with(original)

    def test_controlled_english_plurals_become_singular(self):
        examples = {"people": "person", "persons": "person", "men": "man", "women": "woman",
                    "bags": "bag", "cars": "car", "dogs": "dog", "cats": "cat",
                    "plants": "plant", "pillows": "pillow", "chairs": "chair"}
        for original, expected in examples.items():
            with self.subTest(query=original):
                result = process_query(original, self.make_translator(original, original, "en"))
                self.assertEqual(result["primary_query"], expected)
                self.assertEqual(result["original_query"], original)
                self.assertIsNone(result["translated_query"])

    def test_translated_plural_is_normalized_after_cleanup(self):
        result = process_query("çantalar", self.make_translator("çantalar", "The bags."))
        self.assertEqual(result["original_query"], "çantalar")
        self.assertEqual(result["translated_query"], "The bags.")
        self.assertEqual(result["primary_query"], "bag")
        self.assertEqual(result["fallback_queries"], ["handbag", "backpack", "tote bag"])

    def test_known_plural_in_specific_phrase_preserves_modifiers(self):
        self.assertEqual(normalize_primary_query(" The   red BAGS. "), "red bag")
        result = process_query("laptop bags", self.make_translator("laptop bags", "laptop bags", "en"))
        self.assertEqual(result["primary_query"], "laptop bag")
        self.assertEqual(result["fallback_queries"], ["computer bag", "laptop case"])

    def test_unknown_words_and_existing_singulars_are_not_changed(self):
        for query in ["glass", "bus", "scissors", "jeans", "red sneakers", "backpacks", "bag", "person", "handbags"]:
            with self.subTest(query=query):
                self.assertEqual(normalize_primary_query(query), query)
                self.assertEqual(normalize_primary_query(normalize_primary_query(query)), query)

    def test_translation_sentence_wrapper_is_not_a_detector_prompt(self):
        translator = self.make_translator("çanta", "The bag.")
        result = process_query("çanta", translator)
        self.assertEqual(result["primary_query"], "bag")
        self.assertEqual(result["translated_query"], "The bag.")
        self.assertEqual(result["fallback_queries"], ["handbag", "backpack", "tote bag"])

    def test_normalization_preserves_modifiers_and_unknown_plural(self):
        translator = self.make_translator("kırmızı spor ayakkabı", "The red sneakers.")
        self.assertEqual(process_query("kırmızı spor ayakkabı", translator)["primary_query"], "red sneakers")

    def test_fallback_is_independent_of_translation(self):
        translator = self.make_translator("çanta", "bag")
        result = process_query("çanta", translator)
        self.assertEqual(result["fallback_queries"], ["handbag", "backpack", "tote bag"])
        self.assertEqual(result["primary_query"], "bag")

    def test_specific_query_gets_only_specific_fallback(self):
        translator = self.make_translator("laptop çantası", "laptop bag")
        result = process_query("laptop çantası", translator)
        self.assertEqual(result["fallback_queries"], ["computer bag", "laptop case"])

    def test_duplicate_and_primary_fallbacks_are_removed(self):
        translator = self.make_translator("laptop çantası", "laptop bag")
        with patch.dict("backend.app.services.query_processor.FALLBACK_QUERIES",
                        {"laptop bag": ["Laptop Bag", "computer bag", " Computer   Bag "]}):
            self.assertEqual(process_query("laptop çantası", translator)["fallback_queries"], ["computer bag"])

    def test_unknown_translated_query_is_not_widened(self):
        translator = self.make_translator("kahve fincanı", "coffee cup")
        self.assertEqual(process_query("kahve fincanı", translator)["fallback_queries"], [])


if __name__ == "__main__":
    unittest.main()
