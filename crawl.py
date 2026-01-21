import asyncio
import json
import os
import re

from crawl4ai import AsyncWebCrawler, CacheMode
from bs4 import BeautifulSoup
import google.generativeai as genai
from datetime import datetime
from metadata_helper import extract_metadata_from_content

from crawl4ai import AsyncWebCrawler, CrawlResult, CrawlerRunConfig, JsonCssExtractionStrategy
from crawl4ai import DefaultMarkdownGenerator, PruningContentFilter
from crawl4ai.extraction_strategy import LLMExtractionStrategy

# async def demo_basic_crawl():
#     async with AsyncWebCrawler(verbose=True) as crawler:
#
#         links = [
#             "https://www.dalattrip.com/dulich/du-lich-da-lat-tu-tuc/",
#             "https://www.dalattrip.com/dulich/dia-diem-du-lich-da-lat/"
#         ]
#
#         # lọc nội dung -- filter , config các tag css không cần thiết
#         md_generator = DefaultMarkdownGenerator(
#             content_filter=PruningContentFilter()
#         )
#         config = CrawlerRunConfig(
#             markdown_generator=md_generator
#         )
#
#         results: list[CrawlResult] = await crawler.arun_many(
#             urls=links,
#             config=config
#         )
#
#
#
#
#         for i, result in enumerate(results):
#             print(f"Resutl for URL {i+1}:")
#             if result.success:
#                 print("\n  500 ký tự đầu tiên của Markdown:\n")
#                 print("--------------------------------------------------")
#                 # In ra 500 ký tự đầu
#                 print(result.markdown[:500])
#                 print("--------------------------------------------------")
#                 print(f" Tổng độ dài: {len(result.markdown.fit_markdown)} ký tự.")
#             else:
#                 print(f" Lỗi: {result.error_message}")
# async def demo_media_and_links():
# async def demo_screenshot_and_pdf():

# --- combine
# async def demo_llm_structured_extraction_no_schema():
# async  def demo_css_structured_extraction_no_schema():
    # extraction_strategy = LLMExtractionStrategy(
    #     llm_config=LLMConfig(
    #        provider='',
    #        api_token=''
    #     ),
    #     instruction=
    #     extractt_type="schema",
    #     schema=""
    # extra_args,
    # verbose=True
    # )
    # html = ""
    # # -- trich xuất template css chuẩn để lấy thông tin
    # schema = JsonCssExtractionStrategy.generate_schema(
    #     html=html,
    #     llm_config=LLMConfig(),
    #     query=""
    # )
    # extraction_strategy = JsonCssExtractionStrategy(schema)
    # config = CrawlerRunConfig(extraction_strategy=extraction_strategy)

# ====== CONFIG ======
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyBEmmuMA1dNa28-r7UWuTxWtUvHvCy5j34")
genai.configure(api_key=GEMINI_API_KEY)
MODEL_NAME = "models/gemini-2.0-flash"

# ===== CONTENT CLEANING PATTERNS =====
JUNK_PATTERNS = [
    r"lượt xem",
    r"views today",
    r"view today",
    r"blog vexere",
    r"khám phá ngay",
    r"xem thêm",
    r"đọc thêm",
    r"số lượng người",
    r"đã xem bài viết",
    r"bài viết này",
    r"bài viết",
    r"người đã xem",
]

# -- loại bỏ các câu  thường gặp trong bài viết du lịch, các câu ngắn không ý nghĩa

def remove_junk_sentences(text: str) -> str:
    """Remove sentences containing junk patterns and very short lines."""
    if not text:
        return ""

    # Split by period and newline
    lines = re.split(r"[.\n]", text)
    clean = []

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped or len(line_stripped) < 20:
            continue

        # Check if line contains junk
        line_lower = line_stripped.lower()
        if any(pattern.lower() in line_lower for pattern in JUNK_PATTERNS):
            continue

        clean.append(line_stripped)

    return ". ".join(clean) if clean else text
# -- xử lý space
def _normalize_whitespace(text: str) -> str:
    if not text:
        return ""
    # Replace multiple whitespace/newlines with single space
    # Also clean up weird spacing before dashes/bullets
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s*-\s*", " - ", text)  # Normalize " - " spacing
    return text


def _truncate_by_words(text: str, min_words: int, max_words: int) -> str:
    """Truncate text to be within [min_words, max_words] by words.
    If shorter than min_words, return as-is (we don't hallucinate extra)."""
    if not text:
        return ""
    words = text.split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words])

