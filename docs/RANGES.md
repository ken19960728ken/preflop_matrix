# 理論範圍：需求與格式

`preflop-matrix` 的「理論」欄全部來自一個範圍資料夾。本文件說明程式從哪裡讀範圍、需要哪些檔、每個檔的格式。

範圍檔不會進 git：`.gitignore` 排除所有 `*.txt`、`ranges/`、`Ranges/`，預設資料夾也放在 repo 外面。

## 1. 從哪裡讀（優先順序）

| 順序 | 來源 | 例子 |
|---|---|---|
| 1 | 參數 `--ranges DIR` | `preflop-matrix --hands hh --ranges ~/my-ranges` |
| 2 | 環境變數 `PREFLOP_MATRIX_RANGES` | `export PREFLOP_MATRIX_RANGES=~/my-ranges` |
| 3 | 預設資料夾 `$XDG_CONFIG_HOME/preflop-matrix/ranges` | 沒設 `XDG_CONFIG_HOME` 時是 `~/.config/preflop-matrix/ranges` |

- 每次執行第一行會印出用的是哪一個：`理論範圍來源：預設資料夾 → /Users/…/.config/preflop-matrix/ranges`。
- 取**第一個有設定的來源**；那個來源的資料夾不存在就以結束代碼 `2` 停止，不會再往下找。
- 錯誤訊息會依來源給提示：預設資料夾不存在時列出三種設定方式；環境變數指錯時提示修正或 `unset PREFLOP_MATRIX_RANGES`。
- 有了預設資料夾，平常只要 `preflop-matrix --hands <手牌資料夾>`。

### 設定預設資料夾

```bash
mkdir -p ~/.config/preflop-matrix/ranges
cp -R "<你的範圍資料夾>"/. ~/.config/preflop-matrix/ranges/
```

資料夾會遞迴掃描所有 `.txt`（副檔名小寫；`.TXT` 不會被讀）；子資料夾可以用來分類，但不會跟隨資料夾的符號連結（檔案的符號連結照讀）。名為 `X.txt` 的資料夾若檔名對得上節點，會列為「無法讀取」。`XDG_CONFIG_HOME` 若是相對路徑會被忽略，改用 `~/.config`。

## 2. 需要哪些檔

只用「兩人對抗」的節點。位置順序：UTG → HJ → CO → BTN → SB → BB，開池者一定比對手早。

| 節點 | 決策者 | 需要的檔（每組） | 組數 | 檔數 |
|---|---|---|---|---|
| `open` | 開池者 | 開池範圍 | 5（UTG、HJ、CO、BTN、SB） | 5 |
| `vs_open` | 防守者 | 跟注、3bet | 15（每個開池者 × 每個較晚位置） | 30 |
| `vs_3bet` | 開池者 | 跟注、4bet（可另加 4bet all in） | 15 | 30 |
| `vs_4bet` | 3bettor | 跟注、5bet、5bet all in（至少一個 5bet 檔） | 15 | 30–45 |

完整的一套是 108 個檔（`vs_4bet` 有兩組沒有非全下的 5bet 檔）。缺檔時的行為：

| 情況 | 結果 |
|---|---|
| 缺底範圍（`vs_3bet` 缺開池檔、`vs_4bet` 缺 3bet 檔） | 該格顯示 `–`（無理論） |
| 底範圍在、只缺一個動作檔 | 缺的動作當 0，摘要印「理論範圍不完整：… 缺 … 已當 0」 |
| 整組都沒有 | 該格顯示 `–`，不報錯 |
| `vs_5bet` | 一律沒有理論（檔案會被忽略） |

## 3. 檔名規則

檔名（不含 `.txt`）決定它屬於哪個節點。不分大小寫；尺寸 token（`2bb`、`9.5bb`）可省略（`BTN open` 也可以）；多個空白視為一個。

| 節點 | 檔名格式 | 例子 |
|---|---|---|
| `open` | `<開池者> open <尺寸>` | `BTN Open 2bb`、`SB Open 3bb` |
| `vs_open` | `<防守者> vs <開池者> open [尺寸] call` | `BB vs BTN open 2bb call` |
| | `<防守者> vs <開池者> open [尺寸] 3bet [尺寸]`（`3b` 也可） | `BB vs BTN open 2bb 3bet 9.5bb`、`BB vs HJ open 2bb 3b 10bb` |
| `vs_3bet` | `<開池者> vs <3bettor> 3bet [尺寸] call` | `BTN vs BB 3bet 9.5bb call` |
| | `<開池者> vs <3bettor> 3bet [尺寸] 4bet [尺寸]` | `BTN vs BB 3bet 9.5bb 4bet 22bb` |
| | `… 4bet all in`（和 4bet 檔相加，上限 1） | `SB vs BB 3bet 9bb 4bet all in` |
| `vs_4bet` | `<3bettor> vs <開池者> 4bet [尺寸] call` | `BB vs BTN 4bet 22bb call` |
| | `<3bettor> vs <開池者> 4bet [尺寸] 5bet [尺寸]` | `BB vs CO 4bet 23bb 5bet 48.5bb` |
| | `… 5bet all in`（和 5bet 檔相加，上限 1） | `BB vs BTN 4bet 22bb 5bet all in` |

