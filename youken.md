# 生成AI判別クイズWebサービス 要件定義書（MVP＋拡張前提）

版: 1.0
作成日: 2026-02-18（JST）
想定スタック: Python / Django / Django ORM / MySQL（Cloud SQL）/ Cloud Run / LangChain（任意） / Openrouter（外部LLM連携） / その他必要に応じて

外部LLM: OpenAI系 / Anthropic系 / Google系（管理者が作問時にのみ利用）

---

## 1. 背景・目的

本サービスは、**人間のメッセージに対する複数の返答文**（人間が書いた返答＋複数の生成AIモデルが生成した返答）を提示し、ユーザーが

* フェーズ1: 「どれが人間の返答か？」を当てる
* フェーズ2（4択のみ）: 「AIの返答がどの“モデル系統”か？」を当てる（利きモデル）

という **娯楽性（主）＋AIリテラシー（副）** のクイズ体験を提供する。

---

## 2. 用語・定義

* **シナリオ（Scenario）**:
  人間メッセージ（質問）と、人間が手書きで作成した「人間返答」をまとめた“問題素材”。
* **問題（Question）**:
  シナリオから派生する、実際に出題可能な単位。AI返答（Option）が紐づく。
  同じシナリオから複数の問題（バリアント）を作成可能。
* **選択肢（Option）**:
  Questionに紐づく返答文。`human` もしくは `ai`。AIの場合は利用モデル情報が紐づく。
* **バリアント**:
  同一シナリオでも、温度/seed/プロンプト等を変えて別Questionとして生成したもの。
  **ユーザーには別問題として扱う**（供給量確保）。
* **モデル表示名（display_group / display_name）**:
  ユーザーに見せる系統名（例: GPT系/Claude系/Gemini系）と、表示用の名称。
* **内部モデル名（api_model_name）**:
  実際にAPI呼び出しに使うモデル名（例: gpt-xxx 等）。将来差し替え可能。
* **フェーズ1**: 人間返答当て（2択/4択共通）
* **フェーズ2**: 利きモデル（4択のみ、AI3つの割当）

---

## 3. スコープ

### 3.1 MVPで提供する機能（必須）

**ユーザー向け**

* 新規登録（email / login_id / password）
* ログイン / ログアウト
* クイズ開始（難易度＋形式＋問題数選択）
* クイズ回答

  * 2択: フェーズ1のみ
  * 4択: フェーズ1＋フェーズ2
* 回答結果表示（正誤・累計正答率など）
* セッション結果表示
* ランキング表示（フェーズ1/フェーズ2を別ランキング）
* 問題枯渇（在庫切れ）表示

**管理者向け**

* 管理者ログイン
* ジャンル管理（CRUD）
* タグ管理（CRUD）
* モデル台帳管理（CRUD）
* 問題作成ウィザード（作問→AI生成→プレビュー→公開）
* 生成失敗時の個別再試行
* 問題の公開/停止（アーカイブ）
* 問題ごとの正答率ダッシュボード（最低限）
* ユーザーの強制パスワードリセット（MVPは“管理者が新PW設定”）

**共通**

* 透明性ページ（データ取り扱い方針、ランキング集計方針、禁止事項）

### 3.2 MVPで“やらない”こと（明確に除外）

* 一般ユーザーによる作問（UGC）・課金
* ゲスト向け「今日の1問」（将来）
* 自動モデレーション（将来）
* Elo/Glicko等のレーティング（将来、DBだけ匂わせ）
* 多管理者ワークフロー（作成→レビュー→公開の多段承認）（将来）
* 高度な不正対策（端末指紋・IP制限・自動BAN）（将来）
* メールによるパスワードリセット（将来）

---

## 4. 役割・権限

* **一般ユーザー**

  * クイズ挑戦、結果閲覧、ランキング閲覧
* **管理者**

  * 一般ユーザーの全権限
  * 問題の作成/公開/停止、モデル/タグ/ジャンル管理
  * ユーザーのPWリセット、停止

※MVPは「単一管理者」を想定。ただしDB/権限設計は将来の複数管理者に耐える形。

---

## 5. ゲーム仕様（固定事項）

### 5.1 出題形式

