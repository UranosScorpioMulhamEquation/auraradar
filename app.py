from datetime import datetime, date, time, timedelta
import os
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any, Optional
import uuid

import geonamescache
import pandas as pd
import pytz
import streamlit as st
import swisseph as swe
from timezonefinder import TimezoneFinder

# ==================== إعدادات الأمان ونظام الترخيص ====================
KEY_FILE = "license.key"

def get_machine_id() -> str:
    return hex(uuid.getnode())

def generate_password(mid: str) -> str:
    digits = ''.join(filter(str.isdigit, mid))
    if not digits: 
        try:
            digits = str(int(mid, 16))
        except:
            return "Error"
    num = int(digits)
    result = round(abs(num / 2 * 3.14))
    return str(result)[:6]

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = os.path.exists(KEY_FILE)

if not st.session_state['authenticated']:
    st.set_page_config(page_title="نظام الأمان والتحقق", layout="centered")
    st.title("🛡️ تفعيل نظام الأمان الفلكي")
    st.warning("الرجاء إرسال معرف الجهاز (Machine ID) للمطور للتفعيل: mulham81ahmed@gmail.com")

    mid = get_machine_id()
    st.info(f"Machine ID: {mid}")
    pwd = st.text_input("أدخل مفتاح التفعيل:", type="password")
    
    if st.button("تفعيل النظام"):
        if pwd == generate_password(mid):
            with open(KEY_FILE, "w") as f: 
                f.write(pwd)
            st.session_state['authenticated'] = True
            st.rerun()
        else:
            st.error("مفتاح التفعيل غير صحيح.")
            
    st.stop()

# ==================== إعدادات Swiss Ephemeris ====================
swe.set_ephe_path('')  # استخدام وضع Moshier الافتراضي عالي الدقة

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

@st.cache_resource
def load_cities() -> List[City]:
    gc = geonamescache.GeonamesCache()
    cities_list = []
    for city_id, city_data in gc.get_cities().items():
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
    return sorted(filtered_cities, key=lambda c: c.population, reverse=True)

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

