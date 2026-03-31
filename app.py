import os, json, re
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db, init_db
from dotenv import load_dotenv
import requests as http_requests

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'disasterprep-secret-key-2024')

# ─────────────────────────────────────────────
# Auth helpers
# ─────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

# ─────────────────────────────────────────────
# Page routes
# ─────────────────────────────────────────────
@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/signup', methods=['GET'])
def signup():
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/modules')
@login_required
def modules():
    return render_template('modules.html')

@app.route('/modules/<int:module_id>')
@login_required
def module_detail(module_id):
    return render_template('module_detail.html', module_id=module_id)

@app.route('/drill')
@login_required
def drill():
    return render_template('drill.html')

@app.route('/leaderboard')
@login_required
def leaderboard_page():
    return render_template('leaderboard.html')

@app.route('/alerts')
@login_required
def alerts_page():
    return render_template('alerts.html')

@app.route('/contacts')
@login_required
def contacts():
    return render_template('contacts.html')

@app.route('/chatbot')
@login_required
def chatbot():
    return render_template('chatbot.html')

@app.route('/admin')
@admin_required
def admin_dashboard():
    return render_template('admin.html')

# ─────────────────────────────────────────────
# API – Auth
# ─────────────────────────────────────────────
@app.route('/api/signup', methods=['POST'])
def api_signup():
    data = request.get_json()
    name  = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    pwd   = data.get('password', '')
    city  = data.get('city', 'Mumbai')
    role  = data.get('role', 'student')

    if not all([name, email, pwd]):
        return jsonify({'error': 'All fields required'}), 400

    db = get_db()
    try:
        hashed = generate_password_hash(pwd)
        db.execute(
            "INSERT INTO users (name, email, password, role, city) VALUES (?,?,?,?,?)",
            (name, email, hashed, role, city)
        )
        db.commit()
        user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        db.execute("INSERT OR IGNORE INTO leaderboard (user_id, total_points) VALUES (?,?)", (user['id'], 0))
        db.commit()
        session['user_id'] = user['id']
        session['name'] = user['name']
        session['email'] = user['email']
        session['role'] = user['role']
        session['city'] = user['city']
        return jsonify({'success': True, 'role': role})
    except Exception as e:
        return jsonify({'error': 'Email already exists'}), 409
    finally:
        db.close()

@app.route('/api/login', methods=['POST'])
def api_login():
    data  = request.get_json()
    email = data.get('email', '').strip().lower()
    pwd   = data.get('password', '')

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    db.close()

    if not user or not check_password_hash(user['password'], pwd):
        return jsonify({'error': 'Invalid credentials'}), 401

    session['user_id'] = user['id']
    session['name']    = user['name']
    session['email']   = user['email']
    session['role']    = user['role']
    session['city']    = user['city']
    return jsonify({'success': True, 'role': user['role']})

@app.route('/api/me')
@login_required
def api_me():
    return jsonify({
        'id':    session['user_id'],
        'name':  session['name'],
        'email': session['email'],
        'role':  session['role'],
        'city':  session['city'],
    })

# ─────────────────────────────────────────────
# API – Dashboard
# ─────────────────────────────────────────────
@app.route('/api/dashboard')
@login_required
def api_dashboard():
    uid = session['user_id']
    db  = get_db()

    # Modules completed
    mods_done = db.execute(
        "SELECT COUNT(*) as cnt FROM user_modules WHERE user_id=? AND completed=1", (uid,)
    ).fetchone()['cnt']

    # Quiz scores avg
    quiz_avg = db.execute(
        "SELECT AVG(CAST(score AS FLOAT)/total*100) as avg FROM quiz_scores WHERE user_id=?", (uid,)
    ).fetchone()['avg'] or 0

    # Drill scores
    drills = db.execute(
        "SELECT * FROM drill_scores WHERE user_id=? ORDER BY created_at DESC LIMIT 5", (uid,)
    ).fetchall()

    # Leaderboard position
    lb = db.execute(
        "SELECT total_points FROM leaderboard WHERE user_id=?", (uid,)
    ).fetchone()
    total_points = lb['total_points'] if lb else 0

    rank_row = db.execute(
        "SELECT COUNT(*) as cnt FROM leaderboard WHERE total_points > ?", (total_points,)
    ).fetchone()
    rank = rank_row['cnt'] + 1

    # Preparedness score: weighted combo
    mod_score   = min(mods_done * 25, 100)
    quiz_score  = min(quiz_avg, 100)
    drill_score = 0
    if drills:
        avg_drill = sum((d['score'] / max(d['max_score'], 1)) * 100 for d in drills) / len(drills)
        drill_score = min(avg_drill, 100)
    preparedness = int(0.4 * mod_score + 0.35 * quiz_score + 0.25 * drill_score)

    # Badges
    badges = []
    if mods_done >= 1: badges.append({'name': 'First Module', 'icon': '🎓', 'color': '#4CAF50'})
    if mods_done >= 4: badges.append({'name': 'All Modules', 'icon': '🏆', 'color': '#FFD700'})
    if drills:         badges.append({'name': 'Drill Survivor', 'icon': '⛑️', 'color': '#2196F3'})
    if total_points >= 500: badges.append({'name': 'Point Master', 'icon': '⭐', 'color': '#FF9800'})
    if preparedness >= 80:  badges.append({'name': 'Prepared Hero', 'icon': '🦸', 'color': '#9C27B0'})

    # Alerts for city
    city = session.get('city', 'All')
    alerts = db.execute(
        "SELECT * FROM alerts WHERE city=? OR city='All' ORDER BY created_at DESC LIMIT 3",
        (city,)
    ).fetchall()

    # Recent drill scores for chart
    drill_chart = [{'type': d['disaster_type'], 'score': d['score'], 'max': d['max_score']} for d in drills]

    db.close()
    return jsonify({
        'name': session['name'],
        'city': session.get('city', 'Mumbai'),
        'preparedness': preparedness,
        'modules_completed': mods_done,
        'total_modules': 4,
        'total_points': total_points,
        'rank': rank,
        'badges': badges,
        'alerts': [dict(a) for a in alerts],
        'drill_scores': drill_chart,
        'quiz_avg': round(quiz_avg, 1),
    })