* **4択**: 「人間1 + AI3」固定
* **2択**: 「人間1 + AI1」固定、**フェーズ2なし**

### 5.2 フェーズ構成

* フェーズ1（2択/4択共通）

  * 「どれが人間の返答か？」を選択（A〜B または A〜D）
* フェーズ2（4択のみ）

  * フェーズ1結果後に、**人間の選択肢を明示**してロック
  * 残りのAI3つに対し、ユーザーは **モデル系統（表示名）** を割当てる
  * **部分点**（0〜3）＋ **完全一致ボーナス**（score=3）

### 5.3 公開後編集方針

* 公開後に編集可能: `difficulty / genre / tags / status（公開停止等）`
* 本文（シナリオ文、Option本文、プロンプト等）を変更したい場合は **新Questionとして作成**する

### 5.4 再出題制御

* ユーザーが一度 **解いた（solved）** Questionは **永久に再出題しない**
* 予約（reserved）は一定時間で失効し、再出題対象に戻る

---

## 6. 画面要件（ユーザー）

> MVPは Djangoテンプレート＋最小JS（vanilla）を想定。SPA前提にしない。
> URLは例。実装時に調整可だが、機能と遷移は固定する。

### 6.1 トップ

* URL: `/`
* 要素:

  * クイズを始める（ログイン必須）
  * ログイン / 新規登録
  * ランキング
  * 透明性ページ

### 6.2 新規登録

* URL: `/signup`
* 入力:

  * email（必須、ユニーク）
  * login_id（必須、ユニーク、英数＋_推奨）
  * password（必須、強度チェック最低限）
* 成功: ログイン状態でトップへ

### 6.3 ログイン

* URL: `/login`
* 入力: login_id または email、password
* 成功: トップへ

### 6.4 クイズ設定

* URL: `/quiz/start`
* 入力:

  * difficulty: `easy / normal / hard`
  * choice_count: `2 / 4`
  * num_questions: `1 / 3 / 5 / 10`（※機能フラグで制限）
* ボタン:

  * 開始
* 挙動:

  * 既にactiveセッションが存在する場合

    * 「続きから再開」 or 「破棄して新規開始」

### 6.5 出題（フェーズ1）

* URL: `/quiz/session/{session_id}/q/{index}`
* 表示:

  * 人間メッセージ（Scenario.user_message_text）
  * 選択肢 A〜B / A〜D（shuffle_mapに基づく順）
  * ラジオボタン（A〜）
  * 送信
* 送信で保存:

  * phase1_selected_letter
  * phase1_is_correct
  * phase1_answered_at
  * phase1_time_ms（JSで計測）

### 6.6 フェーズ1結果表示

* URL: `/quiz/session/{session_id}/q/{index}/phase1_result`
* 表示:

  * 正誤
  * 累計（フェーズ1）：正答数/回答数、正答率、streak
* 4択の場合:

  * **この画面では正解の選択肢文字（どれが人間か）を明示しない**
  * 「フェーズ2へ」ボタン
* 2択の場合:

  * フェーズ2が無いので

    * 正解の選択肢を明示してよい（学習/納得感）
    * AI側のモデル系統表示も任意（表示するなら“GPT系”などのgroupのみ推奨）
  * 「次へ」

### 6.7 フェーズ2（4択のみ）割当画面

* URL: `/quiz/session/{session_id}/q/{index}/phase2`
* 表示:

  * フェーズ1の正解（=人間の選択肢）を明示し、そのカードをロック＆グレーアウト
  * 残り3つ（AI）に対し、各カードにセレクトボックスを表示

    * 候補は3つ（例: GPT系 / Claude系 / Gemini系）
    * **同一候補は1回のみ選択可能**（重複選択不可、UIでdisable）
  * 送信ボタン（3つ全て選択されたら活性）
* 送信で保存:

  * phase2_assignment_json（option_id基準）
  * phase2_score（0..3）
  * phase2_is_perfect（score==3）
  * phase2_answered_at
  * phase2_time_ms

### 6.8 フェーズ2結果表示

* URL: `/quiz/session/{session_id}/q/{index}/phase2_result`
* 表示:

  * `score/3`
  * 完全一致ボーナス（あり/なし）
  * 各AIカードに「正解ラベル」表示（どの系統だったか）
  * 累計（フェーズ2）：総得点、点率、完全一致回数（表示仕様は後述）
