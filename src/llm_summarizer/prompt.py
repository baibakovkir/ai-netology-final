from dataclasses import dataclass


@dataclass(frozen=True)
class Prompt:
    system: str
    user: str


def build_prompt(text: str, language: str, max_sentences: int) -> Prompt:
    language_instruction = {
        "auto": "Use the same language as the source text.",
        "ru": "Write the summary in Russian.",
        "en": "Write the summary in English.",
    }[language]
    system = (
        "You summarize user-provided text accurately. Do not add facts that are absent "
        "from the source. Return only the summary without a heading or commentary. "
        f"Use no more than {max_sentences} sentences. {language_instruction}"
    )
    return Prompt(system=system, user=f"SOURCE TEXT:\n{text}")
