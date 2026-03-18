"""
Tests for email_pipeline/merge_and_classify.py
"""

import json
import pytest
from pathlib import Path
import merge_and_classify as mc


# ---------------------------------------------------------------------------
# TestNormalizeMessageId
# ---------------------------------------------------------------------------

class TestNormalizeMessageId:

    def test_strips_angle_brackets(self):
        assert mc.normalize_message_id("<abc123@mail.com>") == "abc123@mail.com"

    def test_strips_whitespace(self):
        assert mc.normalize_message_id("  abc123@mail.com  ") == "abc123@mail.com"

    def test_lowercases(self):
        assert mc.normalize_message_id("ABC123@MAIL.COM") == "abc123@mail.com"

    def test_combined(self):
        assert mc.normalize_message_id("  <ABC@X.COM>  ") == "abc@x.com"

    def test_empty_string(self):
        assert mc.normalize_message_id("") == ""

    def test_no_brackets(self):
        assert mc.normalize_message_id("plain@mail.com") == "plain@mail.com"


# ---------------------------------------------------------------------------
# TestScoreRecord
# ---------------------------------------------------------------------------

class TestScoreRecord:

    def test_eml_beats_gmail(self):
        eml = {"_input_source": "EML_FILE", "Body.Text": "x", "Session.RunDate": "2024-01-01"}
        gml = {"_input_source": "GMAIL_API", "Body.Text": "x", "Session.RunDate": "2024-01-01"}
        assert mc.score_record(eml) > mc.score_record(gml)

    def test_msg_beats_gmail(self):
        msg = {"_input_source": "MSG_FILE", "Body.Text": "x", "Session.RunDate": "2024-01-01"}
        gml = {"_input_source": "GMAIL_API", "Body.Text": "x", "Session.RunDate": "2024-01-01"}
        assert mc.score_record(msg) > mc.score_record(gml)

    def test_larger_body_wins_tiebreaker(self):
        big   = {"_input_source": "GMAIL_API", "Body.Text": "x" * 1000}
        small = {"_input_source": "GMAIL_API", "Body.Text": "x"}
        assert mc.score_record(big) > mc.score_record(small)

    def test_later_run_date_wins_tiebreaker(self):
        later   = {"_input_source": "GMAIL_API", "Body.Text": "x", "Session.RunDate": "2025-01-01"}
        earlier = {"_input_source": "GMAIL_API", "Body.Text": "x", "Session.RunDate": "2024-01-01"}
        assert mc.score_record(later) > mc.score_record(earlier)

    def test_returns_tuple(self):
        r = {"_input_source": "EML_FILE"}
        assert isinstance(mc.score_record(r), tuple)


# ---------------------------------------------------------------------------
# TestPickWinner
# ---------------------------------------------------------------------------

class TestPickWinner:

    def test_single_record_has_no_losers(self):
        record = {"_input_source": "EML_FILE"}
        winner, losers = mc.pick_winner([record])
        assert winner is record
        assert losers == []

    def test_eml_wins_over_gmail(self):
        eml = {"_input_source": "EML_FILE", "Body.Text": ""}
        gml = {"_input_source": "GMAIL_API", "Body.Text": ""}
        winner, losers = mc.pick_winner([gml, eml])
        assert winner is eml
        assert gml in losers

    def test_returns_all_losers(self):
        r1 = {"_input_source": "EML_FILE", "Body.Text": "xxx"}
        r2 = {"_input_source": "GMAIL_API", "Body.Text": "x"}
        r3 = {"_input_source": "GMAIL_API", "Body.Text": ""}
        winner, losers = mc.pick_winner([r1, r2, r3])
        assert winner is r1
        assert len(losers) == 2

    def test_winner_not_in_losers(self):
        r1 = {"_input_source": "EML_FILE"}
        r2 = {"_input_source": "GMAIL_API"}
        winner, losers = mc.pick_winner([r1, r2])
        assert winner not in losers


# ---------------------------------------------------------------------------
# TestGetStripMethod
# ---------------------------------------------------------------------------

