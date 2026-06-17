"""Feishu Wiki uploader for markdown analysis documents."""

from __future__ import annotations

from src.feishu_client import FeishuClient
from src.markdown_to_blocks import markdown_to_feishu_blocks


class FeishuUploader:
    """Create a wiki node, then fill the underlying docx document."""

    def __init__(self, config: dict):
        self.config = config
        self.client = FeishuClient(config)
        self.space_id = config["feishu"]["wiki_space_id"]
        self.parent_node_token = config["feishu"].get("parent_node_token", "")
        self.block_chunk_size = config["feishu"].get("block_chunk_size", 20)

    def upload(self, title: str, markdown_content: str) -> str:
        """Upload one markdown document to Feishu wiki."""
        node = self._create_wiki_node(title)
        node_token = node["node_token"]
        document_id = node["obj_token"]

        blocks = markdown_to_feishu_blocks(markdown_content)
        print(f"   Converted markdown to {len(blocks)} Feishu blocks")
        self._insert_blocks(document_id, document_id, blocks)

        base = self.config["feishu"]["base_url"].replace("open.", "")
        return f"{base}/wiki/{node_token}"

    def _create_wiki_node(self, title: str) -> dict:
        body = {
            "obj_type": "docx",
            "node_type": "origin",
            "title": title,
        }
        if self.parent_node_token:
            body["parent_node_token"] = self.parent_node_token
        data = self.client.request(
            "POST",
            f"/open-apis/wiki/v2/spaces/{self.space_id}/nodes",
            json=body,
        )
        return data["data"]["node"]

    def _insert_blocks(self, document_id: str, parent_block_id: str, blocks: list[dict]) -> None:
        buffer: list[dict] = []
        for block in blocks:
            if block.get("block_type") == 31:
                self._flush_block_buffer(document_id, parent_block_id, buffer)
                buffer = []
                self._insert_table_block(document_id, parent_block_id, block)
                continue
            buffer.append(block)
        self._flush_block_buffer(document_id, parent_block_id, buffer)

    def _flush_block_buffer(self, document_id: str, parent_block_id: str, blocks: list[dict]) -> None:
        if not blocks:
            return

        chunk_size = self.block_chunk_size
        total_chunks = (len(blocks) + chunk_size - 1) // chunk_size
        for index in range(0, len(blocks), chunk_size):
            chunk = [self._strip_internal_fields(block) for block in blocks[index : index + chunk_size]]
            chunk_index = index // chunk_size + 1
            print(f"   Uploading Feishu block chunk {chunk_index}/{total_chunks} ({len(chunk)} block(s))")
            self.client.request(
                "POST",
                f"/open-apis/docx/v1/documents/{document_id}/blocks/{parent_block_id}/children",
                json={"children": chunk, "index": -1},
            )

    def _insert_table_block(self, document_id: str, parent_block_id: str, table_block: dict) -> None:
        payload = self._build_table_descendant_payload(table_block)
        self.client.request(
            "POST",
            f"/open-apis/docx/v1/documents/{document_id}/blocks/{parent_block_id}/descendant",
            json=payload,
        )

    def _build_table_descendant_payload(self, table_block: dict) -> dict:
        rows = table_block.get("_table_rows") or []
        if not rows:
            return {"children_id": [], "index": -1, "descendants": []}

        row_size = table_block["table"]["property"]["row_size"]
        column_size = table_block["table"]["property"]["column_size"]
        column_width = self._estimate_column_widths(rows, column_size)
        temp_ids = self._TempIdFactory()

        table_id = temp_ids.next("table")
        cell_ids = []
        descendants = [{
            "block_id": table_id,
            "block_type": 31,
            "table": {
                "property": {
                    "row_size": row_size,
                    "column_size": column_size,
                    "column_width": column_width,
                    "header_row": row_size > 0,
                }
            },
            "children": [],
        }]

        for row in rows:
            for cell in row:
                cell_id = temp_ids.next("cell")
                text_id = temp_ids.next("cell_text")
                cell_ids.append(cell_id)
                descendants.append({
                    "block_id": cell_id,
                    "block_type": 32,
                    "table_cell": {},
                    "children": [text_id],
                })
                descendants.append({
                    "block_id": text_id,
                    "block_type": 2,
                    "text": {
                        "elements": cell.get("elements") or [self._text_run("", {})],
                        "style": {},
                    },
                    "children": [],
                })

        descendants[0]["children"] = cell_ids
        return {
            "index": -1,
            "children_id": [table_id],
            "descendants": [self._strip_internal_fields(block) for block in descendants],
        }

    def _estimate_column_widths(self, rows: list, column_size: int) -> list[int]:
        widths: list[int] = []
        for col_idx in range(column_size):
            max_len = max(
                len((row[col_idx].get("text", "") if col_idx < len(row) else "").strip())
                for row in rows
            )
            widths.append(min(max(160, max_len * 18), 420))
        return widths

    def _strip_internal_fields(self, value):
        if isinstance(value, dict):
            return {
                key: self._strip_internal_fields(val)
                for key, val in value.items()
                if not key.startswith("_")
            }
        if isinstance(value, list):
            return [self._strip_internal_fields(item) for item in value]
        return value

    def _text_run(self, content: str, style: dict) -> dict:
        return {"text_run": {"content": content, "text_element_style": style}}

    class _TempIdFactory:
        def __init__(self):
            self._counter = 0

        def next(self, prefix: str) -> str:
            self._counter += 1
            return f"{prefix}_{self._counter}"
