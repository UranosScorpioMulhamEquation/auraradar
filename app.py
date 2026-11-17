from datetime import datetime, date, time
import html
import math
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
        except Exception:
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
swe.set_ephe_path('')  # وضع Moshier المدمج (لا يحتاج ملفات خارجية)


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
    'ه': 5, 'ة': 5, 'و': 6, 'ؤ': 6, 'ز': 7,
    'ح': 8, 'ط': 9, 'ي': 10, 'ى': 10, 'ئ': 10,
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

# الحكام التراثيون (الدلو=زحل، الحوت=المشتري) كما في الفلك العربي القديم
SIGN_RULERS = {
    "الحمل": "المريخ", "الثور": "الزهرة", "الجوزاء": "عطارد", "السرطان": "القمر",
    "الأسد": "الشمس", "العذراء": "عطارد", "الميزان": "الزهرة", "العقرب": "المريخ",
    "القوس": "المشتري", "الجدي": "زحل", "الدلو": "زحل", "الحوت": "المشتري"
}

EXALTATION = {
    "الشمس": "الحمل", "القمر": "الثور", "عطارد": "العذراء", "الزهرة": "الحوت",
    "المريخ": "الجدي", "المشتري": "السرطان", "زحل": "الميزان"
}

CARDINAL_SIGNS = ["الحمل", "السرطان", "الميزان", "الجدي"]
FIXED_SIGNS = ["الثور", "الأسد", "العقرب", "الدلو"]
MUTABLE_SIGNS = ["الجوزاء", "العذراء", "القوس", "الحوت"]

FIRE_SIGNS = ["الحمل", "الأسد", "القوس"]
EARTH_SIGNS = ["الثور", "العذراء", "الجدي"]
AIR_SIGNS = ["الجوزاء", "الميزان", "الدلو"]
WATER_SIGNS = ["السرطان", "العقرب", "الحوت"]

ELEMENT_DIRECTION = {"ناري": "الشرق", "ترابي": "الجنوب", "هوائي": "الغرب", "مائي": "الشمال"}

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

NODES = ["راهو", "كيتو"]
MALEFICS = ["المريخ", "زحل", "بلوتو", "كيتو", "راهو"]

# متوسط السرعة اليومية (درجة/يوم) لقياس سرعة الكوكب
MEAN_SPEED = {
    "الشمس": 0.9856, "القمر": 13.176, "عطارد": 1.383, "الزهرة": 1.2,
    "المريخ": 0.524, "المشتري": 0.083, "زحل": 0.034
}

