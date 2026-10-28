from datetime import datetime, date, time, timedelta
import itertools
import os
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any, Optional

import geonamescache
import pandas as pd
import pytz
import streamlit as st
import swisseph as swe
from timezonefinder import TimezoneFinder

# ==================== إعدادات Swiss Ephemeris ====================
swe.set_ephe_path('')  # استخدام وضع Moshier الافتراضي للتقويم الفلكي الدقيق

# ==================== هيكل البيانات الجغرافية ====================
@dataclass
class City:
    geonameid: str
    name: str
    country_code: str
    latitude: float
    longitude: float
    admin1: str
    population: int

# ==================== تحميل البيانات الجغرافية تلقائياً ====================

@st.cache_resource
def load_cities() -> List[City]:
    gc = geonamescache.GeonamesCache()
    cities_list = []
    for city_id, city_data in gc.get_cities().items():
        if city_data.get("population", 0) >= 0:
            cities_list.append(
                City(
                    geonameid=city_id,
                    name=city_data.get("name", ""),
                    country_code=city_data.get("countrycode", ""),
                    latitude=city_data.get("latitude", 0.0),
                    longitude=city_data.get("longitude", 0.0),
                    admin1=city_data.get("admin1code", ""),
                    population=city_data.get("population", 0),
                )
            )
    return cities_list

@st.cache_resource
def load_countries() -> Dict[str, Dict[str, Any]]:
    gc = geonamescache.GeonamesCache()
    return gc.get_countries()

def get_sorted_countries() -> Tuple[Dict[str, str], List[str]]:
    countries_data = load_countries()
    country_map = {c_info["name"]: c_code for c_code, c_info in countries_data.items()}
    sorted_country_names = sorted(list(country_map.keys()))
    return country_map, sorted_country_names

def get_cities_by_country(country_code: str) -> List[City]:
    cities = load_cities()
    filtered_cities = [c for c in cities if c.country_code == country_code]
    return sorted(
        filtered_cities,
        key=lambda c: c.population,
        reverse=True,
    )

def get_utc_julian_day(date_obj: date, time_obj: time, tz_str: str) -> float:
    local_tz = pytz.timezone(tz_str)
    dt = datetime.combine(date_obj, time_obj)
    local_dt = local_tz.localize(dt)
    utc_dt = local_dt.astimezone(pytz.utc)
    return swe.julday(
        utc_dt.year,
        utc_dt.month,
        utc_dt.day,
        utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0,
    )

# ==========================================
# 1. جدول الحروف الأبجدية الكامل (الجمل الكبير)
# ==========================================
ABJAD_DICT = {
    'ا': 1, 'أ': 1, 'إ': 1, 'آ': 1,
    'ب': 2,
    'ج': 3,
    'د': 4,
    'ه': 5, 'ة': 5,
    'و': 6,
    'ز': 7,
    'ح': 8,
    'ط': 9,
    'ي': 10, 'ى': 10,
    'ك': 20,
    'ل': 30,
    'م': 40,
    'ن': 50,
    'س': 60,
    'ع': 70,
    'ف': 80,
    'ص': 90,
    'ق': 100,
    'ر': 200,
    'ش': 300,
    'ت': 400,
    'ث': 500,
    'خ': 600,
    'ذ': 700,
    'ض': 800,
    'ظ': 900,
    'غ': 1000
}

ZODIAC_MAP = {
    1: 'حمل', 2: 'ثور', 3: 'جوزاء', 4: 'سرطان',
    5: 'أسد', 6: 'عذراء', 7: 'ميزان', 8: 'عقرب',
    9: 'قوس', 10: 'جدي', 11: 'دلو', 12: 'حوت'
}

ZODIAC_SIGNS = [
    "الحمل", "الثور", "الجوزاء", "السرطان", "الأسد", "العذراء",
    "الميزان", "العقرب", "القوس", "الجدي", "الدلو", "الحوت"
]

SIGN_RULERS = {
    "الحمل": "المريخ", "الثور": "الزهرة", "الجوزاء": "عطارد", "السرطان": "القمر",
    "الأسد": "الشمس", "العذراء": "عطارد", "الميزان": "الزهرة", "العقرب": "المريخ",
    "القوس": "المشتري", "الجدي": "زحل", "الدلو": "أورانوس", "الحوت": "نبتون"
}

BODIES = {
    "الشمس": swe.SUN,
    "القمر": swe.MOON,
    "عطارد": swe.MERCURY,
    "الزهرة": swe.VENUS,
    "المريخ": swe.MARS,
    "المشتري": swe.JUPITER,
    "زحل": swe.SATURN,
    "أورانوس": swe.URANUS,
    "نبتون": swe.NEPTUNE,
    "بلوتو": swe.PLUTO,
    "راهو": swe.TRUE_NODE,
}

# قائمة النجوم الثابتة التأثيرية الكبرى ومواقعها الفلكية المقربة
MAJOR_FIXED_STARS = {
    "الغول (Algol)": {"lon": 56.2, "nature": "نحس شديد والسحر الأسود"},
    "الدبران (Aldebaran)": {"lon": 69.8, "nature": "خومات وصراعات حادة"},
    "الشعرى اليمانية (Sirius)": {"lon": 104.2, "nature": "قوة طاقية وروحانية عالية"},
    "قلب الأسد (Regulus)": {"lon": 150.1, "nature": "سلطة وتسلط وتسليط"},
    "السماك الأعزل (Spica)": {"lon": 204.0, "nature": "حماية أو تحصين"},
    "قلب العقرب (Antares)": {"lon": 249.8, "nature": "أذى ناري ووساوس وسموم"},
    "النسر الواقع (Vega)": {"lon": 285.3, "nature": "أعمال خفية وطلاسم"},
    "فم الحوت (Fomalhaut)": {"lon": 343.9, "nature": "أعمال سحرية مرتبطة بالماء والمحيطات"}
}

DAYS_PLANETS = {
    'احد': {'planet': 'شمس', 'day_name': 'احد'},
    'اثنين': {'planet': 'قمر', 'day_name': 'اثنين'},
    'ثلاثاء': {'planet': 'مريخ', 'day_name': 'ثلاثاء'},
    'اربعاء': {'planet': 'عطارد', 'day_name': 'اربعاء'},
    'خميس': {'planet': 'مشتري', 'day_name': 'خميس'},
    'جمعه': {'planet': 'زهره', 'day_name': 'جمعه'},
    'سبت': {'planet': 'زحل', 'day_name': 'سبت'}
}

