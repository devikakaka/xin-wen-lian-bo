"""LLM analyzer for one day's news transcript."""

from __future__ import annotations

import time

from openai import OpenAI

from src.news_loader import NewsTranscript


class LLMAnalyzer:
    """Analyze one day's transcript with an OpenAI-compatible API."""

    def __init__(self, config: dict):
        self.cfg = config["llm"]
        self.client = OpenAI(
            api_key=self.cfg["api_key"],
            base_url=self.cfg["base_url"],
        )
        self.model = self.cfg["model"]
        self.system_prompt = self.cfg["system_prompt"]
        self.user_prompt_template = self.cfg["user_prompt_template"]
        self.temperature = self.cfg.get("temperature", 0.2)
        self.max_tokens = self.cfg.get("max_tokens", 5000)
        self.max_items = self.cfg.get("max_items", 30)
        self.max_content_length_per_item = self.cfg.get("max_content_length_per_item", 1500)

    def analyze(self, transcript: NewsTranscript) -> str:
        """Analyze the transcript and return Markdown."""
        return self._analyze_with_retry(transcript)

    def _analyze_with_retry(self, transcript: NewsTranscript, max_retries: int = 3) -> str:
        """Call the LLM with simple exponential backoff."""
        for attempt in range(max_retries):
            try:
                return self._analyze_once(transcript)
            except Exception as exc:  # pragma: no cover - depends on network/API
                wait_seconds = 2 ** (attempt + 1)
                print(f"   Attempt {attempt + 1} failed: {exc}. Retrying in {wait_seconds}s...")
                time.sleep(wait_seconds)
        raise RuntimeError(f"LLM analysis failed after {max_retries} attempts")

    def _analyze_once(self, transcript: NewsTranscript) -> str:
        """Perform one LLM request."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": self._build_user_prompt(transcript)},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        usage = response.usage
        if usage:
            print(
                "   Tokens: "
                f"prompt={usage.prompt_tokens}, "
                f"completion={usage.completion_tokens}, "
                f"total={usage.total_tokens}"
            )
        return (response.choices[0].message.content or "").strip()

    def _build_user_prompt(self, transcript: NewsTranscript) -> str:
        """Render the full user prompt from the day's transcript."""
        parts: list[str] = []
        for index, item in enumerate(transcript.items[: self.max_items], start=1):
            content = item.content_text[: self.max_content_length_per_item]
            parts.append(
                f"{index}. {item.title}\n"
                f"原文链接：{item.url or '无'}\n"
                f"正文：\n{content}"
            )

        return self.user_prompt_template.format(
            date=transcript.date,
            abstract=transcript.abstract,
            items="\n\n".join(parts),
        )
