from pathlib import Path
from app.core.config import settings
from app.core.errors import DomainError
class Filesystem:
    def path(self,key):
        root=Path(settings().asset_root).resolve();path=(root/key).resolve()
        if path==root or not path.is_relative_to(root):raise DomainError("INVALID_ASSET","Invalid asset key")
        return path
    def put(self,key,data):
        path=self.path(key);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    def open(self,key):
        path=self.path(key)
        if not path.is_file():raise DomainError("NOT_FOUND","Asset not found",404)
        return path
assets=Filesystem()
