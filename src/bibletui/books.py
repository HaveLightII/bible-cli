"""書卷名稱與別名表。"""

import re

from .sources.recovery import resolveBook


zhBookNames = [
    "創世記", "出埃及記", "利未記", "民數記", "申命記",
    "約書亞記", "士師記", "路得記", "撒母耳記上", "撒母耳記下",
    "列王紀上", "列王紀下", "歷代志上", "歷代志下", "以斯拉記",
    "尼希米記", "以斯帖記", "約伯記", "詩篇", "箴言",
    "傳道書", "雅歌", "以賽亞書", "耶利米書", "耶利米哀歌",
    "以西結書", "但以理書", "何西阿書", "約珥書", "阿摩司書",
    "俄巴底亞書", "約拿書", "彌迦書", "那鴻書", "哈巴谷書",
    "西番雅書", "哈該書", "撒迦利亞書", "瑪拉基書",
    "馬太福音", "馬可福音", "路加福音", "約翰福音", "使徒行傳",
    "羅馬書", "哥林多前書", "哥林多後書", "加拉太書", "以弗所書",
    "腓立比書", "歌羅西書", "帖撒羅尼迦前書", "帖撒羅尼迦後書",
    "提摩太前書", "提摩太後書", "提多書", "腓利門書", "希伯來書",
    "雅各書", "彼得前書", "彼得後書", "約翰一書", "約翰二書",
    "約翰三書", "猶大書", "啟示錄",
]

enBookNames = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
    "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel",
    "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra",
    "Nehemiah", "Esther", "Job", "Psalms", "Proverbs",
    "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah", "Lamentations",
    "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk",
    "Zephaniah", "Haggai", "Zechariah", "Malachi",
    "Matthew", "Mark", "Luke", "John", "Acts",
    "Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians",
    "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
    "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews",
    "James", "1 Peter", "2 Peter", "1 John", "2 John",
    "3 John", "Jude", "Revelation",
]

bookAliasZh = [
    "創", "出", "利", "民", "申", "書", "士", "得", "撒上", "撒下",
    "王上", "王下", "代上", "代下", "拉", "尼", "斯", "伯", "詩", "箴",
    "傳", "歌", "賽", "耶", "哀", "結", "但", "何", "珥", "摩",
    "俄", "拿", "彌", "鴻", "哈", "番", "該", "亞", "瑪",
    "太", "可", "路", "約", "徒", "羅", "林前", "林後", "加", "弗",
    "腓", "西", "帖前", "帖後", "提前", "提後", "多", "門", "來",
    "雅", "彼前", "彼後", "約一", "約二", "約三", "猶", "啟",
]

bookAliasEn = [
    ("gen", "gn"), ("ex", "exo", "exod"), ("lev", "lv"), ("num", "nu"),
    ("deut", "dt", "deu"), ("josh", "jos"), ("judg", "jdg"), ("ru", "rth"),
    ("1sam", "1sa"), ("2sam", "2sa"), ("1kgs", "1ki", "1kin"),
    ("2kgs", "2ki", "2kin"), ("1chr", "1ch", "1chron"), ("2chr", "2ch", "2chron"),
    ("ezr",), ("neh",), ("esth", "est"), ("jb",), ("ps", "psa", "psalm"),
    ("prov", "pro"), ("eccl", "ecc", "eccles"), ("song", "sos", "sng", "songofsongs", "ss"),
    ("isa", "is"), ("jer",), ("lam",), ("ezek", "eze"), ("dan", "dn"),
    ("hos",), ("joel", "jl"), ("amos", "am"), ("obad", "oba", "ob"),
    ("jon", "jnh"), ("mic",), ("nah", "na"), ("hab",), ("zeph", "zep"),
    ("hag",), ("zech", "zec"), ("mal",),
    ("matt", "mt", "mat"), ("mk", "mar"), ("lk", "luk"), ("jn", "joh"),
    ("act",), ("rom", "ro"), ("1cor", "1co"), ("2cor", "2co"), ("gal",),
    ("eph",), ("phil", "php", "phi"), ("col",), ("1thess", "1th", "1thes"),
    ("2thess", "2th", "2thes"), ("1tim", "1ti"), ("2tim", "2ti"), ("tit",),
    ("phlm", "phm", "philem"), ("heb",), ("jas", "jam"), ("1pet", "1pe", "1pt"),
    ("2pet", "2pe", "2pt"), ("1jn", "1jo", "1joh"), ("2jn", "2jo", "2joh"),
    ("3jn", "3jo", "3joh"), ("jd",), ("rev", "rv", "apoc"),
]


def _normBookKey(name):
    return re.sub(r"[\s.]+", "", name.lower())


def _buildBookAliasMap():
    mapping = {}
    for i, a in enumerate(bookAliasZh, start=1):
        mapping[_normBookKey(a)] = i
    for i, group in enumerate(bookAliasEn, start=1):
        for a in group:
            mapping.setdefault(_normBookKey(a), i)
    extra = {"約壹": 62, "約貳": 63, "約參": 64}
    for k, v in extra.items():
        mapping.setdefault(k, v)
    return mapping


bookAliasMap = _buildBookAliasMap()


def resolveAnyBookName(name, conn=None):
    if name is None:
        return None
    name = name.strip()
    if not name:
        return None
    if name.isdigit():
        idx = int(name)
        return idx if 1 <= idx <= 66 else None
    for i, n in enumerate(zhBookNames, start=1):
        if n == name:
            return i
    norm = re.sub(r"\s+", "", name.lower())
    for i, n in enumerate(enBookNames, start=1):
        if re.sub(r"\s+", "", n.lower()) == norm:
            return i
    if conn is not None:
        idx = resolveBook(conn, name)
        if idx:
            return idx
    else:
        idx = bookAliasMap.get(_normBookKey(name))
        if idx:
            return idx
    matches = [i for i, n in enumerate(zhBookNames, start=1) if name in n]
    if len(matches) == 1:
        return matches[0]
    matches = [i for i, n in enumerate(enBookNames, start=1) if norm and norm in re.sub(r"\s+", "", n.lower())]
    if len(matches) == 1:
        return matches[0]
    return None
