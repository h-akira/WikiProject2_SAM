import os

MAPPING_PATH = ""  # 独自ドメインを使用
MAPPING_PATH_LOCAL = ""  # ローカル開発時のパス設定
DEBUG = True
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__),"../"))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_URL = "/static"  # 先頭の/はあってもなくても同じ扱
TIMEZONE = "Asia/Tokyo"

# DynamoDB テーブル名
WIKI_TABLE = os.environ.get('WIKI_TABLE', 'wikiproject-table')
STORAGE_TABLE = os.environ.get('STORAGE_TABLE', 'wikiproject-storage-table')
S3_BUCKET = os.environ.get('S3_BUCKET', 'wikiproject-storage')

# ログイン周りの設定
from hadx.authenticate import Cognito, ManagedAuthPage
import boto3

# 設定値を環境変数またはSSMから取得
if os.path.exists(os.path.join(BASE_DIR, "../admin.json")):
  import json
  with open(os.path.join(BASE_DIR, "../admin.json")) as f:
    admin = json.load(f)
  kwargs = {}
  try:
    kwargs["region_name"] = admin["region"]
  except KeyError:
    pass
  try:
    kwargs["profile_name"] = admin["profile"]
  except KeyError:
    pass
  session = boto3.Session(**kwargs)
  ssm = session.client('ssm')
else:
  ssm = boto3.client('ssm')

COGNITO = Cognito(
  domain=ssm.get_parameter(Name="/WikiProject/v2/Cognito/domain")["Parameter"]["Value"],
  user_pool_id=ssm.get_parameter(Name="/WikiProject/v2/Cognito/user_pool_id")["Parameter"]["Value"],
  client_id=ssm.get_parameter(Name="/WikiProject/v2/Cognito/client_id")["Parameter"]["Value"],
  client_secret=ssm.get_parameter(Name="/WikiProject/v2/Cognito/client_secret")["Parameter"]["Value"],
  region="ap-northeast-1"
)

AUTH_PAGE = ManagedAuthPage(
  scope="aws.cognito.signin.user.admin email openid phone",
  login_redirect_uri = ssm.get_parameter(Name="/WikiProject/v2/URL/home")["Parameter"]["Value"],
  local_login_redirect_uri="http://localhost:8080"
)

