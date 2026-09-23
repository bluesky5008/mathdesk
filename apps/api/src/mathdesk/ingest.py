"""문서 입력 정규화(DES-11, ADR-004).

`.hwp`·`.hwpx`·`.pdf`·이미지를 `{pages, blocks, page_images}` 공통 구조로 바꾼다.
이후 단계(문항 분할·분석)는 원본 포맷을 알지 못한다.

한글 수식 스크립트는 LaTeX가 아니므로 변환하지 않고 원문 그대로 보존한다(FR-27).
"""
import io
import zipfile
import zlib
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from xml.etree import ElementTree

import olefile
import pypdfium2 as pdfium
from PIL import Image

PDF_SUFFIXES = {".pdf"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}
RENDER_SCALE = 2  # 문항 이미지가 분석에 쓰이므로 화면 해상도보다 크게 뽑는다


class IngestError(Exception):
    """사용자에게 사유를 그대로 보여줄 수 있는 실패."""


@dataclass
class Block:
    page: int
    kind: str  # text | equation | image | table
    text: str | None = None
    bbox: tuple[float, float, float, float] | None = None


@dataclass
class NormalizedDocument:
    format: str
    page_count: int
    blocks: list[Block] = field(default_factory=list)
    page_images: dict[int, bytes] = field(default_factory=dict)
    image_fallback: bool = False


def normalize(data: bytes, filename: str) -> NormalizedDocument:
    suffix = PurePosixPath(filename).suffix.lower()
    if suffix in PDF_SUFFIXES:
        return _from_pdf(data)
    if suffix == ".hwpx":
        return _from_hwpx(data)
    if suffix == ".hwp":
        return _from_hwp(data)
    if suffix in IMAGE_SUFFIXES:
        return _from_image(data)
    raise IngestError(f"지원하지 않는 형식입니다: {suffix or '확장자 없음'}")


def _png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _from_pdf(data: bytes) -> NormalizedDocument:
    try:
        pdf = pdfium.PdfDocument(io.BytesIO(data))
        page_count = len(pdf)
    except pdfium.PdfiumError as error:
        raise IngestError(
            f"PDF를 열 수 없습니다: {error}. 암호가 걸려 있다면 해제 후 다시 올려 주세요."
        ) from error

    document = NormalizedDocument(format="pdf", page_count=page_count)
    for number in range(page_count):
        page = pdf[number]
        text_page = page.get_textpage()
        lines = _merge_lines(_text_fragments(page, text_page))
        for bbox, text in lines:
            document.blocks.append(Block(number + 1, "text", text, bbox))
        # 텍스트 레이어가 없는 페이지(스캔본, 수식이 그림인 문서)는 이미지 경로로 폴백한다
        if not lines:
            document.page_images[number + 1] = _png(page.render(scale=RENDER_SCALE).to_pil())
            document.blocks.append(Block(number + 1, "image"))
            document.image_fallback = True
    return document


TEXT_OBJECT = 1  # FPDF_PAGEOBJ_TEXT
LINE_OVERLAP = 0.5  # 같은 줄로 볼 세로 겹침 비율


def _text_fragments(page, text_page) -> list[tuple[tuple[float, float, float, float], str]]:
    fragments = []
    for obj in page.get_objects():
        if obj.type != TEXT_OBJECT:
            continue
        obj.textpage = text_page
        text = obj.extract()
        if text.strip():
            fragments.append((obj.get_bounds(), text))
    return fragments


def _merge_lines(fragments) -> list[tuple[tuple[float, float, float, float], str]]:
    """글자 단위로 쪼개진 조각을 줄로 합친다.

    PDF의 텍스트 개체는 글꼴·자간이 바뀔 때마다 끊긴다. 한글 문서에서는 글자 하나가
    개체 하나가 되기도 해서, 그대로 쓰면 블록이 글자 수만큼 나온다.
    """
    lines: list[dict] = []
    for (left, bottom, right, top), text in fragments:
        for line in lines:
            # 윗변만 비교하면 마침표·쉼표가 제 줄에서 떨어져 나간다. 세로로 겹치는지를 본다.
            overlap = min(line["top"], top) - max(line["bottom"], bottom)
            shorter = min(line["top"] - line["bottom"], top - bottom)
            if shorter > 0 and overlap / shorter >= LINE_OVERLAP:
                line["parts"].append((left, text))
                line["left"] = min(line["left"], left)
                line["right"] = max(line["right"], right)
                line["bottom"] = min(line["bottom"], bottom)
                line["top"] = max(line["top"], top)
                break
        else:
            lines.append(
                {"top": top, "bottom": bottom, "left": left, "right": right,
                 "parts": [(left, text)]}
            )

    merged = []
    for line in sorted(lines, key=lambda line: -line["top"]):
        # 조각 사이에 공백이 중복으로 들어간다. 줄 안의 공백을 하나로 정리한다.
        text = " ".join("".join(part for _, part in sorted(line["parts"])).split())
        if text:
            bbox = (line["left"], line["bottom"], line["right"], line["top"])
            merged.append((bbox, text))
    return merged


