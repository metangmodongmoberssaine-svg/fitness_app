import os
import sys
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))          # dossier backend/

try:
    import pymysql
except ImportError:
    sys.exit("pymysql n'est pas installé. Lancez :  pip install pymysql cryptography")

from database import db as dbmod                    # noqa: E402

# Ordre imposé par les clés étrangères (parents avant enfants)
TABLES = [
    "utilisateurs", "exercices", "regles_comptage", "objectifs",
    "seances_entrainement", "repetitions", "retours_correction", "notifications",
]


def main():
    sqlite_path = dbmod.SQLITE_PATH
    if not os.path.exists(sqlite_path):
        sys.exit(f"Base SQLite introuvable : {sqlite_path}")

    print(f"[1/4] Connexion à MySQL {dbmod.DB_HOST}:{dbmod.DB_PORT} (base « {dbmod.DB_NAME} »)...")
    try:
        dbmod.init_db()
        probe = pymysql.connect(host=dbmod.DB_HOST, port=dbmod.DB_PORT, user=dbmod.DB_USER,
                                password=dbmod.DB_PASSWORD, database=dbmod.DB_NAME, charset="utf8mb4")
    except Exception as e:
        sys.exit(f"Connexion MySQL impossible : {e}\n"
                 "Vérifiez que MySQL est démarré (WampServer vert / XAMPP) et DB_USER / DB_PASSWORD.")
    probe.close()

    src = sqlite3.connect(sqlite_path)
    src.row_factory = sqlite3.Row
    dst = pymysql.connect(host=dbmod.DB_HOST, port=dbmod.DB_PORT, user=dbmod.DB_USER,
                          password=dbmod.DB_PASSWORD, database=dbmod.DB_NAME, charset="utf8mb4")
    cur = dst.cursor()

    print("[2/4] Vidage des tables MySQL...")
    cur.execute("SET FOREIGN_KEY_CHECKS = 0")
    for t in reversed(TABLES):
        cur.execute(f"TRUNCATE TABLE `{t}`")
    cur.execute("SET FOREIGN_KEY_CHECKS = 1")

    print("[3/4] Copie des données...")
    cur.execute("SET FOREIGN_KEY_CHECKS = 0")
    for t in TABLES:
        rows = src.execute(f"SELECT * FROM {t}").fetchall()
        if not rows:
            print(f"      {t:<24} 0 ligne")
            continue
        cols = rows[0].keys()
        sql = f"INSERT INTO `{t}` ({', '.join('`'+c+'`' for c in cols)}) VALUES ({', '.join(['%s']*len(cols))})"
        cur.executemany(sql, [tuple(r[c] for c in cols) for r in rows])
        print(f"      {t:<24} {len(rows)} ligne(s)")
    cur.execute("SET FOREIGN_KEY_CHECKS = 1")
    dst.commit()

    print("[4/4] Vérification...")
    ok = True
    for t in TABLES:
        n_src = src.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        cur.execute(f"SELECT COUNT(*) FROM `{t}`")
        n_dst = cur.fetchone()[0]
        ok &= (n_src == n_dst)
        print(f"      {t:<24} SQLite={n_src:<4} MySQL={n_dst:<4} {'OK' if n_src == n_dst else 'ERREUR'}")
    dst.close(); src.close()
    print("\nMigration terminée avec succès." if ok else "\nATTENTION : des écarts existent.")


if __name__ == "__main__":
    main()