# ==================== الثوابت التراثية والجداول الحرفية ====================
ABJAD_DICT = {
    'ا': 1, 'أ': 1, 'إ': 1, 'آ': 1, 'ء': 1,
    'ب': 2, 'ج': 3, 'د': 4,
    'ه': 5, 'ة': 5, 'و': 6, 'ز': 7,
    'ح': 8, 'ط': 9, 'ي': 10, 'ى': 10,
    'ك': 20, 'ل': 30, 'م': 40, 'ن': 50,
    'س': 60, 'ع': 70, 'ف': 80, 'ص': 90,
    'ق': 100, 'ر': 200, 'ش': 300, 'ت': 400,
    'ث': 500, 'خ': 600, 'ذ': 700, 'ض': 800,
    'ظ': 900, 'غ': 1000
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

MAJOR_FIXED_STARS = {
    "الغول (Algol)": {"lon": 56.2, "nature": "نحس شديد وعقد مظلمة"},
    "الدبران (Aldebaran)": {"lon": 69.8, "nature": "صراعات حادة وطاقات نارية"},
    "الشعرى اليمانية (Sirius)": {"lon": 104.2, "nature": "قوة طاقية وروحانية عليا"},
    "قلب الأسد (Regulus)": {"lon": 150.1, "nature": "سلطة وتسليط طاقي"},
    "السماك الأعزل (Spica)": {"lon": 204.0, "nature": "تحصين وحماية ربانية"},
    "قلب العقرب (Antares)": {"lon": 249.8, "nature": "أذى خفي ووساوس وسموم أثيرية"},
    "النسر الواقع (Vega)": {"lon": 285.3, "nature": "أعمال خفية وطلاسم معلقة"},
    "فم الحوت (Fomalhaut)": {"lon": 343.9, "nature": "أعمال مرتبطة بالعناصر المائية"}
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

# جداول الفراسة الفلكية التراثية (Physiognomy Tables)
PLANET_PHYSIOGNOMY = {
    "الشمس": {
        "height": "متوسط إلى طويل القامة، ذو هيبة وحضور بارز",
        "weight": "بنية متناسقة وممتلئة قليلاً عند الصدر والكتفين",
        "skin": "بشرة حنطية مائلة للذهبي أو مشربة بحمرة",
        "eyes_size": "عيون متوسطة إلى واسعة، ذات نظرة نافذة وجريئة",
        "eyes_color": "عسلي فاتح أو بني ذهبي",
        "lips": "شفاه متوسطة ومحددة بوضوح",
        "job": "وظيفة إدارية، منصب إشرافي، عمل حكومي، أو تجارة الذهب والمجوهرات"
    },
    "القمر": {
        "height": "متوسط أو قصير القامة قليلاً",
        "weight": "قابلية للسمنة وامتلاء الوجه والجسم (وجه مستدير)",
        "skin": "بشرة بيضاء شاحبة أو فاتحة جداً",
        "eyes_size": "عيون واسعة ومستديرة، كثيرة الرمش أو مدمعة",
        "eyes_color": "بني فاتح، رمادي، أو عسلي مائي",
        "lips": "شفاه ممتلئة وناعمة",
        "job": "عمل في قطاع الأغذية، التمريض، العقارات، السوائل، أو ربة منزل متفرغة"
    },
    "عطارد": {
        "height": "نحيل ومتوسط القامة، سريع الحركة",
        "weight": "وزن خفيف إلى نحيف، قليل اللحم، ملامح حادة",
        "skin": "بشرة حنطية فاتحة أو مائلة للصفرة",
        "eyes_size": "عيون صغيرة إلى متوسطة، سريعة الحركة والالتفات",
        "eyes_color": "بني داكن أو أسود حاد",
        "lips": "شفاه رفيعة ومستقيمة",
        "job": "محاسبة، تجارة، تعليم، كتابة، وساطة، اتصالات، أو أعمال إدارية مكتبية"
    },
    "الزهرة": {
        "height": "متوسط القامة، قوام متناسق وجذاب",
        "weight": "امتلاء أنثوي متناسق أو وزن معتدل مائل للنعومة",
        "skin": "بشرة صافية، ناعمة، بيضاء مشربة بحمرة أو قمحية صافية",
        "eyes_size": "عيون واسعة، جميلة، ذات رموش كثيفة ونظرة ناعمة",
        "eyes_color": "بني غامق جذاب، عسلي، أو ملون (أخضر/أزرق)",
        "lips": "شفاه ممتلئة ومحددة بشكل بارز",
        "job": "تجميل، أزياء، فنون، عطور، ضيافة، أو عمل يعتمد على العلاقات العامة"
    },
    "المريخ": {
        "height": "طويل أو متوسط القامة، بنية عضلية أو عظمية بارزة",
        "weight": "وزن رياضي أو نحيف صلب (قليل الدهون)",
        "skin": "بشرة سمراء محمرة أو بها آثار جروح/ندوب أو نمش",
        "eyes_size": "عيون صغيرة إلى متوسطة، غائرة قليلاً وذات نظرة حادة وغاضبة",
        "eyes_color": "بني محمر أو عسلي داكن",
        "lips": "شفاه رقيقة ومشدودة",
        "job": "أعمال حرة شاقة، هندسة، ميكانيكا، جزارة، أمن، أو مهن تتطلب جهداً بدنياً"
    },
    "المشتري": {
        "height": "طويل القامة، عريض المنكبين، ذو جثة ضخمة",
        "weight": "وزن زائد وممتلئ، بنية كبيرة وبارزة",
        "skin": "بشرة بيضاء مشربة بحمرة أو قمحية صافية",
        "eyes_size": "عيون كبيرة وواسعة ومريحة للناظر",
        "eyes_color": "عسلي، بني فاتح، أو أزرق/رمادي",
        "lips": "شفاه كبيرة وممتلئة",
        "job": "قضاء، محاماة، شؤون دينية، بنوك، تجارة كبرى، أو مناصب أكاديمية"
    },
    "زحل": {
        "height": "إما طويل جداً ونحيل أو قصير ومنحني قليلاً",
        "weight": "نحيف جداً، عظام بارزة، أو بنية ثقيلة وجافة",
        "skin": "بشرة سمراء داكنة، قمحية غامقة، أو شاحبة وجافة",
        "eyes_size": "عيون صغيرة، ضيقة، وغائرة في المحجر",
        "eyes_color": "أسود داكن أو بني غامق جداً",
        "lips": "شفاه رقيقة جداً ومضمومة",
        "job": "زراعة، عقارات وأراضي، مقاولات وبناء، أعمال تقليدية قديمة، أو متقاعد"
    },
    "أورانوس": {
        "height": "طويل القامة بشكل ملفت أو غير معتاد",
        "weight": "نحيف أو متقلب الوزن، ملامح غير تقليدية",
        "skin": "بشرة فاتحة أو حنطية مائلة للشحوب",
        "eyes_size": "عيون واسعة وجاحظة قليلاً أو ذات نظرة شاردة",
        "eyes_color": "فاتح (رمادي، أزرق، أو عسلي فاتح)",
        "lips": "شفاه رفيعة وغير متماثلة قليلاً",
        "job": "تكنولوجيا، برمجة، طيران، كهرباء، أو أعمال حرة غير تقليدية"
    },
    "نبتون": {
        "height": "متوسط القامة، مشية هادئة أو غير مستقرة",
        "weight": "يميل للامتلاء المائي أو الترهل البسيط",
        "skin": "بشرة باهتة أو بيضاء شاحبة",
        "eyes_size": "عيون واسعة، ناعسة، وغامضة النظرة",
        "eyes_color": "عسلي مائي، أخضر باهت، أو رمادي",
        "lips": "شفاه ممتلئة ولينة",
        "job": "مهن بحرية، كيمياء، صيدلة، فنون، أو أعمال خفية وغير واضحة المعالم"
    }
}

def calculate_name_value(name_part: str, is_composite_first_box: bool = False) -> int:
    total = 0
    name_part = name_part.strip()
    if not name_part:
        return 0
    for i, char in enumerate(name_part):
        if char == 'ة':
            if is_composite_first_box and i == len(name_part) - 1:
                total += 400
            else:
                total += 5
        elif char in ABJAD_DICT:
            total += ABJAD_DICT[char]
    return total

def reduce_to_12(number: int) -> int:
    while number > 12:
        number -= 12
    if number <= 0:
        number = ((number - 1) % 12) + 1
    return number

def get_current_naw(check_date: Optional[datetime] = None) -> str:
    if check_date is None:
        check_date = datetime.now()
    month, day = check_date.month, check_date.day
    if (month == 5 and 12 <= day < 25) or (month == 5 and day >= 25) or (month == 6 and day < 7):
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
    elif (month == 8 and day >= 24) or (month == 9 and day < 20):
        return "سهيل"
    elif (month == 9 and day >= 20) or (month == 10 and day < 16):
        return "وسم"
    elif (month == 10 and day >= 16) or (month == 11 and day < 24):
        return "وسم"
    elif (month == 11 and day >= 24) or (month == 12 and day < 7):
        return "مربعانيه"
    elif (month == 12 and day >= 7) or (month == 1 and day < 15):
        return "مربعانيه"
    elif (month == 1 and 15 <= day < 28):
        return "شبط"
    elif (month == 1 and day >= 28) or (month == 2 and day < 23):
        return "عقارب"
    else:
        return "حميمين"

# ==================== محرك قراءة الخريطة الفلكية والفراسة ====================
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

    def _get_aspect_between(self, p1_lon: float, p2_lon: float, orb: float = 6.0) -> Optional[str]:
        diff = abs(p1_lon - p2_lon)
        if diff > 180:
            diff = 360 - diff
        if diff <= orb:
            return "اقتران"
        elif abs(diff - 60) <= orb:
            return "تسديس"
        elif abs(diff - 90) <= orb:
            return "تربيع"
        elif abs(diff - 120) <= orb:
            return "تثليث"
        elif abs(diff - 180) <= orb:
            return "مقابلة"
        return None

    def check_fixed_stars(self) -> List[str]:
        star_clues = []
        for p in self.planets_data:
            if p["house"] in [1, 6, 8, 12]:
                for star_name, star_info in MAJOR_FIXED_STARS.items():
                    diff = abs(p["lon"] - star_info["lon"])
                    if diff > 180:
                        diff = 360 - diff
                    if diff <= 1.5:
                        star_clues.append(
                            f"⭐ **اقتران نجمي مؤثر:** كوكب ({p['body']}) مقترن بالنجم الثابت **[{star_name}]** (درجة {star_info['lon']}°). الدلالة: {star_info['nature']}."
                        )
        return star_clues

    def estimate_damage_timing(self) -> str:
        h12_sign_idx = (self.ascendant_sign_idx + 11) % 12
        h12_sign = ZODIAC_SIGNS[h12_sign_idx]
        h12_ruler = SIGN_RULERS.get(h12_sign)
        ruler_p = next((p for p in self.planets_data if p["body"] == h12_ruler), None)

        if not ruler_p:
            return "توقيت الأذية: غير محدد بدقة لكتمان حركة الحاكم."

        arc_diff = abs(ruler_p["lon"] - self.ascendant_lon)
        if arc_diff > 180:
            arc_diff = 360 - arc_diff

        cardinal_signs = ["الحمل", "السرطان", "الميزان", "الجدي"]
        fixed_signs = ["الثور", "الأسد", "العقرب", "الدلو"]
        
        calculated_months = int((arc_diff / 30) * 12) + 1
        if calculated_months > 24:
            calculated_months = calculated_months % 24 + 1

        if h12_sign in cardinal_signs:
            status_type = "أذية جديدة وطارئة"
            timing_details = f"حدثت خلال الأيام أو الأسابيع القليلة الماضية وتحديداً منذ حوالي {int(arc_diff % 30) + 1} يوماً."
        elif h12_sign in fixed_signs:
            status_type = "أذية قديمة ومتأصلة ومستمرة"
            timing_details = f"الأذية تراكمية ومستمرة منذ عدة أشهر طويلة (نطاق البدء منذ حوالي {int(arc_diff / 10) + 1} إلى {int(arc_diff / 5) + 2} شهراً)."
        else:
            status_type = "أذية متجددة (متوسطة الحداثة)"
            timing_details = f"بدأت الأذية قبل نطاق زمني يقدر بـ {max(1, calculated_months - 1)} إلى {calculated_months + 1} شهراً تقريباً."

        return f"⏱️ **فحص توقيت الأذية:** تصنف كـ **[{status_type}]**. النطاق الزمني: {timing_details} (المسافة القوسية: {arc_diff:.2f}°)."

    def analyze_perpetrator_physiognomy(self, h12_ruler: str, ruler_p: Optional[Dict[str, Any]], planets_in_12: List[str]) -> Dict[str, str]:
        """استخراج الصفات الشكلية والعمل بدقة وفق علم الفراسة الفلكي"""
        base_phys = PLANET_PHYSIOGNOMY.get(h12_ruler, PLANET_PHYSIOGNOMY["عطارد"]).copy()
        
        if ruler_p:
            ruler_sign = ruler_p["sign"]
            # تعديل اللون وحجم العيون والشفاه بناءً على البرج الذي ينزل فيه حاكم الـ 12
            water_signs = ["السرطان", "العقرب", "الحوت"]
            fire_signs = ["الحمل", "الأسد", "القوس"]
            earth_signs = ["الثور", "العذراء", "الجدي"]
            
            if ruler_sign in water_signs:
                base_phys["eyes_size"] = "عيون واسعة، ناعسة أو مدمعة، ذات بريق مائي"
                base_phys["lips"] = "شفاه ممتلئة وبارزة"
                base_phys["weight"] += " (قابلية لاحتباس السوائل وامتلاء الوجه)"
            elif ruler_sign in fire_signs:
                base_phys["skin"] = "بشرة حنطية مشربة بحمرة أو برونزية"
                base_phys["eyes_color"] = "عسلي حاد، بني محمر، أو ذهبي"
                base_phys["eyes_size"] = "عيون متوسطة وذات نظرة ثاقبة وسريعة"
            elif ruler_sign in earth_signs:
                base_phys["skin"] = "بشرة قمحية داكنة أو سمراء صافية"
                base_phys["lips"] = "شفاه محددة ومتوسطة إلى رقيقة"
                base_phys["height"] += " (بنية صلبة ومتماسكة)"

            # فحص الاقترانات مع حاكم الـ 12 لتعديل الوزن والطول
            for other_p in self.planets_data:
                if other_p["body"] != h12_ruler and other_p["body"] not in ["راهو", "كيتو"]:
                    asp = self._get_aspect_between(ruler_p["lon"], other_p["lon"], orb=5.0)
                    if asp == "اقتران":
                        if other_p["body"] == "المشتري":
                            base_phys["weight"] = "وزن زائد وجسم ممتلئ وضخم بوضوح (تأثير اقتران المشتري)"
                        elif other_p["body"] == "زحل":
                            base_phys["weight"] = "نحافة واضحة وبروز في عظام الوجه والكتفين (تأثير اقتران زحل)"
                            base_phys["skin"] = "بشرة داكنة أو شاحبة جافة"
                        elif other_p["body"] == "الزهرة":
                            base_phys["eyes_size"] = "عيون واسعة وجميلة جداً ذات جاذبية ملفتة"
                            base_phys["lips"] = "شفاه ممتلئة ومحددة بشكل واضح"

        return base_phys

    def analyze_exact_kinship(self, h12_ruler_house: int, ruler_p: Optional[Dict[str, Any]], is_fem: bool) -> Dict[str, str]:
        """تحديد درجة القرابة الدقيقة (الأولى، الثانية، الثالثة، الرابعة) والمصاهرة والصفة العائلية"""
        # فحص اتصالات حاكم الـ 12 بالكواكب الدالة على العائلة
        moon_p = next((p for p in self.planets_data if p["body"] == "القمر"), None)
        sun_p = next((p for p in self.planets_data if p["body"] == "الشمس"), None)
        venus_p = next((p for p in self.planets_data if p["body"] == "الزهرة"), None)
        mercury_p = next((p for p in self.planets_data if p["body"] == "عطارد"), None)

        asp_moon = self._get_aspect_between(ruler_p["lon"], moon_p["lon"]) if (ruler_p and moon_p) else None
        asp_sun = self._get_aspect_between(ruler_p["lon"], sun_p["lon"]) if (ruler_p and sun_p) else None
        asp_venus = self._get_aspect_between(ruler_p["lon"], venus_p["lon"]) if (ruler_p and venus_p) else None
        asp_mercury = self._get_aspect_between(ruler_p["lon"], mercury_p["lon"]) if (ruler_p and mercury_p) else None

        degree_label = "خارج دائرة القرابة (غريب / زميل / معرفة)"
        exact_relation = "شخص من خارج العائلة (جار بعيد، زميل عمل، أو معرفة اجتماعية)"

        if h12_ruler_house == 4:
            degree_label = "أقارب الدرجة الأولى (1) - داخل البيت الواحد"
            if is_fem:
                if asp_moon in ["تربيع", "مقابلة", "اقتران"]:
                    exact_relation = "الأم أو الجدة لأم، أو امرأة كبيرة ذات سلطة داخل منزل العائلة"
                else:
                    exact_relation = "الأخت المقيمة في نفس البيت، أو زوجة الأب"
            else:
                if asp_sun in ["تربيع", "مقابلة", "اقتران"]:
                    exact_relation = "الأب أو الجد، أو كبير العائلة في المسكن"
                else:
                    exact_relation = "الأخ المقيم في نفس المنزل"

        elif h12_ruler_house == 3:
            degree_label = "أقارب الدرجة الأولى (1) أو المحيط الملاصق"
            if is_fem:
                if asp_venus or asp_moon:
                    exact_relation = "الأخت، أو زوجة الأخ (السلفة / نسيبة البيت)، أو جارة ملاصقة للباب"
                else:
                    exact_relation = "الأخت غير الشقيقة أو إحدى بنات الجيران الملاصقين"
            else:
                exact_relation = "الأخ، أو زوج الأخت، أو الجار الملاصق للمسكن"

        elif h12_ruler_house == 6:
            degree_label = "أقارب الدرجة الثانية (2) بالدم (أخوال / أعمام)"
            if is_fem:
                if asp_moon:
                    exact_relation = "الخالة أو العمة (أخت الأم أو أخت الأب)"
                else:
                    exact_relation = "زوجة الخال أو زوجة العم"
            else:
                exact_relation = "الخال أو العم (أخو الأم أو أخو الأب)"

        elif h12_ruler_house in [5, 11]:
            degree_label = "أقارب الدرجة الثالثة (3) بالدم (أبناء العمومة والأخوال)"
            if is_fem:
                if asp_venus or asp_mercury:
                    exact_relation = "زوجة ابن العم أو زوجة ابن الخال (قرابة مصاهرة من الدرجة الثالثة)"
                else:
                    exact_relation = "بنت العم، بنت العمة، بنت الخال، أو بنت الخالة"
            else:
                exact_relation = "ابن العم، ابن العمة، ابن الخال، أو ابن الخالة"

        elif h12_ruler_house in [7, 8, 9, 10]:
            degree_label = "أقارب الدرجة الرابعة (4) أو أقارب المصاهرة وأهل الشريك"
            if h12_ruler_house == 10:
                exact_relation = "الحماة (أم الزوج / أم الزوجة) أو امرأة ذات نفوذ في عائلة الشريك" if is_fem else "حمو المستفيد (أبو الشريك) أو مدير/مسؤول مباشر"
            elif h12_ruler_house == 9:
                exact_relation = "زوجة الأخ، أخت الزوج/الزوجة (الحماة الصغيرة)، أو قريبة من عائلة الصهر" if is_fem else "أخو الزوج/الزوجة (السلف) أو زوج الأخت"
            elif h12_ruler_house == 8:
                exact_relation = "قريبة من الدرجة الرابعة (بنت ابن العم/الخال) أو امرأة من أهل الشريك بينكم شراكة أو مال" if is_fem else "قريب من الدرجة الرابعة أو شريك مالي قديم"
            else: # البيت 7
                exact_relation = "شريكة سابقة/حالية، أو امرأة منافسة على الشريك (ضرة أو خطيبة سابقة)" if is_fem else "شريك حياة سابق/حالي أو خصم معلن"

        return {
            "degree_label": degree_label,
            "exact_relation": exact_relation
        }

    def analyze_location_status(self, h12_sign: str, h12_ruler_house: int, ruler_p: Optional[Dict[str, Any]]) -> Dict[str, str]:
        """تحديد ما إذا كان الفاعل مقيماً في نفس بلد المولد أم خارج بلد الميلاد"""
        uranus_p = next((p for p in self.planets_data if p["body"] == "أورانوس"), None)
        rahu_p = next((p for p in self.planets_data if p["body"] == "راهو"), None)
        
        asp_uranus = self._get_aspect_between(ruler_p["lon"], uranus_p["lon"], orb=5.0) if (ruler_p and uranus_p) else None
        asp_rahu = self._get_aspect_between(ruler_p["lon"], rahu_p["lon"], orb=5.0) if (ruler_p and rahu_p) else None

        mutable_signs = ["الجوزاء", "العذراء", "القوس", "الحوت"]
        
        if h12_ruler_house in [9, 12] or asp_uranus in ["اقتران", "مقابلة"] or asp_rahu == "اقتران":
            status = "مقيم خارج بلد الميلاد (في بلد أجنبي أو غربة)"
            details = "تشير الدلائل الفلكية (تواجد الحاكم في بيوت السفر البعيد أو اتصاله بأورانوس/الذنب) إلى أن الفاعل يقيم حالياً خارج بلد المولد ويدير الأذى عن بُعد."
        elif h12_sign in mutable_signs or h12_ruler_house in [3, 11]:
            status = "في نفس بلد المولد (ولكن في مدينة أو منطقة أخرى)"
            details = "الفاعل يتواجد داخل حدود نفس الدولة، لكنه في محافظة أو مدينة بعيدة عن مسكن المستفيد ويتنقل باستمرار."
        else:
            status = "مقيم في نفس بلد المولد ونفس المدينة"
            details = "تواجد الحاكم في أوتاد أو بيوت محلية ثابتة يؤكد وجود الفاعل في نفس بلد المولد ونفس النطاق الجغرافي للمستفيد."

        return {
            "status": status,
            "details": details
        }

    def analyze_motive_and_enmity(self, h12_ruler_house: int, ruler_p: Optional[Dict[str, Any]]) -> Dict[str, str]:
        """كشف سبب العداء والدافع الحقيقي وراء الأذية (مال، انتقام، زواج/علاقة، غيرة)"""
        venus_p = next((p for p in self.planets_data if p["body"] == "الزهرة"), None)
        mars_p = next((p for p in self.planets_data if p["body"] == "المريخ"), None)
        saturn_p = next((p for p in self.planets_data if p["body"] == "زحل"), None)
        pluto_p = next((p for p in self.planets_data if p["body"] == "بلوتو"), None)
        jupiter_p = next((p for p in self.planets_data if p["body"] == "المشتري"), None)

        asp_venus = self._get_aspect_between(ruler_p["lon"], venus_p["lon"]) if (ruler_p and venus_p) else None
        asp_mars = self._get_aspect_between(ruler_p["lon"], mars_p["lon"]) if (ruler_p and mars_p) else None
        asp_saturn = self._get_aspect_between(ruler_p["lon"], saturn_p["lon"]) if (ruler_p and saturn_p) else None
        asp_pluto = self._get_aspect_between(ruler_p["lon"], pluto_p["lon"]) if (ruler_p and pluto_p) else None
        asp_jupiter = self._get_aspect_between(ruler_p["lon"], jupiter_p["lon"]) if (ruler_p and jupiter_p) else None

        if h12_ruler_house in [5, 7] or asp_venus in ["اقتران", "تربيع", "مقابلة"]:
            primary_motive = "التقرب للمسحور بغرض الزواج به أو إقامة علاقة عاطفية / سحر محبة وجلب"
            motive_details = "اتصال حاكم البيت الثاني عشر بالزهرة أو بيوت العاطفة والزواج (5 و 7) يدل على أن الدافع هو التعلق العاطفي، الرغبة في الزواج من المستفيد، أو سحر جلب وطاعة وإخضاع عاطفي."
        elif h12_ruler_house in [2, 8] or asp_jupiter in ["تربيع", "مقابلة"]:
            primary_motive = "الطمع المالي والحصول على مال أو إرث أو منفعة مادية من المستفيد"
            motive_details = "ارتباط الدليل ببيوت المال والمواريث (2 و 8) يثبت أن السبب مادي بحت؛ إما طمعاً في مال المستفيد وممتلكاته، أو نزاع على ميراث أو شراكة مالية."
        elif asp_mars in ["تربيع", "مقابلة", "اقتران"] or asp_pluto in ["تربيع", "مقابلة", "اقتران"] or asp_saturn in ["تربيع", "مقابلة"]:
            primary_motive = "انتقام وثأر قديم وحقد دفين لتدمير حياة المستفيد"
            motive_details = "الزوايا النحيسة من المريخ أو زحل أو بلوتو تكشف عن عداء شديد ورغبة في الانتقام نتيجة خلاف قديم، كسر كبرياء الفاعل، أو رغبة في تعطيل رزق المستفيد وصحته."
        elif h12_ruler_house in [10, 11]:
            primary_motive = "الغيرة من النجاح والمكانة الاجتماعية أو المهنية"
            motive_details = "الفاعل يحسد المستفيد على قبوله الاجتماعي أو نجاحه الوظيفي ويسعى لإسقاط مكانته وتشويه سمعته."
        else:
            primary_motive = "حسد وغيرة عامة وتمني زوال النعمة والاستقرار"
            motive_details = "الدافع نابع من نفسية حاقدة تراقب استقرار المستفيد العائلي والشخصي وتسعى لتفريق شمله."

        return {
            "primary_motive": primary_motive,
            "motive_details": motive_details
        }

    def analyze_magic_perpetrator(self) -> Dict[str, Any]:
        h12_sign_idx = (self.ascendant_sign_idx + 11) % 12
        h12_sign = ZODIAC_SIGNS[h12_sign_idx]
        h12_ruler = SIGN_RULERS.get(h12_sign)
        
        ruler_p = next((p for p in self.planets_data if p["body"] == h12_ruler), None)
        h12_ruler_house = ruler_p["house"] if ruler_p else 12

        planets_in_12 = [p["body"] for p in self.planets_data if p["house"] == 12]
        saturn_in_affliction = any(p["body"] == "زحل" and p["house"] in [6, 8, 12] for p in self.planets_data)
        mars_in_affliction = any(p["body"] == "المريخ" and p["house"] in [6, 8, 12] for p in self.planets_data)
        ketu_in_affliction = any(p["body"] == "كيتو" and p["house"] in [6, 8, 12] for p in self.planets_data)
        neptune_in_affliction = any(p["body"] == "نبتون" and p["house"] in [6, 8, 12] for p in self.planets_data)

        feminine_signs = ["الثور", "السرطان", "العذراء", "العقرب", "الجدي", "الحوت"]
        feminine_planets = ["القمر", "الزهرة", "نبتون"]
        is_fem = (h12_ruler in feminine_planets) or (h12_sign in feminine_signs)
        perpetrator_gender = "امرأة (أنثى)" if is_fem else "رجل (ذكر)"

        if h12_ruler == "زحل" or saturn_in_affliction:
            perpetrator_age = "كبير السن (فوق 50 سنة)"
        elif h12_ruler in ["المشتري", "المريخ", "الشمس"] or mars_in_affliction:
            perpetrator_age = "في منتصف العمر (بين 30 و 50 سنة)"
        else:
            perpetrator_age = "في سن الشباب (تحت 30 سنة)"

        # استدعاء المحركات التفصيلية الجديدة
        physiognomy = self.analyze_perpetrator_physiognomy(h12_ruler, ruler_p, planets_in_12)
        kinship_info = self.analyze_exact_kinship(h12_ruler_house, ruler_p, is_fem)
        location_info = self.analyze_location_status(h12_sign, h12_ruler_house, ruler_p)
        motive_info = self.analyze_motive_and_enmity(h12_ruler_house, ruler_p)

        star_clues = self.check_fixed_stars()
        damage_timing = self.estimate_damage_timing()

        nature_clues = []
        if saturn_in_affliction: nature_clues.append("أثر زحل (سحر أرضي ثقيل ومقابر)")
        if mars_in_affliction: nature_clues.append("أثر المريخ (سحر ناري/مرشوش حاد)")
        if ketu_in_affliction: nature_clues.append("أثر الكيتو (سحر أسود وعقد مظلمة)")
        if neptune_in_affliction: nature_clues.append("أثر نبتون (سحر سائل أو أوهام وتخييلات)")
        if not nature_clues: nature_clues.append("أذى طاقي خفي وطلاسم مدبرة عن بُعد")

        return {
            "h12_sign": h12_sign,
            "h12_ruler": h12_ruler,
            "h12_ruler_house": h12_ruler_house,
            "perpetrator_gender": perpetrator_gender,
            "perpetrator_age": perpetrator_age,
            "physiognomy": physiognomy,
            "kinship_info": kinship_info,
            "location_info": location_info,
            "motive_info": motive_info,
            "star_clues": star_clues,
            "damage_timing": damage_timing,
            "planets_in_12": planets_in_12,
            "nature_clues": nature_clues
        }

    def distinguish_envy_vs_magic(self) -> Dict[str, Any]:
        h12_planets = [p for p in self.planets_data if p["house"] == 12]
        h6_planets = [p for p in self.planets_data if p["house"] == 6]
        saturn_mars_ketu_12 = any(p["body"] in ["زحل", "المريخ", "كيتو"] for p in h12_planets)
        
        if saturn_mars_ketu_12 or any("الغول" in s for s in self.check_fixed_stars()):
            diagnosis_type = "سحر أثري أو مدبّر بالسر وعقد مظلمة"
            recommendation = "يتطلب علاجاً موجهاً ومكثفاً لإبطال العقد وفك الارتباط الطاقي."
        elif len(h6_planets) > 1:
            diagnosis_type = "حسد شديد أو إصابة بالعين المتكررة"
            recommendation = "يتطلب علاجاً بالرقية الشرعية، والاغتسال بالماء المرقي."
        else:
            diagnosis_type = "سحر خفي أو عمل طاقي مقصود عن بُعد"
            recommendation = "يكفي فيها التحصينات اليومية وأذكار الصباح والمساء."

        return {"diagnosis_type": diagnosis_type, "recommendation": recommendation}

    def detect_damage_medium_and_method(self, diagnosis_type: str) -> Dict[str, str]:
        h8_planets = [p for p in self.planets_data if p["house"] == 8]
        h12_sign = ZODIAC_SIGNS[(self.ascendant_sign_idx + 11) % 12]
        
        if "حسد" in diagnosis_type:
            medium_used = "إصابة طاقية مباشرة عبر نظرة حاسدة دون أثر مادي."
            delivery_method = "تأثير مباشر على الهالة الطاقية والنشاط الحيوي."
        else:
            medium_used = "استخدام أثر شخصي مادي (ملابس، شعر، أو صورة) لربط الأثير." if len(h8_planets) > 0 else "اعتماد مباشر على الاسم الثلاثي واسم الأم طاقياً."
            fire_signs = ["الحمل", "الأسد", "القوس"]
            water_signs = ["السرطان", "العقرب", "الحوت"]
            earth_signs = ["الثور", "العذراء", "الجدي"]
            if h12_sign in fire_signs:
                delivery_method = "محرّق (تعريض العمل للنار أو البخور المظلم)."
            elif h12_sign in water_signs:
                delivery_method = "مرشوش (عمل سائل رُشّ أو طُرح في ماء جارٍ)."
            elif h12_sign in earth_signs:
                delivery_method = "مدفون (سحر أرضي دُفن في تراب أو مقابر)."
            else:
                delivery_method = "مأكول أو مشروب."

        return {"medium_used": medium_used, "delivery_method": delivery_method}

    def detect_perpetrator_name_letters(self) -> Dict[str, Any]:
        h12_sign_idx = (self.ascendant_sign_idx + 11) % 12
        h12_sign = ZODIAC_SIGNS[h12_sign_idx]
        fire_signs = ["الحمل", "الأسد", "القوس"]
        earth_signs = ["الثور", "العذراء", "الجدي"]
        air_signs = ["الجوزاء", "الميزان", "الدلو"]

        if h12_sign in fire_signs:
            letters_list = ["أ", "هـ", "ط", "م", "ف", "ش", "ذ"]
            element_desc = "طابع ناري"
        elif h12_sign in earth_signs:
            letters_list = ["ب", "و", "ي", "ن", "ص", "ت", "ض"]
            element_desc = "طابع ترابي"
        elif h12_sign in air_signs:
            letters_list = ["ج", "ز", "ك", "س", "ق", "ث", "ظ"]
            element_desc = "طابع هوائي"
        else:
            letters_list = ["د", "ح", "ل", "ع", "ر", "خ", "غ"]
            element_desc = "طابع مائي"

        return {"h12_sign": h12_sign, "element_desc": element_desc, "letters_list": letters_list}

# ==================== العلاج الروحاني ====================
def suggest_spiritual_treatment(val_first: int, val_mother: int) -> Dict[str, Any]:
    combined_val = val_first + val_mother
    treatment_index = (combined_val % 7) or 7
    treatments_db = {
        1: {"surah_name": "سورة البقرة", "surah_num": 2, "verse_num": "الآية 102 والخواتيم", "verse_text": "وَاتَّبَعُوا مَا تَتْلُوا الشَّيَاطِينُ...", "repetition": "تكرار الآية (102) 21 مرة يومياً", "method": "القراءة على إناء ماء والشرب منه والاغتسال."},
        2: {"surah_name": "سورة الأعراف", "surah_num": 7, "verse_num": "الآيات 117 - 122", "verse_text": "وَأَوْحَيْنَا إِلَىٰ مُوسَىٰ أَنْ أَلْقِ عَصَاكَ...", "repetition": "تكرار الآيات 41 مرة بعد الفجر", "method": "القراءة على زيت زيتون ودهن مواضع الألم."},
        3: {"surah_name": "سورة يونس", "surah_num": 10, "verse_num": "الآيتان 81 و 82", "verse_text": "فَلَمَّا أَلْقَوْا قَالَ مُوسَىٰ مَا جِئْتُم بِهِ السِّحْرُ...", "repetition": "تكرار الآيتين 70 مرة يومياً", "method": "القراءة على ماء الشرب بنية إبطال السحر."},
        4: {"surah_name": "سورة طه", "surah_num": 20, "verse_num": "الآيات 65 إلى 69", "verse_text": "قَالُوا يَا مُوسَىٰ إِمَّا أَن تُلْقِيَ...", "repetition": "تكرار الآية (69) 33 مرة بعد كل صلاة", "method": "وضع اليد على الصدر وقراءة الآيات مع النفث."},
        5: {"surah_name": "سورة الإخلاص والمعوذتان", "surah_num": "112-114", "verse_num": "السور الثلاث مع آية الكرسي", "verse_text": "قُلْ أَعُوذُ بِرَبِّ الْفَلَقِ...", "repetition": "تكرار كل سورة 100 مرة صباحاً ومساءً", "method": "المسح باليدين على الجسد بعد القراءة."},
        6: {"surah_name": "سورة الصافات والحشر", "surah_num": "37 و 59", "verse_num": "أول الصافات وخواتيم الحشر", "verse_text": "وَالصَّافَّاتِ صَفًّا...", "repetition": "قراءة الصافات مرة وخواتيم الحشر 7 مرات", "method": "الاستماع بخشوع لآيات التحصين الشامل."},
        7: {"surah_name": "سورة الفاتحة وآية الكرسي", "surah_num": "1 و 2", "verse_num": "الفاتحة وآية الكرسي (255)", "verse_text": "اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ...", "repetition": "قراءة الفاتحة 7 مرات وآية الكرسي 21 مرة", "method": "القراءة على ماء طاهر والاستحمام به."}
    }
    return treatments_db.get(treatment_index, treatments_db[1])

# ==================== واجهة المستخدم عبر Streamlit ====================
st.set_page_config(page_title="برنامج الهالة الطاقية", layout="wide")

st.title("🔮 نظام الكشفية الطاقية من علوم الفلك العربي و الروحانيات و الحرف و الفراسة")
st.markdown("تطوير الفلكي استرو رادار")
st.markdown("---")

country_map, sorted_country_names = get_sorted_countries()

col1, col2 = st.columns(2)

with col1:
    st.subheader("📍 البيانات الشخصية والمكانية")
    first_name_type = st.selectbox("نوع الاسم الأول:", ["مفرد", "مركب"], key="f_type")
    if first_name_type == "مفرد":
        first_name_part1 = st.text_input("الاسم الأول:", value="", key="fn1")
        first_name_part2 = ""
    else:
        first_name_part1 = st.text_input("الشطر الأول من الاسم الأول:", value="", key="fn1_comp")
        first_name_part2 = st.text_input("الشطر الثاني من الاسم الأول:", value="", key="fn2_comp")
            
    selected_country_name = st.selectbox("دولة الميلاد:", sorted_country_names, key="country_select")
    country_code = country_map[selected_country_name]
    
    country_cities_data = get_cities_by_country(country_code)
    city_names = [city.name for city in country_cities_data] or ["لا توجد بيانات مدن"]
    selected_city_name = st.selectbox("مدينة الميلاد:", city_names, key="city_select")
    
with col2:
    st.subheader("📅 تواريخ الميلاد ووقت الكشف")
    mother_name_type = st.selectbox("نوع اسم الأم:", ["مفرد", "مركب"], key="m_type")
    if mother_name_type == "مفرد":
        mother_name_part1 = st.text_input("اسم الأم:", value="", key="mn1")
        mother_name_part2 = ""
    else:
        mother_name_part1 = st.text_input("الشطر الأول من اسم الأم:", value="", key="mn1_comp")
        mother_name_part2 = st.text_input("الشطر الثاني من اسم الأم:", value="", key="mn2_comp")
            
    birth_date = st.date_input("تاريخ الميلاد:", min_value=date(1950, 1, 1), max_value=date(2030, 1, 1), value=date(1990, 1, 1))
    
    col_h, col_m = st.columns(2)
    with col_h: birth_hour = st.number_input("الساعة (0-23):", min_value=0, max_value=23, value=12)
    with col_m: birth_minute = st.number_input("الدقيقة (0-59):", min_value=0, max_value=59, value=0)

    day_key = st.selectbox("اليوم الحالي للحساب:", options=["احد", "اثنين", "ثلاثاء", "اربعاء", "خميس", "جمعه", "سبت"], index=3)
    
is_night_radio = st.radio("وقت الكشف الحالي:", options=["نهار", "ليل"], index=1)

submitted = st.button("✨ إطلاق التقرير الفلكي التراثي الشامل")

if submitted:
    full_first_name = first_name_part1.strip() if first_name_type == "مفرد" else f"{first_name_part1} {first_name_part2}".strip()
    full_mother_name = mother_name_part1.strip() if mother_name_type == "مفرد" else f"{mother_name_part1} {mother_name_part2}".strip()
    
    val_first = calculate_name_value(first_name_part1, first_name_type == "مركب") + (calculate_name_value(first_name_part2, False) if first_name_type == "مركب" else 0)
    val_mother = calculate_name_value(mother_name_part1, mother_name_type == "مركب") + (calculate_name_value(mother_name_part2, False) if mother_name_type == "مركب" else 0)

    if not full_first_name or not full_mother_name:
        st.error("الرجاء إدخال بيانات الاسم الأول واسم الأم بشكل صحيح.")
    else:
        city_data = next((city for city in country_cities_data if city.name == selected_city_name), None)
        if not city_data:
            st.error("يرجى اختيار مدينة صحيحة.")
            st.stop()

        lat, lng = city_data.latitude, city_data.longitude
        tz_str = TimezoneFinder().timezone_at(lng=lng, lat=lat) or "UTC"
        jd = get_utc_julian_day(birth_date, time(hour=int(birth_hour), minute=int(birth_minute)), tz_str)

        chart_reader = AutoChartReader(jd, lat, lng)
        magic_analysis = chart_reader.analyze_magic_perpetrator()
        envy_vs_magic = chart_reader.distinguish_envy_vs_magic()
        damage_medium = chart_reader.detect_damage_medium_and_method(envy_vs_magic['diagnosis_type'])
        perpetrator_letters = chart_reader.detect_perpetrator_name_letters()
        treatment_proposal = suggest_spiritual_treatment(val_first, val_mother)

        birth_date_str = f"{birth_date.day}.{birth_date.month}.{birth_date.year}"
        digits_sum = sum(int(c) for c in birth_date_str if c.isdigit())
        
        zodiac_index = reduce_to_12(val_first + val_mother)
        zodiac_name = ZODIAC_MAP.get(zodiac_index, 'حمل')
        val_zodiac_name = calculate_name_value(zodiac_name)
        
        current_naw_name = get_current_naw(datetime.now())
        val_naw = calculate_name_value(current_naw_name)
        
        day_info = DAYS_PLANETS.get(day_key.lower(), DAYS_PLANETS['اربعاء'])
        val_day = calculate_name_value(day_info['day_name'])
        planet_name = day_info['planet']
        val_planet = calculate_name_value(planet_name)
        
        time_val = 340 if "ليل" in is_night_radio else 400
        time_label = "ليل (قمر)" if "ليل" in is_night_radio else "نهار (شمس)"

        total_sum = val_first + val_mother + digits_sum + val_zodiac_name + val_naw + val_day + val_planet + time_val
        final_result_num = reduce_to_12(total_sum)

        st.success("تم إتمام التحليل الفلكي والتراثي والفراسة الشاملة بنجاح!")
        st.markdown("---")
        st.subheader("📊 ملخص الحسابات والعناصر الثمانية:")
        
        col_res1, col_res2 = st.columns(2)
        with col_res1:
            st.write(f"1. **الاسم الأول:** {full_first_name} (قيمة: {val_first})")
            st.write(f"2. **اسم الأم:** {full_mother_name} (قيمة: {val_mother})")
            st.write(f"3. **مجموع خانات التاريخ:** {digits_sum}")
            st.write(f"4. **البرج الباطني:** {zodiac_name} (قيمة: {val_zodiac_name})")
        with col_res2:
            st.write(f"5. **النوء الفلكي:** {current_naw_name} (قيمة: {val_naw})")
            st.write(f"6. **اليوم:** {day_info['day_name']} (قيمة: {val_day})")
            st.write(f"7. **الكوكب:** {planet_name} (قيمة: {val_planet})")
            st.write(f"8. **وقت الكشف:** {time_label} (قيمة: {time_val})")
            
        st.info(f"✨ **الطالع الفلكي الحقيقي:** {ZODIAC_SIGNS[chart_reader.ascendant_sign_idx]} | **حاكم البيت 12:** {magic_analysis['h12_ruler']} (في البيت {magic_analysis['h12_ruler_house']}) | **المجموع الكلي:** `{total_sum}` | **النتيجة النهائية:** `{final_result_num}`")

        st.markdown("---")
        st.subheader("🕵️‍♂️ ملف الفراسة الفلكية والصفات الشكلية والمهنية للفاعل:")
        phys = magic_analysis['physiognomy']
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            st.success(f"👤 **الجنس والعمر:** {magic_analysis['perpetrator_gender']} | {magic_analysis['perpetrator_age']}")
            st.info(f"📏 **الطول والقوام:** {phys['height']}")
            st.info(f"⚖️ **الوزن والبنية الجسدية:** {phys['weight']}")
            st.info(f"🎨 **لون البشرة:** {phys['skin']}")
        with col_f2:
            st.info(f"👁️ **حجم وشكل العيون:** {phys['eyes_size']}")
            st.info(f"🧿 **لون العيون:** {phys['eyes_color']}")
            st.info(f"👄 **شكل وحجم الشفاه:** {phys['lips']}")
            st.warning(f"💼 **العمل والمهنة المحتملة:** {phys['job']}")

        st.markdown("---")
        st.subheader("🧬 القرابة الدقيقة، موقع الإقامة، وسبب العداء والدافع:")
        kin = magic_analysis['kinship_info']
        loc = magic_analysis['location_info']
        mot = magic_analysis['motive_info']

        st.error(f"🎯 **درجة القرابة:** {kin['degree_label']}")
        st.warning(f"👪 **التحديد الدقيق للصلة العائلية:** {kin['exact_relation']}")
        
        col_loc, col_mot = st.columns(2)
        with col_loc:
            st.info(f"🌍 **مكان الإقامة بالنسبة لبلد المولد:** {loc['status']}\n\n*{loc['details']}*")
        with col_mot:
            st.error(f"🔥 **سبب العداء والدافع الرئيسي:** {mot['primary_motive']}\n\n*{mot['motive_details']}*")

        st.warning(magic_analysis['damage_timing'])
        for star in magic_analysis['star_clues']: st.error(star)

        st.markdown("---")
        st.subheader("🔬 التشخيص الفلكي ووسيلة الأذى:")
        st.error(f"🎯 **التشخيص المعتمد:** {envy_vs_magic['diagnosis_type']}")
        st.warning(f"💡 **التوجيه العلاجي:** {envy_vs_magic['recommendation']}")
        st.info(f"🧬 **الوسيلة:** {damage_medium['medium_used']} | 🧪 **الطريقة:** {damage_medium['delivery_method']}")

        st.markdown("---")
        st.subheader("🔤 الحروف المحتملة في اسم الفاعل:")
        st.success(f"🔤 الحروف: `{' ، '.join(perpetrator_letters['letters_list'])}` ({perpetrator_letters['element_desc']})")

        st.markdown("---")
        st.subheader("🌿 مقترح العلاج الروحاني:")
        st.success(f"📖 **السورة المقترحة:** {treatment_proposal['surah_name']} ({treatment_proposal['verse_num']})")
        st.info(f"💬 *\"{treatment_proposal['verse_text']}\"*")
        st.warning(f"🔄 **التكرار:** {treatment_proposal['repetition']}")
        st.error(f"🛠️ **الطريقة:** {treatment_proposal['method']}")

        # ==================== تصدير تقرير HTML الشامل ====================
        star_html = "".join([f"<li>{s}</li>" for s in magic_analysis['star_clues']]) if magic_analysis['star_clues'] else "<li>لا توجد اقترانات مباشرة بالنجوم النحسة الكبرى.</li>"

        html_report_content = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>التقرير الفلكي والفراسة والروحانيات - {full_first_name}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: #f8fafc; color: #1e293b; padding: 25px; line-height: 1.6; }}
        .container {{ max-width: 900px; margin: auto; background: #fff; padding: 35px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); }}
        h1 {{ text-align: center; color: #0f172a; font-size: 24px; }}
        .meta {{ text-align: center; color: #64748b; font-size: 14px; margin-bottom: 25px; border-bottom: 1px solid #e2e8f0; padding-bottom: 15px; }}
        h2 {{ color: #2563eb; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-top: 28px; font-size: 18px; }}
        .card {{ background: #f1f5f9; border-right: 4px solid #2563eb; padding: 15px; border-radius: 6px; margin-bottom: 15px; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
        .btn-print {{ display: block; width: 220px; margin: 30px auto; padding: 12px; background: #16a34a; color: white; text-align: center; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 15px; }}
        @media print {{ .btn-print {{ display: none; }} .container {{ box-shadow: none; }} }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔮 التقرير الفلكي الشامل وكشف الفراسة والدوافع</h1>
        <div class="meta"><b>المستفيد:</b> {full_first_name} | <b>اسم الأم:</b> {full_mother_name} | <b>مكان الميلاد:</b> {selected_country_name} - {selected_city_name}</div>
        
        <h2>📊 ملخص العناصر الفلكية والحرفية:</h2>
        <div class="card">
            <p><b>الطالع الفلكي:</b> {ZODIAC_SIGNS[chart_reader.ascendant_sign_idx]} | <b>حاكم البيت 12:</b> {magic_analysis['h12_ruler']} (البيت {magic_analysis['h12_ruler_house']})</p>
            <p><b>البرج الباطني:</b> {zodiac_name} | <b>النوء الحالي:</b> {current_naw_name} | <b>المجموع الكلي:</b> {total_sum} | <b>النتيجة النهائية:</b> {final_result_num}</p>
        </div>

        <h2>🕵️‍♂️ ملف الفراسة الفلكية والصفات الشكلية والمهنية للفاعل:</h2>
        <div class="card" style="border-right-color: #d97706;">
            <div class="grid">
                <div><b>👤 الجنس والعمر:</b> {magic_analysis['perpetrator_gender']} - {magic_analysis['perpetrator_age']}</div>
                <div><b>💼 العمل والمهنة:</b> {phys['job']}</div>
                <div><b>📏 الطول والقوام:</b> {phys['height']}</div>
                <div><b>⚖️ الوزن والبنية:</b> {phys['weight']}</div>
                <div><b>🎨 لون البشرة:</b> {phys['skin']}</div>
                <div><b>👁️ حجم العيون:</b> {phys['eyes_size']}</div>
                <div><b>🧿 لون العيون:</b> {phys['eyes_color']}</div>
                <div><b>👄 شكل الشفاه:</b> {phys['lips']}</div>
            </div>
        </div>

        <h2>🧬 القرابة الدقيقة، الإقامة الجغرافية، وسبب العداء:</h2>
        <div class="card" style="border-right-color: #dc2626;">
            <p><b>🎯 درجة القرابة:</b> {kin['degree_label']}</p>
            <p><b>👪 التحديد الدقيق للصلة العائلية:</b> {kin['exact_relation']}</p>
            <p><b>🌍 الإقامة بالنسبة لبلد المولد:</b> {loc['status']} ({loc['details']})</p>
            <p><b>🔥 سبب العداء والدافع:</b> {mot['primary_motive']} — {mot['motive_details']}</p>
            <p><b>⏱️ التوقيت الزمني:</b> {magic_analysis['damage_timing']}</p>
        </div>

        <h2>🔬 التشخيص الفلكي ووسيلة الأذى والحروف:</h2>
        <div class="card" style="border-right-color: #7c3aed;">
            <p><b>التشخيص المعتمد:</b> {envy_vs_magic['diagnosis_type']}</p>
            <p><b>الوسيلة والطريقة:</b> {damage_medium['medium_used']} | {damage_medium['delivery_method']}</p>
            <p><b>الحروف المحتملة في اسم الفاعل:</b> {' ، '.join(perpetrator_letters['letters_list'])} ({perpetrator_letters['element_desc']})</p>
            <ul>{star_html}</ul>
        </div>

        <h2>🌿 العلاج الروحاني المقترح:</h2>
        <div class="card" style="border-right-color: #16a34a;">
            <p><b>السورة والآية:</b> {treatment_proposal['surah_name']} - {treatment_proposal['verse_num']}</p>
            <p><em>"{treatment_proposal['verse_text']}"</em></p>
            <p><b>التكرار والطريقة:</b> {treatment_proposal['repetition']} | {treatment_proposal['method']}</p>
        </div>

        <button class="btn-print" onclick="window.print()">🖨️ طباعة التقرير / حفظ PDF</button>
    </div>
</body>
</html>"""

        st.markdown("---")
        st.download_button(
            label="📥 تحميل التقرير الشامل كملف HTML جاهز للطباعة",
            data=html_report_content,
            file_name=f"Spiritual_Physiognomy_Report_{full_first_name}.html",
            mime="text/html"
        )