* 「次へ」

### 6.9 セッション結果

* URL: `/quiz/session/{session_id}/result`
* 表示:

  * フェーズ1: 正答率、streak（このセッション）
  * フェーズ2（4択のみ）: 点率、完全一致回数（このセッション）
  * 全体累計（ユーザー統計）
  * ランキング導線
  * もう一回挑戦

### 6.10 在庫切れ画面

* URL: `/quiz/out_of_stock`
* 表示:

  * 現在の条件（difficulty/choice_count/num_questions）
  * 確保可能数（0 または k）
  * 「k問で開始する」ボタン（k>0の場合）
  * 条件を変更する導線

---

## 7. 画面要件（管理者）

### 7.1 管理者ダッシュボード

* URL: `/admin/dashboard`（カスタム） or Django admin index
* 表示（最低限）:

  * 公開中問題数 / 下書き数
  * 難易度別の在庫数（publishedかつ出題可能なQuestion数）
  * 最近の問題の正答率（任意）

### 7.2 問題作成ウィザード（必須）

* URL: `/admin/questions/create`
* Step 1: シナリオ入力

  * 人間メッセージ（必須）
  * 人間返答（必須、手書き）
  * ジャンル選択（必須）
  * タグ選択（任意、複数）
* Step 2: 生成設定

  * choice_count（2 or 4）
  * 使用モデル選択

    * 4択: 3モデル（distinct）必須
    * 2択: 1モデル必須
  * 追加システムプロンプト（任意）
  * max_tokens（任意）
  * temperature（任意）
  * seed（任意）
  * 制約テンプレ（generation_profile）任意
* Step 3: 生成実行＆プレビュー

  * 選択したモデルへ順次または並列でAPIリクエスト
  * **各モデルの応答が返るたびDBに保存**
  * 失敗したモデルにはエラー表示＋「再試行」ボタン
  * 返答A〜D（管理者用プレビュー）を一覧表示（author_type/モデル表示も可）
* Step 4: 公開設定

  * difficulty設定（必須）
  * 公開（published） or 下書き（draft）
  * 保存

### 7.3 問題一覧

* URL: `/admin/questions`
* フィルタ:

  * status / difficulty / genre / choice_count
* 各行表示:

  * question_id、genre、difficulty、status、作成日、公開日
  * フェーズ1正答率、フェーズ2点率（任意）
* 操作:

  * 詳細
  * 公開停止（archived）
  * バリアント作成（同scenarioで新question作成）

### 7.4 ユーザー管理

* URL: `/admin/users`
* 操作:

  * 強制PWリセット（MVP: 管理者が新PW設定）
  * アカウント停止（is_active=false）
* 監査:

  * リセット実行者、実行時刻をログに残す（最低限）

---

## 8. データ要件（DB設計：MySQL）

### 8.1 共通方針

* Django ORMで管理
* 主要キー: BigAutoField
* JSONは MySQL JSON型（Django JSONField）
* created_at / updated_at を原則全テーブルに付与（更新不要なものは省略可）

---

### 8.2 テーブル定義（MVP必須）

#### users（Djangoカスタムユーザー推奨）

* id (PK)
* login_id（unique）
* email（unique）
* password（Django管理）
* is_staff / is_superuser（管理者判定）
* is_active
* created_at, updated_at, last_login_at（任意）

#### genre

* id (PK)
* slug（unique）
* name
* is_active
* created_at, updated_at

#### tag

* id (PK)
* name（unique推奨）
* category（例: `style`固定でOK）
* is_active
* created_at, updated_at

#### scenario

* id (PK)
* user_message_text（Text）
* human_reply_text（Text）
* genre_id (FK → genre)
* created_by_admin_id (FK → users)
* created_at, updated_at

#### scenario_tag（M2M）

* scenario_id (FK)
* tag_id (FK)
* UNIQUE(scenario_id, tag_id)

#### llm_model

* id (PK)
* provider（例: `openai` / `anthropic` / `google`）
* display_group（ユーザー提示用の系統名、例: `GPT系`）
* display_group_slug（内部識別用、例: `gpt` / `claude` / `gemini`、unique推奨）
* display_name（例: `GPT系（最新）`）
* api_model_name（実際のAPIモデル名）
* is_active
* deprecated_at（nullable）
* created_at, updated_at

