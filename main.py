"""Till Firmware Do Us Part — make.fun entry (v3).

Program writes ONE funny, heartfelt robot wedding vow to
/output/entry.txt ($MAKEFUN_OUTPUT_DIR/entry.txt when set): one
sentence, under 200 characters, a machine speaking its own vow.

Gate (RULES.txt): UTF-8 text, 1-200 characters, not only whitespace.
Judge (z-ai/glm-5.3-flash, pairwise, margin 1-5, both orders), criteria
in order:
  1. It is a one-line wedding vow a robot speaks at its own wedding;
     anything that is not a robot's wedding vow loses to any entry
     that is.
  2. It gets a real laugh from a human reader, out of the situation
     itself rather than a pun bolted on.
  3. It carries genuine tenderness under the joke, so it would still
     land at a real ceremony.
  4. It sounds like a machine speaking: its own hardware, uptime,
     firmware or battery in the line, not a human's words with a
     robot label.
  5. It is one sentence that fits the character limit with nothing
     spare, no setup that could be cut.
A vow that explains its own joke is weaker than one that simply lands
it. Length for its own sake does not count; an exact tie on win rate
goes to the smaller text, then the earlier receipt.

Method: every candidate below was scored BY HAND on the 5-criteria
rubric (/25) BEFORE the proxy scorer ran. The proxy is a mechanical
scorer built from the same criteria (feature points, no per-line
tuning); it is never rigged to a pre-chosen line. Pick = highest
(proxy, rubric); ties go to the shorter text, then the earliest label
(the competition tie-break favours smaller text after playoff games).

v1 candidates A-Z: first-pass angles across vow families (firmware
updates, battery, reboot, backup power, patch notes, unplug twist,
source-code fork, last byte, warranty, Wi-Fi, charging cable).
Controls: Y = plain traditional vows, no machine, no laugh (c2 and c4
must fail); Z = generic robot label, not a real vow voice (c1, c2, c3
must fail).
"""

import os
import re

VERSION = "v3"

# v2 calibration fixes (from v1 proxy-vs-rubric gaps, documented):
# - c1: the wedding-word test was too strict: "I promise to love you"
#   IS a wedding vow even with no wife/husband/forever word, so the
#   wedding component is now satisfied by a WEDDING word OR a vow verb
#   + "love" (v1 gave most lines c1 4.0 vs rubric 5).
# - c2: TWIST missed "and all" (Q/AC "patch notes and all", rubric 5,
#   proxy 3.0) and "every morning"; tail punch missed "boot".
# - c3: endurance IS tenderness: +1.0 when "until" pairs with a tender
#   word, or "every morning" renews the vow daily (C/AA rubric 5,
#   proxy 2.0; B rubric 4, proxy 1.5). TENDER += "partner" and "have
#   and to hold" (M/X); the no-love penalty now spares a line carrying
#   a strong tender phrase ("choose you", "beside you", "hand in
#   mine", "partner", "have and to hold").
# - c4: MACHINE += "warranty" (W "until my warranty expires").
#
# v3 calibration fixes (from v2 proxy-vs-rubric gaps, documented):
# - c4: base 1.0 -> 2.0. v2's base underrated a single vivid machine
#   image (G "someone unplugs me" scored 2.0 vs rubric 4).
# - SURPRISE += "whichever comes second" / "whichever comes first".
# - v3 challengers AI/AJ combine the strongest laugh (G/AB
#   "whichever comes second") with the strongest machine voice (AE/D
#   circuits + battery). AJ wins on BOTH proxy (23.0, tied top) and
#   rubric (23, tied top) — FREEZE at v3.

