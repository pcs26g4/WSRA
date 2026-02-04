# WSRA - Web Security Reconnaissance Agent

WSRA is an advanced, autonomous web security reconnaissance and vulnerability scanning agent. It uses a multi-agent architecture to crawl, map, analyze, and identify potential security vulnerabilities in modern web applications (including SPAs).

## Features

- **Orchestration**: Centralized control of the crawl frontier and task dispatching.
- **Crawling**: Playwright-based crawler capable of handling standard web pages and Single Page Applications (SPAs).
- **Mapping**: Automatically discovers and categorizes API endpoints, static assets, and application features.
- **Vulnerability Hinting**: A rule-based engine (`VulnHinter`) that analyzes data patterns to suggest high-probability manual testing targets (XSS, SSRF, LFI, etc.).
- **JavaScript Analysis**: Static analysis of JavaScript files to identify dangerous sinks and user-controlled sources.
- **Interaction**: Automatically clicks buttons, submits forms, and exploring dynamic states.
- **Form Analysis**: Detects and attempts to fill forms to discover functional flows.
- **Reporting**: Generates JSON, Markdown, CSV, and Burp Suite (XML) reports for diverse consumption needs.
- **Dashboard**: Real-time React-based dashboard to monitor scan progress and view findings.

## Architecture

The system consists of a Python FastAPI backend and a React frontend.

### Backend Agents (~/backend/agents)
1.  **Orchestrator**: The central brain that manages the crawl frontier, dispatching tasks to other agents.
2.  **Crawler**: Fetches pages and extracts DOM content.
3.  **Mapper**: Analyzes URL structures and sitemaps.
4.  **JS Analyzer**: Parses JavaScript ASTs to find security flaws.
5.  **Vulnerability Hinter**: Correlates data from other agents to hypothesis vulnerabilities.
6.  **Interaction Agent**: Explores "clickable" elements to find new states.
7.  **Network Monitor**: Captures and analyzes all HTTP traffic.
8.  **Form Filling**: Handles form submission logic.


## Project Structure

WSRA/
├── backend/                     # Python FastAPI Backend
│   ├── agents/                    # Autonomous Agents
│   │   ├── js_parser/               # Node.js AST Analysis tools
│   |   |   └── ast_analysis.js        # JS parser
│   │   ├── crawler.py               # Playwright crawler
│   │   ├── form_filling.py          # Form filling agent
│   │   ├── interaction_agent.py     # Interaction agent
│   │   ├── js_analyzer.py           # JS analyzer
│   │   ├── mapper.py                # Mapper
│   │   ├── network_monitor.py       # Network monitor
│   │   ├── orchestrator.py          # Main logic controller
│   │   └── vuln_hinter.py           # Vulnerability & Hinting engine
│   ├── api/                       # REST API Endpoints
|   |   ├── routes/                  # API Routes
|   |   |   ├── exports.py             # Export Endpoints
|   |   |   ├── scan.py                # Scan Endpoints
|   |   |   ├── summary.py             # Summary Endpoints
|   |   |   ├── utilities.py           # Utilities Endpoints
|   |   |   └── vuln_hinter.py         # Vulnerability & Hinting Endpoints
|   |   ├── main.py                  # API Entry Point
|   |   └── models.py                # API Models
|   ├── config/                    # API Configuration
|   |   |   ├── settings.py          # API Settings
|   ├── database/                  # Database Configuration
|   |   |   ├── connection.py        # Database Connection
|   |   |   └── models.py            # Database Models
│   ├── exports/                   # Export generated reports
|   |   ├── burp_exporter.py         # Burp Exporter
|   |   └── report_generator.py      # Report Generator(csv,json,md)
│   ├── llm/                       # LLM Configuration
│   |   ├── gemini_client.py         # Gemini Client
│   |   └── policy.py                # Policy
│   └── main.py                    # Application Entry Point
│   └── requirements.txt           # Application Dependencies
│   └── reset_db.py                # Reset Database
│
├── frontend/                    # React Dashboard
│   ├── src/
│   │   ├── components/            # UI Components
|   |   |   ├── layout/              # Layout Components (Navbar, AppShell)
|   |   |   └── scan/                # Scan Components
|   |   ├── lib/                   # Library Components
|   |   ├── pages/                 # Route Pages
|   |   |   ├── Dashboard.jsx
|   |   |   ├── ScanDetails.jsx
|   |   |   ├── History.jsx
|   |   |   └── Landing.jsx          # LandingPage
│   │   └── api.js                 # API Client


## Frontend (~/frontend)
- **Tech Stack**: React, Vite, TailwindCSS, Framer Motion.
---

## Prerequisites

- **Python**: 3.8+
- **Node.js**: 16+ (for Frontend & JS parsing fallback)
- **PostgreSQL**: Local or Cloud (e.g., Supabase)

## Installation

### 1. Backend Setup

```bash
cd backend

# Create virtual environment (Recommended)
python -m venv venv
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install JS Analyzer dependencies (Required for JS Agent)
cd agents/js_parser
npm install
cd ../../..

#Run the backend
uvicorn main:app
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

#Run the frontend
npm run dev
```


## Configuration

1.  Create a `.env` file in the **root directory** of the project.
2.  Add the following configuration (replace placeholders):

```env
# AI & LLM Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Database Configuration (PostgreSQL)
# Format: postgresql://user:password@host:port/dbname
DATABASE_URL=postgresql://postgres:password@localhost:5432/wsra

# Browser Configuration
HEADLESS=False  # Set to True for production/servers
```

## Usage

### 1. Start the Backend API

```bash
# From the project root
python backend/main.py
```
The API will start at `http://0.0.0.0:8000`.

### 2. Start the Frontend Dashboard

```bash
cd frontend
npm run dev
```
Access the dashboard at `http://localhost:5173`.

### 3. Running a Scan
1.  Open the Dashboard.
2.  Enter a target URL (e.g., `https://example.com`) or select a previous scan.
3.  Watch as the agents autonomously explore the target.
4.  View results and findings in real-time under the "Vulnerabilities" and "Attack Surface" tabs.

## Exports

WSRA supports multiple export formats:
- **JSON**: Full machine-readable scan data.
- **Markdown**: Human-readable summary and findings.
- **CSV**: Parameter and endpoint inventory.
- **Burp Suite XML**: Importable issues file for Burp Suite Professional/Community.

## Contributing

This project uses a modular agentic architecture. To add a new capability:
1.  Create a new agent class in `backend/agents/`.
2.  Register the agent in `backend/agents/orchestrator.py`.
3.  Update the database models if necessary.