#### generation_profile（将来用、MVPは空運用可）

* id (PK)
* name（unique推奨）
* params_json（JSON）
* created_at, updated_at

#### question

* id (PK)
* scenario_id (FK → scenario)
* status（enum: `draft` / `published` / `archived`）
* difficulty（enum: `easy` / `normal` / `hard`）
* choice_count（int: 2 or 4）
* generation_profile_id (FK nullable)
* variant_of_question_id（FK → question nullable）
* published_at（nullable）
* created_by_admin_id (FK → users)
* created_at, updated_at

#### option

* id (PK)
* question_id (FK → question)
* author_type（enum: `human` / `ai`）
* llm_model_id（FK → llm_model, humanの場合null）
* content_text（Text）
* system_prompt（nullable Text）
* temperature（nullable float）
* seed（nullable int）
* max_tokens（nullable int）
* request_payload_json（nullable JSON）
* response_payload_json（nullable JSON）
* generation_status（enum: `pending` / `ok` / `error`）
* error_message（nullable Text）
* created_at, updated_at

**制約（アプリ側バリデーション）**

* question.choice_count=4:

  * option件数=4
  * human=1、ai=3
  * aiのllm_modelは3つすべて異なる
  * 全option generation_status=ok
* question.choice_count=2:

  * option件数=2
  * human=1、ai=1
  * 全option generation_status=ok

#### quiz_session

* id (PK)
* user_id (FK → users)
* difficulty
* choice_count
* num_questions_requested
* status（enum: `active` / `finished` / `abandoned`）
* started_at, finished_at（nullable）
* created_at, updated_at

#### session_question

* id (PK)

* session_id (FK → quiz_session)

* question_id (FK → question)

* order_index（int）

* shuffle_map_json（JSON）※形式固定（後述）

* phase1_selected_letter（nullable: `A`/`B`/`C`/`D`）

* phase1_is_correct（nullable bool）

* phase1_answered_at（nullable datetime）

* phase1_time_ms（nullable int）

* phase2_assignment_json（nullable JSON）※option_id基準（後述）

* phase2_score（nullable int 0..3）

* phase2_is_perfect（nullable bool）

* phase2_answered_at（nullable datetime）

* phase2_time_ms（nullable int）

#### user_seen_question（再出題制御＋予約）

* user_id (FK)
* question_id (FK)
* status（enum: `reserved` / `solved`）
* session_id（FK → quiz_session, nullable）
* reserved_until（nullable datetime）
* first_seen_at（datetime）
* solved_at（nullable datetime）
* UNIQUE(user_id, question_id)

---

### 8.3 JSONフィールド仕様（固定）

#### shuffle_map_json（session_question）

**形式: A→option_id のJSON（2択はA,Bのみ、4択はA〜D）**

```json
{
  "A": 12345,
  "B": 12346,
  "C": 12347,
  "D": 12348
}
```

* 値は `option.id`（数値）
* 2択の場合:

```json
{ "A": 111, "B": 112 }
```

#### phase2_assignment_json（session_question）

**形式: option_id→display_group_slug のJSON（4択のみ）**

```json
{
  "12346": "gpt",
  "12347": "claude",
  "12348": "gemini"
}
```

* キーはJSON上は文字列になるため、**option_idは文字列キー**で保存する（実装が安全）
* 値は `llm_model.display_group_slug`
* 対象はAIの3optionのみ（人間optionは含めない）
* サーバー側で「3キーが揃っている」「値が全てユニーク」「候補はその問題に使った3系統のみ」を検証

---

## 9. 問題確保ロジック（詳細仕様）

### 9.1 前提

* 同一ユーザーの `active` セッションは **1つまで**
* セッション開始時に **N問を予約**し、セッション中の出題順と選択肢並び（shuffle）を固定する
* 予約は `reserved_until` で失効する（例: 24時間）

### 9.2 セッション開始アルゴリズム

入力: `user_id, difficulty, choice_count, num_questions_requested`

