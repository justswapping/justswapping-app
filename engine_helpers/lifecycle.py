from engine_helpers.db_utils import _swap_rows

from engine_helpers.facts import (
    _exists_fact,
    _fact_type_exists,
    _max_confirmations_for_fact,
)

from engine_helpers.constants import (
    FACT_EXECUTION_STARTED,
    FACT_EXECUTION_FAILED,
    FACT_PAYOUT_CONFIRMED,
    REQUIRED_PAYOUT_CONFIRMATIONS,
)

from engine_helpers.constants import FACT_SWAPPING, SWAPPING_TIMEOUT_SECONDS


def tick_phase_8_7a_deposit_to_swapping(cursor, change_swap_status):
    """
    Phase 3 – Rule #2:
    If FACT_SWAPPING exists for a swap in deposit_received, mark it as swapping.

    - Fact-driven
    - Idempotent
    - Goes through change_swap_status to enforce transition guard
    """

    cursor.execute("""
        SELECT s.id
        FROM swaps s
        WHERE s.status NOT IN ('swapping', 'completed', 'failed')
          AND EXISTS (
              SELECT 1 FROM facts f
              WHERE f.swap_id = s.id
                AND f.fact_type = ?
          )
    """, (FACT_SWAPPING,))

    rows = cursor.fetchall()

    for row in rows:
        swap_id = row["id"]
        print(f"→ advancing swap {swap_id} to swapping (fact-driven)")
        # ✅ FIX: use change_swap_status instead of raw UPDATE
        # so the transition guard is enforced
        change_swap_status(swap_id, "swapping")




def tick_phase_8_7b_swapping_to_completed(cursor, change_swap_status):
    
    cursor.execute("""
        SELECT s.id, s.from_coin, s.to_coin, s.amount, s.withdrawal_amount,
               s.deposit_address, s.receive_address, s.provider, s.email,
               s.from_coin_gbp_rate, s.to_coin_gbp_rate,
               s.from_coin_usd_rate, s.to_coin_usd_rate
        FROM swaps s
        WHERE s.status = 'swapping'
          AND EXISTS (
              SELECT 1
              FROM facts f
              WHERE f.swap_id = s.id
                AND f.fact_type = 'payout_confirmed'
          )
    """)

    rows = cursor.fetchall()

    for row in rows:
        swap_id = row["id"]
        print(f"→ advancing swap {swap_id} to completed (payout confirmed)")
        change_swap_status(swap_id, "completed")

        # Send completion receipt if email provided
        if row["email"]:
            from engine_helpers.email_receipt import send_completion_receipt
            send_completion_receipt(
                swap_id=swap_id,
                from_coin=row["from_coin"],
                to_coin=row["to_coin"],
                amount=row["amount"],
                withdrawal_amount=row["withdrawal_amount"],
                receive_address=row["receive_address"],
                provider=row["provider"],
                user_email=row["email"],
                from_coin_gbp_rate=row["from_coin_gbp_rate"],
                to_coin_gbp_rate=row["to_coin_gbp_rate"],
                from_coin_usd_rate=row["from_coin_usd_rate"],
                to_coin_usd_rate=row["to_coin_usd_rate"],
            )

        
def tick_phase_8_7c_swapping_to_failed(cursor, change_swap_status):
    cursor.execute("""
        SELECT s.id, s.from_coin, s.to_coin, s.amount,
               s.receive_address, s.provider, s.email,
               s.from_coin_gbp_rate, s.from_coin_usd_rate
        FROM swaps s
        WHERE s.status = 'swapping'
          AND NOT EXISTS (
              SELECT 1 FROM facts f
              WHERE f.swap_id = s.id
                AND f.fact_type = ?
          )
          AND EXISTS (
              SELECT 1 FROM facts f2
              WHERE f2.swap_id = s.id
                AND f2.fact_type = 'swapping'
                AND f2.observed_at < datetime('now', '-' || ? || ' seconds')
          )
    """, (FACT_PAYOUT_CONFIRMED, SWAPPING_TIMEOUT_SECONDS))

    rows = cursor.fetchall()

    for row in rows:
        swap_id = row["id"]
        print(f"→ swap {swap_id} timed out in swapping state — marking failed")
        change_swap_status(swap_id, "failed")

        if row["email"]:
            from engine_helpers.email_receipt import send_failed_receipt
            send_failed_receipt(
                swap_id=swap_id,
                from_coin=row["from_coin"],
                to_coin=row["to_coin"],
                amount=row["amount"],
                receive_address=row["receive_address"],
                provider=row["provider"],
                user_email=row["email"],
                from_coin_gbp_rate=row["from_coin_gbp_rate"],
                from_coin_usd_rate=row["from_coin_usd_rate"],
            )


def tick_phase_provider_failed(cursor, change_swap_status):
    """
    If a provider_failed fact exists for a swap that isn't already
    completed or failed, mark it as failed immediately.
    """
    cursor.execute("""
        SELECT s.id, s.from_coin, s.to_coin, s.amount,
               s.receive_address, s.provider, s.email,
               s.from_coin_gbp_rate, s.from_coin_usd_rate
        FROM swaps s
        WHERE s.status NOT IN ('completed', 'failed')
          AND EXISTS (
              SELECT 1 FROM facts f
              WHERE f.swap_id = s.id
                AND f.fact_type = 'provider_failed'
          )
    """)

    rows = cursor.fetchall()

    for row in rows:
        swap_id = row["id"]
        print(f"→ swap {swap_id} failed by provider — marking failed immediately")
        change_swap_status(swap_id, "failed")

        if row["email"]:
            from engine_helpers.email_receipt import send_failed_receipt
            send_failed_receipt(
                swap_id=swap_id,
                from_coin=row["from_coin"],
                to_coin=row["to_coin"],
                amount=row["amount"],
                receive_address=row["receive_address"],
                provider=row["provider"],
                user_email=row["email"],
                from_coin_gbp_rate=row["from_coin_gbp_rate"],
                from_coin_usd_rate=row["from_coin_usd_rate"],
            )