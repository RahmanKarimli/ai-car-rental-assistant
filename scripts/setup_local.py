#!/usr/bin/env python3
from pathlib import Path
from secrets import token_urlsafe
ROOT=Path(__file__).resolve().parents[1]
secrets=ROOT/".secrets";secrets.mkdir(exist_ok=True);secrets.chmod(0o700)
for name in ["postgres_password","app_database_password","graph_database_password","redis_password","quote_signing_key"]:
    file=secrets/name
    if not file.exists():file.write_text(token_urlsafe(40)+"\n");file.chmod(0o600)
key=secrets/"openai_api_key"
if not key.exists():key.touch();key.chmod(0o600)
if not (ROOT/".env").exists():(ROOT/".env").write_text((ROOT/".env.example").read_text())
for file in secrets.iterdir():
    if file.is_file():file.chmod(0o644)
print("Local configuration is ready. Set .secrets/openai_api_key privately, then start Docker Compose.")
