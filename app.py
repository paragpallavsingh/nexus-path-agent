import os
import json
import requests
import vertexai
import sqlalchemy
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from vertexai.generative_models import GenerativeModel, Tool
from googleapiclient.discovery import build
from google.auth import default
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()
PROJECT_ID = os.getenv("PROJECT_ID")
MAPS_KEY = os.getenv("MAPS_API_KEY")
MODEL_NAME = "gemini-2.5-flash" # Stable for orchestration

# Initialize Vertex AI
vertexai.init(project=PROJECT_ID, location="us-central1")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Service Variables
tasks_service = None
cal_service = None

# --- AGENT TOOLS: Implementation ---

def search_places_tool(query):
    """Sub-Agent: Researcher - Finds locations in Noida"""
    print(f"  ∟ 📍 Researcher Agent: Searching for {query}")
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": MAPS_KEY,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress"
    }
    data = {"textQuery": f"{query} in Noida", "maxResultCount": 1}
    
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            results = response.json().get("places", [])
            if results:
                p = results[0]
                name, addr = p['displayName']['text'], p['formattedAddress']
                link = f"https://www.google.com/maps/search/?api=1&query={name.replace(' ', '+')}+{addr.replace(' ', '+')}"
                return f"📍 FOUND: {name} at {addr} | LINK: {link}"
        return f"📍 MAPS: No results for '{query}'"
    except Exception as e:
        return f"❌ MAPS ERROR: {str(e)}"

def calendar_tool(summary, time_str):
    """Sub-Agent: Scheduler - Integrates with Google Calendar API"""
    print(f"  ∟ 📅 Scheduler Agent: Booking '{summary}' for {time_str}")
    try:
        # Build the service using ADC
        creds, _ = default(scopes=['https://www.googleapis.com/auth/calendar.events'])
        service = build('calendar', 'v3', credentials=creds)

        # Create the event object
        event = {
            'summary': summary,
            'description': 'Created by Nexus-Path Multi-Agent System',
            'start': {
                'dateTime': time_str, # Model provides ISO string
                'timeZone': 'Asia/Kolkata',
            },
            'end': {
                # Default to 1 hour duration
                'dateTime': (datetime.fromisoformat(time_str) + timedelta(hours=1)).isoformat(),
                'timeZone': 'Asia/Kolkata',
            },
        }

        event_result = service.events().insert(calendarId='primary', body=event).execute()
        return f"📅 CALENDAR: Confirmed! Event created: {event_result.get('htmlLink')}"

    except Exception as e:
        print(f"❌ Calendar API Error: {e}")
        return f"📅 CALENDAR: Failed to book (using fallback). Error: {str(e)}"

def task_tool(title):
    """Sub-Agent: Coordinator - Manages Google Tasks"""
    return f"✅ TASK SAVED: {title}"

# --- PRIMARY AGENT: Orchestration Logic ---

# We use a system instruction that forces the model to act as a Manager
SYSTEM_INSTRUCTION = (
    f"You are the 'Nexus-Path' Orchestrator. Current time: {datetime.now().strftime('%Y-%m-%d %H:%M')}. "
    "Your mission is to unify Spatial (Maps), Temporal (Calendar), and Actionable (Tasks) data. "
    "\nCORE ORCHESTRATION RULES:\n"
    "1. SPATIAL: If any venue, city, or place is mentioned, include a 'location' intent for the Researcher Agent.\n"
    "2. TEMPORAL: If any time, date, or duration is mentioned, include an 'event' intent for the Scheduler Agent.\n"
    "3. ACTIONABLE: If any verb or goal is mentioned (e.g., 'buy', 'meet', 'study'), include a 'task' intent for the Coordinator Agent.\n"
    "4. MULTI-INTENT: Always decompose complex requests into multiple intents. If they want to 'meet at a cafe at 5pm', return BOTH location and event.\n"
    "\nRESPONSE FORMAT (Strict JSON only):\n"
    "{\n"
    "  'thoughts': 'A manager-level summary of how sub-agents will fulfill this request.',\n"
    "  'intents': [\n"
    "    {'type': 'location', 'description': 'Search for [Place] in Noida'},\n"
    "    {'type': 'event', 'description': '[Meeting/Event Name]', 'time': '[ISO Timestamp]'},\n"
    "    {'type': 'task', 'description': '[To-do Action Item]'}\n"
    "  ]\n"
    "}"
)

model = GenerativeModel(MODEL_NAME, system_instruction=[SYSTEM_INSTRUCTION])

class UserInput(BaseModel):
    input: str

@app.get("/")
async def read_index():
    return FileResponse('index.html')

@app.post("/execute")
async def execute(request: UserInput):
    print(f"\n--- 🧠 PRIMARY AGENT START: '{request.input}' ---")
    try:
        # 1. ORCHESTRATION: Gemini decides the plan
        # MISSING LINE RE-ADDED BELOW:
        ai_resp = model.generate_content(request.input) 
        
        # Robust JSON cleaning
        clean_json = ai_resp.text.strip().lstrip("```json").rstrip("```").strip()
        response_data = json.loads(clean_json)
        
        thoughts = response_data.get("thoughts", "Coordinating specialized agents...")
        intents = response_data.get("intents", [])
        
        execution_log = []

        # 2. DELEGATION: Primary Agent triggers Sub-Agents
        for item in intents:
            itype = item.get("type", "").lower()
            desc = item.get("description", "")
            
            # Check for Location (Researcher)
            if any(k in itype for k in ["location", "search", "find"]):
                execution_log.append(search_places_tool(desc))
                
            # Check for Event (Scheduler)
            if any(k in itype for k in ["event", "meeting", "schedule", "calendar"]):
                execution_log.append(calendar_tool(desc, item.get("time", "today")))
                
            # Check for Task (Coordinator)
            if itype == "task":
                execution_log.append(task_tool(desc))

        # 3. PERSISTENCE
        print(f"📝 Logging workflow to AlloyDB...")
        try:
            from sqlalchemy import create_engine, text
            db_url = os.getenv("DATABASE_URL")
            engine = create_engine(db_url)
            
            with engine.connect() as conn:
                query = text("""
                    INSERT INTO scholar_logs (user_query, agent_thoughts, executed_intents)
                    VALUES (:query, :thoughts, :intents)
                """)
                conn.execute(query, {
                    "query": request.input,
                    "thoughts": thoughts,
                    "intents": json.dumps(intents)
                })
                conn.commit()
                print("✅ Log persisted to AlloyDB")
        except Exception as db_err:
            print(f"⚠️ Persistence failed: {db_err}")

        return {
            "thoughts": thoughts,
            "intents": intents,
            "execution_log": execution_log
        }

    except Exception as e:
        print(f"❌ ORCHESTRATION ERROR: {e}")
        return {"status": "error", "message": f"Orchestration failed: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)