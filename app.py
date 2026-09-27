from dotenv import load_dotenv
load_dotenv()


from flask import Flask, request, jsonify, render_template


import os


from engine_helpers.deposits import tick_phase_8_6_awaiting_deposit
from engine_helpers.execution_intent import tick_phase_8_8_execution_intent
from engine_helpers.lifecycle import (
    tick_phase_8_7a_deposit_to_swapping,
    tick_phase_8_7b_swapping_to_completed,
    tick_phase_8_7c_swapping_to_failed,
    tick_phase_provider_failed,
)

from engine_helpers.resolution import (
    tick_phase_8_9c_timeout,
    tick_phase_8_9a_retry,
    tick_phase_8_9b_refund,
)

from engine_helpers.email_receipt import send_swap_receipt

from engine_helpers.facts import get_fact
from engine_helpers.facts import _count_facts, upsert_fact

from engine_helpers.facts import _exists_fact, _insert_fact
# from engine_helpers.constants import FACT_EXECUTION_STARTED

from datetime import datetime

from engine_helpers.constants import (
    FACT_EXECUTION_STARTED,
    FACT_SWAPPING,
    FACT_PAYOUT_CONFIRMED,
    ENABLE_ENGINE_POLLING,
    ENGINE_POLL_INTERVAL   
)

# 27-09-26 dev_mode changes
from functools import wraps
# 27-09-26 for tokens so that users can only check their own swap
import secrets

import json

# from providers.registry import ProviderRegistry
# from providers.mock import MockProvider

# from providers.changenow import ChangeNOWProvider

from providers.registry import ProviderRegistry
from providers.mock import MockProvider
from providers.changenow import ChangeNOWProvider
from providers.godex import GodexProvider



# 1️⃣ CREATE the registry
provider_registry = ProviderRegistry()

# set a variable as a switch for testing tools 
DEV_MODE = os.environ.get("JUSTSWAPPING_DEV", "").strip() == "1"

# 2️⃣ REGISTER providers
if DEV_MODE:
    provider_registry.register(MockProvider())

# print("All env vars with GODEX:", {k: v for k, v in os.environ.items() if "GODEX" in k})
# print("All env vars with API:", {k: v for k, v in os.environ.items() if "API" in k})

# import of os needed for this, done above
api_key = os.environ.get("CHANGENOW_API_KEY")
if api_key:
    provider_registry.register(ChangeNOWProvider(api_key=api_key))
    print("✅ ChangeNOW provider registered")
else:
    print("⚠️  CHANGENOW_API_KEY not set — ChangeNOW provider not registered")
    
godex_api_key = os.environ.get("GODEX_API_KEY")
if godex_api_key:
    godex_affiliate_id = os.environ.get("GODEX_AFFILIATE_ID", "")
    provider_registry.register(GodexProvider(api_key=godex_api_key, affiliate_id=godex_affiliate_id))
    print("✅ Godex provider registered")
else:
    print("⚠️  GODEX_API_KEY not set — Godex provider not registered")

# provider_registry.register(
#     ChangeNOWProvider(api_key=api_key)
# )


# debug line
print("Registered providers:", provider_registry._providers.keys())


# 8.5 Polling addition basic
import threading
import time


# print(' running in: ', os.getcwd())
# _ROOT = os.path.dirname(os.path.abspath(__file__))
# DB_PATH = os.path.join(_ROOT, "swaps.db")

_ROOT = os.path.dirname(os.path.abspath(__file__))



app = Flask(
    __name__,
    template_folder=os.path.join(_ROOT, "templates"),
    static_folder=os.path.join(_ROOT, "static"),
)

app.config["DEV_MODE"] = DEV_MODE

print("🚀 RUNNING FILE:", os.path.abspath(__file__))

def dev_only(view):
    """Hide development/admin routes on a live server (returns 404)."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not DEV_MODE:
            return jsonify({"error": "Not found"}), 404
        return view(*args, **kwargs)
    return wrapper

def _token_matches(swap_id):
    """Check the ?token= in the web address against the swap's stored token."""
    supplied = request.args.get("token", "")
    if not supplied:
        return False
    conn = get_db()
    row = conn.execute("SELECT access_token FROM swaps WHERE id = ?", (swap_id,)).fetchone()
    conn.close()
    if row is None or not row[0]:
        return False
    return secrets.compare_digest(str(row[0]), supplied)

