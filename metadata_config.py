# Metadata mapping cho các tỉnh thành Việt Nam
VIETNAM_LOCATIONS = {
    # Tây Nguyên
    "lâm đồng": {"province": "Lâm Đồng", "region": "Tây Nguyên", "airport": "Sân bay Liên Khương "},
    "đà lạt": {"province": "Lâm Đồng", "region": "Tây Nguyên", "airport": "Sân bay Liên Khương "},
    "gia lai": {"province": "Gia Lai", "region": "Tây Nguyên", "airport": "Sân bay Pleiku ("},
    "đắk lắk": {"province": "Đắk Lắk", "region": "Tây Nguyên", "airport": "Sân bay Buôn Ma Thuột "},
    "buôn ma thuột": {"province": "Đắk Lắk", "region": "Tây Nguyên", "airport": "Sân bay Buôn Ma Thuột "},

    # Miền Bắc
    "hà nội": {"province": "Hà Nội", "region": "Miền Bắc", "airport": "Sân bay Nội Bài "},
    "hải phòng": {"province": "Hải Phòng", "region": "Miền Bắc", "airport": "Sân bay Cát Bi "},
    "quảng ninh": {"province": "Quảng Ninh", "region": "Miền Bắc", "airport": "Sân bay Vân Đồn "},
    "hạ long": {"province": "Quảng Ninh", "region": "Miền Bắc", "airport": "Sân bay Vân Đồn "},
    "sapa": {"province": "Lào Cai", "region": "Miền Bắc", "airport": "Sân bay Nội Bài "},
    "lào cai": {"province": "Lào Cai", "region": "Miền Bắc", "airport": "Sân bay Nội Bài )"},
    "ninh bình": {"province": "Ninh Bình", "region": "Miền Bắc", "airport": "Sân bay Nội Bài "},

    # Miền Trung
    "huế": {"province": "Thừa Thiên Huế", "region": "Miền Trung", "airport": "Sân bay Phú Bài (HUI)"},
    "đà nẵng": {"province": "Đà Nẵng", "region": "Miền Trung", "airport": "Sân bay Đà Nẵng (DAD)"},
    "quảng nam": {"province": "Quảng Nam", "region": "Miền Trung", "airport": "Sân bay Đà Nẵng (DAD)"},
    "hội an": {"province": "Quảng Nam", "region": "Miền Trung", "airport": "Sân bay Đà Nẵng (DAD)"},
    "nha trang": {"province": "Khánh Hòa", "region": "Miền Trung", "airport": "Sân bay Cam Ranh (CXR)"},
    "khánh hòa": {"province": "Khánh Hòa", "region": "Miền Trung", "airport": "Sân bay Cam Ranh (CXR)"},
    "quy nhơn": {"province": "Bình Định", "region": "Miền Trung", "airport": "Sân bay Phù Cát (UIH)"},
    "phú yên": {"province": "Phú Yên", "region": "Miền Trung", "airport": "Sân bay Tuy Hòa (TBB)"},

    # Miền Nam
    "hồ chí minh": {"province": "TP. Hồ Chí Minh", "region": "Miền Nam", "airport": "Sân bay Tân Sơn Nhất (SGN)"},
    "sài gòn": {"province": "TP. Hồ Chí Minh", "region": "Miền Nam", "airport": "Sân bay Tân Sơn Nhất (SGN)"},
    "tp.hcm": {"province": "TP. Hồ Chí Minh", "region": "Miền Nam", "airport": "Sân bay Tân Sơn Nhất (SGN)"},
    "vũng tàu": {"province": "Bà Rịa - Vũng Tàu", "region": "Miền Nam", "airport": "Sân bay Tân Sơn Nhất (SGN)"},
    "phú quốc": {"province": "Kiên Giang", "region": "Miền Nam", "airport": "Sân bay Phú Quốc (PQC)"},
    "kiên giang": {"province": "Kiên Giang", "region": "Miền Nam", "airport": "Sân bay Phú Quốc (PQC)"},
    "cần thơ": {"province": "Cần Thơ", "region": "Miền Nam", "airport": "Sân bay Cần Thơ (VCA)"},
    "đồng bằng sông cửu long": {"province": "N/A", "region": "Miền Nam", "airport": "Sân bay Cần Thơ (VCA)"},
    "mekong": {"province": "N/A", "region": "Miền Nam", "airport": "Sân bay Cần Thơ (VCA)"},
}

# Climate tags keywords
CLIMATE_KEYWORDS = {
    "Mát mẻ": ["mát mẻ", "se lạnh", "khí hậu ôn hòa", "sương mù", "mát lạnh", "ôn đới"],
    "Nóng": ["nắng", "nóng", "nhiệt đới", "khí hậu nóng"],
    "Mưa nhiều": ["mưa", "gió mùa", "mưa nhiều", "ẩm ướt"],
    "Khô hanh": ["khô", "hanh khô", "ít mưa"],
    "Ôn hòa": ["ôn hòa", "dễ chịu", "khí hậu dễ chịu"],
    "Nhiệt đới": ["nhiệt đới", "nóng ẩm", "nắng gắt"],
}

# Vibe tags keywords
VIBE_KEYWORDS = {
    "Lãng mạn": ["lãng mạn", "cặp đôi", "honeymoon", "tình yêu"],
    "Yên bình": ["yên bình", "thanh bình", "thư giãn", "nghỉ dưỡng", "tĩnh lặng"],
    "Phiêu lưu": ["phiêu lưu", "mạo hiểm", "trekking", "leo núi", "khám phá"],
    "Thiên nhiên": ["thiên nhiên", "núi non", "thác", "rừng", "biển", "hồ"],
    "Check-in": ["check-in", "sống ảo", "instagram", "chụp ảnh"],
    "Ẩm thực": ["ẩm thực", "món ăn", "đặc sản", "food", "culinary"],
    "Văn hóa": ["văn hóa", "lịch sử", "di sản", "truyền thống"],
    "Nghỉ dưỡng": ["nghỉ dưỡng", "resort", "spa", "relax"],
    "Gia đình": ["gia đình", "family", "trẻ em", "kid-friendly"],
    "Biển đảo": ["biển", "đảo", "beach", "bãi biển", "bờ biển"],
    "Núi rừng": ["núi", "rừng", "đồi", "cao nguyên"],
    "Thành phố": ["thành phố", "đô thị", "city", "shopping"],
}

