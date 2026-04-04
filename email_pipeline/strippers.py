"""
strippers.py
------------
Quote-stripping functions for each strip_method.
Each function takes the raw email record dict and returns body_clean (str).

Dispatcher:
    get_body_clean(record, method) -> str

Strip methods:
    Gmail         — strip div/blockquote with class containing 'gmail_quote'
                    (also handles 'x_gmail_quote' from OWA-forwarded Gmail)
    Outlook       — cut at From:/Sent: boundary in plain text
    Forward       — cut at dash-line header, "Begin forwarded message:", or
                    Outlook From:/Sent: block
    GT_Prefix     — remove >-prefixed quoted lines and On...wrote: attribution
    Outlook_Plain — cut at -----Original Message-----, fallback to From:/Sent:
    OnWrote       — cut at "On [date], [name] wrote:" attribution line
    iOS           — cut at Apple Mail "On [date], at [time], ... wrote:",
                    Samsung/Android "-------- Original message --------",
                    Mobile Outlook "From: "Name" <email> / Subject:" block,
                    plus forward/Outlook boundary fallbacks
    Original      — passthrough (no quotes present)
    Inline        — passthrough (inline replies; stripping would destroy context)
    Clean_Reply   — passthrough (sender already deleted quoted text)

Post-processing (applied after all quote strippers):
    _strip_attorney_sig — removes Gravel & Shea / Primmer sig blocks and
                          confidentiality disclaimers from any sender domain.
"""

import re
from bs4 import BeautifulSoup, NavigableString


# ---------------------------------------------------------------------------
# Shared HTML-to-text helper
# ---------------------------------------------------------------------------

def html_to_text(soup) -> str:
    """Convert a BeautifulSoup parse tree to clean plain text.

    - <br> tags become newlines
    - Block elements are separated by newlines via get_text(separator='\\n')
    - Consecutive blank lines collapsed to one
    """
    for br in soup.find_all("br"):
        br.replace_with("\n")
    text = soup.get_text(separator="\n")
    lines = [line.rstrip() for line in text.split("\n")]
    cleaned = []
    prev_blank = False
    for line in lines:
        is_blank = not line.strip()
        if is_blank:
            if not prev_blank:
                cleaned.append("")
            prev_blank = True
        else:
            cleaned.append(line)
            prev_blank = False
    return "\n".join(cleaned).strip()


# ---------------------------------------------------------------------------
# 1. Gmail stripper
#    Handles: class="gmail_quote"  (standard Gmail)
#             class="x_gmail_quote ..." (OWA re-encoding of Gmail quote)
#             <blockquote class="gmail_quote"> (Gmail quote in blockquote)
# ---------------------------------------------------------------------------

def _has_gmail_quote_class(tag) -> bool:
    return bool(tag.name and any("gmail_quote" in c for c in tag.get("class", [])))


def _is_outermost_gmail_quote(tag) -> bool:
    """True if no ancestor also carries a gmail_quote class."""
    for parent in tag.parents:
        if parent.name and any("gmail_quote" in c for c in parent.get("class", [])):
            return False
    return True


def strip_gmail(e: dict) -> str:
    html = e.get("Body.HTML", "") or ""
    if not html:
        return e.get("Body.Text", "") or ""

    soup = BeautifulSoup(html, "html.parser")

    all_gq = soup.find_all(_has_gmail_quote_class)

    if not all_gq:
        # gmail_quote was in a raw string attribute — fall back to full text
        return html_to_text(soup)

    # Outermost quote block = the cut point
    outermost = next((t for t in all_gq if _is_outermost_gmail_quote(t)), all_gq[0])

    # Remove all siblings after outermost (they are trailing boilerplate or
    # additional forwarded blocks)
    for sib in list(outermost.next_siblings):
        sib.extract()

    # Remove immediately-preceding whitespace text nodes and <br> tags
    prev = outermost.previous_sibling
    while prev is not None:
        if isinstance(prev, NavigableString) and not str(prev).strip():
            nxt = prev.previous_sibling
            prev.extract()
            prev = nxt
        elif getattr(prev, "name", None) == "br":
            nxt = prev.previous_sibling
            prev.extract()
            prev = nxt
        else:
            break

    # Remove the quote block itself
    outermost.extract()

    return html_to_text(soup)


# ---------------------------------------------------------------------------
# 2. Outlook stripper
#    Handles: border-top div, blockquote with border-left, From:/Sent: block
#    Strategy: HTML → plain text, then cut at first From:/Sent: boundary.
#    This avoids the nested div complexity of Outlook's WordSection1 wrapper.
# ---------------------------------------------------------------------------