# # Available swap providers
# ROUTES = [
#     {"name": "FastSwap", "fee": 0.015},
#     {"name": "BestRate", "fee": 0.008},
#     {"name": "Balanced", "fee": 0.010}
# ]

# 7.6 updating statuses
ALLOWED_STATUSES = [
    "created",
    "awaiting_deposit",
    "deposit_received",
    "swapping",
    "completed",
    "failed"
]

# ALLOWED_TRANSITIONS = {
#     "created": ["awaiting_deposit"],
#     "awaiting_deposit": ["deposit_received"],
#     "deposit_received": ["swapping"],
#     "swapping": ["completed", "failed"],
#     "completed": [],
#     "failed": []
# }

ALLOWED_TRANSITIONS = {
    "created":           ["awaiting_deposit", "failed"],
    "awaiting_deposit":  ["deposit_received", "failed"],
    "deposit_received":  ["swapping", "failed"],
    "swapping":          ["completed", "failed"],
    "completed":         [],
    "failed":            []
}

# Map CoinGecko IDs → ChangeNOW ticker symbols
# Frontend may send either form; backend normalises to ticker before passing to provider
COINGECKO_TO_TICKER = {
    "litecoin":     "ltc",
    "bitcoin":      "btc",
    "ethereum":     "eth",
    "monero":       "xmr",
    "bitcoin-cash": "bch",
    "dogecoin":     "doge",
    "cardano":      "ada",
    "solana":       "sol",
    "tron":         "trx",
}

def normalise_coin(coin_id: str) -> str:
    """Return the provider ticker for a given coin identifier.
    Accepts both CoinGecko IDs and tickers (idempotent)."""
    return COINGECKO_TO_TICKER.get(coin_id.lower(), coin_id.lower())



from engine_helpers.db_utils import get_db

def init_db():
    conn = get_db()
    cursor = conn.cursor()    

# commented out for gbp data inclusion 01-05-26

    # cursor.execute("""
    #     CREATE TABLE IF NOT EXISTS swaps (
    #         id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         from_coin TEXT,
    #         to_coin TEXT,
    #         amount REAL,
    #         receive_address TEXT,
    #         deposit_address TEXT,
    #         status TEXT,
    #         email TEXT,
    #         provider TEXT,
    #         provider_execution_id TEXT,
    #         rate REAL,
    #         withdrawal_amount REAL,
    #         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    #     )
    # """)
 # 02-05-26 including refund address field   
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS swaps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_coin TEXT,
        to_coin TEXT,
        amount REAL,
        receive_address TEXT,
        refund_address TEXT,
        deposit_address TEXT,
        status TEXT,
        email TEXT,
        provider TEXT,
        provider_execution_id TEXT,
        rate REAL,
        withdrawal_amount REAL,
        from_coin_gbp_rate REAL,
        to_coin_gbp_rate REAL,
        from_coin_usd_rate REAL,
        to_coin_usd_rate REAL,
        commission_gbp REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Access token column: lets only the person who created a swap look it up.
    existing_cols = [c[1] for c in cursor.execute("PRAGMA table_info(swaps)").fetchall()]
    if "access_token" not in existing_cols:
        cursor.execute("ALTER TABLE swaps ADD COLUMN access_token TEXT")

    # ✅ 7.8 NEW: status history table

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS swap_status_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            swap_id INTEGER,
            old_status TEXT,
            new_status TEXT,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (swap_id) REFERENCES swaps(id)
        )
    """)
    
    
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            swap_id INTEGER NOT NULL,
            fact_type TEXT NOT NULL,
            source TEXT NOT NULL,
            confirmations INTEGER NOT NULL,
            observed_at TEXT NOT NULL,
            last_updated TEXT NOT NULL,
            UNIQUE (swap_id, fact_type, source)
        );
    """)
    
    conn.commit()
    conn.close()


