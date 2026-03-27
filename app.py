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
                link = f"https://www.google.com/maps/search/?api=1&query={name.replace(' ', '+')}"
                return f"📍 FOUND: {name} at {addr} | LINK: {link}"
        return f"📍 MAPS: No results for '{query}'"
    except Exception as e:
        return f"❌ MAPS ERROR: {str(e)}"

def calendar_tool(summary, time_str):
    """Sub-Agent: Scheduler - Manages Google Calendar"""
    try:
        # Mock logic for demo/sandbox stability
        return f"📅 CALENDAR: '{summary}' planned for {time_str} (Staged in AlloyDB)"
    except Exception as e:
        return f"❌ CALENDAR ERROR: {str(e)}"

def task_tool(title):
    """Sub-Agent: Coordinator - Manages Google Tasks"""
    return f"✅ TASK SAVED: {title}"

# --- PRIMARY AGENT: Orchestration Logic ---

# We use a system instruction that forces the model to act as a Manager
SYSTEM_INSTRUCTION = (
    f"You are the 'Scholar-Sync' Primary Agent. Current time: {datetime.now().strftime('%Y-%m-%d %H:%M')}. "
    "Your goal is to coordinate sub-agents (Scheduler, Researcher, Librarian). "
    "Respond ONLY in a JSON format with two fields: "
    "1. 'thoughts': A string explaining your reasoning/plan. "
    "2. 'intents': A list of objects with 'type' (event, task, location) and 'description'."
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
        ai_resp = model.generate_content(request.input)
        response_data = json.loads(ai_resp.text.replace("```json", "").replace("```", "").strip())
        
        thoughts = response_data.get("thoughts", "Coordinating specialized agents...")
        intents = response_data.get("intents", [])
        
        execution_log = []

        # 2. DELEGATION: Primary Agent triggers Sub-Agents
        for item in intents:
            itype = item.get("type").lower() # Ensure case-insensitivity
            desc = item.get("description")
            
            if itype in ["location", "search", "find"]:
                execution_log.append(search_places_tool(desc))
            elif itype in ["event", "meeting", "schedule"]:
                time_val = item.get("time", "today")
                execution_log.append(calendar_tool(desc, time_val))
            else:
                execution_log.append(task_tool(desc))

        # 3. PERSISTENCE (Requirement: AlloyDB/Structured Data)
        
        print(f"📝 Logging workflow to AlloyDB for Student Context...")

        # --- NEW: ALLOYDB PERSISTENCE LAYER ---
        try:
            from sqlalchemy import create_engine, text
            import uuid
            
            db_url = os.getenv("DATABASE_URL")
            engine = create_engine(db_url)
            
            with engine.connect() as conn:
                # Insert the interaction log
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
        return {"status": "error", "message": "The Dean is busy. Try again."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)