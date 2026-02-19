# Turing Arena MVP

生成AI判別クイズWebサービス（Django）MVP実装です。  
2択/4択クイズ、フェーズ1/フェーズ2、管理者作問、ランキング、再出題制御を実装しています。

## ローカル起動

1. 仮想環境と依存導入

   1. `python -m venv .venv`
   2. `.venv\Scripts\Activate.ps1`
   3. `pip install -r requirements/dev.txt`

2. 環境変数

   1. `.env.example` を `.env` として配置
   2. 必要に応じて `OPENROUTER_API_KEY` を設定

3. DB

   1. デフォルトはSQLite（`USE_MYSQL=False`）
   2. MySQL利用時は `compose.yaml` で起動し、`.env` で `USE_MYSQL=True`

4. マイグレーションと管理ユーザー

   1. `python manage.py migrate`
   2. `python manage.py createsuperuser`

5. 起動

   1. `python manage.py runserver`

## 主なURL

- `/` トップ
- `/signup` 新規登録
- `/login` ログイン
- `/quiz/start` クイズ設定
- `/ranking` ランキング
- `/transparency` 透明性ページ
- `/admin/dashboard` 管理ダッシュボード
- `/admin/questions/create` 問題作成ウィザード
- `/django-admin/` Django標準Admin

## テスト

- `pytest -q`
