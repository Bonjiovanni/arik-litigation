import sys
from pathlib import Path

# Add email_pipeline/ to sys.path so its modules can be imported directly.
# merge_and_classify.py uses `from strippers import get_body_clean` (bare import),
# which only works if email_pipeline/ is on sys.path.
sys.path.insert(0, str(Path(__file__).parent.parent / "email_pipeline"))

# Add jh_ltc/ to sys.path so its modules can be imported directly.
sys.path.insert(0, str(Path(__file__).parent.parent / "jh_ltc"))
