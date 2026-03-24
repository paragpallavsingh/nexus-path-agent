import os
import vertexai
import json
import googlemaps
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from vertexai.generative_models import GenerativeModel

load_dotenv()
vertexai.init(project=os.getenv("PROJECT_ID"), location="us-central1")
app = FastAPI()
gmaps = googlemaps.Client(key=os.getenv("MAPS_API_KEY")) if os.getenv("MAPS_API_KEY") else None

model = GenerativeModel(
    os.getenv("MODEL"),
    system_instruction=[
        "You are the 'Intent Agent'. Convert text into a JSON list.",
        "CRITICAL: If the user wants to find a place, restaurant, or shop, use type: 'location'.",
        "Types: task, event, location. Output ONLY raw JSON."
    ]
)

class UserInput(BaseModel):
    input: str

@app.post("/execute")
async def execute(request: UserInput):
    try:
        response = model.generate_content(request.input)
        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        intents = json.loads(clean_json)

        execution_log = []
        for item in intents:
            desc = item.get("description", "").lower()
            intent_type = item.get("type", "task")

            # SMART LOGIC: Force location if 'find' or 'place' is in description
            if "find" in desc or "place" in desc or intent_type == "location":
                if gmaps:
                    # Search for the place
                    places_result = gmaps.places(query=item.get("description"))
                    results = places_result.get('results', [])
                    if results:
                        place = results[0]
                        name = place.get('name')
                        vicinity = place.get('formatted_address', 'Noida')
                        # ADDING A MAPS LINK
                        map_url = f"https://www.google.com/maps/search/?api=1&query={name.replace(' ', '+')}"
                        execution_log.append(f"📍 FOUND: {name} in {vicinity}. View: {map_url}")
                    else:
                        execution_log.append(f"📍 MAPS: No momo spots found for '{desc}'")
                else:
                    execution_log.append(f"📍 SIMULATED: Finding momos in Noida...")
            
            elif intent_type == "event":
                execution_log.append(f"📅 Event Scheduled: {item.get('description')}")
            else:
                execution_log.append(f"✅ Task Saved: {item.get('description')}")

        return {"intents": intents, "execution_log": execution_log}
    except Exception as e:
        return {"status": "error", "message": str(e)}