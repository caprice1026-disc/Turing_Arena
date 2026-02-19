# MVP実装 ExecPlan: 生成AI判別クイズWebサービス（Django）

このExecPlanは living document です。`PLANS.md` に従って更新し続けます。

## Purpose / Big Picture

ユーザーが2択/4択クイズ（フェーズ1: 人間当て、フェーズ2: 4択のみモデル系統割当）をプレイでき、管理者が作問・公開・再試行・ユーザー管理を行えるMVPを実装する。再出題制御（reserved/solved）、在庫切れ導線、ランキング2系統を動作確認可能な状態で提供する。

## Progress

- [x] (2026-02-19) 実装方針を確定（機能優先MVP、OpenRouter直接HTTP、Admin中心+作問ウィザード）。
- [x] (2026-02-19) Python仮想環境・依存導入、Djangoプロジェクト初期化、アプリ雛形作成。
- [x] (2026-02-19) 設定分離（base/local/test）とカスタムユーザー認証基盤。
- [x] (2026-02-19) DBモデル・マイグレーション（content/quiz/admin_portal）。
- [x] (2026-02-19) 問題確保ロジック、採点サービス、ユーザー画面フロー。
- [x] (2026-02-19) 管理者作問ウィザード、OpenRouter連携、個別再試行。
- [x] (2026-02-19) ランキング、透明性ページ、監査ログ。
- [x] (2026-02-19) テスト実装・受け入れ基準検証（pytest 9件PASS）。

## Surprises & Discoveries

- 観測: `Python 3.13.1` 環境で開始。  
  証拠: `python --version` 出力。
- 観測: `manage.py test` ではテスト0件、`pytest` 側でテストを管理する構成になった。  
  証拠: `python manage.py test` 出力 `Ran 0 tests`, `pytest -q` 出力 `9 passed`。

## Decision Log

- Decision: 依存は `Django 5.1.x / pytest / pytest-django / httpx / django-environ / PyMySQL` で開始する。  
  Rationale: 実装速度とローカル互換性を優先しつつ、MySQL接続可能性を維持する。  
  Date/Author: 2026-02-19 / Codex
- Decision: MySQLは本番互換性のため環境変数で切替、ローカル/テストはSQLiteを既定値にした。  
  Rationale: 初期実装速度とCI安定性を優先しつつ、Cloud SQL移行余地を維持する。  
  Date/Author: 2026-02-19 / Codex
- Decision: 管理者作問ウィザードは単ページでStep相当をまとめ、CRUD系はDjango Admin/カスタム一覧で補完した。  
  Rationale: MVP工数内で「作問→生成→公開→再試行」要件を満たす最短経路のため。  
  Date/Author: 2026-02-19 / Codex

## Outcomes & Retrospective

- 実装完了。以下を達成:
  - Djangoプロジェクト新規構築、設定分離、カスタムユーザー、MVP必須テーブル実装。
  - セッション確保（reserved/solved）、2択/4択フェーズ、フェーズ2採点、在庫切れ導線実装。
  - 管理者作問、OpenRouter直接HTTP生成、失敗時error保存、個別再試行実装。
  - ランキング2系統、透明性ページ、監査ログ（公開/停止/PWリセット）実装。
  - `pytest -q` で9件の統合テストを通過。
  残課題:
  - Cloud Run/Cloud SQL本番配備手順は次フェーズ。
  - 非同期キュー（Cloud Tasks/Celery）導入は次フェーズ。

## Context and Orientation

現在のリポジトリは仕様文書中心でアプリコード未整備。新規で `config/`, `apps/*`, `templates/`, `requirements/`, `pytest.ini` 等を構築する。

## Plan of Work

設定分離と認証基盤を先に確立し、その上でDBモデルを定義する。次にセッション確保/採点コアを実装し、ユーザー画面・管理画面へ接続する。最後にランキング・透明性ページ・監査ログを統合し、統合テストで受け入れ基準を検証する。

## Concrete Steps

1. 設定分離とURL基盤を構築。  
2. カスタムユーザー実装と認証画面実装。  
3. モデル定義とマイグレーション。  
4. サービス層（セッション確保・採点・OpenRouter）実装。  
5. 画面実装（ユーザー/管理者）とテスト追加。  
6. 全体テストを実行しREADME整備。

## Validation and Acceptance

`pytest -q` を最終検証コマンドにし、要件16章に対応するテストを通過させる。加えて `python manage.py check` と `python manage.py test` も補助的に実行する。

## Idempotence and Recovery

マイグレーションは再実行可能とし、セッション予約は一意制約で衝突回復する。OpenRouter失敗は `generation_status=error` から個別再試行で復旧する。

## Artifacts and Notes

- `ALLOWED_NUM_QUESTIONS`, `RESERVE_TTL_HOURS`, `RANKING_MIN_PHASE1`, `RANKING_MIN_PHASE2` を環境変数化する。
- OpenRouterは本文生ログを保存せず、最小メタ情報中心で保存する。

## Interfaces and Dependencies

- DjangoテンプレートSSR構成、API専用層は作らない。
- `quiz.services.session_allocator`, `quiz.services.answer_service`, `content.services.openrouter_client`, `admin_portal.services.question_wizard_service` を実装契約として固定する。

---

変更履歴:
- 2026-02-19: 初版作成（実装開始時点の進捗と決定事項を反映）。
- 2026-02-19: 実装完了に合わせてProgress/Decision Log/Outcomesを更新。
