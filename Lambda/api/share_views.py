from hadx.shortcuts import json_response
import json
import logging
import boto3
from datetime import datetime
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

def get_dynamodb():
    """DynamoDBクライアントを取得"""
    return boto3.resource('dynamodb', region_name='ap-northeast-1')

def share_handler(master, share_code):
    """
    共有記事の処理（GET/PUT /api/share/{shareCode}）
    """
    method = master.event.get('httpMethod', 'GET')
    
    if method == 'GET':
        return get_shared_page(master, share_code)
    elif method == 'PUT':
        return update_shared_page(master, share_code)
    else:
        return json_response(master, {
            "success": False,
            "message": "サポートされていないHTTPメソッドです",
            "error_code": "METHOD_NOT_ALLOWED"
        }, code=405)

def get_shared_page(master, share_code):
    """
    共有コードによる記事取得
    GET /api/share/{shareCode}
    """
    try:
        dynamodb = get_dynamodb()
        table = dynamodb.Table(master.settings.WIKI_TABLE)
        
        # 共有コードでページを検索
        response = table.query(
            IndexName='ShareCodeIndex',
            KeyConditionExpression=Key('share_code').eq(share_code)
        )
        
        if not response['Items']:
            return json_response(master, {
                "success": False,
                "message": "共有コードが無効です",
                "error_code": "INVALID_SHARE_CODE"
            }, code=404)
        
        page = response['Items'][0]
        
        # 共有が有効かチェック
        if not page.get('share', False):
            return json_response(master, {
                "success": False,
                "message": "この記事は共有されていません",
                "error_code": "INVALID_SHARE_CODE"
            }, code=404)
        
        # レスポンス用データ
        response_data = {
            'username': page.get('username'),
            'slug': page.get('slug'),
            'title': page.get('title'),
            'text': page.get('text'),
            'share_code': page.get('share_code'),
            'share_edit_permission': page.get('share_edit_permission', False),
            'last_updated': page.get('last_updated')
        }
        
        return json_response(master, {
            "success": True,
            "data": response_data
        })
        
    except Exception as e:
        logger.exception(f"Get shared page error: {e}")
        return json_response(master, {
            "success": False,
            "message": "共有記事の取得に失敗しました",
            "error_code": "INTERNAL_ERROR"
        }, code=500)

def update_shared_page(master, share_code):
    """
    共有コードによる記事更新（限定的）
    PUT /api/share/{shareCode}
    """
    try:
        dynamodb = get_dynamodb()
        table = dynamodb.Table(master.settings.WIKI_TABLE)
        
        # 共有コードでページを検索
        response = table.query(
            IndexName='ShareCodeIndex',
            KeyConditionExpression=Key('share_code').eq(share_code)
        )
        
        if not response['Items']:
            return json_response(master, {
                "success": False,
                "message": "共有コードが無効です",
                "error_code": "INVALID_SHARE_CODE"
            }, code=404)
        
        page = response['Items'][0]
        
        # 共有が有効かチェック
        if not page.get('share', False):
            return json_response(master, {
                "success": False,
                "message": "この記事は共有されていません",
                "error_code": "INVALID_SHARE_CODE"
            }, code=404)
        
        # 編集権限チェック
        if not page.get('share_edit_permission', False):
            return json_response(master, {
                "success": False,
                "message": "この共有記事の編集権限がありません",
                "error_code": "PERMISSION_DENIED"
            }, code=403)
        
        body = json.loads(master.event.get('body', '{}'))
        
        # 現在時刻
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 更新可能なフィールドのみ（共有記事では限定的）
        update_data = {}
        if 'title' in body:
            update_data['title'] = body['title']
        if 'text' in body:
            update_data['text'] = body['text']
        update_data['last_updated'] = now
        
        if not update_data:
            return json_response(master, {
                "success": False,
                "message": "更新するデータがありません",
                "error_code": "VALIDATION_ERROR"
            }, code=400)
        
        # DynamoDBを更新
        update_expression = "SET " + ", ".join([f"#{k} = :{k}" for k in update_data.keys()])
        expression_attribute_names = {f"#{k}": k for k in update_data.keys()}
        expression_attribute_values = {f":{k}": v for k, v in update_data.items()}
        
        response = table.update_item(
            Key={'username': page['username'], 'slug': page['slug']},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues='ALL_NEW'
        )
        
        # レスポンス用データ
        updated_page = response['Attributes']
        response_data = {
            'username': updated_page.get('username'),
            'slug': updated_page.get('slug'),
            'title': updated_page.get('title'),
            'text': updated_page.get('text'),
            'share_code': updated_page.get('share_code'),
            'share_edit_permission': updated_page.get('share_edit_permission', False),
            'last_updated': updated_page.get('last_updated')
        }
        
        return json_response(master, {
            "success": True,
            "data": response_data
        })
        
    except Exception as e:
        logger.exception(f"Update shared page error: {e}")
        return json_response(master, {
            "success": False,
            "message": "共有記事の更新に失敗しました",
            "error_code": "INTERNAL_ERROR"
        }, code=500) 