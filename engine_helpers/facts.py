
from engine_helpers.db_utils import get_db
from datetime import datetime

def _deposit_fact_rows(swap_id):
    fact_conn = get_db()
    fact_cursor = fact_conn.cursor()
    fact_cursor.execute(
        """
        SELECT confirmations
        FROM facts
        WHERE swap_id = ?
          AND fact_type = 'deposit'
        """,
        (swap_id,),
    )
    rows = fact_cursor.fetchall()
    fact_conn.close()
    return rows


def _fact_type_exists(swap_id, fact_type):
    fact_conn = get_db()
    fact_cursor = fact_conn.cursor()
    fact_cursor.execute(
        """
        SELECT 1
        FROM facts
        WHERE swap_id = ?
          AND fact_type = ?
        LIMIT 1
        """,
        (swap_id, fact_type),
    )
    row = fact_cursor.fetchone()
    fact_conn.close()
    return row is not None

def _max_confirmations_for_fact(swap_id, fact_type):
    fact_conn = get_db()
    fact_cursor = fact_conn.cursor()
    fact_cursor.execute(
        """
        SELECT confirmations
        FROM facts
        WHERE swap_id = ?
          AND fact_type = ?
        ORDER BY confirmations DESC
        LIMIT 1
        """,
        (swap_id, fact_type),
    )
    row = fact_cursor.fetchone()
    fact_conn.close()
    return row["confirmations"] if row else None


def _insert_fact(swap_id, fact_type, source):
    fact_conn = get_db()
    fact_cursor = fact_conn.cursor()
    fact_cursor.execute(
        """
        INSERT INTO facts (
            swap_id,
            fact_type,
            source,
            confirmations,
            observed_at,
            last_updated
        ) VALUES (
            ?, ?, ?, 1, datetime('now'), datetime('now')
        )
        """,
        (swap_id, fact_type, source),
    )
    fact_conn.commit()
    fact_conn.close()
    
    
def _exists_fact(swap_id, fact_type):
    return _count_facts(swap_id, fact_type) > 0

def _count_facts(swap_id, fact_type):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM facts WHERE swap_id = ? AND fact_type = ?",
        (swap_id, fact_type)
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count


def _count_facts_of_type(swap_id, fact_type):
    fact_conn = get_db()
    fact_cursor = fact_conn.cursor()
    fact_cursor.execute(
        """
        SELECT COUNT(*) AS attempt_count
        FROM facts
        WHERE swap_id = ?
          AND fact_type = ?
        """,
        (swap_id, fact_type),
    )
    row = fact_cursor.fetchone()
    fact_conn.close()
    return row["attempt_count"] if row else 0



# 8.6 additions for fact table
def get_facts_for_swap(swap_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM facts
        WHERE swap_id = ?
    """, (swap_id,))

    rows = cursor.fetchall()
    conn.close()
    return rows

def get_fact(swap_id, fact_type, source):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM facts
        WHERE swap_id = ?
          AND fact_type = ?
          AND source = ?
    """, (swap_id, fact_type, source))

    row = cursor.fetchone()
    conn.close()
    return row



def upsert_fact(swap_id, fact_type, source, confirmations, observed_at):
    now = datetime.utcnow().isoformat()

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO facts (
            swap_id,
            fact_type,
            source,
            confirmations,
            observed_at,
            last_updated
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(swap_id, fact_type, source)
        DO UPDATE SET
            confirmations = max(confirmations, excluded.confirmations),
            last_updated = excluded.last_updated
    """, (
        swap_id,
        fact_type,
        source,
        confirmations,
        observed_at,
        now
    ))

    conn.commit()
    conn.close()
# 8.6 additions #################################