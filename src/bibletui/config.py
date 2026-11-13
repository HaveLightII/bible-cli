"""使用者設定檔（config.json）：目前只記錄預設聖經模組與預設字典。"""

import json
import os

from .paths import userDataDir

configFileName = "config.json"
defaultKeys = {"bible": "defaultBible", "dict": "defaultDict"}


def configPath():
    return os.path.join(userDataDir(), configFileName)


def loadConfig():
    try:
        with open(configPath(), "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def saveConfig(data):
    path = configPath()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    part = path + ".part"
    try:
        with open(part, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(part, path)
    except OSError:
        try:
            os.remove(part)
        except OSError:
            pass
        raise


def getDefaultId(kind):
    value = loadConfig().get(defaultKeys[kind])
    return value if isinstance(value, str) and value else None


def setDefaultId(kind, value):
    data = loadConfig()
    if value:
        data[defaultKeys[kind]] = value
    else:
        data.pop(defaultKeys[kind], None)
    saveConfig(data)