def calculate_name_value(name_part, is_composite_first_box=False):
    total = 0
    name_part = name_part.strip()
    if not name_part:
        return 0
    for i, char in enumerate(name_part):
        if char in ['ء']:
            continue
        if char == 'ة':
            if is_composite_first_box and i == len(name_part) - 1:
                total += 400
            else:
                total += 5
        elif char in ABJAD_DICT:
            total += ABJAD_DICT[char]
    return total

def reduce_to_12(number):
    while number > 12:
        number -= 12
    if number <= 0:
        number = ((number - 1) % 12) + 1
    return number

# ==========================================
# قاموس الأنوية الفلكية الكامل (مصحح بالشروط المنطقية)
# ==========================================
def get_current_naw(check_date=None):
    """تحديد النوء الفلكي الحالي بناءً على التاريخ بدقة متناهية"""
    if check_date is None:
        check_date = datetime.now()
    
    month = check_date.month
    day = check_date.day
    
    if (month == 5 and 12 <= day < 25):
        return "ثريا"
    elif (month == 5 and day >= 25) or (month == 6 and day < 7):
        return "ثريا"
    elif (month == 6 and 7 <= day < 20):
        return "ثريا"
    elif (month == 6 and day >= 20) or (month == 7 and day < 3):
        return "تويبع"
    elif (month == 7 and 3 <= day < 16):
        return "جوزاء"
    elif (month == 7 and 16 <= day < 29):
        return "جوزاء"
    elif (month == 7 and day >= 29) or (month == 8 and day < 11):
        return "مرزم"
    elif (month == 8 and 11 <= day < 24):
        return "كليبين"
    elif (month == 8 and day >= 24) or (month == 9 and day < 6):
        return "سهيل"
    elif (month == 9 and 6 <= day < 20):
        return "سهيل"
    elif (month == 9 and day >= 20) or (month == 10 and day < 3):
        return "سهيل"
    elif (month == 10 and 3 <= day < 16):
        return "سهيل"
    elif (month == 10 and 16 <= day < 29):
        return "وسم"
    elif (month == 10 and day >= 29) or (month == 11 and day < 11):
        return "وسم"
    elif (month == 11 and 11 <= day < 24):
        return "وسم"
    elif (month == 11 and day >= 24) or (month == 12 and day < 7):
        return "وسم"
    elif (month == 12 and 7 <= day < 20):
        return "مربعانيه"
    elif (month == 12 and day >= 20) or (month == 1 and day < 2):
        return "مربعانيه"
    elif (month == 1 and 2 <= day < 15):
        return "مربعانيه"
    elif (month == 1 and 15 <= day < 28):
        return "شبط"
    elif (month == 1 and day >= 28) or (month == 2 and day < 10):
        return "شبط"
    elif (month == 2 and 10 <= day < 23):
        return "عقارب"
    elif (month == 2 and day >= 23) or (month == 3 and day < 8):
        return "عقارب"
    elif (month == 3 and 8 <= day < 21):
        return "عقارب"
    elif (month == 3 and day >= 21) or (month == 4 and day < 3):
        return "حميمين"
    elif (month == 4 and 3 <= day < 16):
        return "حميمين"
    elif (month == 4 and 16 <= day < 29):
        return "ذراعين"
    else:
        return "ذراعين"