def change_swap_status(swap_id, new_status):
    conn = get_db()
    cursor = conn.cursor()
    
    # breakpoint()

    # 1. Fetch current status

    cursor.execute(
        "SELECT status FROM swaps WHERE id = ?",
        (swap_id,)
    )
    row = cursor.fetchone()

    if row is None:
        conn.close()
        return False, {"error": "Swap not found"}

    old_status = row["status"]

    # 2. Enforce lifecycle transition
    if new_status not in ALLOWED_TRANSITIONS[old_status]:
        conn.close()
        return False, {
            "error": "Invalid status transition",
            "from": old_status,
            "allowed_to": ALLOWED_TRANSITIONS[old_status]
        }

    # 3. Update DB
    cursor.execute(
        "UPDATE swaps SET status = ? WHERE id = ?",
        (new_status, swap_id)
    )

    conn.commit()
    conn.close()

    # 4. Emit event + history
    notify_swap_status_change(swap_id, old_status, new_status)

    # 5. Report success
    return True, new_status

    
# # engine_tick is a multi-pass reconciliation loop.
# # Phase order reflects data dependency, not lifecycle sequencing.
# def engine_tick():
#     print("? engine_tick called")

#     conn = get_db()
#     cursor = conn.cursor()

#     tick_phase_8_6_awaiting_deposit(cursor, change_swap_status)
# # phase_8.8 execution_intent must run before deposit_to_swapping:
# # it materialises executable facts off confirmed deposits
#     tick_phase_8_8_execution_intent(cursor)
#     tick_phase_8_7a_deposit_to_swapping(cursor, change_swap_status)
#     tick_phase_8_7b_swapping_to_completed(cursor, change_swap_status)
#     tick_phase_8_7c_swapping_to_failed(cursor, change_swap_status)
#     tick_phase_8_9c_timeout(cursor)
#     # tick_phase_8_9a_retry(cursor)
#     # tick_phase_8_9b_refund(cursor)
     # conn.close()
    

# Reordeing calls from the introduction of time contraints for timeouts
def engine_tick():
    # print("? engine_tick called")
    
    # breakpoint()

    conn = get_db()
    cursor = conn.cursor()

    # Phase 8.6 – deposit observation (unchanged)
    tick_phase_8_6_awaiting_deposit(cursor, change_swap_status)

    # Phase 8.8 – execution intent (inflicts with UI polling temporary commented out)
    # tick_phase_8_8_execution_intent(cursor)

    # ✅ Phase 3 ordering fix starts here

    # Rule #3: swapping → failed (timeout)
    tick_phase_8_7c_swapping_to_failed(cursor, change_swap_status)
    # Rule #4: provider_failed fact → immediate failed status
    tick_phase_provider_failed(cursor, change_swap_status)

    # Rule #2: FACT_SWAPPING → swapping
    tick_phase_8_7a_deposit_to_swapping(cursor, change_swap_status)

    # Rule #1: FACT_PAYOUT_CONFIRMED → completed
    tick_phase_8_7b_swapping_to_completed(cursor, change_swap_status)

    # --- keep retries / refunds for now ---
    # tick_phase_8_9a_retry(cursor)
    tick_phase_8_9b_refund(cursor)
    tick_phase_8_9a_retry(cursor)


    conn.close()