# ─────────────────────────────────────────────
# API – Modules
# ─────────────────────────────────────────────
@app.route('/api/modules')
@login_required
def api_modules():
    uid = session['user_id']
    db  = get_db()
    mods = db.execute("SELECT * FROM modules").fetchall()
    result = []
    for m in mods:
        completed = db.execute(
            "SELECT completed, points_earned FROM user_modules WHERE user_id=? AND module_id=?",
            (uid, m['id'])
        ).fetchone()
        result.append({
            **dict(m),
            'completed': completed['completed'] if completed else 0,
            'points_earned': completed['points_earned'] if completed else 0,
        })
    db.close()
    return jsonify(result)

@app.route('/api/modules/<int:mid>')
@login_required
def api_module_detail(mid):
    uid = session['user_id']
    db  = get_db()
    m = db.execute("SELECT * FROM modules WHERE id=?", (mid,)).fetchone()
    if not m:
        db.close()
        return jsonify({'error': 'Not found'}), 404
    completed_row = db.execute(
        "SELECT completed, points_earned FROM user_modules WHERE user_id=? AND module_id=?",
        (uid, mid)
    ).fetchone()
    db.close()
    return jsonify({
        **dict(m),
        'content': json.loads(m['content']),
        'completed': completed_row['completed'] if completed_row else 0,
        'points_earned': completed_row['points_earned'] if completed_row else 0,
    })

# ─────────────────────────────────────────────
# API – Quiz
# ─────────────────────────────────────────────
QUIZZES = {
    1: [  # Earthquake
        {"q": "What is the first action during an earthquake?", "opts": ["Run outside", "Hide under a table", "Use the elevator", "Call friends"], "ans": 1},
        {"q": "What should you grab in an earthquake kit?", "opts": ["TV remote", "Water and food supplies", "Extra clothes only", "Gaming console"], "ans": 1},
        {"q": "Where is the safest spot during an earthquake indoors?", "opts": ["Near a window", "In an elevator", "Under a sturdy table", "On the roof"], "ans": 2},
        {"q": "After an earthquake, what should you check first?", "opts": ["Social media updates", "Gas leaks and injuries", "Damage to furniture", "Electricity supply"], "ans": 1},
        {"q": "What does 'Drop, Cover, Hold On' mean?", "opts": ["Dance move", "Earthquake response technique", "Sports drill", "Fire drill step"], "ans": 1},
    ],
    2: [  # Fire
        {"q": "What number do you call for fire emergency in India?", "opts": ["100", "108", "101", "112"], "ans": 2},
        {"q": "During a fire, you should:", "opts": ["Use the elevator", "Crawl low under smoke", "Open all windows", "Hide in a cupboard"], "ans": 1},
        {"q": "Before opening a door during fire, you should:", "opts": ["Open it quickly", "Feel it for heat first", "Knock and wait", "Break it down"], "ans": 1},
        {"q": "How often should smoke alarms be tested?", "opts": ["Yearly", "Never", "Monthly", "Daily"], "ans": 2},
        {"q": "If your clothes catch fire, you should:", "opts": ["Run for help", "Stop, Drop, and Roll", "Jump in water", "Fan the flames"], "ans": 1},
    ],
    3: [  # Flood
        {"q": "During a flood, you should avoid:", "opts": ["Moving to higher ground", "Walking in moving water", "Following evacuation orders", "Emergency kits"], "ans": 1},
        {"q": "Why is floodwater dangerous even after flooding?", "opts": ["It's cold", "It may be contaminated", "It's too clean", "It evaporates fast"], "ans": 1},
        {"q": "What does 'Turn Around, Don't Drown' mean?", "opts": ["U-turn driving technique", "Don't drive through flooded roads", "Swimming technique", "Evacuation slogan"], "ans": 1},
        {"q": "Before a flood, you should move valuables:", "opts": ["To the basement", "To higher floors", "Outside the house", "Leave them"], "ans": 1},
        {"q": "What should you do with food after flooding?", "opts": ["Eat it quickly", "Check if it still looks good", "Discard it if it contacted floodwater", "Freeze it"], "ans": 2},
    ],
    4: [  # Cyclone
        {"q": "During a cyclone, the safest place is:", "opts": ["Near windows", "On the roof", "Interior room on lowest floor", "In the car"], "ans": 2},
        {"q": "The 'eye' of a cyclone is:", "opts": ["The most dangerous part", "A brief calm—but storm will return", "A safe zone", "A cloud formation"], "ans": 1},
        {"q": "Before a cyclone, windows should be:", "opts": ["Opened for airflow", "Boarded up", "Cracked open", "Cleaned"], "ans": 1},
        {"q": "During a cyclone, generators should be used:", "opts": ["Inside for safety", "Outdoors only", "In the basement", "Never"], "ans": 1},
        {"q": "After a cyclone, you should watch out for:", "opts": ["Sunny skies", "Downed power lines", "Traffic jams", "Food shortages only"], "ans": 1},
    ],
}

