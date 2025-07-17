from hadx.shortcuts import json_response
import json
import logging
import boto3
import uuid
from datetime import datetime
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
import os

logger = logging.getLogger(__name__)

def get_dynamodb():
    """DynamoDBクライアントを取得"""
    return boto3.resource('dynamodb', region_name='ap-northeast-1')

def pages_handler(master):
    """
    記事一覧の処理（GET/POST /api/wiki/pages）
    """
    method = master.event.get('httpMethod', 'GET')
    
    if method == 'GET':
        return get_pages(master)
    elif method == 'POST':
        return create_page(master)
    else:
        return json_response(master, {
            "success": False,
            "message": "サポートされていないHTTPメソッドです",
            "error_code": "METHOD_NOT_ALLOWED"
        }, code=405)

def recent_handler(master):
    """
    最近の記事取得（GET /api/wiki/recent）
    """
    method = master.event.get('httpMethod', 'GET')
    
    if method == 'GET':
        return get_recent(master)
    else:
        return json_response(master, {
            "success": False,
            "message": "サポートされていないHTTPメソッドです",
            "error_code": "METHOD_NOT_ALLOWED"
        }, code=405)

def page_handler(master, username, slug):
    """
    個別記事の処理（GET/PUT/DELETE /api/wiki/{username}/{slug}）
    """
    method = master.event.get('httpMethod', 'GET')
    
    if method == 'GET':
        return get_page(master, username, slug)
    elif method == 'PUT':
        return update_page(master, username, slug)
    elif method == 'DELETE':
        return delete_page(master, username, slug)
    else:
        return json_response(master, {
            "success": False,
            "message": "サポートされていないHTTPメソッドです",
            "error_code": "METHOD_NOT_ALLOWED"
        }, code=405)

def get_pages(master):
    """
    記事一覧と階層データの取得
    GET /api/wiki/pages
    """
    try:
        dynamodb = get_dynamodb()
        table = dynamodb.Table(master.settings.WIKI_TABLE)
        
        # 全ページをスキャン
        response = table.scan()
        pages = response['Items']
        
        # 認証状態に応じてフィルタリング
        filtered_pages = []
        for page in pages:
            # パブリックページまたは認証済みユーザーの場合表示
            if page.get('public', False) or (master.request.auth and 
                master.request.decode_token.get('cognito:username') == page.get('username')):
                filtered_pages.append({
                    'username': page.get('username'),
                    'slug': page.get('slug'),
                    'title': page.get('title'),
                    'last_updated': page.get('last_updated'),
                    'public': page.get('public', False),
                    'priority': page.get('priority', 0)
                })
        
        # 階層データの生成（簡単な実装）
        tree_data = []
        for username in set(page['username'] for page in filtered_pages):
            user_pages = [p for p in filtered_pages if p['username'] == username]
            html = f"<h3>{username}</h3><ul>"
            for page in sorted(user_pages, key=lambda x: x.get('priority', 0), reverse=True):
                html += f"<li><a href=\"/{username}/{page['slug']}\">{page['title']}</a></li>"
            html += "</ul>"
            tree_data.append({
                'username': username,
                'html': html
            })
        
        return json_response(master, {
            "success": True,
            "data": {
                "pages": filtered_pages,
                "treeData": tree_data
            }
        })
        
    except Exception as e:
        logger.exception(f"Get pages error: {e}")
        return json_response(master, {
            "success": False,
            "message": "記事一覧の取得に失敗しました",
            "error_code": "INTERNAL_ERROR"
        }, code=500)

def get_recent(master):
    """
    最近更新された記事の取得
    GET /api/wiki/recent
    """
    try:
        dynamodb = get_dynamodb()
        table = dynamodb.Table(master.settings.WIKI_TABLE)
        
        # 全ページをスキャンして更新日時でソート
        response = table.scan()
        pages = response['Items']
        
        # 認証状態に応じてフィルタリング
        filtered_pages = []
        for page in pages:
            if page.get('public', False) or (master.request.auth and 
                master.request.decode_token.get('cognito:username') == page.get('username')):
                filtered_pages.append({
                    'username': page.get('username'),
                    'slug': page.get('slug'),
                    'title': page.get('title'),
                    'last_updated': page.get('last_updated')
                })
        
        # 更新日時でソート（最新順）
        filtered_pages.sort(key=lambda x: x.get('last_updated', ''), reverse=True)
        
        # 最新10件を返す
        recent_pages = filtered_pages[:10]
        
        return json_response(master, {
            "success": True,
            "data": recent_pages
        })
        
    except Exception as e:
        logger.exception(f"Get recent pages error: {e}")
        return json_response(master, {
            "success": False,
            "message": "最近の記事取得に失敗しました",
            "error_code": "INTERNAL_ERROR"
        }, code=500)

