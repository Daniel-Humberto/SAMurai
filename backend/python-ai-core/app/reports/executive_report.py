from io import BytesIO
from pathlib import Path
from textwrap import wrap
from uuid import UUID

from app.config import get_settings
from app.narrative.llm_adapter import LLMAdapter


class ExecutiveReportService:
    def __init__(self):
        self.llm = LLMAdapter()
        self.settings = get_settings()

    def build_summary(self, session_stats: dict, events: list[dict]) -> str:
        return self.llm.generate_executive_report(session_stats, events)

    def write_report_artifact(self, session_id: UUID, summary: str, stats: dict, events: list[dict]) -> str:
        self.settings.reports_dir.mkdir(parents=True, exist_ok=True)
        output_path = Path(self.settings.reports_dir) / f"{session_id}.pdf"
        lines = [
            f"Executive Report {session_id}",
            "",
            "Summary",
            summary.strip() or "No summary available.",
            "",
            "Stats",
        ]
        for key, value in stats.items():
            lines.append(f"- {key}: {value}")
        lines.append("")
        lines.append("Events")
        if events:
            for event in events:
                lines.append(
                    f"- t={event.get('timestamp_s', 0):.2f}s | {event.get('event_type', 'unknown')} | {event.get('narration_text', '')}"
                )
        else:
            lines.append("- No events recorded.")

        output_path.write_bytes(self._build_pdf(lines))
        return str(output_path)

    def _build_pdf(self, lines: list[str]) -> bytes:
        page_width = 612
        page_height = 792
        left_margin = 54
        top_y = 756
        bottom_margin = 54
        line_height = 14
        max_chars = 88

        wrapped_lines: list[str] = []
        for line in lines:
            normalized = self._normalize_text(line)
            if not normalized:
                wrapped_lines.append("")
                continue
            wrapped = wrap(normalized, width=max_chars, break_long_words=True, break_on_hyphens=False)
            wrapped_lines.extend(wrapped or [""])

        lines_per_page = max(1, int((top_y - bottom_margin) / line_height))
        pages = [wrapped_lines[index:index + lines_per_page] for index in range(0, len(wrapped_lines), lines_per_page)] or [[""]]

        objects: list[bytes] = []

        def add_object(payload: bytes) -> int:
            objects.append(payload)
            return len(objects)

        font_object = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        page_refs: list[int] = []
        content_refs: list[int] = []

        for page_lines in pages:
            stream = self._build_page_stream(page_lines, left_margin, top_y, line_height)
            content_ref = add_object(
                f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1") + stream + b"\nendstream"
            )
            content_refs.append(content_ref)
            page_refs.append(0)

        pages_ref = len(objects) + len(pages) + 1
        for index, content_ref in enumerate(content_refs):
            page_object = (
                f"<< /Type /Page /Parent {pages_ref} 0 R /MediaBox [0 0 {page_width} {page_height}] "
                f"/Resources << /Font << /F1 {font_object} 0 R >> >> /Contents {content_ref} 0 R >>"
            ).encode("latin-1")
            page_refs[index] = add_object(page_object)

        kids = " ".join(f"{ref} 0 R" for ref in page_refs)
        pages_object = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_refs)} >>".encode("latin-1")
        actual_pages_ref = add_object(pages_object)
        catalog_ref = add_object(f"<< /Type /Catalog /Pages {actual_pages_ref} 0 R >>".encode("latin-1"))

        buffer = BytesIO()
        buffer.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for object_number, payload in enumerate(objects, start=1):
            offsets.append(buffer.tell())
            buffer.write(f"{object_number} 0 obj\n".encode("latin-1"))
            buffer.write(payload)
            buffer.write(b"\nendobj\n")

        xref_offset = buffer.tell()
        buffer.write(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
        buffer.write(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            buffer.write(f"{offset:010d} 00000 n \n".encode("latin-1"))
        buffer.write(
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_ref} 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("latin-1")
        )
        return buffer.getvalue()

    def _build_page_stream(self, lines: list[str], left_margin: int, top_y: int, line_height: int) -> bytes:
        commands = ["BT", "/F1 11 Tf", f"{line_height} TL", f"{left_margin} {top_y} Td"]
        for index, line in enumerate(lines):
            escaped = self._escape_pdf_text(line)
            if index == 0:
                commands.append(f"({escaped}) Tj")
            else:
                commands.append("T*")
                commands.append(f"({escaped}) Tj")
        commands.append("ET")
        return "\n".join(commands).encode("latin-1")

    def _normalize_text(self, value: str) -> str:
        ascii_text = value.replace("\t", " ").replace("\r", " ").replace("\n", " ").strip()
        return ascii_text.encode("latin-1", "replace").decode("latin-1")

    def _escape_pdf_text(self, value: str) -> str:
        return value.replace(chr(92), chr(92) * 2).replace("(", chr(92) + "(").replace(")", chr(92) + ")")
