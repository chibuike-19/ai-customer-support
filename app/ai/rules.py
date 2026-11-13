from app.ai.schemas import Issue

# Steps where the reply goes to the customer, because they have to send something first.
CUSTOMER_STEPS = {"ask-proof"}

COMPLAINT_WINDOW_DAYS = 2  # 48 hours


def resolve_issue(issue: Issue) -> str:
    """Decide the next step for a reported problem. The model reports, Python decides.

    Follows the returns-and-complaints section: complaints need a photo and the order
    confirmation within 48 hours of purchase, and a colleague decides every outcome.
    """
    if issue.problem in {"damaged", "wrong-item", "expired"}:
        if issue.days_since_purchase is not None and issue.days_since_purchase > COMPLAINT_WINDOW_DAYS:
            # Never refuse a late complaint ourselves. A colleague reads it and replies.
            return "review-late-complaint"
        if not (issue.has_photo and issue.has_order_confirmation):
            return "ask-proof"
        return "review-complaint"
    if issue.problem == "opened-return":
        # Opened products cannot be returned, but a colleague tells the customer.
        return "review-opened-return"
    # Anything unexpected goes to a person.
    return "escalate"
