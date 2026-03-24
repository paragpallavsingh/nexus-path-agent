import os
import vertexai
import json
import requests  # Use requests instead of the googlemaps library
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from vertexai.generative_models import GenerativeModel

load_dotenv()
PROJECT_ID = os.getenv("PROJECT_ID")
MAPS_KEY = os.getenv("MAPS_API_KEY")

vertexai.init(project=PROJECT_ID, location="us-central1")
app = FastAPI()

model = GenerativeModel(
    os.getenv("MODEL"),
    system_instruction=["Convert text to JSON list. Types: task, event, location. Output ONLY raw JSON."]
)

class UserInput(BaseModel):
    input: str

def search_places_new(query):
    """Calling the Places API (New) with Field Masking to save credits."""
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
            place = results[0]
            name = place.get("displayName", {}).get("text", "Unknown")
            addr = place.get("formattedAddress", "No address")
            return f"📍 FOUND: {name} at {addr}"
    return f"📍 MAPS: Could not find '{query}'"

@app.post("/execute")
async def execute(request: UserInput):
    try:
        ai_resp = model.generate_content(request.input)
        clean_json = ai_resp.text.replace("```json", "").replace("```", "").strip()
        intents = json.loads(clean_json)

        execution_log = []
        for item in intents:
            desc = item.get("description", "")
            # Smart trigger for Location
            if item.get("type") == "location" or "find" in desc.lower():
                execution_log.append(search_places_new(desc))
            elif item.get("type") == "event":
                execution_log.append(f"📅 Event: {desc}")
            else:
                execution_log.append(f"✅ Task: {desc}")

        return {"intents": intents, "execution_log": execution_log}
    except Exception as e:
        return {"status": "error", "message": str(e)}