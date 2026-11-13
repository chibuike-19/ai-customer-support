import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.config import settings


def connect() -> psycopg.Connection:
    return psycopg.connect(settings.database_url, autocommit=True, row_factory=dict_row)


def start_event(gmail_message_id: str) -> dict | None:
    """Claim a message. Returns None when it is already handled or in progress."""
    with connect() as conn:
        return conn.execute(
            """
            insert into events (gmail_message_id) values (%s)
            on conflict (gmail_message_id) do update
              set attempts = events.attempts + 1, status = 'processing', error = null
              where events.status = 'failed'
            returning id, attempts
            """,
            (gmail_message_id,),
        ).fetchone()


def finish_event(event_id: int, status: str, result: dict) -> None:
    with connect() as conn:
        conn.execute(
            "update events set status = %s, result = %s, processed_at = now() where id = %s",
            (status, Jsonb(result), event_id),
        )


def fail_event(event_id: int, error: str) -> None:
    with connect() as conn:
        conn.execute(
            "update events set status = 'failed', error = %s where id = %s",
            (error, event_id),
        )


def upsert_ticket(gmail_thread_id: str, customer_email: str, subject: str) -> int:
    with connect() as conn:
        row = conn.execute(
            """
            insert into tickets (gmail_thread_id, customer_email, subject)
            values (%s, %s, %s)
            on conflict (gmail_thread_id) do update set updated_at = now()
            returning id
            """,
            (gmail_thread_id, customer_email, subject),
        ).fetchone()
        return row["id"]


def update_ticket(
    ticket_id: int, status: str, category: str | None = None, proposed_action: str | None = None
) -> None:
    with connect() as conn:
        conn.execute(
            """
            update tickets
            set status = %s, category = coalesce(%s, category),
                proposed_action = %s, updated_at = now()
            where id = %s
            """,
            (status, category, proposed_action, ticket_id),
        )


def save_message(
    ticket_id: int, gmail_message_id: str, direction: str, from_address: str, body: str
) -> None:
    with connect() as conn:
        conn.execute(
            """
            insert into messages (ticket_id, gmail_message_id, direction, from_address, body)
            values (%s, %s, %s, %s, %s)
            on conflict (gmail_message_id) do nothing
            """,
            (ticket_id, gmail_message_id, direction, from_address, body),
        )

def list_sections() -> list[str]:
    with connect() as conn:
        rows = conn.execute("select distinct section from knowledge_base order by section").fetchall()
        return [row["section"] for row in rows]


def get_section(section: str) -> list[dict]:
    with connect() as conn:
        return conn.execute(
            "select title, content from knowledge_base where section = %s order by id",
            (section,),
        ).fetchall()

# Dashboard queries


def list_events(status: str | None = None, limit: int = 100) -> list[dict]:
    with connect() as conn:
        return conn.execute(
            """
            select id, gmail_message_id, status, attempts, error, result, created_at, processed_at
            from events
            where %(status)s::text is null or status = %(status)s
            order by created_at desc
            limit %(limit)s
            """,
            {"status": status, "limit": limit},
        ).fetchall()


def list_tickets(status: str | None = None, limit: int = 100) -> list[dict]:
    with connect() as conn:
        return conn.execute(
            """
            select t.id, t.customer_email, t.subject, t.category, t.status, t.proposed_action,
                   t.created_at, t.updated_at, count(m.id)::int as message_count
            from tickets t
            left join messages m on m.ticket_id = t.id
            where %(status)s::text is null or t.status = %(status)s
            group by t.id
            order by t.updated_at desc
            limit %(limit)s
            """,
            {"status": status, "limit": limit},
        ).fetchall()


def get_ticket(ticket_id: int) -> dict | None:
    with connect() as conn:
        ticket = conn.execute(
            """
            select id, gmail_thread_id, customer_email, subject, category, status,
                   proposed_action, created_at, updated_at
            from tickets where id = %s
            """,
            (ticket_id,),
        ).fetchone()
        if ticket is None:
            return None
        ticket["messages"] = conn.execute(
            """
            select id, direction, from_address, body, created_at
            from messages where ticket_id = %s order by created_at
            """,
            (ticket_id,),
        ).fetchall()
        return ticket


def summary() -> dict:
    with connect() as conn:
        tickets = conn.execute("select status, count(*)::int as n from tickets group by status")
        events = conn.execute("select status, count(*)::int as n from events group by status")
        return {
            "tickets": {row["status"]: row["n"] for row in tickets.fetchall()},
            "events": {row["status"]: row["n"] for row in events.fetchall()},
        }


def list_knowledge_base() -> list[dict]:
    with connect() as conn:
        return conn.execute(
            "select id, section, title, content, updated_at from knowledge_base order by section, id"
        ).fetchall()


def update_knowledge_base(entry_id: int, content: str) -> dict | None:
    with connect() as conn:
        return conn.execute(
            """
            update knowledge_base set content = %s, updated_at = now() where id = %s
            returning id, section, title, content, updated_at
            """,
            (content, entry_id),
        ).fetchone()
