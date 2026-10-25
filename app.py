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
# 1. جدول الحروف الأبجدية الكامل (الجمل الكبير مع التاء المربوطة والهاء)
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
# قاموس الأنوية الفلكية الكامل (بدون أي اختصار)
# ==========================================
def get_current_naw(check_date=None):
    """تحديد النوء الفلكي الحالي بناءً على التاريخ بدقة متناهية"""
    if check_date is None:
        check_date = datetime.now()
    
    month = check_date.month
    day = check_date.day
    
    if (month == 5 and day >= 12) or (month == 5 and day < 25):
        return "ثريا"
    elif (month == 5 and day >= 25) or (month == 6 and day < 7):
        return "ثريا"
    elif (month == 6 and day >= 7) or (month == 6 and day < 20):
        return "ثريا"
    elif (month == 6 and day >= 20) or (month == 7 and day < 3):
        return "تويبع"
    elif (month == 7 and day >= 3) or (month == 7 and day < 16):
        return "جوزاء"
    elif (month == 7 and day >= 16) or (month == 7 and day < 29):
        return "جوزاء"
    elif (month == 7 and day >= 29) or (month == 8 and day < 11):
        return "مرزم"
    elif (month == 8 and day >= 11) or (month == 8 and day < 24):
        return "كليبين"
    elif (month == 8 and day >= 24) or (month == 9 and day < 6):
        return "سهيل"
    elif (month == 9 and day >= 6) or (month == 9 and day < 20):
        return "سهيل"
    elif (month == 9 and day >= 20) or (month == 10 and day < 3):
        return "سهيل"
    elif (month == 10 and day >= 3) or (month == 10 and day < 16):
        return "سهيل"
    elif (month == 10 and day >= 16) or (month == 10 and day < 29):
        return "وسم"
    elif (month == 10 and day >= 29) or (month == 11 and day < 11):
        return "وسم"
    elif (month == 11 and day >= 11) or (month == 11 and day < 24):
        return "وسم"
    elif (month == 11 and day >= 24) or (month == 12 and day < 7):
        return "وسم"
    elif (month == 12 and day >= 7) or (month == 12 and day < 20):
        return "مربعانيه"
    elif (month == 12 and day >= 20) or (month == 1 and day < 2):
        return "مربعانيه"
    elif (month == 1 and day >= 2) or (month == 1 and day < 15):
        return "مربعانيه"
    elif (month == 1 and day >= 15) or (month == 1 and day < 28):
        return "شبط"
    elif (month == 1 and day >= 28) or (month == 2 and day < 10):
        return "شبط"
    elif (month == 2 and day >= 10) or (month == 2 and day < 23):
        return "عقارب"
    elif (month == 2 and day >= 23) or (month == 3 and day < 8):
        return "عقارب"
    elif (month == 3 and day >= 8) or (month == 3 and day < 21):
        return "عقارب"
    elif (month == 3 and day >= 21) or (month == 4 and day < 3):
        return "حميمين"
    elif (month == 4 and day >= 3) or (month == 4 and day < 16):
        return "حميمين"
    elif (month == 4 and day >= 16) or (month == 4 and day < 29):
        return "ذراعين"
    else:
        return "ذراعين"

