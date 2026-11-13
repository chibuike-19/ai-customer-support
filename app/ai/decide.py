import asyncio
import logging
import re

from app.ai.agent import write_reply
from app.ai.classifier import classify
from app.ai.rules import CUSTOMER_STEPS, resolve_issue
from app.ai.schemas import Classification, Decision

logger = logging.getLogger(__name__)

SAFETY_NOTE = "Please stop taking the product and seek medical help right away."
PROOF_REQUEST = (
    "So a colleague can review it, please send a clear photo of the product and the problem, "
    "and your order confirmation."
)
SIGN_OFF = "Kind regards,\nThree Pillars Global Limited"

# Sent when the classifier itself fails, so the customer still hears from us.
FALLBACK_ACKNOWLEDGEMENT = f"""Hello,

Thank you for your message. We received it, and a colleague will reply shortly.

{SIGN_OFF}"""


def finish_acknowledgement(classification: Classification) -> str:
    """Add what the knowledge base requires to the model's note, instead of trusting the model.

    The model writes the greeting and thanks. Python adds the safety note for a serious
    reaction, the request for proof for a damaged, wrong, or expired item, and the sign-off.
    """
    body = classification.acknowledgement
    # Drop any sign-off the model wrote, so it appears once, at the end.
    match = re.search(r"\b(kind regards|best regards|regards|sincerely)\b", body, re.IGNORECASE)
    if match:
        body = body[: match.start()]
    body = body.replace("Three Pillars Global Limited", "").strip().rstrip(",").strip()

    lower = body.lower()
    parts = [body]
    if classification.serious_reaction and SAFETY_NOTE.lower() not in lower:
        parts.append(SAFETY_NOTE)
    if classification.reports_item_problem and not ("photo" in lower and "order confirmation" in lower):
        parts.append(PROOF_REQUEST)
    parts.append(SIGN_OFF)
    return "\n\n".join(part for part in parts if part)


async def decide(thread: str, has_attachments: bool = False) -> Decision:
    """Run the AI steps for one email thread. The models propose, this function decides.

    Never raises for a model failure: anything that goes wrong becomes an escalation,
    so a colleague sees the email and the customer gets an acknowledgement.
    """
    try:
        classification = await classify(thread)
    except Exception as error:
        logger.exception("Classifier failed")
        return Decision(
            action="escalate",
            section="other",
            reply=FALLBACK_ACKNOWLEDGEMENT,
            reason=f"The classifier failed: {type(error).__name__}: {error}",
            proposed_action="model-error",
        )
    return await _decide(thread, classification, has_attachments)


async def _decide(thread: str, classification: Classification, has_attachments: bool) -> Decision:
    acknowledgement = finish_acknowledgement(classification)

    def escalate(reason: str, proposed_action: str | None = None) -> Decision:
        return Decision(
            action="escalate",
            section=classification.section,
            reply=acknowledgement,
            reason=reason,
            proposed_action=proposed_action,
        )

    if classification.serious_reaction:
        return escalate("The customer reports a serious reaction", proposed_action="urgent-health")
    if has_attachments:
        return escalate("The email has attachments")
    if classification.needs_human:
        return escalate(f"{classification.escalation_rule}: {classification.reason}")

    try:
        answer = await write_reply(thread, classification.section)
    except Exception as error:
        logger.exception("Agent failed")
        return escalate(
            f"The agent failed: {type(error).__name__}: {error}", proposed_action="model-error"
        )

    if answer.action == "escalate":
        return escalate(f"{answer.escalation} ({answer.escalation_rule_quote}): {answer.reasoning}")
    if not answer.enough_information:
        return escalate("The knowledge base does not answer this")
    if answer.issue:
        step = resolve_issue(answer.issue)
        if step not in CUSTOMER_STEPS:
            return escalate(f"Next step: {step}", proposed_action=step)
    if answer.promises_an_action:
        return escalate(f"The reply promises an action: {answer.promised_actions}")

    return Decision(
        action="reply",
        section=classification.section,
        reply=answer.reply,
        reason=answer.reasoning,
    )


def decide_sync(thread: str, has_attachments: bool = False) -> Decision:
    """For one-off scripts only. It starts a new event loop on every call, so long-running
    code such as the poller must run in one loop and await decide() instead."""
    return asyncio.run(decide(thread, has_attachments))
