import os, sys, sqlite3, tempfile, shutil, importlib.util, io
spec = importlib.util.spec_from_file_location("b", sys.argv[1])
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)

H = "/home/u"
assert b.userDataDir("win32", {"APPDATA": r"C:\Users\u\AppData\Roaming"}, H).endswith("bible-cli")
assert b.userDataDir("win32", {}, H) == os.path.join(H, "AppData", "Roaming", "bible-cli")
assert b.userDataDir("darwin", {}, H) == os.path.join(H, "Library", "Application Support", "bible-cli")
assert b.userDataDir("linux", {}, H) == os.path.join(H, ".local/share/bible-cli")
assert b.userDataDir("linux", {"XDG_DATA_HOME": "/x/y"}, H) == "/x/y/bible-cli"
assert b.userDataDir("linux", {"XDG_DATA_HOME": "rel"}, H) == os.path.join(H, ".local/share/bible-cli")
assert b.userDataDir("linux", {"BIBLE_CLI_DATA_DIR": "/o"}, H) == "/o"
print("paths ok")

tmp = tempfile.mkdtemp()
data = os.path.join(tmp, "data"); script = os.path.join(tmp, "script"); os.makedirs(script)
b.noteDbDefaultPath = os.path.join(data, "bible-note.db")
b.noteDbPointerPath = os.path.join(data, "bible-note.db.path")
b.legacyDeclinedPath = os.path.join(data, ".legacy-declined")
b.legacyNoteDbPath = os.path.join(script, ".bible-note.db")
b.legacyNoteDbPointerPath = os.path.join(script, ".bible-note.db.path")

assert b.resolveNoteDbPath() is None and b.findLegacyNoteDb() is None
assert b._loadStoredSettingsDict() == {}

c = sqlite3.connect(b.legacyNoteDbPath)
c.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT)")
c.execute("INSERT INTO settings VALUES ('default_mode','strong')"); c.commit(); c.close()

out = io.StringIO()
assert b.migrateLegacyNoteDb(lambda q: "n", out) == "declined"
assert os.path.isfile(b.legacyDeclinedPath) and b.findLegacyNoteDb() is None
os.remove(b.legacyDeclinedPath)
assert b.migrateLegacyNoteDb(lambda q: "", out) == "migrated"
assert os.path.isfile(b.legacyNoteDbPath) and os.path.isfile(b.noteDbDefaultPath)
assert b._loadStoredSettingsDict() == {"default_mode": "strong"}
conn = b.openNoteDb(b.noteDbDefaultPath)
assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
assert {r[0] for r in conn.execute("select name from sqlite_master where type='table'")} >= {"settings","notes","bookmarks","refs"}
assert b.migrateLegacyNoteDb(lambda q: 1/0, out) is None
conn.close()

custom = os.path.join(tmp, "elsewhere", "n.db")
b.openNoteDb(custom).close()
b.writeNoteDbPointer(custom)
assert b.resolveNoteDbPath() == custom
os.remove(b.noteDbPointerPath)

shutil.rmtree(data); os.remove(b.legacyNoteDbPath)
open(b.legacyNoteDbPointerPath, "w").write(custom)
assert b.findLegacyNoteDb() == ("link", custom)
assert b.migrateLegacyNoteDb(lambda q: "y", out) == "migrated" and b.resolveNoteDbPath() == custom
print("migration ok")

os.environ[b.dataDirEnvName] = data
shutil.copy(sys.argv[2], data) if os.path.isdir(data) else (os.makedirs(data), shutil.copy(sys.argv[2], data))
r = b.resolveResources(None, {})
assert r["strongBible"] == os.path.join(data, "cuvt.bbl.mybible"), r
r = b.resolveResources(None, {"strong_db_path": sys.argv[2]})
assert r["strongBible"] == sys.argv[2]
print("resolve ok")
shutil.rmtree(tmp)
