import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart            
from datetime import datetime

SMTP_SERVER   = os.environ.get("BREVO_SMTP_SERVER", "smtp-relay.brevo.com")
SMTP_PORT     = int(os.environ.get("BREVO_SMTP_PORT", 587))
SMTP_LOGIN    = os.environ.get("BREVO_SMTP_LOGIN")
SMTP_PASSWORD = os.environ.get("BREVO_SMTP_PASSWORD")
# FROM_ADDRESS  = "hello@justswapping.io"
FROM_ADDRESS  = os.environ.get("EMAIL_FROM_ADDRESS", "hello@justswapping.io")
REPLY_TO_ADDRESS = os.environ.get("EMAIL_REPLY_TO_ADDRESS", "support@justswapping.io")

def _send_email(to_address, subject, body):
    if not SMTP_LOGIN or not SMTP_PASSWORD:
        print("⚠️  Brevo email not configured — skipping email")
        return False
    msg = MIMEMultipart()
    msg["From"]    = FROM_ADDRESS
    msg["To"]      = to_address
    msg["Subject"] = subject
    msg["Reply-To"] = REPLY_TO_ADDRESS
    msg.attach(MIMEText(body, "plain"))
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_LOGIN, SMTP_PASSWORD)
            server.sendmail(FROM_ADDRESS, to_address, msg.as_string())
        return True
    except Exception as e:
        print(f"⚠️  Email send failed: {e}")
        return False


def send_swap_receipt(swap_id, from_coin, to_coin, amount, withdrawal_amount,
                      deposit_address, receive_address, provider, user_email,
                      from_coin_gbp_rate=0, to_coin_gbp_rate=0,
                      from_coin_usd_rate=0, to_coin_usd_rate=0):
    if not user_email:
        print(f"[email] No user email for swap {swap_id} — skipping receipt")
        return
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    subject = f"Your JustSwapping receipt — Swap #{swap_id}"
    body = f"""
Hi,

Your swap has been created successfully. Here are your details:

  Swap ID:          #{swap_id}
  Created at:       {timestamp}
  You send:         {amount} {from_coin.upper()}
  You receive:      {withdrawal_amount} {to_coin.upper()}
  Provider:         {provider}

  Deposit address:  {deposit_address}
  Receive address:  {receive_address}

Please send exactly {amount} {from_coin.upper()} to the deposit address above.
Your swap will be processed automatically once the deposit is confirmed.

Thanks for using JustSwapping!

---
Need help? Reply to this email, or contact {REPLY_TO_ADDRESS} quoting Swap ID #{swap_id}.
"""
    if _send_email(user_email, subject, body):
        # print(f"✅ Receipt sent to {user_email} for swap #{swap_id}")
        print(f"✅ Receipt sent for swap #{swap_id}")
    else:
        print(f"⚠️  Failed to send receipt for swap #{swap_id}")

def send_completion_receipt(swap_id, from_coin, to_coin, amount, withdrawal_amount,
                             receive_address, provider, user_email,
                             from_coin_gbp_rate=0, to_coin_gbp_rate=0,
                             from_coin_usd_rate=0, to_coin_usd_rate=0):
    if not user_email:
        return
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    subject = f"Your JustSwapping swap is complete — Swap #{swap_id}"
    body = f"""
Hi,

Great news — your swap has completed successfully!

  Swap ID:          #{swap_id}
  Completed at:     {timestamp}
  You sent:         {amount} {from_coin.upper()} (≈ £{amount * from_coin_gbp_rate:.2f} GBP / ${amount * from_coin_usd_rate:.2f} USD)
  You received:      {withdrawal_amount} {to_coin.upper()} (≈ £{withdrawal_amount * to_coin_gbp_rate:.2f} GBP / ${withdrawal_amount * to_coin_usd_rate:.2f} USD)
  Provider:         {provider}

  Funds sent to:    {receive_address}

Thank you for using JustSwapping!

---
Need help? Reply to this email, or contact {REPLY_TO_ADDRESS} quoting Swap ID #{swap_id}.
"""
    if _send_email(user_email, subject, body):
        # print(f"✅ Completion receipt sent to {user_email} for swap #{swap_id}")
        print(f"✅ Completion receipt sent for swap #{swap_id}")
    else:
        print(f"⚠️  Failed to send completion receipt for swap #{swap_id}")


def send_failed_receipt(swap_id, from_coin, to_coin, amount,
                        receive_address, provider, user_email,
                        from_coin_gbp_rate=0, from_coin_usd_rate=0):
    if not user_email:
        return
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    subject = f"Your JustSwapping swap could not be completed — Swap #{swap_id}"
    body = f"""
Hi,

Unfortunately your swap could not be completed.

  Swap ID:          #{swap_id}
  Failed at:        {timestamp}
  You sent:         {amount} {from_coin.upper()} (≈ £{amount * from_coin_gbp_rate:.2f} GBP / ${amount * from_coin_usd_rate:.2f} USD)
  Destination:      {receive_address}
  Provider:         {provider}

If you sent funds to the deposit address please contact us immediately
with your Swap ID so we can investigate.

We apologise for the inconvenience.

JustSwapping

---
Need help? Reply to this email, or contact {REPLY_TO_ADDRESS} quoting Swap ID #{swap_id}.
"""
    if _send_email(user_email, subject, body):
        # print(f"✅ Failed receipt sent to {user_email} for swap #{swap_id}")
        print(f"✅ Failed receipt sent for swap #{swap_id}")
    else:
        print(f"⚠️  Failed to send failed receipt for swap #{swap_id}")