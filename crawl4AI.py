import json
import os
import re
import unicodedata
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler, CacheMode
from bs4 import BeautifulSoup
import google.generativeai as genai
from datetime import datetime
from metadata_helper import extract_metadata_from_content

# Load environment variables

# ====== CONFIG ======
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyBEmmuMA1dNa28-r7UWuTxWtUvHvCy5j34")
genai.configure(api_key=GEMINI_API_KEY)

MODEL_NAME = "models/gemini-2.5-flash"

# --- Lọc rác (tối thiểu, dễ mở rộng) ---
JUNK_PATTERNS = [
    r"lượt xem",
    r"views today",
    r"view today",
    r"xem thêm",
    r"đọc thêm",
    r"khám phá ngay",
    r"số lượng người",
    r"đã xem bài viết",
]


def _normalize_ws(text: str) -> str:
    """Chuẩn hoá khoảng trắng."""
    text = re.sub(r"\s+", " ", (text or "")).strip()
    return text


def _remove_junk(text: str) -> str:
    """Bỏ câu rác kiểu CTA / view count."""
    if not text:
        return ""
    chunks = re.split(r"[\n\r]+", text)
    keep: list[str] = []
    for c in chunks:
        s = _normalize_ws(c)
        if len(s) < 15:
            continue
        low = s.lower()
        if any(re.search(p, low) for p in JUNK_PATTERNS):
            continue
        keep.append(s)
    return " ".join(keep).strip()


def _truncate_words(text: str, min_words: int, max_words: int) -> str:
    """Cắt theo số từ (không bịa thêm nếu thiếu)."""
    text = _normalize_ws(_remove_junk(text))
    if not text:
        return ""
    words = text.split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words])


def _slugify(text: str) -> str:
    """Tạo slug an toàn (không dấu) để làm id."""
    text = (text or "").strip().lower()
    if not text:
        return "unknown"
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "unknown"


def _hub_id_from_url_or_name(url: str, name: str) -> str:
    """Ưu tiên slug từ URL, fallback sang title."""
    try:
        path = urlparse(url).path.strip("/")
        segs = [s for s in path.split("/") if s]
        # lấy segment cuối nếu có, bỏ .html
        cand = segs[-1] if segs else ""
        cand = re.sub(r"\.html?$", "", cand, flags=re.IGNORECASE)
        cand = cand.replace("-", " ")
        slug = _slugify(cand)
        if slug and slug != "unknown":
            return slug
    except Exception:
        pass
    return _slugify(name)


def _find_main_content(soup: BeautifulSoup):
    """Chọn vùng content chính, tránh nav/footer/sidebar."""
    for t in soup(["script", "style", "noscript", "svg", "iframe"]):
        t.decompose()

    candidates = [
        soup.find("main"),
        soup.find("article"),
        soup.find("div", id="content"),
        soup.find("div", class_="content"),
        soup.find("div", class_="entry-content"),
        soup.find("div", class_="post-content"),
    ]
    for c in candidates:
        if c and len(c.get_text(" ", strip=True)) > 400:
            return c

    body = soup.body or soup
    for t in body.find_all(["header", "footer", "nav", "aside"], recursive=True):
        t.decompose()
    return body


def _text_from_node(tag) -> str:
    """Lấy text sạch từ node; giữ bullet cho ul/ol."""
    if not tag:
        return ""

    if tag.name in ("ul", "ol"):
        items = []
        for li in tag.find_all("li", recursive=False):
            s = _normalize_ws(li.get_text(" ", strip=True))
            s = _remove_junk(s)
            if len(s) >= 10:
                items.append(f"- {s}")
        return "\n".join(items)

    # p/div/span/strong...
    s = _normalize_ws(tag.get_text(" ", strip=True))
    return _remove_junk(s)


def _collect_section_text(heading_tag, max_words: int) -> str:
    """Gom text sau heading cho tới heading kế tiếp; có thể lấy ul/li/strong."""
    parts: list[str] = []

    # không nhét heading vào content (tránh dính tiêu đề)
    for sib in heading_tag.find_next_siblings():
        if sib.name in ("h1", "h2", "h3", "h4", "h5"):
            break

        if sib.name in ("p", "div", "ul", "ol"):
            t = _text_from_node(sib)
            if t:
                parts.append(t)

        # stop theo word-count
        if sum(len(p.split()) for p in parts) >= max_words:
            break

    return _normalize_ws("\n".join(parts))


