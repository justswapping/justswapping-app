
from engine_helpers.constants import FACT_EXECUTION_REQUESTED
from engine_helpers.constants import FACT_SWAPPING

from engine_helpers.facts import (
    _fact_type_exists,
    _insert_fact,
)

from engine_helpers.db_utils import _swap_rows

# def tick_phase_8_8_execution_intent(cursor):
#     for swap in _swap_rows(cursor, "deposit_received"):
#         swap_id = swap["id"]
#         if _fact_type_exists(swap_id, FACT_EXECUTION_REQUESTED):
#             continue
#         print(f"?? requesting execution for swap {swap_id}")
#         _insert_fact(swap_id, FACT_EXECUTION_REQUESTED, "engine")


def tick_phase_8_8_execution_intent(cursor):
    for swap in _swap_rows(cursor, "deposit_received"):
        swap_id = swap["id"]

        # Do not duplicate execution intent
        if _fact_type_exists(swap_id, FACT_EXECUTION_REQUESTED):
            continue

        print(f"?? requesting execution for swap {swap_id}")

        # NEW: clear prior execution state so retries start clean
        cursor.execute(
            "DELETE FROM facts WHERE swap_id = ? AND fact_type = ?",
            (swap_id, FACT_SWAPPING)
        )

        _insert_fact(
            swap_id,
            FACT_EXECUTION_REQUESTED,
            "engine"
        )

