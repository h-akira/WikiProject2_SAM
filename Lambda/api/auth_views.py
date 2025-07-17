from hadx.shortcuts import json_response
import json
import logging

logger = logging.getLogger(__name__)

def token_exchange(master):
    """
    認証コードをトークンに交換するエンドポイント
    POST /api/auth/token
    """
    try:
        body = json.loads(master.event.get('body', '{}'))
        code = body.get('code')
        
        if not code:
            return json_response(master, {
                "success": False,
                "message": "認証コードが見つかりません",
                "error_code": "INVALID_CREDENTIALS"
            }, code=400)
        
        # hadxのCognito統合を使用してコードをトークンに交換
        flag = master.settings.COGNITO.set_auth_by_code(master, code)
        
        if flag and master.request.auth:
            # 認証成功
            user_info = {
                'sub': master.request.decode_token.get('sub'),
                'email': master.request.decode_token.get('email'),
                'email_verified': master.request.decode_token.get('email_verified'),
                'cognito:username': master.request.decode_token.get('cognito:username')
            }
            
            return json_response(master, {
                "success": True,
                "data": {
                    "token": master.request.access_token,
                    "user": {
                        "username": user_info.get('cognito:username'),
                        "email": user_info.get('email')
                    }
                }
            })
        else:
            # 認証失敗
            return json_response(master, {
                "success": False,
                "message": "認証コードの交換に失敗しました",
                "error_code": "INVALID_CREDENTIALS"
            }, code=400)
            
    except Exception as e:
        logger.exception(f"Token exchange error: {e}")
        return json_response(master, {
            "success": False,
            "message": "内部エラーが発生しました",
            "error_code": "INTERNAL_ERROR"
        }, code=500)

def auth_status(master):
    """
    認証状態を確認するエンドポイント
    GET /api/auth/status
    """
    try:
        if master.request.auth:
            # 認証済みの場合
            user_info = {
                'sub': master.request.decode_token.get('sub'),
                'email': master.request.decode_token.get('email'),
                'email_verified': master.request.decode_token.get('email_verified'),
                'cognito:username': master.request.decode_token.get('cognito:username')
            }
            
            response_data = {
                'success': True,
                'data': {
                    'authenticated': True,
                    'user': {
                        'username': user_info.get('cognito:username'),
                        'email': user_info.get('email')
                    }
                }
            }
        else:
            # 未認証の場合
            response_data = {
                'success': True,
                'data': {
                    'authenticated': False,
                    'user': None
                }
            }
        
        return json_response(master, response_data)
        
    except Exception as e:
        logger.exception(f"Auth status error: {e}")
        return json_response(master, {
            "success": False,
            "message": "内部エラーが発生しました",
            "error_code": "INTERNAL_ERROR"
        }, code=500)

def logout(master):
    """
    ログアウトエンドポイント
    POST /api/auth/logout
    """
    try:
        if master.request.auth:
            # Cognitoからサインアウト
            master.settings.COGNITO.sign_out(master)
        
        response_data = {
            'success': True,
            'message': 'ログアウトしました'
        }
        
        return json_response(master, response_data)
        
    except Exception as e:
        logger.exception(f"Logout error: {e}")
        return json_response(master, {
            "success": False,
            "message": "内部エラーが発生しました",
            "error_code": "INTERNAL_ERROR"
        }, code=500) 