def create_page(master):
    """
    新規記事作成
    POST /api/wiki/pages
    """
    if not master.request.auth:
        return json_response(master, {
            "success": False,
            "message": "認証が必要です",
            "error_code": "AUTH_REQUIRED"
        }, code=401)
    
    try:
        body = json.loads(master.event.get('body', '{}'))
        username = master.request.decode_token.get('cognito:username')
        
        # 必須フィールドの検証
        required_fields = ['title', 'slug', 'text']
        for field in required_fields:
            if not body.get(field):
                return json_response(master, {
                    "success": False,
                    "message": f"{field}は必須です",
                    "error_code": "VALIDATION_ERROR"
                }, code=400)
        
        # 現在時刻
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # ページデータ
        page_data = {
            'username': username,
            'slug': body['slug'],
            'title': body['title'],
            'text': body['text'],
            'priority': body.get('priority', 0),
            'public': body.get('public', False),
            'edit_permission': body.get('edit_permission', False),
            'share': body.get('share', False),
            'share_code': body.get('share_code', str(uuid.uuid4())),
            'share_edit_permission': body.get('share_edit_permission', False),
            'last_updated': now
        }
        
        # DynamoDBに保存
        dynamodb = get_dynamodb()
        table = dynamodb.Table(master.settings.WIKI_TABLE)
        
        # 既存チェック
        try:
            existing = table.get_item(Key={'username': username, 'slug': body['slug']})
            if 'Item' in existing:
                return json_response(master, {
                    "success": False,
                    "message": "この記事は既に存在します",
                    "error_code": "PAGE_EXISTS"
                }, code=400)
        except ClientError:
            pass
        
        table.put_item(Item=page_data)
        
        return json_response(master, {
            "success": True,
            "data": page_data
        })
        
    except Exception as e:
        logger.exception(f"Create page error: {e}")
        return json_response(master, {
            "success": False,
            "message": "記事の作成に失敗しました",
            "error_code": "INTERNAL_ERROR"
        }, code=500)

def get_page(master, username, slug):
    """
    記事詳細の取得
    GET /api/wiki/{username}/{slug}
    """
    try:
        dynamodb = get_dynamodb()
        table = dynamodb.Table(master.settings.WIKI_TABLE)
        
        response = table.get_item(Key={'username': username, 'slug': slug})
        
        if 'Item' not in response:
            return json_response(master, {
                "success": False,
                "message": "記事が見つかりません",
                "error_code": "PAGE_NOT_FOUND"
            }, code=404)
        
        page = response['Item']
        
        # アクセス権限チェック
        is_owner = (master.request.auth and 
                   master.request.decode_token.get('cognito:username') == username)
        is_public = page.get('public', False)
        
        if not is_public and not is_owner:
            return json_response(master, {
                "success": False,
                "message": "この記事にアクセスする権限がありません",
                "error_code": "PERMISSION_DENIED"
            }, code=403)
        
        return json_response(master, {
            "success": True,
            "data": page
        })
        
    except Exception as e:
        logger.exception(f"Get page error: {e}")
        return json_response(master, {
            "success": False,
            "message": "記事の取得に失敗しました",
            "error_code": "INTERNAL_ERROR"
        }, code=500)

def update_page(master, username, slug):
    """
    記事更新
    PUT /api/wiki/{username}/{slug}
    """
    if not master.request.auth:
        return json_response(master, {
            "success": False,
            "message": "認証が必要です",
            "error_code": "AUTH_REQUIRED"
        }, code=401)
    
    try:
        current_user = master.request.decode_token.get('cognito:username')
        
        # 所有者チェック
        if current_user != username:
            return json_response(master, {
                "success": False,
                "message": "この記事を編集する権限がありません",
                "error_code": "PERMISSION_DENIED"
            }, code=403)
        
        body = json.loads(master.event.get('body', '{}'))
        
        # 現在時刻
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 更新データ
        update_data = {
            'title': body.get('title'),
            'text': body.get('text'),
            'priority': body.get('priority', 0),
            'public': body.get('public', False),
            'edit_permission': body.get('edit_permission', False),
            'share': body.get('share', False),
            'share_code': body.get('share_code'),
            'share_edit_permission': body.get('share_edit_permission', False),
            'last_updated': now
        }
        
        # Noneの値を除外
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        # DynamoDBを更新
        dynamodb = get_dynamodb()
        table = dynamodb.Table(master.settings.WIKI_TABLE)
        
        # 更新式を作成
        update_expression = "SET " + ", ".join([f"#{k} = :{k}" for k in update_data.keys()])
        expression_attribute_names = {f"#{k}": k for k in update_data.keys()}
        expression_attribute_values = {f":{k}": v for k, v in update_data.items()}
        
        response = table.update_item(
            Key={'username': username, 'slug': slug},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues='ALL_NEW'
        )
        
        return json_response(master, {
            "success": True,
            "data": response['Attributes']
        })
        
    except Exception as e:
        logger.exception(f"Update page error: {e}")
        return json_response(master, {
            "success": False,
            "message": "記事の更新に失敗しました",
            "error_code": "INTERNAL_ERROR"
        }, code=500)

def delete_page(master, username, slug):
    """
    記事削除
    DELETE /api/wiki/{username}/{slug}
    """
    if not master.request.auth:
        return json_response(master, {
            "success": False,
            "message": "認証が必要です",
            "error_code": "AUTH_REQUIRED"
        }, code=401)
    
    try:
        current_user = master.request.decode_token.get('cognito:username')
        
        # 所有者チェック
        if current_user != username:
            return json_response(master, {
                "success": False,
                "message": "この記事を削除する権限がありません",
                "error_code": "PERMISSION_DENIED"
            }, code=403)
        
        # DynamoDBから削除
        dynamodb = get_dynamodb()
        table = dynamodb.Table(master.settings.WIKI_TABLE)
        
        table.delete_item(Key={'username': username, 'slug': slug})
        
        return json_response(master, {
            "success": True,
            "message": "記事を削除しました"
        })
        
    except Exception as e:
        logger.exception(f"Delete page error: {e}")
        return json_response(master, {
            "success": False,
            "message": "記事の削除に失敗しました",
            "error_code": "INTERNAL_ERROR"
        }, code=500) 