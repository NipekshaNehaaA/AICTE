# Real Multi-Channel Messaging Setup Guide (Live & Sandbox)

This guide documents the configuration and live operation of the AICTE Approval Workflow automation messaging engine. The platform provides verified, multi-channel notification dispatch across:
1. **In-App Notification Desk**: Instant, zero-latency dashboard alerts with live unread badge polling (5s).
2. **Real SMTP Email Channel**: Cryptographically tracked emails with Message-ID receipts, exponential backoff, and quiet-hours enforcement.
3. **Official Twilio WhatsApp Sandbox**: Statutory notifications delivered directly to WhatsApp with Twilio Message SID receipts.

---

## 1. Architecture: Live Workspace vs. Sandbox Mode

To prevent accidental spam to synthetic demo colleges or real institutional contacts during demonstrations, the platform enforces strict workspace-isolated delivery routing:

| Feature | Live Workspace (`live`) | Evaluation Sandbox (`sandbox`) |
| :--- | :--- | :--- |
| **Database** | `backend/aicte_live.db` | `backend/aicte_sandbox.db` |
| **Default Recipients** | Registered institution & officer emails | Synthetic addresses (`@fictional-aicte.edu.in`) |
| **Sandbox Override** | Disabled (not applicable) | **Enabled**: Intercepts all messages and delivers them to the evaluator's personal email & phone |
| **Message Labeling** | Statutory Regulatory Notice | Marked with `[AICTE Statutory Sandbox]` and sandbox header |
| **Receipt Tracking** | Cryptographic SHA-256 Ledger | Cryptographic SHA-256 Ledger |

---

## 2. Real SMTP Email Channel Setup

The platform uses Python's standard `smtplib` with TLS encryption to deliver real emails to mailboxes.

### Option A: Using Gmail (Free & Fast for Live Testing)

1. **Enable 2-Step Verification** on your Google Account:
   - Visit [myaccount.google.com/security](https://myaccount.google.com/security) $\to$ **2-Step Verification** $\to$ Turn ON.
2. **Generate an App Password**:
   - Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).
   - App Name: `AICTE Platform`.
   - Copy the 16-character password (e.g., `abcd efgh ijkl mnop`).
3. **Configure Environment Variables** in `backend/.env`:
   ```bash
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your_email@gmail.com
   SMTP_PASSWORD=abcdefghijklmnop
   SMTP_FROM=your_email@gmail.com
   SMTP_USE_TLS=true
   EMAIL_MAX_RETRIES=3
   ```
4. **Restart Backend Server**:
   ```bash
   cd backend
   uvicorn app.main:app --port 8000 --reload
   ```

### Option B: Local SMTP Sink (Mailpit / Mailhog)

If internet SMTP is restricted in your local environment:
1. Launch Mailpit via Docker:
   ```bash
   docker run -d -p 8025:8025 -p 1025:1025 axllent/mailpit
   ```
2. Configure `backend/.env`:
   ```bash
   SMTP_HOST=127.0.0.1
   SMTP_PORT=1025
   SMTP_USER=
   SMTP_PASSWORD=
   SMTP_FROM=alerts@aicte-india.org
   SMTP_USE_TLS=false
   ```
3. Open Mailpit web inbox at `http://localhost:8025` to inspect all delivered HTML/plain-text emails.

---

## 3. Twilio WhatsApp Sandbox Setup

The platform integrates directly with the official Twilio WhatsApp Sandbox API.