# Matches the Outlook quote header block:
#   From: [Name] <email>
#   Sent: [date and time]
# A bare \n precedes From: so it must be on its own line.
_OUTLOOK_BOUNDARY = re.compile(
    r"\nFrom:[ \t]+\S[^\n]*\n(?:Sent|Date):[ \t]",
    re.IGNORECASE,
)


def strip_outlook(e: dict) -> str:
    html = e.get("Body.HTML", "") or ""
    if not html:
        # Fall back to Body.Text with same cut logic
        return _cut_at_outlook_boundary(e.get("Body.Text", "") or "")

    soup = BeautifulSoup(html, "html.parser")
    text = html_to_text(soup)
    return _cut_at_outlook_boundary(text)


def _cut_at_outlook_boundary(text: str) -> str:
    m = _OUTLOOK_BOUNDARY.search(text)
    if m:
        return text[: m.start()].strip()
    return text.strip()


# ---------------------------------------------------------------------------
# 3. Forward stripper
#    Handles: Gmail/GQ dash-line headers, Apple "Begin forwarded message:",
#             and Outlook From:/Sent: block as a fallback.
#    Strategy: HTML → plain text, then cut at the first forward boundary.
#    Note: Jeanne's anomalous style (her text embedded inside the forwarded
#          block rather than before it) cannot be safely cut and passes through.
# ---------------------------------------------------------------------------

_FWD_DASHES = re.compile(
    r"\n[ \t]*-{4,}[ \t]*(?:Forwarded\s+[Mm]essages?|Original\s+[Mm]essages?)[ \t]*-{4,}",
    re.IGNORECASE,
)

_FWD_BEGIN = re.compile(
    r"\n[Bb]egin\s+[Ff]orwarded\s+[Mm]essage\s*:",
    re.IGNORECASE,
)


def _cut_at_forward_boundary(text: str) -> str:
    """Cut text at the first recognised forward/original-message boundary.

    Priority:
      1. Dash-line header  (---------- Forwarded message ----------)
      2. 'Begin forwarded message:'  (iOS / Apple Mail)
      3. Outlook From:/Sent: block   (forwarded without a dash line)
    """
    # Prepend \\n so patterns anchored to \\n can match at position 0
    t = "\n" + text
    for pat in (_FWD_DASHES, _FWD_BEGIN, _OUTLOOK_BOUNDARY):
        m = pat.search(t)
        if m:
            pos = max(0, m.start() - 1)  # -1 compensates for the prepended \\n
            return text[:pos].strip()
    return text.strip()


def strip_forward(e: dict) -> str:
    html = e.get("Body.HTML", "") or ""
    if html:
        soup = BeautifulSoup(html, "html.parser")
        text = html_to_text(soup)
    else:
        text = e.get("Body.Text", "") or ""
    return _cut_at_forward_boundary(text)


# ---------------------------------------------------------------------------
# Attorney signature / boilerplate stripper
#
# Applied as a post-processing step after every quote stripper.
# Two-pass approach:
#   1. FIRM NAME trigger — finds the firm name line, walks backward past the
#      name/title lines until hitting the blank line that separates the
#      message body from the signature block, and cuts there.
#   2. DISCLAIMER catch-all — cuts at the confidentiality notice when no
#      firm name trigger matched (e.g. for other/unknown firms).
#
# Trigger order matters: first match wins.
# ---------------------------------------------------------------------------

# (trigger_regex, sender_domain_regex_or_None, max_sig_lines_to_walk_back)
_SIG_TRIGGERS = [
    # Firm-specific: walk back past name/title to content/sig blank-line boundary
    (re.compile(r"\nGravel & Shea",   re.IGNORECASE), re.compile(r"gravelshea\.com",  re.IGNORECASE), 5),
    (re.compile(r"\nPRIMMER PIPER",   re.IGNORECASE), re.compile(r"primmer\.com",      re.IGNORECASE), 5),
    (re.compile(r"\nPrimmer Piper",   re.IGNORECASE), re.compile(r"primmer\.com",      re.IGNORECASE), 5),
    # Mobile app sig line — no walk-back, cut here and discard everything after
    (re.compile(r"\nGet Outlook for iOS", re.IGNORECASE), None, 0),
    # Catch-all confidentiality disclaimers — cut at the notice, no walk-back
    (re.compile(r"\nThe information contained in this transmission", re.IGNORECASE), None, 0),
    (re.compile(r"\nTHIS E-MAIL MESSAGE, INCLUDING ANY ATTACHMENTS", re.IGNORECASE), None, 0),
]