def build_heading_keywords_prompt(html_sample: str) -> str:
    """
    Prompt để LLM tìm heading keywords (LIGHTWEIGHT)
    """
    return f"""Analyze this HTML and identify heading keywords for each section.

Find Vietnamese keywords in headings (h2, h3) for these sections:
- overview/introduction
- weather/best time
- transportation  
- food/cuisine
- places/attractions
- travel tips

Return ONLY JSON:
{{
  "keywords": {{
    "weather": ["thời tiết", "khí hậu", "mùa"],
    "transportation": ["phương tiện", "di chuyển", "đi lại"],
    "food": ["ẩm thực", "món ăn", "nhà hàng"],
    "places": ["địa điểm", "tham quan", "danh lam"],
    "tips": ["kinh nghiệm", "lưu ý", "tips"]
  }}
}}

HTML sample:
{html_sample[:3000]}

Return ONLY the JSON."""


async def llm_get_heading_keywords(html_content: str) -> dict:
    """
    LLM chỉ tìm keywords, KHÔNG extract content
    """
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = build_heading_keywords_prompt(html_content)

    print("🤖 LLM đang tìm heading keywords...")

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Clean markdown
        if text.startswith("```json"):
            text = text[7:-3].strip()
        elif text.startswith("```"):
            text = text[3:-3].strip()

        keywords = json.loads(text)
        print("✅ Keywords đã được tìm thấy!")
        return keywords.get("keywords", {})

    except Exception as e:
        print(f"⚠️ LLM failed: {e}, using default keywords")
        return {
            "weather": ["thời tiết", "khí hậu", "thời gian", "mùa"],
            "transportation": ["phương tiện", "di chuyển", "đi lại", "xe"],
            "food": ["ẩm thực", "món ăn", "nhà hàng", "ăn uống"],
            "places": ["địa điểm", "tham quan", "danh lam", "du lịch"],
            "tips": ["kinh nghiệm", "lưu ý", "tips", "mẹo"]
        }


def extract_content_with_beautifulsoup(html: str, keywords: dict) -> dict:
    """Extract content theo heading keywords + rule-based (không dùng LLM)."""
    print("\ud83d\udd0d BeautifulSoup đang extract content...")

    soup = BeautifulSoup(html, "html.parser")
    content_area = _find_main_content(soup)

    extracted = {
        "name": "",
        "overview": "",
        "location_and_geography": "",
        "weather_and_best_time": "",
        "transportation": "",
        "culinary_highlights": "",
        "must_visit_locations": "",
        "travel_tips": "",
    }

    # Title
    title = content_area.find("h1") or soup.find("h1")
    if title:
        extracted["name"] = _normalize_ws(title.get_text(" ", strip=True))
        print(f"   ✓ Title: {extracted['name'][:60]}")

    # Overview: chọn đoạn p dài, không rác
    paras = [
        _remove_junk(p.get_text(" ", strip=True))
        for p in content_area.find_all("p", limit=12)
    ]
    paras = [p for p in paras if p and len(p) >= 80]
    if paras:
        extracted["overview"] = paras[0]
        print(f"   ✓ Overview: {len(extracted['overview'])} chars")

    # Map keyword -> field
    def match_field(h_text: str) -> str | None:
        h = (h_text or "").lower()

        for kw in keywords.get("weather", []):
            if kw in h:
                return "weather_and_best_time"
        for kw in keywords.get("transportation", []):
            if kw in h:
                return "transportation"
        for kw in keywords.get("food", []):
            if kw in h:
                return "culinary_highlights"
        for kw in keywords.get("places", []):
            if kw in h:
                return "must_visit_locations"
        for kw in keywords.get("tips", []):
            if kw in h:
                return "travel_tips"
        return None

    headings = content_area.find_all(["h2", "h3", "h4"])

    # gom section theo heading; không set nếu đã có (tránh overwrite)
    for hd in headings:
        field = match_field(hd.get_text(" ", strip=True))
        if not field or extracted.get(field):
            continue

        section_text = _collect_section_text(hd, max_words=260)
        extracted[field] = section_text
        if extracted[field]:
            print(f"   ✓ {field}: {len(extracted[field])} chars")

    return extracted