@app.route('/api/quiz/<int:module_id>')
@login_required
def api_get_quiz(module_id):
    if module_id not in QUIZZES:
        return jsonify({'error': 'Quiz not found'}), 404
    # Return without answers
    questions = [{'q': q['q'], 'opts': q['opts']} for q in QUIZZES[module_id]]
    return jsonify({'module_id': module_id, 'questions': questions})

@app.route('/api/quiz/submit', methods=['POST'])
@login_required
def api_quiz_submit():
    data      = request.get_json()
    module_id = data.get('module_id')
    answers   = data.get('answers', [])  # list of selected option indices
    uid       = session['user_id']

    if module_id not in QUIZZES:
        return jsonify({'error': 'Invalid module'}), 400

    quiz    = QUIZZES[module_id]
    correct = sum(1 for i, q in enumerate(quiz) if i < len(answers) and answers[i] == q['ans'])
    total   = len(quiz)

    db = get_db()
    db.execute(
        "INSERT INTO quiz_scores (user_id, module_id, score, total) VALUES (?,?,?,?)",
        (uid, module_id, correct, total)
    )

    # Points: 20 pts per correct answer
    pts = correct * 20
    mod = db.execute("SELECT points FROM modules WHERE id=?", (module_id,)).fetchone()
    module_pts = mod['points'] if mod else 0

    # Mark module completed if score >= 60%
    passed = correct / total >= 0.6
    total_pts = pts
    if passed:
        total_pts += module_pts
        existing = db.execute(
            "SELECT id FROM user_modules WHERE user_id=? AND module_id=?", (uid, module_id)
        ).fetchone()
        if existing:
            db.execute(
                "UPDATE user_modules SET completed=1, points_earned=?, completed_at=CURRENT_TIMESTAMP WHERE user_id=? AND module_id=?",
                (total_pts, uid, module_id)
            )
        else:
            db.execute(
                "INSERT INTO user_modules (user_id, module_id, completed, points_earned, completed_at) VALUES (?,?,1,?,CURRENT_TIMESTAMP)",
                (uid, module_id, total_pts)
            )
        # Update leaderboard
        db.execute(
            "INSERT INTO leaderboard (user_id, total_points) VALUES (?,?) ON CONFLICT(user_id) DO UPDATE SET total_points=total_points+?",
            (uid, total_pts, total_pts)
        )

    db.commit()
    db.close()

    return jsonify({
        'correct': correct,
        'total': total,
        'points_earned': total_pts,
        'passed': passed,
        'percentage': round(correct / total * 100),
    })

