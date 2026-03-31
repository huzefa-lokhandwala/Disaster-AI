import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'disasterprep.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'student',
            city TEXT DEFAULT 'Mumbai',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS modules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            disaster_type TEXT NOT NULL,
            description TEXT,
            content TEXT,
            icon TEXT,
            points INTEGER DEFAULT 100
        );

        CREATE TABLE IF NOT EXISTS quiz_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            module_id INTEGER,
            score INTEGER,
            total INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(module_id) REFERENCES modules(id)
        );

        CREATE TABLE IF NOT EXISTS drill_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            disaster_type TEXT,
            score INTEGER,
            max_score INTEGER,
            time_taken INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            city TEXT DEFAULT 'All',
            severity TEXT DEFAULT 'info',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS leaderboard (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            total_points INTEGER DEFAULT 0,
            badges TEXT DEFAULT '[]',
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS emergency_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            category TEXT,
            icon TEXT
        );

        CREATE TABLE IF NOT EXISTS user_modules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            module_id INTEGER,
            completed INTEGER DEFAULT 0,
            points_earned INTEGER DEFAULT 0,
            completed_at TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(module_id) REFERENCES modules(id)
        );
    ''')

    # Seed modules
    c.execute("SELECT COUNT(*) FROM modules")
    if c.fetchone()[0] == 0:
        modules = [
            (
                'Earthquake Preparedness', 'earthquake',
                'Learn how to stay safe before, during, and after an earthquake.',
                '''{"before":["Secure heavy furniture to walls","Prepare an emergency kit with water, food, first aid","Identify safe spots in each room – under sturdy tables","Practice Drop, Cover, and Hold On","Know your building exit routes","Store important documents safely","Keep a battery-powered radio","Ensure gas valves can be shut off quickly"],"during":["DROP to hands and knees immediately","Take COVER under a sturdy desk or table","HOLD ON until shaking stops","Stay away from windows and exterior walls","Do NOT run outside during shaking","If in bed, stay there and protect your head with a pillow","If outdoors, move away from buildings","If in a vehicle, pull over away from bridges"],"after":["Check yourself and others for injuries","Expect aftershocks – use Drop Cover Hold On","Check for gas leaks – if you smell gas, leave building","Do NOT use elevators","Text rather than call to keep lines free","Listen to emergency broadcasts","Stay away from damaged buildings","Document damage for insurance"]}''',
                '🌍', 150
            ),
            (
                'Fire Safety', 'fire',
                'Master fire prevention, evacuation, and response techniques.',
                '''{"before":["Install smoke alarms on every floor","Test smoke alarms monthly","Plan and practice two exit routes from every room","Keep fire extinguisher accessible and know how to use it","Never leave cooking unattended","Store flammable materials safely","Keep electrical cords in good condition","Create a family meeting point outside"],"during":["Activate the building fire alarm","Call fire department immediately (101)","Crawl low under smoke to exit","Feel doors before opening – if hot use another exit","Cover mouth/nose with wet cloth","Close doors to slow fire spread","Never use elevators during fire","Once outside, STAY outside"],"after":["Do NOT re-enter building until cleared by fire department","Seek medical attention for burns or smoke inhalation","Contact insurance company","Let friends/family know you are safe","Watch for structural damage","Avoid areas with ash – use protective mask","Preserve food safety after power outage","Document damage for insurance"]}''',
                '🔥', 150
            ),
            (
                'Flood Response', 'flood',
                'Understand flood warnings, evacuation, and post-flood safety.',
                '''{"before":["Know your area flood risk and evacuation routes","Move valuables to higher floors","Prepare emergency kit – include waterproof bag","Fill bathtub with water for sanitation","Turn off utilities if instructed","Move vehicles to higher ground","Avoid building in flood plains","Install check valves in plumbing"],"during":["Evacuate immediately when told to","Never walk in moving water","Avoid driving through flooded roads – Turn Around Don't Drown","Move to highest level of building if trapped","Signal for help from highest point","Disconnect electrical appliances","Do NOT touch electrical equipment if wet","Stay away from storm drains"],"after":["Return only when authorities clear it safe","Avoid floodwater – may be contaminated","Check for structural damage before entering","Document all damage with photographs","Discard food that contacted floodwater","Clean and disinfect everything","Check for mold growth","Contact your insurance company"]}''',
                '🌊', 150
            ),
            (
                'Cyclone/Hurricane Safety', 'cyclone',
                'Prepare and respond effectively during cyclone and storm events.',
                '''{"before":["Monitor weather alerts and warnings","Board up windows or install storm shutters","Clear yard of loose objects","Fill vehicle with fuel and have cash ready","Charge all devices and power banks","Prepare emergency kit for 72 hours","Know your evacuation zone","Identify nearest cyclone shelter"],"during":["Stay indoors away from windows","Go to interior room on lowest floor","Do NOT go outside during eye of storm – it will return","Turn off utilities if instructed","Stay away from flood-prone areas","Listen to emergency broadcasts","Do NOT use candles – use flashlights","Keep shoes on at all times"],"after":["Wait for official all-clear before going outside","Watch for downed power lines","Avoid floodwaters","Check on neighbors, especially elderly","Document damage for insurance","Boil water until water supply is declared safe","Use generators outdoors only","Report any gas leaks"]}''',
                '🌀', 150
            ),
        ]
        c.executemany(
            "INSERT INTO modules (title, disaster_type, description, content, icon, points) VALUES (?,?,?,?,?,?)",
            modules
        )

    # Seed emergency contacts
    c.execute("SELECT COUNT(*) FROM emergency_contacts")
    if c.fetchone()[0] == 0:
        contacts = [
            ('Police', '100', 'emergency', '🚔'),
            ('Ambulance', '108', 'emergency', '🚑'),
            ('Fire Brigade', '101', 'emergency', '🚒'),
            ('Disaster Management', '1078', 'emergency', '⛑️'),
            ('Women Helpline', '1091', 'helpline', '👩'),
            ('Child Helpline', '1098', 'helpline', '👶'),
            ('Coastal Guard', '1554', 'emergency', '⚓'),
            ('Blood Bank', '104', 'medical', '🩸'),
        ]
        c.executemany(
            "INSERT INTO emergency_contacts (name, phone, category, icon) VALUES (?,?,?,?)",
            contacts
        )

    # Seed admin user
    c.execute("SELECT COUNT(*) FROM users WHERE role='admin'")
    if c.fetchone()[0] == 0:
        from werkzeug.security import generate_password_hash
        admin_pass = generate_password_hash('admin123')
        c.execute(
            "INSERT INTO users (name, email, password, role, city) VALUES (?,?,?,?,?)",
            ('Admin', 'admin@disasterprep.com', admin_pass, 'admin', 'Mumbai')
        )
        admin_id = c.lastrowid
        c.execute("INSERT INTO leaderboard (user_id, total_points) VALUES (?,?)", (admin_id, 0))

    conn.commit()
    conn.close()
    print("✅ Database initialized successfully.")

if __name__ == '__main__':
    init_db()
