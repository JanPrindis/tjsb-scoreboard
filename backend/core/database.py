import sqlite3

DB_PATH = "roster.db"


def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as db:
        db.execute("CREATE TABLE IF NOT EXISTS rosters (id INTEGER PRIMARY KEY, name TEXT)")
        db.execute("""
                   CREATE TABLE IF NOT EXISTS players
                   (
                       id INTEGER PRIMARY KEY,
                       roster_id INTEGER,
                       team TEXT,
                       number INTEGER,
                       first_name TEXT,
                       last_name TEXT,
                       is_active BOOLEAN DEFAULT 1
                   )
                   """)
        db.commit()


def _map_player(p_row):
    p = dict(p_row)
    p["is_active"] = bool(p.get("is_active", 1))
    return p


def get_all_rosters():
    with get_db() as db:
        rosters = db.execute("SELECT * FROM rosters").fetchall()
        result = []
        for r in rosters:
            players = db.execute("SELECT * FROM players WHERE roster_id = ? ORDER BY id ASC", (r["id"],)).fetchall()
            result.append({
                "id": r["id"],
                "name": r["name"],
                "home": [_map_player(p) for p in players if p["team"] == "home"],
                "away": [_map_player(p) for p in players if p["team"] == "away"]
            })
        return result


def get_full_roster(roster_id: int):
    with get_db() as db:
        r = db.execute("SELECT * FROM rosters WHERE id = ?", (roster_id,)).fetchone()
        if not r: return None
        players = db.execute("SELECT * FROM players WHERE roster_id = ? ORDER BY id ASC", (roster_id,)).fetchall()
        return {
            "id": r["id"],
            "name": r["name"],
            "home": [_map_player(p) for p in players if p["team"] == "home"],
            "away": [_map_player(p) for p in players if p["team"] == "away"]
        }


def create_roster(name: str):
    with get_db() as db:
        cur = db.execute("INSERT INTO rosters (name) VALUES (?)", (name,))
        db.commit()
        return cur.lastrowid


def update_roster(roster_id: int, name: str, home_players: list, away_players: list):
    with get_db() as db:
        db.execute("UPDATE rosters SET name = ? WHERE id = ?", (name, roster_id))
        db.execute("DELETE FROM players WHERE roster_id = ?", (roster_id,))

        for p in home_players:
            db.execute(
                "INSERT INTO players (roster_id, team, number, first_name, last_name, is_active) VALUES (?, 'home', ?, ?, ?, ?)",
                (roster_id, p['number'], p.get('first_name', ''), p['last_name'], int(p.get('is_active', True))))

        for p in away_players:
            db.execute(
                "INSERT INTO players (roster_id, team, number, first_name, last_name, is_active) VALUES (?, 'away', ?, ?, ?, ?)",
                (roster_id, p['number'], p.get('first_name', ''), p['last_name'], int(p.get('is_active', True))))
        db.commit()


def delete_roster(roster_id: int):
    with get_db() as db:
        db.execute("DELETE FROM rosters WHERE id = ?", (roster_id,))
        db.execute("DELETE FROM players WHERE roster_id = ?", (roster_id,))
        db.commit()