# ─────────────────────────────────────────────
# API – Drills
# ─────────────────────────────────────────────
DRILLS = {
    'earthquake': {
        'title': '🌍 Earthquake Drill',
        'intro': 'The ground starts shaking violently! Buildings rattle and glass shatters around you.',
        'steps': [
            {
                'id': 1,
                'scenario': '⚡ SHAKING STARTS – You feel the ground moving violently while you are at your desk.',
                'question': 'What is your FIRST action?',
                'options': [
                    {'text': 'Run outside immediately', 'points': -20, 'correct': False, 'feedback': '❌ Running outside during shaking is dangerous – debris may fall on you!'},
                    {'text': 'Drop, Cover under desk, Hold On', 'points': 30, 'correct': True, 'feedback': '✅ Perfect! Drop, Cover, Hold On is the correct earthquake response!'},
                    {'text': 'Use the elevator to get to ground floor', 'points': -30, 'correct': False, 'feedback': '❌ Never use an elevator during an earthquake – you could get trapped!'},
                    {'text': 'Stand near the window to look outside', 'points': -20, 'correct': False, 'feedback': '❌ Standing near windows is very dangerous – glass may shatter!'},
                ],
            },
            {
                'id': 2,
                'scenario': '🏫 INSIDE A MULTI-STORY BUILDING – The shaking intensifies. You are on the 3rd floor.',
                'question': 'Where do you take cover?',
                'options': [
                    {'text': 'Corner of the room', 'points': 5, 'correct': False, 'feedback': '⚠️ Corners aren\'t as safe as under sturdy furniture.'},
                    {'text': 'Under a sturdy table or desk', 'points': 30, 'correct': True, 'feedback': '✅ Excellent! A sturdy table provides protection from falling objects!'},
                    {'text': 'In the doorway', 'points': 5, 'correct': False, 'feedback': '⚠️ The doorway myth is outdated – under a table is safer.'},
                    {'text': 'Next to an interior wall', 'points': 10, 'correct': False, 'feedback': '⚠️ Interior walls are okay but sturdy furniture is better.'},
                ],
            },
            {
                'id': 3,
                'scenario': '⏹️ SHAKING STOPS – The earthquake has ended but you smell gas.',
                'question': 'What do you do?',
                'options': [
                    {'text': 'Turn on lights to check for damage', 'points': -30, 'correct': False, 'feedback': '❌ Electrical switches can spark and ignite gas – very dangerous!'},
                    {'text': 'Evacuate and do not use any switches', 'points': 30, 'correct': True, 'feedback': '✅ Correct! Leave immediately, don\'t touch switches, and call gas company!'},
                    {'text': 'Open windows and continue staying inside', 'points': -10, 'correct': False, 'feedback': '❌ You should evacuate immediately when you smell gas!'},
                    {'text': 'Call friends to tell them about the earthquake', 'points': -20, 'correct': False, 'feedback': '❌ Priority is your safety first – evacuate immediately!'},
                ],
            },
            {
                'id': 4,
                'scenario': '🏥 AFTERSHOCK – A strong aftershock hits while you are outside.',
                'question': 'What do you do?',
                'options': [
                    {'text': 'Run back inside the building', 'points': -20, 'correct': False, 'feedback': '❌ Never run into a building during an aftershock – it may be unstable!'},
                    {'text': 'Move away from buildings, drop and cover', 'points': 30, 'correct': True, 'feedback': '✅ Perfect! Stay in open areas away from buildings and cover your head!'},
                    {'text': 'Lie flat on the ground anywhere', 'points': 10, 'correct': False, 'feedback': '⚠️ Better to move away from hazards first, then drop and cover.'},
                    {'text': 'Use your phone to record the aftershock', 'points': -15, 'correct': False, 'feedback': '❌ Your safety is the priority, not recording!'},
                ],
            },
            {
                'id': 5,
                'scenario': '📡 AFTER THE DISASTER – You need to communicate with your family.',
                'question': 'What is the best way to communicate post-earthquake?',
                'options': [
                    {'text': 'Make multiple phone calls repeatedly', 'points': -10, 'correct': False, 'feedback': '⚠️ Calling repeatedly blocks emergency lines for others.'},
                    {'text': 'Send text messages instead of calling', 'points': 30, 'correct': True, 'feedback': '✅ Correct! Texts use less bandwidth and keep emergency lines free!'},
                    {'text': 'Use social media only', 'points': 5, 'correct': False, 'feedback': '⚠️ Social media can help but text messages are more reliable.'},
                    {'text': 'Do not communicate at all', 'points': -20, 'correct': False, 'feedback': '❌ You should communicate through appropriate channels.'},
                ],
            },
        ]
    },
    'fire': {
        'title': '🔥 Fire Emergency Drill',
        'intro': 'You smell smoke and see flames in the hallway of your school building!',
        'steps': [
            {
                'id': 1,
                'scenario': '🔔 FIRE DETECTED – You smell smoke coming from the hallway.',
                'question': 'What is your FIRST action?',
                'options': [
                    {'text': 'Open the door to see what\'s happening', 'points': -20, 'correct': False, 'feedback': '❌ Never open a door without checking if it\'s hot – fire may be on the other side!'},
                    {'text': 'Activate fire alarm and call 101', 'points': 30, 'correct': True, 'feedback': '✅ Correct! Always alert others and call fire services first!'},
                    {'text': 'Pack your belongings before leaving', 'points': -25, 'correct': False, 'feedback': '❌ Your life is more important than belongings! Leave immediately!'},
                    {'text': 'Hide under your desk', 'points': -15, 'correct': False, 'feedback': '❌ Hiding delays evacuation – you need to get out!'},
                ],
            },
            {
                'id': 2,
                'scenario': '💨 SMOKE-FILLED CORRIDOR – You need to exit through a smoky hallway.',
                'question': 'How do you move through the smoke?',
                'options': [
                    {'text': 'Run upright as fast as possible', 'points': -20, 'correct': False, 'feedback': '❌ Smoke rises – running upright exposes you to more smoke and heat!'},
                    {'text': 'Crawl low, covering mouth and nose', 'points': 30, 'correct': True, 'feedback': '✅ Perfect! Crawling keeps you below the smoke level!'},
                    {'text': 'Hold your breath and sprint through', 'points': -5, 'correct': False, 'feedback': '⚠️ Holding breath helps briefly but crawling is safer.'},
                    {'text': 'Wait for smoke to clear', 'points': -25, 'correct': False, 'feedback': '❌ Smoke is deadly – you must evacuate immediately!'},
                ],
            },
            {
                'id': 3,
                'scenario': '🚪 CLOSED DOOR – You reach a closed door. You need to check if it\'s safe.',
                'question': 'What do you do before opening the door?',
                'options': [
                    {'text': 'Open it quickly and look inside', 'points': -20, 'correct': False, 'feedback': '❌ Opening without checking could release fire and smoke directly!'},
                    {'text': 'Feel the door and handle for heat', 'points': 30, 'correct': True, 'feedback': '✅ Always feel the door for heat before opening – if hot, use another exit!'},
                    {'text': 'Knock and wait for reply', 'points': -5, 'correct': False, 'feedback': '⚠️ Knocking won\'t tell you if fire is behind the door.'},
                    {'text': 'Break the door down immediately', 'points': -10, 'correct': False, 'feedback': '❌ Breaking down could expose you to fire if it\'s behind the door.'},
                ],
            },
        ]
    },
    'flood': {
        'title': '🌊 Flood Emergency Drill',
        'intro': 'Heavy rains have caused flash flooding in your area. Water levels are rising fast!',
        'steps': [
            {
                'id': 1,
                'scenario': '💧 RISING WATER – Flash flood warning issued. Water entering ground floor.',
                'question': 'What is your first action?',
                'options': [
                    {'text': 'Stay and watch water levels', 'points': -20, 'correct': False, 'feedback': '❌ Do not wait – flash floods rise extremely rapidly!'},
                    {'text': 'Move to higher floors immediately', 'points': 30, 'correct': True, 'feedback': '✅ Correct! Moving to higher ground is the priority!'},
                    {'text': 'Drive away from the area', 'points': -10, 'correct': False, 'feedback': '⚠️ Driving through floodwater is very dangerous – never do this.'},
                    {'text': 'Open windows for ventilation', 'points': -5, 'correct': False, 'feedback': '❌ This won\'t help and wastes valuable time.'},
                ],
            },
            {
                'id': 2,
                'scenario': '🚗 FLOODED ROAD – You\'re in a car and see a flooded road ahead.',
                'question': 'What do you do?',
                'options': [
                    {'text': 'Drive through slowly', 'points': -30, 'correct': False, 'feedback': '❌ NEVER drive through floodwater! Even 15cm can sweep a car away!'},
                    {'text': 'Turn around and find alternate route', 'points': 30, 'correct': True, 'feedback': '✅ Turn Around, Don\'t Drown! This is the correct response!'},
                    {'text': 'Park and wait for water to recede', 'points': 5, 'correct': False, 'feedback': '⚠️ Better to move to higher ground rather than staying in the low area.'},
                    {'text': 'Speed through to get past it quickly', 'points': -30, 'correct': False, 'feedback': '❌ Speeding through floodwater is extremely dangerous!'},
                ],
            },
            {
                'id': 3,
                'scenario': '🏠 TRAPPED AT HOME – Water is rising and you cannot evacuate. Help is coming.',
                'question': 'How do you signal for help?',
                'options': [
                    {'text': 'Wait quietly in a lower room', 'points': -15, 'correct': False, 'feedback': '❌ Never go to lower areas when water is rising – go UP!'},
                    {'text': 'Move to roof, signal with bright colors/flashlight', 'points': 30, 'correct': True, 'feedback': '✅ Moving to the highest point and signaling for help is correct!'},
                    {'text': 'Try to swim to safety', 'points': -20, 'correct': False, 'feedback': '❌ Floodwater has dangerous currents and debris – don\'t attempt to swim.'},
                    {'text': 'Use social media to post your location', 'points': 10, 'correct': False, 'feedback': '⚠️ Social media can help but calling emergency services is more reliable.'},
                ],
            },
        ]
    },
    'cyclone': {
        'title': '🌀 Cyclone Drill',
        'intro': 'A Category 3 cyclone is making landfall. Winds are reaching 150 km/h!',
        'steps': [
            {
                'id': 1,
                'scenario': '⚠️ CYCLONE WARNING – Authorities issue Red Alert for your city.',
                'question': 'What do you do first?',
                'options': [
                    {'text': 'Go to the beach to see the waves', 'points': -30, 'correct': False, 'feedback': '❌ Never go near water during a cyclone warning! Extremely dangerous!'},
                    {'text': 'Secure loose objects and board windows', 'points': 30, 'correct': True, 'feedback': '✅ Securing the house is critical – loose objects become deadly projectiles!'},
                    {'text': 'Continue with normal activities', 'points': -20, 'correct': False, 'feedback': '❌ Take cyclone warnings seriously and prepare immediately!'},
                    {'text': 'Call friends and discuss the weather', 'points': -10, 'correct': False, 'feedback': '❌ Use your time to prepare, not socialize!'},
                ],
            },
            {
                'id': 2,
                'scenario': '🌀 CYCLONE HITS – The storm is at full force. You\'re indoors.',
                'question': 'Where do you shelter?',
                'options': [
                    {'text': 'Near windows to monitor the storm', 'points': -30, 'correct': False, 'feedback': '❌ Windows can shatter from debris – stay far away from them!'},
                    {'text': 'Interior room, lowest floor, away from windows', 'points': 30, 'correct': True, 'feedback': '✅ Perfect! Interior rooms provide the most protection!'},
                    {'text': 'On the roof to avoid flooding', 'points': -20, 'correct': False, 'feedback': '❌ The roof is the most dangerous place during a cyclone!'},
                    {'text': 'In your car in the garage', 'points': -15, 'correct': False, 'feedback': '❌ Stay inside your main structure, not in a vehicle!'},
                ],
            },
            {
                'id': 3,
                'scenario': '🌤️ THE EYE – The storm suddenly calms. It seems peaceful outside.',
                'question': 'What should you do?',
                'options': [
                    {'text': 'Go outside since the storm passed', 'points': -30, 'correct': False, 'feedback': '❌ The eye of the storm is temporary – the back eye wall is even more dangerous!'},
                    {'text': 'Stay inside – the other side of the storm is coming', 'points': 30, 'correct': True, 'feedback': '✅ Correct! The eye gives false hope – stay sheltered until official all-clear!'},
                    {'text': 'Start cleaning up the damage', 'points': -15, 'correct': False, 'feedback': '❌ The storm hasn\'t passed yet – stay sheltered!'},
                    {'text': 'Drive to check on relatives', 'points': -25, 'correct': False, 'feedback': '❌ Extremely dangerous – roads may be flooded and storm returns!'},
                ],
            },
        ]
    },
}