# OWPML 네임스페이스. 한컴 규격이 접두사를 hp/hs로 쓴다.
HP = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"


def _from_hwpx(data: bytes) -> NormalizedDocument:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
        sections = sorted(
            name for name in archive.namelist() if name.startswith("Contents/section")
        )
    except zipfile.BadZipFile as error:
        raise IngestError("hwpx 파일을 열 수 없습니다. 파일이 손상되었을 수 있습니다.") from error
    if not sections:
        raise IngestError("hwpx 안에 본문(Contents/section*.xml)이 없습니다.")

    document = NormalizedDocument(format="hwpx", page_count=len(sections))
    for page, name in enumerate(sections, start=1):
        root = ElementTree.fromstring(archive.read(name))
        for element in root.iter():
            tag, text = element.tag, (element.text or "").strip()
            if not text:
                continue
            if tag == f"{HP}t":
                document.blocks.append(Block(page, "text", text))
            elif tag == f"{HP}script":
                # 한글 수식 스크립트다. 변환하지 않는다(ADR-004 결정 5)
                document.blocks.append(Block(page, "equation", text))
    return document


HWP_SIGNATURE = b"HWP Document File"
HWP_ENCRYPTED = 0b10
HWP_DISTRIBUTION = 0b100
HWP_COMPRESSED = 0b1


def hwp_header_flags(header: bytes) -> int:
    """HWP 5.0 FileHeader 스트림의 속성 비트필드(오프셋 36)."""
    if not header.startswith(HWP_SIGNATURE):
        raise IngestError("한글 문서(hwp)가 아닙니다.")
    return int.from_bytes(header[36:40], "little")


def _from_hwp(data: bytes) -> NormalizedDocument:
    if not olefile.isOleFile(io.BytesIO(data)):
        raise IngestError(
            "hwp 파일을 열 수 없습니다. 한글에서 PDF로 저장한 뒤 올려 주세요."
        )
    ole = olefile.OleFileIO(io.BytesIO(data))
    try:
        flags = hwp_header_flags(ole.openstream("FileHeader").read())
        if flags & HWP_ENCRYPTED:
            raise IngestError(
                "암호가 걸린 hwp는 읽을 수 없습니다. 암호를 해제하거나 PDF로 저장해 올려 주세요."
            )
        if flags & HWP_DISTRIBUTION:
            raise IngestError(
                "배포용으로 보호된 hwp는 읽을 수 없습니다. 원본 파일이나 PDF로 올려 주세요."
            )
        return _hwp_body(ole, compressed=bool(flags & HWP_COMPRESSED))
    finally:
        ole.close()


# HWPTAG_BEGIN(0x010) + 51. 문단 텍스트 레코드.
HWPTAG_PARA_TEXT = 0x010 + 51


def _hwp_body(ole: olefile.OleFileIO, compressed: bool) -> NormalizedDocument:
    sections = sorted(
        "/".join(entry) for entry in ole.listdir() if entry[0] == "BodyText"
    )
    document = NormalizedDocument(format="hwp", page_count=len(sections))
    for page, name in enumerate(sections, start=1):
        raw = ole.openstream(name).read()
        body = zlib.decompress(raw, -15) if compressed else raw
        for tag, payload in _hwp_records(body):
            if tag == HWPTAG_PARA_TEXT:
                text = payload.decode("utf-16-le", errors="ignore")
                # 제어 문자(개체·필드 표시)는 본문이 아니다
                text = "".join(c for c in text if c.isprintable()).strip()
                if text:
                    document.blocks.append(Block(page, "text", text))
    if not document.blocks:
        # 이 경로는 실파일로 검증하지 못했다. 조용히 빈 문서를 돌려주면 뒤에서
        # 문항 0개로 흘러가므로, 아무것도 못 읽었으면 여기서 사유를 알린다.
        raise IngestError(
            "hwp 본문에서 텍스트를 찾지 못했습니다. 한글에서 PDF로 저장한 뒤 올려 주세요."
        )
    return document


def _hwp_records(body: bytes):
    """HWP 5.0 레코드 스트림: 32비트 헤더(태그 10 / 수준 10 / 크기 12)."""
    offset = 0
    while offset + 4 <= len(body):
        header = int.from_bytes(body[offset : offset + 4], "little")
        tag, size = header & 0x3FF, (header >> 20) & 0xFFF
        offset += 4
        if size == 0xFFF:  # 확장 크기
            size = int.from_bytes(body[offset : offset + 4], "little")
            offset += 4
        yield tag, body[offset : offset + size]
        offset += size


def _from_image(data: bytes) -> NormalizedDocument:
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except OSError as error:
        raise IngestError("이미지를 열 수 없습니다.") from error
    return NormalizedDocument(
        format="image",
        page_count=1,
        blocks=[Block(1, "image")],
        page_images={1: _png(image.convert("RGB"))},
        image_fallback=True,
    )
