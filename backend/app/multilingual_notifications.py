"""
=============================================================================
STATIC REVIEWED MULTILINGUAL NOTIFICATION TEMPLATES (EN / HI / TA)
=============================================================================
Provides verified, static multilingual templates in English, Hindi, and Tamil
with exact AICTE Approval Process Handbook (APH) clause references and statutory due dates.

Supported Languages:
- en: English
- hi: हिन्दी (Hindi)
- ta: தமிழ் (Tamil)

Features:
- Static, human-reviewed translations ensuring legal and regulatory accuracy.
- Exact statutory clause references (Clause 1.8(f), Clause 1.4.1(e), Clause 1.9, etc.).
- Strict fallback to English ('en') if an untranslated or unsupported language is requested.
=============================================================================
"""

from typing import Dict, Any, Optional, Tuple

SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "हिन्दी (Hindi)",
    "ta": "தமிழ் (Tamil)",
}

NOTIFICATION_TEMPLATES: Dict[str, Dict[str, Dict[str, str]]] = {
    "DEFICIENCY_CURE_NOTICE": {
        "en": {
            "title": "Deficiency Cure Window Notice: {application_no}",
            "message": "Notice for {institution_name}: Under APH Clause {aph_clause_ref}, deficiencies must be rectified and verified documents uploaded by {due_date}. Failure to upload rectifications before the due date may lead to rejection under Chapter II.",
            "aph_clause_ref": "Chapter I Clause 1.8(f) & Clause 2.23.3",
        },
        "hi": {
            "title": "कमी सुधार सूचना: {application_no}",
            "message": "{institution_name} के लिए आवश्यक सूचना: एआईसीएसटीई अनुमोदन प्रक्रिया पुस्तिका की धारा {aph_clause_ref} के अनुसार, पाई गई कमियों को {due_date} तक ठीक करना अनिवार्य है। नियत तिथि तक सुधार दस्तावेज प्रस्तुत न करने पर अध्याय II के तहत अनुमोदन अस्वीकृत किया जा सकता है।",
            "aph_clause_ref": "अध्याय I धारा 1.8(f) एवं धारा 2.23.3",
        },
        "ta": {
            "title": "குறைபாடு திருத்த அறிவிப்பு: {application_no}",
            "message": "{institution_name}-க்கான சட்டப்பூர்வ அறிவிப்பு: ஏஐசிடிஇ வழிகாட்டுதல் விதி {aph_clause_ref}-இன் படி, கண்டறியப்பட்ட குறைபாடுகளை {due_date} ஆம் தேதிக்குள் சரிசெய்து ஆவணங்களை சமர்ப்பிக்க வேண்டும். குறிப்பிட்ட தேதிக்குள் திருத்தங்களை பதிவேற்ற தவறினால் விண்ணப்பம் நிராகரிக்கப்படலாம்.",
            "aph_clause_ref": "அத்தியாயம் I விதி 1.8(f) மற்றும் விதி 2.23.3",
        },
    },
    "LEASE_EXPIRY_WARNING": {
        "en": {
            "title": "Land Lease Expiry Advisory: {institution_name}",
            "message": "Regulatory Advisory for {institution_name}: Registered land lease deed expires on {due_date}. In accordance with APH Clause {aph_clause_ref}, extension of the lease for a further 30 years must be executed and registered prior to the EoA cutoff.",
            "aph_clause_ref": "Chapter I Clause 1.4.1(e) & Clause 2.25",
        },
        "hi": {
            "title": "भूमि पट्टा समाप्ति परामर्श: {institution_name}",
            "message": "{institution_name} के लिए वैधानिक परामर्श: पंजीकृत भूमि पट्टा विलेख {due_date} को समाप्त हो रहा है। एआईसीएसटीई नियम {aph_clause_ref} के तहत, ईओए कटऑफ से पूर्व पट्टे को आगे 30 वर्षों के लिए विस्तारित व पंजीकृत कराना अनिवार्य है।",
            "aph_clause_ref": "अध्याय I धारा 1.4.1(e) एवं धारा 2.25",
        },
        "ta": {
            "title": "நில குத்தகை காலாவதி ஆலோசனை: {institution_name}",
            "message": "{institution_name}-க்கான ஆலோசனை: பதிவு செய்யப்பட்ட நில குத்தகை பத்திரம் {due_date} அன்று முடிவடைகிறது. ஏஐசிடிஇ விதி {aph_clause_ref}-இன் படி, மேலும் 30 ஆண்டுகளுக்கு குத்தகை நீட்டிப்பு பத்திரத்தை பதிவு செய்து சமர்ப்பிக்க வேண்டும்.",
            "aph_clause_ref": "அத்தியாயம் I விதி 1.4.1(e) மற்றும் விதி 2.25",
        },
    },
    "EVC_SCHEDULE_NOTIFICATION": {
        "en": {
            "title": "EVC Inspection Scheduled: {application_no}",
            "message": "Official Expert Visit Committee (EVC) inspection for {institution_name} is scheduled on {due_date} ({mode}). Under APH Clause {aph_clause_ref}, a mandatory 30-minute geotagged video recording and physical infrastructure verification will be conducted.",
            "aph_clause_ref": "Chapter I Clause 1.9 & Annexure-16 Clause 16.5",
        },
        "hi": {
            "title": "विशेषज्ञ समिति (ईवीसी) निरीक्षण निर्धारित: {application_no}",
            "message": "{institution_name} के लिए विशेषज्ञ निरीक्षण समिति (ईवीसी) का दौरा {due_date} ({mode}) को निर्धारित किया गया है। एआईसीएसटीई नियम {aph_clause_ref} के तहत 30 मिनट की जियोटैग्ड वीडियो रिकॉर्डिंग एवं आधारभूत संरचना सत्यापन अनिवार्य है।",
            "aph_clause_ref": "अध्याय I धारा 1.9 एवं अनुलग्नक-16 धारा 16.5",
        },
        "ta": {
            "title": "நிபுணர் குழு (EVC) ஆய்வு திட்டமிடல்: {application_no}",
            "message": "{institution_name}-க்கான நிபுணர் வருகைக் குழு ஆய்வு {due_date} ({mode}) அன்று திட்டமிடப்பட்டுள்ளது. விதி {aph_clause_ref}-இன் படி 30 நிமிட புவிசார் குறிச்சொல் கொண்ட வீடியோ பதிவு மற்றும் கட்டமைப்பு சரிபார்ப்பு கட்டாயமாகும்.",
            "aph_clause_ref": "அத்தியாயம் I விதி 1.9 மற்றும் இணைப்பு-16 விதி 16.5",
        },
    },
    "SLA_BREACH_ALERT": {
        "en": {
            "title": "Urgent: Statutory Timeline Exceeded for {application_no}",
            "message": "Statutory timeline exceeded: Application {application_no} ({institution_name}) exceeded statutory processing timeline (target: {due_date}). The case has been automatically escalated to higher supervisory tier under APH Clause {aph_clause_ref}.",
            "aph_clause_ref": "Chapter I Clause 1.10 (Escalation Ladder)",
        },
        "hi": {
            "title": "अति आवश्यक: {application_no} के लिए वैधानिक समयसीमा समाप्त",
            "message": "{institution_name} के आवेदन {application_no} की वैधानिक समयसीमा (लक्ष्य तिथि: {due_date}) समाप्त हो चुकी है। धारा {aph_clause_ref} के तहत यह मामला स्वतः उच्च प्रशासनिक स्तर पर अग्रेषित कर दिया गया है।",
            "aph_clause_ref": "अध्याय I धारा 1.10 (सोपानिकी सीढ़ी)",
        },
        "ta": {
            "title": "அவசரம்: {application_no} சட்டப்பூர்வ காலக்கெடு மீறல்",
            "message": "{institution_name}-இன் விண்ணப்பம் {application_no} சட்டப்பூர்வ காலக்கெடுவான {due_date}-ஐ கடந்துவிட்டது. விதி {aph_clause_ref}-இன் படி தானாகவே அடுத்த நிர்வாக நிலைக்கு கொண்டு செல்லப்பட்டுள்ளது.",
            "aph_clause_ref": "அத்தியாயம் I விதி 1.10 (படிநிலை ஏணி)",
        },
    },
    "UNDERTAKING_COMPLIANCE_REMINDER": {
        "en": {
            "title": "Time-Bound Undertaking Due: {application_no}",
            "message": "Reminder for {institution_name}: Time-bound undertaking commitments must be fulfilled and compliance uploaded by {due_date}. As stipulated under APH Clause {aph_clause_ref}, non-compliance may invite punitive reduction of approved seats.",
            "aph_clause_ref": "Chapter I Clause 1.8 & Annexure-4",
        },
        "hi": {
            "title": "समयबद्ध वचनबद्धता अनुपालन अनुस्मारक: {application_no}",
            "message": "{institution_name} के लिए अनुस्मारक: समयबद्ध वचनबद्धता की शर्तें {due_date} तक पूर्ण कर अनुपालन रिपोर्ट अपलोड करना अनिवार्य है। धारा {aph_clause_ref} के तहत अनुपालन न करने पर सीटों में कटौती की जा सकती है।",
            "aph_clause_ref": "अध्याय I धारा 1.8 एवं अनुलग्नक-4",
        },
        "ta": {
            "title": "காலக்கெடு உறுதிமொழி நினைவூட்டல்: {application_no}",
            "message": "{institution_name}-க்கான நினைவூட்டல்: ஒப்புக்கொள்ளப்பட்ட உறுதிமொழிகளை {due_date} ஆம் தேதிக்குள் நிறைவேற்றி சமர்ப்பிக்க வேண்டும். விதி {aph_clause_ref}-இன் படி செயல்பட தவறினால் அனுமதிக்கப்பட்ட இடங்களில் குறைப்பு நடவடிக்கை எடுக்கப்படலாம்.",
            "aph_clause_ref": "அத்தியாயம் I விதி 1.8 மற்றும் இணைப்பு-4",
        },
    },
}

