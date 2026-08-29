from __future__ import annotations

import os
import sqlite3
from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path

from flask import Flask, g, has_request_context, jsonify, redirect, render_template, request, send_file, session, url_for
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE = DATA_DIR / "voeding.db"
AUTH_DATABASE = DATA_DIR / "auth.db"
USER_DATA_DIR = DATA_DIR / "user_data"

NUTRIENTS = (
    "energie", "vet", "verzadigd_vet", "koolhydraten",
    "suikers", "vezels", "eiwit", "zout",
)

START_PRODUCTS = {
    "Magere kwark": (52, 0, 0, 4, 4, 0, 9, 0.108),
    "Volkoren brood": (221, 1, 0.2, 41, 1.5, 7.5, 8, 0.59),
    "Rijst": (354, 1, 0.2, 77, 0.1, 0.9, 8.3, 0.001),
    "Salsa": (34.4, 0.212, 0.012, 6.4, 4.4, 1.84, 1.28, 0.172),
    "Kipfilet": (111, 2, 0.7, 1, 0.5, 0, 22, 2),
    "Noodles": (345, 0, 0, 80.6, 0, 0, 5.6, 1.5),
    "Appel": (59, 0.2, 0, 13, 10, 2, 0.3, 0),
    "Komkommer": (13, 0.435, 0.087, 1.3, 1.3, 0.609, 0.696, 0.0087),
    "Aardappel": (88, 0.1, 0.02, 19, 0.8, 1.8, 2, 0),
    "Kip": (109, 1.5, 0.4, 0, 0, 0, 23.3, 0.13),
    "Gehakt": (210, 14, 5.6, 0, 0, 0, 21, 0.1),
    "Pesto": (470, 45, 5.8, 8.5, 7.6, 1.4, 7.1, 2.5),
    "Pasta": (357, 1.4, 0.3, 72, 3.1, 3.2, 12.5, 0.008),
    "Parmazaanse kaas": (407, 31, 21, 0, 0, 0, 32, 1.3),
    "Broccoli": (34, 0.4, 0.1, 4, 1.7, 3, 2.8, 0.08),
    "Wrap": (326, 7.3, 0.9, 55, 3.2, 2.3, 9.4, 0.9),
}

START_PRODUCT_CATEGORIES = {
    "Magere kwark": "Zuivel", "Parmazaanse kaas": "Zuivel",
    "Volkoren brood": "Brood, granen & wraps", "Wrap": "Brood, granen & wraps",
    "Rijst": "Rijst, pasta & noedels", "Pasta": "Rijst, pasta & noedels", "Noodles": "Rijst, pasta & noedels",
    "Appel": "Fruit",
    "Komkommer": "Groenten & aardappelen", "Aardappel": "Groenten & aardappelen", "Broccoli": "Groenten & aardappelen",
    "Kipfilet": "Vlees & gevogelte", "Kip": "Vlees & gevogelte", "Gehakt": "Vlees & gevogelte",
    "Salsa": "Sauzen & smaakmakers", "Pesto": "Sauzen & smaakmakers",
}

START_EXERCISES = (
    "Squat", "Incline dumbbell press", "Row", "Leg curl",
    "Cable lateral raise", "Triceps cable extension", "Leg press",
    "Bench press", "Lat pulldown", "Cable pull-through", "Dumbbell curl",
)

EXERCISE_CATEGORIES = ("Benen", "Borst", "Rug", "Triceps", "Biceps", "Schouders")
START_EXERCISE_CATEGORIES = {
    "Squat": "Benen", "Leg curl": "Benen", "Leg press": "Benen", "Cable pull-through": "Benen",
    "Incline dumbbell press": "Borst", "Bench press": "Borst",
    "Row": "Rug", "Lat pulldown": "Rug",
    "Triceps cable extension": "Triceps", "Dumbbell curl": "Biceps",
    "Cable lateral raise": "Schouders",
}

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "voedingswaarde-lokaal-verander-deze-sleutel")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "true" if os.environ.get("RENDER") else "false").lower() == "true",
)
INITIALIZED_USER_DATABASES = set()


def auth_db():
    connection = sqlite3.connect(AUTH_DATABASE, timeout=20)
    connection.row_factory = sqlite3.Row
    return connection


def current_user_id():
    if has_request_context() and getattr(g, "user_id", None):
        return g.user_id
    return 1


def user_database(user_id=None):
    user_id = int(user_id or current_user_id())
    if user_id == 1:
        return DATABASE
    USER_DATA_DIR.mkdir(exist_ok=True)
    return USER_DATA_DIR / f"user_{user_id}.db"


