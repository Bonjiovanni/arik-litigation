import os

ASSEMBLYAI_API_KEY = os.environ.get("ASSEMBLYAI_API_KEY", "")
PROFILES_DIR = "profiles"
OUTPUT_DIR = "output"
SPEAKER_MATCH_THRESHOLD = 0.75
SRT_PAUSE_THRESHOLD_SEC = 1.5   # seconds of silence to break an SRT block
INAUDIBLE_CONFIDENCE = 0.20     # words at or below this → [inaudible]
PHONETIC_CONFIDENCE = 0.50      # words at or below this → [phonetic: word]
INTERRUPT_GAP_MS = 200          # gap < this between speakers → interruption (--)
MIN_ENROLLMENT_SEC = 12.0       # minimum reference audio for enrollment
