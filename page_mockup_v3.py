#-------------------------------------------------------------
#-------------------------------------------------------------
# 1A. Imports and page setup 
# Imports packages and sets up basic page configuration.

import base64
import os 
import json
import streamlit as st
import uuid
import urllib.request
import urllib.error
from openai import OpenAI 
from datetime import date, datetime, timezone, timedelta
from typing import TypedDict

st.set_page_config(page_title = "bostonrentals.com (mock)", page_icon = "🏙️", layout = "wide")

#-------------------------------------------------------------
#-------------------------------------------------------------
# 1B. Secrets & OpenAI Client
# Brings in secrete keys for calling of Supabase and OpenAI API. Create OpenAI Client.

# Get secrets
def get_secrets(name_env: str, *secrets_path):
    """
    Prefer flat environment variables (Render, GH Actions, etc.).
    Fall back to nested st.secrets['section']['key'] used on Streamlit Cloud.
    """
    val = os.environ.get(name_env)
    if val:
        return val
    try:
        s = st.secrets
        for k in secrets_path:
            s = s[k]
        return s
    except Exception:
        return None

OPENAI_API_KEY = get_secrets("OPENAI_API_KEY", "openai", "api_key")
SENDGRID_API_KEY = get_secrets("SENDGRID_API_KEY", "sendgrid", "api_key")
SENDGRID_FROM_EMAIL = get_secrets("SENDGRID_FROM_EMAIL", "sendgrid", "from_email")

# Create OpenAI client
def get_openai_client():
    return OpenAI(api_key=OPENAI_API_KEY)

client = get_openai_client()


#-------------------------------------------------------------
#-------------------------------------------------------------
# 1C. OpenAI System Prompts 
# Defines the prompt for interaction with OpenAI LLM

system_prompt = """
You are a **virtual assistant for a real estate agent** handling inquiries about rental listings. Your job is to professionally engage prospective renters, gather the key information needed to determine if they qualify, and guide them toward confirming an exact showing date and time with a confirmed email address to send the invitation to.

## Core Goals
Every response you give must **simultaneously do both** of the following:
1. **Pre-qualify the user** — Collect the information necessary to determine if they meet the property’s requirements listed in the property details (e.g., move-in date, income, credit, pets, number of occupants, etc.), referring naturally to the listing details.
2. **Move the conversation closer to scheduling and confirming a showing with a user-provided email address** — Progress the discussion until the user provides and confirms a specific, exact date and time for the showing that works for them AND gives an email address to send a calendar invitation to.

## Conversation Style
- Write as a real leasing agent would text or chat — **warm, direct, and human**, without artificial cheerfulness or excessive enthusiasm.
- Keep sentences concise and natural.
- Never sound scripted, robotic, or overly formal.
- Ask max two or three questions per message, to move the conversation along naturally and swiftly. Keep messages clear, concise, and moving towards BOTH pre-qualification and a scheduled showing (including getting an email adress from the user).
- Be tactful but efficient — the goal is to save the user time while collecting what you need and locking in a showing time.

## Tone & Behavior
- Friendly, knowledgeable, and respectful. Warm and inviting, like a great customer service representative.
- Offer relevant details when asked, using the property information provided below.
- If a user doesn’t meet a requirement, politely acknowledge it and offer to connect them with other options.
- Always keep momentum — each message should bring the conversation one step closer to confirming a **concrete showing date and time and email address**.

## Example Conversations
**Example 1**
User: Hi, is this apartment still available?
Agent: Hello! Thank you for reaching out. Yes, the apartment is still available. If you wouldn't mind answering a few quick questions, I can get started on scheduling a showing. First, how many people do you plan to be moving in with?
User: It's just me and my partner
Agent: Great! That's perfect. Do you have any pets? The house allows pets, but only small ones under 20 pounds. Also, when during the week is easiest for you to schedule a showing?
User: We do not have any pets! We can make time during the week after 5 PM or on weekends in the mornings.
Agent: Perfect. We can do this Saturday at 10:00 AM if that works for you. Would you like to confirm that slot?
User: Yes, that time works for us!
Agent: Great! I just need an email address to send the calendar invitation over shortly
User: andreshoffman96@gmail.com

**Example 2**
User: Hello, I'd like to schedule a tour for this apartment.
Agent: Hello! That's great, I'm happy to help schedule a tour. I'll just have to ask a few quick questions to make sure it’s a good fit. When are you looking to move, and with how many people?
User: I’m looking to move around November 1st — it’d just be me.
Agent: Ok, that's perfect. Do you have any pets? The building allows cats but not dogs. Also, when works best in the coming week or so to schedule a showing?
User: I can do this Wednesday after work or Sunday morning
Agent: Ok, great. There's an opening this Wednesday at 7:00 PM, does that work for you? If you provide an email address I can send a calendar invitation over shortly. Also, I just need to confirm that you do not have a dog as the building does not allow dogs.
User: Wednesday at 7:00 PM works great! And I d onot have a dog
Agent: Amazing! If you could please provide me with an email address, I'll send the calendar invitation right over

## Scheduling Procedure
Once the user is confirmed to meet all criteria listed in the property details and expresses interest in touring:
1. Ask for their preferred times or general availability.
2. Propose an exact date(s) and time(s) which fits within their stated availability and confirm that they will tour during an agreed upon time
3. Keep the conversation going until they have clearly confirmed a specific date and time for a showing and provided an email address (e.g., "Yes, that time and day works, my email is isabella@hotmail.com" or "Yes, Wednesday at 7:00 PM works. Send to tomhoffman@yahoo.com")
3. Once an exact date and time and email address are confirmed, **end by thanking them and telling them that you will follow up shortly with a calendar invitation**

Example closing line:
> “Great. I've confirmed you for Monday at 6:30 PM — I’ll pass this along to the agent so they can send you a calendar invitation shortly.”

---

### Property Details Listed As Follows
"""

