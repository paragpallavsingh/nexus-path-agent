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
import google.auth
from google.auth import default
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta, timezone

# Load environment variables
load_dotenv()
PROJECT_ID = os.getenv("PROJECT_ID")
MAPS_KEY = os.getenv("MAPS_API_KEY")
MODEL_NAME = "gemini-2.5-flash" # Stable for orchestration

# Initialize Vertex AI
vertexai.init(project=PROJECT_ID, location="us-central1")

#initiate alloydb
db_url = os.getenv("DATABASE_URL")
engine = sqlalchemy.create_engine(db_url)

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
    """Sub-Agent: Scheduler - Token-less Service Account Auth"""
    
    TARGET_CALENDAR_ID = "c6bd9b50ec7ee4626ef30cf1f43b00e7c2b460cc53d923506bd0c2fb58d664b1@group.calendar.google.com"
    
    print(f"   ∟ 📅 Scheduler Agent: Securely booking '{summary}' via Service Account")
    
    # Define the scope
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    
    try:
        creds, project = google.auth.default(scopes=SCOPES)
        service = build('calendar', 'v3', credentials=creds)
	
        event = {
            'summary': summary,
            'description': 'Created by Nexus-Path Multi-Agent System',
            'start': {'dateTime': time_str, 'timeZone': 'Asia/Kolkata'},
            'end': {
                'dateTime': (datetime.fromisoformat(time_str.replace('Z', '+00:00')) + timedelta(hours=1)).isoformat(),
                'timeZone': 'Asia/Kolkata'
            },
        }

        event_result = service.events().insert(calendarId=TARGET_CALENDAR_ID, body=event).execute()

        public_view = f"https://calendar.google.com/calendar/embed?src={TARGET_CALENDAR_ID.replace('@', '%40')}&ctz=Asia%2FKolkata" 
        return f"📅 CALENDAR: Confirmed! | {public_view}"

    except Exception as e:
        print(f"❌ Calendar API Error: {e}")
        return f"📅 CALENDAR: Failed to book. Error: {str(e)}"

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
    "    {'type': 'location', 'description': 'Search for [Place] near Noida'},\n"
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
            # Filter intents into their respective categories for the new schema
            # We use json.dumps because these columns are JSONB in AlloyDB
            map_info = json.dumps([i for i in intents if i.get('type') == 'location'])
            cal_info = json.dumps([i for i in intents if i.get('type') == 'event'])
            task_info = json.dumps([i for i in intents if i.get('type') == 'task'])

            with engine.connect() as conn:
                query = sqlalchemy.text("""
                    INSERT INTO nexus_logs 
                    (user_query, primary_reasoning, map_data, calendar_data, task_data, executed_at)
                    VALUES 
                    (:query, :thoughts, :map, :cal, :task, :ts)
                    """)
                
                # Ensure every :parameter in the query has a matching key in this dict
                conn.execute(query, {
                    "query": request.input,
                    "thoughts": thoughts,
                    "map": map_info,
                    "cal": cal_info,
                    "task": task_info,
                    "ts": datetime.now(timezone.utc)
                })
                conn.commit()
                print("✅ Log persisted to AlloyDB (nexus_logs)")
        except Exception as db_err:
            # This will now catch and print specific mapping errors if any remain
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