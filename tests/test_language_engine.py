import unittest
from unittest.mock import patch

from language_engine import (
    bilingual_list,
    bilingual_text,
    detect_input_language,
    translate_question_to_english,
)


class LanguageEngineTests(unittest.TestCase):
    def test_detects_hindi_input(self):
        code, name = detect_input_language("शीर्ष 10 ग्राहक राजस्व के अनुसार")
        self.assertEqual(code, "hi")
        self.assertEqual(name, "Hindi")

    def test_detects_bengali_input(self):
        code, name = detect_input_language("রাজস্ব অনুযায়ী শীর্ষ ১০ গ্রাহক")
        self.assertEqual(code, "bn")
        self.assertEqual(name, "Bengali")

    def test_detects_tamil_input(self):
        code, name = detect_input_language("வருவாயின் அடிப்படையில் முதல் 10 வாடிக்கையாளர்கள்")
        self.assertEqual(code, "ta")
        self.assertEqual(name, "Tamil")

    def test_defaults_to_english_for_empty_input(self):
        code, name = detect_input_language("")
        self.assertEqual(code, "en")
        self.assertEqual(name, "English")

    @patch("language_engine.translate_text", return_value="यह सारांश है")
    def test_non_english_output_matches_input_language_only(self, _mock_translate):
        text = bilingual_text("This is the summary", "hi", "Hindi")
        self.assertEqual(text, "यह सारांश है")

    @patch("language_engine._ask_ollama", return_value="पहला<ITEM_SEP>दूसरा")
    def test_non_english_list_output_is_batched(self, _mock_ask):
        items = bilingual_list(["First summary", "Second summary"], "hi", "Hindi")
        self.assertEqual(items, ["पहला", "दूसरा"])

    @patch("language_engine._ask_ollama", return_value="top 10 customers by revenue")
    def test_non_english_query_is_translated_to_english_for_sql(self, _mock_ask):
        translated = translate_question_to_english(
            "राजस्व के अनुसार शीर्ष 10 ग्राहक",
            "hi",
            "Hindi",
        )
        self.assertIn("revenue", translated)
        self.assertIn("top", translated)
        self.assertIn("customers", translated)

    def test_hindi_trend_query_uses_fast_local_translation(self):
        translated = translate_question_to_english(
            "झे मासिक बिक्री का ट्रेंड दिखाओ",
            "hi",
            "Hindi",
        )
        self.assertEqual(translated, "monthly sales trend show")

    def test_multilingual_monthly_sales_trend_queries_use_fast_local_translation(self):
        cases = [
            ("আমাকে মাসিক বিক্রির প্রবণতা দেখাও", "bn", "Bengali"),
            ("மாதாந்திர விற்பனை போக்கை காட்டவும்", "ta", "Tamil"),
            ("నెలవారీ అమ్మకాల ట్రెండ్ చూపించండి", "te", "Telugu"),
            ("मासिक विक्रीचा ट्रेंड दाखवा", "mr", "Marathi"),
            ("માસિક વેચાણનો ટ્રેન્ડ બતાવો", "gu", "Gujarati"),
            ("ਮਹੀਨਾਵਾਰ ਵਿਕਰੀ ਦਾ ਰੁਝਾਨ ਦਿਖਾਓ", "pa", "Punjabi"),
            ("ಮಾಸಿಕ ಮಾರಾಟದ ಪ್ರವೃತ್ತಿಯನ್ನು ತೋರಿಸಿ", "kn", "Kannada"),
            ("Mostrar tendencia mensual de ventas", "es", "Spanish"),
            ("Afficher la tendance mensuelle des ventes", "fr", "French"),
            ("Monatlichen Verkaufstrend anzeigen", "de", "German"),
            ("显示每月销售趋势", "zh-cn", "Chinese"),
            ("عرض اتجاه المبيعات الشهري", "ar", "Arabic"),
            ("月次売上トレンドを表示する", "ja", "Japanese"),
            ("മാസാന്ത വിൽപ്പന പ്രവണത കാണിക്കുക", "ml", "Malayalam"),
        ]

        for query, code, name in cases:
            with self.subTest(language=code):
                translated = translate_question_to_english(query, code, name)
                self.assertIn("monthly", translated)
                self.assertIn("sales", translated)
                self.assertIn("trend", translated)

    def test_english_query_stays_unchanged(self):
        translated = translate_question_to_english(
            "top 10 customers by revenue",
            "en",
            "English",
        )
        self.assertEqual(translated, "top 10 customers by revenue")

    def test_english_output_stays_english(self):
        text = bilingual_text("This is the summary", "en", "English")
        self.assertEqual(text, "This is the summary")


if __name__ == "__main__":
    unittest.main()
