import os
import re
from functools import lru_cache

import requests
from langdetect import LangDetectException, detect


OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_CONNECT_TIMEOUT = float(os.getenv("OLLAMA_CONNECT_TIMEOUT", "2"))
OLLAMA_READ_TIMEOUT = float(os.getenv("OLLAMA_READ_TIMEOUT", "12"))

SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "bn": "Bengali",
    "ta": "Tamil",
    "te": "Telugu",
    "mr": "Marathi",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "kn": "Kannada",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "zh-cn": "Chinese",
    "zh-tw": "Chinese",
    "ar": "Arabic",
    "ja": "Japanese",
    "ml": "Malayalam",
}

SCRIPT_LANGUAGE_HINTS = [
    (r"[\u0980-\u09FF]", "bn"),
    (r"[\u0B80-\u0BFF]", "ta"),
    (r"[\u0C00-\u0C7F]", "te"),
    (r"[\u0A80-\u0AFF]", "gu"),
    (r"[\u0A00-\u0A7F]", "pa"),
    (r"[\u0C80-\u0CFF]", "kn"),
    (r"[\u0D00-\u0D7F]", "ml"),
]

FAST_QUERY_TRANSLATIONS = {
    "hi": [
        (r"मासिक", "monthly"),
        (r"महीने|माह", "monthly"),
        (r"बिक्री", "sales"),
        (r"राजस्व", "revenue"),
        (r"ग्राहक", "customers"),
        (r"लाभ|मुनाफा", "profit"),
        (r"ऑर्डर|आर्डर|आदेश", "orders"),
        (r"ट्रेंड|रुझान", "trend"),
        (r"तुलना|कम्पेयर|compare", "compare"),
        (r"बनाम|वर्सेस", "versus"),
        (r"औसत", "average"),
        (r"कुल|टोटल", "total"),
        (r"शीर्ष|टॉप", "top"),
        (r"दिखाओ|दिखाइए|दिखाना|बताओ|बताइए", "show"),
        (r"डैशबोर्ड", "dashboard"),
        (r"बनाओ|बनाइए|बनाना", "create"),
        (r"अनुसार|के अनुसार|द्वारा", "by"),
        (r"और", "and"),
        (r"का|की|के|को|से", " "),
        (r"मुझे|मुजे|झे", " "),
    ],
    "bn": [
        (r"মাসিক|মাসান্ত", "monthly"),
        (r"বিক্রির|বিক্রয়|বিক্রি", "sales"),
        (r"প্রবণতা|ট্রেন্ড", "trend"),
        (r"দেখাও|দেখান|দেখাতে", "show"),
        (r"আমাকে", " "),
    ],
    "ta": [
        (r"மாதாந்திர|மாதம்", "monthly"),
        (r"விற்பனை", "sales"),
        (r"போக்கை|போக்கு|ட்ரெண்ட்|டிரெண்ட்", "trend"),
        (r"காட்டவும்|காட்டுங்கள்|காட்டு", "show"),
    ],
    "te": [
        (r"నెలవారీ|మాసిక", "monthly"),
        (r"అమ్మకాల|అమ్మకాలు", "sales"),
        (r"ట్రెండ్|ప్రవణత|ధోరణి", "trend"),
        (r"చూపించండి|చూపించు", "show"),
    ],
    "mr": [
        (r"मासिक|महिनावार|महिन्याचा|महीन्याचा", "monthly"),
        (r"विक्री", "sales"),
        (r"ट्रेंड|प्रवृत्ती|कल", "trend"),
        (r"दाखवा|दाखवा", "show"),
        (r"चा|ची|चे", " "),
    ],
    "gu": [
        (r"માસિક|માસવાર", "monthly"),
        (r"વેચાણ", "sales"),
        (r"ટ્રેન્ડ|પ્રવૃત્તિ", "trend"),
        (r"બતાવો|દર્શાવો", "show"),
        (r"નો|ની|ના", " "),
    ],
    "pa": [
        (r"ਮਹੀਨਾਵਾਰ|ਮਾਸਿਕ", "monthly"),
        (r"ਵਿਕਰੀ", "sales"),
        (r"ਰੁਝਾਨ|ਟ੍ਰੈਂਡ", "trend"),
        (r"ਦਿਖਾਓ|ਦਿਖਾਉ", "show"),
    ],
    "kn": [
        (r"ಮಾಸಿಕ|ತಿಂಗಳವಾರು|ತಿಂಗಳ", "monthly"),
        (r"ಮಾರಾಟದ|ಮಾರಾಟ", "sales"),
        (r"ಪ್ರವೃತ್ತಿಯನ್ನು|ಪ್ರವೃತ್ತಿ|ಟ್ರೆಂಡ್|ಧೋರಣಿ", "trend"),
        (r"ತೋರಿಸಿ|ತೋರಿಸು", "show"),
    ],
    "es": [
        (r"mensual|mensualmente", "monthly"),
        (r"ventas|venta", "sales"),
        (r"tendencia", "trend"),
        (r"mostrar|muestra|muestre", "show"),
        (r"\bde\b|\bdel\b|\bla\b|\bel\b", " "),
    ],
    "fr": [
        (r"mensuelle|mensuel", "monthly"),
        (r"ventes|vente", "sales"),
        (r"tendance", "trend"),
        (r"afficher|montrer|montrez", "show"),
        (r"\bdes\b|\bde\b|\bla\b|\ble\b", " "),
    ],
    "de": [
        (r"monatlichen|monatliche|monatlich", "monthly"),
        (r"verkaufstrend", "sales trend"),
        (r"verkäufe|verkauf|umsatz", "sales"),
        (r"trend", "trend"),
        (r"anzeigen|zeige", "show"),
    ],
    "zh-cn": [
        (r"每月|月度|月次", "monthly"),
        (r"销售", "sales"),
        (r"趋势", "trend"),
        (r"显示|展示", "show"),
    ],
    "zh-tw": [
        (r"每月|月度|月次", "monthly"),
        (r"銷售", "sales"),
        (r"趨勢", "trend"),
        (r"顯示|展示", "show"),
    ],
    "ar": [
        (r"الشهري|شهرية|شهريا", "monthly"),
        (r"المبيعات|مبيعات", "sales"),
        (r"اتجاه|اتجاهات|ترند", "trend"),
        (r"عرض|اظهار|إظهار", "show"),
    ],
    "ja": [
        (r"月次|毎月|月間", "monthly"),
        (r"売上|販売", "sales"),
        (r"トレンド|傾向", "trend"),
        (r"表示する|表示", "show"),
    ],
    "ml": [
        (r"മാസാന്ത|മാസിക|മാസവാരി", "monthly"),
        (r"വിൽപ്പന", "sales"),
        (r"പ്രവണത|ട്രെൻഡ്", "trend"),
        (r"കാണിക്കുക|കാണിക്കൂ", "show"),
    ],
}