# ==========================================
# 2. محرك قراءة الخريطة الفلكية التلقائي وتطبيق القواعد الكلاسيكية الكاملة
# ==========================================
class AutoChartReader:
    def __init__(self, jd: float, lat: float, lng: float):
        self.jd = jd
        self.lat = lat
        self.lng = lng
        self.planets_data = []
        self.ascendant_sign_idx = 0
        self._calculate()

    def _calculate(self):
        # استخدام نظام كل برج بيت (Whole Sign Houses) لتحديد البيوت بدقة تراثية
        flags = swe.FLG_SWIEPH | swe.FLG_SPEED
        cusps, ascmc = swe.houses(self.jd, self.lat, self.lng, b'W')
        asc_lon = ascmc[0]
        self.ascendant_sign_idx = int(asc_lon // 30)

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
                "is_retro": pos[3] < 0
            })

        # إضافة كيتو (الذنب / South Node) المقابل لراهو
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
                "is_retro": True
            })

    def analyze_magic_perpetrator(self) -> Dict[str, Any]:
        # القواعد الكلاسيكية الكاملة المعتمدة في المراجع العربية:
        # البيت 12 (الخبايا والأسرار والسحر المدفون)، البيت 6 (الأمراض والعمالة)، البيت 8 (التدمير والسحر الأسود).
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

        # قواعد البيوت المشتقة لتحديد صلة قرابة الفاعل بدقة متناهية:
        perpetrator_clues = []
        
        if h12_ruler_house == 3:
            perpetrator_clues.append("🔍 **دلالة البيت الثالث (الإخوة والجيران):** الفاعل من الإخوة، الأخوات، أبناء العمومة، أو الجار الملاصق.")
        elif h12_ruler_house == 9:
            perpetrator_clues.append("🔍 **دلالة البيت التاسع (البيت السابع من الثالث):** الفاعل غالباً هي (زوجة الأخ) أو نسيبة من الأقارب بالصهر.")
        elif h12_ruler_house == 4:
            perpetrator_clues.append("🔍 **دلالة البيت الرابع (الأصل والبيت):** الأذى من جذور العائلة، الأب، أفراد البيت الواحد، أو مسكن مشترك.")
        elif h12_ruler_house == 10:
            perpetrator_clues.append("🔍 **دلالة البيت العاشر (السلطة وأم الشريك):** الفاعل شخص ذو سلطة، رب العمل، أو (أم الزوج / أم الزوجة - الحماة) بناءً على اشتفاق البيت العاشر بالنسبة للبيت السابع.")
        elif h12_ruler_house == 7:
            perpetrator_clues.append("🔍 **دلالة البيت السابع (الخصوم والشركاء):** الفاعل هو شريك الحياة (الزوج/الزوجة الحالي أو السابق)، شريك تجاري، أو عدو معلن.")
        elif h12_ruler_house == 8:
            perpetrator_clues.append("🔍 **دلالة البيت الثامن (أهل الشريك والمال المشترك):** الأذى مدبر من جهة (أهل الزوج أو أهل الزوجة)، أو أقارب الشريك وطمّاعي المواريث.")
        elif h12_ruler_house == 5:
            perpetrator_clues.append("🔍 **دلالة البيت الخامس (الأبناء والعشاق):** الفاعل قد يكون (عشيقة، زوجة الابن / الكنة)، أو طرف ثالث تربطه علاقة عاطفية محرمة.")
        elif h12_ruler_house == 11:
            perpetrator_clues.append("🔍 **دلالة البيت الحادي عشر (الأصدقاء):** الأذى من صديق مقرب أو شبكة علاقات تظهر المودة وتضمر الحقد.")
        else:
            perpetrator_clues.append(f"🔍 **دلالة البيت {h12_ruler_house}:** شخص خفي أو طرف يعمل بالسر التام بعيداً عن المحيط المباشر.")

        # النحوس الطاقية وطبيعة الإصابة في المراجع العربية:
        nature_clues = []
        if saturn_in_affliction or (ruler_p and ruler_p["body"] == "زحل"):
            nature_clues.append("🌑 **أثر زحل (السحر الأرضي/المدفون):** دلالة على سحر مدفون في المقابر، أرض، أو معقود بالعظام والحديد القديم، وغالباً الفاعل شخص مسن أو ذو تحكم صارم.")
        if mars_in_affliction or (ruler_p and ruler_p["body"] == "المريخ"):
            nature_clues.append("🔥 **أثر المريخ (السحر الناري/الدموي):** دلالة على عمل مرشوش بمواد محترقة أو دم، والفاعل متسرع، عدائي، أو يلجأ للعنف الظاهري.")
        if ketu_in_affliction:
            nature_clues.append("🐍 **أثر الذنب / الكيتو (السحر الأسود):** دلالة قاطعة على سحر أسود ونجس يعتمد على النجاسات والطلاسم المظلمة المدبرة بليل.")
        if neptune_in_affliction:
            nature_clues.append("💧 **أثر نبتون (السحر المرشوش/السائل):** دلالة على أعمال سائلة، أوهام، أو سحر خفي تدبره امرأة أو شخص مراوغ بطرق خبيثة.")

        if not nature_clues:
            nature_clues.append("⚡ **طبيعة عامة:** أذى طاقي خفي يتم عبر طلاسم أو حسد مكثف مقصود ومخطط له بالسر.")

        return {
            "h12_sign": h12_sign,
            "h12_ruler": h12_ruler,
            "h12_ruler_house": h12_ruler_house,
            "planets_in_12": planets_in_12,
            "planets_in_6": planets_in_6,
            "planets_in_8": planets_in_8,
            "perpetrator_clues": perpetrator_clues,
            "nature_clues": nature_clues
        }

