"""
LLM-based Tag Classifier using Anthropic Claude.

Selects probable book tags from a fixed, authorized vocabulary by prompting
the model with a few sampled passages plus metadata. Returns a scored list.

No API key is stored in code; pass it at runtime and keep it in memory only.
"""

from __future__ import annotations

import json
import os
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import logging
import textwrap

logger = logging.getLogger(__name__)


# Authorized tags (fixed vocabulary)
AUTHORIZED_TAGS: List[str] = [
    "biography",
    "classic",
    "coming-of-age",
    "contemporary-fiction",
    "crime",
    "erotic",
    "essay",
    "fantasy",
    "historical-fiction",
    "horror",
    "literary-fiction",
    "memoir",
    "mystery",
    "non-fiction",
    "philosophy",
    "romance",
    "science-fiction",
    "scientific",
    "short-stories",
    "suspense",
    "teen-young-adult",
    "thriller",
    "true-crime",
    "war",
    "western",
    "womens-fiction",
]


@dataclass
class LLMTagScore:
    tag: str
    score: float


class LLMTagClassifier:
    def __init__(
        self,
        api_key: Optional[str],
        *,
        model: str = "claude-3-haiku-20240307",
        authorized_tags: Optional[List[str]] = None,
        request_timeout: int = 60,
    ) -> None:
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self.authorized_tags = list(authorized_tags) if authorized_tags else list(AUTHORIZED_TAGS)
        self.request_timeout = request_timeout

        if not self.api_key:
            logger.warning("No Anthropic API key provided; LLM tagging will be disabled.")

        # Status flags for caller decisions
        self.last_rate_limited: bool = False

        # Lazy import to avoid hard dependency if not used
        self._anthropic_client = None
        try:
            from anthropic import Anthropic

            self._anthropic_client = Anthropic(api_key=self.api_key) if self.api_key else None
        except Exception:  # pragma: no cover
            self._anthropic_client = None

    def _build_prompt(self, *, title: str, description: str, subjects: List[str], passages: List[str]) -> Tuple[str, List[Dict[str, str]]]:
        system = (
            "Classify a book using a fixed list of tags. "
            "Only output JSON with probabilities in [0,1] for the provided tags."
        )
        # Trim long fields to reduce tokens
        title_s = (title or "")[:200]
        desc_s = (description or "")[:1000]
        subjects_s = ", ".join(subjects or [])[:300]
        passages_joined = "\n---\n".join(passages)
        instructions = textwrap.dedent(
            f"""
            Authorized tags: {json.dumps(self.authorized_tags)}

            Metadata:
            Title: {title_s}
            Description: {desc_s}
            Subjects: {subjects_s}

            Passages (samples):
            {passages_joined}

            Return JSON only:
            {{"probabilities": {{"<tag>": <0..1> for each authorized tag}}}}
            """
        ).strip()
        return system, [{"role": "user", "content": instructions}]

    @staticmethod
    def _sample_passages(text: str, *, max_total_chars: int = 1800, passages: int = 2) -> List[str]:
        if not text:
            return []
        text = text.strip()
        if not text:
            return []
        # Evenly sample beginning, middle, end
        per = max_total_chars // max(1, passages)
        n = len(text)
        if n <= max_total_chars:
            chunks = [text]
        else:
            thirds = [0, n // 2, max(0, n - (n // 3))]
            chunks = []
            for start in thirds[:passages]:
                chunk = text[start : min(n, start + per)]
                chunks.append(chunk)
        # Clean up newlines, condense whitespace a bit
        return ["\n".join([c.strip() for c in ch.splitlines() if c.strip()])[:per] for ch in chunks]

    def classify(
        self,
        *,
        title: str,
        description: str,
        subjects: List[str],
        text: str,
    ) -> List[LLMTagScore]:
        """
        Call Claude to score authorized tags. Returns a list sorted by score desc.
        If the API key is missing or a call fails, returns an empty list.
        """
        if not self.api_key or self._anthropic_client is None:
            return []

        passages = self._sample_passages(text)
        system, messages = self._build_prompt(
            title=title, description=description, subjects=subjects, passages=passages
        )
        # Simple bounded retry with backoff for rate limits
        self.last_rate_limited = False
        backoffs = [2, 5]
        attempt = 0
        while True:
            try:
                resp = self._anthropic_client.messages.create(
                    model=self.model,
                    max_tokens=512,
                    temperature=0.0,
                    system=system,
                    messages=messages,
                )
                text_out = "".join([getattr(b, "text", "") for b in resp.content])
                data = json.loads(text_out)
                probs: Dict[str, float] = data.get("probabilities", {}) if isinstance(data, dict) else {}
                break
            except Exception as e:  # pragma: no cover
                msg = str(e)
                if "429" in msg or "rate_limit" in msg:
                    if attempt < len(backoffs):
                        import time
                        time.sleep(backoffs[attempt])
                        attempt += 1
                        continue
                    else:
                        self.last_rate_limited = True
                        logger.warning(f"LLM tagging failed due to rate limit after retries: {e}")
                        return []
                logger.warning(f"LLM tagging failed: {e}")
                return []

        results: List[LLMTagScore] = []
        for tag in self.authorized_tags:
            val = probs.get(tag, 0.0)
            try:
                score = float(val)
            except Exception:
                score = 0.0
            if math.isnan(score) or score < 0:
                score = 0.0
            if score > 1:
                score = 1.0
            results.append(LLMTagScore(tag=tag, score=score))

        results.sort(key=lambda r: r.score, reverse=True)
        return results