def db(user_id=None):
    connection = sqlite3.connect(user_database(user_id), timeout=20)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_user_db(user_id=1):
    with db(user_id) as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                category TEXT NOT NULL DEFAULT 'Overig',
                energie REAL NOT NULL DEFAULT 0,
                vet REAL NOT NULL DEFAULT 0,
                verzadigd_vet REAL NOT NULL DEFAULT 0,
                koolhydraten REAL NOT NULL DEFAULT 0,
                suikers REAL NOT NULL DEFAULT 0,
                vezels REAL NOT NULL DEFAULT 0,
                eiwit REAL NOT NULL DEFAULT 0,
                zout REAL NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS meals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS meal_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meal_id INTEGER NOT NULL REFERENCES meals(id) ON DELETE CASCADE,
                product_id INTEGER NOT NULL REFERENCES products(id),
                grams REAL NOT NULL CHECK (grams > 0)
            );
            CREATE TABLE IF NOT EXISTS health_days (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day_date TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS health_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                health_day_id INTEGER NOT NULL REFERENCES health_days(id) ON DELETE CASCADE,
                category TEXT NOT NULL CHECK (category IN ('ontbijt','lunch','avondeten','tussendoortje')),
                product_id INTEGER NOT NULL REFERENCES products(id),
                grams REAL NOT NULL CHECK (grams > 0)
            );
            CREATE TABLE IF NOT EXISTS exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                category TEXT NOT NULL DEFAULT 'Overig',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS fitness_days (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day_date TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS workout_exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fitness_day_id INTEGER NOT NULL REFERENCES fitness_days(id) ON DELETE CASCADE,
                exercise_id INTEGER NOT NULL REFERENCES exercises(id),
                position INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS workout_sets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workout_exercise_id INTEGER NOT NULL REFERENCES workout_exercises(id) ON DELETE CASCADE,
                set_type TEXT NOT NULL CHECK (set_type IN ('warmingup','work')),
                set_order INTEGER NOT NULL,
                reps INTEGER NOT NULL CHECK (reps > 0),
                weight REAL NOT NULL CHECK (weight >= 0)
            );
            CREATE TABLE IF NOT EXISTS daily_burn (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day_date TEXT NOT NULL UNIQUE,
                burned_kcal REAL NOT NULL DEFAULT 0 CHECK (burned_kcal >= 0),
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)
        product_columns = {row["name"] for row in connection.execute("PRAGMA table_info(products)").fetchall()}
        if "category" not in product_columns:
            connection.execute("ALTER TABLE products ADD COLUMN category TEXT NOT NULL DEFAULT 'Overig'")
        for product_name, category in START_PRODUCT_CATEGORIES.items():
            connection.execute(
                "UPDATE products SET category = ? WHERE name = ? COLLATE NOCASE AND (category IS NULL OR category = '' OR category = 'Overig')",
                (category, product_name),
            )
        for name, values in START_PRODUCTS.items():
            connection.execute(
                f"INSERT OR IGNORE INTO products (name, category, {', '.join(NUTRIENTS)}) VALUES (?, ?, {', '.join('?' for _ in NUTRIENTS)})",
                (name, START_PRODUCT_CATEGORIES.get(name, "Overig"), *values),
            )
        exercise_columns = {row["name"] for row in connection.execute("PRAGMA table_info(exercises)").fetchall()}
        if "category" not in exercise_columns:
            connection.execute("ALTER TABLE exercises ADD COLUMN category TEXT NOT NULL DEFAULT 'Overig'")
        for exercise_name, category in START_EXERCISE_CATEGORIES.items():
            connection.execute(
                "UPDATE exercises SET category = ? WHERE name = ? COLLATE NOCASE AND (category IS NULL OR category = '' OR category = 'Overig')",
                (category, exercise_name),
            )
        for exercise_name in START_EXERCISES:
            connection.execute(
                "INSERT OR IGNORE INTO exercises (name, category) VALUES (?, ?)",
                (exercise_name, START_EXERCISE_CATEGORIES.get(exercise_name, "Overig")),
            )
    INITIALIZED_USER_DATABASES.add(int(user_id))


def init_db():
    with auth_db() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.execute(
            "INSERT OR IGNORE INTO users (id, username, password_hash) VALUES (1, ?, ?)",
            ("admin", generate_password_hash("test")),
        )
    init_user_db(1)


@app.before_request
def load_logged_in_user():
    public_endpoints = {"login", "register", "static"}
    user_id = session.get("user_id")
    g.user_id = None
    g.username = None
    if user_id:
        with auth_db() as connection:
            user = connection.execute("SELECT id, username FROM users WHERE id = ?", (user_id,)).fetchone()
        if user:
            g.user_id = user["id"]
            g.username = user["username"]
            if g.user_id not in INITIALIZED_USER_DATABASES:
                init_user_db(g.user_id)
    if request.endpoint not in public_endpoints and not g.user_id:
        if request.path.startswith("/api/"):
            return jsonify(error="Log opnieuw in."), 401
        return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user_id:
        return redirect(url_for("index"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        with auth_db() as connection:
            user = connection.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,)).fetchone()
        if not user or not check_password_hash(user["password_hash"], password):
            error = "Onjuiste gebruikersnaam of wachtwoord."
        else:
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("index"))
    return render_template("login.html", mode="login", error=error)


