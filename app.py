from __future__ import annotations

import sqlite3
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "voeding.db"

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

app = Flask(__name__)


def db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    with db() as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE,
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
        """)
        for name, values in START_PRODUCTS.items():
            connection.execute(
                f"INSERT OR IGNORE INTO products (name, {', '.join(NUTRIENTS)}) VALUES (?, {', '.join('?' for _ in NUTRIENTS)})",
                (name, *values),
            )


def product_dict(row):
    return {key: row[key] for key in ("id", "name", *NUTRIENTS)}


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
    try:
        values = [max(0.0, float(data.get(key, 0))) for key in NUTRIENTS]
    except (TypeError, ValueError):
        return jsonify(error="Gebruik alleen geldige, positieve getallen."), 400
    try:
        with db() as connection:
            cursor = connection.execute(
                f"INSERT INTO products (name, {', '.join(NUTRIENTS)}) VALUES (?, {', '.join('?' for _ in NUTRIENTS)})",
                (name, *values),
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


init_db()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
