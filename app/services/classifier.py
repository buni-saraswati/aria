import json
import logging
from openai import AzureOpenAI
from config import Config
from app.models.decision import (
    Decision, ClassificationResult,
    Reversibility, ImpactLevel, RouteDecision
)

logger = logging.getLogger(__name__)

# Routing logic is deterministic — no AI needed here
# AI gives us reversibility + impact, we derive the route
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

- suggested_approvers: role titles, not names (e.g. "Finance Manager", "CFO")
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
        Call GPT to classify a decision.
        Returns a ClassificationResult with reversibility, impact, route.
        """
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
            temperature=0.1,      # low temp = consistent, deterministic output
            max_tokens=300
        )

        raw = response.choices[0].message.content.strip()

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            logger.error(f"Classifier returned invalid JSON: {raw}")
            # safe fallback — treat as unknown/critical, needs approval
            parsed = {
                "reversibility": "unknown",
                "impact": "critical",
                "risk_reason": "Classification failed — defaulting to maximum caution.",
                "suggested_approvers": ["System Administrator"],
                "confidence": 0.0
            }

        reversibility = Reversibility(parsed.get("reversibility", "unknown"))
        impact = ImpactLevel(parsed.get("impact", "critical"))
        route = ROUTE_MATRIX.get((reversibility, impact), RouteDecision.NEEDS_APPROVAL)

        result = ClassificationResult(
            reversibility=reversibility,
            impact=impact,
            risk_reason=parsed.get("risk_reason", ""),
            suggested_approvers=parsed.get("suggested_approvers", []),
            confidence=float(parsed.get("confidence", 0.0)),
            route=route
        )

        logger.info(
            f"Classified {decision.decision_id}: "
            f"{reversibility.value}/{impact.value} → {route.value}"
        )
        return result