class MultilingualNotificationService:
    @staticmethod
    def get_supported_languages() -> Dict[str, str]:
        return SUPPORTED_LANGUAGES

    @staticmethod
    def list_template_keys() -> list:
        return list(NOTIFICATION_TEMPLATES.keys())

    @classmethod
    def render_notification(
        cls,
        template_key: str,
        preferred_language: Optional[str] = "en",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Renders notification title and body using static, reviewed templates.
        Enforces strict fallback to 'en' (English) if language is unsupported or untranslated.
        """
        ctx = context.copy() if context else {}
        
        # Defaults for context placeholders
        ctx.setdefault("application_no", "APP-2026-TBD")
        ctx.setdefault("institution_name", "Technical Institution")
        ctx.setdefault("due_date", "31-Mar-2026")
        ctx.setdefault("mode", "Physical On-Site")

        if template_key not in NOTIFICATION_TEMPLATES:
            raise ValueError(f"Unknown template key '{template_key}'. Available: {list(NOTIFICATION_TEMPLATES.keys())}")

        template_family = NOTIFICATION_TEMPLATES[template_key]
        lang = (preferred_language or "en").lower().strip()

        fallback_applied = False
        fallback_reason = None

        if lang not in SUPPORTED_LANGUAGES:
            fallback_applied = True
            fallback_reason = f"Language '{lang}' is unsupported. Fallback to English ('en') applied."
            lang = "en"
        elif lang not in template_family:
            fallback_applied = True
            fallback_reason = f"Template '{template_key}' is not yet translated to '{lang}'. Fallback to English ('en') applied."
            lang = "en"

        chosen_template = template_family[lang]
        clause_ref = chosen_template.get("aph_clause_ref", "Chapter I Clause 1.8")
        ctx.setdefault("aph_clause_ref", clause_ref)

        rendered_title = chosen_template["title"].format(**ctx)
        rendered_message = chosen_template["message"].format(**ctx)

        return {
            "template_key": template_key,
            "language": lang,
            "language_name": SUPPORTED_LANGUAGES[lang],
            "title": rendered_title,
            "message": rendered_message,
            "aph_clause_ref": clause_ref,
            "due_date": ctx.get("due_date"),
            "fallback_applied": fallback_applied,
            "fallback_reason": fallback_reason,
            "supported_languages": list(SUPPORTED_LANGUAGES.keys()),
        }

multilingual_service = MultilingualNotificationService()
