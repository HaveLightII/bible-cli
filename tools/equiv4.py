import importlib.util
import sqlite3
import sys


def load(path):
    spec = importlib.util.spec_from_file_location("bibleMod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    biblePath = sys.argv[1] if len(sys.argv) > 1 else "bible.py"
    dbPath = sys.argv[2] if len(sys.argv) > 2 else "bible.db"
    mod = load(biblePath)
    conn = sqlite3.connect(dbPath)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT DISTINCT language, book_index, name, acronym_name FROM book_name"
    ).fetchall()
    total = 0
    gaps = []
    wrong = []
    for r in rows:
        for key in ("name", "acronym_name"):
            value = r[key]
            if not value or not str(value).strip():
                continue
            total += 1
            expected = mod.resolveBook(conn, value)
            offline = mod.resolveAnyBookName(value, None)
            if offline is None:
                gaps.append((r["language"], key, value, expected))
            elif offline != expected:
                wrong.append((r["language"], key, value, expected, offline))
    print(f"checked {total} names and acronyms")
    print(f"offline unresolved: {len(gaps)}")
    for g in gaps:
        print("  gap", g)
    print(f"offline resolved to a different book: {len(wrong)}")
    for w in wrong:
        print("  wrong", w)
    print("ok" if not wrong else "mismatch")


if __name__ == "__main__":
    main()
