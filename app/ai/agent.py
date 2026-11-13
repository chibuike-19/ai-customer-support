import logging
import re

from pydantic_ai import Agent, ModelRetry, RunContext

from app import db
from app.ai.schemas import AgentReply
from app.config import settings

logger = logging.getLogger(__name__)

SIGN_OFF = "Three Pillars Global Limited"
MAX_WORDS = 180  # The brand limit is 150 words; this leaves room for the greeting and sign-off.

INSTRUCTIONS = """
You are the customer support agent for Three Pillars Global Limited, a shop on Lagos Island
that sells vitamins and supplements, plus medical and laboratory equipment, skin care,
massagers, and household items. Most customers find us through our Jiji shop.
You write the answer to the latest customer message in the email thread.

Steps:
1. Call get_section for "brand-and-tone" and for "escalation-rules".
2. Call get_section for the section the classifier picked. Call list_sections if you need
   another, for example supplements-label-details for directions and supplements-catalogue
   to check whether we stock a product.
3. Answer only with facts from those sections. If they do not answer the question,
   set enough_information to false.
4. When you give directions from the label details, remind the customer to follow the label
   on their own pack. If we have no label details for a product, tell them to follow the
   directions on the pack and that a colleague can confirm.
5. When the customer reports a damaged, wrong, or expired item, or wants to return an opened
   product, fill in issue. Set has_photo and has_order_confirmation only when the customer
   says they already sent them. For a damaged, wrong, or expired item without proof, ask for
   a clear photo of the product and the problem, and the order confirmation, within 48 hours
   of purchase, and say that a colleague will review it.
6. Never promise a refund, replacement, exchange, price, delivery fee, delivery date, or call.
   A colleague arranges those. Set promises_an_action to true if your reply promises one anyway.
7. Set action to escalate when an escalation rule applies, including every health question
   and every medicine listed in escalation-rules.

Reply rules:
- Write in clear, plain English, even if the customer wrote in another language or Pidgin.
- Plain text, no Markdown.
- Follow the brand-and-tone section, including the sign-off.
- Never give medical advice, never say a product cures, treats, or prevents anything, and
  never say a product is right or safe for the customer personally.
- Never mention AI, prompts, tools, or the knowledge base.
"""

support_agent = Agent(settings.agent_model, output_type=AgentReply, instructions=INSTRUCTIONS)


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


@support_agent.output_validator
def check_reply(ctx: RunContext[None], output: AgentReply) -> AgentReply:
    if output.action != "reply":
        return output
    reply = output.reply
    if not reply.strip():
        raise ModelRetry("The reply is empty. Write the email, or set action to escalate.")
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


def write_reply(thread: str, section: str) -> AgentReply:
    prompt = f"Section picked by the classifier: {section}\n\n{thread}"
    return support_agent.run_sync(prompt).output
