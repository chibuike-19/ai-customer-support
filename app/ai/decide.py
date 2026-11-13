from app.ai.agent import write_reply
from app.ai.classifier import classify
from app.ai.rules import CUSTOMER_STEPS, resolve_issue
from app.ai.schemas import Decision

SAFETY_NOTE = "Please stop taking the product and seek medical help right away."


def decide(thread: str, has_attachments: bool = False) -> Decision:
    """Run the AI steps for one email thread. The models propose, this function decides."""
    classification = classify(thread)

    acknowledgement = classification.acknowledgement
    if classification.serious_reaction and SAFETY_NOTE.lower() not in acknowledgement.lower():
        # The escalation rules require this sentence, so do not leave it to the model.
        greeting, _, rest = acknowledgement.partition("\n\n")
        acknowledgement = f"{greeting}\n\n{SAFETY_NOTE}\n\n{rest}" if rest else f"{SAFETY_NOTE}\n\n{greeting}"

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
        return escalate(classification.reason)

    answer = write_reply(thread, classification.section)
    if answer.action == "escalate":
        return escalate(answer.reasoning)
    if not answer.enough_information:
        return escalate("The knowledge base does not answer this")
    if answer.issue:
        step = resolve_issue(answer.issue)
        if step not in CUSTOMER_STEPS:
            return escalate(f"Next step: {step}", proposed_action=step)
    if answer.promises_an_action:
        return escalate("The reply promises an action")

    return Decision(
        action="reply",
        section=classification.section,
        reply=answer.reply,
        reason=answer.reasoning,
    )