# 7.8 history data update 
def notify_swap_status_change(swap_id, old_status, new_status):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO swap_status_events (
            swap_id,
            old_status,
            new_status
        ) VALUES (?, ?, ?)
    """, (swap_id, old_status, new_status))

    conn.commit()
    conn.close()

    print(
        f"[SWAP {swap_id}] Status changed: "
        f"{old_status} → {new_status}"       
    )
    
# 
# phase 2 logic implement 17-04-26
def poll_providers_and_update_facts():
    """
    Phase 2: Observe provider status and record progress facts.
    This function:
    - does NOT change swap lifecycle
    - does NOT upsert or mutate facts
    - ONLY inserts new immutable facts when observed
    """

    conn = get_db()
    cursor = conn.cursor()

    # Find swaps that have execution started but are not yet completed
    cursor.execute("""
        SELECT s.*
        FROM swaps s
        WHERE EXISTS (
            SELECT 1 FROM facts f
            WHERE f.swap_id = s.id
              AND f.fact_type = ?
        )
        AND NOT EXISTS (
            SELECT 1 FROM facts f
            WHERE f.swap_id = s.id
              AND f.fact_type = ?
        )
    """, (FACT_EXECUTION_STARTED, FACT_PAYOUT_CONFIRMED))

    swaps = cursor.fetchall()
    conn.close()

    for swap in swaps:
        swap_id = swap["id"]

        # Determine which provider handled this swap from the execution_started fact source
        conn2 = get_db()
        cursor2 = conn2.cursor()
        cursor2.execute(
            "SELECT source FROM facts WHERE swap_id = ? AND fact_type = ?",
            (swap_id, "execution_started")
        )
        src_row = cursor2.fetchone()
        conn2.close()

        provider_name = "mock"  # default fallback
        if src_row:
            try:
                source_data = json.loads(src_row["source"])
                provider_name = source_data.get("provider", "mock")
            except Exception:
                pass

        try:
            provider = provider_registry.get(provider_name)
        except KeyError:
            print(f"[poll] provider {provider_name!r} not registered, skipping swap {swap_id}")
            continue

        provider_status = provider.get_status(swap)

        if provider_status == "deposit":
            # Provider has seen the deposit — insert deposit fact so engine can advance
            if not _exists_fact(swap_id, "deposit"):
                _insert_fact(
                    swap_id=swap_id,
                    fact_type="deposit",
                    source=json.dumps({"provider": provider.name})
                )

        elif provider_status == "swapping":
            if not _exists_fact(swap_id, FACT_SWAPPING):
                _insert_fact(
                    swap_id=swap_id,
                    fact_type=FACT_SWAPPING,
                    source=json.dumps({"provider": provider.name})
                )

        elif provider_status == "payout_confirmed":
            if not _exists_fact(swap_id, FACT_PAYOUT_CONFIRMED):
                _insert_fact(
                    swap_id=swap_id,
                    fact_type=FACT_PAYOUT_CONFIRMED,
                    source=json.dumps({"provider": provider.name})
                )

        elif provider_status == "failed":
            if not _exists_fact(swap_id, "provider_failed"):
                
                _insert_fact(
                swap_id=swap_id,
                fact_type="provider_failed",
                source=json.dumps({"provider": provider.name})
                )
# adding hold functionality        
        elif provider_status == "hold":
            if not _exists_fact(swap_id, "provider_hold"):
                _insert_fact(
                    swap_id=swap_id,
                    fact_type="provider_hold",
                    source=json.dumps({"provider": provider.name})
                )
                

# --- Phase 8.5: Engine polling (PULL-based, TOGGLE-controlled) ---




def start_engine_polling():
    """
    Periodically calls engine_tick() to pull external facts.
    This does NOT decide lifecycle; it only triggers the engine.
    """

    def poll_loop():
        print(f"[engine-poll] started (interval={ENGINE_POLL_INTERVAL}s)")
        while True:
            try:
                # NEW: poll providers and persist facts
                poll_providers_and_update_facts()
    
                # EXISTING: engine evaluates current facts
                engine_tick()
            except Exception as e:
                print("[engine-poll] error:", e)
    
            time.sleep(ENGINE_POLL_INTERVAL)


    thread = threading.Thread(target=poll_loop, daemon=True)
    thread.start()
    
####end of 8.5 polling addition

# ROUTES

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/engine/tick", methods=["POST"])
@dev_only
def run_engine():
    # print("🚪 /engine/tick ROUTE HIT")
    engine_tick()
    return jsonify({"status": "engine tick executed"})


# 7.8 status management (with transition enforcement)
@app.route("/swap/<int:swap_id>/status", methods=["POST"])
@dev_only
def update_swap_status(swap_id):
    data = request.get_json(force=True)
    new_status = data.get("status")

    success, result = change_swap_status(swap_id, new_status)

    if not success:
        return jsonify(result), 400
    
    return jsonify({
        "swap_id": swap_id,
        "status": result
    })





@app.route("/swap", methods=["GET"])
def swap():
    """
    Get quotes from all registered real providers.
    Frontend sends: amount, fromCoin, toCoin
    Returns: list of quotes sorted best output first.
    """
    try:
        amount = float(request.args.get("amount", 0))
        from_coin = normalise_coin(request.args.get("fromCoin", "").strip())
        to_coin   = normalise_coin(request.args.get("toCoin", "").strip())

        if amount <= 0:
            return jsonify({"error": "Amount must be greater than 0"}), 400
        if not from_coin or not to_coin:
            return jsonify({"error": "fromCoin and toCoin are required"}), 400
        if from_coin == to_coin:
            return jsonify({"error": "from and to coins must differ"}), 400

        # Query all real providers (skip mock)
 
        real_providers = [
            p for name, p in provider_registry._providers.items()
            if name != "mock"
        ]
        if not real_providers:
            if DEV_MODE:
                real_providers = [provider_registry.get("mock")]
            else:
                return jsonify({"error": "No swap providers are configured"}), 503

        quotes = []
        for provider in real_providers:
            try:
                quote = provider.get_quote(from_coin, to_coin, amount)
                meta  = quote.get("meta", {})
                output = round(quote["output_amount"], 8)
                # Compute implied rate if provider doesn't return one directly
                rate = meta.get("rate")
                if not rate and amount > 0 and output > 0:
                    rate = round(output / amount, 8)
                quotes.append({
                    "provider":   quote["provider"],
                    "output":     output,
                    "fee":        quote["fee"],
                    "rate":       rate,
                    "min_amount": meta.get("min_amount"),
                    "max_amount": meta.get("max_amount"),
                    "error":      None,
                })
            except Exception as e:
                print(f"[/swap quote] {provider.name} error: {e}")
                quotes.append({
                    "provider":   provider.name,
                    "output":     0,
                    "fee":        0,
                    "rate":       None,
                    "min_amount": None,
                    "max_amount": None,
                    "error":      str(e),
                })

        # Sort: valid quotes (output > 0) best first
        quotes.sort(key=lambda q: q["output"] if q["output"] > 0 else -1, reverse=True)

        return jsonify({
            "success": True,
            "input": {
                "amount": amount,
                "fromCoin": from_coin,
                "toCoin": to_coin,
            },
            "quotes": quotes,
        })

    except ValueError:
        return jsonify({"error": "Invalid numeric input"}), 400
    except Exception as e:
        print(f"[/swap quote] error: {e}")
        return jsonify({"error": "Quote failed", "details": str(e)}), 500


# 7.5 get_swap , raed the DB
@app.route("/swaps", methods=["GET"])
@dev_only
def get_swaps():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            from_coin,
            to_coin,
            amount,
            receive_address,
            deposit_address,
            status
        FROM swaps
        ORDER BY id DESC
        LIMIT 20
    """)

    rows = cursor.fetchall()
    conn.close()

    swaps = []
    for row in rows:
        swaps.append({
            "swap_id": row["id"],
            "from_coin": row["from_coin"],
            "to_coin": row["to_coin"],
            "amount": row["amount"],
            "receive_address": row["receive_address"],
            "deposit_address": row["deposit_address"],
            "status": row["status"]
        })

    return jsonify(swaps)



