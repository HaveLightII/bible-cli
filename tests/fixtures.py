"""測試用合成資料：內容皆為虛構，不含任何聖經經文或版權資料。"""

import atexit
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
srcDir = os.path.join(root, "src")
if srcDir not in sys.path:
    sys.path.insert(0, srcDir)

from bibletui.books import zhBookNames, enBookNames

_siteDir = None


def installedLikeSite():
    """複製套件到沒有 pyproject.toml 的暫存位置，模擬安裝版（不搜尋倉庫根目錄），
    避免開發者倉庫內的真實資料庫干擾測試。"""
    global _siteDir
    if _siteDir is None:
        _siteDir = tempfile.mkdtemp()
        atexit.register(shutil.rmtree, _siteDir, True)
        shutil.copytree(
            os.path.join(srcDir, "bibletui"), os.path.join(_siteDir, "bibletui"),
            ignore=shutil.ignore_patterns("__pycache__"),
        )
    return _siteDir


def makeRecoveryDb(path):
    c = sqlite3.connect(path)
    c.executescript(
        """
        CREATE TABLE book_name(language TEXT, book_index INT, name TEXT, acronym_name TEXT);
        CREATE TABLE content(language TEXT, book_index INT, chapter INT, section INT, content TEXT, flag INT DEFAULT 0);
        CREATE TABLE outline(language TEXT, book_index INT, chapter INT, section INT, flag INT, level INT, outline TEXT);
        CREATE TABLE footnote(language TEXT, book_index INT, chapter INT, section INT, location INT, seq INT, note TEXT);
        CREATE TABLE book_intro(language TEXT, book_index INT, type INT, intro TEXT);
        """
    )
    for i in range(66):
        c.execute("INSERT INTO book_name VALUES('big5',?,?,?)", (i + 1, zhBookNames[i], zhBookNames[i][0]))
        c.execute("INSERT INTO book_name VALUES('eng',?,?,?)", (i + 1, enBookNames[i], enBookNames[i][:3]))
    for verse in (1, 2, 3):
        c.execute("INSERT INTO content VALUES('big5',1,1,?,?,0)", (verse, f"恢復本測試甲乙丙{verse}"))
        c.execute("INSERT INTO content VALUES('cuv_big5',1,1,?,?,0)", (verse, f"和合測試丁戊己{verse}"))
        c.execute("INSERT INTO content VALUES('eng',1,1,?,?,0)", (verse, f"english test line {verse}"))
    c.execute("INSERT INTO outline VALUES('big5',1,1,1,0,1,'測試綱目')")
    c.execute("INSERT INTO footnote VALUES('big5',1,1,1,2,1,'測試註解')")
    c.execute("INSERT INTO book_intro VALUES('big5',1,1,'測試簡介')")
    c.commit()
    c.close()


def makeCuvModule(path):
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE Bible(Book INT, Chapter INT, Verse INT, Scripture TEXT)")
    rows = [
        (1, 1, 1, "測試<WH1>，\u3000詞<WH2>甲乙丙<WG3>。"),
        (1, 1, 2, "第二節<WH>文字<WG0>庚辛。"),
        (1, 2, 1, "另一章<WH4>內容壬癸。"),
        (43, 3, 1, "新約測試<WG5>甲乙丙。"),
    ]
    c.executemany("INSERT INTO Bible VALUES(?,?,?,?)", rows)
    c.commit()
    c.close()


def makeGbfModule(path, abbr="Eng/T", strong=0, ot=1, nt=1):
    """虛構的英文模組，帶 MySword 的 GBF 格式標記，不含任何聖經經文。"""
    c = sqlite3.connect(path)
    c.execute(
        "CREATE TABLE Details (Description NVARCHAR(255),Abbreviation NVARCHAR(50),Comments TEXT,"
        "Version TEXT,VersionDate DATETIME,PublishDate DATETIME,RightToLeft BOOL,OT BOOL,NT BOOL,Strong BOOL)"
    )
    c.execute(
        "INSERT INTO Details VALUES(?,?,?,?,?,?,0,?,?,?)",
        (f"Synthetic module {abbr}", abbr, "test", "1.0", "2026-01-01", None, ot, nt, strong),
    )
    c.execute("CREATE TABLE Bible(Book INT, Chapter INT, Verse INT, Scripture TEXT)")
    rows = [
        (1, 1, 1, "<TS>Sample Title<Ts><FI>Lorem<Fi> ipsum<RF>a note<Rf> dolor<WTN-NSF> sit<CM>"),
        (1, 1, 2, "Amet&nbsp;consectetur   <FR>adipiscing<Fr> elit<RX43.3.16>."),
        (1, 1, 3, "Plain   Text Verse"),
        (43, 3, 1, "<PI1><PF0>Nine Newest <i>verse</i> here"),
    ]
    c.executemany("INSERT INTO Bible VALUES(?,?,?,?)", rows)
    c.commit()
    c.close()


def makeDictModule(path):
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE dictionary(relativeorder INT, word TEXT, data TEXT)")
    c.execute("INSERT INTO dictionary VALUES(1,'G26','<b>測試字義</b><br>第二行說明')")
    c.execute("INSERT INTO dictionary VALUES(2,'H157','<b>另一個字義</b>')")
    c.commit()
    c.close()


class TempCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.work = os.path.join(self.tmp, "work")
        self.files = os.path.join(self.tmp, "files")
        os.makedirs(self.work)
        os.makedirs(self.files)
        self.dataDir = os.path.join(self.tmp, "userdata")
        self.dbPath = os.path.join(self.files, "bible.db")
        self.cuvPath = os.path.join(self.files, "cuvt.bbl.mybible")
        self.dictPath = os.path.join(self.files, "strong_lite.dct.mybible")

    def makeAll(self):
        makeRecoveryDb(self.dbPath)
        makeCuvModule(self.cuvPath)
        makeDictModule(self.dictPath)

    def run_(self, args, cwd=None, extraEnv=None, timeout=60):
        env = dict(os.environ)
        env.update({
            "PYTHONPATH": installedLikeSite(),
            "BIBLE_CLI_DATA_DIR": self.dataDir,
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
        })
        for name in ("BIBLE_STRONG_DICT", "BIBLE_STRONG_BIBLE"):
            env.pop(name, None)
        if extraEnv:
            env.update(extraEnv)
        return subprocess.run(
            [sys.executable, "-m", "bibletui"] + list(args),
            capture_output=True, text=True, encoding="utf-8",
            env=env, cwd=cwd or self.work, timeout=timeout,
        )
