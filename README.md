# TW+ H2H 聯盟名人堂

Yahoo Fantasy NBA「TW+ H2H」14 隊聯盟 2023–2025 三季的紀念頁：歷屆冠軍、歷季排名、三季總表、兩兩交手、季後賽對戰樹、每季類別王、賽程運氣、紀錄牆、隊名博物館。

整頁是一個靜態 HTML，不需要伺服器，GitHub Pages 直接開 `index.html`。

## 檔案

| 檔案 | 用途 |
|---|---|
| `index.html` | 成品，`build.py` 產生，別直接改 |
| `template.html` | 頁面原始碼（版面、樣式、互動），資料位置是 `__DATA__` |
| `page_data.json` | 頁面用的資料 |
| `build.py` | `page_data.json` 塞進 `template.html` → `index.html` |
| `scripts/page_data.py` | 從 yahooFantasy 爬下來的聯盟存檔算出 `page_data.json` |

## 更新

改版面：改 `template.html`，再跑

```sh
python3 build.py
```

有新一季的資料：先用 yahooFantasy 把存檔爬好，再

```sh
python3 scripts/page_data.py ~/server/github/yahooFantasy/data/archive page_data.json
python3 build.py
```

只用 Python 標準函式庫，不用安裝套件。