@app.route('/api/drill/start/<disaster_type>')
@login_required
def api_drill_start(disaster_type):
    if disaster_type not in DRILLS:
        return jsonify({'error': 'Unknown disaster type'}), 400
    drill = DRILLS[disaster_type]
    # Return steps without correct answers
    steps = []
    for s in drill['steps']:
        steps.append({
            'id': s['id'],
            'scenario': s['scenario'],
            'question': s['question'],
            'options': [{'text': o['text']} for o in s['options']],
        })
    return jsonify({
        'title': drill['title'],
        'intro': drill['intro'],
        'steps': steps,
        'total_steps': len(steps),
    })

@app.route('/api/drill/submit', methods=['POST'])
@login_required
def api_drill_submit():
    data          = request.get_json()
    disaster_type = data.get('disaster_type')
    answers       = data.get('answers', {})   # {step_id: option_index}
    time_taken    = data.get('time_taken', 0)
    uid           = session['user_id']

    if disaster_type not in DRILLS:
        return jsonify({'error': 'Unknown disaster type'}), 400

    drill     = DRILLS[disaster_type]
    total_pts = 0
    max_pts   = 0
    results   = []

    for step in drill['steps']:
        sid      = step['id']
        opts     = step['options']
        max_pts += max(o['points'] for o in opts)
        chosen   = answers.get(str(sid), answers.get(sid))
        if chosen is not None and 0 <= chosen < len(opts):
            gained = opts[chosen]['points']
            total_pts += gained
            results.append({
                'step_id': sid,
                'chosen': chosen,
                'points': gained,
                'correct': opts[chosen]['correct'],
                'feedback': opts[chosen]['feedback'],
                'scenario': step['scenario'],
            })
        else:
            results.append({'step_id': sid, 'points': 0, 'correct': False, 'feedback': 'No answer given'})

    # Clamp
    total_pts = max(0, total_pts)
    max_pts   = max(max_pts, 1)

    db = get_db()
    db.execute(
        "INSERT INTO drill_scores (user_id, disaster_type, score, max_score, time_taken) VALUES (?,?,?,?,?)",
        (uid, disaster_type, total_pts, max_pts, time_taken)
    )
    # Award leaderboard pts
    if total_pts > 0:
        db.execute(
            "INSERT INTO leaderboard (user_id, total_points) VALUES (?,?) ON CONFLICT(user_id) DO UPDATE SET total_points=total_points+?",
            (uid, total_pts, total_pts)
        )
    db.commit()
    db.close()

    pct = round(total_pts / max_pts * 100)
    grade = 'A+' if pct >= 90 else 'A' if pct >= 80 else 'B' if pct >= 70 else 'C' if pct >= 60 else 'D'

    return jsonify({
        'score': total_pts,
        'max_score': max_pts,
        'percentage': pct,
        'grade': grade,
        'results': results,
        'time_taken': time_taken,
    })