# النجوم الثابتة (خط الطول الاستوائي لعام 2000م، يتم تصحيحها تلقائياً بالمبادرة الاعتدالية)
MAJOR_FIXED_STARS = {
    "الغول (Algol)": {"lon": 56.2, "nature": "نحس شديد وعقد مظلمة"},
    "الدبران (Aldebaran)": {"lon": 69.8, "nature": "صراعات حادة وطاقات نارية"},
    "الشعرى اليمانية (Sirius)": {"lon": 104.1, "nature": "قوة طاقية وروحانية عليا"},
    "قلب الأسد (Regulus)": {"lon": 150.1, "nature": "سلطة وتسليط طاقي"},
    "السماك الأعزل (Spica)": {"lon": 203.8, "nature": "تحصين وحماية ربانية"},
    "قلب العقرب (Antares)": {"lon": 249.8, "nature": "أذى خفي ووساوس وسموم أثيرية"},
    "النسر الواقع (Vega)": {"lon": 285.3, "nature": "أعمال خفية وطلاسم معلقة"},
    "فم الحوت (Fomalhaut)": {"lon": 333.9, "nature": "أعمال مرتبطة بالعناصر المائية"}
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

# ---- منازل القمر الـ 28 وحروف الأبجد (الترتيب الأبجدي على المنازل) ----
ABJAD_ORDER = ["ا", "ب", "ج", "د", "ه", "و", "ز", "ح", "ط", "ي", "ك", "ل", "م", "ن",
               "س", "ع", "ف", "ص", "ق", "ر", "ش", "ت", "ث", "خ", "ذ", "ض", "ظ", "غ"]
MANSIONS = ["الشرطين", "البطين", "الثريا", "الدبران", "الهقعة", "الهنعة", "الذراع", "النثرة",
            "الطرف", "الجبهة", "الزبرة", "الصرفة", "العواء", "السماك", "الغفر", "الزبانى",
            "الإكليل", "القلب", "الشولة", "النعائم", "البلدة", "سعد الذابح", "سعد بلع",
            "سعد السعود", "سعد الأخبية", "الفرغ المقدم", "الفرغ المؤخر", "الرشاء"]

ELEMENT_LETTERS = {
    "ناري": ["ا", "ه", "ط", "م", "ف", "ش", "ذ"],
    "ترابي": ["ب", "و", "ي", "ن", "ص", "ت", "ض"],
    "هوائي": ["ج", "ز", "ك", "س", "ق", "ث", "ظ"],
    "مائي": ["د", "ح", "ل", "ع", "ر", "خ", "غ"],
}

# ---- جداول الفراسة الفلكية التراثية ----
PLANET_PHYSIOGNOMY = {
    "الشمس": {
        "height": "متوسط إلى طويل القامة، ذو هيبة وحضور بارز",
        "weight": "بنية متناسقة وممتلئة قليلاً عند الصدر والكتفين",
        "skin": "بشرة حنطية مائلة للذهبي أو مشربة بحمرة",
        "eyes_size": "عيون متوسطة إلى واسعة، ذات نظرة نافذة وجريئة",
        "eyes_color": "عسلي فاتح أو بني ذهبي",
        "lips": "شفاه متوسطة ومحددة بوضوح",
        "hair": "شعر خفيف نسبياً أو بداية صلع، بلون بني ذهبي",
        "face": "وجه عريض مهيب وجبهة عريضة",
        "job": "وظيفة إدارية، منصب إشرافي، عمل حكومي، أو تجارة الذهب والمجوهرات"
    },
    "القمر": {
        "height": "متوسط أو قصير القامة قليلاً",
        "weight": "قابلية للسمنة وامتلاء الوجه والجسم",
        "skin": "بشرة بيضاء شاحبة أو فاتحة جداً",
        "eyes_size": "عيون واسعة ومستديرة، كثيرة الرمش أو مدمعة",
        "eyes_color": "بني فاتح، رمادي، أو عسلي مائي",
        "lips": "شفاه ممتلئة وناعمة",
        "hair": "شعر ناعم بلون بني فاتح",
        "face": "وجه مستدير ممتلئ",
        "job": "عمل في قطاع الأغذية، التمريض، العقارات، السوائل، أو ربة منزل متفرغة"
    },
    "عطارد": {
        "height": "نحيل ومتوسط القامة، سريع الحركة",
        "weight": "وزن خفيف إلى نحيف، ملامح حادة",
        "skin": "بشرة حنطية فاتحة أو مائلة للصفرة",
        "eyes_size": "عيون صغيرة إلى متوسطة، سريعة الحركة والالتفات",
        "eyes_color": "بني داكن أو أسود حاد",
        "lips": "شفاه رفيعة ومستقيمة",
        "hair": "شعر خفيف ناعم داكن",
        "face": "وجه نحيل مستطيل وملامح ذكية",
        "job": "محاسبة، تجارة، تعليم، كتابة، وساطة، اتصالات، أو أعمال مكتبية"
    },
    "الزهرة": {
        "height": "متوسط القامة، قوام متناسق وجذاب",
        "weight": "امتلاء متناسق أو وزن معتدل مائل للنعومة",
        "skin": "بشرة صافية ناعمة، بيضاء مشربة بحمرة أو قمحية صافية",
        "eyes_size": "عيون واسعة جميلة ذات رموش كثيفة ونظرة ناعمة",
        "eyes_color": "بني غامق جذاب، عسلي، أو ملون (أخضر/أزرق)",
        "lips": "شفاه ممتلئة ومحددة بشكل بارز",
        "hair": "شعر ناعم كثيف مموج",
        "face": "وجه جميل مستدير ناعم وغمازات محتملة",
        "job": "تجميل، أزياء، فنون، عطور، ضيافة، أو عمل يعتمد على العلاقات العامة"
    },
    "المريخ": {
        "height": "طويل أو متوسط القامة، بنية عضلية أو عظمية بارزة",
        "weight": "وزن رياضي أو نحيف صلب",
        "skin": "بشرة سمراء محمرة أو بها آثار جروح/ندوب أو نمش",
        "eyes_size": "عيون صغيرة إلى متوسطة، غائرة قليلاً وذات نظرة حادة",
        "eyes_color": "بني محمر أو عسلي داكن",
        "lips": "شفاه رقيقة ومشدودة",
        "hair": "شعر خشن قصير كثيف، مائل للحمرة أو البني الداكن",
        "face": "وجه زاوي محمر، حواجب كثيفة، وعلامة أو ندبة محتملة",
        "job": "أعمال حرة شاقة، هندسة، ميكانيكا، جزارة، أمن، أو مهن تتطلب جهداً بدنياً"
    },
    "المشتري": {
        "height": "طويل القامة، عريض المنكبين",
        "weight": "وزن زائد وبنية كبيرة بارزة",
        "skin": "بشرة بيضاء مشربة بحمرة أو قمحية صافية",
        "eyes_size": "عيون كبيرة وواسعة ومريحة للناظر",
        "eyes_color": "عسلي، بني فاتح، أو أزرق/رمادي",
        "lips": "شفاه كبيرة وممتلئة",
        "hair": "شعر كثيف لامع بلون بني",
        "face": "وجه عريض بشوش ممتلئ، وذقن مزدوج محتمل",
        "job": "قضاء، محاماة، شؤون دينية، بنوك، تجارة كبرى، أو مناصب أكاديمية"
    },
    "زحل": {
        "height": "إما طويل جداً ونحيل أو قصير ومنحني قليلاً",
        "weight": "نحيف جداً وعظام بارزة، أو بنية ثقيلة وجافة",
        "skin": "بشرة سمراء داكنة، قمحية غامقة، أو شاحبة وجافة",
        "eyes_size": "عيون صغيرة ضيقة وغائرة في المحجر",
        "eyes_color": "أسود داكن أو بني غامق جداً",
        "lips": "شفاه رقيقة جداً ومضمومة",
        "hair": "شعر أسود خشن أو قليل الكثافة",
        "face": "وجه طويل جاف، عظام وجنتين بارزة، وتجاعيد مبكرة",
        "job": "زراعة، عقارات وأراضي، مقاولات وبناء، أعمال تقليدية قديمة، أو متقاعد"
    },
    "أورانوس": {
        "face": "ملامح غريبة غير تقليدية",
        "hair": "شعر غير معتاد أو غير مرتب",
    },
    "نبتون": {
        "face": "ملامح ناعمة غير محددة",
        "hair": "شعر ناعم مائل للتموج",
    },
}

# ---- جداول الدلالات الكوكبية (للجنس / العمر / القوام) ----
PLANET_GENDER = {  # موجب = ذكر، سالب = أنثى
    "الشمس": 2, "المريخ": 2, "المشتري": 2, "زحل": 2, "عطارد": 0,
    "القمر": -2, "الزهرة": -2, "أورانوس": 1, "نبتون": -1, "بلوتو": 0, "راهو": 0, "كيتو": 0
}

PLANET_AGE = {
    "القمر": 24, "عطارد": 24, "الزهرة": 30, "المريخ": 37, "الشمس": 42,
    "المشتري": 52, "زحل": 66, "أورانوس": 35, "نبتون": 45, "بلوتو": 45, "راهو": 33, "كيتو": 45
}

# (درجة الطول، درجة الوزن) من -2 إلى +2
PLANET_BUILD = {
    "الشمس": (0.5, 0.5), "القمر": (-1.0, 1.5), "عطارد": (-0.5, -1.5), "الزهرة": (0.0, 0.5),
    "المريخ": (1.0, -0.5), "المشتري": (2.0, 2.0), "زحل": (1.0, -1.5), "أورانوس": (1.5, -1.0),
    "نبتون": (0.0, 1.0), "بلوتو": (0.5, 0.5), "راهو": (0.5, 0.0), "كيتو": (0.0, -0.5)
}
ELEMENT_BUILD = {"ناري": (0.3, -0.3), "ترابي": (0.0, 0.6), "هوائي": (0.5, -0.8), "مائي": (-0.3, 1.0)}

DEGREE_NAMES = {
    1: "الدرجة الأولى (الوالدان / الإخوة / الأبناء)",
    2: "الدرجة الثانية (الأجداد / الأعمام / الأخوال)",
    3: "الدرجة الثالثة (أبناء العمومة والخؤولة)",
    4: "المصاهرة والعائلة الممتدة",
    0: "خارج دائرة القرابة",
}

# مرشحو القرابة: houses[0] هو البيت الأساسي، gen=(فارق العمر عن المستفيد، الانحراف)
# البيوت المشتقة: الأب=4، الأم=10، الإخوة=3، الأبناء=5، أخو الأب=6 (3 من 4)، أخو الأم=12 (3 من 10)، الشريك=7
KIN_CANDIDATES = [
    {"key": "mother", "m": "الأم", "f": "الأم", "gender": "F", "degree": 1, "houses": [10, 4], "planets": ["القمر", "الزهرة"], "gen": (27, 7)},
    {"key": "father", "m": "الأب", "f": "الأب", "gender": "M", "degree": 1, "houses": [4, 10], "planets": ["الشمس", "زحل"], "gen": (31, 7)},
    {"key": "sister", "m": "الأخت", "f": "الأخت", "gender": "F", "degree": 1, "houses": [3, 11], "planets": ["الزهرة", "عطارد"], "gen": (0, 9)},
    {"key": "brother", "m": "الأخ", "f": "الأخ", "gender": "M", "degree": 1, "houses": [3, 11], "planets": ["المريخ", "عطارد"], "gen": (0, 9)},
    {"key": "daughter", "m": "الابنة", "f": "الابنة", "gender": "F", "degree": 1, "houses": [5], "planets": ["الزهرة", "القمر"], "gen": (-27, 8), "adult_only": True},
    {"key": "son", "m": "الابن", "f": "الابن", "gender": "M", "degree": 1, "houses": [5], "planets": ["الشمس", "المريخ"], "gen": (-27, 8), "adult_only": True},
    {"key": "grandmother", "m": "الجدة", "f": "الجدة", "gender": "F", "degree": 2, "houses": [7, 1], "planets": ["زحل", "القمر"], "gen": (55, 9)},
    {"key": "grandfather", "m": "الجد", "f": "الجد", "gender": "M", "degree": 2, "houses": [7, 1], "planets": ["زحل", "الشمس"], "gen": (58, 9)},
    {"key": "paternal_aunt", "m": "العمة", "f": "العمة", "gender": "F", "degree": 2, "houses": [6, 5], "planets": ["الزهرة", "زحل"], "gen": (6, 12)},
    {"key": "paternal_uncle", "m": "العم", "f": "العم", "gender": "M", "degree": 2, "houses": [6, 5], "planets": ["زحل", "المريخ"], "gen": (6, 12)},
    {"key": "maternal_aunt", "m": "الخالة", "f": "الخالة", "gender": "F", "degree": 2, "houses": [12, 6], "planets": ["القمر", "عطارد"], "gen": (6, 12)},
    {"key": "maternal_uncle", "m": "الخال", "f": "الخال", "gender": "M", "degree": 2, "houses": [12, 6], "planets": ["عطارد", "المشتري"], "gen": (6, 12)},
    {"key": "cousin_f", "m": "بنت العم/العمة/الخال/الخالة", "f": "بنت العم/العمة/الخال/الخالة", "gender": "F", "degree": 3, "houses": [11, 5], "planets": ["الزهرة", "عطارد"], "gen": (0, 12)},
    {"key": "cousin_m", "m": "ابن العم/العمة/الخال/الخالة", "f": "ابن العم/العمة/الخال/الخالة", "gender": "M", "degree": 3, "houses": [11, 5], "planets": ["عطارد", "المريخ"], "gen": (0, 12)},
    {"key": "stepmother", "m": "زوجة الأب", "f": "زوجة الأب", "gender": "F", "degree": 4, "houses": [10, 8], "planets": ["الزهرة", "المريخ", "زحل"], "gen": (15, 10)},
    {"key": "mother_in_law", "m": "حماة (أم الشريك)", "f": "حماة (أم الشريك)", "gender": "F", "degree": 4, "houses": [10, 4], "planets": ["القمر", "زحل"], "gen": (27, 7), "adult_only": True},
    {"key": "father_in_law", "m": "حمو (أبو الشريك)", "f": "حمو (أبو الشريك)", "gender": "M", "degree": 4, "houses": [4, 10], "planets": ["الشمس", "زحل"], "gen": (31, 7), "adult_only": True},
    {"key": "spouse_sibling", "m": "أخو الشريك (السلف)", "f": "أخت الشريك (السلفة)", "gender": "A", "degree": 4, "houses": [9, 3], "planets": ["عطارد", "الزهرة"], "gen": (0, 10), "adult_only": True},
    {"key": "sibling_spouse", "m": "زوج الأخت (الصهر)", "f": "زوجة الأخ (السلفة)", "gender": "A", "degree": 4, "houses": [9, 7], "planets": ["الزهرة", "المريخ"], "gen": (0, 10), "adult_only": True},
    {"key": "spouse", "m": "الزوج/الخطيب (حالي أو سابق)", "f": "الزوجة/الخطيبة (حالية أو سابقة)", "gender": "S", "degree": 4, "houses": [7, 1], "planets": ["الزهرة", "المريخ"], "gen": (0, 10), "adult_only": True},
    {"key": "neighbor", "m": "جار", "f": "جارة", "gender": "A", "degree": 0, "houses": [3, 4], "planets": ["عطارد", "القمر"], "gen": (0, 18)},
    {"key": "friend", "m": "صديق", "f": "صديقة", "gender": "A", "degree": 0, "houses": [11, 3], "planets": ["المشتري", "الزهرة", "عطارد"], "gen": (0, 15)},
    {"key": "colleague", "m": "زميل أو مسؤول عمل", "f": "زميلة أو مسؤولة عمل", "gender": "A", "degree": 0, "houses": [10, 6], "planets": ["الشمس", "زحل", "عطارد"], "gen": (0, 16)},
    {"key": "rival", "m": "منافس أو شريك سابق", "f": "منافسة أو شريكة سابقة", "gender": "A", "degree": 0, "houses": [7, 5], "planets": ["الزهرة", "المريخ"], "gen": (0, 14)},
    {"key": "stranger", "m": "معرفة بعيدة أو شخص غريب", "f": "معرفة بعيدة أو شخصية غريبة", "gender": "A", "degree": 0, "houses": [9, 12, 8], "planets": ["نبتون", "راهو", "أورانوس"], "gen": (0, 20)},
]

HOUSE_TARGET = {
    1: "إضعاف صحة المستفيد وحيويته وحالته النفسية",
    2: "تعطيل الرزق وجلب الديون وضيق المعيشة",
    3: "قطع الصلة بالإخوة والجيران وتعطيل الدراسة والسفر القريب",
    4: "تخريب استقرار البيت والعلاقة بالوالدين وتعطيل العقارات",
    5: "تعطيل الإنجاب أو إيذاء الأبناء أو إفساد العلاقات العاطفية",
    6: "أمراض مزمنة وإرهاق وتعطيل العمل اليومي",
    7: "تعطيل الزواج أو التفريق بين الزوجين وإفساد الشراكات",
    8: "أزمات وخسائر مفاجئة وخوف مزمن وكوابيس",
    9: "منع السفر والهجرة وإغلاق أبواب التوفيق العلمي والديني",
    10: "إسقاط المكانة والعمل والسمعة",
    11: "قطع الأصدقاء وتعطيل الأمنيات والدخل الإضافي",
    12: "العزلة والأرق والحبس النفسي والمكائد الخفية",
}

MOTIVES = {
    "love": {
        "title": "التعلق العاطفي: الرغبة في الزواج بالمستفيد أو إبعاد من يزاحمه (سحر محبة/جلب/تفريق)",
        "detail": "ارتباط حاكم البيت 12 بالزهرة أو ببيوت العاطفة والشراكة (5 و7) يدل على أن أصل الأذية رغبة في التملك العاطفي: إما جلب المستفيد وإخضاعه، أو تفريقه عن شريكه أو خطيبه لأن الفاعل يرى نفسه أحق به.",
        "goal": "إخضاع المستفيد عاطفياً، أو تعطيل زواجه من غيره، أو التفريق بينه وبين شريكه."
    },
    "money": {
        "title": "الطمع المالي: مال أو إرث أو شراكة أو منفعة مادية",
        "detail": "ارتباط الدليل ببيوت المال والمواريث (2 و8) أو بالمشتري بزوايا صعبة يدل على سبب مادي صرف: نزاع على ميراث أو دين أو شراكة، أو رغبة في الاستحواذ على ما يملكه المستفيد أو إفقاره.",
        "goal": "إفقار المستفيد وقطع رزقه وإعاقة تحصيله لحقه المالي لصالح الفاعل."
    },
    "revenge": {
        "title": "الانتقام والحقد الدفين بسبب خلاف قديم أو جرح كبرياء",
        "detail": "الزوايا الصعبة من المريخ أو زحل أو بلوتو مع حاكم البيت 12 تكشف عداءً ثأرياً: الفاعل يرى أنه تعرض لظلم أو إهانة أو خسارة من المستفيد، ويريد رد الصاع بتعطيل حياته وصحته وهدوئه.",
        "goal": "إيلام المستفيد نفسياً وجسدياً وتدمير استقراره كرد فعل على موقف سابق."
    },
    "envy": {
        "title": "الحسد والغيرة من النجاح أو المكانة أو النعمة الظاهرة",
        "detail": "وقوع الدليل في البيتين 10 و11 أو اتصاله بالشمس والمشتري يدل على أن المحرك هو الغيرة من نجاح المستفيد ومكانته وقبوله الاجتماعي، مع رغبة في زوال النعمة وإسقاط الصورة التي يراها الناس عنه.",
        "goal": "إسقاط مكانة المستفيد المهنية والاجتماعية وتشويه سمعته."
    },
    "property": {
        "title": "نزاع على بيت أو أرض أو نفوذ داخل الأسرة",
        "detail": "ارتباط الدليل بالبيت 4 أو 8 مع زحل يدل على صراع حول العقار أو المسكن أو الإرث العائلي أو السيطرة على القرار داخل الأسرة.",
        "goal": "إبعاد المستفيد عن المسكن أو الإرث أو القرار العائلي وإضعاف موقعه داخل الأسرة."
    },
    "control": {
        "title": "السيطرة والتعلق المرضي (ربط وتحكم وإبقاء المستفيد تحت النفوذ)",
        "detail": "اتصال حاكم البيت 12 ببلوتو أو نبتون أو القمر مع وقوعه في البيوت 1 أو 8 أو 12 يشير إلى رغبة في الهيمنة النفسية على المستفيد: عمل ربط وتحكم يبقيه تابعاً أو منعزلاً أو عاجزاً عن اتخاذ قراره.",
        "goal": "عزل المستفيد والتحكم بقراراته وإبقاؤه معتمداً على الفاعل أو خائفاً منه."
    },
}

# ==================== دوال الحروف والأبجدية ====================


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
    if number <= 0:
        return 12
    return ((number - 1) % 12) + 1


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


# ==================== أدوات مساعدة فلكية ====================
ASPECT_W = {"اقتران": 2.0, "مقابلة": 1.5, "تربيع": 1.5, "تثليث": 1.0, "تسديس": 0.8}
HARD_ASPECTS = ("اقتران", "مقابلة", "تربيع")


def aspect_info(l1: float, l2: float, orb: float = 6.0) -> Optional[Tuple[str, float]]:
    """يعيد (اسم الزاوية، الانحراف عن الدقة) أو None."""
    diff = abs(l1 - l2) % 360
    if diff > 180:
        diff = 360 - diff
    for name, angle in (("اقتران", 0), ("تسديس", 60), ("تربيع", 90), ("تثليث", 120), ("مقابلة", 180)):
        d = abs(diff - angle)
        if d <= orb:
            return name, d
    return None


def element_of(sign: str) -> str:
    if sign in FIRE_SIGNS:
        return "ناري"
    if sign in EARTH_SIGNS:
        return "ترابي"
    if sign in AIR_SIGNS:
        return "هوائي"
    return "مائي"


def dignity_of(body: str, sign: str) -> Tuple[int, str]:
    if body not in EXALTATION:
        return 0, "حالة عادية"
    if SIGN_RULERS.get(sign) == body:
        return 2, "في بيته (قوي)"
    if EXALTATION.get(body) == sign:
        return 3, "في شرفه (قوي جداً)"
    opp = ZODIAC_SIGNS[(ZODIAC_SIGNS.index(sign) + 6) % 12]
    if SIGN_RULERS.get(opp) == body:
        return -2, "في وباله (ضعيف)"
    if EXALTATION.get(body) == opp:
        return -3, "في هبوطه (ضعيف جداً)"
    return 0, "حالة عادية"


def softmax(scores: List[float], temp: float = 2.0) -> List[float]:
    m = max(scores)
    exps = [math.exp((s - m) / temp) for s in scores]
    tot = sum(exps)
    return [e / tot for e in exps]


# ==================== محرك قراءة الخريطة الفلكية والفراسة ====================
class AutoChartReader:
    def __init__(self, jd: float, lat: float, lng: float):
        self.jd = jd
        self.lat = lat
        self.lng = lng
        self.planets_data: List[Dict[str, Any]] = []
        self.P: Dict[str, Dict[str, Any]] = {}
        self.ascendant_sign_idx = 0
        self.ascendant_lon = 0.0
        self.evidence: Dict[str, List[str]] = {}
        self._calculate()

    # ---------- الحسابات الأساسية ----------
    def _calculate(self):
        flags = swe.FLG_MOSEPH | swe.FLG_SPEED
        cusps, ascmc = swe.houses(self.jd, self.lat, self.lng, b'W')
        self.ascendant_lon = ascmc[0]
        self.ascendant_sign_idx = int(self.ascendant_lon // 30)

        for b_name, b_id in BODIES.items():
            pos, _ = swe.calc_ut(self.jd, b_id, flags)
            lon = pos[0] % 360
            sign_idx = int(lon // 30)
            sign = ZODIAC_SIGNS[sign_idx]
            house_num = ((sign_idx - self.ascendant_sign_idx) % 12) + 1
            mean = MEAN_SPEED.get(b_name)
            ratio = abs(pos[3]) / mean if mean else 1.0
            self.planets_data.append({
                "body": b_name, "lon": lon, "sign": sign, "sign_idx": sign_idx,
                "house": house_num, "is_retro": pos[3] < 0, "speed": pos[3],
                "speed_ratio": ratio,
                "dignity": dignity_of(b_name, sign),
            })

        rahu = next((p for p in self.planets_data if p["body"] == "راهو"), None)
        if rahu:
            ketu_lon = (rahu["lon"] + 180) % 360
            ketu_sign_idx = int(ketu_lon // 30)
            self.planets_data.append({
                "body": "كيتو", "lon": ketu_lon, "sign": ZODIAC_SIGNS[ketu_sign_idx],
                "sign_idx": ketu_sign_idx,
                "house": ((ketu_sign_idx - self.ascendant_sign_idx) % 12) + 1,
                "is_retro": True, "speed": -0.05, "speed_ratio": 1.0, "dignity": (0, "حالة عادية"),
            })
        self.P = {p["body"]: p for p in self.planets_data}

    def _ev(self, section: str, text: str):
        self.evidence.setdefault(section, []).append(text)

    def _get_aspect_between(self, p1_lon: float, p2_lon: float, orb: float = 6.0) -> Optional[str]:
        res = aspect_info(p1_lon, p2_lon, orb)
        return res[0] if res else None

    def _house_sign(self, house: int) -> str:
        return ZODIAC_SIGNS[(self.ascendant_sign_idx + house - 1) % 12]

    # ---------- النجوم الثابتة ----------
    def check_fixed_stars(self) -> List[str]:
        precession = (self.jd - 2451545.0) / 365.25 * 50.29 / 3600.0
        star_clues = []
        for p in self.planets_data:
            if p["house"] in [1, 6, 8, 12]:
                for star_name, star_info in MAJOR_FIXED_STARS.items():
                    star_lon = (star_info["lon"] + precession) % 360
                    diff = abs(p["lon"] - star_lon)
                    if diff > 180:
                        diff = 360 - diff
                    if diff <= 1.5:
                        star_clues.append(
                            f"⭐ **اقتران نجمي مؤثر:** كوكب ({p['body']}) مقترن بالنجم الثابت **[{star_name}]**. الدلالة: {star_info['nature']}."
                        )
        return star_clues

    # ---------- توقيت الأذية ----------
    def estimate_damage_timing(self) -> str:
        h12_sign = self._house_sign(12)
        h12_ruler = SIGN_RULERS.get(h12_sign)
        ruler_p = self.P.get(h12_ruler)
        if not ruler_p:
            return "توقيت الأذية: غير محدد بدقة."

        arc_diff = abs(ruler_p["lon"] - self.ascendant_lon)
        if arc_diff > 180:
            arc_diff = 360 - arc_diff
        calculated_months = int((arc_diff / 30) * 12) + 1
        if calculated_months > 24:
            calculated_months = calculated_months % 24 + 1

        if h12_sign in CARDINAL_SIGNS:
            status_type = "أذية جديدة وطارئة"
            timing = f"حدثت خلال الأيام أو الأسابيع القليلة الماضية، منذ حوالي {int(arc_diff % 30) + 1} يوماً."
        elif h12_sign in FIXED_SIGNS:
            status_type = "أذية قديمة ومتأصلة ومستمرة"
            timing = f"أذية تراكمية منذ أشهر طويلة (البدء منذ حوالي {int(arc_diff / 10) + 1} إلى {int(arc_diff / 5) + 2} شهراً)."
        else:
            status_type = "أذية متجددة (متوسطة الحداثة)"
            timing = f"بدأت قبل نحو {max(1, calculated_months - 1)} إلى {calculated_months + 1} شهراً."
        return f"⏱️ **فحص توقيت الأذية:** تصنف كـ **[{status_type}]**. {timing} (المسافة القوسية: {arc_diff:.2f}°)."

    # =====================================================================
    # محركات الفاعل (النسخة المطورة)
    # =====================================================================
    def estimate_gender(self, ruler: str, ruler_p: Dict, h12_sign: str, p12: List[str]) -> Dict[str, Any]:
        sec = "الجنس"
        score = 3 * PLANET_GENDER.get(ruler, 0)
        self._ev(sec, f"حاكم البيت 12 هو {ruler} ({'مذكر' if PLANET_GENDER.get(ruler, 0) > 0 else 'مؤنث' if PLANET_GENDER.get(ruler, 0) < 0 else 'محايد'}) → وزن 3.")
        ruler_masc = ruler_p["sign_idx"] % 2 == 0
        score += 1.5 * (1 if ruler_masc else -1)
        self._ev(sec, f"الحاكم في برج {ruler_p['sign']} ({'مذكر' if ruler_masc else 'مؤنث'}) → وزن 1.5.")
        h12_masc = ZODIAC_SIGNS.index(h12_sign) % 2 == 0
        score += 0.75 * (1 if h12_masc else -1)
        self._ev(sec, f"برج البيت 12 هو {h12_sign} ({'مذكر' if h12_masc else 'مؤنث'}) → وزن 0.75.")
        for b in p12:
            if b != ruler and b not in NODES:
                score += 0.5 * PLANET_GENDER.get(b, 0)
                self._ev(sec, f"{b} في البيت 12 يضيف دلالته.")
        for p in self.planets_data:
            if p["body"] != ruler and p["body"] not in NODES:
                if aspect_info(ruler_p["lon"], p["lon"], 5.0) and aspect_info(ruler_p["lon"], p["lon"], 5.0)[0] == "اقتران":
                    score += 0.5 * PLANET_GENDER.get(p["body"], 0)
                    self._ev(sec, f"اقتران الحاكم بـ{p['body']} يضيف دلالته.")
        prob_male = min(0.96, max(0.04, 1 / (1 + math.exp(-score / 3))))
        return {"prob_male": prob_male, "is_male": prob_male >= 0.5, "score": score}

    def estimate_age(self, ruler: str, ruler_p: Dict, p12: List[str]) -> Dict[str, Any]:
        sec = "العمر"
        base = PLANET_AGE.get(ruler, 35)
        adj = 0
        if ruler_p["is_retro"]:
            adj += 5
            self._ev(sec, "الحاكم راجع → يميل لعمر أكبر (+5).")
        if ruler_p["speed_ratio"] > 1.25:
            adj -= 3
            self._ev(sec, "الحاكم سريع السير → يميل لعمر أصغر (-3).")
        elif ruler_p["speed_ratio"] < 0.5:
            adj += 3
            self._ev(sec, "الحاكم بطيء السير → يميل لعمر أكبر (+3).")
        items = [(base + adj, 3.0)]
        self._ev(sec, f"عمر دلالة {ruler} ≈ {base} سنة (وزن 3).")
        disp = SIGN_RULERS.get(ruler_p["sign"])
        if disp and disp != ruler:
            items.append((PLANET_AGE.get(disp, 35), 1.0))
            self._ev(sec, f"حاكم برج الحاكم هو {disp} ≈ {PLANET_AGE.get(disp)} سنة (وزن 1).")
        for b in p12:
            if b != ruler:
                items.append((PLANET_AGE.get(b, 35), 1.0))
                self._ev(sec, f"{b} في البيت 12 ≈ {PLANET_AGE.get(b)} سنة (وزن 1).")
        wsum = sum(w for _, w in items)
        mean = sum(a * w for a, w in items) / wsum
        var = sum(w * (a - mean) ** 2 for a, w in items) / wsum
        sd = math.sqrt(var + 7 ** 2)
        mean = min(85, max(14, mean))
        lo, hi = max(12, int(round((mean - sd) / 5.0) * 5)), int(round((mean + sd) / 5.0) * 5)
        return {"mean": mean, "sd": sd, "range": (lo, hi)}

    def estimate_build(self, ruler: str, ruler_p: Dict, p12: List[str], is_male: bool) -> Dict[str, Any]:
        sec = "الطول والوزن"
        items = [(ruler, 3.0)]
        disp = SIGN_RULERS.get(ruler_p["sign"])
        if disp and disp != ruler:
            items.append((disp, 1.0))
        for b in p12:
            if b != ruler:
                items.append((b, 1.0))
        for p in self.planets_data:
            if p["body"] != ruler and p["body"] not in NODES:
                r = aspect_info(ruler_p["lon"], p["lon"], 5.0)
                if r and r[0] == "اقتران" and p["body"] not in [i[0] for i in items]:
                    items.append((p["body"], 1.0))
        wsum = sum(w for _, w in items)
        h_score = sum(PLANET_BUILD.get(b, (0, 0))[0] * w for b, w in items) / wsum
        w_score = sum(PLANET_BUILD.get(b, (0, 0))[1] * w for b, w in items) / wsum
        elem = element_of(ruler_p["sign"])
        h_score += ELEMENT_BUILD[elem][0]
        w_score += ELEMENT_BUILD[elem][1]
        self._ev(sec, "مساهمات القوام: " + "، ".join(f"{b}×{w:g}" for b, w in items) + f"، وعنصر برج الحاكم ({elem}).")
        if not is_male:
            h_score -= 0.6

        if h_score < -0.8:
            h_label = "قصير القامة"
        elif h_score < 0.5:
            h_label = "متوسط القامة"
        elif h_score < 1.3:
            h_label = "فوق المتوسط"
        else:
            h_label = "طويل القامة"
        if w_score < -0.8:
            w_label = "نحيف"
        elif w_score < 0.5:
            w_label = "متناسق / متوسط البنية"
        elif w_score < 1.2:
            w_label = "ممتلئ"
        else:
            w_label = "ضخم / زائد الوزن"

        height_cm = (176 if is_male else 163) + 5 * h_score
        bmi = min(36, max(17, 23.5 + 3 * w_score))
        weight_kg = bmi * (height_cm / 100) ** 2
        return {
            "h_label": h_label, "w_label": w_label,
            "height_range": (int(height_cm - 5), int(height_cm + 5)),
            "weight_range": (int(weight_kg - 6), int(weight_kg + 6)),
            "h_score": h_score, "w_score": w_score,
        }

    def analyze_perpetrator_physiognomy(self, h12_ruler: str, ruler_p: Optional[Dict[str, Any]],
                                        p12: List[str], build: Dict[str, Any]) -> Dict[str, str]:
        base = PLANET_PHYSIOGNOMY.get(h12_ruler, PLANET_PHYSIOGNOMY["عطارد"]).copy()
        base["height"] = f"{build['h_label']} (تقريباً {build['height_range'][0]}–{build['height_range'][1]} سم)"
        base["weight"] = f"{build['w_label']} (تقريباً {build['weight_range'][0]}–{build['weight_range'][1]} كجم)"

        if ruler_p:
            sign = ruler_p["sign"]
            if sign in WATER_SIGNS:
                base["eyes_size"] = "عيون واسعة، ناعسة أو مدمعة، ذات بريق مائي"
                base["lips"] = "شفاه ممتلئة وبارزة"
            elif sign in FIRE_SIGNS:
                base["skin"] = "بشرة حنطية مشربة بحمرة أو برونزية"
                base["eyes_color"] = "عسلي حاد، بني محمر، أو ذهبي"
                base["eyes_size"] = "عيون متوسطة ذات نظرة ثاقبة وسريعة"
            elif sign in EARTH_SIGNS:
                base["skin"] = "بشرة قمحية داكنة أو سمراء صافية"
                base["lips"] = "شفاه محددة، متوسطة إلى رقيقة"
            elif sign in AIR_SIGNS:
                base["eyes_size"] = "عيون متوسطة سريعة الحركة ونظرة متفحصة"

            for other in self.planets_data:
                if other["body"] != h12_ruler and other["body"] not in NODES:
                    r = aspect_info(ruler_p["lon"], other["lon"], 5.0)
                    if r and r[0] == "اقتران":
                        if other["body"] == "زحل":
                            base["skin"] = "بشرة داكنة أو شاحبة جافة"
                        elif other["body"] == "الزهرة":
                            base["eyes_size"] = "عيون واسعة وجميلة جداً ذات جاذبية ملفتة"
                            base["lips"] = "شفاه ممتلئة ومحددة بشكل واضح"
                        elif other["body"] == "المريخ":
                            base["face"] += " (تأثير المريخ: علامة أو ندبة أو احمرار)"

        extras = []
        for b in p12:
            if b != h12_ruler and b in PLANET_PHYSIOGNOMY and "face" in PLANET_PHYSIOGNOMY[b]:
                extras.append(f"تأثير {b} (كوكب في البيت 12): {PLANET_PHYSIOGNOMY[b]['face']}")
        base["extras"] = " | ".join(extras) if extras else "لا توجد كواكب في البيت 12 تعدل الملامح الأساسية."
        return base

    # ---------- القرابة ----------
    def _candidate_score(self, c: Dict, ruler: str, ruler_p: Dict, p12: List[str], pm: float,
                         est_age: float, est_sd: float, ben_age: float) -> float:
        s = 0.0
        h = ruler_p["house"]
        hs = c["houses"]
        if h == hs[0]:
            s += 4
        elif h in hs[1:]:
            s += 2.5
        pl = c["planets"]
        if ruler in pl:
            s += 3 if pl[0] == ruler else 2.2
        for b in p12:
            if b in pl:
                s += 1
        for b in pl:
            if b != ruler and b in self.P:
                a = aspect_info(ruler_p["lon"], self.P[b]["lon"], 6.0)
                if a:
                    s += ASPECT_W[a[0]] * (1 - a[1] / 12)
        if c["gender"] == "M":
            s += 6 * (pm - 0.5)
        elif c["gender"] == "F":
            s -= 6 * (pm - 0.5)
        expected = ben_age + c["gen"][0]
        sd = math.sqrt(c["gen"][1] ** 2 + est_sd ** 2)
        z = (est_age - expected) / sd
        s -= min(3.5, 0.45 * z * z)
        return s

    def analyze_exact_kinship(self, ruler: str, ruler_p: Dict, p12: List[str], pm: float,
                              est_age: float, est_sd: float, ben_gender: str, ben_age: float) -> Dict[str, Any]:
        sec = "القرابة"
        perp_male = pm >= 0.5
        cands = []
        for c in KIN_CANDIDATES:
            c = dict(c)
            if c.get("adult_only") and ben_age < 20:
                continue
            if c["key"] in ("daughter", "son") and ben_age - 27 < 0:
                continue
            g = c["gender"]
            if g == "S":
                g = "F" if ben_gender == "ذكر" else "M"
            elif g == "A":
                g = "M" if perp_male else "F"
            c["gender_resolved"] = g
            c["label"] = c["m"] if g == "M" else c["f"]
            cands.append(c)

        scores = [self._candidate_score(
            dict(c, gender=c["gender"] if c["gender"] in ("M", "F") else "A"),
            ruler, ruler_p, p12, pm, est_age, est_sd, ben_age) for c in cands]
        probs = softmax(scores, 2.0)
        for c, s, p in zip(cands, scores, probs):
            c["score"], c["prob"] = s, p

        ranking = sorted(cands, key=lambda x: x["prob"], reverse=True)
        deg_prob = {d: sum(c["prob"] for c in cands if c["degree"] == d) for d in (1, 2, 3, 4, 0)}
        best_per_degree = {}
        for d in (1, 2, 3, 4, 0):
            grp = [c for c in ranking if c["degree"] == d]
            if grp:
                tot = sum(c["prob"] for c in grp) or 1
                best_per_degree[d] = {
                    "label": grp[0]["label"], "share": grp[0]["prob"] / tot,
                    "alts": [(g["label"], g["prob"] / tot) for g in grp[1:3]],
                }

        top = ranking[0]
        top_degree = top["degree"]
        # جهة القرابة (أبوية/أمومية) للدرجات 2 و3
        pat, mat = 0.0, 0.0
        if ruler_p["house"] == 6:
            pat += 2
        if ruler_p["house"] == 12:
            mat += 2
        for b, bucket in (("الشمس", "p"), ("زحل", "p"), ("القمر", "m"), ("الزهرة", "m")):
            a = aspect_info(ruler_p["lon"], self.P[b]["lon"], 6.0)
            if a:
                if bucket == "p":
                    pat += ASPECT_W[a[0]]
                else:
                    mat += ASPECT_W[a[0]]
        if abs(pat - mat) < 0.5:
            side = "لا ترجيح واضح بين جهة الأب وجهة الأم"
        else:
            side = "يميل لجهة الأب (الأعمام/العمات)" if pat > mat else "يميل لجهة الأم (الأخوال/الخالات)"

        self._ev(sec, f"حاكم البيت 12 ({ruler}) في البيت {ruler_p['house']} → البيت الأساسي لدلالة القرابة.")
        self._ev(sec, f"الجنس المرجح للفاعل: {'ذكر' if perp_male else 'أنثى'} ({pm:.0%} ذكر) استُخدم لتصفية المرشحين.")
        self._ev(sec, f"العمر المقدر ({est_age:.0f}) قورن بالعمر المتوقع لكل صلة نسبة لعمر المستفيد ({ben_age:.0f}).")
        self._ev(sec, "البيوت المشتقة: الأب 4، الأم 10، الإخوة 3، الأبناء 5، أعمام 6، أخوال 12، الشريك 7.")

        return {
            "ranking": ranking[:8], "best_per_degree": best_per_degree, "deg_prob": deg_prob,
            "top": top, "top_degree": top_degree, "side": side,
            "relative_prob": sum(p for d, p in deg_prob.items() if d in (1, 2, 3)),
        }

    # ---------- مكان الإقامة ----------
    def analyze_location_status(self, h12_sign: str, ruler_p: Dict) -> Dict[str, Any]:
        sec = "مكان الإقامة"
        h = ruler_p["house"]
        sc = {"same_city": 0.0, "other_city": 0.0, "abroad": 0.0}

        same = {1: 3, 3: 2.5, 4: 3, 7: 2.5, 10: 2.5, 6: 1.5, 2: 1.5, 11: 1.5, 5: 1}
        other = {2: 1, 5: 1, 8: 1.5, 11: 1, 9: 0.8, 12: 0.8, 6: 0.5}
        abroad = {9: 3, 12: 2, 8: 1, 3: -1}
        sc["same_city"] += same.get(h, 0)
        sc["other_city"] += other.get(h, 0)
        sc["abroad"] += abroad.get(h, 0)
        self._ev(sec, f"الحاكم في البيت {h}: أوتاد وبيوت قريبة ترجح القرب، والبيتان 9 و12 ترجحان البعد.")

        sign = ruler_p["sign"]
        if sign in FIXED_SIGNS:
            sc["same_city"] += 1.2
            self._ev(sec, "برج الحاكم ثابت → استقرار في المكان.")
        elif sign in MUTABLE_SIGNS:
            sc["other_city"] += 1.0
            sc["abroad"] += 0.8
            self._ev(sec, "برج الحاكم منقلب → تنقل وسفر.")
        else:
            sc["other_city"] += 0.6
            self._ev(sec, "برج الحاكم متحرك → ميل متوسط للحركة.")

        if ruler_p["speed_ratio"] > 1.25:
            sc["other_city"] += 0.6
            self._ev(sec, "الحاكم سريع السير → كثرة تنقل.")

        h9_ruler = SIGN_RULERS.get(self._house_sign(9))
        h9_p = self.P.get(h9_ruler)
        if h9_p and h9_ruler != ruler_p["body"]:
            a = aspect_info(ruler_p["lon"], h9_p["lon"], 6.0)
            if a and a[0] in ("اقتران", "مقابلة"):
                sc["abroad"] += 1.5
                self._ev(sec, f"اتصال الحاكم بحاكم البيت 9 ({h9_ruler}) بـ{a[0]} → رابط بالغربة.")
        for b in ("أورانوس", "راهو"):
            a = aspect_info(ruler_p["lon"], self.P[b]["lon"], 5.0)
            if a and a[0] in ("اقتران", "مقابلة"):
                sc["abroad"] += 1.5
                self._ev(sec, f"اتصال الحاكم بـ{b} ({a[0]}) → دليل غربة.")
        for hn in (3, 4):
            hr = SIGN_RULERS.get(self._house_sign(hn))
            hp = self.P.get(hr)
            if hp and hr != ruler_p["body"]:
                a = aspect_info(ruler_p["lon"], hp["lon"], 6.0)
                if a:
                    sc["same_city"] += 1.0
                    self._ev(sec, f"اتصال الحاكم بحاكم البيت {hn} ({hr}) → قرب من المسكن.")

        keys = ["same_city", "other_city", "abroad"]
        probs = dict(zip(keys, softmax([sc[k] for k in keys], 1.6)))
        best = max(probs, key=probs.get)
        names = {"same_city": "في نفس مدينة الميلاد المدخلة", "other_city": "في مدينة أخرى داخل نفس البلد", "abroad": "في دولة أخرى (غربة)"}
        details = {
            "same_city": "الدلائل تضع الفاعل في النطاق القريب من مسكن المستفيد ومحيطه اليومي، ويسهل عليه المتابعة والاحتكاك المباشر.",
            "other_city": "الفاعل داخل حدود نفس الدولة لكنه في مدينة أو محافظة بعيدة عن المستفيد، مع تنقل أو اتصال عن بعد.",
            "abroad": "الفاعل يقيم خارج بلد الميلاد (غربة أو هجرة أو سفر طويل) ويدير الأذى عن بُعد أو عبر وسيط.",
        }
        direction = ELEMENT_DIRECTION[element_of(sign)]
        return {
            "status": names[best], "details": details[best], "probs": probs, "names": names,
            "direction": direction,
        }

    # ---------- الدافع والهدف ----------
    def analyze_motive_and_enmity(self, ruler: str, ruler_p: Dict) -> Dict[str, Any]:
        sec = "الدافع"
        h = ruler_p["house"]
        M = {k: 0.0 for k in MOTIVES}
        M["envy"] += 1.2  # قاعدة الحسد

        def asp(b, orb=6.0):
            if b == ruler or b not in self.P:
                return None
            return aspect_info(ruler_p["lon"], self.P[b]["lon"], orb)

        if h in (5, 7):
            M["love"] += 3
            self._ev(sec, f"الحاكم في البيت {h} (عاطفة/شراكة) → دافع عاطفي.")
        a = asp("الزهرة")
        if a:
            M["love"] += 1.3 * ASPECT_W[a[0]]
            self._ev(sec, f"اتصال الحاكم بالزهرة ({a[0]}) → دافع عاطفي.")
        h7_planets = [p["body"] for p in self.planets_data if p["house"] == 7 and p["body"] in MALEFICS]
        if h7_planets:
            M["love"] += 1
            self._ev(sec, "نحس في البيت 7 → اضطراب عاطفي/زواجي.")

        if h in (2, 8):
            M["money"] += 3.5
            self._ev(sec, f"الحاكم في البيت {h} (مال/إرث) → دافع مالي.")
        if h == 11:
            M["money"] += 1
        a = asp("المشتري")
        if a and a[0] in HARD_ASPECTS:
            M["money"] += ASPECT_W[a[0]]
            self._ev(sec, f"زاوية صعبة بالمشتري ({a[0]}) → طمع مالي.")

        for b in ("المريخ", "زحل", "بلوتو"):
            a = asp(b)
            if a and a[0] in HARD_ASPECTS:
                M["revenge"] += 1.2 * ASPECT_W[a[0]]
                self._ev(sec, f"زاوية صعبة بـ{b} ({a[0]}) → حقد وانتقام.")
        if ruler_p["is_retro"]:
            M["revenge"] += 1
            self._ev(sec, "رجوع الحاكم → حقد دفين قديم.")
        if h in (6, 8, 12):
            M["revenge"] += 1

        if h in (10, 11):
            M["envy"] += 3
            self._ev(sec, f"الحاكم في البيت {h} (مكانة/أصدقاء) → غيرة من النجاح.")
        for b in ("الشمس", "المشتري"):
            a = asp(b)
            if a:
                M["envy"] += 1
                self._ev(sec, f"اتصال الحاكم بـ{b} → حسد من المكانة.")

        if h == 4:
            M["property"] += 3
        if h == 8:
            M["property"] += 1.5
        a = asp("زحل")
        if a and h in (4, 8, 3):
            M["property"] += 1
        if h == 4:
            self._ev(sec, "الحاكم في البيت 4 (بيت/أرض/عائلة) → نزاع عقاري أو عائلي.")

        if h in (1, 8, 12):
            M["control"] += 2.5
            self._ev(sec, f"الحاكم في البيت {h} → ميل للتحكم والهيمنة.")
        for b in ("بلوتو", "نبتون", "القمر"):
            a = asp(b)
            if a and a[0] in ("اقتران", "مقابلة"):
                M["control"] += 1.2 * ASPECT_W[a[0]]
                self._ev(sec, f"{a[0]} مع {b} → سيطرة وتعلق.")

        order = sorted(M, key=M.get, reverse=True)
        primary, secondary = order[0], order[1]
        total = sum(max(v, 0.01) for v in M.values())

        # المجالات المستهدفة: أكثر البيوت تضرراً من النحوس ومن حاكم البيت 12
        target_scores = {}
        for hn in range(1, 13):
            sc = 0.0
            for p in self.planets_data:
                if p["house"] == hn and p["body"] in MALEFICS:
                    sc += 1.5
            hr = SIGN_RULERS.get(self._house_sign(hn))
            hp = self.P.get(hr)
            if hp:
                if hp["house"] in (6, 8, 12) and hn not in (6, 8, 12):
                    sc += 1
                for mal in ("المريخ", "زحل", "بلوتو"):
                    if mal != hr:
                        a = aspect_info(hp["lon"], self.P[mal]["lon"], 5.0)
                        if a and a[0] in HARD_ASPECTS:
                            sc += 1
                if hr != ruler:
                    a = aspect_info(hp["lon"], ruler_p["lon"], 6.0)
                    if a:
                        sc += 2 if a[0] == "اقتران" else 1.5 if a[0] in HARD_ASPECTS else 0.5
            if ruler_p["house"] == hn and hn != 12:
                sc += 1
            target_scores[hn] = sc
        top_targets = sorted(target_scores, key=target_scores.get, reverse=True)[:3]
        top_targets = [t for t in top_targets if target_scores[t] > 0] or [12]

        return {
            "primary_key": primary, "primary_motive": MOTIVES[primary]["title"],
            "motive_details": MOTIVES[primary]["detail"], "goal": MOTIVES[primary]["goal"],
            "primary_share": max(M[primary], 0.01) / total,
            "secondary_motive": MOTIVES[secondary]["title"], "secondary_share": max(M[secondary], 0.01) / total,
            "targets": [(t, HOUSE_TARGET[t]) for t in top_targets],
        }

    # ---------- حروف الاسم الأول ----------
    def detect_perpetrator_name_letters(self, ruler: str, ruler_p: Dict, p12: List[str]) -> Dict[str, Any]:
        h12_sign = self._house_sign(12)
        elem = element_of(h12_sign)
        scores: Dict[str, float] = {}
        sources: Dict[str, List[str]] = {}
        width = 360 / 28

        def add(letter, w, why):
            scores[letter] = scores.get(letter, 0) + w
            sources.setdefault(letter, []).append(why)

        def by_mansion(lon, w, why):
            idx = int(lon // width) % 28
            add(ABJAD_ORDER[idx], w, f"{why} ({MANSIONS[idx]})")
            pos = lon - idx * width
            if pos < 1.5:
                j = (idx - 1) % 28
                add(ABJAD_ORDER[j], w * 0.35, f"{why} - حدّ منزلة {MANSIONS[j]}")
            elif pos > width - 1.5:
                j = (idx + 1) % 28
                add(ABJAD_ORDER[j], w * 0.35, f"{why} - حدّ منزلة {MANSIONS[j]}")

        by_mansion(ruler_p["lon"], 3.0, f"منزلة {ruler} (حاكم البيت 12)")
        cusp12 = (self.ascendant_lon + 330) % 360
        by_mansion(cusp12, 2.0, "منزلة رأس البيت 12")
        for b in p12:
            if b != ruler and b in self.P:
                by_mansion(self.P[b]["lon"], 1.5, f"منزلة {b} (في البيت 12)")
        for l in ELEMENT_LETTERS[elem]:
            add(l, 0.7, f"من حروف الطبع {elem}")

        total = sum(scores.values())
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:6]
        top_letters = [{"letter": l, "share": s / total, "why": " + ".join(sources[l][:2])} for l, s in ranked]
        self._ev("الحروف", f"الحروف مأخوذة من منازل القمر الـ28 بترتيب الأبجد، مع طبع برج البيت 12 ({h12_sign} - {elem}).")
        return {
            "h12_sign": h12_sign, "element_desc": f"طابع {elem}",
            "letters_list": ELEMENT_LETTERS[elem], "top_letters": top_letters,
        }

    # ---------- الواجهة الرئيسية لتحليل الفاعل ----------
    def analyze_magic_perpetrator(self, ben_gender: str = "ذكر", ben_age: float = 30.0) -> Dict[str, Any]:
        self.evidence = {}
        h12_sign = self._house_sign(12)
        ruler = SIGN_RULERS[h12_sign]
        ruler_p = self.P[ruler]
        p12 = [p["body"] for p in self.planets_data if p["house"] == 12]

        gender = self.estimate_gender(ruler, ruler_p, h12_sign, p12)
        age = self.estimate_age(ruler, ruler_p, p12)
        build = self.estimate_build(ruler, ruler_p, p12, gender["is_male"])
        physio = self.analyze_perpetrator_physiognomy(ruler, ruler_p, p12, build)
        kin = self.analyze_exact_kinship(ruler, ruler_p, p12, gender["prob_male"], age["mean"], age["sd"], ben_gender, ben_age)
        location = self.analyze_location_status(h12_sign, ruler_p)
        motive = self.analyze_motive_and_enmity(ruler, ruler_p)
        letters = self.detect_perpetrator_name_letters(ruler, ruler_p, p12)

        # دمج العمر الفلكي مع عمر الصلة الأرجح (متوسط مرجح بعكس التباين)
        top = kin["top"]
        exp_age = ben_age + top["gen"][0]
        w1, w2 = 1 / age["sd"] ** 2, 1 / top["gen"][1] ** 2
        blended = (age["mean"] * w1 + exp_age * w2) / (w1 + w2)
        bsd = math.sqrt(1 / (w1 + w2))
        age["blended"] = blended
        age["blended_range"] = (max(10, int(round((blended - bsd) / 1.0))), int(round(blended + bsd)))

        d_score, d_label = ruler_p["dignity"]
        if d_score >= 2 and ruler_p["house"] in (1, 4, 7, 10):
            power = "قوي النفوذ وقادر على المتابعة والتنفيذ بنفسه"
        elif d_score <= -2 or ruler_p["house"] in (6, 8, 12):
            power = "ضعيف الموقف أو يعمل في الخفاء ويعتمد على وسطاء"
        else:
            power = "متوسط القدرة والنفوذ"

        saturn_aff = any(p["body"] == "زحل" and p["house"] in [6, 8, 12] for p in self.planets_data)
        mars_aff = any(p["body"] == "المريخ" and p["house"] in [6, 8, 12] for p in self.planets_data)
        ketu_aff = any(p["body"] == "كيتو" and p["house"] in [6, 8, 12] for p in self.planets_data)
        nept_aff = any(p["body"] == "نبتون" and p["house"] in [6, 8, 12] for p in self.planets_data)
        nature = []
        if saturn_aff:
            nature.append("أثر زحل (سحر أرضي ثقيل ومقابر)")
        if mars_aff:
            nature.append("أثر المريخ (سحر ناري/مرشوش حاد)")
        if ketu_aff:
            nature.append("أثر الكيتو (سحر أسود وعقد مظلمة)")
        if nept_aff:
            nature.append("أثر نبتون (سحر سائل أو أوهام وتخييلات)")
        if not nature:
            nature.append("أذى طاقي خفي وطلاسم مدبرة عن بُعد")

        return {
            "h12_sign": h12_sign, "h12_ruler": ruler, "h12_ruler_house": ruler_p["house"],
            "ruler_dignity": d_label, "power": power,
            "gender": gender,
            "perpetrator_gender": f"امرأة (أنثى) - احتمال {1 - gender['prob_male']:.0%}" if not gender["is_male"] else f"رجل (ذكر) - احتمال {gender['prob_male']:.0%}",
            "age": age,
            "build": build,
            "physiognomy": physio,
            "kin": kin, "location": location, "motive": motive, "letters": letters,
            "star_clues": self.check_fixed_stars(),
            "damage_timing": self.estimate_damage_timing(),
            "planets_in_12": p12, "nature_clues": nature,
            "evidence": self.evidence,
        }

    # ---------- التشخيص العام ----------
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
        h12_sign = self._house_sign(12)
        if "حسد" in diagnosis_type:
            medium_used = "إصابة طاقية مباشرة عبر نظرة حاسدة دون أثر مادي."
            delivery_method = "تأثير مباشر على الهالة الطاقية والنشاط الحيوي."
        else:
            medium_used = ("استخدام أثر شخصي مادي (ملابس، شعر، أو صورة) لربط الأثير." if h8_planets
                           else "اعتماد مباشر على الاسم الثلاثي واسم الأم طاقياً.")
            if h12_sign in FIRE_SIGNS:
                delivery_method = "محرّق (تعريض العمل للنار أو البخور المظلم)."
            elif h12_sign in WATER_SIGNS:
                delivery_method = "مرشوش (عمل سائل رُشّ أو طُرح في ماء جارٍ)."
            elif h12_sign in EARTH_SIGNS:
                delivery_method = "مدفون (سحر أرضي دُفن في تراب أو مقابر)."
            else:
                delivery_method = "مأكول أو مشروب."
        return {"medium_used": medium_used, "delivery_method": delivery_method}


# ==================== العلاج الروحاني ====================
def suggest_spiritual_treatment(val_first: int, val_mother: int) -> Dict[str, Any]:
    combined_val = val_first + val_mother
    treatment_index = (combined_val % 7) or 7
    treatments_db = {
        1: {"surah_name": "سورة البقرة", "surah_num": 2, "verse_num": "الآية 102 والخواتيم", "verse_text": "وَاتَّبَعُوا مَا تَتْلُوا الشَّيَاطِينُ...", "repetition": "تكرار الآية (102) 21 مرة يومياً", "method": "القراءة على إناء ماء والشرب منه والاغتسال."},
        2: {"surah_name": "سورة الأعراف", "surah_num": 7, "verse_num": "الآيات 117 - 122", "verse_text": "وَأَوْحَيْنَا إِلَىٰ مُوسَىٰ أَنْ أَلْقِ عَصَاكَ...", "repetition": "تكرار الآيات 41 مرة بعد الفجر", "method": "القراءة على زيت زيتون ودهن مواضع الألم."},
        3: {"surah_name": "سورة يونس", "surah_num": 10, "verse_num": "الآيتان 81 و 82", "verse_text": "فَلَمَّا أَلْقَوْا قَالَ مُوسَىٰ مَا جِئْتُم بِهِ السِّحْرُ...", "repetition": "تكرار الآيتين 70 مرة يومياً", "method": "القراءة على ماء الشرب بنية إبطال السحر."},
        4: {"surah_name": "سورة طه", "surah_num": 20, "verse_num": "الآيات 65 إلى 69", "verse_text": "قَالُوا يَا مُوسَىٰ إِمَّا أَن تُلْقِيَ...", "repetition": "تكرار الآية (69) 33 مرة بعد كل صلاة", "method": "وضع اليد على الصدر وقراءة الآيات مع النفث."},
        5: {"surah_name": "سورة الإخلاص والمعوذتان", "surah_num": "112-114", "verse_num": "السور الثلاث مع آية الكرسي", "verse_text": "قُلْ أَعُوذُ بِرَبِّ الْفَلَقِ...", "repetition": "تكرار كل سورة 100 مرة صباحاً ومساءً", "method": "المسح باليدين على الجسد بعد القراءة."},
        6: {"surah_name": "سورة الصافات والحشر", "surah_num": "37 و 59", "verse_num": "أول الصافات وخواتيم الحشر", "verse_text": "وَالصَّافَّاتِ صَفًّا...", "repetition": "قراءة الصافات مرة وخواتيم الحشر 7 مرات", "method": "الاستماع بخشوع لآيات التحصين الشامل."},
        7: {"surah_name": "سورة الفاتحة وآية الكرسي", "surah_num": "1 و 2", "verse_num": "الفاتحة وآية الكرسي (255)", "verse_text": "اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ...", "repetition": "قراءة الفاتحة 7 مرات وآية الكرسي 21 مرة", "method": "القراءة على ماء طاهر والاستحمام به."}
    }
    return treatments_db.get(treatment_index, treatments_db[1])


# ==================== تقرير HTML ====================
HTML_CSS = """
body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #f8fafc; color: #1e293b; padding: 25px; line-height: 1.7; }
.container { max-width: 950px; margin: auto; background: #fff; padding: 35px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); }
h1 { text-align: center; color: #0f172a; font-size: 24px; }
.meta { text-align: center; color: #64748b; font-size: 14px; margin-bottom: 25px; border-bottom: 1px solid #e2e8f0; padding-bottom: 15px; }
h2 { color: #2563eb; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-top: 28px; font-size: 18px; }
.card { background: #f1f5f9; border-right: 4px solid #2563eb; padding: 15px; border-radius: 6px; margin-bottom: 15px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
table { width: 100%; border-collapse: collapse; margin-top: 8px; }
th, td { border: 1px solid #cbd5e1; padding: 6px 10px; text-align: right; font-size: 14px; }
th { background: #e2e8f0; }
.warn { background: #fef3c7; border-right: 4px solid #d97706; padding: 12px; border-radius: 6px; font-size: 13px; }
.btn-print { display: block; width: 220px; margin: 30px auto; padding: 12px; background: #16a34a; color: white; text-align: center; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 15px; }
@media print { .btn-print { display: none; } .container { box-shadow: none; } }
"""

DISCLAIMER = ("⚠️ تنبيه: هذا التقرير تفسير رمزي تراثي ظنّي قائم على قواعد التنجيم والفراسة العربية، وليس دليلاً قاطعاً ولا يجوز "
              "اتهام أي شخص بناءً عليه. النسب المئوية ترجيحات داخلية للنظام وليست إحصاءات علمية. "
              "في الشكاوى الصحية أو النفسية أو الأسرية يُرجع إلى الطبيب المختص وأهل الخبرة.")


def build_html_report(ctx: Dict[str, Any]) -> str:
    e = html.escape
    m = ctx["magic"]
    phys = m["physiognomy"]
    kin = m["kin"]
    loc = m["location"]
    mot = m["motive"]
    let = m["letters"]
    age = m["age"]
    rows_kin = "".join(
        f"<tr><td>{c['prob']:.0%}</td><td>{e(c['label'])}</td><td>{e(DEGREE_NAMES[c['degree']])}</td></tr>"
        for c in kin["ranking"])
    rows_deg = ""
    for d in (1, 2, 3, 4, 0):
        b = kin["best_per_degree"].get(d)
        if b:
            alts = "، ".join(f"{a} ({s:.0%})" for a, s in b["alts"])
            rows_deg += (f"<tr><td>{e(DEGREE_NAMES[d])}</td><td>{kin['deg_prob'][d]:.0%}</td>"
                         f"<td><b>{e(b['label'])}</b> ({b['share']:.0%})</td><td>{e(alts)}</td></tr>")
    rows_loc = "".join(f"<tr><td>{e(loc['names'][k])}</td><td>{v:.0%}</td></tr>" for k, v in loc["probs"].items())
    targets = "".join(f"<li>البيت {t}: {e(txt)}</li>" for t, txt in mot["targets"])
    letters_rows = "".join(
        f"<tr><td style='font-size:20px'><b>{e(x['letter'])}</b></td><td>{x['share']:.0%}</td><td>{e(x['why'])}</td></tr>"
        for x in let["top_letters"])
    star_html = "".join(f"<li>{e(s)}</li>" for s in m["star_clues"]) or "<li>لا توجد اقترانات مباشرة بالنجوم النحسة الكبرى.</li>"
    tr = ctx["treatment"]
    timing = m["damage_timing"].replace("**", "")

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><title>التقرير الفلكي - {e(ctx['first_name'])}</title><style>{HTML_CSS}</style></head>
<body><div class="container">
<h1>🔮 التقرير الفلكي الشامل وكشف الفراسة والدوافع</h1>
<div class="meta"><b>المستفيد:</b> {e(ctx['first_name'])} | <b>اسم الأم:</b> {e(ctx['mother_name'])} | <b>مكان الميلاد:</b> {e(ctx['country'])} - {e(ctx['city'])}</div>
<div class="warn">{e(DISCLAIMER)}</div>

<h2>📊 ملخص العناصر الفلكية والحرفية</h2>
<div class="card">
<p><b>الطالع:</b> {e(ctx['asc_sign'])} | <b>حاكم البيت 12:</b> {e(m['h12_ruler'])} (البيت {m['h12_ruler_house']}) - {e(m['ruler_dignity'])}</p>
<p><b>البرج الباطني:</b> {e(ctx['zodiac_name'])} | <b>النوء:</b> {e(ctx['naw'])} | <b>المجموع الكلي:</b> {ctx['total']} | <b>النتيجة النهائية:</b> {ctx['final']}</p>
</div>

<h2>🕵️ ملف الفاعل: الجنس والعمر والشكل</h2>
<div class="card" style="border-right-color:#d97706;">
<div class="grid">
<div><b>👤 الجنس:</b> {e(m['perpetrator_gender'])}</div>
<div><b>🎂 العمر المقدر:</b> {age['range'][0]}–{age['range'][1]} سنة (بعد مطابقة الصلة: {age['blended_range'][0]}–{age['blended_range'][1]})</div>
<div><b>📏 الطول:</b> {e(phys['height'])}</div>
<div><b>⚖️ الوزن:</b> {e(phys['weight'])}</div>
<div><b>🎨 البشرة:</b> {e(phys['skin'])}</div>
<div><b>🙂 الوجه:</b> {e(phys['face'])}</div>
<div><b>👁️ العيون:</b> {e(phys['eyes_size'])} - {e(phys['eyes_color'])}</div>
<div><b>👄 الشفاه:</b> {e(phys['lips'])}</div>
<div><b>💇 الشعر:</b> {e(phys['hair'])}</div>
<div><b>💼 المهنة:</b> {e(phys['job'])}</div>
</div>
<p><b>قوة الفاعل:</b> {e(m['power'])}</p>
<p><small>{e(phys['extras'])}</small></p>
</div>

<h2>🧬 صلة القرابة</h2>
<div class="card" style="border-right-color:#dc2626;">
<p><b>احتمال أن يكون من الأقارب (دم):</b> {kin['relative_prob']:.0%} | <b>الأرجح إجمالاً:</b> {e(kin['top']['label'])} ({kin['top']['prob']:.0%})</p>
<p><b>جهة القرابة:</b> {e(kin['side'])}</p>
<table><tr><th>الدرجة</th><th>احتمال الدرجة</th><th>الأرجح داخلها</th><th>بدائل</th></tr>{rows_deg}</table>
<table><tr><th>الاحتمال</th><th>الصلة</th><th>الدرجة</th></tr>{rows_kin}</table>
</div>

<h2>🌍 مكان إقامة الفاعل</h2>
<div class="card" style="border-right-color:#0891b2;">
<p><b>الأرجح:</b> {e(loc['status'])} - اتجاه سكنه بالنسبة للمستفيد: {e(loc['direction'])}</p>
<p>{e(loc['details'])}</p>
<table><tr><th>الاحتمال</th><th>النسبة</th></tr>{rows_loc}</table>
</div>

<h2>🔥 سبب الأذية وهدفها</h2>
<div class="card" style="border-right-color:#dc2626;">
<p><b>الدافع الرئيسي ({mot['primary_share']:.0%}):</b> {e(mot['primary_motive'])}</p>
<p>{e(mot['motive_details'])}</p>
<p><b>الهدف المباشر:</b> {e(mot['goal'])}</p>
<p><b>الدافع الثانوي ({mot['secondary_share']:.0%}):</b> {e(mot['secondary_motive'])}</p>
<p><b>المجالات الأكثر استهدافاً في حياة المستفيد:</b></p><ul>{targets}</ul>
<p>{e(timing)}</p>
</div>

<h2>🔤 حروف الاسم الأول المرجحة</h2>
<div class="card" style="border-right-color:#7c3aed;">
<table><tr><th>الحرف</th><th>الترجيح</th><th>المصدر</th></tr>{letters_rows}</table>
<p><small>حروف الطبع ({e(let['element_desc'])}): {e(' ، '.join(let['letters_list']))}</small></p>
</div>

<h2>🔬 التشخيص ووسيلة الأذى</h2>
<div class="card" style="border-right-color:#7c3aed;">
<p><b>التشخيص:</b> {e(ctx['envy']['diagnosis_type'])}</p>
<p><b>التوجيه:</b> {e(ctx['envy']['recommendation'])}</p>
<p><b>الوسيلة:</b> {e(ctx['medium']['medium_used'])} | <b>الطريقة:</b> {e(ctx['medium']['delivery_method'])}</p>
<ul>{star_html}</ul>
</div>

<h2>🌿 العلاج الروحاني المقترح</h2>
<div class="card" style="border-right-color:#16a34a;">
<p><b>السورة والآية:</b> {e(tr['surah_name'])} - {e(tr['verse_num'])}</p>
<p><em>"{e(tr['verse_text'])}"</em></p>
<p><b>التكرار والطريقة:</b> {e(tr['repetition'])} | {e(tr['method'])}</p>
</div>

<button class="btn-print" onclick="window.print()">🖨️ طباعة التقرير / حفظ PDF</button>
</div></body></html>"""


# ==================== واجهة المستخدم عبر Streamlit ====================
st.set_page_config(page_title="برنامج الهالة الطاقية", layout="wide")
st.markdown(
    "<style>html, body, [class*='st-'] { direction: rtl; text-align: right; }</style>",
    unsafe_allow_html=True,
)

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

    ben_gender = st.radio("جنس المستفيد:", options=["ذكر", "أنثى"], horizontal=True, key="ben_gender")

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
    with col_h:
        birth_hour = st.number_input("الساعة (0-23):", min_value=0, max_value=23, value=12)
    with col_m:
        birth_minute = st.number_input("الدقيقة (0-59):", min_value=0, max_value=59, value=0)

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

        ben_age = max(0.0, (date.today() - birth_date).days / 365.25)

        chart_reader = AutoChartReader(jd, lat, lng)
        magic = chart_reader.analyze_magic_perpetrator(ben_gender, ben_age)
        envy_vs_magic = chart_reader.distinguish_envy_vs_magic()
        damage_medium = chart_reader.detect_damage_medium_and_method(envy_vs_magic['diagnosis_type'])
        treatment = suggest_spiritual_treatment(val_first, val_mother)

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

        asc_sign = ZODIAC_SIGNS[chart_reader.ascendant_sign_idx]

        st.success("تم إتمام التحليل الفلكي والتراثي والفراسة الشاملة بنجاح!")
        st.warning(DISCLAIMER)
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

        st.info(f"✨ **الطالع الفلكي:** {asc_sign} | **حاكم البيت 12:** {magic['h12_ruler']} (في البيت {magic['h12_ruler_house']}، {magic['ruler_dignity']}) | **المجموع الكلي:** `{total_sum}` | **النتيجة النهائية:** `{final_result_num}`")

        # ---------- ملف الفاعل ----------
        st.markdown("---")
        st.subheader("🕵️‍♂️ ملف الفاعل: الجنس والعمر والشكل والمهنة")
        phys = magic['physiognomy']
        age = magic['age']

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            st.success(f"👤 **الجنس:** {magic['perpetrator_gender']}")
            st.success(f"🎂 **العمر المقدر:** {age['range'][0]}–{age['range'][1]} سنة (بعد مطابقته مع الصلة الأرجح: {age['blended_range'][0]}–{age['blended_range'][1]} سنة)")
            st.info(f"📏 **الطول:** {phys['height']}")
            st.info(f"⚖️ **الوزن والبنية:** {phys['weight']}")
            st.info(f"🎨 **لون البشرة:** {phys['skin']}")
            st.info(f"🙂 **شكل الوجه:** {phys['face']}")
        with col_f2:
            st.info(f"👁️ **حجم العيون:** {phys['eyes_size']}")
            st.info(f"🧿 **لون العيون:** {phys['eyes_color']}")
            st.info(f"👄 **الشفاه:** {phys['lips']}")
            st.info(f"💇 **الشعر:** {phys['hair']}")
            st.warning(f"💼 **المهنة المحتملة:** {phys['job']}")
            st.warning(f"💪 **قوة الفاعل:** {magic['power']}")
        st.caption(phys['extras'])

        # ---------- القرابة ----------
        st.markdown("---")
        st.subheader("🧬 صلة القرابة (من هو بالضبط؟)")
        kin = magic['kin']
        st.error(f"🎯 **الأرجح إجمالاً:** {kin['top']['label']} ({kin['top']['prob']:.0%}) — {DEGREE_NAMES[kin['top']['degree']]}")
        st.warning(f"👪 **احتمال كونه من الأقارب بالدم:** {kin['relative_prob']:.0%} | **جهة القرابة:** {kin['side']}")

        deg_rows = []
        for d in (1, 2, 3, 4, 0):
            b = kin['best_per_degree'].get(d)
            if b:
                deg_rows.append({
                    "الدرجة": DEGREE_NAMES[d],
                    "احتمال الدرجة": f"{kin['deg_prob'][d]:.0%}",
                    "الأرجح داخلها": f"{b['label']} ({b['share']:.0%})",
                    "بدائل": "، ".join(f"{a} ({s:.0%})" for a, s in b['alts']),
                })
        st.markdown("**الأرجح في كل درجة قرابة:**")
        st.table(pd.DataFrame(deg_rows))

        rank_df = pd.DataFrame([
            {"الاحتمال": f"{c['prob']:.0%}", "الصلة": c['label'], "الدرجة": DEGREE_NAMES[c['degree']]}
            for c in kin['ranking']
        ])
        rank_df.index = rank_df.index + 1
        st.markdown("**ترتيب أقوى 8 مرشحين:**")
        st.table(rank_df)

        # ---------- الإقامة ----------
        st.markdown("---")
        st.subheader("🌍 مكان إقامة الفاعل")
        loc = magic['location']
        st.info(f"📌 **الأرجح:** {loc['status']} | 🧭 **اتجاه سكنه بالنسبة للمستفيد:** {loc['direction']}\n\n*{loc['details']}*")
        for k, v in loc['probs'].items():
            st.progress(float(v), text=f"{loc['names'][k]}: {v:.0%}")

        # ---------- الدافع ----------
        st.markdown("---")
        st.subheader("🔥 سبب الإيذاء وهدفه الرئيسي")
        mot = magic['motive']
        st.error(f"🔥 **الدافع الرئيسي ({mot['primary_share']:.0%}):** {mot['primary_motive']}\n\n*{mot['motive_details']}*")
        st.warning(f"🎯 **الهدف المباشر:** {mot['goal']}")
        st.info(f"↪️ **الدافع الثانوي ({mot['secondary_share']:.0%}):** {mot['secondary_motive']}")
        st.markdown("**أكثر مجالات حياة المستفيد استهدافاً:**")
        for t, txt in mot['targets']:
            st.write(f"- البيت {t}: {txt}")

        st.warning(magic['damage_timing'])
        for star in magic['star_clues']:
            st.error(star)

        # ---------- الحروف ----------
        st.markdown("---")
        st.subheader("🔤 الحروف المرجحة في اسم الفاعل الأول")
        let = magic['letters']
        letters_df = pd.DataFrame([
            {"الحرف": x['letter'], "الترجيح": f"{x['share']:.0%}", "المصدر": x['why']} for x in let['top_letters']
        ])
        st.table(letters_df)
        st.caption(f"حروف الطبع ({let['element_desc']}): {' ، '.join(let['letters_list'])}")

        # ---------- التشخيص ----------
        st.markdown("---")
        st.subheader("🔬 التشخيص الفلكي ووسيلة الأذى:")
        st.error(f"🎯 **التشخيص المعتمد:** {envy_vs_magic['diagnosis_type']}")
        st.warning(f"💡 **التوجيه العلاجي:** {envy_vs_magic['recommendation']}")
        st.info(f"🧬 **الوسيلة:** {damage_medium['medium_used']} | 🧪 **الطريقة:** {damage_medium['delivery_method']}")
        st.caption("طبيعة العمل: " + " ، ".join(magic['nature_clues']))

        # ---------- العلاج ----------
        st.markdown("---")
        st.subheader("🌿 مقترح العلاج الروحاني:")
        st.success(f"📖 **السورة المقترحة:** {treatment['surah_name']} ({treatment['verse_num']})")
        st.info(f"💬 *\"{treatment['verse_text']}\"*")
        st.warning(f"🔄 **التكرار:** {treatment['repetition']}")
        st.error(f"🛠️ **الطريقة:** {treatment['method']}")

        # ---------- الأدلة ----------
        with st.expander("🧾 الأدلة الفلكية التفصيلية وراء كل استنتاج"):
            for section, lines in magic['evidence'].items():
                st.markdown(f"**{section}**")
                for line in lines:
                    st.write(f"- {line}")

        # ---------- التصدير ----------
        html_report_content = build_html_report({
            "magic": magic, "envy": envy_vs_magic, "medium": damage_medium, "treatment": treatment,
            "first_name": full_first_name, "mother_name": full_mother_name,
            "country": selected_country_name, "city": selected_city_name,
            "asc_sign": asc_sign, "zodiac_name": zodiac_name, "naw": current_naw_name,
            "total": total_sum, "final": final_result_num,
        })

        st.markdown("---")
        st.download_button(
            label="📥 تحميل التقرير الشامل كملف HTML جاهز للطباعة",
            data=html_report_content,
            file_name=f"Spiritual_Physiognomy_Report_{full_first_name}.html",
            mime="text/html"
        )
