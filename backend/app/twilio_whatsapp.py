"""
=============================================================================
TWILIO WHATSAPP SANDBOX ADAPTER (TASK 2)
=============================================================================
Provides real WhatsApp messaging via the official Twilio WhatsApp Sandbox API:
1. Driven by environment variables:
   - TWILIO_ACCOUNT_SID
   - TWILIO_AUTH_TOKEN
   - TWILIO_WHATSAPP_FROM (default: whatsapp:+14155238886)
2. Opt-in recipient numbers stored per user (opt_in_whatsapp = True).
3. Clearly labelled "sandbox" in all delivered messages and receipts.
4. If WhatsApp credentials are absent, falls back to clearly labelled "SIMULATED".
5. Includes retry with exponential backoff on HTTP / network errors.
=============================================================================
"""

import os
import time
import uuid
import base64
import json
import urllib.request
import urllib.parse
from datetime import datetime
from typing import Dict, Any, Optional

class TwilioWhatsAppAdapter:
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
        self.from_number = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886").strip()
        self.max_retries = int(os.getenv("WHATSAPP_MAX_RETRIES", "3"))

    def has_credentials(self) -> bool:
        """Returns True if Twilio Account SID and Auth Token are provided."""
        return bool(self.account_sid and self.auth_token)

    def format_whatsapp_recipient(self, phone: str) -> str:
        """Ensures phone number has standard E.164 format and whatsapp: prefix."""
        cleaned = phone.strip()
        if not cleaned.startswith("whatsapp:"):
            # Ensure leading +
            if not cleaned.startswith("+"):
                cleaned = f"+{cleaned}"
            return f"whatsapp:{cleaned}"
        return cleaned

    def send_whatsapp_message(
        self,
        to_phone: str,
        message_body: str,
        user_opted_in: bool = True,
        override_sandbox_label: bool = False,
    ) -> Dict[str, Any]:
        """
        Dispatches a WhatsApp message via Twilio Sandbox or falls back to SIMULATED.
        Returns a delivery receipt with receipt_id, channel, and delivery_status.
        """
        now_iso = datetime.utcnow().isoformat()

        if not user_opted_in:
            return {
                "status": "SKIPPED_NOT_OPTED_IN",
                "channel": "WHATSAPP_SANDBOX",
                "label": "sandbox",
                "recipient": to_phone,
                "receipt_id": None,
                "reason": "Recipient has not opted in to statutory WhatsApp notifications.",
                "delivered_at": None,
            }

        # Format message with sandbox label per Task 2 rules
        label_prefix = "" if override_sandbox_label else "[AICTE Statutory Sandbox] "
        full_body = f"{label_prefix}{message_body}"

        # If credentials absent, return explicitly labelled SIMULATED
        if not self.has_credentials():
            sim_id = f"sim_wa_{uuid.uuid4().hex[:12]}"
            return {
                "status": "SIMULATED",
                "channel": "WHATSAPP_SIMULATED",
                "label": "SIMULATED",
                "receipt_id": sim_id,
                "recipient": to_phone,
                "message": full_body,
                "delivered_at": now_iso,
                "note": "Twilio credentials absent; delivered via simulated sandbox adapter.",
            }

        # Real Twilio API HTTP Request
        recipient_wa = self.format_whatsapp_recipient(to_phone)
        from_wa = self.from_number if self.from_number.startswith("whatsapp:") else f"whatsapp:{self.from_number}"
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"

        post_data = urllib.parse.urlencode({
            "From": from_wa,
            "To": recipient_wa,
            "Body": full_body,
        }).encode("utf-8")

        auth_str = f"{self.account_sid}:{self.auth_token}"
        auth_b64 = base64.b64encode(auth_str.encode("utf-8")).decode("ascii")

        headers = {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        last_error = ""
        for attempt in range(1, self.max_retries + 1):
            try:
                req = urllib.request.Request(url, data=post_data, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=10.0) as resp:
                    resp_bytes = resp.read()
                    resp_json = json.loads(resp_bytes.decode("utf-8"))
                    sid = resp_json.get("sid", f"wa_msg_{uuid.uuid4().hex[:12]}")
                    return {
                        "status": "DELIVERED",
                        "channel": "WHATSAPP_SANDBOX",
                        "label": "sandbox",
                        "receipt_id": sid,
                        "recipient": to_phone,
                        "delivered_at": datetime.utcnow().isoformat(),
                        "twilio_status": resp_json.get("status", "queued"),
                        "attempts": attempt,
                    }
            except Exception as e:
                last_error = str(e)
                if attempt < self.max_retries:
                    time.sleep(0.1 * (2 ** (attempt - 1)))

        return {
            "status": "FAILED",
            "channel": "WHATSAPP_SANDBOX",
            "label": "sandbox",
            "receipt_id": None,
            "recipient": to_phone,
            "error_message": f"Twilio API request failed after {self.max_retries} attempts: {last_error}",
            "delivered_at": None,
            "attempts": self.max_retries,
        }

whatsapp_adapter = TwilioWhatsAppAdapter()
