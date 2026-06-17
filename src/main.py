"""Main pipeline: load transcript JSON -> analyze -> save markdown -> upload Feishu."""

from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

if __package__ in {None, ""}:
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from src.config_loader import load_config
from src.feishu_uploader import FeishuUploader
from src.llm_analyzer import LLMAnalyzer
from src.news_loader import load_transcript, resolve_transcript_path
import yaml


BEIJING_TZ = ZoneInfo("Asia/Shanghai")


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description="Analyze CCTV News transcript and upload the markdown to Feishu.",
    )
    parser.add_argument("--config", default="config/config.yaml", help="Path to config file")
    parser.add_argument("--date", help="Target date in YYYYMMDD format, default is Beijing today")
    parser.add_argument("--input-json", help="Path to structured transcript JSON")
    parser.add_argument("--skip-feishu", action="store_true", help="Generate markdown but skip Feishu upload")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    target_date = _resolve_target_date(args.date)
    preferred_input_path = Path(args.input_json or f"news/{target_date}.json")
    input_path = resolve_transcript_path(preferred_input_path)

    print("📋 Loading configuration...")
    config = load_config(args.config)

    print(f"📰 Loading transcript: {input_path}")
    transcript = load_transcript(input_path)
    print(f"   Date: {transcript.date}")
    print(f"   Items: {len(transcript.items)}")
    source_name = _resolve_source_name(config)
    print(f"   Source: {source_name}")

    print("🤖 Generating analysis markdown...")
    analyzer = LLMAnalyzer(config)
    document_title = config["feishu"].get("document_title_template", "《新闻联播》解析 - {date}").format(date=target_date)
    analysis_markdown = _normalize_document(analyzer.analyze(transcript), document_title)

    if config["output"].get("save_analysis", True):
        save_paths = _save_analysis(config, target_date, analysis_markdown, source_name=source_name)
        for path in save_paths:
            print(f"   Saved: {path}")

    feishu_enabled = (
        not args.skip_feishu
        and config["feishu"].get("upload_enabled", False)
        and config["feishu"].get("wiki_space_id")
    )
    if not feishu_enabled:
        print("⏭️  Skipping Feishu upload")
        return

    print("📤 Uploading to Feishu...")
    uploader = FeishuUploader(config)
    uploaded_url = uploader.upload(document_title, analysis_markdown, source_name=source_name)
    print(f"✅ Uploaded: {uploaded_url}")


def _resolve_target_date(date_text: str | None) -> str:
    """Resolve the target date in YYYYMMDD format."""
    if not date_text:
        date_text = os.getenv("NEWS_DATE", "").strip() or None
    if date_text:
        try:
            return datetime.strptime(date_text, "%Y%m%d").strftime("%Y%m%d")
        except ValueError as exc:
            raise ValueError("--date must use YYYYMMDD") from exc
    return datetime.now(BEIJING_TZ).strftime("%Y%m%d")


def _normalize_document(markdown: str, title: str) -> str:
    """Ensure the markdown starts with a single H1 title."""
    body = markdown.strip()
    if not body:
        return f"# {title}\n"

    lines = body.splitlines()
    first_h1 = next((i for i, line in enumerate(lines) if line.startswith("# ")), None)
    if first_h1 is None:
        return f"# {title}\n\n{body}\n"

    lines[first_h1] = f"# {title}"
    return "\n".join(lines).rstrip() + "\n"


def _save_analysis(config: dict, target_date: str, markdown: str, source_name: str) -> list[Path]:
    """Save date-specific and latest analysis markdown files."""
    output_cfg = config["output"]
    analysis_dir = Path(output_cfg.get("analysis_dir", "analysis"))
    analysis_dir.mkdir(parents=True, exist_ok=True)

    file_template = output_cfg.get("analysis_file_template", "{date}.md")
    dated_path = analysis_dir / file_template.format(date=target_date)
    rendered = _render_analysis_file(
        title=f"《新闻联播》 - {target_date}",
        source_name=source_name,
        article_date=target_date,
        body=markdown,
    )
    dated_path.write_text(rendered, encoding="utf-8")

    saved_paths = [dated_path]
    latest_path_text = output_cfg.get("latest_analysis_path")
    if latest_path_text:
        latest_path = Path(latest_path_text)
        latest_path.parent.mkdir(parents=True, exist_ok=True)
        latest_path.write_text(rendered, encoding="utf-8")
        saved_paths.append(latest_path)
    return saved_paths


def _resolve_source_name(config: dict) -> str:
    """Resolve the logical source name used for Feishu parent-node routing."""
    explicit_source_name = (config.get("feishu", {}).get("source_name") or "").strip()
    if explicit_source_name:
        return explicit_source_name

    source_parent_node_tokens = config.get("feishu", {}).get("source_parent_node_tokens", {})
    if len(source_parent_node_tokens) == 1:
        return next(iter(source_parent_node_tokens))

    return "新闻联播"


def _render_analysis_file(
    title: str,
    source_name: str,
    article_date: str,
    body: str,
) -> str:
    """Render analysis markdown with YAML front matter metadata."""
    front_matter = {
        "title": title,
        "source_name": source_name,
        "date": article_date,
    }
    return (
        "---\n"
        f"{yaml.safe_dump(front_matter, allow_unicode=True, sort_keys=False).strip()}\n"
        "---\n\n"
        f"{body.rstrip()}\n"
    )


if __name__ == "__main__":
    main()
