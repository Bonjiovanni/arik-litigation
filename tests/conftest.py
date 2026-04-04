import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent

# Repo root — needed for root-level modules (fw_dir_tree, fw_file_inventory,
# drive_scout_server, fw_walk, fw_classify, fw_triage, etc.)
sys.path.insert(0, str(_REPO_ROOT))

# Add email_pipeline/ to sys.path so its modules can be imported directly.
# merge_and_classify.py uses `from strippers import get_body_clean` (bare import),
# which only works if email_pipeline/ is on sys.path.
sys.path.insert(0, str(_REPO_ROOT / "email_pipeline"))

# Add jh_ltc/ to sys.path so its modules can be imported directly.
sys.path.insert(0, str(_REPO_ROOT / "jh_ltc"))
