from hadx.shortcuts import json_response
import json
import logging
import boto3
import uuid
import base64
import mimetypes
from datetime import datetime
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
import os

logger = logging.getLogger(__name__)

def get_dynamodb():
    """DynamoDBクライアントを取得"""
    return boto3.resource('dynamodb', region_name='ap-northeast-1')

def get_s3():
    """S3クライアントを取得"""
    return boto3.client('s3', region_name='ap-northeast-1')

def storage_items_handler(master):
    """
    ファイル・フォルダ一覧取得（GET /api/storage/items）
    """
    method = master.event.get('httpMethod', 'GET')
    
    if method == 'GET':
        return get_storage_items(master)
    else:
        return json_response(master, {
            "success": False,
            "message": "サポートされていないHTTPメソッドです",
            "error_code": "METHOD_NOT_ALLOWED"
        }, code=405)

def storage_upload_handler(master):
    """
    ファイルアップロード（POST /api/storage/upload）
    """
    method = master.event.get('httpMethod', 'POST')
    
    if method == 'POST':
        return upload_file(master)
    else:
        return json_response(master, {
            "success": False,
            "message": "サポートされていないHTTPメソッドです",
            "error_code": "METHOD_NOT_ALLOWED"
        }, code=405)

def storage_folder_handler(master):
    """
    フォルダ作成（POST /api/storage/folder）
    """
    method = master.event.get('httpMethod', 'POST')
    
    if method == 'POST':
        return create_folder(master)
    else:
        return json_response(master, {
            "success": False,
            "message": "サポートされていないHTTPメソッドです",
            "error_code": "METHOD_NOT_ALLOWED"
        }, code=405)

def get_storage_items(master):
    """
    ファイル・フォルダ一覧取得
    GET /api/storage/items?path=/
    """
    if not master.request.auth:
        return json_response(master, {
            "success": False,
            "message": "認証が必要です",
            "error_code": "AUTH_REQUIRED"
        }, code=401)
    
    try:
        username = master.request.decode_token.get('cognito:username')
        path = master.request.query_params.get('path', '/')
        
        dynamodb = get_dynamodb()
        table = dynamodb.Table(master.settings.STORAGE_TABLE)
        
        # ユーザーのファイル一覧を取得
        response = table.query(
            IndexName='OwnerPathIndex',
            KeyConditionExpression=Key('owner').eq(username) & Key('path').begins_with(path)
        )
        
        items = []
        for item in response['Items']:
            items.append({
                'id': item.get('id'),
                'name': item.get('name'),
                'type': item.get('type', 'file'),
                'path': item.get('path'),
                'size': item.get('size', 0),
                'mimetype': item.get('mimetype', ''),
                'created_at': item.get('created_at'),
                'updated_at': item.get('updated_at'),
                'owner': item.get('owner')
            })
        
        return json_response(master, {
            "success": True,
            "data": {
                "items": items,
                "total": len(items)
            }
        })
        
    except Exception as e:
        logger.exception(f"Get storage items error: {e}")
        return json_response(master, {
            "success": False,
            "message": "ファイル一覧の取得に失敗しました",
            "error_code": "INTERNAL_ERROR"
        }, code=500)

def upload_file(master):
    """
    ファイルアップロード
    POST /api/storage/upload
    """
    if not master.request.auth:
        return json_response(master, {
            "success": False,
            "message": "認証が必要です",
            "error_code": "AUTH_REQUIRED"
        }, code=401)
    
    try:
        username = master.request.decode_token.get('cognito:username')
        
        # multipart/form-dataのパース（簡単な実装）
        body = master.event.get('body', '')
        is_base64 = master.event.get('isBase64Encoded', False)
        
        if is_base64:
            body = base64.b64decode(body)
        else:
            body = body.encode('utf-8')
        
        # ここではJSONとして送信されたファイルデータを想定
        # 実際の実装ではmultipart/form-dataのパーサーが必要
        try:
            data = json.loads(master.event.get('body', '{}'))
        except:
            return json_response(master, {
                "success": False,
                "message": "無効なリクエスト形式です",
                "error_code": "VALIDATION_ERROR"
            }, code=400)
        
        file_data = data.get('file_data')  # base64エンコードされたファイルデータ
        filename = data.get('filename')
        path = data.get('path', '/')
        
        if not file_data or not filename:
            return json_response(master, {
                "success": False,
                "message": "ファイルデータまたはファイル名が不正です",
                "error_code": "VALIDATION_ERROR"
            }, code=400)
        
        # ファイルIDを生成
        file_id = str(uuid.uuid4())
        
        # S3にアップロード
        s3 = get_s3()
        bucket_name = master.settings.S3_BUCKET
        s3_key = f"{username}/{file_id}/{filename}"
        
        # ファイルデータをデコード
        file_content = base64.b64decode(file_data)
        file_size = len(file_content)
        
        # MIMEタイプを推測
        mimetype, _ = mimetypes.guess_type(filename)
        if not mimetype:
            mimetype = 'application/octet-stream'
        
        # S3にアップロード
        s3.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=file_content,
            ContentType=mimetype
        )
        
        # DynamoDBにメタデータを保存
        now = datetime.now().isoformat()
        dynamodb = get_dynamodb()
        table = dynamodb.Table(master.settings.STORAGE_TABLE)
        
        item_data = {
            'id': file_id,
            'name': filename,
            'type': 'file',
            'path': path,
            'size': file_size,
            'mimetype': mimetype,
            'owner': username,
            's3_key': s3_key,
            'created_at': now,
            'updated_at': now
        }
        
        table.put_item(Item=item_data)
        
        # レスポンス
        response_data = {
            'uploaded_files': [{
                'id': file_id,
                'name': filename,
                'path': path,
                'size': file_size,
                'url': f"/api/storage/download/{file_id}"
            }]
        }
        
        return json_response(master, {
            "success": True,
            "data": response_data
        })
        
    except Exception as e:
        logger.exception(f"Upload file error: {e}")
        return json_response(master, {
            "success": False,
            "message": "ファイルのアップロードに失敗しました",
            "error_code": "INTERNAL_ERROR"
        }, code=500)