FAST_ENGLISH_QUERY_KEYWORDS = {
    "show",
    "trend",
    "sales",
    "revenue",
    "customers",
    "profit",
    "orders",
    "average",
    "total",
    "top",
    "dashboard",
    "compare",
    "versus",
    "monthly",
    "daily",
}


def _detect_indic_script_language(sample):
    for pattern, language_code in SCRIPT_LANGUAGE_HINTS:
        if re.search(pattern, sample):
            return language_code
    if re.search(r"[\u0900-\u097F]", sample):
        try:
            devanagari_code = detect(sample).lower()
        except LangDetectException:
            devanagari_code = "hi"
        if devanagari_code == "mr":
            return "mr"
        return "hi"
    return None


def detect_input_language(text):
    sample = (text or "").strip()
    if not sample:
        return "en", "English"
    script_language = _detect_indic_script_language(sample)
    if script_language and script_language in SUPPORTED_LANGUAGES:
        return script_language, SUPPORTED_LANGUAGES[script_language]
    try:
        code = detect(sample).lower()
    except LangDetectException:
        code = "en"
    if code not in SUPPORTED_LANGUAGES and code.startswith("zh"):
        code = "zh-cn"
    if code not in SUPPORTED_LANGUAGES:
        return "en", "English"
    return code, SUPPORTED_LANGUAGES[code]