def _walk_back_sig(lines: list, max_lines: int) -> list:
    """Remove trailing signature name/title lines from a split-line list.

    Removes non-blank lines (up to max_lines) walking backward until a blank
    line is found — that blank line is the content/signature paragraph break.
    The blank line itself is left in place (it becomes the new trailing blank,
    which strip() will clean up afterward).
    """
    # Drop trailing blank lines first so we start on actual content
    while lines and not lines[-1].strip():
        lines.pop()
    removed = 0
    while lines and removed < max_lines:
        if not lines[-1].strip():
            if removed > 0:
                break   # blank line after removing sig lines = boundary found
            # blank line within sig block (e.g. between title and firm name) —
            # remove it and keep walking
        lines.pop()
        removed += 1
    return lines


def _strip_attorney_sig(text: str, sender: str) -> str:
    """Remove attorney signature block and confidentiality disclaimer.

    Works on the plain-text body_clean produced by the quote strippers.
    Normalises line endings first so all patterns use \\n.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    for trigger_re, domain_re, walk_back in _SIG_TRIGGERS:
        # Skip firm-specific triggers when sender domain doesn't match
        if domain_re and not domain_re.search(sender):
            continue
        m = trigger_re.search(text)
        if not m:
            continue
        # Cut at trigger position (m.start() = the \n before the trigger line)
        before = text[: m.start()]
        if walk_back > 0:
            lines = _walk_back_sig(before.split("\n"), walk_back)
            return "\n".join(lines).strip()
        else:
            return before.strip()

    return text.strip()


# ---------------------------------------------------------------------------
# 4. GT_Prefix stripper
#    Handles: >-prefixed quoted lines (RFC 2822 / plain-text quoting).
#
#    Two sender patterns occur:
#      Standard  — sender text first, then > block (Arik, Molly)
#      Anomalous — > block first, sender text at the END (Jeanne's style)
#
#    Strategy: remove all > lines and "On [date] wrote:" attribution lines.
#    Blank gaps left behind are collapsed. The remaining text is sender content
#    in either case — pre-block for standard, post-block for Jeanne.
#
#    Only 1 of 42 GT_Prefix records has HTML; the rest operate on Body.Text.
# ---------------------------------------------------------------------------

_ON_WROTE_RE = re.compile(r"^On .{5,}wrote:\s*$", re.IGNORECASE)


def _remove_gt_quoted(text: str) -> str:
    """Remove >-prefix quoted lines and On ... wrote: attribution lines."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    keep = []
    for line in text.splitlines():
        if line.startswith(">") or _ON_WROTE_RE.match(line):
            continue
        keep.append(line)
    # Collapse consecutive blanks left by the removed > block
    cleaned = []
    prev_blank = False
    for line in keep:
        is_blank = not line.strip()
        if is_blank:
            if not prev_blank:
                cleaned.append("")
            prev_blank = True
        else:
            cleaned.append(line)
            prev_blank = False
    return "\n".join(cleaned).strip()


def strip_gt_prefix(e: dict) -> str:
    html = e.get("Body.HTML", "") or ""
    if html:
        soup = BeautifulSoup(html, "html.parser")
        text = html_to_text(soup)
    else:
        text = e.get("Body.Text", "") or ""
    return _remove_gt_quoted(text)


# ---------------------------------------------------------------------------
# 5. Outlook_Plain stripper
#    Handles: -----Original Message----- plain-text reply chains.
#    Primary cut point: -----Original Message----- marker.
#    Fallback: Outlook From:/Sent: boundary (for records without the marker).
#    Works on HTML (converted to text) or raw Body.Text.
# ---------------------------------------------------------------------------

_ORIG_MSG_BOUNDARY = re.compile(
    r"\n-----Original Message-----",
    re.IGNORECASE,
)


def strip_outlook_plain(e: dict) -> str:
    html = e.get("Body.HTML", "") or ""
    if html:
        soup = BeautifulSoup(html, "html.parser")
        text = html_to_text(soup)
    else:
        text = e.get("Body.Text", "") or ""
    # Prepend \n so the boundary pattern can match at position 0
    t = "\n" + text
    m = _ORIG_MSG_BOUNDARY.search(t)
    if m:
        pos = max(0, m.start() - 1)
        return text[:pos].strip()
    return _cut_at_outlook_boundary(text)