async def extract_hub_info(url: str) -> dict:
    """
    WORKFLOW SIMPLIFIED:
    1. Crawl4AI fetch HTML
    2. LLM tìm keywords (lightweight)
    3. BeautifulSoup extract content (rule-based)
    4. Metadata helper format JSON
    """

    # ===== BƯỚC 1: CRAWL4AI FETCH HTML =====
    print(f"\n{'='*60}")
    print(f"🚀 BƯỚC 1: Crawl4AI fetch HTML")
    print(f"{'='*60}")

    async with AsyncWebCrawler(verbose=True) as crawler:
        result = await crawler.arun(
            url=url,
            cache_mode=CacheMode.BYPASS
        )

        if not result.success:
            raise Exception(f"Crawl failed: {result.error_message}")

        html_content = result.html
        print(f"✅ Đã fetch HTML ({len(html_content)} chars)")

    # ===== BƯỚC 2: LLM TÌM KEYWORDS =====
    print(f"\n{'='*60}")
    print(f"🤖 BƯỚC 2: LLM tìm heading keywords (lightweight)")
    print(f"{'='*60}")

    keywords = await llm_get_heading_keywords(html_content)
    print(f"✅ Keywords: {json.dumps(keywords, ensure_ascii=False)[:200]}")

    # ===== BƯỚC 3: BEAUTIFULSOUP EXTRACT =====
    print(f"\n{'='*60}")
    print(f"🔍 BƯỚC 3: BeautifulSoup extract content")
    print(f"{'='*60}")

    raw_extracted = extract_content_with_beautifulsoup(html_content, keywords)
    print(f"✅ Đã extract {len([v for v in raw_extracted.values() if v])} fields có nội dung")

    # ===== BƯỚC 4: FORMAT JSON FINAL =====
    print(f"\n{'='*60}")
    print(f"📦 BƯỚC 4: Format JSON final với metadata")
    print(f"{'='*60}")

    name = raw_extracted.get("name", "Unknown Destination")
    overview_raw = raw_extracted.get("overview", "")

    # --- chuẩn hoá + giới hạn theo yêu cầu (word range) ---
    overview = _truncate_words(overview_raw, 120, 250)
    location_geo = _truncate_words(raw_extracted.get("location_and_geography", ""), 80, 150)
    weather = _truncate_words(raw_extracted.get("weather_and_best_time", ""), 120, 200)
    transportation = _truncate_words(raw_extracted.get("transportation", ""), 80, 150)
    locations = _truncate_words(raw_extracted.get("must_visit_locations", ""), 150, 300)
    food = _truncate_words(raw_extracted.get("culinary_highlights", ""), 120, 200)
    tips = _truncate_words(raw_extracted.get("travel_tips", ""), 80, 150)

    # Detect metadata
    content_dict = {
        "overview": overview,
        "weather": weather,
        "locations": locations,
        "food": food,
    }

    metadata = extract_metadata_from_content(name, overview, content_dict)

    print("✅ Metadata detected:")
    print(f"   - Region: {metadata['region']}")
    print(f"   - Province: {metadata['province']}")
    print(f"   - Airport: {metadata['airport']}")
    print(f"   - Climate: {metadata['climate_tag']}")
    print(f"   - Vibe: {metadata['vibe_tag']}")

    # text_content: dài hơn overview, dùng cho retrieval
    text_content = _normalize_ws(
        " ".join([
            overview,
            weather[:600],
            locations[:600],
            food[:600],
            tips[:400],
        ])
    )

    hub_id = _hub_id_from_url_or_name(url, name)

    final_data = {
        "id": f"hub_{hub_id}",
        "name": name,
        "metadata": {
            "type": "hub_info",
            "region": metadata["region"],
            "province": metadata["province"],
            "airport": metadata["airport"],
            "climate_tag": metadata["climate_tag"],
            "vibe_tag": metadata["vibe_tag"],
            "sources": [url],
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
        },
        "text_content": text_content,
        "content": {
            "overview": overview,
            "location_and_geography": location_geo,
            "weather_and_best_time": weather,
            "transportation": transportation,
            "must_visit_locations": locations,
            "culinary_highlights": food,
            "travel_tips": tips,
        },
    }

    print("✅ JSON final hoàn tất!")
    return final_data


if __name__ == "__main__":
    # Chạy test nhanh (tuỳ chọn): bỏ comment để chạy.
    import asyncio
    pass

    url = "https://www.dalattrip.com/dulich/du-lich-da-lat-tu-tuc/"
    hub_info = asyncio.run(extract_hub_info(url))
    print(json.dumps(hub_info, indent=2, ensure_ascii=False))
