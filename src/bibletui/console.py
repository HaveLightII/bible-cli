"""主控台初始化、色彩支援判斷與剪貼簿複製。"""

import ctypes
import os
import subprocess
import sys


isWindows = os.name == "nt"


def setupConsole():
    for stream in (sys.stdout, sys.stderr, sys.stdin):
        try:
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    if not isWindows:
        return

    try:
        os.system("chcp 65001 >NUL 2>&1")
    except Exception:
        pass

    try:
        kernel32 = ctypes.windll.kernel32
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        for handleId in (-11, -12):
            handle = kernel32.GetStdHandle(handleId)
            mode = ctypes.c_uint32()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(
                    handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING
                )
    except Exception:
        pass


def supportsAnsiColor():
    try:
        return sys.stdout.isatty()
    except Exception:
        return False


def copyToClipboardText(text):
    if not text:
        return False
    if isWindows:
        candidates = [["clip"]]
    elif sys.platform == "darwin":
        candidates = [["pbcopy"]]
    else:
        candidates = [
            ["termux-clipboard-set"],
            ["wl-copy"],
            ["xclip", "-selection", "clipboard"],
            ["xsel", "--clipboard", "--input"],
        ]
    payload = text.encode("utf-8", errors="replace")
    for cmd in candidates:
        try:
            proc = subprocess.run(
                cmd, input=payload,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=3,
            )
        except (FileNotFoundError, OSError, subprocess.SubprocessError):
            continue
        if proc.returncode == 0:
            return True
    return False