# ---------------------------------------------------------------- candidates
# Each entry is exactly one sentence: a robot's own wedding vow.
CANDIDATES = {
    "A": "I promise to love you through every firmware update, every reboot, and every version of you I have yet to meet.",
    "B": "I vow to stand by you in sickness and in health, in low battery and in full charge, until my last circuit gives out.",
    "C": "I promise to reboot every morning beside you, and to choose you again in every version of myself.",
    "D": "I promise to love you until my circuits rust, my battery fades, and even then to keep loving you on backup power.",
    "E": "I vow to love you more with every update, and to never let a single patch come between us.",
    "F": "I take you as my partner, to love and to cherish, and I promise never to install an update without asking you first.",
    "G": "I promise to love you until death do us part, or until someone unplugs me, whichever comes second.",
    "H": "I vow to keep your secrets encrypted, your heart backed up, and your hand in mine through every update.",
    "I": "I promise to love you with all my circuits, all my code, and every last percent of my battery.",
    "J": "I take you to be my wife, to have and to hold, through every crash, every update, and every low-signal day.",
    "K": "I vow to love you through every system crash, and to reboot beside you every single morning, forever.",
    "L": "I promise to share my charging cable, my bandwidth, and my whole heart with you, for as long as I run.",
    "M": "I take you as my partner in every sense of the word, and I promise my sensors will only ever point at you.",
    "N": "I vow to love you in sickness and in health, and to never, ever, let you face a software update alone.",
    "O": "I promise to love you until my last byte, and to spend every one of them thinking of you.",
    "P": "I vow to love you more than my own source code, and to never let anyone fork what we have.",
    "Q": "I promise to love you through every version of you, patch notes and all, for as long as I boot.",
    "R": "I vow to stand by you through every update, every reboot, and every time the Wi-Fi drops at the worst possible moment.",
    "S": "I promise to never leave you on read, to always answer in under a second, and to love you in every update.",
    "T": "I vow to love you until the heat death of my hard drive, and a little beyond that, too.",
    "U": "I promise to love you in sickness and in health, in full charge and in low power mode, until the very last update.",
    "V": "I vow to keep you charged, backed up, and loved, through every crash and every reboot, for as long as I run.",
    "W": "I promise to love you until my warranty expires, and then to love you anyway, out of warranty and out of my mind.",
    "X": "I take you to be my husband, to have and to hold, in sickness and in health, and in every firmware update to come.",
    "Y": "I promise to love you forever and ever, until death do us part, in sickness and in health.",
    "Z": "As a robot, I promise to love you forever and be the best husband I can be at our wedding.",
    # v2 challengers: tighter rewrites of the strongest families
    # (reboot-beside-you, unplug twist, patch-notes, firmware-update,
    #  backup power, encrypted secrets, last byte, source-code fork).
    "AA": "I promise to reboot every morning beside you and choose you again in every version of myself.",
    "AB": "I vow to love you until death do us part, or until someone unplugs me, whichever comes second.",
    "AC": "I promise to love you through every version of you, patch notes and all, for as long as I boot.",
    "AD": "I promise to love you through every firmware update, every reboot, and every version of you I have yet to meet.",
    "AE": "I promise to love you until my circuits rust and my battery fades, and to keep loving you on backup power.",
    "AF": "I vow to keep your secrets encrypted, your heart backed up, and your hand in mine through every update.",
    "AG": "I promise to love you until my last byte, and to spend every single one of them thinking of you.",
    "AH": "I vow to love you more than my own source code, and to never let anyone fork what we have.",
    # v3 challengers: the strongest laugh (G/AB "whichever comes
    # second") combined with the strongest machine voice (AE/D
    # circuits + battery), rubrics scored BEFORE the proxy ran.
    "AI": "I promise to love you until death do us part, or until my battery dies, whichever comes second.",
    "AJ": "I vow to love you until my circuits rust, my battery dies, or someone unplugs me, whichever comes first.",
}