@app.route("/register", methods=["GET", "POST"])
def register():
    if g.user_id:
        return redirect(url_for("index"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            error = "Vul een gebruikersnaam en wachtwoord in."
        else:
            try:
                with auth_db() as connection:
                    cursor = connection.execute(
                        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                        (username, generate_password_hash(password)),
                    )
                    user_id = cursor.lastrowid
                init_user_db(user_id)
                session.clear()
                session["user_id"] = user_id
                return redirect(url_for("index"))
            except sqlite3.IntegrityError:
                error = "Deze gebruikersnaam bestaat al."
    return render_template("login.html", mode="register", error=error)


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/api/auth/me")
def auth_me():
    return jsonify(id=g.user_id, username=g.username)


def product_dict(row):
    return {key: row[key] for key in ("id", "name", "category", *NUTRIENTS)}


def valid_date(value):
    try:
        return date.fromisoformat(str(value)).isoformat()
    except (TypeError, ValueError):
        return None


def health_days_data(connection, start=None, end=None):
    query = "SELECT * FROM health_days"
    params = []
    clauses = []
    if start:
        clauses.append("day_date >= ?")
        params.append(start)
    if end:
        clauses.append("day_date <= ?")
        params.append(end)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY day_date DESC"
    days = []
    for day_row in connection.execute(query, params).fetchall():
        entries = connection.execute("""
            SELECT he.id, he.category, he.product_id, he.grams, p.*
            FROM health_entries he JOIN products p ON p.id = he.product_id
            WHERE he.health_day_id = ? ORDER BY he.id
        """, (day_row["id"],)).fetchall()
        totals = {key: 0.0 for key in NUTRIENTS}
        categories = {key: [] for key in ("ontbijt", "lunch", "avondeten", "tussendoortje")}
        for entry in entries:
            factor = entry["grams"] / 100
            nutrients = {key: entry[key] * factor for key in NUTRIENTS}
            for key in NUTRIENTS:
                totals[key] += nutrients[key]
            categories[entry["category"]].append({
                "id": entry["id"], "product_id": entry["product_id"],
                "name": entry["name"], "grams": entry["grams"], "nutrients": nutrients,
            })
        days.append({"id": day_row["id"], "date": day_row["day_date"], "categories": categories, "totals": totals})
    return days


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/products")
def products():
    with db() as connection:
        rows = connection.execute("SELECT * FROM products ORDER BY name COLLATE NOCASE").fetchall()
    return jsonify([product_dict(row) for row in rows])


@app.post("/api/products")
def add_product():
    data = request.get_json(force=True)
    name = str(data.get("name", "")).strip()
    if not name:
        return jsonify(error="Vul een productnaam in."), 400
    category = str(data.get("category", "Overig")).strip() or "Overig"
    try:
        values = [max(0.0, float(data.get(key, 0))) for key in NUTRIENTS]
    except (TypeError, ValueError):
        return jsonify(error="Gebruik alleen geldige, positieve getallen."), 400
    try:
        with db() as connection:
            cursor = connection.execute(
                f"INSERT INTO products (name, category, {', '.join(NUTRIENTS)}) VALUES (?, ?, {', '.join('?' for _ in NUTRIENTS)})",
                (name, category, *values),
            )
            product_id = cursor.lastrowid
            row = connection.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    except sqlite3.IntegrityError:
        return jsonify(error="Dit product bestaat al."), 409
    return jsonify(product_dict(row)), 201


@app.delete("/api/products/<int:product_id>")
def delete_product(product_id):
    try:
        with db() as connection:
            result = connection.execute("DELETE FROM products WHERE id = ?", (product_id,))
    except sqlite3.IntegrityError:
        return jsonify(error="Dit product wordt gebruikt in een opgeslagen maaltijd."), 409
    if not result.rowcount:
        return jsonify(error="Product niet gevonden."), 404
    return "", 204


@app.get("/api/meals")
def meals():
    with db() as connection:
        meals_rows = connection.execute("SELECT * FROM meals ORDER BY id DESC").fetchall()
        result = []
        for meal in meals_rows:
            items = connection.execute("""
                SELECT mi.id, mi.product_id, mi.grams, p.*
                FROM meal_items mi JOIN products p ON p.id = mi.product_id
                WHERE mi.meal_id = ? ORDER BY mi.id
            """, (meal["id"],)).fetchall()
            totals = {key: 0.0 for key in NUTRIENTS}
            output_items = []
            for item in items:
                factor = item["grams"] / 100
                nutrients = {key: item[key] * factor for key in NUTRIENTS}
                for key in NUTRIENTS:
                    totals[key] += nutrients[key]
                output_items.append({"product_id": item["product_id"], "name": item["name"], "grams": item["grams"], "nutrients": nutrients})
            result.append({"id": meal["id"], "name": meal["name"], "created_at": meal["created_at"], "items": output_items, "totals": totals})
    return jsonify(result)


@app.post("/api/meals")
def add_meal():
    data = request.get_json(force=True)
    name = str(data.get("name", "")).strip()
    items = data.get("items", [])
    if not name:
        return jsonify(error="Geef de maaltijd een naam."), 400
    if not items:
        return jsonify(error="Voeg minimaal één product toe."), 400
    try:
        clean_items = [(int(item["product_id"]), float(item["grams"])) for item in items if float(item["grams"]) > 0]
    except (KeyError, TypeError, ValueError):
        return jsonify(error="Controleer de producten en grammen."), 400
    if not clean_items:
        return jsonify(error="Voeg minimaal één hoeveelheid groter dan 0 gram toe."), 400
    try:
        with db() as connection:
            cursor = connection.execute("INSERT INTO meals (name) VALUES (?)", (name,))
            meal_id = cursor.lastrowid
            connection.executemany("INSERT INTO meal_items (meal_id, product_id, grams) VALUES (?, ?, ?)", [(meal_id, *item) for item in clean_items])
    except sqlite3.IntegrityError:
        return jsonify(error="Een gekozen product bestaat niet meer."), 400
    return jsonify(id=meal_id), 201


@app.delete("/api/meals/<int:meal_id>")
def delete_meal(meal_id):
    with db() as connection:
        result = connection.execute("DELETE FROM meals WHERE id = ?", (meal_id,))
    if not result.rowcount:
        return jsonify(error="Maaltijd niet gevonden."), 404
    return "", 204


@app.get("/api/exercises")
def get_exercises():
    with db() as connection:
        rows = connection.execute("SELECT id, name, category FROM exercises ORDER BY category, name COLLATE NOCASE").fetchall()
    return jsonify([dict(row) for row in rows])


@app.post("/api/exercises")
def add_exercise():
    data = request.get_json(force=True)
    name = str(data.get("name", "")).strip()
    category = str(data.get("category", "")).strip()
    if not name:
        return jsonify(error="Vul een naam voor de oefening in."), 400
    if not category:
        return jsonify(error="Vul een categorie voor de oefening in."), 400
    try:
        with db() as connection:
            exercise_id = connection.execute("INSERT INTO exercises (name, category) VALUES (?, ?)", (name, category)).lastrowid
            row = connection.execute("SELECT id, name, category FROM exercises WHERE id = ?", (exercise_id,)).fetchone()
    except sqlite3.IntegrityError:
        return jsonify(error="Deze oefening bestaat al."), 409
    return jsonify(dict(row)), 201


@app.delete("/api/exercises/<int:exercise_id>")
def delete_exercise(exercise_id):
    try:
        with db() as connection:
            result = connection.execute("DELETE FROM exercises WHERE id = ?", (exercise_id,))
    except sqlite3.IntegrityError:
        return jsonify(error="Deze oefening wordt gebruikt in een opgeslagen training."), 409
    if not result.rowcount:
        return jsonify(error="Oefening niet gevonden."), 404
    return "", 204


def fitness_day_data(connection, day_date):
    day = connection.execute("SELECT * FROM fitness_days WHERE day_date = ?", (day_date,)).fetchone()
    if not day:
        return {"id": None, "date": day_date, "exercises": []}
    exercises = []
    rows = connection.execute("""
        SELECT we.id, we.exercise_id, e.name
        FROM workout_exercises we JOIN exercises e ON e.id = we.exercise_id
        WHERE we.fitness_day_id = ? ORDER BY we.position, we.id
    """, (day["id"],)).fetchall()
    for exercise in rows:
        sets = connection.execute("""
            SELECT id, set_type, set_order, reps, weight FROM workout_sets
            WHERE workout_exercise_id = ?
            ORDER BY CASE set_type WHEN 'warmingup' THEN 0 ELSE 1 END, set_order, id
        """, (exercise["id"],)).fetchall()
        exercises.append({
            "id": exercise["id"], "exercise_id": exercise["exercise_id"],
            "name": exercise["name"], "sets": [dict(item) for item in sets],
        })
    return {"id": day["id"], "date": day["day_date"], "exercises": exercises}


def fitness_days_data(connection, start, end):
    dates = connection.execute(
        "SELECT day_date FROM fitness_days WHERE day_date >= ? AND day_date <= ? ORDER BY day_date",
        (start, end),
    ).fetchall()
    return [fitness_day_data(connection, row["day_date"]) for row in dates]


OVERVIEW_PERIODS = {"day", "week", "month", "3months", "6months", "year"}


def overview_range(day_date, period):
    """Return the calendar period containing the selected date."""
    selected = date.fromisoformat(day_date)
    if period == "day":
        start = end = selected
    elif period == "week":
        start = selected - timedelta(days=selected.weekday())
        end = start + timedelta(days=6)
    elif period == "year":
        start, end = date(selected.year, 1, 1), date(selected.year, 12, 31)
    else:
        months = {"month": 1, "3months": 3, "6months": 6}[period]
        start_index = selected.year * 12 + selected.month - months
        start = date(start_index // 12, start_index % 12 + 1, 1)
        next_month_index = selected.year * 12 + selected.month
        end = date(next_month_index // 12, next_month_index % 12 + 1, 1) - timedelta(days=1)
    return start.isoformat(), end.isoformat()


def overview_data(user_id, day_date, period="day"):
    start_date, end_date = overview_range(day_date, period)
    result = overview_data_range(user_id, start_date, end_date)
    result.update({"date": day_date, "period": period})
    return result


def overview_data_range(user_id, start_date, end_date):
    if int(user_id) not in INITIALIZED_USER_DATABASES:
        init_user_db(user_id)
    with db(user_id) as connection:
        food_days = health_days_data(connection, start_date, end_date)
        fitness_days = fitness_days_data(connection, start_date, end_date)
        burn_rows = connection.execute(
            "SELECT day_date, burned_kcal FROM daily_burn WHERE day_date >= ? AND day_date <= ?",
            (start_date, end_date),
        ).fetchall()
    totals = {key: sum(day["totals"][key] for day in food_days) for key in NUTRIENTS}
    burn_by_date = {row["day_date"]: row["burned_kcal"] for row in burn_rows}
    current = date.fromisoformat(start_date)
    last = date.fromisoformat(end_date)
    burn_days = []
    while current <= last:
        day_key = current.isoformat()
        burn_days.append({"date": day_key, "burned_kcal": burn_by_date.get(day_key, 0.0)})
        current += timedelta(days=1)
    burned = sum(day["burned_kcal"] for day in burn_days)
    return {
        "start_date": start_date, "end_date": end_date,
        "food": {"days": food_days, "totals": totals},
        "fitness": {"days": fitness_days},
        "burn": {"days": burn_days},
        "burned_kcal": burned, "balance": burned - totals["energie"],
    }


def requested_overview_range():
    start = valid_date(request.args.get("from"))
    end = valid_date(request.args.get("to"))
    if not start or not end or start > end:
        return None
    return start, end


@app.get("/api/overview")
def get_overview_range():
    selected_range = requested_overview_range()
    if not selected_range:
        return jsonify(error="Kies een geldige periode."), 400
    result = overview_data_range(g.user_id, *selected_range)
    result["user"] = {"id": g.user_id, "username": g.username, "is_self": True}
    return jsonify(result)


@app.get("/api/overview/<day_date>")
def get_overview(day_date):
    day_date = valid_date(day_date)
    if not day_date:
        return jsonify(error="Kies een geldige datum."), 400
    period = request.args.get("period", "day")
    if period not in OVERVIEW_PERIODS:
        return jsonify(error="Kies een geldige periode."), 400
    result = overview_data(g.user_id, day_date, period)
    result["user"] = {"id": g.user_id, "username": g.username, "is_self": True}
    return jsonify(result)


@app.post("/api/overview/<day_date>/burn")
def save_daily_burn(day_date):
    day_date = valid_date(day_date)
    if not day_date:
        return jsonify(error="Kies een geldige datum."), 400
    try:
        burned = float(request.get_json(force=True).get("burned_kcal", 0))
        if burned < 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify(error="Vul een geldige verbranding in."), 400
    with db() as connection:
        connection.execute("""
            INSERT INTO daily_burn (day_date, burned_kcal) VALUES (?, ?)
            ON CONFLICT(day_date) DO UPDATE SET burned_kcal = excluded.burned_kcal, updated_at = CURRENT_TIMESTAMP
        """, (day_date, burned))
    return jsonify(burned_kcal=burned)


@app.get("/api/friends")
def get_friends():
    with auth_db() as connection:
        rows = connection.execute(
            "SELECT id, username FROM users WHERE id != ? ORDER BY username COLLATE NOCASE",
            (g.user_id,),
        ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.get("/api/users/<int:user_id>/overview/<day_date>")
def get_friend_overview(user_id, day_date):
    day_date = valid_date(day_date)
    if not day_date:
        return jsonify(error="Kies een geldige datum."), 400
    with auth_db() as connection:
        user = connection.execute("SELECT id, username FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        return jsonify(error="Gebruiker niet gevonden."), 404
    period = request.args.get("period", "day")
    if period not in OVERVIEW_PERIODS:
        return jsonify(error="Kies een geldige periode."), 400
    result = overview_data(user_id, day_date, period)
    result["user"] = {"id": user["id"], "username": user["username"], "is_self": user["id"] == g.user_id}
    return jsonify(result)


@app.get("/api/users/<int:user_id>/overview")
def get_friend_overview_range(user_id):
    selected_range = requested_overview_range()
    if not selected_range:
        return jsonify(error="Kies een geldige periode."), 400
    with auth_db() as connection:
        user = connection.execute("SELECT id, username FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        return jsonify(error="Gebruiker niet gevonden."), 404
    result = overview_data_range(user_id, *selected_range)
    result["user"] = {"id": user["id"], "username": user["username"], "is_self": user["id"] == g.user_id}
    return jsonify(result)


@app.get("/api/fitness-days/<day_date>")
def get_fitness_day(day_date):
    day_date = valid_date(day_date)
    if not day_date:
        return jsonify(error="Kies een geldige datum."), 400
    with db() as connection:
        result = fitness_day_data(connection, day_date)
    return jsonify(result)


@app.post("/api/fitness-days/<day_date>/exercises")
def save_fitness_exercise(day_date):
    day_date = valid_date(day_date)
    if not day_date:
        return jsonify(error="Kies een geldige datum."), 400
    data = request.get_json(force=True)
    try:
        exercise_id = int(data["exercise_id"])
        clean_sets = []
        counters = {"warmingup": 0, "work": 0}
        for item in data.get("sets", []):
            set_type = str(item["set_type"])
            reps = int(item["reps"])
            weight = float(item["weight"])
            if set_type not in counters or reps <= 0 or weight < 0:
                raise ValueError
            counters[set_type] += 1
            clean_sets.append((set_type, counters[set_type], reps, weight))
    except (KeyError, TypeError, ValueError):
        return jsonify(error="Controleer de herhalingen en gewichten."), 400
    if not clean_sets or not counters["work"]:
        return jsonify(error="Voeg minimaal één geldige werkset toe."), 400
    try:
        with db() as connection:
            if not connection.execute("SELECT 1 FROM exercises WHERE id = ?", (exercise_id,)).fetchone():
                return jsonify(error="Oefening niet gevonden."), 404
            day = connection.execute("SELECT id FROM fitness_days WHERE day_date = ?", (day_date,)).fetchone()
            if day:
                day_id = day["id"]
                connection.execute("UPDATE fitness_days SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (day_id,))
            else:
                day_id = connection.execute("INSERT INTO fitness_days (day_date) VALUES (?)", (day_date,)).lastrowid
            position = connection.execute("SELECT COUNT(*) FROM workout_exercises WHERE fitness_day_id = ?", (day_id,)).fetchone()[0]
            workout_exercise_id = connection.execute(
                "INSERT INTO workout_exercises (fitness_day_id, exercise_id, position) VALUES (?, ?, ?)",
                (day_id, exercise_id, position),
            ).lastrowid
            connection.executemany(
                "INSERT INTO workout_sets (workout_exercise_id, set_type, set_order, reps, weight) VALUES (?, ?, ?, ?, ?)",
                [(workout_exercise_id, *item) for item in clean_sets],
            )
    except sqlite3.IntegrityError:
        return jsonify(error="De oefening kon niet worden opgeslagen."), 400
    return jsonify(id=workout_exercise_id), 201


@app.delete("/api/workout-exercises/<int:workout_exercise_id>")
def delete_workout_exercise(workout_exercise_id):
    with db() as connection:
        result = connection.execute("DELETE FROM workout_exercises WHERE id = ?", (workout_exercise_id,))
    if not result.rowcount:
        return jsonify(error="Trainingsoefening niet gevonden."), 404
    return "", 204


@app.get("/api/health-days")
def get_health_days():
    with db() as connection:
        result = health_days_data(connection, valid_date(request.args.get("from")), valid_date(request.args.get("to")))
    return jsonify(result)


@app.post("/api/health-days")
def save_health_day():
    data = request.get_json(force=True)
    day_date = valid_date(data.get("date"))
    if not day_date:
        return jsonify(error="Kies een geldige datum."), 400
    allowed = {"ontbijt", "lunch", "avondeten", "tussendoortje"}
    clean_entries = []
    try:
        for entry in data.get("entries", []):
            category = str(entry["category"]).lower()
            product_id = int(entry["product_id"])
            grams = float(entry["grams"])
            if category not in allowed or grams <= 0:
                raise ValueError
            clean_entries.append((category, product_id, grams))
    except (KeyError, TypeError, ValueError):
        return jsonify(error="Controleer de producten en hoeveelheden."), 400
    if not clean_entries:
        return jsonify(error="Voeg minimaal één product of maaltijd toe."), 400
    try:
        with db() as connection:
            existing = connection.execute("SELECT id FROM health_days WHERE day_date = ?", (day_date,)).fetchone()
            if existing:
                day_id = existing["id"]
                connection.execute("DELETE FROM health_entries WHERE health_day_id = ?", (day_id,))
                connection.execute("UPDATE health_days SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (day_id,))
            else:
                day_id = connection.execute("INSERT INTO health_days (day_date) VALUES (?)", (day_date,)).lastrowid
            connection.executemany(
                "INSERT INTO health_entries (health_day_id, category, product_id, grams) VALUES (?, ?, ?, ?)",
                [(day_id, *entry) for entry in clean_entries],
            )
    except sqlite3.IntegrityError:
        return jsonify(error="Een gekozen product bestaat niet meer."), 400
    return jsonify(id=day_id, date=day_date), 201


@app.delete("/api/health-days/<int:day_id>")
def delete_health_day(day_id):
    with db() as connection:
        result = connection.execute("DELETE FROM health_days WHERE id = ?", (day_id,))
    if not result.rowcount:
        return jsonify(error="Dag niet gevonden."), 404
    return "", 204


@app.get("/api/overview-export.pdf")
def export_overview_pdf():
    start = valid_date(request.args.get("from"))
    end = valid_date(request.args.get("to"))
    if not start or not end or start > end:
        return jsonify(error="Kies een geldige periode."), 400
    with db() as connection:
        food_days = health_days_data(connection, start, end)
        fitness_days = fitness_days_data(connection, start, end)
        burn_rows = connection.execute(
            "SELECT day_date, burned_kcal FROM daily_burn WHERE day_date >= ? AND day_date <= ?",
            (start, end),
        ).fetchall()

    food_by_date = {day["date"]: day for day in food_days}
    fitness_by_date = {day["date"]: day for day in fitness_days}
    burn_by_date = {row["day_date"]: row["burned_kcal"] for row in burn_rows}
    dates = sorted(set(food_by_date) | set(fitness_by_date) | set(burn_by_date))
    total_eaten = sum(day["totals"]["energie"] for day in food_days)
    total_burned = sum(burn_by_date.values())
    total_volume = sum(
        item["reps"] * item["weight"]
        for day in fitness_days for exercise in day["exercises"] for item in exercise["sets"]
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=15*mm, leftMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm, title=f"MyHealth overzicht {start} tot {end}",
    )
    styles = getSampleStyleSheet()
    shown_start = datetime.fromisoformat(start).strftime("%d-%m-%Y")
    shown_end = datetime.fromisoformat(end).strftime("%d-%m-%Y")
    story = [
        Paragraph("MyHealth persoonlijk overzicht", styles["Title"]),
        Paragraph(f"Periode: {shown_start} t/m {shown_end}", styles["BodyText"]),
        Spacer(1, 5*mm),
    ]
    summary = Table([
        ["Gegeten", "Verbrand", "Balans", "Trainingsvolume"],
        [f"{total_eaten:.0f} kcal", f"{total_burned:.0f} kcal", f"{total_burned-total_eaten:.0f} kcal", f"{total_volume:.0f} kg"],
    ], colWidths=[43*mm]*4)
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#14261c")), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("BACKGROUND", (0,1), (-1,1), colors.HexColor("#eef3e5")), ("FONTNAME", (0,0), (-1,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9), ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("GRID", (0,0), (-1,-1), .3, colors.HexColor("#d3ddd5")), ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ]))
    story += [summary, Spacer(1, 7*mm)]
    if not dates:
        story.append(Paragraph("In deze periode zijn geen gegevens geregistreerd.", styles["BodyText"]))

    labels = {"ontbijt":"Ontbijt", "lunch":"Lunch", "avondeten":"Avondeten", "tussendoortje":"Tussendoortje"}
    for day_date in dates:
        food = food_by_date.get(day_date)
        fitness = fitness_by_date.get(day_date)
        eaten = food["totals"]["energie"] if food else 0
        burned = burn_by_date.get(day_date, 0)
        shown_date = datetime.fromisoformat(day_date).strftime("%d-%m-%Y")
        story += [Paragraph(shown_date, styles["Heading2"])]
        day_summary = Table([
            ["Gegeten", "Verbrand", "Balans"],
            [f"{eaten:.0f} kcal", f"{burned:.0f} kcal", f"{burned-eaten:.0f} kcal"],
        ], colWidths=[57.3*mm]*3)
        day_summary.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#e9ecf8")), ("TEXTCOLOR", (0,0), (-1,0), colors.HexColor("#4f4593")),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 8),
            ("ALIGN", (0,0), (-1,-1), "CENTER"), ("GRID", (0,0), (-1,-1), .3, colors.HexColor("#d8d8e8")),
        ]))
        story += [day_summary, Spacer(1, 3*mm)]

        if food:
            food_rows = [["Moment", "Product", "Gram", "kcal", "Eiwit", "KH", "Vet"]]
            for category, entries in food["categories"].items():
                for index, entry in enumerate(entries):
                    nutrients = entry["nutrients"]
                    food_rows.append([labels[category] if index == 0 else "", entry["name"], f"{entry['grams']:g}", f"{nutrients['energie']:.0f}", f"{nutrients['eiwit']:.1f}", f"{nutrients['koolhydraten']:.1f}", f"{nutrients['vet']:.1f}"])
            food_table = Table(food_rows, colWidths=[28*mm, 53*mm, 17*mm, 17*mm, 19*mm, 18*mm, 18*mm], repeatRows=1)
            food_table.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2f7651")), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 8),
                ("GRID", (0,0), (-1,-1), .3, colors.HexColor("#dfe4dc")), ("ALIGN", (2,1), (-1,-1), "RIGHT"),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f7f7f2")]),
            ]))
            story += [Paragraph("Voeding", styles["Heading3"]), food_table, Spacer(1, 3*mm)]

        if fitness and fitness["exercises"]:
            fitness_rows = [["Oefening", "Type", "Set", "Herhalingen", "Gewicht", "Volume"]]
            for exercise in fitness["exercises"]:
                for index, item in enumerate(exercise["sets"]):
                    fitness_rows.append([
                        exercise["name"] if index == 0 else "", "Warming-up" if item["set_type"] == "warmingup" else "Werkset",
                        item["set_order"], item["reps"], f"{item['weight']:g} kg", f"{item['reps']*item['weight']:g} kg",
                    ])
            fitness_table = Table(fitness_rows, colWidths=[55*mm, 28*mm, 16*mm, 26*mm, 23*mm, 27*mm], repeatRows=1)
            fitness_table.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#163b75")), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 8),
                ("GRID", (0,0), (-1,-1), .3, colors.HexColor("#cfe0fb")), ("ALIGN", (2,1), (-1,-1), "RIGHT"),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f4f8ff")]),
            ]))
            story += [Paragraph("Fitness", styles["Heading3"]), fitness_table]
        story.append(Spacer(1, 7*mm))

    doc.build(story)
    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name=f"myhealth_overzicht_{start}_tot_{end}.pdf")


