
from engine_helpers.db_utils import _swap_rows
from engine_helpers.facts import  _deposit_fact_rows
from engine_helpers.constants import REQUIRED_DEPOSIT_CONFIRMATIONS




def tick_phase_8_6_awaiting_deposit(cursor, change_swap_status):
    for swap in _swap_rows(cursor, "awaiting_deposit"):
        swap_id = swap["id"]
        deposit_facts = _deposit_fact_rows(swap_id)
        if not deposit_facts:
            continue
        # print("[DEBUG] deposit facts seen by engine:", deposit_facts)
        best = max(f["confirmations"] for f in deposit_facts)
        if best >= REQUIRED_DEPOSIT_CONFIRMATIONS:
            print(f"? advancing swap {swap_id} to deposit_received")
            change_swap_status(swap_id, "deposit_received")

