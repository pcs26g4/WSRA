from dataclasses import dataclass

@dataclass(frozen=True)
class LLMPermission:
    mapper: bool = True
    interaction: bool = False
    form_filling: bool = True
    js_analyzer: bool = True

