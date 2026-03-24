import os, vertexai, json, requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # Added for Frontend support
from pydantic import BaseModel
from dotenv import load_dotenv
from vertexai.generative_models import GenerativeModel
from googleapiclient.discovery import build
from google.auth import default
from datetime import datetime, timedelta

load_dotenv()
PROJECT_ID = os.getenv("PROJECT_ID")
MAPS_KEY = os.getenv("MAPS_API_KEY")

vertexai.init(project=PROJECT_ID, location="us-central1")
app = FastAPI()

# --- NEW: Add CORS Middleware (Essential for building a UI) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

model = GenerativeModel(
    os.getenv("MODEL"),
    system_instruction=[
        "You are an Executive Assistant AI. Convert text into a JSON list.",
        "Types: 'task' (reminders), 'location' (finding places), 'event' (meetings/appointments).",
        "If it's an 'event', try to extract a 'time' field. Output ONLY raw JSON."
    ]
)

class UserInput(BaseModel):
    input: str

# --- Maps Tool ---
def search_places_new(query):
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": MAPS_KEY,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress"
    }
    data = {"textQuery": query, "maxResultCount": 1}
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        results = response.json().get("places", [])
        if results:
            p = results[0]
            return f"📍 FOUND: {p['displayName']['text']} at {p['formattedAddress']}"
    return f"📍 MAPS: No results for '{query}'"

# --- Tasks Tool ---
def create_google_task(title):
    try:
        creds, _ = default()
        service = build('tasks', 'v1', credentials=creds)
        service.tasks().insert(tasklist='@default', body={'title': title}).execute()
        return f"✅ TASK CREATED: '{title}'"
    except Exception as e: return f"❌ TASK FAILED: {str(e)}"

# --- NEW: Calendar Tool ---
def create_calendar_event(summary):
    try:
        creds, _ = default()
        service = build('calendar', 'v3', credentials=creds)
        start = datetime.utcnow().isoformat() + 'Z' # Default to now for demo
        end = (datetime.utcnow() + timedelta(hours=1)).isoformat() + 'Z'
        event = {
            'summary': summary,
            'start': {'dateTime': start},
            'end': {'dateTime': end},
        }
        service.events().insert(calendarId='primary', body=event).execute()
        return f"📅 CALENDAR: Event '{summary}' scheduled for now."
    except Exception as e: return f"❌ CALENDAR FAILED: {str(e)}"

@app.post("/execute")
async def execute(request: UserInput):
    try:
        ai_resp = model.generate_content(request.input)
        clean_json = ai_resp.text.replace("```json", "").replace("```", "").strip()
        intents = json.loads(clean_json)

        execution_log = []
        for item in intents:
            desc = item.get("description", "")
            itype = item.get("type", "task")

            if itype == "location" or "find" in desc.lower():
                execution_log.append(search_places_new(desc))
            elif itype == "event" or "meet" in desc.lower():
                execution_log.append(create_calendar_event(desc))
            else:
                execution_log.append(create_google_task(desc))

        return {"intents": intents, "execution_log": execution_log}
    except Exception as e:
        return {"status": "error", "message": str(e)}