# preflop-matrix

6-max 翻前「位置對位置」頻率熱力圖。讀 GG Rush & Cash 手牌與理論範圍資料夾，輸出單一 HTML，
顯示三種頻率：**理論**、**Hero（我）**、**玩家池**。零第三方執行期依賴。

## 安裝

```bash
uv tool install .          # 安裝成全域指令 preflop-matrix
uv run preflop-matrix ...  # 或在專案內直接執行
```

需要 Python 3.12+。開發：`uv sync && uv run pytest`。

## 用法

```bash
preflop-matrix --hands <GG手牌資料夾> --ranges <理論範圍資料夾> -o out.html
```

| 參數 | 說明 |
|---|---|
| `--hands DIR` | 必填。遞迴掃描 `.txt`，同一 hand id 只算一次 |
| `--ranges DIR` | 必填。理論範圍 `.txt` |
| `-o, --out FILE` | 輸出 HTML，預設 `preflop_matrix.html` |
| `--hero NAME` | Hero 的玩家名稱，預設 `Hero` |
| `--title TEXT` | 頁面標題 |
| `--json PATH` | 另存矩陣資料（與 HTML 內嵌的相同） |

結束代碼：`0` 成功；`2` 資料夾不存在／參數錯誤；`1` 沒有可用手牌、範圍資料夾沒有 `.txt`、無法寫入輸出。
無法解析的手牌會計數跳過，最後印出摘要（含範例）；只要還有可用手牌就仍輸出並回傳 0。

## 節點定義

每個節點都只有兩個人之間的決策；一旦有第三人做過非棄牌動作（limp、冷跟、squeeze、冷 4bet…），該決策就排除。

| 節點 | 決策者 | 選項 |
|---|---|---|
| `open` | 前面全棄的位置（SB 的 limp 算不開池） | 開池 / 其他 |
| `vs_open` | 開池後，中間沒人跟或加注的防守位置 | fold / call / 3bet |
| `vs_3bet` | 開池者面對單一 3bet（其他人全棄、不含 squeeze） | fold / call / 4bet |
| `vs_4bet` | 3bettor 面對開池者的 4bet | fold / call / 5bet |
| `vs_5bet` | 開池者面對 5bet | fold / call / 6bet（無理論） |

有人先 limp 的手牌不進任何 `vs_*` 節點。小於最小加注的 all-in 加注視為跟注。
位置由按鈕推算（SB, BB, UTG, HJ, CO, BTN）；**只採用 6 人桌**，其他人數的手牌排除並在摘要中計數。
「玩家池」＝除 Hero 以外所有人。

### 理論公式

權重：對子 6、同花 4、不同花 12 combos，總和 1326。

- `open`、`vs_open`：範圍 combo 數 / 1326。
- `vs_3bet`：以開池範圍為分母，Σ 開池權重 × 條件頻率 ÷ Σ 開池 combos。
- `vs_4bet`：以 3bettor 對該開池者的 3bet 範圍為底。5bet 範圍＝「5bet」＋「5bet all in」兩檔相加（上限 1）。
- `vs_5bet`：沒有理論。

後兩街的範圍檔給的是「該手牌在所有發牌中」的權重（已含前一層的篩選），所以每手牌的權重先截在底範圍權重以內，
等同「條件頻率 = min(1, 檔案權重 / 底範圍權重)」。

## 範圍檔命名規則

檔名（不含 `.txt`）對應到節點；內容為 `AsAh: 1,KsKh: 0.5,...`（combo: 權重，省略權重視為 1）。
尺寸 token 為 `2bb`、`9.5bb` 這類，可省略。

| 檔名 | 節點 |
|---|---|
| `BTN Open 2bb` | `open` BTN |
| `BB vs BTN open [2bb] call` / `3bet [9.5bb]`（`3b` 也可） | `vs_open`：BB 面對 BTN 開池 |
| `BTN vs BB 3bet 9.5bb call` / `4bet 22bb` | `vs_3bet`：BTN 開池，面對 BB 的 3bet |
| `BB vs BTN 4bet 22bb call` / `5bet [5bet] 46bb` / `5bet all in` | `vs_4bet`：BB（3bettor）面對 BTN 的 4bet |

第一個位置是做決策的人；`vs_open` 與 `vs_4bet` 的第二個位置是對手，`vs_3bet` 的第二個位置是 3bettor。
開池者必須比 3bettor／防守者更早行動。含第三人的檔名（`SB call`、`squeeze`、第三人 3bet／4bet…）、
`vs_5bet`／6bet 的檔一律忽略。對應不到的節點在 HTML 顯示 `–`（無理論），不會報錯。
同一節點有多個檔時只用排序在前的一個並在摘要列出。

## 限制

- 只支援 GG／Natural8 Rush & Cash 格式（`Poker Hand #...` + 6 人桌）；只解析翻前。
- 只採用 6 人桌手牌。
- 頁面使用 Google Fonts，離線時退回系統字型。
- HTML 樣板不含針對特定資料集撰寫的文字評論。
