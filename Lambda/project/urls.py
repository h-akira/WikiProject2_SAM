from hadx.urls import Path, Router
from .views import home

urlpatterns = [
  Path("", home, name="home"),
  Router("api/auth", "api.auth_urls", name="auth_api"),
  Router("api/wiki", "api.wiki_urls", name="wiki_api"),
  Router("api/storage", "api.storage_urls", name="storage_api"),
  Router("api/share", "api.share_urls", name="share_api"),
  Router("accounts", "accounts.urls", name="accounts"),
]
