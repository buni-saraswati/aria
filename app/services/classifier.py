import json
import logging
from openai import AzureOpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from config import Config
from app.models.decision import (
    Decision, ClassificationResult,
    Reversibility, ImpactLevel, RouteDecision
)

logger = logging.getLogger(__name__)

ROUTE_MATRIX = {
    (Reversibility.REVERSIBLE,   ImpactLevel.LOW):      RouteDecision.AUTO_APPROVE,
    (Reversibility.REVERSIBLE,   ImpactLevel.MEDIUM):   RouteDecision.AUTO_APPROVE,
    (Reversibility.REVERSIBLE,   ImpactLevel.HIGH):     RouteDecision.NEEDS_APPROVAL,
    (Reversibility.REVERSIBLE,   ImpactLevel.CRITICAL): RouteDecision.NEEDS_APPROVAL,
    (Reversibility.IRREVERSIBLE, ImpactLevel.LOW):      RouteDecision.NEEDS_APPROVAL,
    (Reversibility.IRREVERSIBLE, ImpactLevel.MEDIUM):   RouteDecision.NEEDS_APPROVAL,
    (Reversibility.IRREVERSIBLE, ImpactLevel.HIGH):     RouteDecision.NEEDS_APPROVAL,
    (Reversibility.IRREVERSIBLE, ImpactLevel.CRITICAL): RouteDecision.HARD_BLOCK,
    (Reversibility.UNKNOWN,      ImpactLevel.LOW):      RouteDecision.NEEDS_APPROVAL,
    (Reversibility.UNKNOWN,      ImpactLevel.MEDIUM):   RouteDecision.NEEDS_APPROVAL,
    (Reversibility.UNKNOWN,      ImpactLevel.HIGH):     RouteDecision.NEEDS_APPROVAL,
    (Reversibility.UNKNOWN,      ImpactLevel.CRITICAL): RouteDecision.HARD_BLOCK,
}

SYSTEM_PROMPT = """
You are ARIA's classification engine. Your job is to evaluate AI agent actions
in enterprise environments and assess their risk.

For every action, return a JSON object with exactly these fields:

{
  "reversibility": "reversible" | "irreversible" | "unknown",
  "impact": "low" | "medium" | "high" | "critical",
  "risk_reason": "<one sentence explaining the risk in plain english>",
  "suggested_approvers": ["<role or email>"],
  "confidence": <float between 0.0 and 1.0>
}

Guidelines:
- reversible: action can be undone (send draft, flag record, generate report)
- irreversible: action cannot be undone (wire transfer, delete data, send mass email)
- unknown: you cannot determine reversibility from the context given
- low:      no financial/data/compliance risk
- medium:   moderate risk, affects internal records
- high:     significant risk, affects external parties or large data
- critical: cannot be undone AND has major financial, legal, or data consequences
- suggested_approvers: role titles not names (e.g. "Finance Manager", "CFO")
- confidence: how confident you are in this classification

Return ONLY the JSON object. No explanation, no markdown, no extra text.
""".strip()


class Classifier:
    def __init__(self):
        self.client = AzureOpenAI(
            azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
            api_key=Config.AZURE_OPENAI_KEY,
            api_version="2024-12-01-preview"
        )

    def classify(self, decision: Decision) -> ClassificationResult:
        """
        Classify a decision with automatic retry on transient failures.
        Falls back to maximum caution if all retries exhausted.
        """
        try:
            return self._classify_with_retry(decision)
        except Exception as e:
            logger.error(
                f"All retries exhausted for decision {decision.decision_id}: {e}. "
                f"Applying safe fallback classification."
            )
            return self._fallback_classification()

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    def _classify_with_retry(self, decision: Decision) -> ClassificationResult:
        """Inner method — retried up to 3 times with exponential backoff."""
        user_message = f"""
Action Type:  {decision.action_type}
Description:  {decision.description}
Context:      {decision.context or "No additional context provided."}
Payload:      {json.dumps(decision.payload, indent=2)}
""".strip()

        logger.info(f"Classifying decision: {decision.decision_id}")

        response = self.client.chat.completions.create(
            model=Config.AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1,
            max_tokens=300
        )

        raw = response.choices[0].message.content.strip()

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error(f"Classifier returned invalid JSON: {raw}")
            # raise so tenacity retries
            raise ValueError(f"Invalid JSON from classifier: {e}") from e

        # validate required fields present
        required = {"reversibility", "impact", "risk_reason", "confidence"}
        missing = required - set(parsed.keys())
        if missing:
            raise ValueError(f"Classifier response missing fields: {missing}")

        reversibility = Reversibility(parsed["reversibility"])
        impact = ImpactLevel(parsed["impact"])
        route = ROUTE_MATRIX.get((reversibility, impact), RouteDecision.NEEDS_APPROVAL)

        result = ClassificationResult(
            reversibility=reversibility,
            impact=impact,
            risk_reason=parsed["risk_reason"],
            suggested_approvers=parsed.get("suggested_approvers", []),
            confidence=float(parsed["confidence"]),
            route=route
        )

        logger.info(
            f"Classified {decision.decision_id}: "
            f"{reversibility.value}/{impact.value} → {route.value} "
            f"(confidence: {result.confidence})"
        )
        return result

    def _fallback_classification(self) -> ClassificationResult:
        """
        Safe fallback when all retries fail.
        Always needs_approval — never auto-approve or hard-block on a failed classification.
        """
        return ClassificationResult(
            reversibility=Reversibility.UNKNOWN,
            impact=ImpactLevel.HIGH,
            risk_reason="Classification service unavailable — defaulting to human review.",
            suggested_approvers=["System Administrator"],
            confidence=0.0,
            route=RouteDecision.NEEDS_APPROVAL
        )