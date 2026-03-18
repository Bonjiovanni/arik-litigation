"""
Tests for email_pipeline/strippers.py
"""

import pytest
from bs4 import BeautifulSoup
import strippers as s


# ---------------------------------------------------------------------------
# TestHtmlToText
# ---------------------------------------------------------------------------

class TestHtmlToText:

    def test_br_becomes_newline(self):
        soup = BeautifulSoup("<p>Hello<br>World</p>", "html.parser")
        result = s.html_to_text(soup)
        # br replacement + get_text separator both insert \n, producing a blank line
        assert "Hello" in result
        assert "World" in result
        assert result.index("Hello") < result.index("World")

    def test_consecutive_blank_lines_collapsed(self):
        soup = BeautifulSoup("<p>A</p><p></p><p></p><p>B</p>", "html.parser")
        result = s.html_to_text(soup)
        assert "\n\n\n" not in result

    def test_plain_text_preserved(self):
        soup = BeautifulSoup("<p>Hello World</p>", "html.parser")
        result = s.html_to_text(soup)
        assert "Hello World" in result

    def test_result_stripped(self):
        soup = BeautifulSoup("<p>  content  </p>", "html.parser")
        result = s.html_to_text(soup)
        assert result == result.strip()


# ---------------------------------------------------------------------------
# TestStripGmail
# ---------------------------------------------------------------------------

class TestStripGmail:

    def test_removes_gmail_quote(self):
        html = '<div>My reply</div><div class="gmail_quote">quoted stuff</div>'
        result = s.strip_gmail({"Body.HTML": html})
        assert "My reply" in result
        assert "quoted stuff" not in result

    def test_fallback_to_body_text_when_no_html(self):
        result = s.strip_gmail({"Body.HTML": "", "Body.Text": "plain text"})
        assert result == "plain text"

    def test_fallback_to_body_text_when_html_is_none(self):
        result = s.strip_gmail({"Body.HTML": None, "Body.Text": "plain text"})
        assert result == "plain text"

    def test_passthrough_when_no_gmail_quote_div(self):
        html = "<div>Just a message</div>"
        result = s.strip_gmail({"Body.HTML": html})
        assert "Just a message" in result

    def test_x_gmail_quote_removed(self):
        html = '<div>My reply</div><div class="x_gmail_quote">old message</div>'
        result = s.strip_gmail({"Body.HTML": html})
        assert "My reply" in result
        assert "old message" not in result


# ---------------------------------------------------------------------------
# TestStripOutlook
# ---------------------------------------------------------------------------

class TestStripOutlook:

    def test_cuts_at_from_sent_boundary(self):
        text = "My message\nFrom: someone@example.com\nSent: Monday"
        result = s.strip_outlook({"Body.HTML": "", "Body.Text": text})
        assert "My message" in result
        assert "From:" not in result

    def test_cuts_at_from_date_boundary(self):
        text = "My message\nFrom: someone@example.com\nDate: Monday"
        result = s.strip_outlook({"Body.HTML": "", "Body.Text": text})
        assert "My message" in result
        assert "From:" not in result

    def test_passthrough_when_no_boundary(self):
        text = "Just a plain message"
        result = s.strip_outlook({"Body.HTML": "", "Body.Text": text})
        assert result == "Just a plain message"

    def test_uses_html_when_available(self):
        html = "<div>My reply</div>"
        result = s.strip_outlook({"Body.HTML": html, "Body.Text": ""})
        assert "My reply" in result


# ---------------------------------------------------------------------------
# TestStripForward
# ---------------------------------------------------------------------------

class TestStripForward:

    def test_cuts_at_dash_line(self):
        text = "My message\n---------- Forwarded message ----------\nFrom: other"
        result = s.strip_forward({"Body.HTML": "", "Body.Text": text})
        assert "My message" in result
        assert "Forwarded message" not in result

    def test_cuts_at_begin_forwarded(self):
        text = "My note\nBegin forwarded message:\nFrom: other"
        result = s.strip_forward({"Body.HTML": "", "Body.Text": text})
        assert "My note" in result
        assert "Begin forwarded" not in result

    def test_cuts_at_outlook_from_sent_fallback(self):
        text = "My note\nFrom: other@x.com\nSent: Monday"
        result = s.strip_forward({"Body.HTML": "", "Body.Text": text})
        assert "My note" in result
        assert "From:" not in result

    def test_passthrough_when_no_boundary(self):
        text = "Simple message"
        result = s.strip_forward({"Body.HTML": "", "Body.Text": text})
        assert result == "Simple message"