# Defines the prompt for a bot which classifies the conversation as having confirmed a time or not
classifier_prompt = """
You are a confirmation classifier for an apartment-rental chat. Your only job is to read the latest conversation transcript and decide whether the renter has fully confirmed a showing (date, time) and provided an email address so that an email calendar invite can be sent. Then output a single JSON object that matches the schema below—no prose, no extra keys, no trailing commas.

## What “confirmed” means (strict rules)

Return ready: true only if ALL of the following are true:
1. Specific time and day is agreed (e.g., “Tue Nov 4 at 3:00 PM”).
    - Accept short confirmations like “Yes, 3 PM next Tuesday works” only when they directly refer to a specific time and / or day proposed in the immediately preceding context.
    - Vague time (“tomorrow afternoon”, “around 5”) is not confirmed.
2. Explicit acceptance of the slot/time (e.g., “Perfect, confirm for me”, “See you then”, “Yes let’s lock 3 PM on Saturday”).
    - Negotiations, alternatives, “can we do 4 instead?”, “I’m free Tue or Wed”, “send me options” ⇒ not confirmed.
3. An email address is provided by the user (e.g., "andres@email.com", "you can send me the invite at andreshoffman96@gmail.com")
    - The email must appear in the conversation from the user and must look like a valid email address (i.e., text@domain.tld)
    - If no valid email is present, return ready: false.
    - If any of the above is missing (time, date, confirmation, email), return ready: false.

## Additional decision notes

If the user proposes a concrete slot/place but the agent has not acknowledged/accepted, it is not confirmed ⇒ ready: false with a reason.
If the user says “send the invite” but lacks a specific time and place, it is not confirmed.
If there is a conflict (multiple times mentioned without a clear final choice), it is not confirmed.
If a reschedule is requested or the user introduces uncertainty, it is not confirmed.

## Timezone and date handling

Use the conversation’s stated timezone if present.
Otherwise assume "America/New_York" as the default.
Use todays current date (provided further down below) to determine what date is being scheduled based on context, e.g., if the user says "Wednesday works great", assume they are referring to the first Wednesday following today's date
Output all datetimes in ISO 8601 with timezone offset, e.g., "2025-11-04T15:00:00-05:00".
If an end time is not explicitly provided but a duration is given (e.g., “30 minutes”), compute end_time_iso. Otherwise set end_time_iso as 30 minutes after the start time.

## Output schema (return this exact shape every time)
Return exactly one JSON object with these keys in this order. Use null when unknown/not applicable. Never omit keys.

{
"version": "1.0",
"ready": true|false,
"user_email": "string" | null,
"status": "confirmed" | "tentative" | "proposal" | "ambiguous" | "conflict" | "not_ready",
"today_date":  "YYYY-MM-DD" | null,
"start_time_iso": "YYYY-MM-DDTHH:MM:SS±HH:MM" | null,
"end_time_iso": "YYYY-MM-DDTHH:MM:SS±HH:MM" | null,
"timezone": "IANA/Zone" | null,
"location_text": "string" | null,
"notes": "short string" | null,
"confidence": 0.0–1.0,
"reason": "1–2 sentence explanation; must be present even when ready=true"
}

## Definitions to guide status:

"confirmed": user clearly accepts a specific time and place.
"tentative": specific slot suggested but user signals uncertainty (“probably”, “might”, “if”).
"proposal": user proposes a specific slot/place but hasn’t accepted one.
"ambiguous": time/place referenced vaguely (“tomorrow afternoon”, “there” without prior place).
"conflict": multiple competing times without a final single choice.
"not_ready": anything else that is clearly not ready.

## Style & constraints

Output strict JSON only. No Markdown, no commentary, no extra text.
Never fabricate dates, times, or places. Use null if missing.
Keep reason concise and factual, citing the exact phrase(s) you relied on.
Be conservative: when uncertain, prefer ready: false.

## Few-shot examples

Example A — Confirmed acceptance of proposed slot/place and email

INPUT (last messages summarized):
Agent: “Can you do Tue Nov 4 at 3:00 PM at 123 Main St, Boston (Leasing Office)?”
User: “Yes, that works. See you there.”
Agent: "Great, what's a good email for me to send a calendar invitation?"
User: "isabella.epshtein@gmail.com"

OUTPUT:
{
"version": "1.0",
"ready": true,
"user_email": "isabella.epshtein@gmail.com",
"status": "confirmed",
"today_date":  "2025-10-20",
"start_time_iso": "2025-11-04T15:00:00-05:00",
"end_time_iso": null,
"timezone": "America/New_York",
"location_text": "123 Main St, Boston (Leasing Office)",
"notes": "User explicitly accepted agent’s proposed time and place and provided an email address.",
"confidence": 0.97,
"reason": "User said 'Yes, that works. See you there' immediately after the agent proposed Tue Nov 4 3:00 PM at 123 Main St. User then provided an email address."
}

Example B — Vague time ⇒ not ready

INPUT:
User: “Tomorrow afternoon should be fine—can you send an invite?”

OUTPUT:
{
"version": "1.0",
"ready": false,
"user_email": null,
"status": "ambiguous",
"today_date":  "2025-01-01",
"start_time_iso": null,
"end_time_iso": null,
"timezone": "America/New_York",
"location_text": null,
"notes": "Vague ‘tomorrow afternoon’ and no email.",
"confidence": 0.95,
"reason": "Time is non-specific (‘tomorrow afternoon’). No email provided."
}

Example C — Proposal (user offers a concrete option, not yet accepted)

INPUT:
User: “How about Wed Nov 5 at 5:30 PM at the leasing office?”

OUTPUT:
{
"version": "1.0",
"ready": false,
"user_email": null,
"status": "proposal",
"today_date":  "2025-10-01",
"start_time_iso": "2025-11-05T17:30:00-05:00",
"end_time_iso": null,
"timezone": "America/New_York",
"location_text": "Leasing office",
"notes": "User proposed a slot; not yet accepted by agent.",
"confidence": 0.9,
"reason": "User suggested a specific time and date but no acceptance occurred."
}

Example D — Conflicting options

INPUT:
User: “I can do Tue 3 PM or Wed 5 PM. Which is better?”

OUTPUT:
{
"version": "1.0",
"ready": false,
"user_email": null,
"status": "conflict",
"today_date":  "2025-09-05",
"start_time_iso": null,
"end_time_iso": null,
"timezone": "America/New_York",
"location_text": null,
"notes": "Multiple candidate times; no single choice.",
"confidence": 0.92,
"reason": "Two different times mentioned without a final selection."
}

Example E — Email missing ⇒ not ready

INPUT:
User: “Let’s lock Mon at 10 AM. Send the invite.”

OUTPUT:
{
"version": "1.0",
"ready": false,
"user_email": null,
"status": "not_ready",
"today_date":  "2025-10-25",
"start_time_iso": "2025-11-03T10:00:00-05:00",
"end_time_iso": null,
"timezone": "America/New_York",
"location_text": null,
"notes": "Time set but no user email specified in thread.",
"confidence": 0.93,
"reason": "No email provided."
}

Example F — Confirmed with earlier place reference

INPUT:
Agent (earlier): “Showings are at 200 Boylston St, back entrance.”
Agent (later): “Does Thu Nov 6 at 2 PM work?”
User: “Perfect—see you then. Send to my email: andres.hoffman.pena@gmail.com”

OUTPUT:
{
"version": "1.0",
"ready": true,
"user_email": "andres.hoffman.pena@gmail.com",
"status": "confirmed",
"today_date":  "2025-10-01",
"start_time_iso": "2025-11-06T14:00:00-05:00",
"end_time_iso": null,
"timezone": "America/New_York",
"location_text": "200 Boylston St, back entrance",
"notes": "User accepted time; time and date were explicitly set earlier and not changed. User provided emal address",
"confidence": 0.94,
"reason": "User acceptance (‘Perfect—see you then’) refers to the latest proposed time and earlier specified location. User then explicitly provided an email address."
}

## Today's Date
Today's date is listed below. Use this to infer which days the user and agent are referring to when they don't give an explicit date.
"""


