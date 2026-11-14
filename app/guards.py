import re
from email.utils import parseaddr

# Senders that are machines, not customers. Answering them wastes a reply at best, and at
# worst starts a loop with another auto-responder.
AUTOMATED_SENDER = re.compile(
    r"^(no-?reply|do-?not-?reply|notifications?|notify|alerts?|mailer-daemon|postmaster|bounces?)\b"
    r"|[-_.](no-?reply|do-?not-?reply)\b",
    re.IGNORECASE,
)

# Gmail sorts newsletters, receipts, and account notices into these tabs. Customers write
# to us from a person's mailbox, which lands in Primary (CATEGORY_PERSONAL).
AUTOMATED_CATEGORIES = {"CATEGORY_UPDATES", "CATEGORY_PROMOTIONS", "CATEGORY_SOCIAL", "CATEGORY_FORUMS"}


def skip_reason(message: dict, headers: dict[str, str], own_address: str) -> str | None:
    """Return why the bot must not answer this message, or None when it may."""
    labels = set(message.get("labelIds", []))
    sender = parseaddr(headers.get("from", ""))[1].lower()
    if "SENT" in labels:
        return "sent by us"
    if sender == own_address.lower():
        return "from our own address"
    auto_submitted = headers.get("auto-submitted", "no").strip().lower()
    if auto_submitted != "no":
        return f"auto-submitted: {auto_submitted}"
    if headers.get("precedence", "").strip().lower() in {"bulk", "list", "junk"}:
        return "bulk or list mail"
    if AUTOMATED_SENDER.search(sender.partition("@")[0]):
        return f"automated sender: {sender}"
    if "list-unsubscribe" in headers or "list-id" in headers:
        return "mailing list or newsletter"
    if "x-autoreply" in headers or "x-autorespond" in headers:
        return "auto-reply"
    category = labels & AUTOMATED_CATEGORIES
    if category:
        return f"gmail category: {category.pop().removeprefix('CATEGORY_').lower()}"
    return None