1. `active` セッションの有無確認

   * ある場合:

     * 既存セッションに戻す（再開）
     * または「破棄して新規開始」

       * 破棄時は session.status=abandoned
       * user_seen_question.status=reserved かつ session_id=当該 の行を解除（削除 or reserved_untilを過去に）

2. 新規セッション作成（status=active）

3. 候補questionの抽出（概念）

   * 条件:

     * question.status='published'
     * question.difficulty=選択difficulty
     * question.choice_count=選択choice_count
     * option条件を満たす（出題可能）
     * user_seen_question で

       * solvedは除外（永久）
       * reservedかつ reserved_until>now は除外（予約中）
   * N件ランダムで選ぶ

     * MVPは `ORDER BY RAND()` で可（小規模前提）
     * 将来の高速化は別途（random_key等）

4. 候補が0の場合: 在庫切れ画面へ
   候補がk（1..N-1）の場合:

   * 「k問で開始する」 or 条件変更

5. 予約（トランザクション推奨）

   * 選んだ question_id ごとに user_seen_question を `reserved` で upsert/insert

     * UNIQUE(user_id, question_id)制約により二重予約を防ぐ
     * 競合した場合は別候補で穴埋めする
   * reserved_until = now + 24h（設定可能）
   * session_id=作成したsession
   * first_seen_at=now

6. session_question生成

   * N問について order_index を決定
   * 各問について shuffle_map_json を生成し保存

     * option.id一覧をランダムにシャッフルして A〜D（or A,B）に割当

7. 1問目へ遷移

### 9.3 “解いた”判定と永久排除のタイミング

* フェーズ1回答送信時点で `solved` とみなす（4択でも同様）

  * user_seen_question.status = solved
  * solved_at = now
  * reserved解除（reserved_until不要）

### 9.4 予約の期限切れ処理

MVPは「セッション開始時」または「ユーザーのトップ表示時」に掃除で十分。

* reserved_until < now の reserved行は削除 or reserved解除（status更新）
* それに紐づく放置セッションを abandoned にしても良い（任意）

---

## 10. 採点・スコア仕様

### 10.1 フェーズ1（人間当て）

* 正解条件:

  * ユーザーが選んだ letter が、人間option_idに対応している
* 保存:

  * session_question.phase1_is_correct
* ユーザー累計:

  * phase1_total += 1
  * phase1_correct += 1（正解時）
* streak:

  * 正解で +1、誤答で0にリセット
  * best_streak を更新

### 10.2 フェーズ2（利きモデル、4択のみ）

* 正解条件:

  * ユーザーが割り当てた `option_id -> display_group_slug` が、各optionの `llm_model.display_group_slug` と一致
* score:

  * 一致数（0..3）
* 完全一致ボーナス:

  * is_perfect = (score==3)
  * 表示上「ボーナスあり」を出す
  * 加点方式は下記のどちらか（MVPはA推奨）

    * A) **スコアは0..3のまま**、別途perfect回数を記録して演出（実装が簡単・公平）
    * B) perfect時に+1点（最大4点扱い）
      ※ランキング算出がやや複雑になる
* ユーザー累計（A案の場合）:

  * phase2_total_questions += 1
  * phase2_total_points += score
  * phase2_perfect += 1（is_perfect時）

### 10.3 ランキング仕様（MVP）

ランキングは2系統で別ページ（またはタブ）

* フェーズ1ランキング:

  * 指標: `phase1_correct / phase1_total`
  * 同率の並び:

    * phase1_total（多い方を上）
    * 更新日時（古い/新しいは好みで固定）
* フェーズ2ランキング:

  * 指標: `phase2_total_points / (phase2_total_questions * 3)`
  * 同率の並び:

    * phase2_total_questions（多い方を上）

**ランキング掲載条件（ノイズ対策）**

* `min_attempts` を設定（例: フェーズ1は10問以上、フェーズ2は5問以上）
  ※環境変数で調整可能

---

## 11. 外部LLM連携要件（OpenRouter）

### 11.1 連携方針

