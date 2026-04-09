"""Speaker enrollment CLI. Adds a named speaker to the persistent profile library."""
import argparse
import json
import os
import sys

import config
from utils.audio_utils import load_audio, extract_segment, parse_timestamp
from utils.embed_utils import get_embedding, save_embedding

PROFILES_DIR = config.PROFILES_DIR
MIN_ENROLLMENT_SEC = config.MIN_ENROLLMENT_SEC


def enroll_speaker(
    name: str,
    clip_path: str = None,
    file_path: str = None,
    start: str = None,
    end: str = None,
) -> None:
    """Enroll a speaker into the profile library."""
    name_key = name.strip().lower()

    if clip_path:
        audio, sr = load_audio(clip_path)
        duration = len(audio) / sr
        if duration < MIN_ENROLLMENT_SEC:
            raise ValueError(
                f"Clip is too short ({duration:.1f}s). "
                f"Need at least {MIN_ENROLLMENT_SEC}s of speech."
            )
    elif file_path and start and end:
        start_sec = parse_timestamp(start)
        end_sec = parse_timestamp(end)
        duration = end_sec - start_sec
        if duration < MIN_ENROLLMENT_SEC:
            raise ValueError(
                f"Segment is too short ({duration:.1f}s). "
                f"Need at least {MIN_ENROLLMENT_SEC}s of speech."
            )
        audio = extract_segment(file_path, start_sec, end_sec)
    else:
        raise ValueError("Provide either --clip or --file with --start and --end.")

    embedding = get_embedding(audio)

    os.makedirs(PROFILES_DIR, exist_ok=True)
    index_path = os.path.join(PROFILES_DIR, "index.json")
    if os.path.exists(index_path):
        with open(index_path) as f:
            index = json.load(f)
    else:
        index = {}

    npy_filename = f"{name_key}.npy"
    npy_path = os.path.join(PROFILES_DIR, npy_filename)
    save_embedding(embedding, npy_path)
    index[name_key] = npy_filename

    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)

    print(f"Enrolled '{name}' -> {npy_path}")


def main():
    parser = argparse.ArgumentParser(description="Enroll a speaker into the profile library.")
    parser.add_argument("--name", required=True, help="Speaker name, e.g. 'David'")
    parser.add_argument("--clip", help="Path to a standalone reference audio clip")
    parser.add_argument("--file", help="Path to a recording containing the speaker")
    parser.add_argument("--start", help="Start timestamp in recording, e.g. '8:10'")
    parser.add_argument("--end", help="End timestamp in recording, e.g. '8:22'")
    args = parser.parse_args()

    try:
        enroll_speaker(
            name=args.name,
            clip_path=args.clip,
            file_path=args.file,
            start=args.start,
            end=args.end,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