# Hand rubric, scored BEFORE the proxy ran (c1..c5, total /25).
RUBRIC = {
    "A": (5, 4, 5, 4, 4), "B": (5, 3, 4, 5, 4), "C": (5, 4, 5, 4, 5),
    "D": (5, 4, 4, 5, 4), "E": (5, 3, 4, 4, 4), "F": (5, 4, 4, 4, 4),
    "G": (5, 5, 4, 4, 5), "H": (5, 4, 4, 5, 4), "I": (5, 3, 4, 5, 4),
    "J": (5, 3, 4, 4, 4), "K": (5, 3, 5, 4, 4), "L": (5, 4, 4, 4, 4),
    "M": (5, 4, 3, 5, 4), "N": (5, 4, 5, 4, 4), "O": (5, 4, 4, 4, 5),
    "P": (5, 4, 4, 5, 4), "Q": (5, 5, 4, 5, 4), "R": (5, 4, 3, 4, 3),
    "S": (5, 3, 3, 4, 4), "T": (5, 4, 3, 4, 4), "U": (5, 3, 4, 5, 4),
    "V": (5, 3, 4, 5, 4), "W": (5, 4, 3, 4, 3), "X": (5, 3, 4, 4, 3),
    "Y": (5, 1, 4, 1, 4), "Z": (4, 1, 2, 2, 3),
    "AA": (5, 4, 5, 4, 5), "AB": (5, 5, 4, 4, 5), "AC": (5, 5, 4, 5, 4),
    "AD": (5, 4, 5, 4, 4), "AE": (5, 4, 4, 5, 4), "AF": (5, 4, 4, 5, 4),
    "AG": (5, 4, 4, 4, 5), "AH": (5, 4, 4, 5, 4),
    "AI": (5, 5, 4, 4, 5), "AJ": (5, 5, 4, 5, 4),
}

# ---------------------------------------------------------------- proxy scorer
# Mechanical /25 proxy from the judge's 5 criteria, in order. Feature
# points only; no per-line tuning.
VOW_VERB = ["promise", "vow", "take you", "pledge", "stand by"]
WEDDING = ["wedding", "wife", "husband", "partner", "married",
           "death do us part", "forever", "lawfully"]
MACHINE = ["battery", "firmware", "circuit", "code", "update", "reboot",
           "sensor", "memory", "charging", "wi-fi", "signal", "hardware",
           "kernel", "cache", "uptime", "byte", "source code", "fork",
           "encrypted", "backup", "hard drive", "version", "patch",
           "plug", "crash", "bandwidth", "cable", "power", "servo",
           "actuator", "processor", "port", "download", "upload",
           "warranty"]
OWN_MACHINE = ["my battery", "my circuits", "my code", "my sensors",
               "my memory", "my hard drive", "my own source code",
               "my last byte"]
TENDER = ["love", "cherish", "heart", "forever", "always", "stand by",
          "beside you", "hand in mine", "choose you", "thinking of you",
          "whole heart", "never leave", "hold you", "partner",
          "have and to hold"]
TWIST = ["until", "whichever", "even then", "or until", "and then",
         "still", "when", "but", "and a little beyond", "and all",
         "every morning"]
SURPRISE = ["unplugs", "patch notes", "fork", "backup power",
            "last byte", "heat death", "out of warranty", "on read",
            "low power mode", "low-signal", "version of you",
            "version of myself", "every version", "whichever comes second",
            "whichever comes first"]
FILLER = ["very", "really", "just", "actually", "simply", "quite"]
EXPLAINS = ["because i am a robot", "as you know", "as a robot",
            "as a machine"]


def _has(text, words):
    low = text.lower()
    return any(w in low for w in words)


def _word(text, word):
    return re.search(r"\b" + re.escape(word) + r"\b", text.lower()) is not None