* 外部LLM呼び出しは **管理者の作問フローでのみ実行**する（一般ユーザーの回答・ランキング閲覧等では外部LLM APIを呼ばない）。
* OpenRouterを利用し、複数プロバイダ/モデルの呼び出しを **単一のAPIスキーマに統一**する。
* OpenRouter APIキーは **サーバーサイド（Cloud Run）にのみ保持**し、フロントエンドへ露出させない（Secret Manager等で注入する）。
* リクエストの並列実行（モデル3本同時など）は許可するが、**レート制限や混雑で失敗する前提**で「途中保存＋個別再試行」を必須要件とする。 ([OpenRouter][1])

---

### 11.2 使用エンドポイント

#### 11.2.1 Chat Completions（作問時の本文生成）

* 使用エンドポイント（非ストリーミング）：

```text
POST https://openrouter.ai/api/v1/chat/completions
```

* 必須ヘッダ：

```text
Authorization: Bearer <OPENROUTER_API_KEY>
Content-Type: application/json
```

OpenRouterの Chat Completion API は上記エンドポイントで提供され、レスポンスは `id / choices / created / model / usage` 等を含む。 ([OpenRouter][1])

#### 11.2.2 APIキー状態・残量確認（運用・監視用）

* **レート制限やクレジット残量**の確認に用いる（管理者のみ・サーバーサイドのみ）：

```text
GET https://openrouter.ai/api/v1/key
```

このエンドポイントで「残クレジット」「日次利用量」等が取得できる。 ([OpenRouter][2])

#### 11.2.3 （任意）App Attribution（OpenRouterランキング/分析への帰属）

OpenRouter側でアプリ帰属を付けたい場合、以下の **任意ヘッダ**を付与してよい（MVPでは任意、ただし付けても挙動には影響しない）。 ([OpenRouter][3])

```text
HTTP-Referer: https://<your-app-domain>
X-Title: <Your App Name>
```

---

### 11.3 リクエスト仕様（作問時）

#### 11.3.1 基本構造

* OpenRouter Chat Completionsのリクエストボディは、最低限以下を含む：

```json
{
  "model": "<llm_model.api_model_name>",
  "messages": [
    {"role": "system", "content": "<system_prompt_final>"},
    {"role": "user", "content": "<scenario.user_message_text>"}
  ],
  "temperature": <float>,
  "seed": <int>,
  "max_tokens": <int>,
  "stream": false
}
```

* `messages` は必須。 `temperature / seed / max_tokens / stream` は任意だが、本サービスでは「問題の再現性・バリアント管理」のため保存可能な形で指定できるようにする。 ([OpenRouter][1])
* `system_prompt_final` は「管理者の追加システムプロンプト」＋「（任意）制約テンプレ」を結合して生成する。

#### 11.3.2 ルーティング・観測（任意）

* OpenRouterは `session_id`（グルーピング）や `metadata` 等のパラメータを持つため、運用上必要なら付与してよい（MVPでは任意）。 ([OpenRouter][1])

---

### 11.4 レスポンス処理（作問時）

* 正常時は `choices[0].message.content` をAI返答本文として採用し、`option.content_text` に保存する。
* レスポンスには `id`, `model`, `created`, `usage` 等が含まれるため、後述の「最低限メタ情報」に従って保存する。 ([OpenRouter][1])
* 生成失敗時（HTTP 4xx/5xx、またはネットワーク例外）は、`option.generation_status=error` とし、エラー情報を保存し、管理画面で個別再試行を可能にする。
* OpenRouterのAPIは少なくとも `400 / 401 / 429 / 500` のエラーを定義しているため、これらを前提に制御する。 ([OpenRouter][1])

---

### 11.5 保存するメタ情報（最低限）

**目的**：

* “どのモデルで生成したか” の追跡
* コスト/トークンの概算把握
* 再試行や障害解析（最低限）
* ただし、過剰なログ保存は避け、**個人情報/機密が混じり得るデータは最小化**する

#### 11.5.1 DB項目への対応（最低限）

`option` テーブルに以下を保存する（既存カラム設計に合わせた最小セット）。

**A. 生成パラメータ（再現性/バリアント管理のため）**

* `option.system_prompt`：最終的にモデルへ渡したsystemプロンプト（結合後）
* `option.temperature`：指定値（未指定ならnull）
* `option.seed`：指定値（未指定ならnull）
* `option.max_tokens`：指定値（未指定ならnull）

（OpenRouterのChat Completionパラメータとして定義されている） ([OpenRouter][1])

