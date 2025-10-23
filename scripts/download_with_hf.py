#!/usr/bin/env python3
# Optional helper: download a HF repo snapshot without the CLI.
# Usage: ./scripts/download_with_hf.py <repo_id> <dest_dir>
import sys
from huggingface_hub import snapshot_download

if len(sys.argv) < 3:
    print("Usage: download_with_hf.py <repo_id> <dest_dir>")
    sys.exit(2)

repo_id = sys.argv[1]
dest = sys.argv[2]
snapshot_download(repo_id=repo_id, local_dir=dest, local_dir_use_symlinks=False)
print("Downloaded:", repo_id, "->", dest)