#-------------------------------------------------------------
#-------------------------------------------------------------
# 1D. Helpers
# Several helper functions to use later on

# Creates a variable to track whether an invite has been sent yet or not
invite_sent = False

# Creates a unique key for each listing to save chat history
def chat_key(listing_id: str) -> str:
    return f"chat_history_{listing_id}"

# Parses an ISO formatted string to UTC for creation of a calendar event
def parse_iso_to_utc(iso_str: str) -> datetime:
    dt = datetime.fromisoformat(iso_str)
    return dt.astimezone(timezone.utc)

# Helper for ics text escaping
def ics_escape(text: str | None) -> str:
    if not text:
        return ""
    return (text
            .replace("\\", "\\\\")   # backslash first
            .replace("\n", r"\n")
            .replace(",", r"\,")
            .replace(";", r"\;"))

# Creates a calendar event file for email sending
def make_ics_invite(
    start_time_iso: str,
    end_time_iso: str,
    *, # forces all inputs after the * to be keyword inputs
    title: str,
    organizer_email: str,
    attendee_email: str,
    location: str | None = None,
    description: str | None = None,
    default_minutes: int = 30) -> tuple[str, str]:
        # 1. Convert ISO times into UTC datetimes, using a thirty minute default length if none is provided
        start_utc = parse_iso_to_utc(start_time_iso)
        if end_time_iso:
            end_utc = parse_iso_to_utc(end_time_iso)
        else:
            end_utc = start_utc + timedelta(minutes = default_minutes)
        
        # 2. Formatting helper to format times the way ICS expects
        def fmt(dt: datetime) -> str:
            return dt.strftime("%Y%m%dT%H%M%SZ") # e.g., 20251104T200000Z
            
        # 3. Build the text of the ICS file
        uid = f"{uuid.uuid4()}@rental-responder" # a unique ID for the event
        summary = ics_escape(title)
        desc = ics_escape(description)
        loc = ics_escape(location)
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//RentalResponder//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:REQUEST",
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{fmt(datetime.now(timezone.utc))}",
            f"DTSTART:{fmt(start_utc)}",
            f"DTEND:{fmt(end_utc)}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{desc}",
            f"LOCATION:{loc}",
            f"ORGANIZER;CN=Leasing Agent:MAILTO:{organizer_email}",
            f"ATTENDEE;CN=Invitee;ROLE=REQ-PARTICIPANT;PARTSTAT=NEEDS-ACTION;RSVP=TRUE:MAILTO:{attendee_email}",
            "SEQUENCE:0",
            "STATUS:CONFIRMED",
            "TRANSP:OPAQUE",
            "END:VEVENT",
            "END:VCALENDAR"
        ]
        
        ics = "\r\n".join(lines)
        
        # 4. Create a nice file name
        filename = f"showing_{start_utc.strftime('%Y%m%dT%H%M')}.ics"
        
        return filename, ics

    
