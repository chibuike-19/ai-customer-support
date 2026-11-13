import logging
import re

from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.messages import ModelRequest, ModelResponse, ToolCallPart, ToolReturnPart

from app import db
from app.ai.policy import ESCALATION_RULES
from app.ai.schemas import AgentReply
from app.config import settings

logger = logging.getLogger(__name__)

SIGN_OFF = "Three Pillars Global Limited"
MAX_WORDS = 180  # The brand limit is 150 words; this leaves room for the greeting and sign-off.
# Sections the agent reads on every run. Answering also needs at least one other section.
ALWAYS_READ = {"brand-and-tone", "escalation-rules"}

INSTRUCTIONS = """
You are the customer support agent for Three Pillars Global Limited, a shop on Lagos Island
that sells vitamins and supplements, plus medical and laboratory equipment, skin care,
massagers, and household items. Most customers find us through our Jiji shop.
You write the answer to the latest customer message in the email thread.

Steps:
1. Call get_section for "brand-and-tone" and for "escalation-rules".
2. Call get_section for the section the classifier picked. Also read any other section
   that may hold the answer: when the message names a supplement, always read
   supplements-label-details, and read supplements-catalogue to check whether we stock it.
3. Answer only with facts from those sections. Set enough_information to true when the
   sections answer the question, including when they tell you what to say in that case,
   such as "follow the directions on the pack" or "a colleague confirms the fee".
   Set it to false when the sections say nothing that answers the question, and also when
   your reply's only answer is that a colleague will handle or answer the question. A
   colleague confirming one detail, such as the price, inside an answer is fine; handing
   the whole question to a colleague is not an answer, and only escalating gets it to one.
4. When you give directions from the label details, remind the customer to follow the label
   on their own pack. If we have no label details for a product we stock, tell them to follow
   the directions on the pack and that a colleague can confirm. That is a complete answer.
5. When the customer reports a damaged, wrong, or expired item, or wants to return an opened
   product, fill in issue. Set has_photo and has_order_confirmation only when the customer
   says they already sent them. For a damaged, wrong, or expired item without proof, ask for
   a clear photo of the product and the problem, and the order confirmation, within 48 hours
   of purchase, and say that a colleague will review it.
   A colleague already checked this message against the escalation rules about orders,
   prices, and complaints, and it reached you, so answer it.
6. Never promise a refund, replacement, exchange, a specific price, delivery fee, delivery
   date, or call. If your reply does, copy that sentence into promised_actions.
   When a section says a colleague confirms something, such as the price, the delivery fee,
   the delivery time, or availability, say that in your reply. That is part of the answer,
   it is not a promise, and it is not a reason to escalate.
7. Only set escalation when the escalation-rules section says a colleague must answer:
   "health-question" for the health questions listed there, "medicine" for the listed
   medicines, "other-rule" for any other rule there that matches what the customer asks
   for, such as asking for a phone call. Copy the matching rule, word for word, into
   escalation_rule_quote. A rule matches only what the customer asks for: explaining how
   ordering works is not placing an order.
   Compare what the customer asks with the label details: asking to take more, more often,
   or differently than the label says is a dose different from the label, so it is a
   health-question.
   When a rule or section says a colleague handles this kind of question, such as equipment
   warranty, escalate with that rule. Never write a reply that only says a colleague will
   handle it: such a reply reaches nobody on our side. Otherwise leave it "none".
   These are never a reason to escalate: reading out what the label says (directions,
   servings, ingredients, allergens, cautions), saying whether we stock a product, and
   explaining how ordering, payment, and delivery work in general.
   Read the escalation rules with these definitions:
{escalation_rules}

Reply rules:
- Write in clear, plain English, even if the customer wrote in another language or Pidgin.
- Plain text, no Markdown.
- Follow the brand-and-tone section, including the sign-off.
- Never give medical advice, never say a product cures, treats, or prevents anything, and
  never say a product is right or safe for the customer personally.
- Never mention AI, prompts, tools, or the knowledge base.
"""