def create_folder(master):
    """
    フォルダ作成
    POST /api/storage/folder
    """
    if not master.request.auth:
        return json_response(master, {
            "success": False,
            "message": "認証が必要です",
            "error_code": "AUTH_REQUIRED"
        }, code=401)
    
    try:
        username = master.request.decode_token.get('cognito:username')
        body = json.loads(master.event.get('body', '{}'))
        
        name = body.get('name')
        path = body.get('path', '/')
        
        if not name:
            return json_response(master, {
                "success": False,
                "message": "フォルダ名が必要です",
                "error_code": "VALIDATION_ERROR"
            }, code=400)
        
        # フォルダIDを生成
        folder_id = str(uuid.uuid4())
        
        # DynamoDBにフォルダ情報を保存
        now = datetime.now().isoformat()
        dynamodb = get_dynamodb()
        table = dynamodb.Table(master.settings.STORAGE_TABLE)
        
        folder_data = {
            'id': folder_id,
            'name': name,
            'type': 'folder',
            'path': path,
            'size': 0,
            'mimetype': '',
            'owner': username,
            'created_at': now,
            'updated_at': now
        }
        
        table.put_item(Item=folder_data)
        
        return json_response(master, {
            "success": True,
            "data": {
                'id': folder_id,
                'name': name,
                'path': path,
                'created_at': now
            }
        })
        
    except Exception as e:
        logger.exception(f"Create folder error: {e}")
        return json_response(master, {
            "success": False,
            "message": "フォルダの作成に失敗しました",
            "error_code": "INTERNAL_ERROR"
        }, code=500)

def download_file(master, item_id):
    """
    ファイルダウンロード
    GET /api/storage/download/{item_id}
    """
    try:
        dynamodb = get_dynamodb()
        table = dynamodb.Table(master.settings.STORAGE_TABLE)
        
        # ファイル情報を取得
        response = table.get_item(Key={'id': item_id})
        
        if 'Item' not in response:
            return json_response(master, {
                "success": False,
                "message": "ファイルが見つかりません",
                "error_code": "FILE_NOT_FOUND"
            }, code=404)
        
        item = response['Item']
        
        # 権限チェック（所有者のみ）
        if master.request.auth:
            username = master.request.decode_token.get('cognito:username')
            if item.get('owner') != username:
                return json_response(master, {
                    "success": False,
                    "message": "ファイルにアクセスする権限がありません",
                    "error_code": "PERMISSION_DENIED"
                }, code=403)
        else:
            return json_response(master, {
                "success": False,
                "message": "認証が必要です",
                "error_code": "AUTH_REQUIRED"
            }, code=401)
        
        # S3からファイルを取得
        s3 = get_s3()
        bucket_name = master.settings.S3_BUCKET
        s3_key = item.get('s3_key')
        
        if not s3_key:
            return json_response(master, {
                "success": False,
                "message": "ファイルデータが見つかりません",
                "error_code": "FILE_NOT_FOUND"
            }, code=404)
        
        # S3オブジェクトを取得
        obj = s3.get_object(Bucket=bucket_name, Key=s3_key)
        file_content = obj['Body'].read()
        
        # バイナリレスポンスを返す
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': item.get('mimetype', 'application/octet-stream'),
                'Content-Disposition': f'attachment; filename="{item.get("name")}"',
                'Content-Length': str(len(file_content))
            },
            'body': base64.b64encode(file_content).decode('utf-8'),
            'isBase64Encoded': True
        }
        
    except Exception as e:
        logger.exception(f"Download file error: {e}")
        return json_response(master, {
            "success": False,
            "message": "ファイルのダウンロードに失敗しました",
            "error_code": "INTERNAL_ERROR"
        }, code=500)

def delete_item(master, item_id):
    """
    ファイル・フォルダ削除
    DELETE /api/storage/item/{item_id}
    """
    if not master.request.auth:
        return json_response(master, {
            "success": False,
            "message": "認証が必要です",
            "error_code": "AUTH_REQUIRED"
        }, code=401)
    
    try:
        username = master.request.decode_token.get('cognito:username')
        
        dynamodb = get_dynamodb()
        table = dynamodb.Table(master.settings.STORAGE_TABLE)
        
        # アイテム情報を取得
        response = table.get_item(Key={'id': item_id})
        
        if 'Item' not in response:
            return json_response(master, {
                "success": False,
                "message": "アイテムが見つかりません",
                "error_code": "ITEM_NOT_FOUND"
            }, code=404)
        
        item = response['Item']
        
        # 所有者チェック
        if item.get('owner') != username:
            return json_response(master, {
                "success": False,
                "message": "アイテムを削除する権限がありません",
                "error_code": "PERMISSION_DENIED"
            }, code=403)
        
        # ファイルの場合はS3からも削除
        if item.get('type') == 'file' and item.get('s3_key'):
            s3 = get_s3()
            bucket_name = master.settings.S3_BUCKET
            s3.delete_object(Bucket=bucket_name, Key=item['s3_key'])
        
        # DynamoDBから削除
        table.delete_item(Key={'id': item_id})
        
        return json_response(master, {
            "success": True,
            "message": "削除が完了しました"
        })
        
    except Exception as e:
        logger.exception(f"Delete item error: {e}")
        return json_response(master, {
            "success": False,
            "message": "アイテムの削除に失敗しました",
            "error_code": "INTERNAL_ERROR"
        }, code=500) 