"""Search endpoint for the catalog.

Accepts a free-text query and returns matching product rows. The 500 only
appears for queries that contain quotes or special characters.
"""

import sqlite3
from flask import Blueprint, request, jsonify

search_bp = Blueprint("search", __name__)

DB_PATH = "/var/lib/app/catalog.db"


def _row_to_dict(row) -> dict:
    return {"id": row[0], "name": row[1], "price": row[2]}


@search_bp.route("/api/search", methods=["GET"])
def search():
    term = request.args.get("q", "")
    conn = sqlite3.connect(DB_PATH)
    try:
        # Direct string formatting into the query. Malformed input breaks the
        # statement and raises at execution time.
        query = (
            "SELECT id, name, price FROM products "
            "WHERE name LIKE '%" + term + "%'"
        )
        cursor = conn.execute(query)
        rows = cursor.fetchall()
        return jsonify([_row_to_dict(r) for r in rows]), 200
    except sqlite3.OperationalError as exc:
        return jsonify({"error": "internal error", "detail": str(exc)}), 500
    finally:
        conn.close()
