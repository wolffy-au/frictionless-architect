"""Presidio-backed detection (research.md R1, R2).

The `AnalyzerEngine`/`AnonymizerEngine` pair, and the spaCy `en_core_web_lg` NLP
engine behind it, are built once at module import and reused across calls -- model
load is the expensive part of SC-005's 2-second budget and must happen once, not
per `scrub()` call.
"""

from __future__ import annotations

from typing import cast

from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from presidio_anonymizer.entities import RecognizerResult as AnonymizerRecognizerResult

#: PII categories FR-002 requires (name/email/phone/physical-address), backed by
#: Presidio's built-in recognizers over the `en_core_web_lg` model (research.md R1).
PII_ENTITIES = ["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "LOCATION"]

#: PHI categories with a built-in Presidio recognizer (research.md R2).
_BUILTIN_PHI_ENTITIES = ["US_SSN", "MEDICAL_LICENSE"]

#: ADR-0014's named PHI categories with no built-in Presidio recognizer, covered by a
#: small custom `PatternRecognizer` set (research.md R2).
_CUSTOM_PHI_RECOGNIZERS = [
    PatternRecognizer(
        supported_entity="MEDICAL_RECORD_NUMBER",
        patterns=[Pattern(name="mrn", regex=r"\bMRN[-:\s]?\d{6,10}\b", score=0.85)],
    ),
    PatternRecognizer(
        supported_entity="DIAGNOSIS_CODE",
        patterns=[Pattern(name="icd10", regex=r"\b[A-TV-Z][0-9][0-9AB]\.?[0-9A-TV-Z]{0,4}\b", score=0.6)],
    ),
]

PHI_ENTITIES = [*_BUILTIN_PHI_ENTITIES, *(r.supported_entities[0] for r in _CUSTOM_PHI_RECOGNIZERS)]

ALL_ENTITIES = [*PII_ENTITIES, *PHI_ENTITIES]


def _build_analyzer() -> AnalyzerEngine:
    provider = NlpEngineProvider(
        nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}],
        }
    )
    analyzer = AnalyzerEngine(nlp_engine=provider.create_engine(), supported_languages=["en"])
    for recognizer in _CUSTOM_PHI_RECOGNIZERS:
        analyzer.registry.add_recognizer(recognizer)
    return analyzer


_analyzer = _build_analyzer()
_anonymizer = AnonymizerEngine()


def analyze(text: str) -> list[RecognizerResult]:
    """Run every registered PII/PHI recognizer over `text`.

    Returns:
        One `RecognizerResult` per detected span/category pair -- a span matching
        more than one category yields more than one result sharing the same span
        (spec Edge Cases).
    """
    # Presidio ships no type stubs; `follow_imports = "skip"` (platform/pyproject.toml)
    # makes every presidio_* symbol `Any` to mypy, so the real return type is asserted
    # here rather than inferred.
    return cast("list[RecognizerResult]", _analyzer.analyze(text=text, entities=ALL_ENTITIES, language="en"))


def anonymize(text: str, results: list[RecognizerResult]) -> str:
    """Redact every detected span in `text`, replacing it with `<CATEGORY>`.

    Args:
        text: The original text.
        results: The spans to redact, from `analyze()`.

    Returns:
        `text` with each span replaced; identical to `text` when `results` is empty.
    """
    if not results:
        return text
    operators = {
        result.entity_type: OperatorConfig("replace", {"new_value": f"<{result.entity_type}>"}) for result in results
    }
    anonymizer_results = [
        AnonymizerRecognizerResult(entity_type=r.entity_type, start=r.start, end=r.end, score=r.score) for r in results
    ]
    return cast("str", _anonymizer.anonymize(text=text, analyzer_results=anonymizer_results, operators=operators).text)