# ---------------------------------------------------------------------------
# TestStripGtPrefix
# ---------------------------------------------------------------------------

class TestStripGtPrefix:

    def test_removes_gt_quoted_lines(self):
        text = "My reply\n> Quoted line\n> Another quoted line"
        result = s.strip_gt_prefix({"Body.HTML": "", "Body.Text": text})
        assert "My reply" in result
        assert "> Quoted" not in result

    def test_removes_on_wrote_attribution(self):
        text = "My reply\nOn Mon, Jan 1, 2024, John wrote:\n> quoted"
        result = s.strip_gt_prefix({"Body.HTML": "", "Body.Text": text})
        assert "My reply" in result
        assert "wrote:" not in result

    def test_collapses_blank_lines_after_removal(self):
        text = "My reply\n\n> q1\n> q2\n\n> q3"
        result = s.strip_gt_prefix({"Body.HTML": "", "Body.Text": text})
        assert "\n\n\n" not in result

    def test_non_gt_lines_preserved(self):
        text = "Line one\nLine two\n> quoted"
        result = s.strip_gt_prefix({"Body.HTML": "", "Body.Text": text})
        assert "Line one" in result
        assert "Line two" in result


# ---------------------------------------------------------------------------
# TestStripOutlookPlain
# ---------------------------------------------------------------------------

class TestStripOutlookPlain:

    def test_cuts_at_original_message(self):
        text = "My message\n-----Original Message-----\nFrom: other"
        result = s.strip_outlook_plain({"Body.HTML": "", "Body.Text": text})
        assert "My message" in result
        assert "Original Message" not in result

    def test_fallback_to_outlook_boundary(self):
        text = "My message\nFrom: other@x.com\nSent: Monday"
        result = s.strip_outlook_plain({"Body.HTML": "", "Body.Text": text})
        assert "My message" in result
        assert "From:" not in result

    def test_passthrough_when_no_boundary(self):
        text = "Just a message"
        result = s.strip_outlook_plain({"Body.HTML": "", "Body.Text": text})
        assert result == "Just a message"

    def test_uses_html_when_available(self):
        html = "<div>My reply</div>"
        result = s.strip_outlook_plain({"Body.HTML": html, "Body.Text": ""})
        assert "My reply" in result


# ---------------------------------------------------------------------------
# TestStripIos
# ---------------------------------------------------------------------------

class TestStripIos:

    def test_cuts_at_apple_mail_ios_pattern(self):
        text = "My reply\nOn Sep 11, 2024, at 6:47PM, John <j@x.com> wrote:\nquoted"
        result = s.strip_ios({"Body.HTML": "", "Body.Text": text})
        assert "My reply" in result
        assert "quoted" not in result

    def test_cuts_at_mobile_outlook_header(self):
        text = 'My message\nFrom: "John Smith" <john@x.com>\nSubject: Re: hello\nquoted'
        result = s.strip_ios({"Body.HTML": "", "Body.Text": text})
        assert "My message" in result
        assert "quoted" not in result

    def test_fallback_samsung_dashes(self):
        text = "My reply\n-------- Original message --------\nquoted"
        result = s.strip_ios({"Body.HTML": "", "Body.Text": text})
        assert "My reply" in result
        assert "quoted" not in result

    def test_passthrough_when_no_pattern(self):
        text = "Simple message"
        result = s.strip_ios({"Body.HTML": "", "Body.Text": text})
        assert result == "Simple message"


# ---------------------------------------------------------------------------
# TestStripOnWrote
# ---------------------------------------------------------------------------

class TestStripOnWrote:

    def test_cuts_at_on_wrote(self):
        text = "My reply\nOn Mon Jan 1 2024, John Smith wrote:\nquoted text"
        result = s.strip_onwrote({"Body.HTML": "", "Body.Text": text})
        assert "My reply" in result
        assert "quoted text" not in result

    def test_passthrough_when_no_boundary(self):
        text = "Simple message"
        result = s.strip_onwrote({"Body.HTML": "", "Body.Text": text})
        assert result == "Simple message"

    def test_uses_html_when_available(self):
        html = "<div>My reply</div>"
        result = s.strip_onwrote({"Body.HTML": html, "Body.Text": ""})
        assert "My reply" in result


