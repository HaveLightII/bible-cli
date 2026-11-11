"""經文、註解與字典 HTML 的文字轉譯。"""

import re
from html.parser import HTMLParser

from .constants import (
    bold,
    cyan,
    dim,
    red,
    reset,
)
from .sources.cuv import strongTagPattern


def insertFootnoteMarkers(content, footnotes, color=True):
    if not footnotes:
        return content
    result = content
    for loc, seq in sorted(footnotes, key=lambda x: -x[0]):
        idx = loc - 1
        if idx < 0 or idx > len(result):
            continue
        marker = f"{seq}"
        if color:
            marker = f"{red}{marker}{reset}"
        result = result[:idx] + marker + result[idx:]
    return result


class DictHtmlRenderer(HTMLParser):

    def __init__(self, color=True):
        super().__init__(convert_charrefs=True)
        self.color = color
        self.lines = [""]
        self.olStack = []

    def _write(self, text):
        self.lines[-1] += text

    def _newline(self):
        if self.lines[-1] != "":
            self.lines.append("")

    def handle_starttag(self, tag, attrs):
        if tag in ("p", "br"):
            self._newline()
        elif tag == "ol":
            self.olStack.append(0)
        elif tag == "li":
            self._newline()
            depth = len(self.olStack)
            if self.olStack:
                self.olStack[-1] += 1
                num = self.olStack[-1]
            else:
                num = 1
            indent = "  " * max(0, depth - 1)
            marker = f"{num}." if depth <= 1 else f"{chr(96 + num)})"
            self._write(f"{indent}{marker} ")
        elif tag in ("strong", "b"):
            if self.color:
                self._write(bold)
        elif tag in ("i", "em"):
            if self.color:
                self._write(dim)
        elif tag == "a":
            if self.color:
                self._write(cyan)

    def handle_endtag(self, tag):
        if tag == "ol":
            if self.olStack:
                self.olStack.pop()
            self._newline()
        elif tag == "li":
            self._newline()
        elif tag == "p":
            self._newline()
        elif tag in ("strong", "b", "i", "em", "a"):
            if self.color:
                self._write(reset)

    def handle_data(self, data):
        self._write(data)

    def getText(self):
        text = "\n".join(self.lines)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip("\n")


def renderDictHtml(htmlText, color=True):
    parser = DictHtmlRenderer(color=color)
    parser.feed(htmlText)
    return parser.getText()


def splitStrongVerse(scripture):
    parts = re.split(r"(<W[GH]\d*>)", scripture)
    segments = []
    curText, curCodes = "", []
    first = True
    for part in parts:
        m = strongTagPattern.fullmatch(part)
        if m:
            if len(m.group(1)) > 1:
                curCodes.append(m.group(1))
        elif part == "":
            continue
        else:
            if not first:
                segments.append((curText, curCodes))
            curText, curCodes = part, []
            first = False
    segments.append((curText, curCodes))
    return segments


def renderStrongVerse(segments, color):
    displayParts = []
    legend = {}
    idx = 0
    for text, codes in segments:
        if codes:
            idx += 1
            legend[idx] = codes
            marker = f"[{idx}]"
            if color:
                displayParts.append(f"{text}{dim}{marker}{reset}")
            else:
                displayParts.append(f"{text}{marker}")
        else:
            displayParts.append(text)
    return "".join(displayParts), legend
