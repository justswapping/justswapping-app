from engine_helpers.db_utils import _swap_rows

from engine_helpers.facts import (
    _fact_type_exists,
    _insert_fact,
    _count_facts_of_type,
)

from engine_helpers.constants import (
    FACT_EXECUTION_REQUESTED,
    FACT_EXECUTION_FAILED,
    FACT_EXECUTION_TIMED_OUT,
    FACT_REFUND_REQUESTED,
    MAX_EXECUTION_ATTEMPTS,
)

from engine_helpers.constants import FACT_SWAPPING


def tick_phase_8_9c_timeout(cursor):
    swapping_swaps = _swap_rows(cursor, "swapping")

    for swap in swapping_swaps:
        swap_id = swap["id"]
        if _fact_type_exists(swap_id, FACT_EXECUTION_TIMED_OUT):
            print(f"?? execution timed out for swap {swap_id}")

    for swap in swapping_swaps:
        swap_id = swap["id"]
        if not _fact_type_exists(swap_id, FACT_EXECUTION_TIMED_OUT):
            continue
        if _fact_type_exists(swap_id, FACT_EXECUTION_FAILED):
            continue
        print(f"? marking execution failed due to timeout for swap {swap_id}")
        _insert_fact(swap_id, FACT_EXECUTION_FAILED, "engine_timeout")


def tick_phase_8_9a_retry(cursor):
    failed_swaps = _swap_rows(cursor, "failed")

    # ✅ Single pass — check count, log, and insert in one loop
    # so the logged attempt number always matches what is being inserted
    for swap in failed_swaps:
        swap_id = swap["id"]
        attempt_count = _count_facts_of_type(swap_id, FACT_EXECUTION_REQUESTED)

        if attempt_count >= MAX_EXECUTION_ATTEMPTS:
            print(
                f"? swap {swap_id} retry limit reached "
                f"({attempt_count}/{MAX_EXECUTION_ATTEMPTS})"
            )
            continue

        next_attempt = attempt_count + 1
        source = f"engine_attempt_{next_attempt}"

        print(
            f"?? retrying execution for swap {swap_id} "
            f"(attempt {next_attempt}/{MAX_EXECUTION_ATTEMPTS})"
        )
        _insert_fact(swap_id, FACT_EXECUTION_REQUESTED, source)


def tick_phase_8_9b_refund(cursor):
    failed_swaps = _swap_rows(cursor, "failed")

    # First pass: log eligibility
    for swap in failed_swaps:
        swap_id = swap["id"]
        attempt_count = _count_facts_of_type(
            swap_id, FACT_EXECUTION_REQUESTED
        )
        refund_exists = _fact_type_exists(
            swap_id, FACT_REFUND_REQUESTED
        )

        if attempt_count >= MAX_EXECUTION_ATTEMPTS and not refund_exists:
            print(
                f"?? swap {swap_id} eligible for refund "
                f"(attempts exhausted: {attempt_count}/{MAX_EXECUTION_ATTEMPTS})"
            )
        elif refund_exists:
            print(f"? swap {swap_id} refund already requested")

    # Second pass: request refund
    for swap in failed_swaps:
        swap_id = swap["id"]
        attempt_count = _count_facts_of_type(
            swap_id, FACT_EXECUTION_REQUESTED
        )
        refund_exists = _fact_type_exists(
            swap_id, FACT_REFUND_REQUESTED
        )

        if attempt_count >= MAX_EXECUTION_ATTEMPTS and not refund_exists:
            print(f"?? requesting refund for swap {swap_id}")
            _insert_fact(
                swap_id, FACT_REFUND_REQUESTED, "engine"
            )
