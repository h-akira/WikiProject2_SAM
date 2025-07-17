from hadx.shortcuts import json_response

def home(master):
    """
    ホームエンドポイント
    """
    return json_response(master, {
        "message": "hadx_sample backend API",
        "version": "1.0.0",
        "endpoints": {
            "auth": {
                "token": "/api/auth/token",
                "status": "/api/auth/status", 
                "logout": "/api/auth/logout"
            }
        }
    })
