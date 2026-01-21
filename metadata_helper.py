"""
Helper functions để tự động detect metadata và tags từ nội dung
Sử dụng data-driven approach thay vì hardcode
"""

from metadata_config import VIETNAM_LOCATIONS, CLIMATE_KEYWORDS, VIBE_KEYWORDS


def detect_location_metadata(content: str) -> dict:
    """
    Tự động detect region, province, airport từ nội dung

    Args:
        content: Nội dung text để phân tích (lowercase)

    Returns:
        dict với keys: region, province, airport
    """
    content_lower = content.lower()

    # Tìm location match đầu tiên
    for location_keyword, location_data in VIETNAM_LOCATIONS.items():
        if location_keyword in content_lower:
            return {
                "region": location_data["region"],
                "province": location_data["province"],
                "airport": location_data["airport"]
            }

    # Fallback nếu không tìm được
    return {
        "region": "N/A",
        "province": "N/A",
        "airport": "N/A"
    }


def detect_climate_tags(content: str) -> list:
    """
    Tự động detect climate tags từ nội dung dựa trên keywords

    Args:
        content: Nội dung text để phân tích (lowercase)

    Returns:
        list of climate tags
    """
    content_lower = content.lower()
    detected_tags = []

    for tag_name, keywords in CLIMATE_KEYWORDS.items():
        if any(kw in content_lower for kw in keywords):
            detected_tags.append(tag_name)

    # Loại bỏ duplicate và return
    return list(set(detected_tags)) if detected_tags else ["N/A"]


def detect_vibe_tags(content: str) -> list:
    """
    Tự động detect vibe tags từ nội dung dựa trên keywords

    Args:
        content: Nội dung text để phân tích (lowercase)

    Returns:
        list of vibe tags
    """
    content_lower = content.lower()
    detected_tags = []

    for tag_name, keywords in VIBE_KEYWORDS.items():
        if any(kw in content_lower for kw in keywords):
            detected_tags.append(tag_name)

    # Loại bỏ duplicate và return
    return list(set(detected_tags)) if detected_tags else ["Du lịch"]


def extract_metadata_from_content(name: str, overview: str, all_content: dict = None) -> dict:
    """
    Hàm tổng hợp để extract tất cả metadata từ nội dung

    Args:
        name: Tên địa điểm
        overview: Nội dung tổng quan
        all_content: Dict chứa tất cả nội dung các fields (optional)

    Returns:
        dict chứa: region, province, airport, climate_tag, vibe_tag
    """
    # Kết hợp tất cả nội dung để phân tích
    full_content = name + " " + overview
    if all_content:
        full_content += " " + " ".join(all_content.values())

    # Detect location metadata
    location_data = detect_location_metadata(full_content)

    # Detect tags
    climate_tags = detect_climate_tags(full_content)
    vibe_tags = detect_vibe_tags(full_content)

    return {
        "region": location_data["region"],
        "province": location_data["province"],
        "airport": location_data["airport"],
        "climate_tag": climate_tags,
        "vibe_tag": vibe_tags
    }

