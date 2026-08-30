"""Comparison-only text canonicalization profiles (Issue #77).

These helpers produce temporary comparison copies. They must not mutate
authoritative runtime text, forensic records, or provider output.
"""

from __future__ import annotations

import unicodedata

# Presentation-verbatim profile: typographic apostrophe/single-quote → ASCII '
_PRESENTATION_APOSTROPHE_TRANSLATION = str.maketrans(
    {
        "\u2018": "'",  # left single quotation mark
        "\u2019": "'",  # right single quotation mark (U+2019 — #73 regression)
        "\u201a": "'",  # single low-9 quotation mark
        "\u201b": "'",  # single high-reversed-9 quotation mark
        "\u2032": "'",  # prime (occasionally used as apostrophe)
    }
)

# Presentation-verbatim profile: curly double quotes → ASCII "
_PRESENTATION_DOUBLE_QUOTE_TRANSLATION = str.maketrans(
    {
        "\u201c": '"',  # left double quotation mark
        "\u201d": '"',  # right double quotation mark
        "\u201e": '"',  # double low-9 quotation mark
        "\u201f": '"',  # double high-reversed-9 quotation mark
    }
)

# Bounded space variants → ordinary ASCII space (no run collapse).
_PRESENTATION_SPACE_TRANSLATION = str.maketrans(
    {
        "\u00a0": " ",  # no-break space
        "\u202f": " ",  # narrow no-break space
        "\u2007": " ",  # figure space
    }
)


def canonicalize_for_presentation_verbatim(value: str) -> str:
    """Return a comparison-only form for Narrator presentation-verbatim checks.

    Profile scope (Issue #77 consensus):
    - NFC Unicode normalization
    - typographic apostrophe/single-quote → ASCII apostrophe
    - curly double quotes → ASCII double quote
    - selected space variants → ASCII space

    Explicitly excluded: NFKC, dash/ellipsis equivalence, punctuation stripping,
    whitespace-run collapse, semantic/fuzzy matching.
  """
    if not isinstance(value, str):
        return ""
    normalized = unicodedata.normalize("NFC", value)
    normalized = normalized.translate(_PRESENTATION_APOSTROPHE_TRANSLATION)
    normalized = normalized.translate(_PRESENTATION_DOUBLE_QUOTE_TRANSLATION)
    normalized = normalized.translate(_PRESENTATION_SPACE_TRANSLATION)
    return normalized