@app.get("/api/health-export.pdf")
def export_health_pdf():
    start = valid_date(request.args.get("from"))
    end = valid_date(request.args.get("to"))
    if not start or not end or start > end:
        return jsonify(error="Kies een geldige periode."), 400
    with db() as connection:
        days = health_days_data(connection, start, end)
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=15*mm, leftMargin=15*mm, topMargin=15*mm, bottomMargin=15*mm,
                            title=f"MyHealth {start} tot {end}")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="RightSmall", parent=styles["BodyText"], alignment=TA_RIGHT, fontSize=8))
    story = [Paragraph("MyHealth voedingsoverzicht", styles["Title"]), Paragraph(f"Periode: {datetime.fromisoformat(start).strftime('%d-%m-%Y')} t/m {datetime.fromisoformat(end).strftime('%d-%m-%Y')}", styles["BodyText"]), Spacer(1, 7*mm)]
    labels = {"ontbijt":"Ontbijt", "lunch":"Lunch", "avondeten":"Avondeten", "tussendoortje":"Tussendoortje"}
    if not days:
        story.append(Paragraph("In deze periode zijn geen dagen geregistreerd.", styles["BodyText"]))
    for day in reversed(days):
        shown_date = datetime.fromisoformat(day["date"]).strftime("%d-%m-%Y")
        story += [Paragraph(shown_date, styles["Heading2"]), Spacer(1, 2*mm)]
        table_data = [["Moment", "Product", "Gram", "kcal", "Eiwit", "KH", "Vet"]]
        for category, entries in day["categories"].items():
            for index, entry in enumerate(entries):
                n = entry["nutrients"]
                table_data.append([labels[category] if index == 0 else "", entry["name"], f"{entry['grams']:g}", f"{n['energie']:.0f}", f"{n['eiwit']:.1f}", f"{n['koolhydraten']:.1f}", f"{n['vet']:.1f}"])
        t = day["totals"]
        table_data.append(["Totaal", "", "", f"{t['energie']:.0f}", f"{t['eiwit']:.1f}", f"{t['koolhydraten']:.1f}", f"{t['vet']:.1f}"])
        table = Table(table_data, colWidths=[28*mm, 53*mm, 17*mm, 17*mm, 19*mm, 18*mm, 18*mm], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#14261c")), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#eaf3c9")), ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"), ("GRID", (0,0), (-1,-1), .3, colors.HexColor("#dfe4dc")),
            ("FONTSIZE", (0,0), (-1,-1), 8), ("ALIGN", (2,1), (-1,-1), "RIGHT"), ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, colors.HexColor("#f7f7f2")]),
        ]))
        summary_data = [
            ["Energie", "Vet", "Verzadigd", "Koolhydraten", "Suikers", "Vezels", "Eiwit", "Zout"],
            [f"{t['energie']:.0f} kcal", f"{t['vet']:.1f} g", f"{t['verzadigd_vet']:.1f} g", f"{t['koolhydraten']:.1f} g", f"{t['suikers']:.1f} g", f"{t['vezels']:.1f} g", f"{t['eiwit']:.1f} g", f"{t['zout']:.3f} g"],
        ]
        summary = Table(summary_data, colWidths=[21.25*mm]*8)
        summary.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#eef3e5")), ("TEXTCOLOR", (0,0), (-1,0), colors.HexColor("#2f7651")),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 7),
            ("ALIGN", (0,0), (-1,-1), "CENTER"), ("GRID", (0,0), (-1,-1), .3, colors.HexColor("#dfe4dc")),
        ]))
        story += [table, Spacer(1, 2*mm), summary, Spacer(1, 7*mm)]
    doc.build(story)
    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name=f"myhealth_{start}_tot_{end}.pdf")