@app.route("/swap/<int:swap_id>", methods=["GET"])
def get_swap(swap_id):
    if not _token_matches(swap_id):
        return jsonify({"error": "Swap not found"}), 404
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            from_coin,
            to_coin,
            amount,
            receive_address,
            deposit_address,
            status,
            provider,
            provider_execution_id,
            rate,
            withdrawal_amount
        FROM swaps
        WHERE id = ?
    """, (swap_id,))

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return jsonify({"error": "Swap not found"}), 404

    return jsonify({
        "swap_id":              row["id"],
        "from_coin":            row["from_coin"],
        "to_coin":              row["to_coin"],
        "amount":               row["amount"],
        "receive_address":      row["receive_address"],
        "deposit_address":      row["deposit_address"],
        "status":               row["status"],
        "provider":             row["provider"],
        "provider_execution_id": row["provider_execution_id"],
        "rate":                 row["rate"],
        "withdrawal_amount":    row["withdrawal_amount"],
    })



@app.route("/create_swap", methods=["POST"])
def create_swap():
    from models.swap import Swap
    
    # MH set hard core breakpoint fort debugging 
    
    # breakpoint()   # <-- leave this here
    
    data = request.get_json(force=True)

    from_coin = normalise_coin(data.get("from_coin", ""))
    to_coin   = normalise_coin(data.get("to_coin", ""))
    amount = data.get("amount")
    receive_address = data.get("receive_address")

    # --- Basic server-side validation ---
    if not all([from_coin, to_coin, amount, receive_address]):
        return jsonify({"error": "Missing required fields"}), 400

    if float(amount) <= 0:
        return jsonify({"error": "Invalid amount"}), 400
    
    # --- Phase 8.3: create Swap object and get provider ---
 

    # Use provider chosen by frontend, fall back to changenow, then mock
    requested_provider = data.get("provider", "").strip().lower()

    if requested_provider and requested_provider in provider_registry._providers:
        provider_name = requested_provider
    elif "changenow" in provider_registry._providers:
        provider_name = "changenow"
    elif DEV_MODE:
        provider_name = "mock"
    else:
        return jsonify({"error": "No swap providers are configured"}), 503

    provider = provider_registry.get(provider_name)
    print(f"[create_swap] using provider: {provider_name}")
    
    email = data.get("email", "")
    rate = float(data.get("rate", 0) or 0)
    withdrawal_amount = float(data.get("withdrawal_amount", 0) or 0)
    from_coin_gbp_rate = float(data.get("from_coin_gbp_rate", 0) or 0)
    to_coin_gbp_rate   = float(data.get("to_coin_gbp_rate", 0) or 0)
    from_coin_usd_rate = float(data.get("from_coin_usd_rate", 0) or 0)
    to_coin_usd_rate   = float(data.get("to_coin_usd_rate", 0) or 0)
    refund_address = data.get("refund_address", "")

    # swap = Swap(
    #     id=None,
    #     from_coin=from_coin,
    #     to_coin=to_coin,
    #     amount=float(amount),
    #     status="created",
    #     provider=provider_name,
    #     receive_address=receive_address,
    #     email=email,
    # )
    # 02-05-26 add refund address
    swap = Swap(
        id=None,
        from_coin=from_coin,
        to_coin=to_coin,
        amount=float(amount),
        status="created",
        provider=provider_name,
        receive_address=receive_address,
        email=email,
        refund_address=refund_address,
    )

# --- Phase 8.3: provider decides deposit details ---
    provider_result = provider.create_swap(swap)
# used in Phase 1 fact insertion
    provider_execution_id = provider_result["provider_execution_id"]

    deposit_address = provider_result["deposit_address"]
    # status = "created"

    conn = get_db()
    cursor = conn.cursor()

    # cursor.execute("""
    #     INSERT INTO swaps (
    #         from_coin,
    #         to_coin,
    #         amount,
    #         receive_address,
    #         deposit_address,
    #         status,
    #         email,
    #         provider,
            # provider_execution_id,
    #         rate,
    #         withdrawal_amount
    #     ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    # """, (
        # swap.from_coin,
    #     swap.to_coin,
    #     swap.amount,
    #     swap.receive_address,
    #     deposit_address,
    #     swap.status,
    #     swap.email,
    #     provider_name,
    #     provider_execution_id,
    #     rate,
    #     withdrawal_amount,
    # ))
    