# ─────────────────────────────────────────────
# API – Leaderboard
# ─────────────────────────────────────────────
@app.route('/api/leaderboard')
@login_required
def api_leaderboard():
    uid = session['user_id']
    db  = get_db()
    rows = db.execute(
        """SELECT u.name, u.city, l.total_points,
           (SELECT COUNT(*) FROM user_modules WHERE user_id=u.id AND completed=1) as modules_done
           FROM leaderboard l JOIN users u ON l.user_id=u.id
           WHERE u.role='student'
           ORDER BY l.total_points DESC LIMIT 20"""
    ).fetchall()
    my_pts = db.execute("SELECT total_points FROM leaderboard WHERE user_id=?", (uid,)).fetchone()
    my_rank = db.execute(
        "SELECT COUNT(*) as cnt FROM leaderboard l JOIN users u ON l.user_id=u.id WHERE u.role='student' AND l.total_points > ?",
        (my_pts['total_points'] if my_pts else 0,)
    ).fetchone()['cnt'] + 1
    db.close()
    return jsonify({
        'leaderboard': [dict(r) for r in rows],
        'my_rank': my_rank,
        'my_points': my_pts['total_points'] if my_pts else 0,
    })

# ─────────────────────────────────────────────
# API – Alerts
# ─────────────────────────────────────────────
@app.route('/api/alert/send', methods=['POST'])
@admin_required
def api_alert_send():
    data     = request.get_json()
    message  = data.get('message', '').strip()
    city     = data.get('city', 'All')
    severity = data.get('severity', 'info')
    if not message:
        return jsonify({'error': 'Message required'}), 400
    db = get_db()
    db.execute(
        "INSERT INTO alerts (message, city, severity) VALUES (?,?,?)",
        (message, city, severity)
    )
    db.commit()
    db.close()
    return jsonify({'success': True})

