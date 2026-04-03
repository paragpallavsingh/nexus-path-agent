# 🧭 Nexus-Path: Multi-Agent AI Orchestrator

**Nexus-Path** is a production-grade AI agent system that transforms natural language into actionable spatial, temporal, and task-based data. Built for the **Hack2Skill Google Cloud Hackathon**, it leverages Gemini 2.5 Flash to coordinate a swarm of specialized sub-agents.

## 🚀 Live Demo
**Production URL:** [https://nexus-path-secure-agent-327842541443.us-central1.run.app/](https://nexus-path-secure-agent-327842541443.us-central1.run.app/)

## 🧠 Architecture: The "Nexus" Pattern
Nexus-Path uses a **Manager-Worker** architecture. The Primary Agent (Gemini) performs **Intent Decomposition**, breaking down a single user query into three distinct dimensions:
* 📍 **Spatial (Researcher Agent):** Fetches real-time location data and deep links via Google Places API.
* 📅 **Temporal (Scheduler Agent):** Seamlessly books events into a dedicated Sandbox Calendar.
* ✅ **Actionable (Coordinator Agent):** Extracts granular, atomic tasks for workflow management.



## 🛠️ Tech Stack
* **Orchestration:** Gemini 2.5 Flash (Vertex AI SDK)
* **Backend:** FastAPI (Python 3.12)
* **Frontend:** Tailwind CSS & JavaScript (Real-time Iframe Integration)
* **Database:** Google AlloyDB (PostgreSQL)
* **Compute:** Google Cloud Run (Serverless)
* **Networking:** Direct VPC Egress for secure, private database communication.

## 🔒 Security & Infrastructure
* **Token-less Authentication:** The system utilizes **GCP Workload Identity**. By running under a specific Service Account (`nexus-calendar-sa`), the app communicates with Vertex AI and Google Calendar APIs without storing sensitive `client_secret.json` or `token.json` files in the container.
* **Private Networking:** Cloud Run communicates with AlloyDB over a **Private VPC Network** (`easy-alloydb-vpc`), ensuring database traffic never touches the public internet.
* **Stateful Persistence:** Every "thought" and "intent" is logged into AlloyDB as a `JSONB` object, providing a durable, queryable audit trail of the AI's reasoning process.

## 📊 Live Monitoring
The UI features a **Real-Time Agent Schedule Widget**, a public embed of the Service Account's sandbox calendar. This allows users to see the agent's scheduled actions update instantly as it "thinks" and "executes."

## 🎯 Example "Stress Test" Query
> *"Plan to go to Mall Road Shimla on 5th April at 12 PM. Remind me to pack warm clothes."*

**The Result:** 1. **Researcher:** Finds the exact coordinates for Mall Road, Shimla.
2. **Scheduler:** Pins the event to the Nexus-Path Sandbox Calendar.
3. **Coordinator:** Saves "Pack warm clothes" as an actionable task.
4. **AlloyDB:** Records the full JSON intent-tree for later analysis.

## 📈 Database Schema
```sql
CREATE TABLE scholar_logs (
    id SERIAL PRIMARY KEY,
    log_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_query TEXT,
    agent_thoughts TEXT,
    executed_intents JSONB
);