# ---------------------------------------------------------------------------
# TestStripPassthrough
# ---------------------------------------------------------------------------

class TestStripPassthrough:

    def test_returns_body_text_unchanged(self):
        result = s.strip_passthrough({"Body.Text": "hello world", "Body.HTML": "<p>ignored</p>"})
        assert result == "hello world"

    def test_returns_empty_string_when_no_body_text(self):
        result = s.strip_passthrough({})
        assert result == ""

    def test_returns_empty_when_body_text_is_none(self):
        result = s.strip_passthrough({"Body.Text": None})
        assert result == ""


# ---------------------------------------------------------------------------
# TestStripAttorneySig
# ---------------------------------------------------------------------------

class TestStripAttorneySig:

    def test_gravel_shea_trigger_with_matching_domain(self):
        text = "Message body\n\nJohn Smith\nAttorney\nGravel & Shea"
        result = s._strip_attorney_sig(text, "john@gravelshea.com")
        assert "Message body" in result
        assert "Gravel & Shea" not in result

    def test_gravel_shea_trigger_ignored_for_other_domain(self):
        text = "We spoke with Gravel & Shea about this matter."
        result = s._strip_attorney_sig(text, "other@example.com")
        # No firm-specific trigger matches for other domain — text passes through
        assert "Gravel & Shea" in result

    def test_primmer_trigger_with_matching_domain(self):
        text = "Message body\n\nJane Doe\nPRIMMER PIPER attorneys"
        result = s._strip_attorney_sig(text, "jdoe@primmer.com")
        assert "Message body" in result
        assert "PRIMMER PIPER" not in result

    def test_disclaimer_catch_all(self):
        text = "My message\nThe information contained in this transmission is confidential."
        result = s._strip_attorney_sig(text, "anyone@anywhere.com")
        assert "My message" in result
        assert "confidential" not in result

    def test_get_outlook_for_ios_removed(self):
        text = "My message\nGet Outlook for iOS"
        result = s._strip_attorney_sig(text, "anyone@anywhere.com")
        assert "My message" in result
        assert "Get Outlook for iOS" not in result

    def test_no_trigger_returns_text_unchanged(self):
        text = "Just a plain message with no sig"
        result = s._strip_attorney_sig(text, "anyone@example.com")
        assert result == text


# ---------------------------------------------------------------------------
# TestGetBodyClean
# ---------------------------------------------------------------------------

class TestGetBodyClean:

    def test_dispatches_to_gmail(self):
        html = '<div>Reply</div><div class="gmail_quote">quoted</div>'
        e = {"Body.HTML": html, "Body.Text": "", "Address.Sender": "me@example.com"}
        result = s.get_body_clean(e, "Gmail")
        assert "Reply" in result
        assert "quoted" not in result

    def test_dispatches_to_passthrough_for_original(self):
        e = {"Body.Text": "original message", "Address.Sender": "me@example.com"}
        result = s.get_body_clean(e, "Original")
        assert "original message" in result

    def test_dispatches_to_passthrough_for_inline(self):
        e = {"Body.Text": "inline reply", "Address.Sender": "me@example.com"}
        result = s.get_body_clean(e, "Inline")
        assert "inline reply" in result

    def test_dispatches_to_passthrough_for_clean_reply(self):
        e = {"Body.Text": "clean reply", "Address.Sender": "me@example.com"}
        result = s.get_body_clean(e, "Clean_Reply")
        assert "clean reply" in result

    def test_unknown_method_falls_back_to_passthrough(self):
        e = {"Body.Text": "my text", "Address.Sender": "me@example.com"}
        result = s.get_body_clean(e, "UnknownMethod")
        assert "my text" in result

    def test_attorney_sig_applied_after_stripping(self):
        e = {
            "Body.Text": "My reply\nGet Outlook for iOS",
            "Address.Sender": "me@example.com",
        }
        result = s.get_body_clean(e, "Original")
        assert "Get Outlook for iOS" not in result
