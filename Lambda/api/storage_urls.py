from hadx.urls import Path, Router
from .storage_views import (
    storage_items_handler, storage_upload_handler, storage_folder_handler,
    download_file, delete_item
)

urlpatterns = [
    Path("items", storage_items_handler, name="storage_items_handler"),       # GET /api/storage/items
    Path("upload", storage_upload_handler, name="storage_upload_handler"),    # POST /api/storage/upload
    Path("folder", storage_folder_handler, name="storage_folder_handler"),    # POST /api/storage/folder
    Path("download/<str:item_id>", download_file, name="download_file"),      # GET /api/storage/download/{item_id}
    Path("item/<str:item_id>", delete_item, name="delete_item"),              # DELETE /api/storage/item/{item_id}
] 