# ==========================================
# 2. محرك قراءة الخريطة الفلكية وتحديد صفات الفاعل والنجوم الثابتة والتوقيت والعلاج
# ==========================================
class AutoChartReader:
    def __init__(self, jd: float, lat: float, lng: float):
        self.jd = jd
        self.lat = lat
        self.lng = lng
        self.planets_data = []
        self.ascendant_sign_idx = 0
        self.ascendant_lon = 0.0
        self._calculate()

    def _calculate(self):
        flags = swe.FLG_SWIEPH | swe.FLG_SPEED
        cusps, ascmc = swe.houses(self.jd, self.lat, self.lng, b'W')
        self.ascendant_lon = ascmc[0]
        self.ascendant_sign_idx = int(self.ascendant_lon // 30)

        for b_name, b_id in BODIES.items():
            pos, _ = swe.calc_ut(self.jd, b_id, flags)
            lon = pos[0]
            sign_idx = int(lon // 30)
            house_num = ((sign_idx - self.ascendant_sign_idx) % 12) + 1
            self.planets_data.append({
                "body": b_name,
                "lon": lon,
                "sign": ZODIAC_SIGNS[sign_idx],
                "sign_idx": sign_idx,
                "house": house_num,
                "is_retro": pos[3] < 0,
                "speed": pos[3]
            })

        rahu = next((p for p in self.planets_data if p["body"] == "راهو"), None)
        if rahu:
            ketu_lon = (rahu["lon"] + 180) % 360
            ketu_sign_idx = int(ketu_lon // 30)
            ketu_house = ((ketu_sign_idx - self.ascendant_sign_idx) % 12) + 1
            self.planets_data.append({
                "body": "كيتو",
                "lon": ketu_lon,
                "sign": ZODIAC_SIGNS[ketu_sign_idx],
                "sign_idx": ketu_sign_idx,
                "house": ketu_house,
                "is_retro": True,
                "speed": -0.05
            })

    def check_fixed_stars(self) -> List[str]:
        """فحص اقتران الكواكب الحاكمة أو المنحوسة بالنجوم الثابتة الخطرة"""
        star_clues = []
        for p in self.planets_data:
            if p["house"] in [1, 6, 8, 12]:
                for star_name, star_info in MAJOR_FIXED_STARS.items():
                    diff = abs(p["lon"] - star_info["lon"])
                    if diff > 180:
                        diff = 360 - diff
                    if diff <= 1.5:  # جُرم اقتران 1.5 درجة
                        star_clues.append(
                            f"⭐ **اقتران نجمي مؤثر:** كوكب ({p['body']}) مقترن بالنجم الثابت **[{star_name}]** (على درجة {star_info['lon']}°). "
                            f"الدلالة التراثية: {star_info['nature']}."
                        )
        return star_clues

    def estimate_damage_timing(self) -> str:
        """حساب وتفحص هل الأذية قديمة أم جديدة، وتحديد نطاق بدء الأذى بالأشهر بدقة فلكية وتوقيت وقوعها"""
        h12_sign_idx = (self.ascendant_sign_idx + 11) % 12
        h12_sign = ZODIAC_SIGNS[h12_sign_idx]
        h12_ruler = SIGN_RULERS.get(h12_sign)
        ruler_p = next((p for p in self.planets_data if p["body"] == h12_ruler), None)

        if not ruler_p:
            return "توقيت الأذية: غير محدد بدقة لكتمان حركة الحاكم."

        # حساب المسافة القوسية بين حاكم 12 والطالع
        arc_diff = abs(ruler_p["lon"] - self.ascendant_lon)
        if arc_diff > 180:
            arc_diff = 360 - arc_diff

        cardinal_signs = ["الحمل", "السرطان", "الميزان", "الجدي"]
        fixed_signs = ["الثور", "الأسد", "العقرب", "الدلو"]
        mutable_signs = ["الجوزاء", "العذراء", "القوس", "الحوت"]

        # حساب نطاق الأشهر بدقة استناداً إلى حركة الحاكم والبرج
        calculated_months = int((arc_diff / 30) * 12) + 1
        if calculated_months > 24:
            calculated_months = calculated_months % 24 + 1

        if h12_sign in cardinal_signs:
            status_type = "أذية جديدة كلياً (طارئة)"
            timing_details = f"حدثت خلال الأيام أو الأسابيع القليلة الماضية وتحديداً منذ حوالي {int(arc_diff % 30) + 1} أيام إلى شهر كحد أقصى."
        elif h12_sign in fixed_signs:
            status_type = "أذية قديمة ومتأصلة ومستمرة"
            timing_details = f"الأذية قديمة وتراكمية ومستمرة منذ عدة أشهر طويلة أو سنوات (نطاق البدء منذ حوالي {int(arc_diff / 10) + 1} إلى {int(arc_diff / 5) + 2} أشهر أو أكثر)."
        else:
            status_type = "أذية متجددة (متوسطة الحداثة)"
            timing_details = f"بدأت الأذية قبل نطاق زمني يقدر بـ {max(1, calculated_months - 1)} إلى {calculated_months + 1} أشهر تقريباً، وهي تتجدد دورياً."

        return f"⏱️ **فحص توقيت الأذية (قديمة أم جديدة):** الحالة تصنف كـ **[{status_type}]**. نطاق بدء الأذى بالقديم أو الجديد: {timing_details} (المسافة القوسية للحاكم: {arc_diff:.2f}°)."

    def analyze_magic_perpetrator(self) -> Dict[str, Any]:
        h12_sign_idx = (self.ascendant_sign_idx + 11) % 12
        h12_sign = ZODIAC_SIGNS[h12_sign_idx]
        h12_ruler = SIGN_RULERS.get(h12_sign)
        
        ruler_p = next((p for p in self.planets_data if p["body"] == h12_ruler), None)
        h12_ruler_house = ruler_p["house"] if ruler_p else 12

        planets_in_12 = [p["body"] for p in self.planets_data if p["house"] == 12]
        planets_in_6 = [p["body"] for p in self.planets_data if p["house"] == 6]
        planets_in_8 = [p["body"] for p in self.planets_data if p["house"] == 8]

        saturn_in_affliction = any(p["body"] == "زحل" and p["house"] in [6, 8, 12] for p in self.planets_data)
        mars_in_affliction = any(p["body"] == "المريخ" and p["house"] in [6, 8, 12] for p in self.planets_data)
        ketu_in_affliction = any(p["body"] == "كيتو" and p["house"] in [6, 8, 12] for p in self.planets_data)
        neptune_in_affliction = any(p["body"] == "نبتون" and p["house"] in [6, 8, 12] for p in self.planets_data)

        # 1. تحديد الجنس (رجل / امرأة)
        feminine_signs = ["الثور", "السرطان", "العذراء", "العقرب", "الجدي", "الحوت"]
        feminine_planets = ["القمر", "الزهرة", "نبتون"]
        is_fem = (h12_ruler in feminine_planets) or (h12_sign in feminine_signs) or any(p in feminine_planets for p in planets_in_12)
        perpetrator_gender = "امرأة (أنثى)" if is_fem else "رجل (ذكر)"

        # 2. تحديد الفئة العمرية
        if h12_ruler == "زحل" or saturn_in_affliction:
            perpetrator_age = "كبير السن (فوق 50 سنة - طاقة زحل الشائخة)"
        elif h12_ruler in ["المشتري", "المريخ", "الشمس"] or mars_in_affliction:
            perpetrator_age = "في منتصف العمر (بين 30 و 50 سنة - طاقة النضج والقوة)"
        else:
            perpetrator_age = "في سن الشباب (تحت 30 سنة - طاقة سريعة أو طائشة)"

        # 3. صلة القرابة ودرجتها بالدم أو الصهر بدقة تامة
        kinship_degree_text = "لا يوجد صلة قرابة بالدم (شخص خارجي / جار / زميل / معرفة خارجية)"
        is_relative_text = "ليس بالضرورة من الأقارب المباشرين"

        if h12_ruler_house in [3, 4]:
            kinship_degree_text = "من المحيط اليومي المباشر(قريب، أو شخص في محيط الحركة اليومية أو الإخوة، الأخوات، الأب، الأم، أو أفراد العائلة في نفس المسكن)."
            is_relative_text = "محتمل أن يكون قريباً غير مباشر أو شخصاً من المحيط اليومي أو الأقارب من الدرجة الأولى (1)"
        elif h12_ruler_house in [6]:
            kinship_degree_text = "من الدرجة الثانية (2) بالدم (الأعمام، العمات، الأخوال، الخالات)."
            is_relative_text = "نعم، الفاعل من الأقارب من الدرجة الثانية (2)"
        elif h12_ruler_house in [5, 11]:
            kinship_degree_text = "من الدرجة الثالثة (3) بالدم (أبناء العمومة، أبناء الأخوال، أو أصدقاء مقربون جداً بمثابة الأقارب)."
            is_relative_text = "نعم، الفاعل من الأقارب من الدرجة الثالثة (3)"
        elif h12_ruler_house in [9, 10, 8]:
            kinship_degree_text = "من الدرجة الرابعة (4) أو أقارب بالصهر والمصاهرة (زوجة الأخ، أم الزوج / أم الزوجة - الحماة، أو أهل الشريك)."
            is_relative_text = "نعم، الفاعل من الأقارب بالصهر / الدرجة الرابعة (4)"
        else:
            is_relative_text = "لا يوجد صلة قرابة بالدم نهائياً"
            kinship_degree_text = "لا توجد صلة قرابة بالدم (شخص خارجي، جار، زميل عمل، أو شخص بعيد عن العائلة)."

        # 4. مكان وجود الفاعل
        mutable_signs = ["الجوزاء", "العذراء", "القوس", "الحوت"]
        if h12_sign in mutable_signs or h12_ruler_house in [9, 12]:
            distance_text = "عن بُعد (محتمل جداً أنه يتواجد في مدينة أخرى أو بلد بعيد وقام بالأذية طاقياً عن بُعد)"
        else:
            distance_text = "في نفس البلد والمحيط الجغرافي القريب"

        # 5. استخراج اقترانات النجوم الثابتة وتوقيت الأذية
        star_clues = self.check_fixed_stars()
        damage_timing = self.estimate_damage_timing()

        perpetrator_clues = []
        if h12_ruler_house == 3:
            perpetrator_clues.append("🔍 **دلالة البيت الثالث (الإخوة والجيران):** الفاعل من الإخوة، الأخوات، أبناء العمومة، أو الجار الملاصق.")
        elif h12_ruler_house == 9:
            perpetrator_clues.append("🔍 **دلالة البيت التاسع (البيت السابع من الثالث):** الفاعل غالباً هي (زوجة الأخ) أو نسيبة من الأقارب بالصهر.")
        elif h12_ruler_house == 4:
            perpetrator_clues.append("🔍 **دلالة البيت الرابع (الأصل والبيت):** الأذى من جذور العائلة، الأب، أفراد البيت الواحد، أو مسكن مشترك.")
        elif h12_ruler_house == 10:
            perpetrator_clues.append("🔍 **دلالة البيت العاشر (السلطة وأم الشريك):** الفاعل شخص ذو سلطة، رب العمل، أو (أم الزوج / أم الزوجة - الحماة).")
        elif h12_ruler_house == 7:
            perpetrator_clues.append("🔍 **دلالة البيت السابع (الخصوم والشركاء):** الفاعل هو شريك الحياة (الزوج/الزوجة الحالي أو السابق)، شريك تجاري، أو عدو معلن.")
        elif h12_ruler_house == 8:
            perpetrator_clues.append("🔍 **دلالة البيت الثامن (أهل الشريك والمال المشترك):** الأذى مدبر من جهة (أهل الزوج أو أهل الزوجة)، أو طمّاعي المواريث.")
        elif h12_ruler_house == 5:
            perpetrator_clues.append("🔍 **دلالة البيت الخامس (الأبناء والعشاق):** الفاعل قد يكون (عشيقة، زوجة الابن / الكنة)، أو طرف ثالث تربطه علاقة عاطفية.")
        elif h12_ruler_house == 11:
            perpetrator_clues.append("🔍 **دلالة البيت الحادي عشر (الأصدقاء):** الأذى من صديق مقرب أو شبكة علاقات تظهر المودة وتضمر الحقد.")
        else:
            perpetrator_clues.append(f"🔍 **دلالة البيت {h12_ruler_house}:** شخص خفي أو طرف يعمل بالسر التام بعيداً عن المحيط المباشر.")

        nature_clues = []
        if saturn_in_affliction or (ruler_p and ruler_p["body"] == "زحل"):
            nature_clues.append("🌑 **أثر زحل (السحر الأرضي/المدفون):** دلالة على سحر مدفون في المقابر، أرض، أو معقود بالعظام والحديد القديم.")
        if mars_in_affliction or (ruler_p and ruler_p["body"] == "المريخ"):
            nature_clues.append("🔥 **أثر المريخ (السحر الناري/الدموي):** دلالة على عمل مرشوش بمواد محترقة أو دم، والفاعل متسرع أو عدائي.")
        if ketu_in_affliction:
            nature_clues.append("🐍 **أثر الذنب / الكيتو (السحر الأسود):** دلالة قاطعة على سحر أسود ونجس يعتمد على النجاسات والطلاسم المظلمة.")
        if neptune_in_affliction:
            nature_clues.append("💧 **أثر نبتون (السحر المرشوش/السائل):** دلالة على أعمال سائلة، أوهام، أو سحر خفي تدبره امرأة مراوغة.")

        if not nature_clues:
            nature_clues.append("⚡ **طبيعة عامة:** أذى طاقي خفي يتم عبر طلاسم أو حسد مكثف مقصود ومخطط له بالسر.")

        return {
            "h12_sign": h12_sign,
            "h12_ruler": h12_ruler,
            "h12_ruler_house": h12_ruler_house,
            "perpetrator_gender": perpetrator_gender,
            "perpetrator_age": perpetrator_age,
            "is_relative_text": is_relative_text,
            "kinship_degree_text": kinship_degree_text,
            "distance_text": distance_text,
            "star_clues": star_clues,
            "damage_timing": damage_timing,
            "planets_in_12": planets_in_12,
            "planets_in_6": planets_in_6,
            "planets_in_8": planets_in_8,
            "perpetrator_clues": perpetrator_clues,
            "nature_clues": nature_clues
        }

    def distinguish_envy_vs_magic(self) -> Dict[str, Any]:
        """دالة متطورة للتمييز الفلكي الروحاني بين الإصابة بالسحر أو الحسد والعين"""
        
        # تتبع الكواكب في بيوت الخطر
        h12_planets = [p for p in self.planets_data if p["house"] == 12]
        h6_planets = [p for p in self.planets_data if p["house"] == 6]
        
        # فحص وجود نحوسات قوية (زحل أو كيتو أو المريخ)
        saturn_mars_ketu_12 = any(p["body"] in ["زحل", "المريخ", "كيتو"] for p in h12_planets)
        mars_afflicting_moon = False
        
        moon_p = next((p for p in self.planets_data if p["body"] == "القمر"), None)
        mars_p = next((p for p in self.planets_data if p["body"] == "المريخ"), None)
        
        if moon_p and mars_p:
            diff_lon = abs(moon_p["lon"] - mars_p["lon"])
            if diff_lon > 180:
                diff_lon = 360 - diff_lon
            # اقتران أو تربيع أو مقابلة قريبة بين المريخ والقمر (دلالة قاطعة على العين والحسد الحار)
            if diff_lon <= 7.0 or abs(diff_lon - 90) <= 7.0 or abs(diff_lon - 180) <= 7.0:
                mars_afflicting_moon = True

        # اتخاذ القرار الروحاني الفلكي بناءً على المعطيات
        if saturn_mars_ketu_12 or any("الغول" in s for s in self.check_fixed_stars()):
            diagnosis_type = "سحر أثري أو مدبّر بالسر (طابع البيت الثاني عشر والنجوم الثابتة النحسة)"
            recommendation = "يتطلب علاجاً موجهاً لإبطال العقد وفك الارتباط الطاقي المظلم."
        elif mars_afflicting_moon or len(h6_planets) > 0:
            diagnosis_type = "حسد شديد أو إصابة بالعين (نظرة حارة تؤثر مباشرة على الهالة والجسد الأثيري)"
            recommendation = "يتطلب علاجاً بالرقية، الاغتسال بماء مضاف إليه أثر الحاسد إن عرف، وآيات الحفظ والتحصين."
        else:
            diagnosis_type = "ضغوط طاقية عامة أو إرهاق هالة ناتج عن مخالطة اجتماعية"
            recommendation = "يكفي فيها التحصينات اليومية وأذكار الصباح والمساء."

        return {
            "diagnosis_type": diagnosis_type,
            "recommendation": recommendation,
            "mars_afflicts_moon": mars_afflicting_moon
        }

# ==========================================
# 3. الدالة الجديدة: اقتراح العلاج الروحاني وتحديد الآيات القرآنية والسورة والتكرار والطريقة
# ==========================================
def suggest_spiritual_treatment(val_first: int, val_mother: int, full_name: str, full_mother_name: str) -> Dict[str, Any]:
    """دالة مقترحة لتقديم العلاج الروحاني (فك تأثير السحر) بناءً على القيم الحرفية لاسم الشخص واسم أمه"""
    combined_val = val_first + val_mother
    treatment_index = (combined_val % 7) + 1

    treatments_db = {
        1: {
            "surah_name": "سورة البقرة",
            "surah_num": 2,
            "verse_num": "الآية 102 والخواتيم (285-286)",
            "verse_text": "وَاتَّبَعُوا مَا تَتْلُوا الشَّيَاطِينُ عَلَىٰ مُلْكِ سُلَيْمَانَ... وَاتَّقُوا اللَّهَ وَيُعَلِّمُكُمُ اللَّهُ",
            "repetition": "تكرار الآية (102) 21 مرة يومياً مع قراءة الخواتيم 3 مرات",
            "method": "القراءة بصوت هادئ على إناء ماء طاهر ونقي مع النفث فيه، والشرب منه على ريق النوم والصباح، والغتسال بماء مرقي لمدة 7 أيام متتالية لإبطال السحر المدفون."
        },
        2: {
            "surah_name": "سورة الأعراف",
            "surah_num": 7,
            "verse_num": "الآيات 117 إلى 122",
            "verse_text": "وَأَوْحَيْنَا إِلَىٰ مُوسَىٰ أَنْ أَلْقِ عَصَاكَ... فَوَقَعَ الْحَقُّ وَبَطَلَ مَا كَانُوا يَعْمَلُونَ",
            "repetition": "تكرار الآيات (117-122) 41 مرة بعد صلاة الفجر",
            "method": "القراءة على زيت زيتون مبارك ودهن مواضع الألم أو الجسد به، وقراءتها على ماء الشرب لفك سحر العقد والربط وإبطال أثره."
        },
        3: {
            "surah_name": "سورة يونس",
            "surah_num": 10,
            "verse_num": "الآيتان 81 و 82",
            "verse_text": "فَلَمَّا أَلْقَوْا قَالَ مُوسَىٰ مَا جِئْتُم بِهِ السِّحْرُ إِنَّ اللَّهَ سَيُبْطِلُهُ إِنَّ اللَّهَ لَا يُصْلِحُ عَمَلَ الْمُفْسِدِينَ",
            "repetition": "تكرار الآيتين 70 مرة بتركيز ويقين يومياً",
            "method": "القراءة الكثيفة على إناء ماء كبير بنية إبطال السحر المرشوش أو المأكول، والشرب منه مستمراً والاغتسال به خارج دورات المياه."
        },
        4: {
            "surah_name": "سورة طه",
            "surah_num": 20,
            "verse_num": "الآيات 65 إلى 69",
            "verse_text": "قَالُوا يَا مُوسَىٰ إِمَّا أَن تُلْقِيَ وَإِمَّا أَن نَّكُونَ أَوَّلَ مَنْ أَلْقَىٰ... وَلَا يُفْلِحُ السَّاحِرُ حَيْثُ أَتَىٰ",
            "repetition": "تكرار الآية (69) 33 مرة بعد كل صلاة مكتوبة",
            "method": "وضع اليد اليمنى على الصدر وقراءة الآيات مع النفث والمسح، مع شرب ماء مقروء عليه مضاف إليه قطرات من مسك الروحانيات الأبيض."
        },
        5: {
            "surah_name": "سورة الإخلاص والمعوذتان (الفلق والناس)",
            "surah_num": "112, 113, 114",
            "verse_num": "السور الثلاث كاملة مع آية الكرسي",
            "verse_text": "قُلْ أَعُوذُ بِرَبِّ الْفَلَقِ... وَمِن شَرِّ النَّفَّاثَاتِ فِي الْعُقَدِ",
            "repetition": "تكرار كل سورة 100 مرة صباحاً ومساءً",
            "method": "الجمع بين الكفين والنفث فيهما بعد القراءة ومسح الجسد كله، وقراءتها على زجاجة ماء عذب للشرب المستمر والحماية الشاملة."
        },
        6: {
            "surah_name": "سورة الصافات وسورة الحشر",
            "surah_num": "37 و 59",
            "verse_num": "أول الصافات (1 إلى 10) وخواتيم الحشر",
            "verse_text": "وَالصَّافَّاتِ صَفًّا... لَوْ أَنزَلْنَا هَٰذَا الْقُرْآنَ عَلَىٰ جَبَلٍ لَّرَأَيْتَهُ خَاشِعًا مُّتَصَدِّعًا",
            "repetition": "قراءة سورة الصافات كاملة مرة واحدة وخواتيم الحشر 7 مرات",
            "method": "الاستماع بسماعات الأذن بخشوع لآيات التحصين وبطلان السحر مع شرب ماء مرقي مضاف إليه قطرات من ماء الورد الطبيعي."
        },
        7: {
            "surah_name": "سورة الفاتحة وآية الكرسي",
            "surah_num": "1 و 2",
            "verse_num": "الفاتحة الكبرى وآية الكرسي (255)",
            "verse_text": "اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ لَا تَأْخُذُهُ سِنَةٌ وَلَا نَوْمٌ",
            "repetition": "قراءة الفاتحة 7 مرات وآية الكرسي 21 مرة متتالية",
            "method": "القراءة بصوت جهرية هادئ على ماء زمزم أو ماء عذب طاهر مع الاستحمام بماء مرقي خارج الحمام والالتزام بالاستغفار."
        }
    }

    chosen_treatment = treatments_db.get(treatment_index, treatments_db[1])
    chosen_treatment["name_sum"] = combined_val
    return chosen_treatment

# ==========================================
# 4. واجهة المستخدم عبر Streamlit (ديناميكية للتحديث الفوري)
# ==========================================
st.set_page_config(page_title="نظام كشف الطاقات السلبية المطور", layout="wide")

st.title("🔮 نظام كشف أمراض الهالة الروحانية من علم الحرف والتنجيم العربي المطور")
st.markdown("---")

country_map, sorted_country_names = get_sorted_countries()

col1, col2 = st.columns(2)

with col1:
    st.subheader("إعدادات الاسم الأول و الدولة و المدينة")
    first_name_type = st.selectbox("نوع الاسم الأول:", ["مفرد", "مركب"], key="f_type")
    if first_name_type == "مفرد":
        first_name_part1 = st.text_input("أدخل الاسم الأول المفرد (مثل: نعمة):", value="", key="fn1")
        first_name_part2 = ""
    else:
        first_name_part1 = st.text_input("الشطر الأول من الاسم الأول (مثل: نعمة):", value="", key="fn1_comp")
        first_name_part2 = st.text_input("الشطر الثاني من الاسم الأول (مثل: الله):", value="", key="fn2_comp")
            
    selected_country_name = st.selectbox("دولة الميلاد:", sorted_country_names, key="country_select")
    country_code = country_map[selected_country_name]
    
    country_cities_data = get_cities_by_country(country_code)
    city_names = [city.name for city in country_cities_data]
    if not city_names:
        city_names = ["لا توجد بيانات مدن"]
    selected_city_name = st.selectbox("مدينة الميلاد (مرتبة حسب عدد السكان):", city_names, key="city_select")
    
with col2:
    st.subheader("إعدادات اسم الأم و تاريخ الميلاد و الوقت و اليوم الحالي")
    mother_name_type = st.selectbox("نوع اسم الأم:", ["مفرد", "مركب"], key="m_type")
    if mother_name_type == "مفرد":
        mother_name_part1 = st.text_input("أدخل اسم الأم المفرد:", value="", key="mn1")
        mother_name_part2 = ""
    else:
        mother_name_part1 = st.text_input("الشطر الأول من اسم الأم:", value="", key="mn1_comp")
        mother_name_part2 = st.text_input("الشطر الثاني من اسم الأم:", value="", key="mn2_comp")
            
    birth_date = st.date_input("تاريخ الميلاد:", min_value=date(1950, 1, 1), max_value=date(2030, 1, 1), value=date(1990, 1, 1))
    
    st.subheader("ساعة ودقيقة الميلاد")
    col_h, col_m = st.columns(2)
    with col_h:
        birth_hour = st.number_input("الساعة (0-23):", min_value=0, max_value=23, value=12)
    with col_m:
        birth_minute = st.number_input("الدقيقة (0-59):", min_value=0, max_value=59, value=0)

    day_key = st.selectbox(
        "اليوم الحالي للحساب:",
        options=["احد", "اثنين", "ثلاثاء", "اربعاء", "خميس", "جمعه", "سبت"],
        index=3
    )
    
is_night_radio = st.radio(
    "الوقت الحالي للكشف:",
    options=["نهار (بعد شروق الشمس إلى قبل غروبها)", "ليل (بعد غروب الشمس إلى قبل شروقها)"],
    index=1
)

submitted = st.button("✨ إطلاق التقرير التراثي الشامل وكشف الفاعل والنجوم الثابتة والعلاج الروحاني")

if submitted:
    if first_name_type == "مفرد":
        full_first_name = first_name_part1.strip()
        val_first = calculate_name_value(full_first_name, is_composite_first_box=False)
    else:
        full_first_name = f"{first_name_part1} {first_name_part2}".strip()
        val_first_part1 = calculate_name_value(first_name_part1, is_composite_first_box=True)
        val_first_part2 = calculate_name_value(first_name_part2, is_composite_first_box=False)
        val_first = val_first_part1 + val_first_part2

    if mother_name_type == "مفرد":
        full_mother_name = mother_name_part1.strip()
        val_mother = calculate_name_value(full_mother_name, is_composite_first_box=False)
    else:
        full_mother_name = f"{mother_name_part1} {mother_name_part2}".strip()
        val_mother_part1 = calculate_name_value(mother_name_part1, is_composite_first_box=True)
        val_mother_part2 = calculate_name_value(mother_name_part2, is_composite_first_box=False)
        val_mother = val_mother_part1 + val_mother_part2

    if not full_first_name or not full_mother_name:
        st.error("الرجاء إدخال بيانات الاسم الأول واسم الأم بشكل صحيح.")
    else:
        city_data = next((city for city in country_cities_data if city.name == selected_city_name), None)
        if not city_data:
            st.error("يرجى اختيار مدينة صحيحة.")
            st.stop()

        lat = city_data.latitude
        lng = city_data.longitude
        tf = TimezoneFinder()
        tz_str = tf.timezone_at(lng=lng, lat=lat) or "UTC"
        tob = time(hour=int(birth_hour), minute=int(birth_minute))
        jd = get_utc_julian_day(birth_date, tob, tz_str)

        chart_reader = AutoChartReader(jd, lat, lng)
        magic_analysis = chart_reader.analyze_magic_perpetrator()
        envy_vs_magic = chart_reader.distinguish_envy_vs_magic()
        treatment_proposal = suggest_spiritual_treatment(val_first, val_mother, full_first_name, full_mother_name)

        # 1. حساب أرقام تاريخ الميلاد
        birth_date_str = f"{birth_date.day}.{birth_date.month}.{birth_date.year}"
        digits_sum = sum(int(char) for char in birth_date_str if char.isdigit())
        
        # 2. حساب البرج الباطني وقيمته الحرفية
        zodiac_calc = val_first + val_mother
        zodiac_index = reduce_to_12(zodiac_calc)
        zodiac_name = ZODIAC_MAP.get(zodiac_index, 'حمل')
        val_zodiac_name = calculate_name_value(zodiac_name, is_composite_first_box=False)

        # 3. حساب النوء الفلكي الحالي وقيمته
        current_naw_name = get_current_naw(datetime.now())
        val_naw = calculate_name_value(current_naw_name, is_composite_first_box=False)

        # 4. حساب اليوم الحالي والكوكب المرتبط به وقيمتهما الحرفية
        day_info = DAYS_PLANETS.get(day_key.lower(), DAYS_PLANETS['اربعاء'])
        val_day = calculate_name_value(day_info['day_name'], is_composite_first_box=False)
        planet_name = day_info['planet']
        val_planet = calculate_name_value(planet_name, is_composite_first_box=False)

        # 5. حساب وقت الكشف (340 ليل / 400 نهار)
        is_night = True if "ليل" in is_night_radio else False
        time_val = 340 if is_night else 400
        time_label = "ليل (قمر)" if is_night else "نهار (شمس)"

        # 6. المجموع الكلي وفق العناصر الثمانية للتنجيم التراثي
        total_sum = (val_first + val_mother + digits_sum + val_zodiac_name + 
                     val_naw + val_day + val_planet + time_val)
        final_result_num = reduce_to_12(total_sum)

        st.success("تم إتمام التحليل التراثي والفلكي الشامل المطور بنجاح!")
        
        st.markdown("---")
        st.subheader("📊 تفاصيل القيم الحرفية وعناصر الكشف التراثي الثمانية:")
        col_res1, col_res2 = st.columns(2)
        with col_res1:
            st.write(f"1. **الاسم الأول المدخل ({full_first_name}):** مجموع قيمته = {val_first}")
            st.write(f"2. **اسم الأم المدخل ({full_mother_name}):** مجموع قيمته = {val_mother}")
            st.write(f"3. **مجموع خانات تاريخ الميلاد:** {digits_sum}")
            st.write(f"4. **البرج الباطني المستخرج:** {zodiac_name} (رقم {zodiac_index} - قيمته الحرفية: {val_zodiac_name})")
            st.write(f"5. **النوء الفلكي الحالي:** {current_naw_name} (قيمته الحرفية: {val_naw})")
            
        with col_res2:
            st.write(f"6. **اليوم الحالي للحساب:** {day_info['day_name']} (قيمته الحرفية: {val_day})")
            st.write(f"7. **الكوكب المرتبط باليوم:** {planet_name} (قيمته الحرفية: {val_planet})")
            st.write(f"8. **الوقت الحالي للكشف:** {time_label} (القيمة الرقمية: {time_val})")
            st.write(f"• **برج الطالع الفلكي الحقيقي:** {ZODIAC_SIGNS[chart_reader.ascendant_sign_idx]}")
            st.write(f"• **حاكم البيت الثاني عشر:** {magic_analysis['h12_ruler']} (يستقر في البيت {magic_analysis['h12_ruler_house']})")
            st.markdown(f"### 🧮 **المجموع الثماني الكلي:** `{total_sum}` | **النتيجة النهائية (المقسوم على 12):** `{final_result_num}`")

        st.markdown("---")
        st.subheader("🕵️‍♂️ تقرير كشف صفات الفاعل وتوقيت الأذية ودرجة القرابة والدلالات النجمية:")
        
        st.info(f"📌 **تحليل البيت الثاني عشر:** برج البيت هو ({magic_analysis['h12_sign']}) وحاكمه ({magic_analysis['h12_ruler']}) يستقر في **البيت {magic_analysis['h12_ruler_house']}**.")
        st.info(magic_analysis['damage_timing'])

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.success(f"👤 **جنس الفاعل المتوقع:** {magic_analysis['perpetrator_gender']}")
            st.success(f"👥 **صلة القرابة والدرجة:** {magic_analysis['kinship_degree_text']}")
        with col_p2:
            st.warning(f"⏳ **الفئة العمرية:** {magic_analysis['perpetrator_age']}")
            st.warning(f"🌍 **النطاق الجغرافي / البعد:** {magic_analysis['distance_text']}")

        if magic_analysis['star_clues']:
            st.subheader("⭐ الاتصالات بالنجوم الثابتة العظمى:")
            for star in magic_analysis['star_clues']:
                st.error(star)

        if magic_analysis['planets_in_12']:
            st.warning(f"⚠️ **تنبيه:** تواجد كواكب ({' ، '.join(magic_analysis['planets_in_12'])}) في البيت الثاني عشر يدعم قطعية الإصابة الخفية.")

        for clue in magic_analysis['perpetrator_clues']:
            st.warning(clue)

        for nature in magic_analysis['nature_clues']:
            st.error(nature)

        st.markdown("---")
        st.subheader("🔬 التحليل الفلكي المتقدم للتمييز بين السحر والحسد والعين:")
        st.error(f"🎯 **نوع الإصابة الفلكي:** {envy_vs_magic['diagnosis_type']}")
        st.warning(f"💡 **التوجيه العلاجي الفلكي:** {envy_vs_magic['recommendation']}")

        st.markdown("---")
        st.subheader("🌿 مقترح العلاج الروحاني وتفكيك السحر (حسب الاسم واسم الأم):")
        st.success(f"📖 **السورة المقترحة:** {treatment_proposal['surah_name']} (رقم السورة: {treatment_proposal['surah_num']})")
        st.info(f"📜 **الآية أو المقطع العلاجي:** {treatment_proposal['verse_num']}\n\n> *\"{treatment_proposal['verse_text']}\"*")
        st.warning(f"🔄 **مدى التكرار:** {treatment_proposal['repetition']}")
        st.error(f"🛠️ **طريقة الاستخدام والتحضير:** {treatment_proposal['method']}")

        st.markdown("---")
        st.subheader("📜 التشخيص الروحي النهائي للحالة:")
        diagnosis_text = ""
        if final_result_num == 12:
            diagnosis_text = "النتيجة (12): تعرض الهالة لضغوط تسبب مرضاً نفسياً واختلالاً طاقياً خفياً."
            st.error(f"**{diagnosis_text}**")
        elif final_result_num == 9:
            diagnosis_text = "النتيجة (9): تأثير طاقي سلبي ينعكس على الجانب العضوي والجسدي."
            st.warning(f"**{diagnosis_text}**")
        elif final_result_num in [2, 4]:
            diagnosis_text = f"النتيجة ({final_result_num}): إصابة طاقية سلبية مؤكدة، والفعل صادر عن كائن مرئي (شخص قريب ومعروف في محيط العائلة المباشر)."
            st.warning(f"**{diagnosis_text}**")
        elif final_result_num in [1, 3, 5, 6, 7, 8, 10, 11]:
            diagnosis_text = f"النتيجة ({final_result_num}): إصابة روحانية وطاقية سلبية بسبب كائن غير مرئي أو أعمال خفية مدبرة بالسر التام."
            st.info(f"**{diagnosis_text}**")

        # ==========================================
        # 📄 توليد تقرير HTML المطور جاهز للطباعة والتحميل
        # ==========================================
        perpetrator_html_items = "".join([f"<li>{c}</li>" for c in magic_analysis['perpetrator_clues']])
        nature_html_items = "".join([f"<li>{n}</li>" for n in magic_analysis['nature_clues']])
        star_html_items = "".join([f"<li>{s}</li>" for s in magic_analysis['star_clues']]) if magic_analysis['star_clues'] else "<li>لا توجد اقترانات مباشرة بالنجوم النحسة الكبرى.</li>"

        html_report_content = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>التقرير الروحاني والتنجيم المطور - {full_first_name}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; color: #1e293b; padding: 25px; line-height: 1.6; }}
        .container {{ max-width: 850px; margin: auto; background: #ffffff; padding: 35px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); }}
        h1 {{ text-align: center; color: #0f172a; margin-bottom: 5px; font-size: 24px; }}
        .meta {{ text-align: center; color: #64748b; font-size: 14px; margin-bottom: 30px; border-bottom: 1px solid #e2e8f0; padding-bottom: 15px; }}
        h2 {{ color: #2563eb; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-top: 30px; font-size: 18px; }}
        .card {{ background: #f1f5f9; border-right: 4px solid #2563eb; padding: 15px; border-radius: 6px; margin-bottom: 15px; }}
        ul {{ padding-right: 20px; }}
        li {{ margin-bottom: 8px; }}
        .btn-print {{ display: block; width: 220px; margin: 30px auto; padding: 12px; background: #16a34a; color: white; text-align: center; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 16px; }}
        @media print {{ .btn-print {{ display: none; }} body {{ padding:0; }} .container {{ box-shadow: none; max-width:100%; }} }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔮 التقرير الروحاني والتنجيم المطور لكشف الفاعل والعلاج القرآني</h1>
        <div class="meta">
            <b>اسم المستفيد:</b> {full_first_name} | <b>اسم الأم:</b> {full_mother_name} | <b>تاريخ الميلاد:</b> {birth_date} ({birth_hour}:{birth_minute}) | <b>الموقع:</b> {selected_country_name} - {selected_city_name}
        </div>

        <h2>📊 القيم الحرفية وعناصر الكشف التراثي الثمانية:</h2>
        <div class="card">
            <p>1. <b>الاسم الأول المدخل:</b> {full_first_name} (المجموع: {val_first})</p>
            <p>2. <b>اسم الأم المدخل:</b> {full_mother_name} (المجموع: {val_mother})</p>
            <p>3. <b>مجموع خانات تاريخ الميلاد:</b> {digits_sum}</p>
            <p>4. <b>البرج الباطني المستخرج:</b> {zodiac_name} (رقم {zodiac_index} - القيمة الحرفية: {val_zodiac_name})</p>
            <p>5. <b>النوء الفلكي الحالي:</b> {current_naw_name} (القيمة الحرفية: {val_naw})</p>
            <p>6. <b>اليوم الحالي للحساب:</b> {day_info['day_name']} (القيمة الحرفية: {val_day})</p>
            <p>7. <b>الكوكب المرتبط باليوم:</b> {planet_name} (القيمة الحرفية: {val_planet})</p>
            <p>8. <b>الوقت الحالي للكشف:</b> {time_label} (القيمة الرقمية: {time_val})</p>
            <hr>
            <p>• <b>برج الطالع الفلكي الحقيقي:</b> {ZODIAC_SIGNS[chart_reader.ascendant_sign_idx]}</p>
            <p>• <b>حاكم البيت الثاني عشر:</b> {magic_analysis['h12_ruler']} (يستقر في البيت {magic_analysis['h12_ruler_house']})</p>
            <p style="font-size: 16px; font-weight: bold; color: #1e3a8a;">• المجموع الثماني الكلي: {total_sum} | النتيجة النهائية: {final_result_num}</p>
        </div>

        <h2>🕵️‍♂️ تقرير كشف هوية الفاعل وتوقيت الأذية ودرجة القرابة:</h2>
        <div class="card" style="border-right-color: #d97706;">
            <p>👤 <b>جنس الفاعل المتوقع:</b> {magic_analysis['perpetrator_gender']}</p>
            <p>⏳ <b>الفئة العمرية للفاعل:</b> {magic_analysis['perpetrator_age']}</p>
            <p>👥 <b>صلة القرابة ودرجتها:</b> {magic_analysis['kinship_degree_text']}</p>
            <p>🌍 <b>النطاق الجغرافي / البعد:</b> {magic_analysis['distance_text']}</p>
            <p>⏱️ <b>تقدير توقيت الأذية ونطاق بدء الأذى:</b> {magic_analysis['damage_timing']}</p>
            <hr>
            <p><b>تحليل البيت الثاني عشر:</b> برج البيت هو ({magic_analysis['h12_sign']}) وحاكمه ({magic_analysis['h12_ruler']}) يستقر في البيت {magic_analysis['h12_ruler_house']}.</p>
            <ul>
                {perpetrator_html_items}
            </ul>
        </div>

        <h2>🔬 التحليل الفلكي المتقدم للتمييز بين السحر والحسد:</h2>
        <div class="card" style="border-right-color: #8b5cf6;">
            <p>🎯 <b>نوع الإصابة الفلكي:</b> {envy_vs_magic['diagnosis_type']}</p>
            <p>💡 <b>التوجيه العلاجي المقترح:</b> {envy_vs_magic['recommendation']}</p>
        </div>

        <h2>🌿 مقترح العلاج الروحاني وفك السحر (مخصص بالاسم واسم الأم):</h2>
        <div class="card" style="border-right-color: #16a34a;">
            <p>📖 <b>السورة المقترحة ورقمها:</b> {treatment_proposal['surah_name']} (رقم السورة: {treatment_proposal['surah_num']})</p>
            <p>📜 <b>الآية أو المقطع العلاجي:</b> {treatment_proposal['verse_num']}</p>
            <p>💬 <b>نص الآية الكريمة:</b> <em>"{treatment_proposal['verse_text']}"</em></p>
            <p>🔄 <b>مدى التكرار المطلوب:</b> {treatment_proposal['repetition']}</p>
            <p>🛠️ <b>طريقة الاستخدام والكيفية:</b> {treatment_proposal['method']}</p>
        </div>

        <h2>⭐ الاتصالات النجمية الكبرى:</h2>
        <div class="card" style="border-right-color: #7c3aed;">
            <ul>
                {star_html_items}
            </ul>
        </div>

        <h2>🔥 طبيعة الإصابة والأثر الطاقي:</h2>
        <div class="card" style="border-right-color: #dc2626;">
            <ul>
                {nature_html_items}
            </ul>
        </div>

        <h2>📜 التشخيص الروحي النهائي للهالة:</h2>
        <div class="card" style="border-right-color: #0284c7;">
            <p><b>{diagnosis_text}</b></p>
        </div>

        <button class="btn-print" onclick="window.print()">🖨️ طباعة التقرير / حفظ PDF</button>
    </div>
</body>
</html>"""

        st.markdown("---")
        st.subheader("📥 تنزيل أو طباعة التقرير الشامل")
        st.download_button(
            label="📥 تحميل التقرير كملف HTML جاهز للطباعة والفتح",
            data=html_report_content,
            file_name=f"Spiritual_Report_Advanced_{full_first_name}.html",
            mime="text/html"
        )