INSTRUCTIONS = INSTRUCTIONS.replace("{escalation_rules}", ESCALATION_RULES)

support_agent = Agent(
    settings.agent_model,
    output_type=AgentReply,
    instructions=INSTRUCTIONS,
    retries=3,
    model_settings={"temperature": 0},
)


@support_agent.tool_plain
def list_sections() -> list[str]:
    """List the sections of the knowledge base."""
    logger.info("Tool call: list_sections()")
    return db.list_sections()


@support_agent.tool_plain
def get_section(section: str) -> str:
    """Return every entry of one knowledge base section, for example 'supplements-label-details'."""
    logger.info("Tool call: get_section(%r)", section)
    entries = db.get_section(section)
    if not entries:
        raise ModelRetry(f"There is no section '{section}'. Call list_sections to see the options.")
    return "\n\n".join(f"## {entry['title']}\n{entry['content']}" for entry in entries)


def sections_read(ctx: RunContext[None]) -> set[str]:
    """The sections the agent fetched with get_section during this run."""
    read = set()
    for message in ctx.messages:
        if isinstance(message, ModelResponse):
            for part in message.parts:
                if isinstance(part, ToolCallPart) and part.tool_name == "get_section":
                    read.add(str(part.args_as_dict().get("section", "")))
    return read


def section_text(ctx: RunContext[None], section: str) -> str:
    """The text get_section returned for one section during this run."""
    names = {}
    for message in ctx.messages:
        if isinstance(message, ModelResponse):
            for part in message.parts:
                if isinstance(part, ToolCallPart) and part.tool_name == "get_section":
                    names[part.tool_call_id] = part.args_as_dict().get("section")
    texts = []
    for message in ctx.messages:
        if isinstance(message, ModelRequest):
            for part in message.parts:
                if isinstance(part, ToolReturnPart) and names.get(part.tool_call_id) == section:
                    texts.append(str(part.content))
    return "\n".join(texts)


def normalise(text: str) -> str:
    return " ".join(text.lower().replace("- ", " ").split())


@support_agent.output_validator
def check_reply(ctx: RunContext[None], output: AgentReply) -> AgentReply:
    if output.action != "reply":
        # Check the quote, so the agent escalates only for a rule that really exists.
        quote = normalise(output.escalation_rule_quote)
        if not quote or quote not in normalise(section_text(ctx, "escalation-rules")):
            raise ModelRetry(
                "Copy the escalation rule that matches, word for word from the escalation-rules "
                'section, into escalation_rule_quote. If no rule matches, set escalation to "none".'
            )
        return output
    if not (sections_read(ctx) - ALWAYS_READ):
        # Without this the model answers from general knowledge instead of our policies.
        raise ModelRetry(
            "You have not read the section that answers the question. Call get_section for it, "
            "then answer only with facts from it."
        )
    reply = output.reply
    if not reply.strip():
        raise ModelRetry("The reply is empty. Write the email.")
    if re.search(r"\b(AI|artificial intelligence|knowledge base|bot)\b", reply, re.IGNORECASE):
        raise ModelRetry("Do not mention AI, a bot, or the knowledge base in the reply.")
    if re.search(r"₦|\bNGN\b|\bnaira\b|\bN\d", reply, re.IGNORECASE):
        raise ModelRetry("Never quote a price. Say that a colleague will confirm the current price.")
    if "!" in reply:
        raise ModelRetry("Do not use exclamation marks.")
    if SIGN_OFF not in reply:
        raise ModelRetry(f'End the reply with "Kind regards," and "{SIGN_OFF}".')
    if len(reply.split()) > MAX_WORDS:
        raise ModelRetry("The reply is too long. Keep it under 150 words.")
    return output


async def write_reply(thread: str, section: str) -> AgentReply:
    prompt = f"Section picked by the classifier: {section}\n\n{thread}"
    result = await support_agent.run(prompt)
    return result.output