class TestGetStripMethod:

    def _e(self, body="", html="", subject="", in_reply=""):
        return {
            "Body.SenderText":    body,
            "Body.HTML":          html,
            "Header.Subject":     subject,
            "Header.In-Reply-To": in_reply,
        }

    def test_inline_detected(self):
        assert mc.get_strip_method(self._e(body="this is an inline reply")) == "Inline"

    def test_forward_fw_detected(self):
        assert mc.get_strip_method(self._e(subject="Fw: hello")) == "Forward"

    def test_forward_fwd_detected(self):
        assert mc.get_strip_method(self._e(subject="Fwd: hello")) == "Forward"

    def test_gmail_detected(self):
        assert mc.get_strip_method(self._e(html='<div class="gmail_quote">x</div>')) == "Gmail"

    def test_outlook_detected(self):
        assert mc.get_strip_method(self._e(html='<div class="MsoNormal">x</div>')) == "Outlook"

    def test_gt_prefix_detected(self):
        assert mc.get_strip_method(self._e(body="> quoted line", subject="Re: x", in_reply="<x>")) == "GT_Prefix"

    def test_ios_detected(self):
        assert mc.get_strip_method(self._e(html='<div dir="auto">text</div>', subject="Re: x", in_reply="<abc@x.com>")) == "iOS"

    def test_outlook_plain_by_original_message_marker(self):
        body = "text\n-----Original Message-----\nFrom: other"
        assert mc.get_strip_method(self._e(body=body, subject="Re: x", in_reply="<x>")) == "Outlook_Plain"

    def test_outlook_plain_by_from_subject_header(self):
        body = "text\nFrom: other@x.com\nSubject: hello"
        assert mc.get_strip_method(self._e(body=body, subject="Re: x", in_reply="<x>")) == "Outlook_Plain"

    def test_on_wrote_detected(self):
        body = "On Monday January 1 2024, John Smith wrote: something"
        assert mc.get_strip_method(self._e(body=body, subject="Re: x", in_reply="<x>")) == "OnWrote"

    def test_original_when_no_in_reply_to(self):
        assert mc.get_strip_method(self._e()) == "Original"

    def test_clean_reply_as_fallback(self):
        assert mc.get_strip_method(self._e(subject="Re: x", in_reply="<abc@x.com>")) == "Clean_Reply"


# ---------------------------------------------------------------------------
# TestLoadExport
# ---------------------------------------------------------------------------

class TestLoadExport:

    def test_loads_valid_json(self, tmp_path):
        data = {"emails": [{"id": "1"}, {"id": "2"}]}
        p = tmp_path / "export.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        records = mc.load_export(p, "GMAIL_API")
        assert len(records) == 2
        assert all(r["_input_source"] == "GMAIL_API" for r in records)

    def test_source_label_set_on_all_records(self, tmp_path):
        data = {"emails": [{"id": "1"}, {"id": "2"}, {"id": "3"}]}
        p = tmp_path / "export.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        records = mc.load_export(p, "EML_FILE")
        assert all(r["_input_source"] == "EML_FILE" for r in records)

    def test_missing_emails_key_raises(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text(json.dumps({"data": []}), encoding="utf-8")
        with pytest.raises(ValueError):
            mc.load_export(p, "EML_FILE")

    def test_non_list_emails_raises(self, tmp_path):
        p = tmp_path / "bad2.json"
        p.write_text(json.dumps({"emails": "not a list"}), encoding="utf-8")
        with pytest.raises(ValueError):
            mc.load_export(p, "EML_FILE")


# ---------------------------------------------------------------------------
# TestDeduplication
# ---------------------------------------------------------------------------

class TestDeduplication:

    def test_normalize_strips_brackets_and_lowercases(self):
        assert mc.normalize_message_id("<Test@Mail.COM>") == "test@mail.com"

    def test_pick_winner_eml_over_gmail_same_sha(self):
        eml = {"_input_source": "EML_FILE", "Body.Text": "x"}
        gml = {"_input_source": "GMAIL_API", "Body.Text": "x"}
        winner, losers = mc.pick_winner([gml, eml])
        assert winner["_input_source"] == "EML_FILE"
        assert len(losers) == 1

    def test_no_key_record_is_kept_with_no_losers(self):
        r = {"Email.HashSHA256": "", "Header.Message-ID": ""}
        winner, losers = mc.pick_winner([r])
        assert winner is r
        assert losers == []

    def test_body_size_tiebreaker(self):
        big   = {"_input_source": "EML_FILE", "Body.Text": "a" * 500, "Body.HTML": ""}
        small = {"_input_source": "EML_FILE", "Body.Text": "a", "Body.HTML": ""}
        winner, _ = mc.pick_winner([small, big])
        assert winner is big

    def test_run_date_tiebreaker(self):
        newer = {"_input_source": "EML_FILE", "Body.Text": "x", "Session.RunDate": "2025-06-01"}
        older = {"_input_source": "EML_FILE", "Body.Text": "x", "Session.RunDate": "2024-01-01"}
        winner, _ = mc.pick_winner([older, newer])
        assert winner is newer


# ---------------------------------------------------------------------------
# TestZeroRecordsHalt
# ---------------------------------------------------------------------------

class TestZeroRecordsHalt:

    def test_main_halts_when_no_inputs_selected(self, monkeypatch):
        monkeypatch.setattr(mc, "load_config", lambda: {})
        monkeypatch.setattr(mc, "save_config", lambda cfg: None)
        monkeypatch.setattr(mc, "pick_input_file", lambda *a, **kw: None)
        # Should return early without raising or attempting file I/O
        mc.main()  # no exception = pass
