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

# U3 Pro transcription prompt. Mutually exclusive with KEYTERMS — do not set both.
# Priority: accurate word capture and correct speaker attribution, especially during
# overlapping speech. [CROSSTALK] and [masked] are last resorts only.
# Recording context: one speaker (Arik) is consistently close to the mic; all others
# are ambient and will sound softer — this is a mic distance issue, not unclear speech.
TRANSCRIPTION_PROMPT: str = (
    "Always: Transcribe speech exactly as heard. "
    "Accuracy is the top priority — work hard to capture every word correctly, "
    "including during overlapping or difficult speech. "
    "After transcribing, review for hallucinations or errors and revise."
    "\n\n"
    "When two speakers talk simultaneously, attempt to transcribe and attribute "
    "each speaker's words separately. "
    "Only use [CROSSTALK] when overlapping speech is genuinely indistinguishable "
    "after your best effort — it is a last resort, not a default."
    "\n\n"
    "If a word or phrase remains truly unclear after your best attempt, "
    "mark it as [masked] rather than guessing."
    "\n\n"
    "One speaker is consistently closer to the microphone and will sound louder "
    "throughout. Other speakers are more distant and will sound softer. "
    "Treat volume differences as a recording condition, not as unclear speech — "
    "transcribe all speakers with equal effort regardless of volume. "
    "The close-mic speaker tends to speak rapidly, with tangential trains of thought, "
    "and does not always enunciate clearly — do not treat fast or clipped speech as "
    "unclear; work hard to capture it accurately."
    "\n\n"
    "Preserve meaningful speech patterns: include false starts (I was— I went), "
    "self-corrections, and restarts as spoken. "
    "Capture significant hesitations where they affect meaning or pacing. "
    "You do not need to capture every filler word."
)