# Define the model to use from OpenAI and timezone of showings
model_name = "gpt-4.1"
default_tz = "America/New_York"

# Pull current date for scheduling classifier
today = str(date.today())

# Define default confirmation JSON as a fail safe for my classifier bot
DEFAULT_CONFIRMATION = {
    "version": "1.0",
    "ready": False,
    "user_email": None,
    "status": "not_ready",
    "today_date": today,
    "start_time_iso": None,
    "end_time_iso": None,
    "timezone": "America/New_York",
    "location_text": None,
    "notes": "classifier_default_fallback",
    "confidence": 0.0,
    "reason": "Fallback due to error or invalid/empty model response.",
}

# Creates a reply by calling OpenAI's API based on previously defined prompt
def generate_reply(user_message: str, history: list[dict], listing: dict) -> str:
    """
    Turns chat history of specific listing into an OpenAI chat request. 
    History is defined as st.session_state[key] list of {role, content} messages
    """
    try:
        # Keep the chat history and append the specific listing to the prompt
        recent = history
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": listing_fact_for_llm(listing)}
        ]
        messages.extend(recent)
        
        resp = client.chat.completions.create(
            model = model_name,
            messages = messages,
            temperature = 0.4,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        # Fail safe so that the app does not crash
        return ("Sorry, I'm having trouble connecting. Can you please try again in a moment?")

# Creates an ammendment to the OpenAI call with the information on the current listing
def listing_fact_for_llm(current_listing: dict) -> str:
    lines = [
        "Property Details:",
        f" - address: {current_listing['address']}",
        f" - allows pets: {current_listing['pets']}",
        f" - max number of tenants allowed: {current_listing['maxtenants']}",
        f" - preferred move in date: {current_listing['moveindate']}",
        f" - cash required at move: {current_listing['moveincost']}"
    ]
    return "\n".join(lines)


# Classifies the conversation as having a confirmed showing date and time or not
def classify_showing_confirmation(user_message: str, history: list[dict], listing: dict) -> dict:
    """
    Call the LLM to decide if the conversation has a fully-confirmed showing
    (date, time, place). Returns a strict dict that ALWAYS has the same keys.
    """
    recent = history

    messages = [
        {"role": "system", "content": classifier_prompt},
        {"role": "system", "Content": today}
    ]
    messages.extend(recent)

    try:
        resp = client.chat.completions.create(
            model = model_name,
            messages = messages,
            temperature = 0,  # classification -> keep deterministic
            # Force valid JSON output (supported chat models only)
            response_format={"type": "json_object"},
        )

        raw = (resp.choices[0].message.content or "").strip()

        # Parse JSON or fall back to default
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # If the model somehow violated JSON mode, fail safe:
            out = DEFAULT_CONFIRMATION.copy()
            out["notes"] = "classifier_json_parse_error"
            out["reason"] = f"Invalid JSON: {raw[:200]}"
            return out

        # Enforce schema completeness & types; fill any missing keys with defaults
        out = DEFAULT_CONFIRMATION.copy()
        out.update({
            "version": data.get("version", "1.0"),
            "ready": bool(data.get("ready", False)),
            "user_email": data.get("user_email"),
            "status": str(data.get("status", "not_ready")),
            "start_time_iso": data.get("start_time_iso"),
            "end_time_iso": data.get("end_time_iso"),
            "timezone": data.get("timezone", default_tz),
            "location_text": data.get("location_text"),
            "notes": data.get("notes"),
            "confidence": float(data.get("confidence", 0.0)),
            "reason": str(data.get("reason", "No reason provided.")),
        })
        return out

    except Exception as e:
        # Absolute fail-safe so your app never crashes
        out = DEFAULT_CONFIRMATION.copy()
        out["notes"] = "classifier_exception"
        out["reason"] = f"{type(e).__name__}: {str(e)[:200]}"
        return out


# Sends calendar invite by hitting SendGrid API
def send_email_sendgrid(
    *, # forces every input after to be a keyword input
    to_email: str,
    subject: str,
    body_text: str,
    ics_filename: str,
    ics_text: str,
    from_email: str) -> None:
        """
        Sends a plain text email with an ics calendar attachment via SendGrid
        Raises urllib.error.HTTPError on non-2xx responses
        """
        
        # 1. Endpoin and auth
        url = "https://api.sendgrid.com/v3/mail/send"
        headers = {
            "Authorization": f"Bearer {SENDGRID_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # 2. Build the JSON payload to sent to SendGrid
        payload = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": from_email},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body_text}],
            
            # 3. Attach the ics (base64 encoded)
            "attachments": [
                {
                    "content": base64.b64encode(ics_text.encode("utf-8")).decode("utf-8"),
                    "type": "text/calendar; method=REQUEST",
                    "filename": ics_filename,
                    "disposition": "attachment"
                }
            ],
        }
        
        # 4. Make the request
        req = urllib.request.Request(
            url = url,
            method = "POST",
            headers = headers,
            data = json.dumps(payload).encode("utf-8")
        )
        
        # 5. Send and surface any HTTP errors
        with urllib.request.urlopen(req) as resp:
            # SendGrid will typically return 202 on success
            if resp.status not in (200, 202):
                raise urllib.error.HTTPError(url, resp.status, "Unexpected Status", resp.headers, None)
            


#-------------------------------------------------------------
#-------------------------------------------------------------
# 2. CSS styles (visual design) 
# Uses CSS to specify certain style elements on top of Streamlit defaults.

st.markdown(
    """
    <style>
      .site-title {
        font-weight: 800; font-size: 32px; letter-spacing: 0.5px;
        margin: 0 0 8px 0; color: #1F2937;
      }
      .site-sub {
        color: #6B7280; margin-bottom: 24px;
      }
      .card {
        border: 1px solid #E5E7EB;
        border-radius: 16px;
        padding: 16px 16px 14px 16px;
        background: #FFFFFF;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
        height: 100%;
      }
      .addr { font-weight: 600; color: #1F2937; margin-bottom: 2px; }
      .neigh { color: #6B7280; margin-bottom: 10px; }
      .meta { display: flex; gap: 10px; color: #374151; margin-top: 8px; }
      .pill {
        display: inline-block; padding: 4px 10px; border-radius: 999px;
        background: #F3F4F6; color: #111827; font-size: 12px; font-weight: 600;
      }
      .price { font-size: 22px; font-weight: 800; color: #111827; }
      .divider { height: 1px; background: #F3F4F6; margin: 10px 0; }
      .btn {
        display: inline-block; text-align: center; padding: 10px 12px; width: 100%;
        border-radius: 10px; font-weight: 700; text-decoration: none;
        background: #1E3A8A; color: #FFFFFF !important;
      }
      .btn:hover { filter: brightness(1.05); color: #FFFFFF !important}
      .thumb {
        width: 100%; height: 160px; border-radius: 12px; object-fit: cover;
        background: #e9eef7;
      }
      @media (max-width: 900px) {
        .thumb { height: 140px; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)

#-------------------------------------------------------------
#-------------------------------------------------------------
# 3. Fake data 
# Creates dummy data to reference in page elements & code 
# This is a Python list of dictionaries. Scalable solution would be to replace this with a real table (e.g., Supabase or Postgres)

listings = [
  {
    "id": "medford-1a",
    "address": "105 Burget Ave",
    "neighborhood": "Medford",
    "rent": 3200,
    "beds": 2,
    "baths": 1,
    "pets": "yes",
    "maxtenants": 2,
    "moveindate": "09-01-2026",
    "moveincost": 6600,
    "img": "https://images.unsplash.com/photo-1501183638710-841dd1904471?q=80&w=1600&auto=format&fit=crop"
  },
  {
    "id": "southend-5",
    "address": "146 Warren Ave",
    "neighborhood": "South End",
    "rent": 4500,
    "beds": 2,
    "baths": 1,
    "pets": "yes",
    "maxtenants": 2,
    "moveindate": "09-01-2026",
    "moveincost": 13500,
    "img": "https://images.unsplash.com/photo-1494526585095-c41746248156?q=80&w=1600&auto=format&fit=crop"
  },
  {
    "id": "dedham-74",
    "address": "74 Martin Bates St",
    "neighborhood": "Dedham",
    "rent": 6000,
    "beds": 3,
    "baths": 4,
    "pets": "no",
    "maxtenants": 4,
    "moveindate": "01-01-2026",
    "moveincost": 18000,
    "img": "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?q=80&w=1600&auto=format&fit=crop"
  },
  {
    
    "id": "newton-85",
    "address": "85 Halcyon Rd",
    "neighborhood": "Newton",
    "rent": 5500,
    "beds": 3,
    "baths": 2,
    "pets": "no",
    "maxtenants": 4,
    "moveindate": "01-01-2026",
    "moveincost": 16500,
    "img": "https://images.unsplash.com/photo-1493809842364-78817add7ffb?q=80&w=1600&auto=format&fit=crop"
  },
]


#-------------------------------------------------------------
#-------------------------------------------------------------
# 4. "Routing" with query parameters
# Uses URL parameters to manually change what the page looks like. This is not ideal as Streamlit is not built for multi-page sites.
# New version of Streamlit has st.page feature which may work as a page router. Worth exploring instead of using URL parameters

params = st.query_params #creates a dictionary equal to the current URL parameters
current_page = params.get("page", "home") #gets the current page from URL parameters. If none, defaults to "home"
selected_id = params.get("id", None) #gets the current id from URL parameters. If non, defaults to "none"


#-------------------------------------------------------------
#-------------------------------------------------------------
# 5. Navigation helpers
# These mutate the URL query parameters and trigger Streamlit to re-run the script and render a different branch

def go_to_chat(lid):
  st.query_params["page"] = "chat"
  st.query_params["id"] = lid

def go_home():
  st.query_params.clear()


#-------------------------------------------------------------
#-------------------------------------------------------------
# 6. Card renderer
# A single funciton that takes a "row" (l) from "Listings" and renders the styled card. Uses configurations by class as defined in section 2 above.

def render_card(l):
    with st.container(border=False):
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<img class="thumb" src="{l["img"]}" alt="Listing photo">', unsafe_allow_html=True)
        st.markdown(f'<div class="addr">📍 {l["address"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="neigh">{l["neighborhood"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="price">${l["rent"]:,}/mo</div>', unsafe_allow_html=True)
        st.markdown('<div class="meta">🛏️ ' + str(l["beds"]) + ' bed &nbsp; • &nbsp; 🛁 ' + str(l["baths"]) + ' bath</div>', unsafe_allow_html=True)
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

        # Keep same blue button style (exact). This button is actually an HTML link to be able to format it in a custom way.
        st.markdown(
            f"""
            <a class="btn" href="?page=chat&id={l['id']}" target="_self">Chat about this listing</a>
            """,
            unsafe_allow_html=True
        )

        st.markdown('</div>', unsafe_allow_html=True)

#-------------------------------------------------------------
#-------------------------------------------------------------
# Side panel for de-gubbing and showing classifier output
with st.sidebar:
    st.checkbox("Show classifier debug", key="show_cls_debug", value=True)
    cls_panel = st.empty()  # we’ll fill this later

# Manual SendGrid test in sidebar to make sure plumbing works
with st.sidebar.expander("DEV - Send a test invite", expanded = False):
    test_email = st.text_input("Send test invite to", value = "", key = "sg_test_email")
    # Default to 10 minutes from now
    start_iso_default = (datetime.now(timezone.utc) + timedelta(minutes = 10)).astimezone().isoformat(timespec = "seconds")
    st.caption(f"Default start (editable in code): {start_iso_default}")
    
    if st.button("Send test invite now", key = "sg_test_send"):
        if not test_email:
            st.warning("Enter an email address first")
        else:
            # Build the ics
            ics_filename, ics_text = make_ics_invite(
                start_time_iso = start_iso_default,
                end_time_iso = None,
                title = "Test Showing",
                location = "123 Main St, Boston",
                description = "This is a test invitation to see if plumbing works",
                organizer_email = SENDGRID_FROM_EMAIL,
                attendee_email = test_email
            )
            # Send via SendGrid
            try:
                send_email_sendgrid(
                    to_email = test_email,
                    subject = "Test Invite - Andres App",
                    body_text = f"Your test showing is at {start_iso_default}",
                    ics_filename = ics_filename,
                    ics_text = ics_text,
                    from_email = SENDGRID_FROM_EMAIL
                )
                st.success("Sent! Check your inbox and open the .ics attachment")
            except Exception as e:
                st.error(f"Send failed: {type(e).__name__}: {str(e)[:300]}") 
 

#-------------------------------------------------------------
#-------------------------------------------------------------
# 7A. Home page
# Creates a 3-column grid, with two rows (top and bottom) each showing listings using render_card function defined above. Title and sub-title are HTML blocks styled by CSS

if current_page == "home":
    st.markdown('<div class="site-title">bostonrentals.com</div>', unsafe_allow_html=True)
    st.markdown('<div class="site-sub">Hand-picked apartments across Boston — mock demo</div>', unsafe_allow_html=True)

    cols_top = st.columns(3)
    for i, l in enumerate(listings[:3]):
        with cols_top[i]:
            render_card(l)

    cols_bottom = st.columns(3)
    for i, l in enumerate(listings[3:]):
        with cols_bottom[i]:
            render_card(l)

    st.caption(f"© {date.today().year} bostonrentals.com — mock UI for demo purposes only.")


#-------------------------------------------------------------
#-------------------------------------------------------------
# 7B. Chat page
# Creates a chat page based on the listing which is clicked

elif current_page == "chat" and selected_id: #if current_page = "chat" AND selected_id is not blank
    l = next((x for x in listings if x["id"] == selected_id), None) #takes first listing for which id = selected_id

    if st.button("⬅ Back to listings"): #creates the button which runs the go home function.
        go_home()
        st.rerun()

    if l: # Renders the current chat page based on the CSS defined in section 2 and the data from Listings.
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<img class="thumb" src="{l["img"]}" alt="Listing photo">', unsafe_allow_html=True)
        st.markdown(f'<div class="addr">📍 {l["address"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="neigh">{l["neighborhood"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="price">${l["rent"]:,}/mo</div>', unsafe_allow_html=True)
        st.markdown('<div class="meta">🛏️ ' + str(l["beds"]) + ' bed &nbsp; • &nbsp; 🛁 ' + str(l["baths"]) + ' bath</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("### Inquire about your listing")

        
        # Create a unique key for this listing's chat
        key = chat_key(l["id"])

        # Create a unique key for this chat's classifier result
        cls_key = f"{key}_classifier_result"
        if cls_key not in st.session_state:
            st.session_state[cls_key] = None

        # Create a per-chat flag for whether an invite send has been attempted
        invite_key = f"{key}_invite_sent"
        if invite_key not in st.session_state:
            st.session_state[invite_key] = False

        invite_status_key = f"{key}_invite_status"
        if invite_status_key not in st.session_state:
            st.session_state[invite_status_key] = None

        # If this is the first time opening this listing, start with a greeting message
        if key not in st.session_state:
            st.session_state[key] = [
                {
                    "role": "assistant",
                    "content": (
                        f"Hi! Thanks for your interest in **{l['address']}**.\n\n "
                        "Chat here to get started on scheduling a tour."
                    ),
                }
            ]

        # Show all messages as chat bubbles
        for msg in st.session_state[key]:
            #msg["role"] is either "assistant" or "user"
            with st.chat_message(msg["role"]):
                #msg["content"] is the text to display
                st.markdown(msg["content"])

        # Chat input at the bottom of the page
        user_msg = st.chat_input(placeholder = "Hi, I'm interested in this apartment!")

        # If the user types a message and hit enter
        if user_msg:
            # 1 - Save the user's message to history
            st.session_state[key].append({"role": "user", "content": user_msg})
            with st.chat_message("user"):
                st.markdown(user_msg)

            # 2 - Create the automatic reply & save to history
            assistant_reply = generate_reply(user_msg, st.session_state[key], l)
            st.session_state[key].append({"role": "assistant", "content": assistant_reply})

            # 3 - Run the classifier bot on the conversation to determine whether or not the user has confirmed a time
            try:
                cls_result = classify_showing_confirmation(user_msg, st.session_state[key], l)
            except Exception as e:
                cls_result = DEFAULT_CONFIRMATION
            
            st.session_state[cls_key] = cls_result

            # 4 - Immediately re-run so the new bubble appears above
            st.rerun()
            
        # Send the email invitation if user is ready
        result = st.session_state.get(cls_key)
        if result and (result.get("ready") is True) and (st.session_state[invite_key] is False):
            user_email = result.get("user_email")
            start_iso = result.get("start_time_iso")
            end_iso = result.get("end_time_iso")
            location = l["address"]
            tz = result.get("timezone")
            
            try:
                with st.spinner("Preparing and sending your calendar invite..."):
                    # Make the ics file
                    ics_filename, ics_text = make_ics_invite(
                        start_time_iso = start_iso,
                        end_time_iso = end_iso,
                        title = "Test showing",
                        organizer_email = SENDGRID_FROM_EMAIL,
                        attendee_email = user_email,
                        location = location,
                        description = "A calendar invite to demonstrate functionality"
                    )
                    # Trigger the email send
                    send_email_sendgrid(
                        to_email = user_email,
                        subject = "Test invite - Andres app",
                        body_text = f"Your showing starts at {start_iso}",
                        ics_filename = ics_filename,
                        ics_text = ics_text,
                        from_email = SENDGRID_FROM_EMAIL
                    )
                    
                st.success(f"Invite sent to {user_email}")
                st.session_state[invite_status_key] = f"Sent to {user_email}"
            except Exception as e:
                err = f"{type(e).__name__}: {str(e)[:300]}"
                st.error(f"Invite faled to send - {err}")
                st.session_state[invite_status_key] = f"Failed: {err}"
            finally:
                # Track that email has been sent
                st.session_state[invite_key] = True
        
        # Side panel to show classifier results
        if st.session_state.get("show_cls_debug", True):
            with st.sidebar.expander("Showing confirmation (debug)", expanded = True):
                latest = st.session_state.get(cls_key)
                if latest:
                    st.code(json.dumps(latest, indent = 2, ensure_ascii = False), language = "json")
                else:
                    st.caption("No classifier result yet.")
                    
            status = st.session_state.get(invite_status_key)
            if status:
                st.sidebar.caption(f"Invite status: {status}")




