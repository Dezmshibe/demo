"""Marula Table Catering - Flask backend"""
import csv, io, os, re, smtplib, sqlite3, time
from contextlib import closing
from datetime import date, datetime
from email.message import EmailMessage
from functools import wraps
from threading import Thread
import secrets
from flask import (Flask, Response, jsonify, redirect, render_template,
                   request, session, url_for)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.environ.get("DATABASE", os.path.join(BASE_DIR, "enquiries.db"))
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "change-me")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL", "")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024

# Sessions are signed with this. Set SECRET_KEY in the environment for
# production; otherwise a fresh one is generated on each start (which just
# means everyone is logged out when you restart the dev server).
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

SITE = {
    "name": "Marula Table Catering",
    "city": "Johannesburg, Gauteng",
    "tagline": "Food that keeps your event on schedule and your guests talking.",
    "intro": ("We cater boardroom lunches, product launches, conferences and "
              "year-end functions for companies across Gauteng. Tell us the date "
              "and headcount and we'll send a quote within one working day."),
    "facts": [("Events catered", "1,200+"), ("Group sizes", "10 to 800"),
              ("Quote turnaround", "1 working day")],
    "phone": "011 000 0000", "phone_href": "+27110000000",
    "email": "events@marulatable.co.za",
    "whatsapp": "082 000 0000", "whatsapp_href": "27820000000",
}

EVENTS = [
    {"type": "conference", "title": "Annual Leadership Summit",
     "meta": "Sandton \u00b7 420 guests \u00b7 2 days",
     "color_a": "#17302B", "color_b": "#E8A317", "image": "", "image_alt": "",
     "blurb": "Breakfast, working lunch and tea stations for two days, with live carving and a dedicated dietary counter."},
    {"type": "launch", "title": "Vehicle Brand Launch",
     "meta": "Midrand \u00b7 250 guests \u00b7 Evening",
     "color_a": "#4B1D3F", "color_b": "#E8A317", "image": "", "image_alt": "",
     "blurb": "Canap\u00e9 service with a craft-cocktail pairing, timed to the reveal and cleared before the speeches ended."},
    {"type": "gala", "title": "Year-End Gala Dinner",
     "meta": "Pretoria \u00b7 380 guests \u00b7 4 courses",
     "color_a": "#C8372D", "color_b": "#17302B", "image": "", "image_alt": "",
     "blurb": "Plated four-course dinner with a halaal and vegan alternative served at every table, not by request."},
    {"type": "boardroom", "title": "Quarterly Board Lunches",
     "meta": "Rosebank \u00b7 14 guests \u00b7 Recurring",
     "color_a": "#E8A317", "color_b": "#4B1D3F", "image": "", "image_alt": "",
     "blurb": "A rotating monthly menu delivered, plated and cleared without interrupting the meeting."},
    {"type": "conference", "title": "Mining Indaba Hospitality Suite",
     "meta": "Johannesburg \u00b7 150 guests \u00b7 3 days",
     "color_a": "#2F6B5A", "color_b": "#F2C14E", "image": "", "image_alt": "",
     "blurb": "All-day grazing tables and a hot lunch service for a rotating client hospitality suite."},
    {"type": "launch", "title": "Fintech Office Opening",
     "meta": "Melrose \u00b7 180 guests \u00b7 Cocktail",
     "color_a": "#E8A317", "color_b": "#C8372D", "image": "", "image_alt": "",
     "blurb": "Street-food style stations built around local flavours, served across three floors."},
]

def _items(*rows):
    return [{"text": t, "tags": tags} for t, *tags in rows]

