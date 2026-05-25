"""Tests del ensamblaje de system prompt."""

from __future__ import annotations

import unittest

from app.models import ChatMessage, ChatOptions, ChatRequest, ClassificationMetadata, HeadConfidences
from app.prompts.builder import build_messages, build_output_format, build_system_prompt, select_rules
from app.prompts.modifiers import CONFIDENCE_RELIABLE_THRESHOLD


def _meta(**overrides: object) -> ClassificationMetadata:
    base = {
        "nivel_tecnico": "principiante",
        "urgencia": "alta",
        "emocion": "frustracion",
        "dominio": "backend",
        "confianza": 0.87,
    }
    base.update(overrides)
    return ClassificationMetadata(**base)  # type: ignore[arg-type]


class PromptBuilderTests(unittest.TestCase):
    def test_build_system_prompt_includes_all_dimensions(self) -> None:
        prompt = build_system_prompt(_meta())
        self.assertIn("Synapse", prompt)
        self.assertIn("principiante", prompt)
        self.assertIn("REGLAS POR URGENCIA", prompt)
        self.assertIn("REGLAS POR DOMINIO", prompt)
        self.assertIn("87%", prompt)

    def test_low_confidence_policy(self) -> None:
        prompt = build_system_prompt(_meta(confianza=0.4))
        self.assertIn("incierta", prompt.lower())

    def test_high_confidence_policy(self) -> None:
        prompt = build_system_prompt(_meta(confianza=CONFIDENCE_RELIABLE_THRESHOLD))
        self.assertIn("fiable", prompt.lower())

    def test_weak_head_in_rules(self) -> None:
        heads = HeadConfidences(
            nivel_tecnico=0.9,
            urgencia=0.88,
            emocion=0.3,
            dominio=0.85,
        )
        rules = select_rules(_meta(emocion="frustracion"), heads)
        self.assertTrue("debil" in rules.lower() or "incierto" in rules.lower())

    def test_weak_head_uncertainty_block(self) -> None:
        heads = HeadConfidences(
            nivel_tecnico=0.9,
            urgencia=0.88,
            emocion=0.3,
            dominio=0.85,
        )
        prompt = build_system_prompt(_meta(), heads)
        self.assertIn("SEÑALES DE INCERTIDUMBRE", prompt)

    def test_urgent_format(self) -> None:
        fmt = build_output_format(_meta(urgencia="alta", emocion="desesperado"))
        self.assertIn("ahora", fmt.lower())

    def test_build_messages_orders_roles(self) -> None:
        request = ChatRequest(
            pregunta="Como uso async?",
            metadata=_meta(),
            historial=[
                ChatMessage(rol="user", contenido="Hola"),
                ChatMessage(rol="assistant", contenido="Hola, en que ayudo?"),
            ],
            options=ChatOptions(),
        )
        messages = build_messages(request)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[-1]["content"], "Como uso async?")


if __name__ == "__main__":
    unittest.main()