@app.route('/api/alert/get')
@login_required
def api_alert_get():
    city = session.get('city', 'All')
    db   = get_db()
    alerts = db.execute(
        "SELECT * FROM alerts WHERE city=? OR city='All' ORDER BY created_at DESC LIMIT 20",
        (city,)
    ).fetchall()
    db.close()
    return jsonify([dict(a) for a in alerts])

@app.route('/api/alert/all')
@admin_required
def api_alert_all():
    db = get_db()
    alerts = db.execute("SELECT * FROM alerts ORDER BY created_at DESC").fetchall()
    db.close()
    return jsonify([dict(a) for a in alerts])

# ─────────────────────────────────────────────
# API – Emergency Contacts
# ─────────────────────────────────────────────
@app.route('/api/contacts')
@login_required
def api_contacts():
    db = get_db()
    contacts = db.execute("SELECT * FROM emergency_contacts ORDER BY category, name").fetchall()
    db.close()
    return jsonify([dict(c) for c in contacts])

# ─────────────────────────────────────────────
# API – Chatbot
# ─────────────────────────────────────────────
CHATBOT_KNOWLEDGE = {
    'earthquake': """During an EARTHQUAKE:
• DROP to your hands and knees
• Take COVER under a sturdy table or against an interior wall
• HOLD ON until shaking stops
• Stay away from windows, glass, and exterior walls
• Do NOT run outside during shaking
• After shaking stops: Check for injuries, watch for gas leaks
• Expect aftershocks – use Drop, Cover, Hold On each time
• Text rather than call to keep emergency lines free""",

    'fire': """During a FIRE emergency:
• Immediately activate fire alarm
• Call fire brigade: 101
• Crawl low under smoke to exit
• Feel doors before opening – if hot, use alternate exit
• Never use elevators – use stairs only
• Once outside, STAY outside
• Stop, Drop, and Roll if clothes catch fire
• Cover mouth/nose with wet cloth if available""",

    'flood': """During a FLOOD:
• Move to higher ground immediately
• Never walk or drive through floodwater
• 'Turn Around, Don't Drown' – even 15cm water can knock you down
• If trapped, move to roof and signal for help
• Disconnect electrical appliances
• Avoid contact with floodwater – it may be contaminated
• Follow evacuation orders immediately""",

    'cyclone': """During a CYCLONE:
• Stay indoors, away from windows
• Go to interior room on lowest floor
• Secure loose objects that could become projectiles
• Do NOT go outside during the eye – storm returns!
• Turn off utilities if instructed
• Listen to emergency broadcasts
• After: Watch for downed power lines""",

    'kit': """Emergency Preparedness KIT should contain:
• Water: 1 gallon per person per day (3-day supply)
• Non-perishable food (3-day supply)
• Battery-powered radio
• Flashlight and extra batteries
• First aid kit
• Whistle to signal for help
• Dust masks
• Plastic sheeting and duct tape
• Moist towelettes, garbage bags
• Wrench or pliers to shut off utilities
• Manual can opener
• Local maps
• Cell phone with chargers and backup battery
• Important documents in waterproof container""",

    'contact': """Emergency Contact Numbers (India):
• Police: 100
• Ambulance: 108
• Fire Brigade: 101
• Disaster Management Helpline: 1078
• Women Helpline: 1091
• Child Helpline: 1098
• Coastal Guard: 1554
• Blood Bank: 104
• National Emergency Number: 112""",
}