### Step 1: Create Free Twilio Account & Access Sandbox
1. Register at [twilio.com](https://www.twilio.com/try-twilio).
2. In the Twilio Console, navigate to **Messaging** $\to$ **Try it out** $\to$ **Send a WhatsApp message**.
3. Note the Twilio WhatsApp Phone Number (typically `+1 415 523 8886`).

### Step 2: Join the Sandbox on Your Mobile Phone
1. Open WhatsApp on your mobile phone.
2. Send a WhatsApp text to `+1 415 523 8886` containing your unique sandbox join phrase:
   ```text
   join <your-two-words>
   ```
   *(For example: `join brave-tiger`)*
3. Twilio will reply with: *"You are all set! The sandbox will automatically stop receiving messages from this number after 72 hours."*

### Step 3: Configure Twilio Credentials in `backend/.env`
```bash
TWILIO_ACCOUNT_SID=ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
WHATSAPP_MAX_RETRIES=3
```

> [!NOTE]
> If `TWILIO_ACCOUNT_SID` or `TWILIO_AUTH_TOKEN` is not configured, the platform safely returns status `SIMULATED` with an explicit notice, rather than faking delivery receipts.

---

## 4. Evaluator Sandbox Override (Live Demonstrations)

When demonstrating in **Sandbox** workspace, synthetic institutions have simulated emails (`principal@fictional-aicte.edu.in`).

To receive real emails and real WhatsApp messages on your own phone without modifying institutional seed data:
1. Click the **"Override Real Messages"** button in the TopBar or Login Screen banner.
2. Enter your real test email and E.164 WhatsApp number:
   - **Test Email**: `evaluator@yourdomain.com`
   - **WhatsApp Phone**: `+919876543210`
3. Click **"Save Override"**.
4. All subsequent automated regulatory notices (deficiency notices, EVC schedules, lease expiry warnings) will immediately be delivered to your inbox and WhatsApp!

---

## 5. Statutory Multilingual Templates & Exact APH Citations

Every notification is generated from human-reviewed static templates with statutory citations from the AICTE Approval Process Handbook (APH 2024–27):

| Template Key | Trigger / Condition | APH Statutory Clause Citation | Supported Languages |
| :--- | :--- | :--- | :--- |
| `DEFICIENCY_CURE_NOTICE` | Scrutiny noted documentary defect | Chapter I Clause 1.8(f) & Clause 2.23.3 | English, हिन्दी, தமிழ் |
| `LEASE_EXPIRY_WARNING` | Land lease $< 30$ years remaining | Chapter I Clause 1.4.1(e) & Clause 2.25 | English, हिन्दी, தமிழ் |
| `EVC_SCHEDULE_NOTIFICATION` | Expert Visit Committee scheduled | Chapter I Clause 1.9 & Annexure-16 Clause 16.5 | English, हिन्दी, தமிழ் |
| `SLA_BREACH_ALERT` | Clock breached without pause | Chapter I Clause 1.10 (Escalation Ladder) | English, हिन्दी, தமிழ் |
| `UNDERTAKING_COMPLIANCE_REMINDER` | Time-bound commitment deadline | Chapter I Clause 1.8(g) & Clause 2.23 | English, हिन्दी, தமிழ் |

---

## 6. Quiet Hours & Regulatory SLA Retries

### Quiet Hours Window
- **Statutory Purpose**: Prevents non-emergency communications during nighttime hours.
- **Configurable Hours**: Default is 22:00 to 06:00 (10 PM to 6 AM).
- **Behavior**: If an automated trigger fires during quiet hours, its status is recorded as `DEFERRED_QUIET_HOURS` in the database.
- **Urgent / Manual Override**: Manual resends and explicit test messages automatically override quiet hours.

### Due-Date Alert Resend / Retry
1. Navigate to the **Notifications** tab or the **Case Docket $\to$ Alerts** tab.
2. For any notification in `FAILED` or `DEFERRED_QUIET_HOURS` status, click **"Resend"**.
3. The platform re-executes dispatch over the configured channel with exponential backoff.
4. An immutable audit record (`ALERT_RESENT`) is chained into the SHA-256 regulatory ledger.

### "Send Test Notification" Interactive Verification
In the Notification Center, click **"Channel & Language Preferences"** $\to$ **"Send Test Notification"**:
- Select target channels (`In-App`, `Email`, `WhatsApp Sandbox`).
- Choose preferred language (`English`, `हिन्दी`, `தமிழ்`).
- Click **"Dispatch Test Message"**.
- The platform returns the real provider response with live Message-ID, Twilio SID, or connection details.
