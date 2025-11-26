# SG Car Advisor
AI-Powered Smart Car Recommender for Singapore Drivers  
Built with Groq LLMs, Flask, DuckDB, and SGCarMart Data

---

## Overview

SG Car Advisor is an AI-driven web application that helps Singapore car buyers make smarter car-purchase decisions.

Users simply answer 5 to 6 natural-language questions. The system then:

- Understands the user's needs via conversational Q&A  
- Infers buying intent (budget, family size, driving pattern, new/used preference, etc.)  
- Searches a curated DuckDB dataset of SGCarMart listings  
- Computes a Value Score for each car  
- Generates a personalised AI explanation for the top picks  
- Adds the AI explanation directly into each recommendation card  

---

## Key Features

### 1. Conversational Q&A Flow (Groq Llama-3.1)
- Adaptive question flow with a maximum of 5 questions  
- Learns budget, usage, family size, preferences  
- Produces a user profile summary

### 2. Rule-Based Inference Engine
Extracts information from free-text answers:
- Budget extraction (100k, 80-120k, 120000)  
- Family size parsing  
- Condition preference (used/new)  
- Body type suitability  
- Driving environment classification  

### 3. DuckDB Search Engine
Embedded SQL engine containing SGCarMart listings:
- Make, model, variant  
- Price  
- Mileage  
- COE years left  
- Efficiency  
- Dealer details  
- Filters by price, year, mileage, and condition  

### 4. Value Score Model
Each car gets a Value Score (0 to 100) based on:
- Depreciation per year  
- Mileage vs age  
- Remaining COE  
- Brand and reliability heuristics  
- Weighted scoring model  

### 5. AI Recommendation Explanations
- Explains why each car fits the user  
- Considers preferences, trade-offs and caveats  
- Generated using Groq Llama-3.1  

### 6. Flask Web Application
Pages included:
- /                   Start  
- /questions          Conversational Q&A  
- /recommendations    Car results with value scoring  
- /car/<id>           Full listing details  

---

## Architecture Diagram

```
User
  |
  v
Flask UI
  |
  v
Q&A Engine (LLM)
  |
  v
User Profile (structured fields)
  |
  v
Rule-Based Inference
  |
  v
DuckDB Filtering
  |
  v
Value Score Model
  |
  v
LLM Explanation Engine
  |
  v
Final Recommendations UI
```

---

## Project Structure

```
01_Final_project/
├── app.py
├── cars.duckdb
│
├── llm.py
├── llm_summary.py
├── question_llm.py
├── profile_llm.py
├── db_search.py
├── value_model.py
├── value_score.py
│
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── questions.html
│   ├── recommendations.html
│   └── result.html
```

---

## Installation

### Step 1: Clone the project
```
git clone <repo_url>
cd sg-car-advisor
```

### Step 2: Create a virtual environment
```
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install dependencies
```
pip install -r requirements.txt
```

### Step 4: Add API key
Create a .env file:

```
GROQ_API_KEY=your_api_key_here
```

### Step 5: Run the application
```
python app.py
```

Open http://127.0.0.1:5000/

---

## User Guide

### Step 1: Start Q&A
The app asks up to 5 adaptive questions about:
- Budget  
- Family size  
- Driving condition  
- Car purpose  
- Preferences  

### Step 2: Summary  
The system summarises the user's needs.

### Step 3: Recommendations  
The app presents:
- Top cars that fit the filters  
- Value Scores  
- Price, mileage, depreciation  
- AI-generated reasons  
- Links to actual SGCarMart listings  

---

## Recommendation Logic

### Input
- Natural language answers from user

### Processing
- Q&A modeled through Groq Llama-3.1  
- Rule-based parsers for budget, family size, driving pattern  
- Search filters converted into SQL  

### Output
- Ranked recommendations  
- Value Scores  
- AI explanations  

---

## Why This Project Is Unique

- Fast inference using Groq compute  
- Hybrid system: rule-based + AI-based  
- Singapore-specific logic (COE, depreciation, SGCarMart)  
- Transparent scoring  
- Personalized explanations  

---

## Roadmap

- Real-time SGCarMart scraping  
- Fuel cost simulation  
- Performance benchmarking  
- Multi-model LLM options  
- Mobile-responsive UI  


