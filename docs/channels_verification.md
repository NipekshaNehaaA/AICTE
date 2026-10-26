# AICTE Regulatory Channels Verification Guide (WhatsApp & SMTP)

## 1. Overview & Statutory Architecture

The AICTE Approval Process Handbook (APH 2024–27) mandates statutory stakeholder communications across multiple tiers of urgency:
- **In-App Realtime Notifications:** Immediate alert display within the institution tracker and officer queues.
- **Real SMTP Email Channel:** Authoritative legal notices with signed HTML templates and deep links.
- **WhatsApp Sandbox Channel:** Real-time mobile alerts for urgent inspection scheduling, deficiency cure deadlines, and escalation cascades.
- **SMS Channel:** Secondary mobile dispatch with explicit simulated fallback labeling.

Every dispatch record is tracked in the immutable `Notification` table and stamped into the cryptographic SHA-256 audit ledger (`AuditTrail`).

---

## 2. Twilio WhatsApp Integration

### 2.1 Configuration Environment Variables

Configure the following variables in `.env` or your production deployment environment:

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `TWILIO_ACCOUNT_SID` | Your Twilio Account SID from Twilio Console | `ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX` |
| `TWILIO_AUTH_TOKEN` | Your Twilio Auth Token | `your_auth_token_here` |
| `TWILIO_WHATSAPP_FROM` | Twilio WhatsApp Sender Number | `whatsapp:+14155238886` |
| `WHATSAPP_MAX_RETRIES` | Max retry attempts with exponential backoff | `3` |

### 2.2 Joining the Twilio WhatsApp Sandbox

To receive live statutory messages on your mobile device during testing or evaluation:
1. Save Twilio's WhatsApp number to your mobile contacts: **`+1 (415) 523-8886`**.
2. Open WhatsApp, send the sandbox activation keyword assigned to your Twilio account:
   ```text
   join <your-sandbox-keyword>
   ```
   *(e.g., `join code-orange` or `join bright-river`)*
3. Twilio will reply with a confirmation message: *"You are all set! The sandbox will remain active for 72 hours."*
4. Ensure the recipient's registered mobile number in the portal matches the WhatsApp account in international E.164 format:
   ```text
   +919876543210
   ```

### 2.3 Message Format & Statutory Labeling

In compliance with AICTE transparency standards and sandbox guidelines:
- Every message sent via Twilio Sandbox automatically includes the mandatory prefix:
  ```text
  [AICTE Statutory Sandbox] <Statutory Message Content>
  ```
- Delivery receipts record:
  - `channel`: `"WHATSAPP_SANDBOX"`
  - `label`: `"sandbox"`
  - `receipt_id`: Real Twilio Message SID (e.g., `SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)
  - `twilio_status`: `"queued"` / `"sent"` / `"delivered"`

### 2.4 User Opt-In Consent Protocol

Per Digital Personal Data Protection (DPDP) Act 2023 norms:
- Technical institutions and officers must have `opt_in_whatsapp = True` in the `users` table.
- If a user has not opted in, the dispatch is gracefully skipped with status:
  ```json
  {
    "status": "SKIPPED_NOT_OPTED_IN",
    "channel": "WHATSAPP_SANDBOX",
    "reason": "Recipient has not opted in to statutory WhatsApp notifications."
  }
  ```

---

## 3. Fallback Behavior (When Credentials are Absent)

When `TWILIO_ACCOUNT_SID` or `TWILIO_AUTH_TOKEN` is not configured:
- The system **never crashes or blocks workflow progression**.
- Dispatches automatically route to the clearly labeled simulated adapter:
  - `channel`: `"WHATSAPP_SIMULATED"`
  - `label`: `"SIMULATED"`
  - `status`: `"SIMULATED"`
  - `receipt_id`: `sim_wa_<12-hex-uuid>`
  - `note`: `"Twilio credentials absent; delivered via simulated sandbox adapter."`
- The fallback status is faithfully rendered in the Notification Delivery Center without misleading claims.

---

## 4. Quiet Hours & Statutory Delivery Policy

Statutory communications adhere to strict anti-harassment and quiet hour policies:
- **Quiet Window:** Defined by `QUIET_HOURS_START` (default: 22:00 / 10:00 PM) to `QUIET_HOURS_END` (default: 06:00 / 6:00 AM).
- **Severity Overrides:**
  - **CRITICAL Alerts (SLA Breaches, EVC Cancellations, Emergency Hearings):** Set `override_quiet=True` and deliver immediately 24/7.
  - **ROUTINE / WARNING Alerts (Document Renewal Reminders at T-90, T-60):** Respect quiet hours; status marked as `DEFERRED_QUIET_HOURS` until 06:00 AM.

---

## 5. Verification & Test Execution

### 5.1 Automated Unit & Integration Tests

Run the dedicated multi-channel test suite:
```powershell
python -m pytest tests/test_scheduler_and_real_channels.py -v
```

This verifies:
1. `test_twilio_whatsapp_adapter_http_mock`: Simulates live Twilio API HTTP Basic Auth, JSON response parsing, and sandbox labeling.
2. `test_twilio_whatsapp_adapter_fallback_to_simulated`: Validates zero crash and truthful `SIMULATED` labeling when credentials are omitted.
3. `test_real_smtp_exponential_backoff_and_retry`: Verifies SMTP connection handling and exponential backoff retry.
4. `test_scheduler_evaluates_at_correct_offsets_on_frozen_clock`: Validates statutory offsets (T-90, T-60, T-30, T-7, Overdue) with idempotency key deduplication.

### 5.2 Manual Live WhatsApp Send Verification

To trigger a live WhatsApp dispatch using active Twilio credentials:
```powershell
$env:TWILIO_ACCOUNT_SID="ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
$env:TWILIO_AUTH_TOKEN="your_auth_token_here"
$env:TWILIO_WHATSAPP_FROM="whatsapp:+14155238886"

python -c "
from app.twilio_whatsapp import whatsapp_adapter
res = whatsapp_adapter.send_whatsapp_message(
    to_phone='+919876543210',
    message_body='AICTE Portal Test: EVC Inspection successfully confirmed for 15-Nov-2026.',
    user_opted_in=True
)
print(res)
"
```
Output:
```json
{
  "status": "DELIVERED",
  "channel": "WHATSAPP_SANDBOX",
  "label": "sandbox",
  "receipt_id": "SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "recipient": "+919876543210",
  "delivered_at": "2026-10-25T08:20:00.000000",
  "twilio_status": "queued",
  "attempts": 1
}
```
