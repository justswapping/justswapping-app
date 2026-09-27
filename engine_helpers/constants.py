
REQUIRED_DEPOSIT_CONFIRMATIONS = 1

# --- Phase 8.7 fact types ---
FACT_EXECUTION_STARTED = "execution_started"
FACT_PAYOUT_CONFIRMED = "payout_confirmed"

REQUIRED_EXECUTION_CONFIRMATIONS = 1
REQUIRED_PAYOUT_CONFIRMATIONS = 1
# --- Phase 8.7 fact failure ---
FACT_EXECUTION_FAILED = "execution_failed"
# --- Phase 8.9a retry policy ---
MAX_EXECUTION_ATTEMPTS = 3
REQUIRED_FAILURE_CONFIRMATIONS = 1
# --- Phase 8.8 fact failure ---
FACT_EXECUTION_REQUESTED = "execution_requested"
# --- Phase 8.9b refund facts ---
FACT_REFUND_REQUESTED = "refund_requested"
FACT_REFUND_BROADCAST = "refund_broadcast"
FACT_REFUND_CONFIRMED = "refund_confirmed"
# --- Phase 8.9c timeout facts ---
FACT_EXECUTION_TIMED_OUT = "execution_timed_out"
# phase 2 17-04-26 addition
FACT_SWAPPING = "swapping"
# Phase 3 – swapping timeout (seconds)
SWAPPING_TIMEOUT_SECONDS = 1800  # 10 minutes (adjust for testing)
# near final stage 01-05-26
ENABLE_ENGINE_POLLING = True     # ← set to True to enable polling
ENGINE_POLL_INTERVAL = 15   


