import pytest

from llm_summarizer.fallback import extractive_summary
from llm_summarizer.postprocessing import EmptyModelResponseError, clean_summary
from llm_summarizer.prompt import build_prompt


def test_prompt_contains_constraints_and_language() -> None:
    prompt = build_prompt("Исходный текст", "ru", 3)
    assert "no more than 3 sentences" in prompt.system
    assert "in Russian" in prompt.system
    assert prompt.user.endswith("Исходный текст")


def test_clean_summary_removes_heading_and_whitespace() -> None:
    assert clean_summary('  Резюме:  "Короткий   ответ." ') == "Короткий ответ."


def test_clean_summary_rejects_empty_value() -> None:
    with pytest.raises(EmptyModelResponseError):
        clean_summary("  \n ")


def test_fallback_takes_requested_number_of_sentences() -> None:
    text = "Первое предложение. Второе предложение! Третье предложение?"
    assert extractive_summary(text, 2) == "Первое предложение. Второе предложение!"
