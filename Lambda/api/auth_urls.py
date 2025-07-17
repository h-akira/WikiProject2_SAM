from hadx.urls import Path, Router
from .auth_views import token_exchange, auth_status, logout

urlpatterns = [
    Path("token", token_exchange, name="token_exchange"),
    Path("status", auth_status, name="auth_status"), 
    Path("logout", logout, name="logout"),
] 