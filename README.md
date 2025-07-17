# WikiProject Backend

hadxフレームワークを使用したWikiProjectのバックエンドAPI

## 機能

- **認証**: Cognitoマネージドログインページによる認証（既存のCognitoリソースを使用）
- **Wiki記事管理**: Markdownメモの作成、編集、削除、閲覧
- **共有機能**: 記事の共有コードによる閲覧・編集
- **ファイルストレージ**: S3を使用したファイルアップロード・管理
- **アクセス制御**: パブリック/プライベート記事の管理

## 技術スタック

- **フレームワーク**: hadx
- **ランタイム**: Python 3.13
- **データベース**: DynamoDB
- **ストレージ**: S3
- **認証**: Amazon Cognito（外部リソース、SSM経由で参照）
- **インフラ**: AWS SAM

## 前提条件

### Cognito設定
このバックエンドはCognitoリソースを作成しません。既存のCognitoリソースをSSMパラメータストア経由で参照します。
以下の既存リソースが必要です：

- Cognito User Pool
- Cognito User Pool Client
- Cognito User Pool Domain

## デプロイ手順

### 1. 前提条件

- AWS CLI設定済み
- SAM CLI インストール済み
- Python 3.13+
- 既存のCognitoリソース（User Pool、Client、Domain）

### 2. SSMパラメータの事前設定

**デプロイ前に**、既存のCognito設定をSSMパラメータストアに登録してください：

```bash
# Cognito設定（実際の値に置き換えてください）
aws ssm put-parameter --name "/WikiProject/Cognito/domain" --value "your-cognito-domain.auth.ap-northeast-1.amazoncognito.com" --type "String"
aws ssm put-parameter --name "/WikiProject/Cognito/user_pool_id" --value "ap-northeast-1_XXXXXXXXX" --type "String"
aws ssm put-parameter --name "/WikiProject/Cognito/client_id" --value "xxxxxxxxxxxxxxxxxxxxxxxxxx" --type "String"
aws ssm put-parameter --name "/WikiProject/Cognito/client_secret" --value "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" --type "String" --overwrite

# URL設定
aws ssm put-parameter --name "/WikiProject/URL/home" --value "https://wiki2.h-akira.net" --type "String"
```

### 3. 初回デプロイ

```bash
# プロジェクトディレクトリに移動
cd backend

# ビルド
sam build

# デプロイ
sam deploy --guided
```

初回デプロイ時に以下のパラメータを設定：
- `CustomDomainName`: wiki2.h-akira.net
- `ACMCertificateArn`: SSL証明書のARN（事前に作成が必要）

### 4. 2回目以降のデプロイ

```bash
sam build && sam deploy
```

## API エンドポイント

### 認証
- `POST /api/auth/token` - 認証コードをトークンに交換
- `GET /api/auth/status` - 認証状態確認
- `POST /api/auth/logout` - ログアウト

### Wiki記事
- `GET /api/wiki/pages` - 記事一覧取得
- `POST /api/wiki/pages` - 新規記事作成
- `GET /api/wiki/recent` - 最近更新された記事
- `GET /api/wiki/{username}/{slug}` - 記事詳細取得
- `PUT /api/wiki/{username}/{slug}` - 記事更新
- `DELETE /api/wiki/{username}/{slug}` - 記事削除

### 共有機能
- `GET /api/share/{shareCode}` - 共有記事取得
- `PUT /api/share/{shareCode}` - 共有記事更新

### ファイルストレージ
- `GET /api/storage/items` - ファイル一覧取得
- `POST /api/storage/upload` - ファイルアップロード
- `POST /api/storage/folder` - フォルダ作成
- `GET /api/storage/download/{item_id}` - ファイルダウンロード
- `DELETE /api/storage/item/{item_id}` - ファイル・フォルダ削除

## ローカル開発

### 1. 環境設定

`admin.json`ファイルを適切に設定：

```json
{
  "region": "ap-northeast-1",
  "profile": "default",
  "cognito": {
    "domain": "your-cognito-domain",
    "user_pool_id": "ap-northeast-1_XXXXXXXXX",
    "client_id": "xxxxxxxxxxxxxxxxxxxxxxxxxx",
    "client_secret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  },
  "url": {
    "home": "http://localhost:8080"
  }
}
```

### 2. ローカルサーバー起動

```bash
# ビルド
sam build

# ローカル起動
sam local start-api --port 3000
```

## フロントエンドとの統合

フロントエンド（wikiproject_vue）で以下の環境変数を設定：

```bash
# Cognitoログインページ（実際のドメインに置き換えてください）
VUE_APP_COGNITO_LOGIN_URL="https://your-cognito-domain.auth.ap-northeast-1.amazoncognito.com/login?client_id=xxx&response_type=code&scope=email+openid+phone+aws.cognito.signin.user.admin&redirect_uri=https%3A%2F%2Fwiki2.h-akira.net"

# Cognitoサインアップページ  
VUE_APP_COGNITO_SIGNUP_URL="https://your-cognito-domain.auth.ap-northeast-1.amazoncognito.com/signup?client_id=xxx&response_type=code&scope=email+openid+phone+aws.cognito.signin.user.admin&redirect_uri=https%3A%2F%2Fwiki2.h-akira.net"

# APIベースURL
VUE_APP_API_BASE_URL="https://api.wiki2.h-akira.net/api"
```

## 作成されるリソース一覧

### DynamoDB テーブル
- **Wiki記事**: `wikiproject-table`
- **ファイルストレージ**: `wikiproject-storage-table`

### S3 バケット
- **ファイルストレージ**: `wikiproject-storage`

### Lambda関数
- **メイン処理**: `lambda-wikiproject`

### API Gateway
- **REST API**: `api-wikiproject`

## 外部依存リソース

### Cognito（既存のリソースを参照）
- User Pool（SSMパラメータ: `/WikiProject/Cognito/user_pool_id`）
- User Pool Client（SSMパラメータ: `/WikiProject/Cognito/client_id`, `/WikiProject/Cognito/client_secret`）
- User Pool Domain（SSMパラメータ: `/WikiProject/Cognito/domain`）

## トラブルシューティング

### SSMパラメータの確認

```bash
# Cognitoパラメータの確認
aws ssm get-parameter --name "/WikiProject/Cognito/domain"
aws ssm get-parameter --name "/WikiProject/Cognito/user_pool_id"
aws ssm get-parameter --name "/WikiProject/Cognito/client_id"
```

### Cognitoの設定確認

```bash
# User Pool IDの確認
aws cognito-idp list-user-pools --max-items 10

# Client IDの確認
aws cognito-idp list-user-pool-clients --user-pool-id ap-northeast-1_XXXXXXXXX
```

### ログの確認

```bash
# Lambda関数のログ
aws logs tail /aws/lambda/lambda-wikiproject --follow

# CloudFormationスタックの確認
aws cloudformation describe-stacks --stack-name stack-wiki2-main
```

## セキュリティ

- 全APIエンドポイントでCORS設定済み
- 既存のCognito認証によるユーザー管理
- DynamoDBでユーザーごとのデータ分離
- S3でユーザーごとのファイル分離