def is_english_language(code):
    return str(code).lower() == "en"


def _quick_translate_query_to_english(text, language_code):
    content = (text or "").strip().lower()
    if not content:
        return ""

    translated = content
    for pattern, replacement in FAST_QUERY_TRANSLATIONS.get(str(language_code).lower(), []):
        translated = re.sub(pattern, f" {replacement} ", translated, flags=re.IGNORECASE)

    translated = re.sub(r"[^\x00-\x7F]+", " ", translated)
    translated = re.sub(r"[^a-z0-9\s]", " ", translated)
    translated = re.sub(r"\s+", " ", translated).strip()
    return translated


def _is_usable_english_query(text):
    tokens = set(re.findall(r"[a-z0-9]+", (text or "").lower()))
    return bool(tokens & FAST_ENGLISH_QUERY_KEYWORDS)


def _ask_ollama(prompt):
    payload = {"model": "llama3", "prompt": prompt, "stream": False}
    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=(OLLAMA_CONNECT_TIMEOUT, OLLAMA_READ_TIMEOUT),
    )
    response.raise_for_status()
    return response.json().get("response", "").strip()


@lru_cache(maxsize=256)
def _translate_text_cached(content, target_language_name):
    prompt = f"""
Translate the following business dashboard text into {target_language_name}.
Keep numbers, metric names, and structure accurate.
If the target language is an Indian language, use its native script.
Return only the translated text.

Text:
{content}
"""
    try:
        translated = _ask_ollama(prompt)
        return translated or content
    except requests.RequestException:
        return content


def translate_text(text, target_language_name):
    content = (text or "").strip()
    if not content:
        return ""
    return _translate_text_cached(content, target_language_name)


@lru_cache(maxsize=256)
def _translate_question_to_english_cached(content, source_language_name):
    prompt = f"""
Translate this user query into English for SQL and dashboard generation.
Preserve the business intent exactly.
Keep column names, numbers, filters, and metric words accurate.
Return only the English query text.

Source language:
{source_language_name}

Query:
{content}
"""
    try:
        translated = _ask_ollama(prompt)
        return translated.strip() or content
    except requests.RequestException:
        return content


def translate_question_to_english(text, input_language_code, input_language_name):
    content = (text or "").strip()
    if not content:
        return ""
    if is_english_language(input_language_code):
        return content
    fast_translation = _quick_translate_query_to_english(content, input_language_code)
    if _is_usable_english_query(fast_translation):
        return fast_translation
    return _translate_question_to_english_cached(content, input_language_name)


@lru_cache(maxsize=128)
def _translate_list_cached(serialized_items, target_language_name):
    items = tuple(item for item in serialized_items if str(item).strip())
    if not items:
        return tuple()

    separator = "<ITEM_SEP>"
    prompt = f"""
Translate each item below into {target_language_name}.
Keep numbers, metric names, and order accurate.
If the target language is an Indian language, use its native script.
Return only the translated items joined by this exact separator:
{separator}

Items:
{separator.join(items)}
"""
    try:
        translated = _ask_ollama(prompt)
        parts = tuple(part.strip() for part in translated.split(separator))
        if len(parts) == len(items) and all(parts):
            return parts
    except requests.RequestException:
        pass

    return tuple(translate_text(item, target_language_name) for item in items)


@lru_cache(maxsize=512)
def _bilingual_text_cached(content, input_language_code, input_language_name):
    if is_english_language(input_language_code):
        return content
    return translate_text(content, input_language_name)


def bilingual_text(text, input_language_code, input_language_name):
    content = (text or "").strip()
    if not content:
        return ""
    return _bilingual_text_cached(
        content,
        str(input_language_code).lower(),
        input_language_name,
    )


def bilingual_list(items, input_language_code, input_language_name):
    cleaned_items = [str(item).strip() for item in (items or []) if str(item).strip()]
    if not cleaned_items:
        return []
    if is_english_language(input_language_code):
        return cleaned_items
    return list(_translate_list_cached(tuple(cleaned_items), input_language_name))
