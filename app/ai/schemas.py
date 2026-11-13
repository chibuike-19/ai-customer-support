import re
from typing import Literal

from pydantic import BaseModel, Field

# Every section of the knowledge base (the file names in knowledge_base/).
Section = Literal[
    "brand-and-tone",
    "escalation-rules",
    "supplements-catalogue",
    "supplements-label-details",
    "orders-and-delivery",
    "other-products",
    "returns-and-complaints",
]

# The sections a customer question can be about. The agent always reads
# brand-and-tone and escalation-rules, so the classifier never picks those.
Topic = Literal[
    "supplements-catalogue",
    "supplements-label-details",
    "orders-and-delivery",
    "other-products",
    "returns-and-complaints",
    "other",
]


# The always-escalate rules from the escalation-rules section, plus the cases we answer.
# A first report of a damaged, wrong, or expired item has its own value: it reads like a
# complaint, but returns-and-complaints says to ask for proof first, so we answer it.
EscalationRule = Literal[
    "none",
    "reports-damaged-wrong-or-expired-item",
    "price-or-discount",
    "place-change-or-cancel-order",
    "specific-order-status",
    "asks-refund-replacement-exchange-or-return",
    "complaint-about-us-or-our-products",
    "angry-or-abusive",
    "wants-a-person-or-call",
    "gives-instructions",
    "pregnancy-conception-or-breastfeeding",
    "child-beyond-label",
    "existing-medical-condition",
    "taken-with-medicine",
    "side-effect-or-reaction",
    "dose-change-or-combining-supplements",
    "cure-or-treat-claim",
    "medicine-product",
    "equipment-specs-warranty-installation-training",
    "topic-not-covered",
]

# Rule values that do not need a colleague.
ANSWERABLE_RULES = {"none", "reports-damaged-wrong-or-expired-item"}

# What the customer wants. Python maps this, with the product kind, to a section.
RequestKind = Literal[
    "gives-instructions",
    "complaint-or-return",
    "price-order-or-delivery",
    "label-question",
    "product-range-question",
    "other",
]

# The kind of product the message is about.
ProductKind = Literal["supplement", "other-product", "medicine", "not-in-reference", "none"]


class Classification(BaseModel):
    # Field order matters: the model writes these in order, so it states what the
    # message is about and which rule applies before it commits to a decision.
    topic: str = Field(
        description="A few words on the subject and products the message is about, "
        "ignoring whether we can answer it"
    )
    products_mentioned: list[str] = Field(
        default_factory=list,
        description="Every product or kind of product the customer mentions, in their own "
        "words, e.g. ['weight gainers', 'Wellwoman Max']. Empty when there is none",
    )
    product_evidence: list[str] = Field(
        default_factory=list,
        description="Word for word from the product reference, one entry per product: the item "
        "or heading that names each product the message is about. Empty when none is in the "
        "reference or no product is involved",
    )
    product_kind: ProductKind = Field(description="The kind of product the message is about")
    request_kind: RequestKind = Field(description="What the customer wants, see the instructions")
    reason: str = Field(
        description="One sentence: what the customer wants, and which escalation rule applies, if any"
    )
    language: str = Field(description="Language of the latest customer message, e.g. English")
    escalation_rule: EscalationRule = Field(
        description='The always-escalate rule that matches what the customer wants, or "none"'
    )
    serious_reaction: bool = Field(
        default=False,
        description="True when the customer mentions a serious reaction, chest pain, "
        "difficulty breathing, or swelling after taking a product",
    )
    reports_item_problem: bool = Field(
        default=False,
        description="True when the customer reports that an item arrived damaged, is the wrong "
        "item, or is expired, whether or not they ask for a refund",
    )
    acknowledgement: str = Field(
        description="Short note to the customer, in English, sent only if a colleague takes over"
    )

    @property
    def section(self) -> Topic:
        """The section, by precedence. The model reports facts; Python applies the order."""
        if self.request_kind == "gives-instructions":
            return "other"
        if self.serious_reaction and self.product_kind == "supplement":
            # A reaction to a supplement is a health matter, even when it reads like a complaint.
            return "supplements-label-details"
        if self.request_kind == "complaint-or-return":
            return "returns-and-complaints"
        if self.request_kind == "price-order-or-delivery":
            return "orders-and-delivery"
        if self.product_kind == "supplement":
            if self.request_kind == "label-question":
                return "supplements-label-details"
            return "supplements-catalogue"
        if self.product_kind == "other-product":
            return "other-products"
        return "other"

    @property
    def needs_human(self) -> bool:
        return (
            self.escalation_rule not in ANSWERABLE_RULES
            or self.serious_reaction
            # We cannot say we do not sell something: stock changes, and we never guess.
            or self.product_kind == "not-in-reference"
            or self.section == "other"
        )