@app.get("/api/fitness-export.pdf")
def export_fitness_pdf():
    start = valid_date(request.args.get("from"))
    end = valid_date(request.args.get("to"))
    if not start or not end or start > end:
        return jsonify(error="Kies een geldige periode."), 400
    with db() as connection:
        days = fitness_days_data(connection, start, end)
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=15*mm, leftMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm, title=f"MyFitness {start} tot {end}",
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph("MyFitness trainingsoverzicht", styles["Title"]),
        Paragraph(
            f"Periode: {datetime.fromisoformat(start).strftime('%d-%m-%Y')} t/m {datetime.fromisoformat(end).strftime('%d-%m-%Y')}",
            styles["BodyText"],
        ),
        Spacer(1, 7*mm),
    ]
    if not days:
        story.append(Paragraph("In deze periode zijn geen trainingen geregistreerd.", styles["BodyText"]))
    for day in days:
        shown_date = datetime.fromisoformat(day["date"]).strftime("%d-%m-%Y")
        story += [Paragraph(shown_date, styles["Heading2"]), Spacer(1, 2*mm)]
        table_data = [["Oefening", "Type", "Set", "Herhalingen", "Gewicht", "Volume"]]
        day_volume = 0.0
        for exercise in day["exercises"]:
            for index, item in enumerate(exercise["sets"]):
                volume = item["reps"] * item["weight"]
                day_volume += volume
                table_data.append([
                    exercise["name"] if index == 0 else "",
                    "Warming-up" if item["set_type"] == "warmingup" else "Werkset",
                    item["set_order"], item["reps"], f"{item['weight']:g} kg", f"{volume:g} kg",
                ])
        table_data.append(["Dagtotaal", "", "", "", "", f"{day_volume:g} kg"])
        table = Table(table_data, colWidths=[55*mm, 28*mm, 16*mm, 26*mm, 23*mm, 27*mm], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#163b75")), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#dbeafe")), ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"), ("GRID", (0,0), (-1,-1), .3, colors.HexColor("#cfe0fb")),
            ("FONTSIZE", (0,0), (-1,-1), 8), ("ALIGN", (2,1), (-1,-1), "RIGHT"), ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, colors.HexColor("#f4f8ff")]),
        ]))
        story += [table, Spacer(1, 7*mm)]
    doc.build(story)
    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name=f"myfitness_{start}_tot_{end}.pdf")


init_db()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
