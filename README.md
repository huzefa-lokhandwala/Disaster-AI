# ⛑️ DisasterPrep – Disaster Management Training Platform

> A full-stack hackathon project for schools and colleges to teach students how to respond during disasters through interactive learning, virtual drills, gamification, AI chatbot, and admin analytics.

![Python](https://img.shields.io/badge/Python-3.8+-blue) ![Flask](https://img.shields.io/badge/Flask-3.0-green) ![SQLite](https://img.shields.io/badge/Database-SQLite-orange) ![License](https://img.shields.io/badge/License-MIT-purple)

---

## 🚀 Quick Start

```bash
# 1. Clone / navigate to project
cd disasterprep

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Set up OpenAI API key
cp .env.example .env
# Edit .env and add: OPENAI_API_KEY=sk-...

# 5. Run the app
python app.py

# 6. Open browser → http://127.0.0.1:5000
```

---

## 🔐 Demo Accounts

| Role    | Email                       | Password   |
|---------|-----------------------------|------------|
| Admin   | admin@disasterprep.com      | admin123   |
| Student | Sign up at `/signup`        | any (6+ chars) |

---

## ✨ Features

### 🎓 Student Features
- **Dashboard** – Preparedness score dial, points, rank, badges, alerts
- **4 Learning Modules** – Earthquake, Fire, Flood, Cyclone
  - Before / During / After guides with 8 action items each
  - 5-question quiz with grading and points
- **🎯 Virtual Drill Simulation** *(star feature)*
  - Realistic scenario-based decisions with a countdown timer
  - Instant feedback: correct answers earn points, wrong choices deduct
  - 4 drill types: Earthquake (5 steps), Fire (3), Flood (3), Cyclone (3)
  - Final grade (A+/A/B/C/D) + score stored in database
- **🏆 Leaderboard** – Podium + full rankings table with "(You)" highlight
- **🔔 Alerts** – City-based emergency notifications with auto-refresh
- **🤖 AI Chatbot** – Rule-based + OpenAI fallback for disaster Q&A
- **📞 Emergency Contacts** – Clickable phone numbers by category
- **🎖️ Badges** – Earned by completing modules, drills, and reaching score thresholds

### ⚙️ Admin Features
- **Dashboard** – Total students, avg preparedness, drill participation stats
- **Analytics Charts** – Drill performance by disaster type (Doughnut), Daily signups (Line)
- **Send Alerts** – Target by city + severity (Info/Warning/Danger)
- **Top Students** – Podium display
- **User Table** – Searchable student list with points, modules, join date

---

## 📁 Project Structure

```
disasterprep/
├── app.py                 # All Flask routes and API endpoints
├── database.py            # SQLite schema, seeding, and helpers
├── requirements.txt
├── .env.example
├── disasterprep.db        # Auto-created on first run
├── static/
│   └── css/style.css      # Complete dark-mode design system
└── templates/
    ├── base.html          # Sidebar layout with mobile support
    ├── login.html         # Animated particles login
    ├── signup.html        # Registration with city/role
    ├── dashboard.html     # Student dashboard + Chart.js charts
    ├── modules.html       # Module cards grid
    ├── module_detail.html # Before/During/After tabs + quiz
    ├── drill.html         # ⭐ Interactive drill simulation
    ├── leaderboard.html   # Podium + rankings
    ├── alerts.html        # Emergency alert feed
    ├── contacts.html      # Emergency contacts by category
    ├── chatbot.html       # AI assistant chat UI
    └── admin.html         # Admin dashboard + charts + alert sender
```

---

## 🗄️ Database Schema

| Table             | Key Columns |
|-------------------|-------------|
| `users`           | id, name, email, password (hashed), role, city |
| `modules`         | id, title, disaster_type, content (JSON), points |
| `quiz_scores`     | user_id, module_id, score, total |
| `drill_scores`    | user_id, disaster_type, score, max_score, time_taken |
| `alerts`          | id, message, city, severity, created_at |
| `leaderboard`     | user_id, total_points |
| `emergency_contacts` | name, phone, category, icon |
| `user_modules`    | user_id, module_id, completed, points_earned |

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/signup` | Register new user |
| POST | `/api/login` | Authenticate user |
| GET  | `/api/me` | Current user info |
| GET  | `/api/dashboard` | Student dashboard data |
| GET  | `/api/modules` | All modules with completion status |
| GET  | `/api/modules/<id>` | Single module detail |
| GET  | `/api/quiz/<module_id>` | Quiz questions |
| POST | `/api/quiz/submit` | Submit quiz answers |
| GET  | `/api/drill/start/<type>` | Start a drill |
| POST | `/api/drill/submit` | Submit drill answers |
| GET  | `/api/leaderboard` | Rankings |
| GET  | `/api/alert/get` | Alerts for current user's city |
| POST | `/api/alert/send` | Admin: send alert |
| GET  | `/api/contacts` | Emergency contacts |
| POST | `/api/chatbot` | AI chatbot |
| GET  | `/api/admin/stats` | Admin analytics |
| GET  | `/api/admin/users` | All students |

---

## 🌐 Deployment

### Render / Railway (Recommended)
1. Push to GitHub
2. Connect repo to Render/Railway
3. Build command: `pip install -r requirements.txt`
4. Start command: `python app.py`
5. Environment variables: `SECRET_KEY`, `OPENAI_API_KEY`

### Heroku
```bash
echo "web: python app.py" > Procfile
heroku create disasterprep-app
heroku config:set SECRET_KEY=your-secret
git push heroku main
```

---

## 🤖 AI Chatbot

Works **without** an API key using built-in disaster knowledge for:
- Earthquake, Fire, Flood, Cyclone safety steps
- Emergency contact numbers
- Emergency kit contents

With `OPENAI_API_KEY` set in `.env`, it upgrades to GPT-3.5-turbo for open-ended questions.

---

## 🏆 Gamification System

| Action | Points Earned |
|--------|---------------|
| Quiz correct answer | +20 pts |
| Module completion (≥60%) | +150 pts |
| Drill correct action | +10 to +30 pts |
| Drill wrong action | -10 to -30 pts |

**Badges:**
- 🎓 First Module – Complete 1 module
- 🏆 All Modules – Complete all 4 modules
- ⛑️ Drill Survivor – Complete any drill
- ⭐ Point Master – Earn 500+ points
- 🦸 Prepared Hero – Reach 80%+ preparedness score

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python Flask 3.0 |
| Database | SQLite (via sqlite3) |
| Frontend | HTML5 + Vanilla CSS + JS |
| Charts | Chart.js 4.4 |
| Auth | Werkzeug password hashing |
| AI | Rule-based + OpenAI GPT-3.5 |
| Maps | Ready for Leaflet.js integration |
| Fonts | Google Fonts (Inter) |

---

*Built for hackathon – DisasterPrep helps schools build a culture of emergency preparedness.*