# -- chọn lọc overview
def extract_semantic_overview(paragraphs: list[str], name: str) -> str:
    """Extract first paragraph that contains destination name and is substantial.
    Prioritize paragraphs that DON'T contain junk patterns."""
    if not paragraphs:
        return ""

    name_lower = name.lower()

    # Prefer paragraph containing destination name AND doesn't have junk
    for p in paragraphs:
        p_lower = p.lower()
        # Skip if contains junk patterns
        if any(pattern.lower() in p_lower for pattern in JUNK_PATTERNS):
            continue
        if name_lower in p_lower and len(p) > 80:
            return p

    # Second pass: paragraph without junk, first substantial one
    for p in paragraphs:
        p_lower = p.lower()
        if any(pattern.lower() in p_lower for pattern in JUNK_PATTERNS):
            continue
        if len(p) > 80:
            return p

    # Last resort: return first substantial paragraph
    return paragraphs[0] if paragraphs else ""

# --- get nội dung main (loại bỏ header, footer, ads)
def get_main_content_sample(html: str, limit: int = 6000) -> str:
    """
    Lấy mẫu HTML từ PHẦN CONTENT CHÍNH, không phải từ đầu file
    Bỏ qua header, nav, footer, script, style
    """
    soup = BeautifulSoup(html, "html.parser")

    # Xóa các thẻ không cần thiết trước
    for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
        tag.decompose()

    # Tìm main content area theo thứ tự ưu tiên
    main = (
        soup.find("main") or
        soup.find("article") or
        soup.find("div", id="content") or
        soup.find("div", class_="content") or
        soup.find("div", class_="entry-content") or
        soup.find("div", class_="post-content")
    )

    if main:
        # Trả về HTML của main content, limit 6000 chars
        return str(main)[:limit]

    # Fallback: lấy body nhưng bỏ header/footer
    if soup.body:
        for tag in soup.body(["header", "footer", "nav", "aside"]):
            tag.decompose()
        return str(soup.body)[:limit]

    # Worst case: trả về raw HTML
    return html[:limit]

# --- build prompt tìm keywords
def build_heading_keywords_prompt(html_sample: str) -> str:
    """
    Prompt để LLM tìm heading keywords for each section.

    Find Vietnamese keywords in headings (h2, h3) for these sections:
    - overview/introduction
    - weather/best time
    - transportation
    - food/cuisine
    - places/attractions
    - travel tips

    Return ONLY JSON:
    {
      "keywords": {
        "weather": ["thời tiết", "khí hậu", "mùa", "mùa du lịch", "thời điểm", "thời gian lý tưởng", "nhiệt độ", "lượng mưa"],
        "transportation": ["phương tiện", "di chuyển", "đi lại", "giao thông","cách đi","cách di chuyển", "đường đi", "máy bay", "xe khách","tàu"],
        "food": ["ẩm thực", "món ăn", "nhà hàng","quán ăn","đặc sản", "ăn uống", "quán ăn", "quán ngon","địa chỉ ăn","ăn gì"],
        "places": ["địa điểm", "tham quan", "danh lam","điểm đến","địa danh", "du lịch", "đi đâu", "nơi nên đến","check-in", "nơi tham quan"],
        "tips": ["kinh nghiệm", "lưu ý", "tips", "mẹo", "hướng dẫn". "bí quyết", "cẩm nang", "bí quyết"]
      }
    }

    HTML MAIN CONTENT sample (6000 chars from content area, not header):
    {content_sample}

    Return ONLY the JSON.
    """

    # Lấy sample từ MAIN CONTENT thay vì từ đầu HTML
    content_sample = get_main_content_sample(html_sample, limit=15000)

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
    "weather": ["thời tiết", "khí hậu", "mùa", "mùa du lịch", "thời điểm", "thời gian lý tưởng", "nhiệt độ", "lượng mưa"],
    "transportation": ["phương tiện", "di chuyển", "đi lại", "giao thông","cách đi","cách di chuyển", "đường đi", "máy bay", "xe khách","tàu"],
    "food": ["ẩm thực", "món ăn", "nhà hàng","quán ăn","đặc sản", "ăn uống", "quán ăn", "quán ngon","địa chỉ ăn","ăn gì"],
    "places": ["địa điểm", "tham quan", "danh lam","điểm đến","địa danh", "du lịch", "đi đâu", "nơi nên đến","check-in", "nơi tham quan"],
    "tips": ["kinh nghiệm", "lưu ý", "tips", "mẹo", "hướng dẫn". "bí quyết", "cẩm nang", "bí quyết"]
  }}
}}