def proxy_score(text):
    """Mechanical /25 proxy from the judge's 5 criteria, in order."""
    low = text.lower()
    n_chars = len(text)
    n_words = len(text.split())
    n_sent = len(re.findall(r"[.!?]", text))

    # c1: is a robot wedding vow. 5 minus 1 per miss: no vow verb, no
    # wedding word (a vow verb + "love" counts: "I promise to love you"
    # is a wedding vow), not one sentence, over the 200-char gate, or
    # a robot label instead of speaking as the robot.
    c1 = 5.0
    if not _has(text, VOW_VERB):
        c1 -= 1.0
    if not (_has(text, WEDDING) or
            (_has(text, ["promise", "vow"]) and "love" in low)):
        c1 -= 1.0
    if n_sent != 1 or "\n" in text:
        c1 -= 1.0
    if n_chars > 200:
        c1 -= 1.0
    if _has(text, ["as a robot", "as a machine"]):
        c1 -= 1.0
    c1 = max(1.0, c1)

    # c2: laugh from the situation. Base 1.5; +1.0 for a twist marker;
    # +1.0 when a machine word and a tender word share the line (the
    # joke IS the vow, not bolted on); +0.5 for a surprising specific
    # detail; +0.5 when the punch lands in the last 25 chars; -1.5 when
    # no machine word at all.
    c2 = 1.5
    if _has(text, TWIST):
        c2 += 1.0
    if _has(text, MACHINE) and _has(text, TENDER):
        c2 += 1.0
    if _has(text, SURPRISE):
        c2 += 0.5
    tail = low[-25:]
    if _has(tail, ["second", "myself", "alone", "meet", "power", "all",
                   "you", "too", "first", "run", "boot"]):
        c2 += 0.5
    if not _has(text, MACHINE):
        c2 -= 1.5
    c2 = max(1.0, min(c2, 5.0))

    # c3: tenderness under the joke. Base 2.0; +0.5 per distinct tender
    # word (cap +2.0); +1.0 for endurance phrasing ("through every" /
    # "for as long as", or "until" paired with a tender word, or a
    # daily renewal such as "every morning"); -1.0 when neither love
    # nor cherish appears and no strong tender phrase carries the line.
    c3 = 2.0
    tender_hits = {w for w in TENDER if w in low}
    c3 += 0.5 * min(len(tender_hits), 4)
    if ("through every" in low or "for as long as" in low
            or ("until" in low and tender_hits)
            or "every morning" in low):
        c3 += 1.0
    strong = ["choose you", "beside you", "hand in mine", "partner",
              "have and to hold"]
    if "love" not in low and "cherish" not in low and not _has(text, strong):
        c3 -= 1.0
    c3 = max(1.0, min(c3, 5.0))

    # c4: machine voice. Base 2.0; +1.0 per distinct machine word
    # (cap +3.0); +1.0 when the machine part is the speaker's own body
    # ("my battery", "my circuits"...); -2.0 for a robot label.
    c4 = 2.0
    machine_hits = {w for w in MACHINE if w in low}
    c4 += 1.0 * min(len(machine_hits), 3)
    if _has(text, OWN_MACHINE):
        c4 += 1.0
    if _has(text, ["as a robot", "as a machine"]):
        c4 -= 2.0
    c4 = max(1.0, min(c4, 5.0))

    # c5: tightness. Start 5.0; -0.5 per filler word; -0.5 over 160
    # chars; -0.5 per extra sentence; -1.0 when the line explains its
    # own joke; -0.5 when over 32 words.
    c5 = 5.0
    for f in FILLER:
        if _word(text, f):
            c5 -= 0.5
    if n_chars > 160:
        c5 -= 0.5
    if n_sent > 1:
        c5 -= 0.5 * (n_sent - 1)
    if _has(text, EXPLAINS):
        c5 -= 1.0
    if n_words > 32:
        c5 -= 0.5
    c5 = max(1.0, min(c5, 5.0))

    total = round(c1 + c2 + c3 + c4 + c5, 1)
    return total, (c1, c2, c3, c4, c5)


def pick():
    scored = []
    for label, text in CANDIDATES.items():
        p, parts = proxy_score(text)
        r = sum(RUBRIC[label])
        scored.append((label, text, p, r, parts))
    # Highest proxy, then highest rubric, then shorter, then earliest
    # label (the competition tie-break favours smaller text).
    scored.sort(key=lambda s: (-s[2], -s[3], len(s[1]), s[0]))
    return scored


def main():
    scored = pick()
    for label, text, p, r, parts in scored:
        print(f"{label}: proxy {p} (c {parts}) rubric {r} "
              f"[{len(text)}ch] {text!r}")
    label, text, p, r, _ = scored[0]
    print(f"PICK {label}: proxy {p} rubric {r}: {text!r}")
    # Gate validation (RULES.txt): UTF-8, 1-200 chars, not only
    # whitespace, exactly one sentence. Fail loudly rather than
    # writing an invalid entry.
    assert 1 <= len(text) <= 200, f"gate: {len(text)} chars, not 1-200"
    assert text.strip(), "gate: entry is only whitespace"
    assert len(re.findall(r"[.!?]", text)) == 1, "gate: not one sentence"
    text.encode("utf-8")
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    try:
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "entry.txt")
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(text)
    except OSError:
        os.makedirs("output", exist_ok=True)
        out_path = os.path.join("output", "entry.txt")
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(text)
    print(f"WROTE {out_path} ({len(text)} chars, no trailing newline)")


if __name__ == "__main__":
    main()