# ==========================================
# 3. واجهة المستخدم عبر Streamlit (ديناميكية للتحديث الفوري)
# ==========================================
st.set_page_config(page_title="نظام كشف الطاقات السلبية", layout="wide")

st.title("🔮 نظام كشف أمراض الهالة الروحانية من علم الحرف و التنجيم العربي")
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

submitted = st.button("✨ إطلاق التقرير التراثي الشامل وكشف الفاعل")

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

        birth_date_str = f"{birth_date.day}.{birth_date.month}.{birth_date.year}"
        digits_sum = sum(int(char) for char in birth_date_str if char.isdigit())
        zodiac_calc = val_first + val_mother
        zodiac_index = reduce_to_12(zodiac_calc)
        zodiac_name = ZODIAC_MAP.get(zodiac_index, 'حمل')
        val_zodiac_name = calculate_name_value(zodiac_name, is_composite_first_box=False)

        day_info = DAYS_PLANETS.get(day_key.lower(), DAYS_PLANETS['اربعاء'])
        val_day = calculate_name_value(day_info['day_name'], is_composite_first_box=False)
        planet_name = day_info['planet']
        val_planet = calculate_name_value(planet_name, is_composite_first_box=False)
        is_night = True if "ليل" in is_night_radio else False
        time_val = 340 if is_night else 400
        
        current_naw_name = get_current_naw(datetime.now())
        val_naw = calculate_name_value(current_naw_name, is_composite_first_box=False)

        total_sum = (val_first + val_mother + digits_sum + val_zodiac_name + 
                     val_day + val_planet + time_val + val_naw)
        final_result_num = reduce_to_12(total_sum)

        st.success("تم إتمام التحليل التراثي والفلكي الشامل بنجاح!")
        
        st.markdown("---")
        st.subheader("📊 تفاصيل القيم الحرفية والبرج الباطني والنوء:")
        col_res1, col_res2 = st.columns(2)
        with col_res1:
            st.write(f"• **الاسم الأول المدخل ({full_first_name}):** مجموع قيمته = {val_first}")
            st.write(f"• **اسم الأم المدخل ({full_mother_name}):** مجموع قيمته = {val_mother}")
            st.write(f"• **مجموع خانات تاريخ الميلاد:** {digits_sum}")
            st.write(f"• **البرج الباطني المستخرج:** {zodiac_name} (رقم {zodiac_index} - قيمته: {val_zodiac_name})")
            
        with col_res2:
            st.write(f"• **برج الطالع الفلكي الحقيقي:** {ZODIAC_SIGNS[chart_reader.ascendant_sign_idx]}")
            st.write(f"• **النوء الفلكي المسيطر:** {current_naw_name} (القيمة: {val_naw})")
            st.write(f"• **حاكم البيت الثاني عشر:** {magic_analysis['h12_ruler']} (يستقر في البيت {magic_analysis['h12_ruler_house']})")
            st.write(f"• **المجموع الكلي الثماني:** {total_sum} | **النتيجة النهائية:** {final_result_num}")

        st.markdown("---")
        st.subheader("🕵️‍♂️ تقرير كشف هوية الفاعل وصلة القرابة (وفق مراجع التنجيم العربي الكلاسيكي):")
        
        st.info(f"📌 **تحليل البيت الثاني عشر:** برج البيت هو ({magic_analysis['h12_sign']}) وحاكمه ({magic_analysis['h12_ruler']}) يستقر في **البيت {magic_analysis['h12_ruler_house']}**.")
        
        if magic_analysis['planets_in_12']:
            st.warning(f"⚠️ **تنبيه:** تواجد كواكب ({' ، '.join(magic_analysis['planets_in_12'])}) في البيت الثاني عشر يدعم قطعية الإصابة الخفية.")

        for clue in magic_analysis['perpetrator_clues']:
            st.warning(clue)

        for nature in magic_analysis['nature_clues']:
            st.error(nature)

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
        # 📄 توليد تقرير HTML جاهز للطباعة والتحميل
        # ==========================================
        perpetrator_html_items = "".join([f"<li>{c}</li>" for c in magic_analysis['perpetrator_clues']])
        nature_html_items = "".join([f"<li>{n}</li>" for n in magic_analysis['nature_clues']])

        html_report_content = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>التقرير الروحاني والتنجيم الشامل - {full_first_name}</title>
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
        <h1>🔮 التقرير الروحاني والتنجيم الشامل لكشف الأذى والسحر</h1>
        <div class="meta">
            <b>اسم المستفيد:</b> {full_first_name} | <b>اسم الأم:</b> {full_mother_name} | <b>تاريخ الميلاد:</b> {birth_date} ({birth_hour}:{birth_minute}) | <b>الموقع:</b> {selected_country_name} - {selected_city_name}
        </div>

        <h2>📊 القيم الحرفية والبرج الباطني والنوء:</h2>
        <div class="card">
            <p>• <b>الاسم الأول المدخل:</b> {full_first_name} (المجموع: {val_first})</p>
            <p>• <b>اسم الأم المدخل:</b> {full_mother_name} (المجموع: {val_mother})</p>
            <p>• <b>مجموع خانات تاريخ الميلاد:</b> {digits_sum}</p>
            <p>• <b>البرج الباطني المستخرج:</b> {zodiac_name} (رقم {zodiac_index} - القيمة: {val_zodiac_name})</p>
            <p>• <b>برج الطالع الفلكي الحقيقي:</b> {ZODIAC_SIGNS[chart_reader.ascendant_sign_idx]}</p>
            <p>• <b>النوء الفلكي المسيطر:</b> {current_naw_name} (القيمة: {val_naw})</p>
            <p>• <b>حاكم البيت الثاني عشر:</b> {magic_analysis['h12_ruler']} (يستقر في البيت {magic_analysis['h12_ruler_house']})</p>
            <p>• <b>المجموع الكلي الثماني:</b> {total_sum} | <b>النتيجة النهائية:</b> {final_result_num}</p>
        </div>

        <h2>🕵️‍♂️ تقرير كشف هوية الفاعل وصلة القرابة:</h2>
        <div class="card" style="border-right-color: #d97706;">
            <p><b>تحليل البيت الثاني عشر:</b> برج البيت هو ({magic_analysis['h12_sign']}) وحاكمه ({magic_analysis['h12_ruler']}) يستقر في البيت {magic_analysis['h12_ruler_house']}.</p>
            <ul>
                {perpetrator_html_items}
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
            file_name=f"Spiritual_Report_{full_first_name}.html",
            mime="text/html"
        )
