from hadx.urls import Path, Router
from .share_views import share_handler

urlpatterns = [
    Path("<str:share_code>", share_handler, name="share_handler"),  # GET/PUT /api/share/{shareCode}
] 