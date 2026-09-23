"""TASK-30 — DocumentIngest 4포맷 정규화(FR-27, AC-21, ADR-004).

픽스처는 **합성 문서**다. 실제 학원 시험지 파일을 확보하지 못했다(2026-09-24, 사용자 확인).
- `.pdf` 2종은 진짜 PDF다(Chromium 인쇄, Pillow 이미지). 이 경로는 실물로 검증된다.
- `.hwpx`·`.hwp`는 공개 규격대로 손으로 만든 최소 파일이다. 규격 해석이 틀렸을 가능성이 남으므로
  실파일 확보 전까지 **미검증**으로 본다([Q-03 인접 위험, RISK-02](../../docs/requirements.md#위험)).
"""
import io
import zipfile
from pathlib import Path

import pytest

from mathdesk.ingest import (
    HWP_DISTRIBUTION,
    HWP_ENCRYPTED,
    IngestError,
    hwp_header_flags,
    normalize,
)

FIXTURES = Path(__file__).parent / "fixtures"

OWPML = """<?xml version="1.0" encoding="UTF-8"?>
<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"
        xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">
  <hp:p><hp:run><hp:t>1. 다항식의 전개식에서 x의 계수는?</hp:t></hp:run></hp:p>
  <hp:p><hp:run><hp:equation><hp:script>x^2 over 2</hp:script></hp:equation></hp:run></hp:p>
  <hp:p><hp:run><hp:t>2. 등차수열의 합을 구하시오.</hp:t></hp:run></hp:p>
</hs:sec>
"""


def _hwpx(sections: int = 1) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("mimetype", "application/hwp+zip")
        for index in range(sections):
            archive.writestr(f"Contents/section{index}.xml", OWPML)
    return buffer.getvalue()


def test_pdf_with_a_text_layer_yields_pages_and_text_blocks():
    document = normalize((FIXTURES / "exam-text.pdf").read_bytes(), "exam-text.pdf")

    assert document.format == "pdf"
    assert document.page_count == 2
    texts = [block.text for block in document.blocks if block.kind == "text"]
    assert any("다항식" in text for text in texts)
    assert any("등차수열" in text for text in texts)
    assert all(block.page >= 1 for block in document.blocks)
    assert document.blocks[0].bbox is not None  # 좌표를 함께 준다(FR-27)
    # 글자 단위 조각이 줄로 합쳐진다. 문장 끝 마침표가 제 줄에서 떨어지지 않는다.
    assert [block.text for block in document.blocks if block.page == 2] == [
        "3. 함수 f(x)=x^2-4x+1의 최솟값을 구하시오."
    ]


def test_pdf_without_a_text_layer_falls_back_to_page_images():
    document = normalize((FIXTURES / "exam-scan.pdf").read_bytes(), "exam-scan.pdf")

    assert document.page_count == 1
    assert document.image_fallback is True
    assert document.page_images[1].startswith(b"\x89PNG")


def test_image_upload_is_treated_as_a_single_page_image():
    document = normalize((FIXTURES / "exam-scan.png").read_bytes(), "exam-scan.png")

    assert document.format == "image"
    assert document.page_count == 1
    assert document.image_fallback is True
    assert document.page_images[1].startswith(b"\x89PNG")


def test_hwpx_sections_become_pages_with_text_and_equation_blocks():
    document = normalize(_hwpx(sections=2), "시험지.hwpx")

    assert document.format == "hwpx"
    assert document.page_count == 2
    kinds = [block.kind for block in document.blocks]
    assert kinds.count("text") == 4
    assert kinds.count("equation") == 2
    equation = next(block for block in document.blocks if block.kind == "equation")
    assert equation.text == "x^2 over 2"  # 한글 수식 스크립트는 원문 그대로 보존한다


def _file_header(flags: int) -> bytes:
    """HWP 5.0 공개 규격의 FileHeader 스트림(256바이트) 앞부분만 만든다."""
    header = bytearray(256)
    header[0:17] = b"HWP Document File"
    header[36:40] = flags.to_bytes(4, "little")
    return bytes(header)


def test_hwp_header_flags_read_the_protection_bits():
    """OLE 컨테이너를 만들 수 없어 헤더 해석만 단위로 검사한다. 실파일 경로는 미검증이다."""
    assert hwp_header_flags(_file_header(0b10)) & HWP_ENCRYPTED
    assert hwp_header_flags(_file_header(0b100)) & HWP_DISTRIBUTION
    assert not hwp_header_flags(_file_header(0b1)) & HWP_ENCRYPTED

    with pytest.raises(IngestError):
        hwp_header_flags(b"\x00" * 256)


def test_hwp_that_is_not_an_ole_file_reports_the_pdf_alternative():
    with pytest.raises(IngestError) as raised:
        normalize(b"not an ole container", "시험지.hwp")

    assert "PDF" in str(raised.value)


def test_unsupported_format_is_rejected_with_its_extension():
    with pytest.raises(IngestError) as raised:
        normalize(b"hello", "메모.txt")

    assert ".txt" in str(raised.value)
