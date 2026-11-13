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


class Classification(BaseModel):
    section: Topic
    language: str = Field(description="Language of the latest customer message, e.g. English")
    needs_human: bool = Field(description="True when an always-escalate rule applies")
    serious_reaction: bool = Field(
        default=False,
        description="True when the customer mentions a serious reaction, chest pain, "
        "difficulty breathing, or swelling after taking a product",
    )
    reason: str = Field(description="One sentence explaining the classification")
    acknowledgement: str = Field(
        description="Short note to the customer, in English, that a colleague will reply shortly"
    )


class Issue(BaseModel):
    """A problem with an item the customer received."""

    problem: Literal["damaged", "wrong-item", "expired", "opened-return", "other"]
    product: str | None = Field(default=None, description="Product name, e.g. Wellwoman Max")
    hours_since_purchase: int | None = Field(
        default=None, description="Hours since the customer bought the item, when known"
    )
    has_photo: bool = Field(
        default=False, description="True when the customer already sent a photo of the problem"
    )
    has_order_confirmation: bool = Field(
        default=False, description="True when the customer already sent the order confirmation"
    )


class AgentReply(BaseModel):
    action: Literal["reply", "escalate"]
    reply: str = Field(description="The email to the customer, plain text")
    reasoning: str = Field(description="Which knowledge base entries you used, and why")
    enough_information: bool = Field(description="True when the knowledge base answers the question")
    promises_an_action: bool = Field(
        description="True when the reply promises a refund, replacement, exchange, price, "
        "delivery fee, delivery date, or call"
    )
    issue: Issue | None = Field(
        default=None,
        description="Fill in when the customer reports a damaged, wrong, or expired item, "
        "or wants to return an opened product",
    )


class Decision(BaseModel):
    action: Literal["reply", "escalate"]
    section: str
    reply: str
    reason: str
    proposed_action: str | None = None
