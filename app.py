import os
import vertexai
import json
import googlemaps
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from vertexai.generative_models import GenerativeModel

# 1. Setup & Config
load_dotenv()
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION", "us-central1")
MODEL_ID = os.getenv("MODEL")
MAPS_KEY = os.getenv("MAPS_API_KEY")

vertexai.init(project=PROJECT_ID, location=LOCATION)
app = FastAPI()

# Initialize Maps Client (Only if Key is present)
gmaps = googlemaps.Client(key=MAPS_KEY) if MAPS_KEY else None

model = GenerativeModel(
    MODEL_ID,
    system_instruction=[
        "You are the 'Intent Agent'. Convert text into a JSON list.",
        "Types: task, event, location. Output ONLY raw JSON.",
        "Include keys: 'type' and 'description'."
    ]
)

# 2. Data Model
class UserInput(BaseModel):
    input: str

# 3. API Routes
@app.get("/")
def home():
    return {"status": "online", "project": "Intent-Execution-AI"}

@app.post("/execute")
async def execute(request: UserInput):
    try:
        response = model.generate_content(request.input)

        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        intents = json.loads(clean_json)

        execution_log = []
        
        for item in intents:
            desc = item.get("description", "No description")
            
            if item.get("type") == "location":
                if gmaps:
                    # REAL CALL: Using 'places' for high accuracy
                    # We limit results to 1 to save credits
                    places_result = gmaps.places(query=desc)
                    results = places_result.get('results', [])
                    if results:
                        place = results[0]
                        name = place.get('name')
                        addr = place.get('formatted_address')
                        execution_log.append(f"📍 REAL MAPS: Found {name} at {addr}")
                    else:
                        execution_log.append(f"📍 MAPS: No results found for {desc}")
                else:
                    execution_log.append(f"📍 SIMULATED: Found {desc} (Missing API Key)")
            
            elif item.get("type") == "event":
                execution_log.append(f"📅 Scheduled: {desc}")
                
            else:
                execution_log.append(f"✅ Task: {desc}")

        return {"intents": intents, "execution_log": execution_log}
    except Exception as e:
        return {"status": "error", "message": str(e)}