MENUS = [
    {"slug": "breakfast", "tab": "Breakfast & boardroom",
     "title": "Breakfast & boardroom", "price": "From R135 per person",
     "courses": [
        {"name": "Pastries & bakes", "items": _items(
            ("Mini croissants with butter and apricot preserve", "V"),
            ("Cheddar and chive scones", "V"),
            ("Seasonal muffin selection", "V"))},
        {"name": "Hot items", "items": _items(
            ("Scrambled eggs with chives", "V", "GF"),
            ("Beef or chicken sausage", "H"),
            ("Roasted tomato and mushroom", "VG", "GF"))},
        {"name": "Fresh & drinks", "items": _items(
            ("Fruit platter and yoghurt with granola", "V"),
            ("Filter coffee, rooibos and juices"))},
     ]},
    {"slug": "lunch", "tab": "Working lunch", "title": "Working lunch",
     "price": "From R185 per person",
     "courses": [
        {"name": "Mains, choose two", "items": _items(
            ("Slow-roasted lamb with rosemary jus", "H", "GF"),
            ("Peri-peri chicken thighs", "H"),
            ("Butternut and chickpea curry", "VG", "GF"))},
        {"name": "Sides, choose three", "items": _items(
            ("Garlic and herb baby potatoes", "VG"),
            ("Coconut turmeric rice", "VG", "GF"),
            ("Charred greens with lemon", "VG"),
            ("Seasonal garden salad", "VG"))},
        {"name": "To finish", "items": _items(
            ("Malva pudding with custard", "V"),
            ("Fruit and mint skewers", "VG", "GF"))},
     ]},
    {"slug": "cocktail", "tab": "Cocktail & canap\u00e9s",
     "title": "Cocktail & canap\u00e9s", "price": "From R220 per person",
     "courses": [
        {"name": "Cold", "items": _items(
            ("Smoked trout blini with dill cream",),
            ("Biltong and blue cheese tartlet",),
            ("Beetroot hummus cups", "VG", "GF"))},
        {"name": "Hot", "items": _items(
            ("Mini boerewors rolls with chakalaka", "H"),
            ("Spinach and feta spanakopita", "V"),
            ("Crispy chicken bao", "H"))},
        {"name": "Sweet", "items": _items(
            ("Mini koeksister bites", "V"),
            ("Dark chocolate and rooibos pots", "V", "GF"))},
     ]},
    {"slug": "gala", "tab": "Gala dinner", "title": "Gala dinner",
     "price": "From R420 per person",
     "courses": [
        {"name": "Starter", "items": _items(
            ("Seared springbok carpaccio with pickled pear", "GF"),
            ("Whipped goat's cheese with beetroot", "V", "GF"))},
        {"name": "Main", "items": _items(
            ("Beef fillet with red wine reduction", "H", "GF"),
            ("Line fish with saffron cream", "GF"),
            ("Wild mushroom and barley risotto", "VG"))},
        {"name": "Dessert", "items": _items(
            ("Amarula cheesecake", "V"),
            ("Poached pear with vanilla bean", "VG", "GF"))},
     ]},
]

STEPS = [
    {"title": "Send the details", "body": "Date, venue, headcount and budget range. Rough numbers are fine."},
    {"title": "Get a quote", "body": "You'll receive an itemised quote within one working day."},
    {"title": "Taste and confirm", "body": "For events over 80 guests we arrange a tasting before you commit."},
    {"title": "We handle the day", "body": "Setup, service and clear-down, with a named event lead on site."},
]

