"""共用的訊息字串、語言群組、簡介類型與 ANSI 色碼。"""


missingContentMsg = "此資料來源不含此內容"


needRecoveryMsg = missingContentMsg + "（需要恢復本資料庫 bible.db）"


zhLangs = ("big5", "gb", "cuv_big5", "cuv_gb")


enLangs = ("eng", "darby_eng", "kjv_eng")


introTypeLabel = {
    1: "著者",
    2: "著時",
    3: "著地",
    4: "受者",
    5: "主旨",
    6: "涵蓋時段",
}


red = "\033[31m"


cyan = "\033[36m"


bold = "\033[1m"


dim = "\033[2m"


reset = "\033[0m"