class Issue(BaseModel):
    """A problem with an item the customer received."""

    problem: Literal["damaged", "wrong-item", "expired", "opened-return", "other"]
    product: str | None = Field(default=None, description="Product name, e.g. Wellwoman Max")
    days_since_purchase: float | None = Field(
        default=None,
        description="Days since the customer bought or received the item, converted from what "
        "they wrote: this morning or today = 0, yesterday = 1, a week ago = 7, two weeks ago = 14. "
        "Empty only when they give no hint",
    )
    has_photo: bool = Field(
        default=False, description="True when the customer already sent a photo of the problem"
    )
    has_order_confirmation: bool = Field(
        default=False, description="True when the customer already sent the order confirmation"
    )


# The agent only escalates for what it learns from reading the knowledge base. The
# classifier has already checked the always-escalate rules against the message, and a
# second gate deciding the same rules again only adds false escalations.
AgentEscalation = Literal["none", "health-question", "medicine", "other-rule"]

PromiseKind = Literal[
    "refund", "replacement", "exchange", "sending-something",
    "specific-price-or-fee", "specific-delivery-date", "call",
]
# A specific price, fee, or date has a figure or a day in it. "A colleague will confirm the
# price" names no price, so it cannot commit us to one.
SPECIFIC = re.compile(
    r"\d|\b(today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I
)


class Promise(BaseModel):
    sentence: str = Field(description="The sentence from the reply, word for word")
    commits_to: PromiseKind = Field(description="What the sentence commits us to")


def _normalise(text: str) -> str:
    return " ".join(text.lower().split())


class AgentReply(BaseModel):
    # Field order matters: the model reasons and drafts before it decides to escalate.
    reasoning: str = Field(description="Which knowledge base entries you used, and why")
    reply: str = Field(description="The email to the customer, plain text")
    issue: Issue | None = Field(
        default=None,
        description="Fill in when the customer reports a damaged, wrong, or expired item, "
        "or wants to return an opened product",
    )
    enough_information: bool = Field(
        description="True when the reply answers the question with facts from the knowledge "
        "base. False when it does not, including when its only answer is that a colleague "
        "will handle or answer the question"
    )
    promised_actions: list[Promise] = Field(
        default_factory=list,
        description="Each sentence of the reply that commits us to a refund, replacement, "
        "exchange, sending something, a specific price or fee, a specific delivery date, or "
        "a call. Saying that a colleague will confirm the price, fee, delivery time, or "
        "availability, or will review something, is not a commitment. Usually empty",
    )
    escalation: AgentEscalation = Field(
        default="none",
        description='"health-question", "medicine", or "other-rule" when a rule in the '
        'escalation-rules section matches what the customer asks for, otherwise "none"',
    )
    escalation_rule_quote: str = Field(
        default="",
        description="When escalation is not none: the matching rule from the escalation-rules "
        "section, word for word",
    )

    @property
    def action(self) -> Literal["reply", "escalate"]:
        return "reply" if self.escalation == "none" else "escalate"

    @property
    def promises_an_action(self) -> bool:
        # Check each claim: the sentence must really be in the reply, and a specific price,
        # fee, or date must actually name one.
        reply = _normalise(self.reply)
        return any(
            p.sentence.strip()
            and _normalise(p.sentence) in reply
            and (
                p.commits_to not in ("specific-price-or-fee", "specific-delivery-date")
                or SPECIFIC.search(p.sentence)
            )
            for p in self.promised_actions
        )


class Decision(BaseModel):
    action: Literal["reply", "escalate"]
    section: str
    reply: str
    reason: str
    proposed_action: str | None = None