def db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with closing(db()) as conn, conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS enquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL, company TEXT NOT NULL, name TEXT NOT NULL,
            email TEXT NOT NULL, phone TEXT NOT NULL, event_type TEXT NOT NULL,
            event_date TEXT NOT NULL, guests INTEGER NOT NULL, budget TEXT,
            venue TEXT, diet TEXT, message TEXT,
            status TEXT NOT NULL DEFAULT 'new')""")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_recent = {}

def client_ip():
    if os.environ.get("TRUST_PROXY") == "1":
        fwd = request.headers.get("X-Forwarded-For", "")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.remote_addr or "unknown"

def rate_limited(ip, limit=5, window=600):
    now = time.time()
    hits = [t for t in _recent.get(ip, []) if now - t < window]
    if len(hits) >= limit:
        _recent[ip] = hits
        return True
    hits.append(now)
    _recent[ip] = hits
    return False

def clean(v, n=500):
    return str(v or "").strip()[:n]

def validate(data):
    errors = []
    out = {
        "company": clean(data.get("company"), 120),
        "name": clean(data.get("name"), 120),
        "email": clean(data.get("email"), 160),
        "phone": clean(data.get("phone"), 40),
        "event_type": clean(data.get("eventType"), 80),
        "event_date": clean(data.get("date"), 10),
        "budget": clean(data.get("budget"), 60),
        "venue": clean(data.get("venue"), 160),
        "diet": clean(data.get("diet"), 200),
        "message": clean(data.get("message"), 2000),
    }
    for f, label in [("company", "Company name"), ("name", "Your name"),
                     ("phone", "Phone"), ("event_type", "Type of event")]:
        if not out[f]:
            errors.append(label)
    if not EMAIL_RE.match(out["email"]):
        errors.append("Work email")
    try:
        d = datetime.strptime(out["event_date"], "%Y-%m-%d").date()
        if d < date.today():
            errors.append("Event date (must be today or later)")
    except ValueError:
        errors.append("Event date")
    try:
        out["guests"] = int(data.get("guests"))
        if not 1 <= out["guests"] <= 5000:
            raise ValueError
    except (TypeError, ValueError):
        errors.append("Number of guests")
    return out, errors

def send_notification(row):
    host = os.environ.get("SMTP_HOST")
    if not (host and NOTIFY_EMAIL):
        return
    msg = EmailMessage()
    msg["Subject"] = f"New catering enquiry: {row['company']} ({row['guests']} guests)"
    msg["From"] = os.environ.get("SMTP_USER", NOTIFY_EMAIL)
    msg["To"] = NOTIFY_EMAIL
    msg["Reply-To"] = row["email"]
    msg.set_content("\n".join([
        f"Company:   {row['company']}",
        f"Contact:   {row['name']} <{row['email']}>  {row['phone']}",
        f"Event:     {row['event_type']} on {row['event_date']}",
        f"Guests:    {row['guests']}",
        f"Budget:    {row['budget'] or 'Not sure'}",
        f"Venue:     {row['venue'] or '-'}",
        f"Dietary:   {row['diet'] or '-'}", "", row["message"] or "(no message)",
    ]))
    try:
        with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", 587)), timeout=15) as s:
            s.starttls()
            if os.environ.get("SMTP_USER"):
                s.login(os.environ["SMTP_USER"], os.environ.get("SMTP_PASSWORD", ""))
            s.send_message(msg)
    except Exception as exc:
        app.logger.error("Enquiry saved but email failed: %s", exc)

def require_admin(view):
    @wraps(view)
    def wrapped(*a, **kw):
        if not session.get("admin"):
            return redirect(url_for("login", next=request.path))
        return view(*a, **kw)
    return wrapped

@app.route("/")
def home():
    return render_template("index.html", site=SITE, events=EVENTS,
                           menus=MENUS, steps=STEPS,
                           client_config={"endpoint": "/api/enquiry",
                                          "email": SITE["email"]})

@app.route("/api/enquiry", methods=["POST"])
def create_enquiry():
    data = request.get_json(silent=True) or request.form.to_dict()
    if data.get("website"):
        return jsonify(ok=True), 201
    if rate_limited(client_ip()):
        return jsonify(ok=False, error="Too many enquiries. Please try again later."), 429
    row, errors = validate(data)
    if errors:
        return jsonify(ok=False, error="Please check: " + ", ".join(errors)), 400
    with closing(db()) as conn, conn:
        conn.execute("""INSERT INTO enquiries
            (created_at, company, name, email, phone, event_type, event_date,
             guests, budget, venue, diet, message)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (datetime.now().isoformat(timespec="seconds"), row["company"], row["name"],
             row["email"], row["phone"], row["event_type"], row["event_date"],
             row["guests"], row["budget"], row["venue"], row["diet"], row["message"]))
    Thread(target=send_notification, args=(row,), daemon=True).start()
    return jsonify(ok=True), 201
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        user = request.form.get("username", "")
        pw = request.form.get("password", "")
        # compare_digest avoids leaking length via timing
        ok_user = secrets.compare_digest(user, ADMIN_USER)
        ok_pass = secrets.compare_digest(pw, ADMIN_PASSWORD)
        if ok_user and ok_pass:
            session["admin"] = True
            dest = request.args.get("next") or url_for("admin")
            # only allow same-site redirects
            if not dest.startswith("/"):
                dest = url_for("admin")
            return redirect(dest)
        error = "Wrong username or password."
    return render_template("login.html", error=error), (401 if error else 200)


@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("login"))
@app.route("/admin")
@require_admin
def admin():
    with closing(db()) as conn:
        rows = conn.execute("SELECT * FROM enquiries ORDER BY id DESC").fetchall()
    return render_template("admin.html", rows=rows)

@app.route("/admin/export.csv")
@require_admin
def export_csv():
    with closing(db()) as conn:
        rows = conn.execute("SELECT * FROM enquiries ORDER BY id DESC").fetchall()
    buf = io.StringIO()
    w = csv.writer(buf)
    if rows:
        w.writerow(rows[0].keys())
        w.writerows([tuple(r) for r in rows])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=enquiries.csv"})

init_db()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")