# ---------------------------------------------------------------------------
# 6. iOS stripper
#    Handles three mobile-client reply formats:
#      a) Apple Mail iOS — "On Sep 11, 2024, at 6:47PM, Name <email> wrote:"
#      b) Samsung/Android — "-------- Original message --------"
#         (via _cut_at_forward_boundary → _FWD_DASHES)
#      c) Mobile Outlook — "From: "Name" <email>\nSubject:" header block
#         (Outlook mobile omits the Sent: line; standard _OUTLOOK_BOUNDARY
#          requires From:\nSent: or From:\nDate: so can't match this layout)
# ---------------------------------------------------------------------------

# Apple Mail iOS attribution line: "On Sep 11, 2024, at 6:47PM, ..."
_IOS_ON_AT_WROTE = re.compile(
    r"\nOn [A-Za-z]+ \d{1,2}, \d{4}, at \d{1,2}:\d{2}(?:\s*[AP]M)?,",
    re.IGNORECASE,
)

# Mobile Outlook header: From: "Name" <email> / Subject: (no Sent: line)
_MOBILE_OUTLOOK_HDR = re.compile(
    r"\nFrom:[ \t]+\"[^\"]{1,80}\"[ \t]+<[^>]{1,80}>\s*\n(?:Subject|Date|To):[ \t]",
    re.IGNORECASE,
)


def strip_ios(e: dict) -> str:
    html = e.get("Body.HTML", "") or ""
    plain = e.get("Body.Text", "") or ""
    if html:
        soup = BeautifulSoup(html, "html.parser")
        text = html_to_text(soup)
    else:
        text = plain

    # Try iOS-specific patterns against the HTML-derived text first, then
    # Body.Text as fallback.  HTML table rendering can fragment the
    # "From: "Name" <email>" line across lines, defeating _MOBILE_OUTLOOK_HDR;
    # Body.Text preserves the header on one line where the pattern can match.
    for candidate in ([text, plain] if (html and plain) else [text]):
        t = "\n" + candidate
        for pat in (_IOS_ON_AT_WROTE, _MOBILE_OUTLOOK_HDR):
            m = pat.search(t)
            if m:
                pos = max(0, m.start() - 1)  # -1 compensates for prepended \n
                return candidate[:pos].strip()

    # Fallback: handles Samsung "-------- Original message --------",
    # "Begin forwarded message:", and standard Outlook From:/Sent: blocks.
    return _cut_at_forward_boundary(text)


# ---------------------------------------------------------------------------
# 7. OnWrote stripper
#    Handles: "On [date], [name] wrote:" attribution line as the cut point.
#    Sender text comes before the On...wrote: line; quoted text comes after.
#    Strategy: HTML -> plain text, cut at first On...wrote: line.
#    Note: records where On...wrote: is embedded mid-line (e.g. in an inline
#    quote) are not matched and pass through intact.
# ---------------------------------------------------------------------------

_ON_WROTE_BOUNDARY = re.compile(
    r"\nOn .{5,}wrote:",
    re.IGNORECASE,
)


def strip_onwrote(e: dict) -> str:
    html = e.get("Body.HTML", "") or ""
    if html:
        soup = BeautifulSoup(html, "html.parser")
        text = html_to_text(soup)
    else:
        text = e.get("Body.Text", "") or ""
    # Prepend \n so the pattern can match at position 0
    t = "\n" + text
    m = _ON_WROTE_BOUNDARY.search(t)
    if m:
        pos = max(0, m.start() - 1)
        return text[:pos].strip()
    return text.strip()


# ---------------------------------------------------------------------------
# Passthrough — no stripping needed or not yet implemented
# ---------------------------------------------------------------------------

def strip_passthrough(e: dict) -> str:
    """Return Body.Text unchanged."""
    return e.get("Body.Text", "") or ""


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_STRIPPERS = {
    "Gmail":         strip_gmail,
    "Outlook":       strip_outlook,
    # No-op passes
    "Original":      strip_passthrough,
    "Inline":        strip_passthrough,
    "Clean_Reply":   strip_passthrough,
    "Forward":       strip_forward,
    "GT_Prefix":     strip_gt_prefix,
    "Outlook_Plain": strip_outlook_plain,
    "OnWrote":       strip_onwrote,
    "iOS":           strip_ios,
}


def get_body_clean(e: dict, method: str) -> str:
    fn = _STRIPPERS.get(method, strip_passthrough)
    text = fn(e)
    sender = e.get("Address.Sender", "") or ""
    return _strip_attorney_sig(text, sender)