注意第二個位置的意思不同：`vs_open`、`vs_4bet` 是「對手」，`vs_3bet` 是「3bettor」；第一個位置永遠是做決策的人。

**會被忽略的檔**（摘要列為「忽略」）：
- 名字裡出現第三個位置或多人動作：`BB vs BTN open 2bb SB call call`、`… squeeze …`、`CO vs HJ 3bet UTG …`
- 5bet／6bet 之後的節點：`BTN vs BB 5bet 46bb all in`、`… 6bet all in call`
- 其他對不上格式的檔

同一節點有多個檔時，依完整路徑**逐層比較路徑元件**（區分大小寫、按 Unicode code point；例如 `a/` 排在 `a b/` 之前）排序，**先成功讀到、且不是空白檔**的那個勝出；其他有內容的檔列為「重複」（包括讀不了的）；空白檔一律列為「未填」（見第 4 節）。

## 4. 檔案內容格式

PioSOLVER／GTO Wizard 匯出的 combo 權重格式，逗號或換行分隔：

```
AsAh: 1,AsAd: 1,KsKh: 0.5,AhKh,7c6c: 0.25
```

- 每個 token 是 `<兩張牌>[: 權重]`。牌是點數 `AKQJT98765432` + 花色 `shdc`，例如 `Ts9s`。
- 省略權重 = 1。權重必須是 ≥ 0 的有限數字。
- 同一個 combo（不分順序）不可出現兩次；一個 combo 的兩張牌不可相同（不同 combo 共用同一張牌沒問題）。
- 檔案可以有 UTF-8 BOM。
- 違反任何一條，該檔列為「無法讀取」，不會中斷整個執行。
- **能對應到節點的檔**，去掉一個 BOM 後只剩空白的檔，視為**未填**。「空白」是 Python `str.isspace` 的集合：空白、Tab、換行、U+001C–U+001F、U+0085、U+00A0、U+3000 等；U+200B（零寬空白）不算，有它的檔列為「無法讀取」；兩個 BOM 也列為「無法讀取」。未填的檔不佔用節點（同節點排序在後、有內容的檔會勝出），摘要列為「未填（空白檔）」，不算無法讀取、也不算重複。對不上節點的空白檔（例如多人檔）仍列為「忽略」。只有逗號的檔（例如 `,,,`）不是空白檔，仍是有效的範圍（所有權重 0）。

程式把 combo 合併成 169 種手牌：每種手牌的值＝權重總和 ÷ combo 數（對子 6、同花 4、不同花 12），上限 1。

### 權重的意義（重要）

| 節點 | 權重代表 |
|---|---|
| `open`、`vs_open` | 這手牌在**全部發牌**中做這個動作的比例 |
| `vs_3bet`、`vs_4bet` | 同上，是**聯合權重**：已經包含前一層的篩選 |

例如 `BTN vs BB 3bet 9.5bb call` 裡 `AhKh: 0.3`，意思是在所有 AhKh 裡有 30% 走到「BTN 開池 → 被 BB 3bet → 跟注」，不是「開池的 AhKh 裡 30% 跟注」。GTO Wizard、PioSOLVER 匯出某個節點的範圍時就是這種權重。

計算時每手牌（169 種手牌層級，不是逐個 combo）先截在底範圍以內：`min(檔案權重, 底範圍權重)`。整格的條件頻率＝以底範圍加權的平均：`Σ min(w, base) × combos ÷ Σ base × combos`；底範圍權重為 0 的手牌不計。底範圍是 `vs_3bet` 用開池檔、`vs_4bet` 用該 3bettor 對該開池者的 3bet 檔。

如果你的檔是條件權重（例如「開池的牌裡 30% 跟注」），`vs_3bet`／`vs_4bet` 的理論值會被高估。請先乘上底範圍再存檔。

## 5. 檢查你的範圍資料夾

```bash
preflop-matrix --hands <手牌資料夾> --ranges <範圍資料夾> -o check.html
```

看摘要這一行：

```
理論範圍：354 個檔案，對應到節點 108 個；忽略（多人或不認得）246、重複 0、無法讀取 0、未填（空白檔）0
```

- 「對應到節點」少於 108：用第 3 節的格式檢查檔名。
- 有「無法讀取」：摘要會列出檔名和原因（壞牌、重複 combo、權重不合法）。
- 範圍資料夾裡沒有任何 `.txt` 才會 exit 1；全部空白或全部被忽略仍會輸出報告並 exit 0。
- 有「未填（空白檔）」：摘要會列出檔名；這些檔還沒填內容，不算有範圍，也不會佔用節點。
- 有「理論範圍不完整」：該節點缺某個動作檔。
- 有「警告：… 理論的跟注 + 加注 = … 超過 1，已按比例縮到 1」（stderr）：整格的跟注 + 加注超過 1。`vs_3bet`／`vs_4bet` 通常是條件／聯合權重混用；`vs_open` 沒有底範圍，表示跟注檔和 3bet 檔佔全部發牌的比例加起來超過 1（兩檔重疊）。