# 02-05-26 adding refund address to swap   
    access_token = secrets.token_urlsafe(24)
    cursor.execute("""
        INSERT INTO swaps (
            from_coin,
            to_coin,
            amount,
            receive_address,
            refund_address,
            deposit_address,
            status,
            email,
            provider,
            provider_execution_id,
            rate,
            withdrawal_amount,
            from_coin_gbp_rate,
            to_coin_gbp_rate,
            from_coin_usd_rate,
            to_coin_usd_rate,
            access_token
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        swap.from_coin,
        swap.to_coin,
        swap.amount,
        swap.receive_address,
        swap.refund_address or "",
        deposit_address,
        swap.status,
        swap.email,
        provider_name,
        provider_execution_id,
        rate,
        withdrawal_amount,
        from_coin_gbp_rate,
        to_coin_gbp_rate,
        from_coin_usd_rate,
        to_coin_usd_rate,
        access_token,
    ))
        
        

    swap_id = cursor.lastrowid

    conn.commit()
    conn.close()
    
    
    # import json
    
    if not _exists_fact(swap_id, FACT_EXECUTION_STARTED):
        _insert_fact(
            swap_id=swap_id,
            fact_type=FACT_EXECUTION_STARTED,
            source=json.dumps({
                "provider": provider_name,
                "provider_execution_id": provider_execution_id,
            })
        )

    
    change_swap_status(swap_id, "awaiting_deposit")
    
    send_swap_receipt(
    swap_id=swap_id,
    from_coin=swap.from_coin,
    to_coin=swap.to_coin,
    amount=swap.amount,
    withdrawal_amount=withdrawal_amount,
    deposit_address=deposit_address,
    receive_address=swap.receive_address,
    provider=provider_name,
    user_email=swap.email,
    from_coin_gbp_rate=from_coin_gbp_rate,
    to_coin_gbp_rate=to_coin_gbp_rate,
    from_coin_usd_rate=from_coin_usd_rate,
    to_coin_usd_rate=to_coin_usd_rate,
    )
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM swaps WHERE id = ?", (swap_id,))
    current_status = cursor.fetchone()["status"]
    conn.close()
    
    
# update to show provider_execution_id tracking link to UI 08-July-26 

#     return jsonify({
#         "swap_id": swap_id,
#         "deposit_address": deposit_address,
#         "amount": amount,
#         "status": current_status,
#         "from_coin": from_coin,
# })

    return jsonify({
        "swap_id": swap_id,
        "deposit_address": deposit_address,
        "amount": amount,
        "status": current_status,
        "from_coin": from_coin,
        "provider": provider_name, #bug fix 27-09-26
        "provider_execution_id": provider_execution_id,
        "access_token": access_token,
})






@app.route("/swap/<int:swap_id>/history", methods=["GET"])
def get_swap_history(swap_id):
    if not _token_matches(swap_id):
        return jsonify({"error": "Swap not found"}), 404
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            old_status,
            new_status,
            changed_at
        FROM swap_status_events
        WHERE swap_id = ?
        ORDER BY changed_at ASC
    """, (swap_id,))

    rows = cursor.fetchall()
    conn.close()

    history = []
    for row in rows:
        history.append({
            "from": row["old_status"],
            "to": row["new_status"],
            "at": row["changed_at"]
        })

    return jsonify({
        "swap_id": swap_id,
        "history": history
    })