HTML MAIN CONTENT sample (6000 chars from content area, not header):
{content_sample}

Return ONLY the JSON."""

def extract_text_from_block(tag) -> list[str]:
    texts: list[str] = []

    if not getattr(tag, "name", None):
        return texts

    if tag.name == "p":
        text = tag.get_text(strip=True)
        if len(text) > 20:
            texts.append(text)

    elif tag.name in ["ul", "ol"]:
        for li in tag.find_all("li", recursive=False):
            li_text = li.get_text(" ", strip=True)
            if len(li_text) > 10:
                texts.append(f"- {li_text}")

    elif tag.name == "table":
        for row in tag.find_all("tr"):
            cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"]) ]
            if cells:
                texts.append(" | ".join(cells))

    elif tag.name == "div":
        text = tag.get_text(strip=True)
        if len(text) > 30:
            texts.append(text)

    return texts

# Duyệt qua HTML.
# Tìm các thẻ Heading (H2, H3...) khớp với từ khóa AI đưa.
# Nếu khớp, lấy toàn bộ nội dung bên dưới (đến khi gặp Heading khác thì dừng).
def extract_content_with_beautifulsoup(html: str, keywords: dict) -> dict:
    """BeautifulSoup extract content theo keywords chỉ từ MAIN CONTENT.
    Ưu tiên các vùng main/article/content, bỏ header/nav/footer/sidebar."""
    print(" BeautifulSoup đang extract content...")

    soup = BeautifulSoup(html, 'html.parser')

    # Xóa các thẻ không cần thiết trước (script, style, iframe, svg...)
    for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
        tag.decompose()

    # Tìm main content area giống logic get_main_content_sample
    content_area = (
        soup.find("main") or
        soup.find("article") or
        soup.find("div", id="content") or
        soup.find("div", class_="content") or
        soup.find("div", class_="entry-content") or
        soup.find("div", class_="post-content") or
        soup.body
    )

    extracted = {
        "name": "",
        "overview": "",
        "weather_and_best_time": "",
        "transportation": "",
        "culinary_highlights": "",
        "must_visit_locations": "",
        "travel_tips": ""
    }

    # Extract title trong vùng main content
    title = content_area.find('h1') if content_area else None
    if not title and content_area:
        title = content_area.find('h2', class_='head')
    if title:
        extracted["name"] = title.get_text(strip=True)
        print(f"   ✓ Title: {extracted['name'][:50]}")

    # Extract overview: vài đoạn p đầu trong main content
    if content_area:
        first_paras = content_area.find_all('p', limit=5)
    else:
        first_paras = []

    overview_texts = []
    for p in first_paras:
        text = p.get_text(strip=True)
        if len(text) > 50:  # Skip short paragraphs
            overview_texts.append(text)

    # Use semantic overview extraction: prefer paragraph with destination name
    # Và loại bỏ junk ngay từ đây
    if overview_texts and extracted["name"]:
        candidate = extract_semantic_overview(overview_texts, extracted["name"])
        # Clean junk ngay lập tức
        candidate = remove_junk_sentences(candidate)
        extracted["overview"] = candidate
    elif overview_texts:
        candidate = overview_texts[0]
        candidate = remove_junk_sentences(candidate)
        extracted["overview"] = candidate

    if extracted["overview"]:
        print(f"   ✓ Overview (raw): {len(extracted['overview'])} chars")

    if not content_area:
        return extracted

    # Extract sections by keywords CHỈ trong main content
    # Tìm TẤT CẢ heading từ h2 đến h5, strong, b (để bắt được h3, h4, strong)
    all_headings = content_area.find_all(['h2', 'h3', 'h4', 'h5', 'strong', 'b'])

    for heading in all_headings:
        heading_text = heading.get_text().lower()

        # Match keywords to fields
        matched_field = None

        for kw in keywords.get("weather", []):
            if kw in heading_text:
                matched_field = "weather_and_best_time"
                break

        if not matched_field:
            for kw in keywords.get("transportation", []):
                if kw in heading_text:
                    matched_field = "transportation"
                    break

        if not matched_field:
            for kw in keywords.get("food", []):
                if kw in heading_text:
                    matched_field = "culinary_highlights"
                    break

        if not matched_field:
            for kw in keywords.get("places", []):
                if kw in heading_text:
                    matched_field = "must_visit_locations"
                    break

        if not matched_field:
            for kw in keywords.get("tips", []):
                if kw in heading_text:
                    matched_field = "travel_tips"
                    break

        # Extract content after matched heading
        if matched_field and not extracted[matched_field]:
            content_parts: list[str] = []

            # Get all siblings until next heading trong main content
            # CUT BY WORD COUNT, NOT BLOCK COUNT
            current = heading.find_next_sibling()
            while current:
                # Dừng khi gặp heading tiếp
                current_tag_name = getattr(current, "name", None)
                if current_tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    break

                # Extract content từ current element
                block_texts = extract_text_from_block(current)
                for t in block_texts:
                    content_parts.append(t)

                # Check word count across all parts
                total_words = sum(len(t.split()) for t in content_parts)
                if total_words >= 220:  # Stop when reaching ~220 words
                    break

                current = current.find_next_sibling()

            extracted[matched_field] = "\n\n".join(content_parts)
            if extracted[matched_field]:
                word_count = sum(len(t.split()) for t in content_parts)
                print(f"    {matched_field} (raw): {len(extracted[matched_field])} chars, ~{word_count} words")
            else:
                print(f"    {matched_field}: No content found after heading")

    return extracted

# lấy danh sách từ khóa JSON
async def llm_get_heading_keywords(html_content: str) -> dict:
    """
    LLM chỉ tìm keywords, KHÔNG extract content
    """
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = build_heading_keywords_prompt(html_content)

    print(" LLM đang tìm heading keywords...")

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Clean markdown
        if text.startswith("```json"):
            text = text[7:-3].strip()
        elif text.startswith("```"):
            text = text[3:-3].strip()

        keywords = json.loads(text)
        print(" Keywords đã được tìm thấy!")
        return keywords.get("keywords", {})

    except Exception as e:
        print(f" LLM failed: {e}, using default keywords")
        return {
            "weather": ["thời tiết", "khí hậu", "thời gian", "mùa"],
            "transportation": ["phương tiện", "di chuyển", "đi lại", "xe"],
            "food": ["ẩm thực", "món ăn", "nhà hàng", "ăn uống"],
            "places": ["địa điểm", "tham quan", "danh lam", "du lịch"],
            "tips": ["kinh nghiệm", "lưu ý", "tips", "mẹo"]
        }

async def extract_hub_info(url: str) -> dict:
    """Crawl 1 URL và trả về JSON hub_info cho đúng URL truyền vào."""
    async with AsyncWebCrawler(verbose=True) as crawler:
        result = await crawler.arun(
            url=url,
            cache_mode=CacheMode.BYPASS
        )

        if not result.success:
            raise Exception(f"Crawl failed: {result.error_message}")

        html_content = result.html
        print(f"  fetch HTML ({len(html_content)} chars) từ: {url}")

        # ===== BƯỚC 2: LLM TÌM KEYWORDS =====
        print(f"\n{'='*60}")
        print(f" BƯỚC 2: LLM tìm heading keywords (lightweight)")
        print(f"{'='*60}")

        keywords = await llm_get_heading_keywords(html_content)
        print(f"Keywords: {json.dumps(keywords, ensure_ascii=False)[:500]}")

        # ===== BƯỚC 3: BEAUTIFULSOUP EXTRACT =====
        print(f"\n{'='*60}")
        print(f" BƯỚC 3: BeautifulSoup extract content")
        print(f"{'='*60}")

        raw_extracted = extract_content_with_beautifulsoup(html_content, keywords)
        print(f" Đã extract {len([v for v in raw_extracted.values() if v])} fields có nội dung")

        # ===== BƯỚC 4: CLEANING + NORMALIZATION =====
        print(f"\n{'='*60}")
        print(f" BƯỚC 4: Content cleaning & normalization")
        print(f"{'='*60}")

        name = raw_extracted.get("name", "Unknown Destination")
        overview_raw = raw_extracted.get("overview", "")

        # Step 1: Remove junk sentences from all fields
        overview_raw = remove_junk_sentences(overview_raw)
        weather_raw = remove_junk_sentences(raw_extracted.get("weather_and_best_time", ""))
        transportation_raw = remove_junk_sentences(raw_extracted.get("transportation", ""))
        locations_raw = remove_junk_sentences(raw_extracted.get("must_visit_locations", ""))
        food_raw = remove_junk_sentences(raw_extracted.get("culinary_highlights", ""))
        tips_raw = remove_junk_sentences(raw_extracted.get("travel_tips", ""))

        # Step 2: Normalize whitespace
        overview_clean = _normalize_whitespace(overview_raw)
        weather_clean = _normalize_whitespace(weather_raw)
        transportation_clean = _normalize_whitespace(transportation_raw)
        locations_clean = _normalize_whitespace(locations_raw)
        food_clean = _normalize_whitespace(food_raw)
        tips_clean = _normalize_whitespace(tips_raw)

        print(f" Cleaned content:")
        print(f"   - overview: {len(overview_clean)} chars")
        print(f"   - weather: {len(weather_clean)} chars")
        print(f"   - transportation: {len(transportation_clean)} chars")
        print(f"   - locations: {len(locations_clean)} chars")
        print(f"   - food: {len(food_clean)} chars")
        print(f"   - tips: {len(tips_clean)} chars")

        content_dict = {
            "overview": overview_clean,
            "weather": weather_clean,
            "locations": locations_clean,
            "food": food_clean
        }

        metadata = extract_metadata_from_content(name, overview_clean, content_dict)

        print(f"\n{'='*60}")
        print(f" BƯỚC 5: Format JSON final với metadata")
        print(f"{'='*60}")

        print(f" Metadata detected:")
        print(f"   - Region: {metadata['region']}")
        print(f"   - Province: {metadata['province']}")
        print(f"   - Airport: {metadata['airport']}")
        print(f"   - Climate: {metadata['climate_tag']}")
        print(f"   - Vibe: {metadata['vibe_tag']}")

        # Step 3: Apply word-length constraints per your spec
        overview_final = _truncate_by_words(overview_clean, 120, 250)
        weather_final = _truncate_by_words(weather_clean, 120, 200)
        transportation_final = _truncate_by_words(transportation_clean, 80, 150)
        locations_final = _truncate_by_words(locations_clean, 150, 300)
        food_final = _truncate_by_words(food_clean, 120, 200)
        tips_final = _truncate_by_words(tips_clean, 80, 150)

        print(f" After truncation:")
        print(f"   - overview: {len(overview_final.split())} words")
        print(f"   - weather: {len(weather_final.split())} words")
        print(f"   - transportation: {len(transportation_final.split())} words")
        print(f"   - locations: {len(locations_final.split())} words")
        print(f"   - food: {len(food_final.split())} words")
        print(f"   - tips: {len(tips_final.split())} words")

        # Step 4: Build text_content as comprehensive hub summary
        # Combine overview + snippets from weather/locations/food
        summary_parts = [overview_final]

        if weather_final:
            summary_parts.append(_truncate_by_words(weather_final, 0, 100))
        if locations_final:
            summary_parts.append(_truncate_by_words(locations_final, 0, 100))
        if food_final:
            summary_parts.append(_truncate_by_words(food_final, 0, 100))

        text_content_raw = " ".join(summary_parts)
        text_content = _truncate_by_words(text_content_raw, 200, 600)

        # Final cleanup
        text_content = remove_junk_sentences(text_content)
        text_content = _normalize_whitespace(text_content)
        text_content = _truncate_by_words(text_content, 200, 600)

        # Sinh hub_id động dựa trên tên địa điểm (name)
        def simple_slug(text: str) -> str:
            return text.strip().lower().replace(" ", "_") if text else "unknown"

        hub_id = simple_slug(name)

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
                "last_updated": datetime.now().strftime("%Y-%m-%d")
            },
            "text_content": text_content,
            "content": {
                "overview": overview_final,
                "weather_and_best_time": weather_final,
                "transportation": transportation_final,
                "must_visit_locations": locations_final,
                "culinary_highlights": food_final,
                "travel_tips": tips_final
            }
        }

        print(f" final")
        return final_data


# 4. Entry point
if __name__ == "__main__":
    # mỗi lần chạy main, chỉ dùng đúng URL này, không bị dính URL cũ
    url = "https://blog.vexere.com/du-lich-da-lat-tu-tuc/"
    hub_info = asyncio.run(extract_hub_info(url))

    print("\n================ KẾT QUẢ JSON =================\n")
    print(json.dumps(hub_info, ensure_ascii=False, indent=2))