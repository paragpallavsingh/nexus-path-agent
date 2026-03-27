# 🧭 Nexus-Path: Multi-Agent AI Orchestrator

**Nexus-Path** is a production-grade AI agent system that transforms natural language into actionable spatial, temporal, and task-based data. Built for the **Hack2Skill Google Cloud Hackathon**, it leverages Gemini 2.5 Flash to coordinate a swarm of specialized sub-agents.

## 🚀 Live Demo
**URL:** [https://nexus-path-agent-327842541443.us-central1.run.app/](https://nexus-path-agent-327842541443.us-central1.run.app/)

## 🧠 Architecture: The "Nexus" Pattern
Nexus-Path uses a **Manager-Worker** architecture. The Primary Agent (Gemini) performs **Intent Decomposition**, breaking down a single user query into three distinct dimensions:
* 📍 **Spatial (Researcher Agent):** Fetches real-time location data and deep links via Google Places API.
* 📅 **Temporal (Scheduler Agent):** Generates ISO-8601 timestamps for calendar integration.
* ✅ **Actionable (Coordinator Agent):** Extracts granular, atomic tasks for checklist management.



## 🛠️ Tech Stack
* **Orchestration:** Gemini 2.5 Flash (Vertex AI SDK)
* **Backend:** FastAPI (Python 3.11)
* **Database:** Google AlloyDB (PostgreSQL)
* **Compute:** Google Cloud Run (Serverless)
* **Networking:** Direct VPC Egress for secure, private database communication.

## 🔒 Security & Infrastructure
* **Private Networking:** The system uses a dedicated VPC with a private subnet. Cloud Run communicates with AlloyDB over a private Google network, ensuring no database traffic is exposed to the public internet.
* **Stateful Persistence:** Unlike stateless chatbots, every "thought" and "intent" is logged into AlloyDB as a `JSONB` object, providing a durable audit trail of the AI's reasoning.

## 🎯 Example "Stress Test" Query
> *"Plan a full day in Delhi for next Tuesday: Start with breakfast at Saravana Bhavan CP at 9 AM, then head to Chandni Chowk for sightseeing, and finally meet a friend at India Gate at 6 PM. Remind me to carry my power bank."*

**The Result:** 9 parallel actions triggered across 3 sub-agents, validated timestamps, and structured logging in AlloyDB.

## 📈 Database Schema
```sql
CREATE TABLE scholar_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_query TEXT,
    agent_thoughts TEXT,
    executed_intents JSONB
);
```