def get_chatbot_response(message):
    msg_lower = message.lower()

    # Rule-based first
    for keyword, response in [
        (['earthquake', 'quake', 'tremor', 'seismic'], CHATBOT_KNOWLEDGE['earthquake']),
        (['fire', 'smoke', 'burn', 'flame', 'blaze'], CHATBOT_KNOWLEDGE['fire']),
        (['flood', 'water', 'rain', 'inundat'], CHATBOT_KNOWLEDGE['flood']),
        (['cyclone', 'hurricane', 'typhoon', 'storm', 'wind'], CHATBOT_KNOWLEDGE['cyclone']),
        (['kit', 'bag', 'supply', 'supplies', 'prepare', 'stock'], CHATBOT_KNOWLEDGE['kit']),
        (['contact', 'number', 'call', 'police', 'ambulance', 'helpline'], CHATBOT_KNOWLEDGE['contact']),
    ]:
        if any(kw in msg_lower for kw in keyword):
            return response

    # Try OpenAI if key available
    api_key = os.getenv('OPENAI_API_KEY', '')
    if api_key and api_key != 'your_openai_api_key_here':
        try:
            resp = http_requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                json={
                    'model': 'gpt-3.5-turbo',
                    'messages': [
                        {'role': 'system', 'content': 'You are DisasterPrep AI, an emergency preparedness assistant. Give concise, actionable safety advice for disaster situations. Keep responses under 200 words.'},
                        {'role': 'user', 'content': message}
                    ],
                    'max_tokens': 250,
                },
                timeout=10
            )
            if resp.status_code == 200:
                return resp.json()['choices'][0]['message']['content']
        except Exception:
            pass

    # Default
    return """I can help you with disaster preparedness! Ask me about:
• 🌍 Earthquake safety
• 🔥 Fire emergency response
• 🌊 Flood preparedness
• 🌀 Cyclone safety
• 🎒 Emergency kit contents
• 📞 Emergency contact numbers

Type any of these topics to get detailed safety information!"""

@app.route('/api/chatbot', methods=['POST'])
@login_required
def api_chatbot():
    data    = request.get_json()
    message = data.get('message', '').strip()
    if not message:
        return jsonify({'error': 'Message required'}), 400
    response = get_chatbot_response(message)
    return jsonify({'response': response})

# ─────────────────────────────────────────────
# API – Admin
# ─────────────────────────────────────────────
@app.route('/api/admin/stats')
@admin_required
def api_admin_stats():
    db = get_db()
    total_students = db.execute("SELECT COUNT(*) as cnt FROM users WHERE role='student'").fetchone()['cnt']
    avg_prep = db.execute(
        "SELECT AVG(total_points) as avg FROM leaderboard l JOIN users u ON l.user_id=u.id WHERE u.role='student'"
    ).fetchone()['avg'] or 0
    drill_parts = db.execute("SELECT COUNT(DISTINCT user_id) as cnt FROM drill_scores").fetchone()['cnt']
    total_drills = db.execute("SELECT COUNT(*) as cnt FROM drill_scores").fetchone()['cnt']
    modules_completed = db.execute("SELECT COUNT(*) as cnt FROM user_modules WHERE completed=1").fetchone()['cnt']

    # Points by disaster type for chart
    drill_by_type = db.execute(
        "SELECT disaster_type, AVG(CAST(score AS FLOAT)/max_score*100) as avg_pct FROM drill_scores GROUP BY disaster_type"
    ).fetchall()

    # Daily signups (last 7 days)
    daily_users = db.execute(
        "SELECT DATE(created_at) as day, COUNT(*) as cnt FROM users WHERE role='student' GROUP BY day ORDER BY day DESC LIMIT 7"
    ).fetchall()

    # Top students
    top = db.execute(
        """SELECT u.name, u.city, l.total_points FROM leaderboard l
           JOIN users u ON l.user_id=u.id WHERE u.role='student'
           ORDER BY l.total_points DESC LIMIT 5"""
    ).fetchall()

    db.close()
    return jsonify({
        'total_students': total_students,
        'avg_preparedness': round(avg_prep / 10),  # normalize to 0-100
        'drill_participants': drill_parts,
        'total_drills': total_drills,
        'modules_completed': modules_completed,
        'drill_by_type': [dict(r) for r in drill_by_type],
        'daily_signups': [dict(r) for r in daily_users],
        'top_students': [dict(r) for r in top],
    })

@app.route('/api/admin/users')
@admin_required
def api_admin_users():
    db = get_db()
    users = db.execute(
        """SELECT u.id, u.name, u.email, u.city, u.created_at,
           COALESCE(l.total_points,0) as points,
           (SELECT COUNT(*) FROM user_modules WHERE user_id=u.id AND completed=1) as modules_done
           FROM users u LEFT JOIN leaderboard l ON l.user_id=u.id
           WHERE u.role='student' ORDER BY u.created_at DESC"""
    ).fetchall()
    db.close()
    return jsonify([dict(u) for u in users])

# ─────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
