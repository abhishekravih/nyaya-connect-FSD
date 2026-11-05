"""
NyayaConnect Database Module (Person 4: System Integration)
File: /backend/database.py
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("nyayaconnect.database")

DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "nyayaconnect_secret_pass")
DB_DATABASE = os.getenv("DB_DATABASE", "nyayaconnect")

DATABASE_URL = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DATABASE}"

async def get_lawyers_by_category_db(category: str) -> List[Dict[str, Any]]:
    """
    Attempts to fetch verified lawyers matching category from MySQL,
    sorted by consultation_fee ASC. Returns empty list if MySQL is unavailable.
    """
    try:
        import mysql.connector
        cnx = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_DATABASE,
            connection_timeout=2
        )
        cursor = cnx.cursor(dictionary=True)
        query = """
            SELECT id, name, category AS specialization, bar_council_id, experience_years,
                   consultation_fee, rating, reviews_count, verified, languages, location, milestones
            FROM lawyers
            WHERE category = %s AND verified = 1
            ORDER BY consultation_fee ASC
            LIMIT 3
        """
        cursor.execute(query, (category,))
        rows = cursor.fetchall()
        cursor.close()
        cnx.close()

        results = []
        for row in rows:
            langs = row.get("languages", "")
            if isinstance(langs, str):
                langs_list = [l.strip() for l in langs.split(",") if l.strip()]
            else:
                langs_list = langs or []

            milestones_raw = row.get("milestones", "[]")
            try:
                milestones_list = json.loads(milestones_raw) if isinstance(milestones_raw, str) else milestones_raw
            except Exception:
                milestones_list = [
                    "1. Case Evaluation & Evidence Audit",
                    "2. Legal Notice & Pleadings Formulation",
                    "3. Commission/Court Filing",
                    "4. Final Decree & Settlement Enforcement"
                ]

            results.append({
                "id": row["id"],
                "name": row["name"],
                "specialization": row["specialization"],
                "bar_council_id": row["bar_council_id"],
                "experience_years": row["experience_years"],
                "consultation_fee": float(row["consultation_fee"]),
                "rating": float(row["rating"]),
                "reviews_count": row["reviews_count"],
                "verified": bool(row["verified"]),
                "languages_spoken": langs_list,
                "location": row["location"],
                "milestones": milestones_list
            })
        return results
    except Exception as e:
        logger.debug(f"MySQL query failed (using mock dataset): {e}")
        return []
