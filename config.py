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

# AssemblyAI diarization: expected speaker range for your recordings.
# Setting max too high splits single speakers across multiple labels.
MIN_SPEAKERS = 2
MAX_SPEAKERS = 4

# U3 Pro temperature: 0.0 = fully deterministic. 0.1 yields ~5% relative WER improvement
# per AssemblyAI docs by introducing a small amount of decoding exploration.
TRANSCRIPTION_TEMPERATURE = 0.1

# Names and terms passed to AssemblyAI to boost recognition accuracy (Universal-3 Pro).
# Add names with unusual spellings or pronunciations. The model will hear these more reliably.
# Example: ["Arika", "Devraj", "Saoirse"]
KEYTERMS: list[str] = []

# Custom spelling corrections applied to AssemblyAI output text.
# Use when the model transcribes a name phonetically but spells it wrong.
# Each entry: {"from": ["phonetic spelling", "alternate"], "to": "CorrectSpelling"}
# "to" must be a single word. "from" is case-insensitive.
# Example: [{"from": ["erica", "africa"], "to": "Arika"}]
CUSTOM_SPELLING: list[dict] = []
