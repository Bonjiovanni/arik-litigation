"""Tests for session_importer.py — merges Claude Code JSONL sessions across project folders."""

import json
import os
import shutil
import tempfile
import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_dirs(tmp_path):
    """Create source and target project folders with realistic structure."""
    source = tmp_path / "c--Users-arika-Repo-for-Claude-android"
    target = tmp_path / "C--Users-arika-OneDrive-CLaude-Cowork"
    source.mkdir()
    target.mkdir()
    return source, target


def make_jsonl_line(role, cwd, extra=None):
    """Build a single JSONL message line with realistic structure."""
    obj = {
        "type": role,
        "message": {"role": role, "content": "hello"},
        "cwd": cwd,
        "sessionId": "abc-123",
        "timestamp": "2026-04-05T08:00:00.000Z",
        "entrypoint": "claude-vscode",
    }
    if extra:
        obj.update(extra)
    return json.dumps(obj)


def write_session(path, lines):
    """Write a list of JSON strings as a .jsonl file."""
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")


def read_session(path):
    """Read a .jsonl file and return list of parsed dicts."""
    results = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    return results


# ── Import target ─────────────────────────────────────────────────────────────

from session_importer import import_sessions


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestBasicCopy:
    """Sessions are copied from source to target."""

    def test_copies_jsonl_to_target(self, tmp_dirs):
        source, target = tmp_dirs
        write_session(
            source / "aaa-111.jsonl",
            [make_jsonl_line("user", r"C:\Users\arika\Repo-for-Claude-android")],
        )

        import_sessions(str(source), str(target))

        assert (target / "aaa-111.jsonl").exists()

    def test_copies_multiple_files(self, tmp_dirs):
        source, target = tmp_dirs
        for name in ["aaa-111.jsonl", "bbb-222.jsonl", "ccc-333.jsonl"]:
            write_session(
                source / name,
                [make_jsonl_line("user", r"C:\Users\arika\Repo-for-Claude-android")],
            )

        import_sessions(str(source), str(target))

        assert (target / "aaa-111.jsonl").exists()
        assert (target / "bbb-222.jsonl").exists()
        assert (target / "ccc-333.jsonl").exists()

    def test_copies_subagent_directories(self, tmp_dirs):
        source, target = tmp_dirs
        # Main session
        write_session(
            source / "aaa-111.jsonl",
            [make_jsonl_line("user", r"C:\Users\arika\Repo-for-Claude-android")],
        )
        # Subagent directory and file
        sub_dir = source / "aaa-111" / "subagents"
        sub_dir.mkdir(parents=True)
        write_session(
            sub_dir / "agent-abc123.jsonl",
            [make_jsonl_line("assistant", r"C:\Users\arika\Repo-for-Claude-android")],
        )

        import_sessions(str(source), str(target))

        assert (target / "aaa-111.jsonl").exists()
        assert (target / "aaa-111" / "subagents" / "agent-abc123.jsonl").exists()


class TestCwdReplacement:
    """Cat 1: cwd fields are replaced with the target path."""

    def test_replaces_cwd_in_user_message(self, tmp_dirs):
        source, target = tmp_dirs
        old_cwd = r"C:\Users\arika\Repo-for-Claude-android"
        new_cwd = r"C:\Users\arika\OneDrive\CLaude Cowork"
        write_session(
            source / "aaa-111.jsonl",
            [make_jsonl_line("user", old_cwd)],
        )

        import_sessions(str(source), str(target), target_cwd=new_cwd)

        records = read_session(target / "aaa-111.jsonl")
        assert records[0]["cwd"] == new_cwd

    def test_replaces_cwd_in_every_line(self, tmp_dirs):
        source, target = tmp_dirs
        old_cwd = r"C:\Users\arika\Repo-for-Claude-android"
        new_cwd = r"C:\Users\arika\OneDrive\CLaude Cowork"
        write_session(
            source / "aaa-111.jsonl",
            [
                make_jsonl_line("user", old_cwd),
                make_jsonl_line("assistant", old_cwd),
                make_jsonl_line("user", old_cwd),
            ],
        )

        import_sessions(str(source), str(target), target_cwd=new_cwd)

        records = read_session(target / "aaa-111.jsonl")
        for rec in records:
            assert rec["cwd"] == new_cwd

    def test_replaces_cwd_in_subagent_files(self, tmp_dirs):
        source, target = tmp_dirs
        old_cwd = r"C:\Users\arika\Repo-for-Claude-android"
        new_cwd = r"C:\Users\arika\OneDrive\CLaude Cowork"
        sub_dir = source / "aaa-111" / "subagents"
        sub_dir.mkdir(parents=True)
        write_session(
            source / "aaa-111.jsonl",
            [make_jsonl_line("user", old_cwd)],
        )
        write_session(
            sub_dir / "agent-abc.jsonl",
            [make_jsonl_line("assistant", old_cwd)],
        )

        import_sessions(str(source), str(target), target_cwd=new_cwd)

        records = read_session(target / "aaa-111" / "subagents" / "agent-abc.jsonl")
        assert records[0]["cwd"] == new_cwd


