"""字元寬度、換行與顯示行資料結構。"""

import unicodedata


def cwidth(ch):
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def fitWidth(text, width):
    out = []
    used = 0
    for ch in text:
        cw = cwidth(ch)
        if used + cw > width:
            break
        out.append(ch)
        used += cw
    return "".join(out) + " " * (width - used)


def _isWordChar(ch):
    return ch.isascii() and (ch.isalnum() or ch in ("'", "-"))


def wrapMarked(chars, width):
    lines = []
    cur = []
    curw = 0
    pending = []
    pendw = 0

    def flushPending():
        nonlocal cur, curw, pending, pendw
        if not pending:
            return
        if curw + pendw <= width:
            cur.extend(pending)
            curw += pendw
        elif pendw <= width:
            lines.append(cur)
            cur = list(pending)
            curw = pendw
        else:
            for pc, pflag in pending:
                pw = cwidth(pc)
                if curw + pw > width:
                    lines.append(cur)
                    cur = []
                    curw = 0
                cur.append((pc, pflag))
                curw += pw
        pending = []
        pendw = 0

    for ch, flag in chars:
        if ch == "\n":
            flushPending()
            lines.append(cur)
            cur = []
            curw = 0
            continue
        if _isWordChar(ch):
            pending.append((ch, flag))
            pendw += cwidth(ch)
            continue
        flushPending()
        w = cwidth(ch)
        if curw + w > width:
            lines.append(cur)
            cur = []
            curw = 0
        cur.append((ch, flag))
        curw += w
    flushPending()
    lines.append(cur)
    return lines


def plainWrap(text, width):
    return wrapMarked([(c, 0) for c in text], width)


class Line:
    __slots__ = ("segments", "section", "clickable")

    def __init__(self, segments, section=None, clickable=False):
        self.segments = segments
        self.section = section
        self.clickable = clickable


class SegLine:
    __slots__ = ("segments", "verse")

    def __init__(self, segments, verse=None):
        self.segments = segments
        self.verse = verse