**B. 結果本文（必須）**

* `option.content_text`：`choices[0].message.content`

（レスポンス構造として `choices[].message.content` が返る） ([OpenRouter][1])

**C. OpenRouterレスポンス最低限メタ**

* `option.response_payload_json`（JSON、必要最小限に絞る推奨）

  * `id`（OpenRouterの生成ID）
  * `model`（実際に返却されたmodel名）
  * `created`（Unix time）
  * `usage.prompt_tokens / usage.completion_tokens / usage.total_tokens`（存在する場合）

（レスポンス例に `id / model / created / usage` が含まれる） ([OpenRouter][1])

**D. 失敗時メタ**

* `option.generation_status`：`pending / ok / error`
* `option.error_message`：例外/HTTPステータス/本文の要点（短く）

（OpenRouterが `429 Too Many Requests` 等を返しうるため、失敗前提で保持する） ([OpenRouter][1])

#### 11.5.2 保存しない（またはデフォルトOFFにする）もの

* OpenRouterへ投げた **全文のrequest/responseの生ログ**は、原則保存しない（必要ならデバッグフラグでON）。

  * もし保存する場合も「本文（messages）」は保存せず、ハッシュや長さ、トークン数などのメタに留める。

---

### 11.6 リトライ方針（自動＋手動）

**前提**：OpenRouterや上流モデルは混雑・停止・レート制限が起こり得る。429は「減速しろ」の合図として扱う。 ([openrouter.zendesk.com][4])

#### 11.6.1 自動リトライ対象

以下を **自動リトライ対象（Retryable）** とする：

* ネットワーク例外（タイムアウト、接続断など）
* HTTP `429 Too Many Requests`
* HTTP `500` 系（OpenRouter側/上流側の一時障害とみなす）

OpenRouterのChat Completion APIは `429` や `500` を明示している。 ([OpenRouter][1])

#### 11.6.2 自動リトライしない対象

以下は **原則リトライしない（Non-retryable）**：

* HTTP `400 Bad Request`：入力/パラメータが不正（プロンプトやJSON生成を修正）
* HTTP `401 Unauthorized`：APIキー/権限の問題（運用・設定修正）
* HTTP `402`：クレジット残高が負の場合に起こり得る（自動リトライでは治らないため管理者対応） ([OpenRouter][2])

#### 11.6.3 バックオフ方式（指数バックオフ＋ジッター）

* 429（レート制限）時は特に **指数バックオフ**を行う（例：1s → 2s → 4s → 8s）。 ([openrouter.zendesk.com][4])
* 実装要件：

  * 初期待機：1秒
  * 以降2倍（最大8秒）
  * 各待機に 0〜250ms 程度のランダムジッターを加える（同時再試行の衝突回避）
  * 最大試行回数：**3回まで**（初回＋リトライ2回）を推奨

    * 理由：OpenRouterの案内では「失敗試行も日次クォータにカウントされ得る」ため、無限リトライは悪手。 ([openrouter.zendesk.com][4])

#### 11.6.4 レート制限ヘッダの扱い（任意だが推奨）

* 429時はレスポンスの `x-ratelimit-*` ヘッダを参照して状況判断する（可能ならログに保存）。 ([openrouter.zendesk.com][4])
* Freeモデル（末尾が `:free`）を使う場合、モデル/アカウント状況により **20 req/min** や **日次上限**があるため、連打しない。 ([OpenRouter][2])

#### 11.6.5 手動リトライ（管理画面）

* 自動リトライが尽きた、または non-retryable 判定となった場合でも、管理者は

  * 「失敗したoptionだけ再試行」
  * 「時間を置いて再試行」
    を実行できる。
* 再試行時は `option` レコードを更新し、成功したら `generation_status=ok` にする（履歴を残したい場合は別途履歴テーブルを追加）。 ([OpenRouter][1])

[1]: https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request "Create a chat completion | OpenRouter | Documentation"
[2]: https://openrouter.ai/docs/api/reference/limits "API Rate Limits | Configure Usage Limits in OpenRouter | OpenRouter | Documentation"
[3]: https://openrouter.ai/docs/app-attribution "App Attribution | OpenRouter Documentation | OpenRouter | Documentation"
[4]: https://openrouter.zendesk.com/hc/en-us/articles/39501163636379-OpenRouter-Rate-Limits-What-You-Need-to-Know "OpenRouter Rate Limits – What You Need to Know – OpenRouter"