@app.route("/debug/db")
@dev_only
def debug_db():
    conn = get_db()
    conn.execute("SELECT 1")
    conn.close()
    return "db ok"

@app.route("/dev/simulate_deposit/<int:swap_id>", methods=["POST"])
@dev_only
def dev_simulate_deposit(swap_id):
    if not app.config.get("DEV_MODE"):
        return {"error": "disabled"}, 403

    _insert_fact(
        swap_id=swap_id,
        fact_type="deposit",
        source="dev_simulator"
    )
    return {"ok": True}

@app.route("/dev/simulate_swapping/<int:swap_id>", methods=["POST"])
@dev_only
def dev_simulate_swapping(swap_id):
    _insert_fact(
        swap_id=swap_id,
        fact_type="swapping",
        source="dev_simulator"
    )
    return {"ok": True}


# @app.route("/dev/simulate_payout_confirmed/<int:swap_id>", methods=["POST"])
# def dev_simulate_payout_confirmed(swap_id):
    
#     _insert_fact(
#     swap_id=swap_id,
#     fact_type="payout_confirmed",
#     source="dev_simulator"
#    )
    
#     return {"ok": True}

@app.route("/dev/simulate_payout_confirmed/<int:swap_id>", methods=["POST"])
@dev_only
def dev_simulate_payout_confirmed(swap_id):
    _insert_fact(swap_id, "payout_confirmed", "dev_simulator")
    return {"ok": True}

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

# 31-05-26 commented out and replaced with below to work with Gunicorn 

# if __name__ == "__main__":
#     # app.run(debug=True) # causes crash 
#     init_db()
    
    
#     # print(">>> Manual Phase 2 polling test")
#     poll_providers_and_update_facts()
    


    
    
#     if ENABLE_ENGINE_POLLING:
#         start_engine_polling()
        
#     # print(app.url_map)

#     app.run(debug=False, use_reloader=False)
    
    
    # Run on startup regardless of how the app is started (Gunicorn or direct)
init_db()

if ENABLE_ENGINE_POLLING:
    start_engine_polling()

if __name__ == "__main__":
    # print(">>> Manual Phase 2 polling test")
    poll_providers_and_update_facts()
    app.run(debug=False, use_reloader=False)