class TestCat2Untouched:
    """Cat 2: Tool I/O file paths are NOT modified."""

    def test_leaves_file_path_input_unchanged(self, tmp_dirs):
        source, target = tmp_dirs
        old_cwd = r"C:\Users\arika\Repo-for-Claude-android"
        new_cwd = r"C:\Users\arika\OneDrive\CLaude Cowork"
        file_path = r"C:\Users\arika\Repo-for-Claude-android\fw_walk.py"
        line = make_jsonl_line("assistant", old_cwd, extra={
            "message": {
                "role": "assistant",
                "content": [{"type": "tool_use", "input": {"file_path": file_path}}],
            }
        })
        write_session(source / "aaa-111.jsonl", [line])

        import_sessions(str(source), str(target), target_cwd=new_cwd)

        records = read_session(target / "aaa-111.jsonl")
        tool_input = records[0]["message"]["content"][0]["input"]
        assert tool_input["file_path"] == file_path

    def test_leaves_bash_command_unchanged(self, tmp_dirs):
        source, target = tmp_dirs
        old_cwd = r"C:\Users\arika\Repo-for-Claude-android"
        new_cwd = r"C:\Users\arika\OneDrive\CLaude Cowork"
        bash_cmd = r'dir "C:\Users\arika\Repo-for-Claude-android\tests"'
        line = make_jsonl_line("assistant", old_cwd, extra={
            "message": {
                "role": "assistant",
                "content": [{"type": "tool_use", "input": {"command": bash_cmd}}],
            }
        })
        write_session(source / "aaa-111.jsonl", [line])

        import_sessions(str(source), str(target), target_cwd=new_cwd)

        records = read_session(target / "aaa-111.jsonl")
        tool_input = records[0]["message"]["content"][0]["input"]
        assert tool_input["command"] == bash_cmd


class TestCat3Untouched:
    """Cat 3: Content text mentioning paths is NOT modified."""

    def test_leaves_text_content_unchanged(self, tmp_dirs):
        source, target = tmp_dirs
        old_cwd = r"C:\Users\arika\Repo-for-Claude-android"
        new_cwd = r"C:\Users\arika\OneDrive\CLaude Cowork"
        text_with_path = r"The script lives at C:\Users\arika\Repo-for-Claude-android\fw_walk.py"
        line = make_jsonl_line("assistant", old_cwd, extra={
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": text_with_path}],
            }
        })
        write_session(source / "aaa-111.jsonl", [line])

        import_sessions(str(source), str(target), target_cwd=new_cwd)

        records = read_session(target / "aaa-111.jsonl")
        text = records[0]["message"]["content"][0]["text"]
        assert text == text_with_path


class TestSafety:
    """Import is safe — no data loss, no overwrites."""

    def test_preserves_original_files(self, tmp_dirs):
        source, target = tmp_dirs
        write_session(
            source / "aaa-111.jsonl",
            [make_jsonl_line("user", r"C:\Users\arika\Repo-for-Claude-android")],
        )

        import_sessions(str(source), str(target))

        # Source file must still exist, unmodified
        assert (source / "aaa-111.jsonl").exists()
        original = read_session(source / "aaa-111.jsonl")
        assert original[0]["cwd"] == r"C:\Users\arika\Repo-for-Claude-android"

    def test_skips_existing_files_in_target(self, tmp_dirs):
        source, target = tmp_dirs
        write_session(
            source / "aaa-111.jsonl",
            [make_jsonl_line("user", r"C:\Users\arika\Repo-for-Claude-android")],
        )
        # Pre-existing file in target with different content
        write_session(
            target / "aaa-111.jsonl",
            [make_jsonl_line("user", r"C:\Users\arika\OneDrive\CLaude Cowork",
                             extra={"message": {"role": "user", "content": "ORIGINAL"}})],
        )

        result = import_sessions(str(source), str(target))

        # Target file should NOT be overwritten
        records = read_session(target / "aaa-111.jsonl")
        assert records[0]["message"]["content"] == "ORIGINAL"
        assert "aaa-111.jsonl" in result["skipped"]

    def test_does_not_modify_non_jsonl_files(self, tmp_dirs):
        source, target = tmp_dirs
        # Put a non-jsonl file in source
        (source / "notes.txt").write_text("do not copy me")
        write_session(
            source / "aaa-111.jsonl",
            [make_jsonl_line("user", r"C:\Users\arika\Repo-for-Claude-android")],
        )

        import_sessions(str(source), str(target))

        assert not (target / "notes.txt").exists()


