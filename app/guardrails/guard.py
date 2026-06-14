"""The Guardrails orchestrator that composes the individual checks."""

from app.guardrails.base import GuardrailResult
from app.guardrails.injection import detect_prompt_injection
from app.guardrails.pii import redact_pii
from app.guardrails.toxicity import contains_blocked_terms


class Guardrails:
    """Composes input and output guards. Construct via :func:`get_guardrails`."""

    def __init__(
        self,
        *,
        block_injection: bool = True,
        redact_pii: bool = True,
        redact_pii_in_input: bool = False,
        min_faithfulness: float = 0.0,
        toxicity_denylist: list[str] | None = None,
    ):
        self.block_injection = block_injection
        self.redact_pii = redact_pii
        self.redact_pii_in_input = redact_pii_in_input
        self.min_faithfulness = min_faithfulness
        self.toxicity_denylist = toxicity_denylist or []

    def guard_input(self, text: str) -> GuardrailResult:
        """Check a user query before it reaches the model."""
        if self.block_injection:
            hits = detect_prompt_injection(text)
            if hits:
                return GuardrailResult(
                    allowed=False,
                    text=text,
                    action="block",
                    reasons=[f"prompt_injection:{h}" for h in hits],
                    findings={"injection": hits},
                )

        blocked = contains_blocked_terms(text, self.toxicity_denylist)
        if blocked:
            return GuardrailResult(
                allowed=False,
                text=text,
                action="block",
                reasons=[f"blocked_term:{t}" for t in blocked],
                findings={"blocked_terms": blocked},
            )

        out_text = text
        findings: dict = {}
        action = "allow"
        if self.redact_pii_in_input and self.redact_pii:
            out_text, pii = redact_pii(text)
            if pii:
                action = "redact"
                findings["pii"] = pii

        return GuardrailResult(
            allowed=True,
            text=out_text,
            action=action,
            reasons=[f"pii:{lbl}" for lbl, _ in findings.get("pii", [])],
            findings=findings,
        )

    def guard_output(
        self, text: str, *, contexts: list[str] | None = None
    ) -> GuardrailResult:
        """Sanitise a generated answer: redact PII, flag low grounding / blocked terms.

        Output is never hard-blocked (that would drop a useful answer); instead it
        is redacted and/or flagged so the caller can decide. ``allowed`` stays True.
        """
        reasons: list[str] = []
        findings: dict = {}
        action = "allow"
        out = text

        if self.redact_pii:
            out, pii = redact_pii(text)
            if pii:
                action = "redact"
                reasons += [f"pii:{lbl}" for lbl, _ in pii]
                findings["pii"] = pii

        blocked = contains_blocked_terms(out, self.toxicity_denylist)
        if blocked:
            action = "flag"
            reasons += [f"blocked_term:{t}" for t in blocked]
            findings["blocked_terms"] = blocked

        if self.min_faithfulness > 0.0 and contexts:
            from app.evaluation.answer_metrics import faithfulness

            score = faithfulness(out, contexts)
            findings["faithfulness"] = score
            if score < self.min_faithfulness:
                action = "flag"
                reasons.append(f"low_faithfulness:{score:.2f}")

        return GuardrailResult(
            allowed=True, text=out, action=action, reasons=reasons, findings=findings
        )
