import os
import sqlite3
import sys
import tempfile

root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
sys.path.insert(0, os.path.join(root, "src"))

from bibletui import install as ins


def makeDb(path, tables):
    c = sqlite3.connect(path)
    for t in tables:
        c.execute(f"CREATE TABLE {t} (x)")
    c.commit()
    c.close()


tmp = tempfile.mkdtemp()
src = os.path.join(tmp, "src")
dest = os.path.join(tmp, "dest")
os.makedirs(src)

assert ins.matchKnownName("cuvt_bbl.mybible") == "cuvt.bbl.mybible"
assert ins.matchKnownName("Strong_Lite.dct.mybible") == "strong_lite.dct.mybible"
assert ins.matchKnownName("bible.db") == "bible.db"
assert ins.matchKnownName("other.db") is None

fakeCuv = os.path.join(src, "cuvt.bbl.mybible")
makeDb(fakeCuv, ["Bible"])
status, msg = ins.installOne(fakeCuv, dest)
assert status == "error" and "SHA-256 不符" in msg, msg
assert not os.path.exists(dest)
status, msg = ins.installOne(fakeCuv, dest, force=True)
assert status == "installed", msg
assert os.path.isfile(os.path.join(dest, "cuvt.bbl.mybible"))
assert not [n for n in os.listdir(dest) if n.endswith(".part")]
status, msg = ins.installOne(fakeCuv, dest)
assert status == "skipped", msg

other = os.path.join(src, "other", "cuvt.bbl.mybible")
os.makedirs(os.path.dirname(other))
makeDb(other, ["Bible", "Details"])
status, msg = ins.installOne(other, dest, force=False)
assert status == "error", msg
status, msg = ins.installOne(other, dest, force=True)
assert status == "installed", msg

custom = os.path.join(src, "my.bbl.mybible")
makeDb(custom, ["Bible"])
status, msg = ins.installOne(custom, dest)
assert status == "installed" and os.path.isfile(os.path.join(dest, "my.bbl.mybible")), msg

junk = os.path.join(src, "junk.mybible")
open(junk, "w").write("not sqlite")
assert ins.installOne(junk, dest)[0] == "error"
assert ins.installOne(os.path.join(src, "nope.txt"), dest)[0] == "error"

badDb = os.path.join(src, "bible.db")
makeDb(badDb, ["foo"])
status, msg = ins.installOne(badDb, dest)
assert status == "error" and "不是恢復本" in msg, msg
makeDb(badDb + "2", ["content", "book_name"])
os.rename(badDb + "2", os.path.join(src, "bible_db"))
status, msg = ins.installOne(os.path.join(src, "bible_db"), dest)
assert status == "installed" and "作者版本不同" in msg, msg
assert os.path.isfile(os.path.join(dest, "bible.db"))

found = ins.findInDir(src)
assert [os.path.basename(p) for p in found] == ["bible.db", "bible_db", "cuvt.bbl.mybible"], found
assert ins.findInDir(os.path.join(tmp, "missing")) == []
print("install ok")