class TestEdgeCases:
    """Graceful handling of malformed data and edge cases."""

    def test_handles_malformed_json_lines(self, tmp_dirs):
        source, target = tmp_dirs
        session_file = source / "aaa-111.jsonl"
        with open(session_file, "w", encoding="utf-8") as f:
            f.write(make_jsonl_line("user", r"C:\Users\arika\Repo-for-Claude-android") + "\n")
            f.write("NOT VALID JSON\n")
            f.write(make_jsonl_line("assistant", r"C:\Users\arika\Repo-for-Claude-android") + "\n")

        # Should not crash
        import_sessions(str(source), str(target))

        assert (target / "aaa-111.jsonl").exists()
        # Malformed line should be preserved as-is
        with open(target / "aaa-111.jsonl", "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert lines[1].strip() == "NOT VALID JSON"

    def test_handles_lines_without_cwd(self, tmp_dirs):
        source, target = tmp_dirs
        new_cwd = r"C:\Users\arika\OneDrive\CLaude Cowork"
        # Some JSONL lines don't have cwd (e.g., metadata lines)
        no_cwd_line = json.dumps({"type": "agent-setting", "agentSetting": "orchestrator"})
        with_cwd_line = make_jsonl_line("user", r"C:\Users\arika\Repo-for-Claude-android")
        write_session(source / "aaa-111.jsonl", [no_cwd_line, with_cwd_line])

        import_sessions(str(source), str(target), target_cwd=new_cwd)

        records = read_session(target / "aaa-111.jsonl")
        assert "cwd" not in records[0]  # metadata line unchanged
        assert records[1]["cwd"] == new_cwd

    def test_handles_empty_source_folder(self, tmp_dirs):
        source, target = tmp_dirs
        # No JSONL files at all
        result = import_sessions(str(source), str(target))
        assert result["copied"] == 0

    def test_handles_case_variations_in_cwd(self, tmp_dirs):
        """Windows paths can have inconsistent casing (c: vs C:)."""
        source, target = tmp_dirs
        new_cwd = r"C:\Users\arika\OneDrive\CLaude Cowork"
        # Some sessions use lowercase c:, some uppercase C:
        write_session(source / "aaa-111.jsonl", [
            make_jsonl_line("user", r"c:\Users\arika\Repo-for-Claude-android"),
            make_jsonl_line("user", r"C:\Users\arika\Repo-for-Claude-android"),
        ])

        import_sessions(str(source), str(target), target_cwd=new_cwd)

        records = read_session(target / "aaa-111.jsonl")
        assert records[0]["cwd"] == new_cwd
        assert records[1]["cwd"] == new_cwd


class TestReturnValue:
    """import_sessions returns a summary of what happened."""

    def test_returns_count_of_copied_files(self, tmp_dirs):
        source, target = tmp_dirs
        for name in ["aaa.jsonl", "bbb.jsonl"]:
            write_session(
                source / name,
                [make_jsonl_line("user", r"C:\Users\arika\Repo-for-Claude-android")],
            )

        result = import_sessions(str(source), str(target))

        assert result["copied"] == 2

    def test_returns_list_of_skipped_files(self, tmp_dirs):
        source, target = tmp_dirs
        write_session(
            source / "existing.jsonl",
            [make_jsonl_line("user", r"C:\Users\arika\Repo-for-Claude-android")],
        )
        write_session(target / "existing.jsonl", [make_jsonl_line("user", "whatever")])

        result = import_sessions(str(source), str(target))

        assert "existing.jsonl" in result["skipped"]
        assert result["copied"] == 0


class TestDryRun:
    """Dry run mode previews without writing."""

    def test_dry_run_does_not_copy(self, tmp_dirs):
        source, target = tmp_dirs
        write_session(
            source / "aaa-111.jsonl",
            [make_jsonl_line("user", r"C:\Users\arika\Repo-for-Claude-android")],
        )

        result = import_sessions(str(source), str(target), dry_run=True)

        assert not (target / "aaa-111.jsonl").exists()
        assert result["would_copy"] == 1

    def test_dry_run_reports_what_would_be_skipped(self, tmp_dirs):
        source, target = tmp_dirs
        write_session(
            source / "aaa-111.jsonl",
            [make_jsonl_line("user", r"C:\Users\arika\Repo-for-Claude-android")],
        )
        write_session(target / "aaa-111.jsonl", [make_jsonl_line("user", "whatever")])

        result = import_sessions(str(source), str(target), dry_run=True)

        assert "aaa-111.jsonl" in result["would_skip"]
        assert result["would_copy"] == 0