---

## 12. 機能フラグ（Feature Flags）

環境変数で制御（例）

* `ALLOWED_NUM_QUESTIONS="1,3,5"`（初期は少なくして枯渇回避）
* `RESERVE_TTL_HOURS=24`
* `RANKING_MIN_PHASE1=10`
* `RANKING_MIN_PHASE2=5`

---

## 13. 透明性ページ（必須コンテンツ）

* 本サービスは「人間の返答」と「生成AIの返答」を混ぜたクイズである
* 作問時に外部LLM APIへ送信する情報は、管理者が入力したメッセージ等のみ
* 個人情報・機密情報を入力しない（管理者・将来のユーザー作問も同様）
* ランキング算出方法（フェーズ1/フェーズ2）
* 禁止事項（誹謗中傷、個人情報、差別、著作権侵害等）※将来UGCに備えて先に掲示

---

## 14. セキュリティ要件（MVP最低限）

* HTTPS前提（Cloud Run）
* CSRF対策（Django標準）
* XSS対策（テンプレートのautoescape、入力のサニタイズは基本）
* パスワードはDjango標準ハッシュ
* 管理者画面へのアクセス制御（is_staff等）
* 監査ログ（最低限）

  * 問題の公開/停止
  * ユーザーのPWリセット
* レート制限（将来でも可だが、ログイン・クイズ回答は簡易制限があると安心）

---

## 15. 非機能要件

* 可用性: MVPはベストエフォート（外部APIは管理画面のみ）
* 性能:

  * セッション開始（問題確保）: 2秒以内を目標
  * 1問回答送信: 500ms以内目標（DB保存のみ）
* 拡張性:

  * ジャンル別出題、今日の1問、UGC、課金、レーティングを追加してもDBが破綻しない設計
* 運用性:

  * 管理者が作問→公開→在庫管理できる

---

## 16. 受け入れ基準（MVP）

以下が満たされればMVP完成とする。

### 16.1 ユーザー機能

* [ ] 登録/ログイン/ログアウトができる
* [ ] クイズ設定（難易度、2択/4択、問題数）ができる
* [ ] セッション開始時に未回答問題が確保され、同一問題が再出題されない
* [ ] 2択: フェーズ1のみで完結し、結果が表示される
* [ ] 4択: フェーズ1→結果→フェーズ2→結果の流れが動作する
* [ ] フェーズ2は option_id基準で割当を保存し、重複割当ができない
* [ ] セッション結果が表示される
* [ ] ランキングがフェーズ1/フェーズ2で表示される（min_attempts適用）

### 16.2 管理者機能

* [ ] 管理者がジャンル/タグ/モデルを登録できる
* [ ] 管理者がシナリオを作成し、モデルに投げてAI回答を生成できる
* [ ] 生成失敗したモデルのみ再試行できる
* [ ] 必要な選択肢が揃った問題だけ公開できる
* [ ] 公開中/下書き/停止の管理ができる
* [ ] ユーザーのPWを強制リセットできる（ログが残る）

---

## 17. 将来拡張（この設計で自然に追加できる）

* ジャンル別モード（出題フィルタにgenre追加）
* 今日の1問（guestセッション、user_id nullable）
* レーティング（user_statsにレーティング列追加）
* 自動難易度補正（question_stats導入）
* 不正の怪しさスコア（risk_eventテーブル追加、ランキング非表示）
* UGC＋課金（community_question系の追加、モデレーション導入）

---

# 付録A: 実装メモ（AIが組む時の“迷い所”を潰す）

* モデルの“利き当て”は **display_group_slug**（gpt/claude/gemini）で判定し、内部モデル名変更の影響を遮断する
* shuffle_map_jsonは **セッション作成時に確定して保存**。リロードで並びが変わる事故を絶対に起こさない
* フェーズ1結果画面は、4択では正解文字を出さず、フェーズ2画面で人間選択肢を明示する（納得感＋理不尽回避）
* user_seen_questionを `reserved/solved` で持つと、並行アクセスや多重開始に強い

---



