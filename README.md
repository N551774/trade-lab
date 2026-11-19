# 短期トレード・ラボ（クラウド版）

スマホ・PCのブラウザから使える、短期売買の分析・検証・記録アプリです（Streamlit）。

- 起動ファイル：`app.py`
- 必要なライブラリ：`requirements.txt`（Streamlit Cloud が自動でインストール）
- 保存先：Secrets に Google スプレッドシートを設定すると、記録が消えずに残ります。設定しない場合は一時保存（アプリ再起動で消える）。
- パスワード：Secrets に `app_password` を設定すると、開くときにパスワードが必要になります。

設定の書き方は `secrets_example.toml` を参照（このファイルは公開しないこと）。

⚠️ 本アプリは条件に合うチャートを機械的に探す分析ツールで、投資助言ではありません。

---

# 経理ラボ『バランスシート』

`keiri/` フォルダにある、経理の仕事を学ぶスマホゲームです。新入社員からCFOまで、仕事と人生の選択を重ねる物語。

- 起動：`streamlit run keiri/app.py`（Streamlit Cloud の Main file path も `keiri/app.py`）
- 本体：`keiri/web/balance.html`（`python keiri/web/build.py` で `balance.src.html`・問題データ・立ち絵から生成）
- 遊び
  - **ストーリー**（無料）：1話3〜5分。1章「期首」・2章「仮勘定」の全10話。物語の中のバトルは仲間固定
  - **バトル**：問題に答えると攻撃。制限時間・速答クリティカル・コンボ・仲間の必殺技（カットイン）・敵の反撃カウント
  - **月次決算ラン**（気力10）：4週＋締め日を1回5分で回す育成ラン。行動カード、ランダムな事件、締め日のボス
  - **スカウト**：辞令封筒で仲間カードを集める。提供割合・天井を表示。課金はデモで請求なし
  - **社内チャット**：キャラクターとのやりとりで絆が上がる
  - ログインボーナス、デイリーミッション、12時間ごとの無料スカウト、結果画面で間違えた問題を見直し
- 設定資料：`keiri/web/cast.html`（登場人物）、`keiri/web/prompts.html`（画像生成プロンプト）、`keiri/web/analysis.html`（ヒットRPGの分析）
- 立ち絵：`keiri/web/img/人物_表情.webp`。元画像は `python keiri/web/tools/prep_portrait.py 元画像 出力.webp` で背景を抜いて作る（`pip install "rembg[cpu]"`）
- 旧版：`keiri/web/index.html`（学習アプリ版）、`streamlit run keiri/classic.py`（表形式の学習ツール）
- 登場する人物・会社はすべて架空です
