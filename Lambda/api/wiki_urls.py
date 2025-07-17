from hadx.urls import Path, Router
from .wiki_views import pages_handler, recent_handler, page_handler

urlpatterns = [
    Path("pages", pages_handler, name="pages_handler"),          # GET/POST /api/wiki/pages
    Path("recent", recent_handler, name="recent_handler"),       # GET /api/wiki/recent
    Path("<str:username>/<path:slug>", page_handler, name="page_handler"), # GET/PUT/DELETE /api/wiki/{username}/{slug}
] 