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

# ==================== إعداد الصفحة وتوجيه الواجهة ====================
st.set_page_config(
    page_title="نظام الكشفية الطاقية وكشف الفاعل والعلاج الروحاني",
    page_icon="🔮",
    layout="wide",
)

# ==================== إعدادات Swiss Ephemeris ====================
swe.set_ephe_path('')  # وضع Moshier المدمج (يعمل سحابياً دون ملفات خارجية)


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
    try:
        local_tz = pytz.timezone(tz_str)
    except Exception:
        local_tz = pytz.utc
    dt = datetime.combine(date_obj, time_obj)
    try:
        local_dt = local_tz.localize(dt, is_dst=None)
    except Exception:
        local_dt = local_tz.localize(dt, is_dst=False)
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

# الحكام التراثيون (الدلو=زحل، الحوت=المشتري) كما في التنجيم العربي القديم
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

ELEMENT_DIRECTION = {
    "ناري": "الشرق",
    "ترابي": "الجنوب",
    "هوائي": "الغرب",
    "مائي": "الشمال"
}

SIGN_EXACT_DIRECTION = {
    "الحمل": "الشرق تماماً",
    "الأسد": "الشرق المائل للشمال (الشمال الشرقي)",
    "القوس": "الشرق المائل للجنوب (الجنوب الشرقي)",
    "الثور": "الجنوب المائل للشرق (الجنوب الشرقي)",
    "العذراء": "الجنوب تماماً",
    "الجدي": "الجنوب المائل للغرب (الجنوب الغربي)",
    "الجوزاء": "الغرب المائل للجنوب (الجنوب الغربي)",
    "الميزان": "الغرب تماماً",
    "الدلو": "الغرب المائل للشمال (الشمال الغربي)",
    "السرطان": "الشمال المائل للشرق (الشمال الشرقي)",
    "العقرب": "الشمال تماماً",
    "الحوت": "الشمال المائل للغرب (الشمال الغربي)",
}

SIGN_ENVIRONMENT = {
    "الحمل": "منطقة مرتفعة أو قرب طرق سريعة ومحطات وقود أو ورش",
    "الثور": "منطقة هادئة ذات حدائق أو مزارع أو بيوت أرضية واسعة",
    "الجوزاء": "حي سكني حيوي قريب من المدارس أو الأسواق والمراكز التجارية",
    "السرطان": "منطقة قريبة من مسطحات مائية أو آبار أو مبانٍ قديمة متلاصقة",
    "الأسد": "حي راقٍ أو شارع رئيسي بارز قرب مبانٍ حكومية أو قصور",
    "العذراء": "منطقة منظمة قريبة من مكاتب أو مستشفيات أو مستودعات ومخازن",
    "الميزان": "منطقة حديثة منظمة أو مجمعات سكنية متقابلة ذات واجهات جميلة",
    "العقرب": "مكان منعزل نسبياً أو قرب مبانٍ مهجورة أو مجاري مياه أو مقابر",
    "القوس": "أطراف المدينة أو منطقة مفتوحة قرب مساجد كبرى أو طرق سفر",
    "الجدي": "أحياء قديمة متينة البناء أو مناطق حجرية/جبلية واطئة الحركة",
    "الدلو": "أبراج سكنية عالية أو منطقة حديثة البناء ذات طابع تقني مفتوح",
    "الحوت": "منطقة رطبة أو قرب ساحل أو مستنقعات أو زقاق هادئ قليل الإضاءة",
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

NODES = ["راهو", "كيتو"]
MALEFICS = ["المريخ", "زحل", "بلوتو", "كيتو", "راهو"]

MEAN_SPEED = {
    "الشمس": 0.9856, "القمر": 13.176, "عطارد": 1.383, "الزهرة": 1.2,
    "المريخ": 0.524, "المشتري": 0.083, "زحل": 0.034
}

MAJOR_FIXED_STARS = {
    "الغول (Algol)": {"lon": 56.2, "nature": "عقد مظلمة ونحس شديد متجذر"},
    "الدبران (Aldebaran)": {"lon": 69.8, "nature": "صراعات حادة وتسليط ناري"},
    "الشعرى اليمانية (Sirius)": {"lon": 104.1, "nature": "قوة طاقية نافذة وتأثير روحاني قوي"},
    "قلب الأسد (Regulus)": {"lon": 150.1, "nature": "سلطة وهيمنة وتسليط من صاحب نفوذ"},
    "السماك الأعزل (Spica)": {"lon": 203.8, "nature": "حفظ إلهي وقابلية سريعة للاستشفاء والتحصين"},
    "قلب العقرب (Antares)": {"lon": 249.8, "nature": "أذى خفي ووساوس وسموم أثيرية متجددة"},
    "النسر الواقع (Vega)": {"lon": 285.3, "nature": "أعمال خفية وطلاسم معلّقة في الهواء"},
    "فم الحوت (Fomalhaut)": {"lon": 333.9, "nature": "أعمال مائية مرشوشة أو ملقاة في ماء جارٍ"}
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

ABJAD_ORDER = [
    "ا", "ب", "ج", "د", "ه", "و", "ز", "ح", "ط", "ي", "ك", "ل", "م", "ن",
    "س", "ع", "ف", "ص", "ق", "ر", "ش", "ت", "ث", "خ", "ذ", "ض", "ظ", "غ"
]
MANSIONS = [
    "الشرطين", "البطين", "الثريا", "الدبران", "الهقعة", "الهنعة", "الذراع", "النثرة",
    "الطرف", "الجبهة", "الزبرة", "الصرفة", "العواء", "السماك", "الغفر", "الزبانى",
    "الإكليل", "القلب", "الشولة", "النعائم", "البلدة", "سعد الذابح", "سعد بلع",
    "سعد السعود", "سعد الأخبية", "الفرغ المقدم", "الفرغ المؤخر", "الرشاء"
]

ELEMENT_LETTERS = {
    "ناري": ["ا", "ه", "ط", "م", "ف", "ش", "ذ"],
    "ترابي": ["ب", "و", "ي", "ن", "ص", "ت", "ض"],
    "هوائي": ["ج", "ز", "ك", "س", "ق", "ث", "ظ"],
    "مائي": ["د", "ح", "ل", "ع", "ر", "خ", "غ"],
}

# ---- جداول الفراسة الفلكية التراثية الموسعة ----
PLANET_PHYSIOGNOMY = {
    "الشمس": {
        "skin": "بشرة حنطية مائلة للذهبي أو مشربة بحمرة واضحة",
        "eyes_size": "عيون متوسطة إلى واسعة ذات نظرة نافذة وجريئة",
        "eyes_color": "عسلي فاتح أو بني ذهبي",
        "lips": "شفاه متوسطة ومحددة بوضوح",
        "hair": "شعر خفيف نسبياً في المقدمة أو بداية صلع، بلون بني ذهبي",
        "face": "وجه عريض مهيب وجبهة عريضة بارزة",
        "voice": "صوت جهوري واثق يميل إلى فرض الرأي في المجالس",
        "mark": "ارتفاع واضح في الجبهة أو أثر علامة خفيفة في الوجه أو الكتف الأيمن",
        "behavior": "يُظهر الوقار والنصح والاهتمام، لكنه يراقب مكانة المستفيد ورزقه عن كثب",
        "job": "وظيفة إدارية، منصب إشرافي، عمل حكومي، أو تجارة الذهب والمجوهرات"
    },
    "القمر": {
        "skin": "بشرة بيضاء شاحبة أو فاتحة جداً ناعمة",
        "eyes_size": "عيون واسعة ومستديرة، كثيرة الرمش أو مدمعة",
        "eyes_color": "بني فاتح، رمادي، أو عسلي مائي",
        "lips": "شفاه ممتلئة وناعمة",
        "hair": "شعر ناعم بلون بني فاتح أو مائل للشقرة",
        "face": "وجه مستدير ممتلئ الخدين",
        "voice": "صوت هادئ لين متقلب النبرة، يميل للشكوى والتودد المصطنع",
        "mark": "شامة واضحة في الخد أو الرقبة أو استدارة لافتة في الوجه",
        "behavior": "قريب من الجلسات المنزلية، يكثر من الأسئلة عن تفاصيل البيت والأسرة",
        "job": "عمل في قطاع الأغذية، التمريض، العقارات، السوائل، أو ربة منزل متفرغة"
    },
    "عطارد": {
        "skin": "بشرة حنطية فاتحة أو مائلة للصفرة",
        "eyes_size": "عيون صغيرة إلى متوسطة، سريعة الحركة والالتفات",
        "eyes_color": "بني داكن أو أسود حاد",
        "lips": "شفاه رفيعة ومستقيمة",
        "hair": "شعر خفيف ناعم داكن",
        "face": "وجه نحيل مستطيل وملامح حادة ذكية",
        "voice": "صوت سريع الإيقاع كثير الكلام والتبرير ونقل الأخبار",
        "mark": "خطوط تعبيرية دقيقة في الجبهة أو نحافة ملحوظة في الأصابع واليدين",
        "behavior": "يتظاهر باللطف والذكاء والوساطة، ويتحاشى المواجهة المباشرة",
        "job": "محاسبة، تجارة، تعليم، كتابة، وساطة، اتصالات، أو أعمال مكتبية"
    },
    "الزهرة": {
        "skin": "بشرة صافية ناعمة، بيضاء مشربة بحمرة أو قمحية صافية",
        "eyes_size": "عيون واسعة جميلة ذات رموش كثيفة ونظرة ناعمة",
        "eyes_color": "بني غامق جذاب، عسلي، أو ملون (أخضر/أزرق)",
        "lips": "شفاه ممتلئة ومحددة بشكل بارز",
        "hair": "شعر ناعم كثيف مموج ومعتنى به",
        "face": "وجه جميل مستدير ناعم مع غمازات واضحة",
        "voice": "صوت ناعم عذب يجيد الإقناع والمجاملة لإخفاء النوايا",
        "mark": "غمازة في الخد أو الذقن أو اهتمام لافت بالزينة والعطور",
        "behavior": "يُظهر المحبة الزائدة ويقدّم الهدايا أو الطعام والضيافة بكثرة",
        "job": "تجميل، أزياء، فنون، عطور، ضيافة، أو عمل يعتمد على العلاقات العامة"
    },
    "المريخ": {
        "skin": "بشرة سمراء محمرة أو بها آثار جروح/ندوب أو نمش",
        "eyes_size": "عيون صغيرة إلى متوسطة، غائرة قليلاً وذات نظرة حادة",
        "eyes_color": "بني محمر أو عسلي داكن",
        "lips": "شفاه رقيقة ومشدودة",
        "hair": "شعر خشن قصير كثيف، مائل للحمرة أو البني الداكن",
        "face": "وجه زاوي محمر، حواجب كثيفة متقاربة",
        "voice": "صوت حاد جاف سريع الانفعال ونبرة قاطعة",
        "mark": "ندبة أو أثر حرق/جرح قديم في الوجه أو الحاجب أو اليد",
        "behavior": "عصبي المزاج، يدخل في خصومات سريعة أو يضمر العداء عند أول خلاف",
        "job": "أعمال حرة شاقة، هندسة، ميكانيكا، جزارة، أمن، أو مهن تتطلب جهداً بدنياً"
    },
    "المشتري": {
        "skin": "بشرة بيضاء مشربة بحمرة أو قمحية صافية",
        "eyes_size": "عيون كبيرة وواسعة ومريحة للناظر",
        "eyes_color": "عسلي، بني فاتح، أو أزرق/رمادي",
        "lips": "شفاه كبيرة وممتلئة",
        "hair": "شعر كثيف لامع بلون بني مع شيب مبكر في الجانبين",
        "face": "وجه عريض بشوش ممتلئ، وذقن مزدوج واضح",
        "voice": "صوت رزين وقور يتحدث باسم الحكمة والنصيحة الدينية أو العائلية",
        "mark": "اتساع الصدر والمنكبين أو شيب وقور في اللحية/الشعر",
        "behavior": "يظهر بمظهر المصلح والمستشار، لكنه يتدخل في قرارات المال والنفوذ",
        "job": "قضاء، محاماة، شؤون دينية، بنوك، تجارة كبرى، أو مناصب أكاديمية"
    },
    "زحل": {
        "skin": "بشرة سمراء داكنة، قمحية غامقة، أو شاحبة جافة",
        "eyes_size": "عيون صغيرة ضيقة وغائرة في المحجر",
        "eyes_color": "أسود داكن أو بني غامق جداً",
        "lips": "شفاه رقيقة جداً ومضمومة",
        "hair": "شعر أسود خشن أو قليل الكثافة مخالط بالشيب",
        "face": "وجه طويل جاف، عظام وجنتين بارزة، وتجاعيد مبكرة",
        "voice": "صوت خافت أو ثقيل بطيء، قليل الكلام وكثير الصمت والمراقبة",
        "mark": "انحناءة خفيفة في الكتفين أو تجاعيد عميقة حول العينين أو ضعف في الركبة/الأسنان",
        "behavior": "كتوم، حقود طويل النفس، يراقب بصمت ولا يُظهر غضبه مباشرة",
        "job": "زراعة، عقارات وأراضي، مقاولات وبناء، أعمال تقليدية قديمة، أو متقاعد"
    },
    "أورانوس": {
        "face": "ملامح حادة غير تقليدية ونظرة متوترة",
        "hair": "شعر متطاير أو تسريحة غير مألوفة",
    },
    "نبتون": {
        "face": "ملامح ناعمة غامضة ونظرة شاردة",
        "hair": "شعر ناعم مائل للتموج",
    },
}

PLANET_GENDER = {
    "الشمس": 2, "المريخ": 2, "المشتري": 2, "زحل": 2, "عطارد": 0,
    "القمر": -2, "الزهرة": -2, "أورانوس": 1, "نبتون": -1, "بلوتو": 0, "راهو": 0, "كيتو": 0
}

PLANET_AGE = {
    "القمر": 24, "عطارد": 24, "الزهرة": 30, "المريخ": 37, "الشمس": 42,
    "المشتري": 52, "زحل": 66, "أورانوس": 35, "نبتون": 45, "بلوتو": 45, "راهو": 33, "كيتو": 45
}

PLANET_BUILD = {
    "الشمس": (0.5, 0.5), "القمر": (-1.0, 1.5), "عطارد": (-0.5, -1.5), "الزهرة": (0.0, 0.5),
    "المريخ": (1.0, -0.5), "المشتري": (2.0, 2.0), "زحل": (1.0, -1.5), "أورانوس": (1.5, -1.0),
    "نبتون": (0.0, 1.0), "بلوتو": (0.5, 0.5), "راهو": (0.5, 0.0), "كيتو": (0.0, -0.5)
}
ELEMENT_BUILD = {"ناري": (0.3, -0.3), "ترابي": (0.0, 0.6), "هوائي": (0.5, -0.8), "مائي": (-0.3, 1.0)}

DEGREE_NAMES = {
    1: "قرابة دم من الدرجة الأولى (الوالدان / الإخوة / الأبناء)",
    2: "قرابة دم من الدرجة الثانية (الأجداد / الأعمام / العمات / الأخوال / الخالات)",
    3: "قرابة دم من الدرجة الثالثة (أبناء العمومة والخؤولة)",
    4: "قرابة مصاهرة وعلاقة زوجية (بدون صلة دم)",
    0: "خارج دائرة القرابة العائلية (من المحيط الاجتماعي أو العمل)",
}

# مرشحو القرابة المفصلون (تم فصل جهة الأب وجهة الأم بدقة)
KIN_CANDIDATES = [
    {"key": "mother", "m": "الأم", "f": "الأم", "gender": "F", "degree": 1, "blood": True, "side_type": "direct",
     "detail": "الأم المباشرة — علاقة منزلية يومية لصيقة وتداخل مباشر في شؤون السكن والقرار", "houses": [10, 4], "planets": ["القمر", "الزهرة"], "gen": (27, 7)},
    {"key": "father", "m": "الأب", "f": "الأب", "gender": "M", "degree": 1, "blood": True, "side_type": "direct",
     "detail": "الأب المباشر — سلطة عائلية مباشرة وتحكم في المسكن أو الشؤون المادية", "houses": [4, 10], "planets": ["الشمس", "زحل"], "gen": (31, 7)},
    {"key": "sister", "m": "الأخت الشقيقة أو من أحد الأبوين", "f": "الأخت الشقيقة أو من أحد الأبوين", "gender": "F", "degree": 1, "blood": True, "side_type": "direct",
     "detail": "الأخت — احتكاك متكرر ومقارنة دائمة في الرزق والزواج ومكانة العائلة", "houses": [3, 11], "planets": ["الزهرة", "عطارد"], "gen": (0, 9)},
    {"key": "brother", "m": "الأخ الشقيق أو من أحد الأبوين", "f": "الأخ الشقيق أو من أحد الأبوين", "gender": "M", "degree": 1, "blood": True, "side_type": "direct",
     "detail": "الأخ — تنافس عائلي أو نزاع على حقوق وميراث أو سلطة داخل الأسرة", "houses": [3, 11], "planets": ["المريخ", "عطارد"], "gen": (0, 9)},
    {"key": "daughter", "m": "الابنة", "f": "الابنة", "gender": "F", "degree": 1, "blood": True, "side_type": "direct",
     "detail": "الابنة — توتر حاد في العلاقة الأبوية/الأمومية وتداخل يومي في المنزل", "houses": [5], "planets": ["الزهرة", "القمر"], "gen": (-27, 8), "adult_only": True},
    {"key": "son", "m": "الابن", "f": "الابن", "gender": "M", "degree": 1, "blood": True, "side_type": "direct",
     "detail": "الابن — صراع على القرار أو الموارد أو توتر شديد داخل البيت", "houses": [5], "planets": ["الشمس", "المريخ"], "gen": (-27, 8), "adult_only": True},
    {"key": "grandmother", "m": "الجدة", "f": "الجدة", "gender": "F", "degree": 2, "blood": True, "side_type": "paternal_or_maternal",
     "detail": "الجدة — من كبار العائلة ولها نفوذ قديم وتوجيه مؤثر داخل الأسرة", "houses": [7, 1], "planets": ["زحل", "القمر"], "gen": (55, 9)},
    {"key": "grandfather", "m": "الجد", "f": "الجد", "gender": "M", "degree": 2, "blood": True, "side_type": "paternal_or_maternal",
     "detail": "الجد — من كبار العائلة ومرجعيته مرتبطة بالأملاك والميراث", "houses": [7, 1], "planets": ["زحل", "الشمس"], "gen": (58, 9)},
    {"key": "paternal_aunt", "m": "العمة (أخت الأب)", "f": "العمة (أخت الأب)", "gender": "F", "degree": 2, "blood": True, "side_type": "paternal",
     "detail": "العمة من جهة الأب — تدخل متكرر في شؤون عائلة المستفيد ومقارنات مالية أو عائلية", "houses": [6, 5], "planets": ["الزهرة", "زحل"], "gen": (14, 12)},
    {"key": "paternal_uncle", "m": "العم (أخو الأب)", "f": "العم (أخو الأب)", "gender": "M", "degree": 2, "blood": True, "side_type": "paternal",
     "detail": "العم من جهة الأب — ارتباط مباشر بشؤون الإرث أو العقار أو الزعامة العائلية", "houses": [6, 5], "planets": ["زحل", "المريخ"], "gen": (16, 12)},
    {"key": "maternal_aunt", "m": "الخالة (أخت الأم)", "f": "الخالة (أخت الأم)", "gender": "F", "degree": 2, "blood": True, "side_type": "maternal",
     "detail": "الخالة من جهة الأم — مطّلعة على أسرار البيت وتتردد على الأسرة باستمرار", "houses": [12, 6], "planets": ["القمر", "عطارد"], "gen": (14, 12)},
    {"key": "maternal_uncle", "m": "الخال (أخو الأم)", "f": "الخال (أخو الأم)", "gender": "M", "degree": 2, "blood": True, "side_type": "maternal",
     "detail": "الخال من جهة الأم — علاقة خفية أو مالية متوترة مع أسرة الأم", "houses": [12, 6], "planets": ["عطارد", "المشتري"], "gen": (16, 12)},
    {"key": "paternal_cousin_f", "m": "بنت العم أو بنت العمة (من جهة الأب)", "f": "بنت العم أو بنت العمة (من جهة الأب)", "gender": "F", "degree": 3, "blood": True, "side_type": "paternal",
     "detail": "قريبة من جهة الأب في الجيل نفسه — دافع غيرة أو تنافس عاطفي/عائلي", "houses": [11, 5], "planets": ["الزهرة", "زحل"], "gen": (0, 12)},
    {"key": "paternal_cousin_m", "m": "ابن العم أو ابن العمة (من جهة الأب)", "f": "ابن العم أو ابن العمة (من جهة الأب)", "gender": "M", "degree": 3, "blood": True, "side_type": "paternal",
     "detail": "قريب من جهة الأب في الجيل نفسه — رغبة في الزواج/التحكم أو منافسة على الميراث والمكانة", "houses": [11, 5], "planets": ["المريخ", "زحل"], "gen": (0, 12)},
    {"key": "maternal_cousin_f", "m": "بنت الخال أو بنت الخالة (من جهة الأم)", "f": "بنت الخال أو بنت الخالة (من جهة الأم)", "gender": "F", "degree": 3, "blood": True, "side_type": "maternal",
     "detail": "قريبة من جهة الأم في الجيل نفسه — تدخل متكرر واطلاع مباشر على خصوصيات المستفيد", "houses": [11, 12], "planets": ["القمر", "الزهرة", "عطارد"], "gen": (0, 12)},
    {"key": "maternal_cousin_m", "m": "ابن الخال أو ابن الخالة (من جهة الأم)", "f": "ابن الخال أو ابن الخالة (من جهة الأم)", "gender": "M", "degree": 3, "blood": True, "side_type": "maternal",
     "detail": "قريب من جهة الأم في الجيل نفسه — تعلق عاطفي أو حسد من النجاح والظهور", "houses": [11, 12], "planets": ["عطارد", "القمر"], "gen": (0, 12)},
    {"key": "stepmother", "m": "زوجة الأب", "f": "زوجة الأب", "gender": "F", "degree": 4, "blood": False, "side_type": "inlaw",
     "detail": "من عائلة الأب بالمصاهرة — توتر حول النفوذ والاهتمام والموارد داخل الأسرة", "houses": [10, 8], "planets": ["الزهرة", "المريخ", "زحل"], "gen": (15, 10)},
    {"key": "mother_in_law", "m": "الحماة (أم الزوج أو أم الزوجة)", "f": "الحماة (أم الزوج أو أم الزوجة)", "gender": "F", "degree": 4, "blood": False, "side_type": "inlaw",
     "detail": "من أهل الشريك بالمصاهرة — تحكم في الحياة الزوجية وتدخل مستمر في شؤون البيت", "houses": [10, 4], "planets": ["القمر", "زحل"], "gen": (27, 7), "adult_only": True},
    {"key": "father_in_law", "m": "الحمو (أبو الزوج أو أبو الزوجة)", "f": "الحمو (أبو الزوج أو أبو الزوجة)", "gender": "M", "degree": 4, "blood": False, "side_type": "inlaw",
     "detail": "من أهل الشريك بالمصاهرة — صراع سلطة أو التزامات مالية مرتبطة بالزواج", "houses": [4, 10], "planets": ["الشمس", "زحل"], "gen": (31, 7), "adult_only": True},
    {"key": "spouse_sibling", "m": "أخو الشريك (السلف)", "f": "أخت الشريك (السلفة)", "gender": "A", "degree": 4, "blood": False, "side_type": "inlaw",
     "detail": "من إخوة الشريك بالمصاهرة — مقارنة دائمة وحسد من الاستقرار العائلي", "houses": [9, 3], "planets": ["عطارد", "الزهرة"], "gen": (0, 10), "adult_only": True},
    {"key": "sibling_spouse", "m": "زوج الأخت (الصهر)", "f": "زوجة الأخ (السلفة)", "gender": "A", "degree": 4, "blood": False, "side_type": "inlaw",
     "detail": "من أزواج الإخوة بالمصاهرة — احتكاك أسري متكرر وتنافس خفي على المكانة", "houses": [9, 7], "planets": ["الزهرة", "المريخ"], "gen": (0, 10), "adult_only": True},
    {"key": "spouse", "m": "الزوج أو الخطيب (حالي أو سابق)", "f": "الزوجة أو الخطيبة (حالية أو سابقة)", "gender": "S", "degree": 4, "blood": False, "side_type": "inlaw",
     "detail": "شريك ارتباط حالي أو سابق — رغبة في الربط والسيطرة أو انتقام بعد انفصال", "houses": [7, 1], "planets": ["الزهرة", "المريخ"], "gen": (0, 10), "adult_only": True},
    {"key": "neighbor", "m": "جار ملاصق أو في نفس الحي", "f": "جارة ملاصقة أو في نفس الحي", "gender": "A", "degree": 0, "blood": False, "side_type": "external",
     "detail": "من الجيران في محيط السكن — يراقب الداخل والخارج ويسهل عليه الوصول لعتبة البيت", "houses": [3, 4], "planets": ["عطارد", "القمر"], "gen": (0, 18)},
    {"key": "friend", "m": "صديق مقرب أو رفيق دراسة", "f": "صديقة مقربة أو رفيقة دراسة", "gender": "A", "degree": 0, "blood": False, "side_type": "external",
     "detail": "من دائرة الصداقة المقربة — مطّلع على أسرار المستفيد وأحواله الشخصية", "houses": [11, 3], "planets": ["المشتري", "الزهرة", "عطارد"], "gen": (0, 15)},
    {"key": "colleague", "m": "زميل أو مسؤول في محيط العمل", "f": "زميلة أو مسؤولة في محيط العمل", "gender": "A", "degree": 0, "blood": False, "side_type": "external",
     "detail": "من محيط العمل والمهنة — غيرة من الترقية والرزق أو تنافس وظيفي مباشر", "houses": [10, 6], "planets": ["الشمس", "زحل", "عطارد"], "gen": (0, 16)},
    {"key": "rival", "m": "منافس أو شريك مالي/عاطفي سابق", "f": "منافسة أو شريكة مالية/عاطفية سابقة", "gender": "A", "degree": 0, "blood": False, "side_type": "external",
     "detail": "خصم أو شريك قديم — خلاف مالي أو عاطفي لم يُغلق ملفه بعد", "houses": [7, 5], "planets": ["الزهرة", "المريخ"], "gen": (0, 14)},
    {"key": "stranger", "m": "شخص من المعارف البعيدة (أو عبر وسيط خارجي)", "f": "شخصية من المعارف البعيدة (أو عبر وسيط خارجي)", "gender": "A", "degree": 0, "blood": False, "side_type": "external",
     "detail": "من خارج الدائرة القريبة — يعمل من مسافة بعيدة عبر المعلومات الشخصية والاسم", "houses": [9, 12, 8], "planets": ["نبتون", "راهو", "أورانوس"], "gen": (0, 20)},
]

HOUSE_TARGET = {
    1: "إضعاف صحة المستفيد وحيويته وحالته النفسية وإشعاره بالخمول الدائم",
    2: "تعطيل الرزق وجلب الديون وضيق المعيشة وتبخر المال",
    3: "قطع الصلة بالإخوة والجيران وتعطيل الدراسة والسفر القريب",
    4: "تخريب استقرار البيت والعلاقة بالوالدين وإثارة النفور داخل المسكن",
    5: "تعطيل الإنجاب أو إيذاء الأبناء أو إفساد العلاقات العاطفية",
    6: "أمراض مزمنة متكررة وإرهاق بدني وتعطيل العمل اليومي",
    7: "تعطيل الزواج أو التفريق بين الزوجين وإفساد الشراكات",
    8: "أزمات وخسائر مفاجئة وخوف مزمن وكوابيس ليلية",
    9: "منع السفر والهجرة وإغلاق أبواب التوفيق العلمي والديني",
    10: "إسقاط المكانة والعمل والسمعة أمام الناس",
    11: "قطع الأصدقاء وتعطيل الأمنيات والدخل الإضافي",
    12: "العزلة والأرق والحبس النفسي والمكائد الخفية",
}

MOTIVES = {
    "love": {
        "title": "التعلق العاطفي: الرغبة في الاستحواذ على المستفيد أو تفريقه عن شريكه (سحر محبة/جلب/تفريق)",
        "detail": "ارتباط حاكم البيت 12 بالزهرة أو ببيوت العاطفة والشراكة (5 و7) يقطع بأن أصل الأذية رغبة في التملك العاطفي: إما جلب المستفيد وإخضاعه، أو تفريقه عن شريكه أو خطيبه.",
        "goal": "إخضاع المستفيد عاطفياً، أو تعطيل زواجه من غيره، أو التفريق بينه وبين شريكه."
    },
    "money": {
        "title": "الطمع المالي: مال أو إرث أو شراكة أو منفعة مادية",
        "detail": "ارتباط الدليل ببيوت المال والمواريث (2 و8) أو بالمشتري بزوايا صعبة يقطع بوجود سبب مادي صرف: نزاع على ميراث أو دين أو شراكة أو رغبة في إفقار المستفيد.",
        "goal": "إفقار المستفيد وقطع رزقه وإعاقة تحصيله لحقه المالي لصالح الفاعل."
    },
    "revenge": {
        "title": "الانتقام والحقد الدفين بسبب خلاف قديم أو جرح كبرياء",
        "detail": "الزوايا الصعبة من المريخ أو زحل أو بلوتو مع حاكم البيت 12 تكشف عداءً ثأرياً: الفاعل يرى أنه تعرض لإهانة أو خسارة من المستفيد ويريد رد الصاع بتدمير هدوئه.",
        "goal": "إيلام المستفيد نفسياً وجسدياً وتدمير استقراره كرد فعل على موقف سابق."
    },
    "envy": {
        "title": "الحسد والغيرة الشديدة من النجاح والمكانة والقبول الاجتماعي",
        "detail": "وقوع الدليل في البيتين 10 و11 أو اتصاله بالشمس والمشتري يقطع بأن المحرك هو الغيرة من نجاح المستفيد ومكانته وقبوله عند الناس، مع رغبة في زوال النعمة.",
        "goal": "إسقاط مكانة المستفيد المهنية والاجتماعية وتشويه سمعته وسلب بركته."
    },
    "property": {
        "title": "نزاع على بيت أو أرض أو نفوذ داخل الأسرة",
        "detail": "ارتباط الدليل بالبيت 4 أو 8 مع زحل يقطع بوجود صراع حول العقار أو المسكن أو الإرث العائلي أو السيطرة على القرار داخل الأسرة.",
        "goal": "إبعاد المستفيد عن المسكن أو الإرث أو القرار العائلي وإضعاف موقعه داخل الأسرة."
    },
    "control": {
        "title": "السيطرة والتعلق المرضي (ربط وتحكم وإبقاء المستفيد تحت النفوذ)",
        "detail": "اتصال حاكم البيت 12 ببلوتو أو نبتون أو القمر مع وقوعه في البيوت 1 أو 8 أو 12 يقطع بوجود رغبة في الهيمنة النفسية وعمل ربط وتحكم يبقيه تابعاً ومنعزلاً.",
        "goal": "عزل المستفيد والتحكم بقراراته وإبقاؤه خائفاً أو معتمداً على الفاعل."
    },
}

# ==================== قاعدة بيانات الأعشاب المنزلية المتوافرة ====================
HOUSEHOLD_HERBS_DB = {
    "ناري": {
        "element_label": "الطبع الناري (لتبريد حرارة السحر المحروق والانفعال والالتهابات الطاقية)",
        "drink_herb": "منقوع البابونج مع النعناع الأخضر والكزبرة اليابسة: تُغلى ملعقة بابونج ونصف ملعقة كزبرة في كوب ماء ثم تُترك لتبرد قليلاً ويُقرأ عليها وتُشرب مساءً لتبريد الجسد وتهدئة الخفقان والأرق.",
        "wash_herb": "ورق السدر الأخضر المطحون (7 ورقات أو ملعقة كبيرة) + كوب ماء ورد + ملعقة كبيرة ملح بحري خشن في دلو ماء بارد؛ يُقرأ عليه ويُغتسل به خارج الحمام ويُرش في زوايا الغرفة.",
        "oil_herb": "زيت الزيتون البكر ممزوجاً بنصف ملعقة صغيرة حبة البركة المطحونة ورشة زعفران: يُقرأ عليه ويُدهن به الصدر والجبهة ومفاصل اليدين والقدمين قبل النوم.",
        "incense_herb": "ورق الغار (ورق اللورا) مع قليل من الكزبرة اليابسة وإكليل الجبل (الروزماري) على جمر هادئ لتنقية هواء البيت وطرد الطاقات المحترقة."
    },
    "ترابي": {
        "element_label": "الطبع الترابي (لفك العقد الثقيلة والخمول والسحر المدفون وضيق الرزق)",
        "drink_herb": "القسط الهندي (ربع ملعقة صغيرة) مع العسل الطبيعي في كوب ماء دافئ أو مغلي الزنجبيل الخفيف مع القرفة صباحاً على الريق لتنشيط الدورة الدموية وفك الخمول.",
        "wash_herb": "ورق السدر الأخضر (7 ورقات مدقوقة) + ملعقتان كبيرتان ملح صخري خشن + ملعقة خل تفاح طبيعي في لترين ماء فاتر؛ للاغتسال ومسح عتبة المنزل الرئيسية.",
        "oil_herb": "زيت الزيتون الدافئ الممزوج بحبة البركة (الحبة السوداء) والقليل من القرنفل المطحون لدهن أسفل الظهر والقدمين والركبتين بعد القراءة عليه.",
        "incense_herb": "الحرمل أو لبان الذكر مع ورق الغار وحبة البركة؛ يُبخر به البيت وقت العصر مع فتح النوافذ لإخراج الثقل والتعطيل."
    },
    "هوائي": {
        "element_label": "الطبع الهوائي (لتهدئة الوساوس وتشتت الذهن والأذى المعلّق عن بُعد)",
        "drink_herb": "مغلي إكليل الجبل (الروزماري) مع الميرمية أو الشمر (الشومر) محلى بعسل طبيعي: يُشرب كوب دافئ بعد العصر لتصفية الذهن وقطع الوساوس.",
        "wash_herb": "منقوع الريحان الطازج أو المجفف + ورق السدر + ماء الزهر والملح الخشن؛ يُغتسل به الرأس والجسد مرة كل يومين قبل المغرب.",
        "oil_herb": "زيت الزيتون البكر المخلوط بقطرات من المسك الأبيض أو ماء الورد مع الزعفران؛ يُدهن به أعلى الرأس والرقبة ومنطقة الصدر.",
        "incense_herb": "العود أو لبان الذكر مع الريحان الجاف أو الخزامى (اللافندر) في غرف النوم لقطع التسلط الهوائي والكوابيس."
    },
    "مائي": {
        "element_label": "الطبع المائي (لإبطال السحر المرشوش والمشروب وإزالة الرطوبة والغم)",
        "drink_herb": "مغلي أوراق الريحان مع النعناع وحبة البركة المحلى بالعسل الطبيعي، مع إضافة خيط من الزعفران في ماء مقروء عليه؛ يُشرب كوب صباحاً وكوب مساءً لتنظيف البطن والهالة.",
        "wash_herb": "ملح خشن (3 ملاعق) + ورق سدر أخضر مطحون + مغلي ورق الغار المصفّى؛ يُستخدم للغسل ومسح عتبة الباب ومداخل المنزل بالكامل.",
        "oil_herb": "زيت الزيتون البكر مع حبة البركة والزعفران وقطرة زيت النعناع؛ يُدهن به البطن والمعدة وأسفل القدمين يومياً.",
        "incense_herb": "تبخير البيت بورق الغار وإكليل الجبل والقسط الهندي الجاف أو لبان الذكر بعد مسح الأرضية بالماء والملح."
    }
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
    m, d = check_date.month, check_date.day
    mmdd = m * 100 + d
    if 512 <= mmdd < 620:
        return "ثريا"
    elif 620 <= mmdd < 703:
        return "تويبع"
    elif 703 <= mmdd < 729:
        return "جوزاء"
    elif 729 <= mmdd < 811:
        return "مرزم"
    elif 811 <= mmdd < 824:
        return "كليبين"
    elif 824 <= mmdd < 920:
        return "سهيل"
    elif 920 <= mmdd < 1124:
        return "وسم"
    elif mmdd >= 1124 or mmdd < 115:
        return "مربعانيه"
    elif 115 <= mmdd < 128:
        return "شبط"
    elif 128 <= mmdd < 223:
        return "عقارب"
    elif 223 <= mmdd < 321:
        return "حميمين"
    else:
        return "ذرعان"


# ==================== أدوات مساعدة فلكية ====================
ASPECT_W = {"اقتران": 2.0, "مقابلة": 1.5, "تربيع": 1.5, "تثليث": 1.0, "تسديس": 0.8}
HARD_ASPECTS = ("اقتران", "مقابلة", "تربيع")


def aspect_info(l1: float, l2: float, orb: float = 6.0) -> Optional[Tuple[str, float]]:
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
        return 0, "حالة معتدلة"
    if SIGN_RULERS.get(sign) == body:
        return 2, "في بيته (قوي ومتسلط)"
    if EXALTATION.get(body) == sign:
        return 3, "في شرفه (نافذ القوة)"
    opp = ZODIAC_SIGNS[(ZODIAC_SIGNS.index(sign) + 6) % 12]
    if SIGN_RULERS.get(opp) == body:
        return -2, "في وباله (مضطرب ويعمل في الخفاء)"
    if EXALTATION.get(body) == opp:
        return -3, "في هبوطه (ضعيف المواجهة ومعتمد على المكيدة)"
    return 0, "حالة معتدلة"


# ==================== محرك قراءة الخريطة الفلكية والفراسة القطعي ====================
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

    def _calculate(self):
        flags = swe.FLG_MOSEPH | swe.FLG_SPEED
        _, ascmc = swe.houses(self.jd, self.lat, self.lng, b'W')
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
                "is_retro": True, "speed": -0.05, "speed_ratio": 1.0, "dignity": (0, "حالة معتدلة"),
            })
        self.P = {p["body"]: p for p in self.planets_data}

    def _ev(self, section: str, text: str):
        self.evidence.setdefault(section, []).append(text)

    def _house_sign(self, house: int) -> str:
        return ZODIAC_SIGNS[(self.ascendant_sign_idx + house - 1) % 12]

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
                            f"اقتران كوكب ({p['body']}) بالنجم الثابت [{star_name}] — الدلالة: {star_info['nature']}."
                        )
        return star_clues

    def estimate_damage_timing(self) -> str:
        h12_sign = self._house_sign(12)
        h12_ruler = SIGN_RULERS.get(h12_sign)
        ruler_p = self.P.get(h12_ruler)
        if not ruler_p:
            return "توقيت الأذية: حالة مستقرة قيد المتابعة."

        arc_diff = abs(ruler_p["lon"] - self.ascendant_lon)
        if arc_diff > 180:
            arc_diff = 360 - arc_diff
        calculated_months = int((arc_diff / 30) * 12) + 1
        if calculated_months > 24:
            calculated_months = (calculated_months % 24) + 1

        if h12_sign in CARDINAL_SIGNS:
            status_type = "أذية جديدة وطارئة"
            timing = f"بدأت خلال الأسابيع القليلة الماضية (منذ نحو {int(arc_diff % 30) + 1} يوماً)."
        elif h12_sign in FIXED_SIGNS:
            status_type = "أذية قديمة ومتأصلة ومستمرة"
            timing = f"أذية متجذرة ممتدة منذ {int(arc_diff / 8) + 3} شهراً تقريباً وتستدعي علاجاً متواصلاً."
        else:
            status_type = "أذية متجددة (متوسطة الحداثة ومرتبطة بمواسم)"
            timing = f"بدأت قبل نحو {calculated_months} شهراً وتتجدد على فترات."
        return f"[{status_type}] — {timing} (البعد القوسي عن الطالع: {arc_diff:.2f}°)."

    def _determine_gender(self, ruler: str, ruler_p: Dict, h12_sign: str, p12: List[str]) -> Dict[str, Any]:
        sec = "تحديد الجنس القطعي"
        score = 3.0 * PLANET_GENDER.get(ruler, 0)
        ruler_masc = ruler_p["sign_idx"] % 2 == 0
        score += 1.5 * (1 if ruler_masc else -1)
        h12_masc = ZODIAC_SIGNS.index(h12_sign) % 2 == 0
        score += 0.75 * (1 if h12_masc else -1)
        for b in p12:
            if b != ruler and b not in NODES:
                score += 0.5 * PLANET_GENDER.get(b, 0)
        for p in self.planets_data:
            if p["body"] != ruler and p["body"] not in NODES:
                asp = aspect_info(ruler_p["lon"], p["lon"], 5.0)
                if asp and asp[0] == "اقتران":
                    score += 0.5 * PLANET_GENDER.get(p["body"], 0)
        is_male = score >= 0
        label = "رجل (ذكر)" if is_male else "امرأة (أنثى)"
        self._ev(sec, f"حاكم البيت 12 ({ruler}) في برج {ruler_p['sign']} وطبيعة البيت 12 ({h12_sign}) تقطع بأن الفاعل {label}.")
        return {"is_male": is_male, "label": label, "score": score}

    def _determine_age(self, ruler: str, ruler_p: Dict, p12: List[str]) -> Dict[str, Any]:
        sec = "تحديد العمر"
        base = PLANET_AGE.get(ruler, 35)
        adj = 0
        if ruler_p["is_retro"]:
            adj += 5
            self._ev(sec, "الحاكم في حالة تراجع فلكي مما يدل على نضج عمري إضافي (+5 سنوات).")
        if ruler_p["speed_ratio"] > 1.25:
            adj -= 3
            self._ev(sec, "الحاكم سريع السير مما يميل بالعمر نحو مرحلة أصغر (-3 سنوات).")
        elif ruler_p["speed_ratio"] < 0.5:
            adj += 3
            self._ev(sec, "الحاكم بطيء السير مما يدل على تقدّم في السن (+3 سنوات).")
        items = [(base + adj, 3.0)]
        disp = SIGN_RULERS.get(ruler_p["sign"])
        if disp and disp != ruler:
            items.append((PLANET_AGE.get(disp, 35), 1.0))
        for b in p12:
            if b != ruler:
                items.append((PLANET_AGE.get(b, 35), 1.0))
        wsum = sum(w for _, w in items)
        mean = sum(a * w for a, w in items) / wsum
        var = sum(w * (a - mean) ** 2 for a, w in items) / wsum
        sd = math.sqrt(var + 49.0)
        mean = min(82.0, max(16.0, mean))
        self._ev(sec, f"الدلالة العمرية لحاكم البيت 12 ({ruler}) وموضعه تعطي متوسطاً فلكياً يقارب {round(mean)} سنة.")
        return {"mean": mean, "sd": sd}

    def _determine_build(self, ruler: str, ruler_p: Dict, p12: List[str], is_male: bool) -> Dict[str, Any]:
        sec = "القوام والبنية"
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
        if not is_male:
            h_score -= 0.6

        if h_score < -0.8:
            h_label = "قصير القامة" if is_male else "قصيرة القامة"
        elif h_score < 0.5:
            h_label = "متوسط القامة" if is_male else "متوسطة القامة"
        elif h_score < 1.3:
            h_label = "فوق المتوسط" if is_male else "فوق المتوسطة"
        else:
            h_label = "طويل القامة" if is_male else "طويلة القامة"

        if w_score < -0.8:
            w_label = "نحيف البنية" if is_male else "نحيفة البنية"
        elif w_score < 0.5:
            w_label = "متناسق البنية" if is_male else "متناسقة البنية"
        elif w_score < 1.2:
            w_label = "ممتلئ الجسم" if is_male else "ممتلئة الجسم"
        else:
            w_label = "ضخم / زائد الوزن" if is_male else "ممتلئة جداً / زائدة الوزن"

        height_cm = round((176 if is_male else 163) + 5 * h_score)
        bmi = min(36, max(17, 23.5 + 3 * w_score))
        weight_kg = round(bmi * (height_cm / 100) ** 2)
        self._ev(sec, f"الطبع {elem} لبرج الحاكم مع تكوين الكواكب يحدد القوام ({h_label}، {w_label}).")
        return {
            "h_label": h_label,
            "w_label": w_label,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
        }

    def analyze_perpetrator_physiognomy(
        self, h12_ruler: str, ruler_p: Dict[str, Any], p12: List[str],
        build: Dict[str, Any], is_male: bool, exact_age: int
    ) -> Dict[str, str]:
        base = PLANET_PHYSIOGNOMY.get(h12_ruler, PLANET_PHYSIOGNOMY["عطارد"]).copy()
        base["height"] = f"{build['h_label']} (في حدود {build['height_cm']} سم)"
        base["weight"] = f"{build['w_label']} (في حدود {build['weight_kg']} كجم)"

        sign = ruler_p["sign"]
        if sign in WATER_SIGNS:
            base["eyes_size"] = "عيون واسعة ناعسة أو مدمعة ذات بريق مائي"
            base["lips"] = "شفاه ممتلئة وبارزة"
        elif sign in FIRE_SIGNS:
            base["skin"] = "بشرة حنطية مشربة بحمرة أو برونزية"
            base["eyes_color"] = "عسلي حاد أو بني محمر"
            base["eyes_size"] = "عيون متوسطة ذات نظرة ثاقبة وسريعة"
        elif sign in EARTH_SIGNS:
            base["skin"] = "بشرة قمحية داكنة أو سمراء صافية"
            base["lips"] = "شفاه محددة متوسطة إلى رقيقة"
        elif sign in AIR_SIGNS:
            base["eyes_size"] = "عيون متوسطة سريعة الحركة ونظرة متفحصة"

        for other in self.planets_data:
            if other["body"] != h12_ruler and other["body"] not in NODES:
                r = aspect_info(ruler_p["lon"], other["lon"], 5.0)
                if r and r[0] == "اقتران":
                    if other["body"] == "زحل":
                        base["skin"] = "بشرة داكنة أو شاحبة جافة تميل للسمرة"
                        base["mark"] = "تجاعيد مبكرة أو انحناء خفيف أو أثر سمرة داكنة في الوجه"
                    elif other["body"] == "الزهرة":
                        base["eyes_size"] = "عيون واسعة جميلة ذات جاذبية لافتة"
                        base["lips"] = "شفاه ممتلئة ومحددة بوضوح"
                    elif other["body"] == "المريخ":
                        base["face"] += " مع أثر ندبة أو احمرار واضح"
                        base["mark"] = "أثر جرح قديم أو ندبة في الوجه أو الحاجب أو اليد"

        # الحالة الاجتماعية المرجحة قطعياً من البيت 7 وحاكم 12 والعمر
        h7_mal = any(p["house"] == 7 and p["body"] in MALEFICS for p in self.planets_data)
        if exact_age < 24:
            marital = "أعزب / غير متزوج" if is_male else "عزباء / غير متزوجة"
        elif exact_age >= 56 and (ruler_p["house"] in (8, 12) or h7_mal):
            marital = "أرمل أو منفصل" if is_male else "أرملة أو منفصلة"
        elif h7_mal and ruler_p["house"] in (7, 12):
            marital = "يعيش توتراً زوجياً أو سبق له الانفصال" if is_male else "تعيش توتراً زوجياً أو سبق لها الانفصال"
        else:
            marital = "متزوج وله أسرة" if is_male else "متزوجة ولها أسرة"
        base["marital_status"] = marital

        extras = []
        for b in p12:
            if b != h12_ruler and b in PLANET_PHYSIOGNOMY and "face" in PLANET_PHYSIOGNOMY[b]:
                extras.append(f"أثر {b} في البيت 12: {PLANET_PHYSIOGNOMY[b]['face']}")
        base["extras"] = " | ".join(extras) if extras else "الملامح صافية ومطابقة تماماً لدلالة حاكم البيت 12."
        return base

    def _candidate_score(
        self, c: Dict, ruler: str, ruler_p: Dict, p12: List[str],
        is_male: bool, est_age: float, est_sd: float, ben_age: float,
        pat_score: float, mat_score: float
    ) -> float:
        s = 0.0
        h = ruler_p["house"]
        hs = c["houses"]
        if h == hs[0]:
            s += 4.2
        elif h in hs[1:]:
            s += 2.6
        pl = c["planets"]
        if ruler in pl:
            s += 3.0 if pl[0] == ruler else 2.2
        for b in p12:
            if b in pl:
                s += 1.0
        for b in pl:
            if b != ruler and b in self.P:
                a = aspect_info(ruler_p["lon"], self.P[b]["lon"], 6.0)
                if a:
                    s += ASPECT_W[a[0]] * (1 - a[1] / 12)
        if c["gender"] == "M":
            s += 3.2 if is_male else -3.2
        elif c["gender"] == "F":
            s += -3.2 if is_male else 3.2
        if c["side_type"] == "paternal":
            s += (pat_score - mat_score) * 0.6
        elif c["side_type"] == "maternal":
            s += (mat_score - pat_score) * 0.6
        expected = ben_age + c["gen"][0]
        sd = math.sqrt(c["gen"][1] ** 2 + est_sd ** 2)
        z = (est_age - expected) / sd
        s -= min(3.5, 0.45 * z * z)
        return s

    def analyze_decisive_kinship(
        self, ruler: str, ruler_p: Dict, p12: List[str], is_male: bool,
        est_age: float, est_sd: float, ben_gender: str, ben_age: float
    ) -> Dict[str, Any]:
        sec = "القرابة وصلة الدم"
        pat, mat = 0.0, 0.0
        if ruler_p["house"] in (4, 6):
            pat += 2.0
        if ruler_p["house"] in (10, 12):
            mat += 2.0
        for b, bucket in (("الشمس", "p"), ("زحل", "p"), ("القمر", "m"), ("الزهرة", "m")):
            a = aspect_info(ruler_p["lon"], self.P[b]["lon"], 6.0)
            if a:
                if bucket == "p":
                    pat += ASPECT_W[a[0]]
                else:
                    mat += ASPECT_W[a[0]]
        if pat == mat:
            pat += 0.2 if ruler_p["sign_idx"] % 2 == 0 else -0.2

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
                g = "M" if is_male else "F"
            c["gender_resolved"] = g
            c["label"] = c["m"] if g == "M" else c["f"]
            cands.append(c)

        for c in cands:
            c["score"] = self._candidate_score(
                dict(c, gender=c["gender"] if c["gender"] in ("M", "F") else "A"),
                ruler, ruler_p, p12, is_male, est_age, est_sd, ben_age, pat, mat
            )

        ranking = sorted(cands, key=lambda x: x["score"], reverse=True)
        top = ranking[0]

        is_blood = bool(top["blood"])
        blood_verdict = (
            "نعم، الفاعل يقرب للمستفيد بالدم المباشر"
            if is_blood
            else "لا، الفاعل لا يقرب للمستفيد بالدم"
        )

        if top["side_type"] == "paternal":
            side_desc = "من جهة الأب (أقارب الأب والأعمام)"
        elif top["side_type"] == "maternal":
            side_desc = "من جهة الأم (أقارب الأم والأخوال)"
        elif top["side_type"] == "paternal_or_maternal":
            side_desc = "من جهة الأب (كبار العائلة الأبوية)" if pat >= mat else "من جهة الأم (كبار عائلة الأم)"
        elif top["side_type"] == "inlaw":
            side_desc = "علاقة مصاهرة وزواج (دائرة الأصهار وأهل الشريك دون صلة دم)"
        elif top["side_type"] == "direct":
            side_desc = "داخل البيت الأسري المباشر (عصب العائلة الأول)"
        else:
            side_desc = "من خارج نطاق القرابة العائلية (محيط السكن أو العمل أو المعارف)"

        self._ev(sec, f"وقوع حاكم البيت 12 ({ruler}) في البيت {ruler_p['house']} مع تطابق الجنس والفارق العمري يقطع بصلة: {top['label']}.")
        self._ev(sec, f"تحليل المحور الأبوي/الأمومي: {side_desc}.")

        return {
            "is_blood": is_blood,
            "blood_verdict": blood_verdict,
            "degree_name": DEGREE_NAMES[top["degree"]],
            "exact_label": top["label"],
            "kinship_detail": top["detail"],
            "side_desc": side_desc,
            "top": top,
        }

    def analyze_decisive_location(self, ruler_p: Dict, city_name: str, country_name: str) -> Dict[str, Any]:
        sec = "مكان الإقامة والمدينة"
        h = ruler_p["house"]
        sc = {"same_city": 0.0, "other_city": 0.0, "abroad": 0.0}

        same = {1: 3.2, 3: 2.8, 4: 3.4, 7: 2.6, 10: 2.5, 6: 1.6, 2: 1.5, 11: 1.5, 5: 1.2}
        other = {2: 1.0, 5: 1.0, 8: 1.6, 11: 1.1, 9: 0.9, 12: 0.9, 6: 0.5}
        abroad = {9: 3.4, 12: 2.2, 8: 1.1, 3: -1.0}
        sc["same_city"] += same.get(h, 0)
        sc["other_city"] += other.get(h, 0)
        sc["abroad"] += abroad.get(h, 0)

        sign = ruler_p["sign"]
        if sign in FIXED_SIGNS:
            sc["same_city"] += 1.2
        elif sign in MUTABLE_SIGNS:
            sc["other_city"] += 1.0
            sc["abroad"] += 0.8
        else:
            sc["other_city"] += 0.6

        if ruler_p["speed_ratio"] > 1.25:
            sc["other_city"] += 0.6

        h9_ruler = SIGN_RULERS.get(self._house_sign(9))
        h9_p = self.P.get(h9_ruler)
        if h9_p and h9_ruler != ruler_p["body"]:
            a = aspect_info(ruler_p["lon"], h9_p["lon"], 6.0)
            if a and a[0] in ("اقتران", "مقابلة"):
                sc["abroad"] += 1.5
        for b in ("أورانوس", "راهو"):
            a = aspect_info(ruler_p["lon"], self.P[b]["lon"], 5.0)
            if a and a[0] in ("اقتران", "مقابلة"):
                sc["abroad"] += 1.5
        for hn in (3, 4):
            hr = SIGN_RULERS.get(self._house_sign(hn))
            hp = self.P.get(hr)
            if hp and hr != ruler_p["body"]:
                a = aspect_info(ruler_p["lon"], hp["lon"], 6.0)
                if a:
                    sc["same_city"] += 1.0

        best = max(sc, key=sc.get)
        is_same_city = best == "same_city"
        if best == "same_city":
            verdict = f"نعم، الفاعل مقيم في نفس مدينة المستفيد ({city_name})"
            details = "الدلائل الفلكية تضعه في النطاق الجغرافي القريب من مسكن المستفيد ومحيطه اليومي، مما يسهّل عليه المراقبة والاحتكاك المباشر."
        elif best == "other_city":
            verdict = f"لا، الفاعل مقيم في مدينة أخرى داخل نفس البلد ({country_name})"
            details = "الفاعل داخل حدود الدولة لكنه يسكن في مدينة أو محافظة أخرى، ويتواصل مع أخبار المستفيد عبر معارف أو رحلات متقطعة."
        else:
            verdict = "لا، الفاعل مقيم في دولة أخرى (خارج البلاد)"
            details = "الفاعل يقيم خارج حدود البلد الأصلي (غربة أو إقامة دائمة بالخارج) ويدير الأذى من مسافات بعيدة أو بواسطة طرف ثالث."

        exact_dir = SIGN_EXACT_DIRECTION.get(sign, ELEMENT_DIRECTION[element_of(sign)])
        env = SIGN_ENVIRONMENT.get(sign, "حي سكني متوسط")
        self._ev(sec, f"تمركز حاكم البيت 12 في البيت {h} وبرج {sign} يقطع بموضع الإقامة ({verdict}) وباتجاه {exact_dir}.")
        return {
            "category": best,
            "is_same_city": is_same_city,
            "verdict": verdict,
            "details": details,
            "direction": exact_dir,
            "environment": env,
        }

    def analyze_decisive_motive(self, ruler: str, ruler_p: Dict) -> Dict[str, Any]:
        sec = "الدافع والهدف"
        h = ruler_p["house"]
        M = {k: 0.0 for k in MOTIVES}
        M["envy"] += 1.2

        def asp(b, orb=6.0):
            if b == ruler or b not in self.P:
                return None
            return aspect_info(ruler_p["lon"], self.P[b]["lon"], orb)

        if h in (5, 7):
            M["love"] += 3.0
        a = asp("الزهرة")
        if a:
            M["love"] += 1.3 * ASPECT_W[a[0]]
        if any(p["house"] == 7 and p["body"] in MALEFICS for p in self.planets_data):
            M["love"] += 1.0

        if h in (2, 8):
            M["money"] += 3.5
        if h == 11:
            M["money"] += 1.0
        a = asp("المشتري")
        if a and a[0] in HARD_ASPECTS:
            M["money"] += ASPECT_W[a[0]]

        for b in ("المريخ", "زحل", "بلوتو"):
            a = asp(b)
            if a and a[0] in HARD_ASPECTS:
                M["revenge"] += 1.2 * ASPECT_W[a[0]]
        if ruler_p["is_retro"]:
            M["revenge"] += 1.0
        if h in (6, 8, 12):
            M["revenge"] += 1.0

        if h in (10, 11):
            M["envy"] += 3.0
        for b in ("الشمس", "المشتري"):
            if asp(b):
                M["envy"] += 1.0

        if h == 4:
            M["property"] += 3.0
        if h == 8:
            M["property"] += 1.5
        if asp("زحل") and h in (4, 8, 3):
            M["property"] += 1.0

        if h in (1, 8, 12):
            M["control"] += 2.5
        for b in ("بلوتو", "نبتون", "القمر"):
            a = asp(b)
            if a and a[0] in ("اقتران", "مقابلة"):
                M["control"] += 1.2 * ASPECT_W[a[0]]

        order = sorted(M, key=M.get, reverse=True)
        primary, secondary = order[0], order[1]

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
                    sc += 1.0
                for mal in ("المريخ", "زحل", "بلوتو"):
                    if mal != hr:
                        a = aspect_info(hp["lon"], self.P[mal]["lon"], 5.0)
                        if a and a[0] in HARD_ASPECTS:
                            sc += 1.0
                if hr != ruler:
                    a = aspect_info(hp["lon"], ruler_p["lon"], 6.0)
                    if a:
                        sc += 2.0 if a[0] == "اقتران" else 1.5 if a[0] in HARD_ASPECTS else 0.5
            if ruler_p["house"] == hn and hn != 12:
                sc += 1.0
            target_scores[hn] = sc
        top_targets = sorted(target_scores, key=target_scores.get, reverse=True)[:3]
        top_targets = [t for t in top_targets if target_scores[t] > 0] or [12]

        self._ev(sec, f"الدافع القطعي هو ({MOTIVES[primary]['title']}) بدلالة البيت {h} واتصالات الكوكب الحاكم.")
        return {
            "primary_key": primary,
            "primary_motive": MOTIVES[primary]["title"],
            "motive_details": MOTIVES[primary]["detail"],
            "goal": MOTIVES[primary]["goal"],
            "secondary_motive": MOTIVES[secondary]["title"],
            "targets": [(t, HOUSE_TARGET[t]) for t in top_targets],
        }

    def detect_perpetrator_name_letters(self, ruler: str, ruler_p: Dict, p12: List[str]) -> Dict[str, Any]:
        h12_sign = self._house_sign(12)
        elem = element_of(h12_sign)
        scores: Dict[str, float] = {}
        sources: Dict[str, List[str]] = {}
        width = 360 / 28

        def add(letter: str, w: float, why: str):
            scores[letter] = scores.get(letter, 0.0) + w
            sources.setdefault(letter, []).append(why)

        def by_mansion(lon: float, w: float, why: str):
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
            add(l, 0.7, f"حرف الطبع {elem}")

        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        primary_letter = ranked[0][0]
        supporting_letters = [l for l, _ in ranked[1:5]]
        details_list = [
            {"letter": l, "rank": idx + 1, "why": " + ".join(sources[l][:2])}
            for idx, (l, _) in enumerate(ranked[:5])
        ]
        self._ev("الحروف", f"الحرف الأقوى من المنزلة القمرية لحاكم البيت 12 وطبع {elem} هو حرف ({primary_letter}).")
        return {
            "h12_sign": h12_sign,
            "element": elem,
            "element_desc": f"طبع {elem}",
            "primary_letter": primary_letter,
            "supporting_letters": supporting_letters,
            "letters_list": ELEMENT_LETTERS[elem],
            "top_letters": details_list,
        }

    def analyze_delivery_method(self, ruler: str, ruler_p: Dict, is_same_city: bool, diagnosis_type: str) -> Dict[str, Any]:
        """تحديد قطعي لطريقة الأذى: هل تم عن بُعد أم عن طريق إعطاء شيء مادي للشخص."""
        sec = "طريقة توصيل الأذى"
        h12_sign = self._house_sign(12)
        h12_elem = element_of(h12_sign)
        h = ruler_p["house"]

        physical_score = 0.0
        remote_score = 0.0

        # دلائل التوصيل المادي المباشر (طعام/شراب/هدية/عطر/ملابس/عتبة بيت)
        if h in (1, 2, 4, 6, 7):
            physical_score += 3.0
        if ruler in ("القمر", "الزهرة", "عطارد"):
            physical_score += 1.5
        if any(p["house"] in (2, 4) and p["body"] in MALEFICS for p in self.planets_data):
            physical_score += 1.5

        asc_ruler = SIGN_RULERS.get(self._house_sign(1))
        asc_p = self.P.get(asc_ruler)
        if asc_p and asc_ruler != ruler:
            a = aspect_info(ruler_p["lon"], asc_p["lon"], 6.0)
            if a and a[0] in HARD_ASPECTS:
                physical_score += 1.8

        h2_ruler = SIGN_RULERS.get(self._house_sign(2))
        h2_p = self.P.get(h2_ruler)
        if h2_p and h2_ruler != ruler:
            a = aspect_info(ruler_p["lon"], h2_p["lon"], 6.0)
            if a and a[0] in HARD_ASPECTS:
                physical_score += 1.5

        # دلائل الأذى عن بُعد (طاقي/اسمي/هوائي/ناري/نبتون/أورانوس/بلوتو/البيت 9 أو 11 أو 12)
        if h in (9, 11, 12, 8):
            remote_score += 2.8
        if ruler in ("زحل", "المريخ", "الشمس", "المشتري"):
            remote_score += 1.0
        if h12_elem in ("هوائي", "ناري"):
            remote_score += 1.4
        if not is_same_city:
            remote_score += 2.5
        for b in ("أورانوس", "نبتون", "بلوتو", "راهو", "كيتو"):
            if self.P[b]["house"] == 12 or (aspect_info(ruler_p["lon"], self.P[b]["lon"], 5.0) is not None):
                remote_score += 1.2

        is_physical = physical_score >= remote_score

        if "حسد" in diagnosis_type and not is_physical:
            delivery_verdict = "تم الأذى عن بُعد عبر الإصابة بالعين والنظرة الحاسدة المباشرة دون أي مادة ملموسة"
            medium_used = "تأثير طاقي مباشر بالنظرة والذكر الحاسد على الهالة."
            channel_detail = "لا يوجد جسم مادي؛ الأذى ناجم عن انبعاث نظرة وحسد متكرر في المجالس أو عبر المتابعة عن بُعد."
            where_to_check = "التركيز على التحصين اليومي والغسل بماء السدر والملح لقطع أثر العين المتراكم."
        elif is_physical:
            delivery_verdict = "تم الأذى عن طريق إعطاء أو دسّ شيء مادي للشخص المتضرر"
            if h in (2, 6) or h12_elem == "مائي" and h != 4:
                medium_used = "مادة مأكولة أو مشروبة (طعام، حلويات، قهوة، أو عصير قُدّم للمستفيد)."
                channel_detail = "تم تمرير الأذى عبر مأكول أو مشروب استقر أثره الطاقي في المعدة والبطن (أو عطر/سائل لامس الجسد مباشرة)."
                where_to_check = "تذكّر أي ضيافة أو طعام أو مشروب خاص قُدّم من هذا الشخص، والبدء فوراً بشرب الماء المرقي مع العسل والزعفران والريحان."
            elif h == 4 or h12_elem == "ترابي":
                medium_used = "شيء مادي موضوع أو مدسوس في المسكن (عتبة البيت، غرفة النوم، أو هدية منزلية)."
                channel_detail = "تم الأذى بإدخال قطعة مادية أو رش مادة عند عتبة الباب أو وضع حرز/تراب في أركان البيت."
                where_to_check = "تفتيش عتبة الباب وزوايا غرفة النوم وأسفل الأسرّة وخزائن الملابس، وغسل العتبات بماء السدر والملح الخشن."
            else:
                medium_used = "هدية مادية مباشرة (عطر، قطعة ملابس، حُلي، أو غرض شخصي تم تبادله باليد)."
                channel_detail = "تم نقل الأذى عبر مناولة يدوية لشيء مادي ملموس يحتفظ به المستفيد في مقتنياته."
                where_to_check = "مراجعة الهدايا أو الملابس أو العطور القادمة من هذه الجهة، وغسلها أو التخلص من أي شيء يثير النفور أو الخمول عند لمسه."
        else:
            delivery_verdict = "تم الأذى عن بُعد (دون إعطاء أي شيء مادي للمستفيد)"
            if h12_elem == "ناري":
                medium_used = "تسليط عن بُعد عبر الاسم واسم الأم بإحراق الأثر أو البخور المظلم."
                channel_detail = "أذى ناري رُصد عن بُعد باستخدام الاسم أو صورة شخصية دون احتكاك جسدي مباشر."
                where_to_check = "لا يوجد جسم مادي في طعام أو شراب؛ الفك يتم بآيات الإبطال والاغتسال البارد بماء السدر وماء الورد."
            elif h12_elem == "هوائي":
                medium_used = "تسليط هوائي عن بُعد (طلاسم معلّقة أو نفث في العقد على الاسم)."
                channel_detail = "عمل معلّق في الهواء يرسل وساوس وتشتتاً وأرقاً عن بُعد."
                where_to_check = "التحصين الصوتي بقراءة الآيات الكاملة والتهوية المستمرة وتبخير المنزل باللبان والريحان."
            elif h12_elem == "ترابي":
                medium_used = "عمل مدفون في مكان بعيد باستخدام أثر قديم (صورة أو شعر أو اسم)."
                channel_detail = "أذى ترابي مدفون خارج نطاق بيت المستفيد يعمل على إبطاء الرزق والحركة."
                where_to_check = "العلاج بآيات سورة الأعراف/يونس كاملة والاغتسال بماء السدر والملح الصخري لفك الربط الأرضي."
            else:
                medium_used = "عمل سائل طُرح في ماء جارٍ أو بحر بعيد بالاسم واسم الأم."
                channel_detail = "تسليط مائي عن بُعد دون مناولة مادية مباشرة، يُضعف العزيمة ويولّد الضيق."
                where_to_check = "الاغتسال والدهان بزيت الزيتون المقروء عليه وتبخير البيت بورق الغار وإكليل الجبل."

        self._ev(sec, f"الموازنة بين البيوت المادية (1،2،4،6،7) وبيوت البعد (8،9،11،12) تقطع بـ: {delivery_verdict}.")
        return {
            "is_physical": is_physical,
            "delivery_verdict": delivery_verdict,
            "medium_used": medium_used,
            "channel_detail": channel_detail,
            "where_to_check": where_to_check,
        }

    def distinguish_envy_vs_magic(self) -> Dict[str, Any]:
        h12_planets = [p for p in self.planets_data if p["house"] == 12]
        h6_planets = [p for p in self.planets_data if p["house"] == 6]
        saturn_mars_ketu_12 = any(p["body"] in ["زحل", "المريخ", "كيتو"] for p in h12_planets)

        if saturn_mars_ketu_12 or any("الغول" in s for s in self.check_fixed_stars()):
            diagnosis_type = "سحر أثري معقود ومدبّر في الخفاء"
            recommendation = "يتطلب التزاماً يومياً بقراءة الآيات الكاملة بنية فك العقد وإبطال الأذى مع برنامج الغسل والدهان العشبي لمدة 14 يوماً متواصلة."
        elif len(h6_planets) > 1:
            diagnosis_type = "حسد شديد وإصابة بالعين المتراكمة"
            recommendation = "يتطلب المداومة على الرقية القرآنية الكاملة والاغتسال بماء السدر والملح وتبخير البيت لإزالة أثر العين."
        else:
            diagnosis_type = "عمل طاقي وسحر خفي موجه للتعطيل"
            recommendation = "يتطلب المواظبة على الأذكار والآيات الكاملة المحددة أدناه مع المشروب العشبي والدهن قبل النوم."
        return {"diagnosis_type": diagnosis_type, "recommendation": recommendation}

    def analyze_magic_perpetrator(
        self, ben_gender: str = "ذكر", ben_age: float = 30.0,
        city_name: str = "", country_name: str = ""
    ) -> Dict[str, Any]:
        self.evidence = {}
        h12_sign = self._house_sign(12)
        ruler = SIGN_RULERS[h12_sign]
        ruler_p = self.P[ruler]
        p12 = [p["body"] for p in self.planets_data if p["house"] == 12]

        gender = self._determine_gender(ruler, ruler_p, h12_sign, p12)
        age = self._determine_age(ruler, ruler_p, p12)
        build = self._determine_build(ruler, ruler_p, p12, gender["is_male"])
        kin = self.analyze_decisive_kinship(
            ruler, ruler_p, p12, gender["is_male"], age["mean"], age["sd"], ben_gender, ben_age
        )

        # العمر القطعي المدموج مع الفارق العمري للصلة المحددة
        top = kin["top"]
        exp_age = ben_age + top["gen"][0]
        w1, w2 = 1.0 / (age["sd"] ** 2), 1.0 / (top["gen"][1] ** 2)
        blended = (age["mean"] * w1 + exp_age * w2) / (w1 + w2)
        exact_age = max(16, min(85, round(blended)))
        if exact_age < 26:
            age_stage = "في مقتبل العمر (شباب)"
        elif exact_age < 42:
            age_stage = "في سن النضج والحيوية"
        elif exact_age < 58:
            age_stage = "في منتصف العمر"
        else:
            age_stage = "كبير في السن"

        physio = self.analyze_perpetrator_physiognomy(
            ruler, ruler_p, p12, build, gender["is_male"], exact_age
        )
        location = self.analyze_decisive_location(ruler_p, city_name, country_name)
        motive = self.analyze_decisive_motive(ruler, ruler_p)
        letters = self.detect_perpetrator_name_letters(ruler, ruler_p, p12)
        envy_vs_magic = self.distinguish_envy_vs_magic()
        delivery = self.analyze_delivery_method(
            ruler, ruler_p, location["is_same_city"], envy_vs_magic["diagnosis_type"]
        )

        d_score, d_label = ruler_p["dignity"]
        if d_score >= 2 and ruler_p["house"] in (1, 4, 7, 10):
            power = "صاحب نفوذ وقدرة على التنفيذ والمتابعة بنفسه دون وسطاء"
        elif d_score <= -2 or ruler_p["house"] in (6, 8, 12):
            power = "يعمل في الخفاء ويعتمد على وسطاء أو تنفيذ مستتر"
        else:
            power = "متوسط النفوذ ويلجأ للمكيدة غير المباشرة"

        saturn_aff = any(p["body"] == "زحل" and p["house"] in [6, 8, 12] for p in self.planets_data)
        mars_aff = any(p["body"] == "المريخ" and p["house"] in [6, 8, 12] for p in self.planets_data)
        ketu_aff = any(p["body"] == "كيتو" and p["house"] in [6, 8, 12] for p in self.planets_data)
        nept_aff = any(p["body"] == "نبتون" and p["house"] in [6, 8, 12] for p in self.planets_data)
        nature = []
        if saturn_aff:
            nature.append("أثر زحل (عقد أرضية ثقيلة وتأثير قديم)")
        if mars_aff:
            nature.append("أثر المريخ (طاقة نارية حادة وسرعة اشتعال)")
        if ketu_aff:
            nature.append("أثر الكيتو (سحر أسود وعقد غامضة)")
        if nept_aff:
            nature.append("أثر نبتون (أوهام وتخييلات وأحلام مزعجة)")
        if not nature:
            nature.append("أذى طاقي موجه بعقد وأرصاد خفية")

        return {
            "h12_sign": h12_sign,
            "h12_element": element_of(h12_sign),
            "h12_ruler": ruler,
            "h12_ruler_house": ruler_p["house"],
            "ruler_dignity": d_label,
            "power": power,
            "gender": gender,
            "perpetrator_gender": gender["label"],
            "exact_age": exact_age,
            "age_stage": age_stage,
            "build": build,
            "physiognomy": physio,
            "kin": kin,
            "location": location,
            "motive": motive,
            "letters": letters,
            "envy": envy_vs_magic,
            "delivery": delivery,
            "star_clues": self.check_fixed_stars(),
            "damage_timing": self.estimate_damage_timing(),
            "planets_in_12": p12,
            "nature_clues": nature,
            "evidence": self.evidence,
        }


# ==================== العلاج الروحاني بالآيات الكاملة والأعشاب المنزلية ====================
def suggest_spiritual_treatment(val_first: int, val_mother: int, h12_element: str) -> Dict[str, Any]:
    combined_val = val_first + val_mother
    treatment_index = (combined_val % 7) or 7
    treatments_db = {
        1: {
            "surah_name": "سورة البقرة (آية السحر والخواتيم)",
            "verse_ref": "سورة البقرة: الآية 102 + الآيتان 285 و 286",
            "verse_text": (
                "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ ۝ "
                "وَاتَّبَعُوا مَا تَتْلُو الشَّيَاطِينُ عَلَىٰ مُلْكِ سُلَيْمَانَ ۖ وَمَا كَفَرَ سُلَيْمَانُ وَلَٰكِنَّ الشَّيَاطِينَ كَفَرُوا يُعَلِّمُونَ النَّاسَ السِّحْرَ وَمَا أُنزِلَ عَلَى الْمَلَكَيْنِ بِبَابِلَ هَارُوتَ وَمَارُوتَ ۚ وَمَا يُعَلِّمَانِ مِنْ أَحَدٍ حَتَّىٰ يَقُولَا إِنَّمَا نَحْنُ فِتْنَةٌ فَلَا تَكْفُرْ ۖ فَيَتَعَلَّمُونَ مِنْهُمَا مَا يُفَرِّقُونَ بِهِ بَيْنَ الْمَرْءِ وَزَوْجِهِ ۚ وَمَا هُم بِضَارِّينَ بِهِ مِنْ أَحَدٍ إِلَّا بِإِذْنِ اللَّهِ ۚ وَيَتَعَلَّمُونَ مَا يَضُرُّهُمْ وَلَا يَنفَعُهُمْ ۚ وَلَقَدْ عَلِمُوا لَمَنِ اشْتَرَاهُ مَا لَهُ فِي الْآخِرَةِ مِنْ خَلَاقٍ ۚ وَلَبِئْسَ مَا شَرَوْا بِهِ أَنفُسَهُمْ ۚ لَوْ كَانُوا يَعْلَمُونَ ۝ "
                "آمَنَ الرَّسُولُ بِمَا أُنزِلَ إِلَيْهِ مِن رَّبِّهِ وَالْمُؤْمِنُونَ ۚ كُلٌّ آمَنَ بِاللَّهِ وَمَلَائِكَتِهِ وَكُتُبِهِ وَرُسُلِهِ لَا نُفَرِّقُ بَيْنَ أَحَدٍ مِّن رُّسُلِهِ ۚ وَقَالُوا سَمِعْنَا وَأَطَعْنَا ۖ غُفْرَانَكَ رَبَّنَا وَإِلَيْكَ الْمَصِيرُ ۝ "
                "لَا يُكَلِّفُ اللَّهُ نَفْسًا إِلَّا وُسْعَهَا ۚ لَهَا مَا كَسَبَتْ وَعَلَيْهَا مَا اكْتَسَبَتْ ۗ رَبَّنَا لَا تُؤَاخِذْنَا إِن نَّسِينَا أَوْ أَخْطَأْنَا ۚ رَبَّنَا وَلَا تَحْمِلْ عَلَيْنَا إِصْرًا كَمَا حَمَلْتَهُ عَلَى الَّذِينَ مِن قَبْلِنَا ۚ رَبَّنَا وَلَا تُحَمِّلْنَا مَا لَا طَاقَةَ لَنَا بِهِ ۖ وَاعْفُ عَنَّا وَاغْفِرْ لَنَا وَارْحَمْنَا ۚ أَنتَ مَوْلَانَا فَانصُرْنَا عَلَى الْقَوْمِ الْكَافِرِينَ"
            ),
            "repetition": "قراءة الآية (102) 21 مرة يومياً، وخواتيم البقرة (285-286) 3 مرات كل مساء لمدة 14 يوماً.",
            "method": "القراءة على إناء ماء طاهر مع النفث ثلاثاً، ثم الشرب منه صباحاً والاغتسال بالباقي مع أوراق السدر خارج مجاري الصرف.",
        },
        2: {
            "surah_name": "سورة الأعراف (آيات إبطال السحر)",
            "verse_ref": "سورة الأعراف: الآيات 117 إلى 122 كاملة",
            "verse_text": (
                "وَأَوْحَيْنَا إِلَىٰ مُوسَىٰ أَنْ أَلْقِ عَصَاكَ ۖ فَإِذَا هِيَ تَلْقَفُ مَا يَأْفِكُونَ ۝ "
                "فَوَقَعَ الْحَقُّ وَبَطَلَ مَا كَانُوا يَعْمَلُونَ ۝ "
                "فَغُلِبُوا هُنَالِكَ وَانقَلَبُوا صَاغِرِينَ ۝ "
                "وَأُلْقِيَ السَّحَرَةُ سَاجِدِينَ ۝ "
                "قَالُوا آمَنَّا بِرَبِّ الْعَالَمِينَ ۝ "
                "رَبِّ مُوسَىٰ وَهَارُونَ"
            ),
            "repetition": "تكرار هذه الآيات الست كاملةً 41 مرة بعد صلاة الفجر و7 مرات قبل النوم لمدة 14 يوماً.",
            "method": "القراءة على زيت الزيتون البكر وماء الشرب؛ يُدهن بالزيت موضع الصدر والكتفين وأسفل القدمين ويُشرب من الماء طوال اليوم.",
        },
        3: {
            "surah_name": "سورة يونس (آيات إحقاق الحق وإبطال عمل المفسدين)",
            "verse_ref": "سورة يونس: الآيات 79 إلى 82 كاملة",
            "verse_text": (
                "وَقَالَ فِرْعَوْنُ ائْتُونِي بِكُلِّ سَاحِرٍ عَلِيمٍ ۝ "
                "فَلَمَّا جَاءَ السَّحَرَةُ قَالَ لَهُم مُّوسَىٰ أَلْقُوا مَا أَنتُم مُّلْقُونَ ۝ "
                "فَلَمَّا أَلْقَوْا قَالَ مُوسَىٰ مَا جِئْتُم بِهِ السِّحْرُ ۖ إِنَّ اللَّهَ سَيُبْطِلُهُ ۖ إِنَّ اللَّهَ لَا يُصْلِحُ عَمَلَ الْمُفْسِدِينَ ۝ "
                "وَيُحِقُّ اللَّهُ الْحَقَّ بِكَلِمَاتِهِ وَلَوْ كَرِهَ الْمُجْرِمُونَ"
            ),
            "repetition": "تكرار الآيات كاملةً 70 مرة يومياً مع التركيز واليقين بأن الله سيبطل العمل، لمدة 14 يوماً.",
            "method": "القراءة على ماء نقي ممزوج بماء الورد وقليل من الملح الخشن؛ يُشرب من الماء ويُمسح به الوجه والصدر وتُرش به عتبة المنزل.",
        },
        4: {
            "surah_name": "سورة طه (آيات فك الخوف وهزيمة الكيد)",
            "verse_ref": "سورة طه: الآيات 65 إلى 69 كاملة",
            "verse_text": (
                "قَالُوا يَا مُوسَىٰ إِمَّا أَن تُلْقِيَ وَإِمَّا أَن نَّكُونَ أَوَّلَ مَنْ أَلْقَىٰ ۝ "
                "قَالَ بَلْ أَلْقُوا ۖ فَإِذَا حِبَالُهُمْ وَعِصِيُّهُمْ يُخَيَّلُ إِلَيْهِ مِن سِحْرِهِمْ أَنَّهَا تَسْعَىٰ ۝ "
                "فَأَوْجَسَ فِي نَفْسِهِ خِيفَةً مُّوسَىٰ ۝ "
                "قُلْنَا لَا تَخَفْ إِنَّكَ أَنتَ الْأَعْلَىٰ ۝ "
                "وَأَلْقِ مَا فِي يَمِينِكَ تَلْقَفْ مَا صَنَعُوا ۖ إِنَّمَا صَنَعُوا كَيْدُ سَاحِرٍ ۖ وَلَا يُفْلِحُ السَّاحِرُ حَيْثُ أَتَىٰ"
            ),
            "repetition": "قراءة الآيات من 65 إلى 69 ثلاث وثلاثين (33) مرة بعد صلاتي الفجر والمغرب يومياً.",
            "method": "وضع اليد اليمنى على الصدر وقراءة الآيات كاملة مع النفث في الكفين والمسح على الرأس والجسد من الأعلى للأسفل.",
        },
        5: {
            "surah_name": "المعوذات الثلاث (الإخلاص والفلق والناس)",
            "verse_ref": "سور الإخلاص (112) والفلق (113) والناس (114) كاملة",
            "verse_text": (
                "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ ۝ قُلْ هُوَ اللَّهُ أَحَدٌ ۝ اللَّهُ الصَّمَدُ ۝ لَمْ يَلِدْ وَلَمْ يُولَدْ ۝ وَلَمْ يَكُن لَّهُ كُفُوًا أَحَدٌ ۝ "
                "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ ۝ قُلْ أَعُوذُ بِرَبِّ الْفَلَقِ ۝ مِن شَرِّ مَا خَلَقَ ۝ وَمِن شَرِّ غَاسِقٍ إِذَا وَقَبَ ۝ وَمِن شَرِّ النَّفَّاثَاتِ فِي الْعُقَدِ ۝ وَمِن شَرِّ حَاسِدٍ إِذَا حَسَدَ ۝ "
                "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ ۝ قُلْ أَعُوذُ بِرَبِّ النَّاسِ ۝ مَلِكِ النَّاسِ ۝ إِلَٰهِ النَّاسِ ۝ مِن شَرِّ الْوَسْوَاسِ الْخَنَّاسِ ۝ الَّذِي يُوَسْوِسُ فِي صُدُورِ النَّاسِ ۝ مِنَ الْجِنَّةِ وَالنَّاسِ"
            ),
            "repetition": "قراءة كل سورة 11 مرة بعد كل صلاة مفروضة و33 مرة قبل النوم.",
            "method": "الجمع بين الكفين والنفث فيهما بعد القراءة ثم المسح على سائر الجسد ثلاث مرات، مع شرب منقوع الأعشاب المهدئة.",
        },
        6: {
            "surah_name": "أوائل الصافات وخواتيم الحشر (التحصين الشامل)",
            "verse_ref": "سورة الصافات: الآيات 1 إلى 10 + سورة الحشر: الآيات 21 إلى 24 كاملة",
            "verse_text": (
                "وَالصَّافَّاتِ صَفًّا ۝ فَالزَّاجِرَاتِ زَجْرًا ۝ فَالتَّالِيَاتِ ذِكْرًا ۝ إِنَّ إِلَٰهَكُمْ لَوَاحِدٌ ۝ رَّبُّ السَّمَاوَاتِ وَالْأَرْضِ وَمَا بَيْنَهُمَا وَرَبُّ الْمَشَارِقِ ۝ إِنَّا زَيَّنَّا السَّمَاءَ الدُّنْيَا بِزِينَةٍ الْكَوَاكِبِ ۝ وَحِفْظًا مِّن كُلِّ شَيْطَانٍ مَّارِدٍ ۝ لَّا يَسَّمَّعُونَ إِلَى الْمَلَإِ الْأَعْلَىٰ وَيُقْذَفُونَ مِن كُلِّ جَانِبٍ ۝ دُحُورًا ۖ وَلَهُمْ عَذَابٌ وَاصِبٌ ۝ إِلَّا مَنْ خَطِفَ الْخَطْفَةَ فَأَتْبَعَهُ شِهَابٌ ثَاقِبٌ ۝ "
                "لَوْ أَنزَلْنَا هَٰذَا الْقُرْآنَ عَلَىٰ جَبَلٍ لَّرَأَيْتَهُ خَاشِعًا مُّتَصَدِّعًا مِّنْ خَشْيَةِ اللَّهِ ۚ وَتِلْكَ الْأَمْثَالُ نَضْرِبُهَا لِلنَّاسِ لَعَلَّهُمْ يَتَفَكَّرُونَ ۝ هُوَ اللَّهُ الَّذِي لَا إِلَٰهَ إِلَّا هُوَ ۖ عَالِمُ الْغَيْبِ وَالشَّهَادَةِ ۖ هُوَ الرَّحْمَٰنُ الرَّحِيمُ ۝ هُوَ اللَّهُ الَّذِي لَا إِلَٰهَ إِلَّا هُوَ الْمَلِكُ الْقُدُّوسُ السَّلَامُ الْمُؤْمِنُ الْمُهَيْمِنُ الْعَزِيزُ الْجَبَّارُ الْمُتَكَبِّرُ ۚ سُبْحَانَ اللَّهِ عَمَّا يُشْرِكُونَ ۝ هُوَ اللَّهُ الْخَالِقُ الْبَارِئُ الْمُصَوِّرُ ۖ لَهُ الْأَسْمَاءُ الْحُسْنَىٰ ۚ يُسَبِّحُ لَهُ مَا فِي السَّمَاوَاتِ وَالْأَرْضِ ۖ وَهُوَ الْعَزِيزُ الْحَكِيمُ"
            ),
            "repetition": "قراءة أوائل الصافات 7 مرات وخواتيم الحشر 7 مرات صباحاً ومساءً.",
            "method": "القراءة بصوت مسموع في أرجاء المنزل بعد تبخيره بالأعشاب الطيبة، مع الاغتسال بماء السدر والملح الصخري.",
        },
        7: {
            "surah_name": "سورة الفاتحة وآية الكرسي (الشفاء والحفظ الأعظم)",
            "verse_ref": "سورة الفاتحة كاملة (1-7) + آية الكرسي كاملة (البقرة: 255)",
            "verse_text": (
                "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ ۝ الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ ۝ الرَّحْمَٰنِ الرَّحِيمِ ۝ مَالِكِ يَوْمِ الدِّينِ ۝ إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ ۝ اهْدِنَا الصِّرَاطَ الْمُسْتَقِيمَ ۝ صِرَاطَ الَّذِينَ أَنْعَمْتَ عَلَيْهِمْ غَيْرِ الْمَغْضُوبِ عَلَيْهِمْ وَلَا الضَّالِّينَ ۝ "
                "اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ ۚ لَا تَأْخُذُهُ سِنَةٌ وَلَا نَوْمٌ ۚ لَّهُ مَا فِي السَّمَاوَاتِ وَمَا فِي الأَرْضِ ۗ مَن ذَا الَّذِي يَشْفَعُ عِندَهُ إِلَّا بِإِذْنِهِ ۚ يَعْلَمُ مَا بَيْنَ أَيْدِيهِمْ وَمَا خَلْفَهُمْ ۖ وَلَا يُحِيطُونَ بِشَيْءٍ مِّنْ عِلْمِهِ إِلَّا بِمَا شَاءَ ۚ وَسِعَ كُرْسِيُّهُ السَّمَاوَاتِ وَالْأَرْضَ ۖ وَلَا يَئُودُهُ حِفْظُهُمَا ۚ وَهُوَ الْعَلِيُّ الْعَظِيمُ"
            ),
            "repetition": "قراءة سورة الفاتحة 7 مرات وآية الكرسي 21 مرة يومياً بعد صلاة الفجر وقبل النوم.",
            "method": "القراءة على ماء طاهر وإناء عسل طبيعي؛ يُؤخذ من العسل ملعقة على الريق ويُغتسل بالماء الممزوج بأوراق السدر.",
        },
    }
    res = treatments_db.get(treatment_index, treatments_db[1]).copy()
    res["herbs"] = HOUSEHOLD_HERBS_DB.get(h12_element, HOUSEHOLD_HERBS_DB["مائي"])
    res["schedule"] = [
        "الصباح (بعد الفجر): شرب كوب من المشروب العشبي الموصى به مع قراءة الورد القرآني الكامل على الماء والعسل.",
        "العصر (قبل الغروب): تبخير المنزل بالأعشاب الطبيعية وفتح النوافذ، ومسح عتبة المنزل بماء السدر والملح عند الحاجة.",
        "المساء (قبل النوم): الاغتسال بماء السدر والملح كل يومين، ثم دهن الصدر والرقبة والقدمين بزيت الزيتون المقروء عليه وقراءة المعوذات وآية الكرسي.",
    ]
    return res


# ==================== تقرير HTML القابل للطباعة ====================
HTML_CSS = """
@page { size: A4; margin: 14mm; }
body { font-family: 'Segoe UI', Tahoma, Arial, sans-serif; background: #f8fafc; color: #0f172a; padding: 24px; line-height: 1.75; }
.container { max-width: 960px; margin: auto; background: #ffffff; padding: 34px; border-radius: 12px; border: 1px solid #cbd5e1; }
h1 { text-align: center; color: #0f172a; font-size: 24px; margin-bottom: 6px; }
.subtitle { text-align: center; color: #475569; font-size: 13px; margin-bottom: 18px; }
.meta { text-align: center; color: #334155; font-size: 14px; margin-bottom: 20px; border-bottom: 2px solid #e2e8f0; padding-bottom: 14px; background: #f8fafc; padding: 10px; border-radius: 8px; }
h2 { color: #1e3a8a; border-bottom: 2px solid #cbd5e1; padding-bottom: 6px; margin-top: 24px; font-size: 18px; page-break-after: avoid; }
.card { background: #f8fafc; border-right: 5px solid #1e40af; padding: 14px 18px; border-radius: 8px; margin-bottom: 14px; page-break-inside: avoid; }
.verdict-box { background: #fef2f2; border: 1px solid #fecaca; border-right: 5px solid #dc2626; padding: 14px 18px; border-radius: 8px; margin-bottom: 14px; page-break-inside: avoid; }
.heal-box { background: #f0fdf4; border: 1px solid #bbf7d0; border-right: 5px solid #16a34a; padding: 14px 18px; border-radius: 8px; margin-bottom: 14px; page-break-inside: avoid; }
.quran-text { background: #ffffff; border: 1px solid #86efac; padding: 16px; border-radius: 8px; font-size: 17px; line-height: 2.1; color: #064e3b; margin: 10px 0; text-align: justify; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
table { width: 100%; border-collapse: collapse; margin-top: 8px; }
th, td { border: 1px solid #cbd5e1; padding: 7px 10px; text-align: right; font-size: 14px; }
th { background: #e2e8f0; color: #0f172a; }
.btn-print { display: block; width: 250px; margin: 28px auto 10px; padding: 12px 18px; background: #16a34a; color: white; text-align: center; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 15px; }
@media print {
  body { background: #ffffff; padding: 0; }
  .container { border: none; padding: 0; max-width: 100%; }
  .btn-print { display: none; }
}
"""


def build_html_report(ctx: Dict[str, Any]) -> str:
    e = html.escape
    m = ctx["magic"]
    phys = m["physiognomy"]
    kin = m["kin"]
    loc = m["location"]
    mot = m["motive"]
    let = m["letters"]
    deliv = m["delivery"]
    tr = ctx["treatment"]
    herbs = tr["herbs"]

    targets = "".join(f"<li><b>البيت {t}:</b> {e(txt)}</li>" for t, txt in mot["targets"])
    letters_rows = "".join(
        f"<tr><td>{x['rank']}</td><td style='font-size:18px'><b>{e(x['letter'])}</b></td><td>{e(x['why'])}</td></tr>"
        for x in let["top_letters"]
    )
    star_html = "".join(f"<li>{e(s)}</li>" for s in m["star_clues"]) or "<li>لا توجد اقترانات مباشرة بنجوم نحسة كبرى.</li>"
    schedule_html = "".join(f"<li>{e(step)}</li>" for step in tr["schedule"])

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <title>التقرير الفلكي والروحاني القطعي - {e(ctx['first_name'])}</title>
  <style>{HTML_CSS}</style>
</head>
<body>
<div class="container">
  <h1>🔮 التقرير القطعي للكشفية الطاقية ومعرفة الفاعل والعلاج الروحاني</h1>
  <div class="subtitle">إصدار نظام الكشفية الطاقية من علوم الحرف والفراسة والتنجيم العربي القديم — تطوير الفلكي استرو رادار</div>
  <div class="meta">
    <b>المستفيد:</b> {e(ctx['first_name'])} | <b>اسم الأم:</b> {e(ctx['mother_name'])} |
    <b>الجنس:</b> {e(ctx['ben_gender'])} | <b>مكان الميلاد:</b> {e(ctx['country'])} - {e(ctx['city'])} |
    <b>تاريخ الميلاد:</b> {e(ctx['birth_date_str'])}
  </div>

  <h2>1. الخلاصة الفلكية والحرفية المرجعية</h2>
  <div class="card">
    <div class="grid">
      <div><b>الطالع الفلكي:</b> {e(ctx['asc_sign'])}</div>
      <div><b>حاكم البيت 12 (دليل الفاعل):</b> {e(m['h12_ruler'])} في البيت {m['h12_ruler_house']} ({e(m['ruler_dignity'])})</div>
      <div><b>البرج الباطني الحرفي:</b> {e(ctx['zodiac_name'])}</div>
      <div><b>النوء الفلكي المعتمد:</b> {e(ctx['naw'])}</div>
      <div><b>المجموع الكلي:</b> {ctx['total']}</div>
      <div><b>المفتاح العددي النهائي:</b> {ctx['final']}</div>
    </div>
  </div>

  <h2>2. الهوية القطعية للفاعل وصلة القرابة ومكان الإقامة</h2>
  <div class="verdict-box">
    <p><b>👤 الجنس القطعي:</b> {e(m['perpetrator_gender'])}</p>
    <p><b>🎂 العمر الدقيق:</b> {m['exact_age']} سنة ({e(m['age_stage'])})</p>
    <p><b>🧬 القرابة بالدم:</b> {e(kin['blood_verdict'])}</p>
    <p><b>🤝 صلة القرابة بالتفصيل:</b> {e(kin['exact_label'])} — ({e(kin['degree_name'])})</p>
    <p><b>🧭 جهة القرابة وتفصيل العلاقة:</b> {e(kin['side_desc'])} — {e(kin['kinship_detail'])}</p>
    <p><b>🏙️ الإقامة والمدينة:</b> {e(loc['verdict'])}</p>
    <p><b>📍 الاتجاه الجغرافي وبيئة السكن:</b> {e(loc['direction'])} بالنسبة لمسكن المستفيد ({e(loc['environment'])})</p>
    <p><b>📝 الوصف المكاني:</b> {e(loc['details'])}</p>
  </div>

  <h2>3. مواصفات الفراسة الجسدية والنفسية الموسعة للفاعل</h2>
  <div class="card" style="border-right-color:#d97706;">
    <div class="grid">
      <div><b>📏 الطول:</b> {e(phys['height'])}</div>
      <div><b>⚖️ الوزن والبنية:</b> {e(phys['weight'])}</div>
      <div><b>🎨 لون البشرة:</b> {e(phys['skin'])}</div>
      <div><b>🙂 شكل الوجه:</b> {e(phys['face'])}</div>
      <div><b>👁️ العيون:</b> {e(phys['eyes_size'])} — {e(phys['eyes_color'])}</div>
      <div><b>👄 الفم والشفاه:</b> {e(phys['lips'])}</div>
      <div><b>💇 الشعر:</b> {e(phys['hair'])}</div>
      <div><b>💍 الحالة الاجتماعية:</b> {e(phys['marital_status'])}</div>
      <div><b>🗣️ الصوت والأسلوب:</b> {e(phys['voice'])}</div>
      <div><b>🔎 العلامة الفارقة:</b> {e(phys['mark'])}</div>
      <div><b>💼 المهنة ومصدر الدخل:</b> {e(phys['job'])}</div>
      <div><b>💪 مستوى النفوذ:</b> {e(m['power'])}</div>
    </div>
    <p style="margin-top:10px;"><b>🎭 سلوكه أمام المستفيد:</b> {e(phys['behavior'])}</p>
    <p><small>{e(phys['extras'])}</small></p>
  </div>

  <h2>4. حروف اسم الفاعل (المستخرجة من المنزلة القمرية والطبع)</h2>
  <div class="card" style="border-right-color:#7c3aed;">
    <p><b>الحرف الأقوى في الاسم الأول للفاعل:</b> <span style="font-size:20px;color:#5b21b6;"><b>{e(let['primary_letter'])}</b></span> | <b>الحروف المساندة:</b> {e(' ، '.join(let['supporting_letters']))}</p>
    <table>
      <tr><th>الترتيب</th><th>الحرف</th><th>الدليل الفلكي</th></tr>
      {letters_rows}
    </table>
    <p><small>مجموعة حروف {e(let['element_desc'])}: {e(' ، '.join(let['letters_list']))}</small></p>
  </div>

  <h2>5. طريقة الأذى (عن بُعد أم بشيء مادي) والدافع والهدف</h2>
  <div class="card" style="border-right-color:#dc2626;">
    <p><b>🔬 التشخيص المعتمد:</b> {e(m['envy']['diagnosis_type'])}</p>
    <p><b>🧪 طريقة تنفيذ الأذى (قطعي):</b> {e(deliv['delivery_verdict'])}</p>
    <p><b>📦 الوسيلة والأسلوب:</b> {e(deliv['medium_used'])}</p>
    <p><b>📌 التفصيل العملي للوسيلة:</b> {e(deliv['channel_detail'])}</p>
    <p><b>🔍 موضع التحقق والفحص:</b> {e(deliv['where_to_check'])}</p>
    <p><b>🔥 الدافع الرئيسي للفاعل:</b> {e(mot['primary_motive'])}</p>
    <p>{e(mot['motive_details'])}</p>
    <p><b>🎯 الهدف المباشر:</b> {e(mot['goal'])}</p>
    <p><b>⏱️ توقيت الأذى:</b> {e(m['damage_timing'])}</p>
    <p><b>أكثر مجالات حياة المستفيد استهدافاً:</b></p>
    <ul>{targets}</ul>
    <p><b>الدلالات النجمية والطاقية:</b></p>
    <ul>{star_html}</ul>
  </div>

  <h2>6. العلاج الروحاني الكامل (الآيات كاملةً + الأعشاب المنزلية المتوافرة)</h2>
  <div class="heal-box">
    <p><b>📖 السورة والآيات المخصصة:</b> {e(tr['surah_name'])} — ({e(tr['verse_ref'])})</p>
    <div class="quran-text">{e(tr['verse_text'])}</div>
    <p><b>🔄 التكرار اليومي:</b> {e(tr['repetition'])}</p>
    <p><b>🛠️ طريقة الرقية والاستعمال:</b> {e(tr['method'])}</p>
    <hr style="border:none;border-top:1px solid #bbf7d0;margin:14px 0;">
    <p><b>🌿 الأعشاب المنزلية المتوافرة المساعدة في العلاج ({e(herbs['element_label'])}):</b></p>
    <ul>
      <li><b>🥤 المشروب العشبي المنزلي:</b> {e(herbs['drink_herb'])}</li>
      <li><b>🚿 الغسل والرش بالأعشاب:</b> {e(herbs['wash_herb'])}</li>
      <li><b>🫒 الدهن العشبي الموضعي:</b> {e(herbs['oil_herb'])}</li>
      <li><b>💨 التبخير والتعطير الطبيعي:</b> {e(herbs['incense_herb'])}</li>
    </ul>
    <p><b>🗓️ البرنامج اليومي العملي (لمدة 14 يوماً):</b></p>
    <ul>{schedule_html}</ul>
  </div>

  <button class="btn-print" onclick="window.print()">🖨️ طباعة التقرير / حفظ PDF</button>
</div>
</body>
</html>"""


# ==================== واجهة المستخدم عبر Streamlit ====================
def main():
    st.markdown(
        "<style>html, body, [class*='st-'] { direction: rtl; text-align: right; }</style>",
        unsafe_allow_html=True,
    )

    st.title("🔮 نظام الكشفية الطاقية ومعرفة الفاعل والعلاج الروحاني")
    st.markdown("من علوم الحرف والفراسة والتنجيم العربي القديم — تطوير الفلكي استرو رادار")
    st.markdown("---")

    country_map, sorted_country_names = get_sorted_countries()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📍 البيانات الشخصية والمكانية للمستفيد")
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
        st.subheader("📅 اسم الأم وتوقيت الميلاد والكشف")
        mother_name_type = st.selectbox("نوع اسم الأم:", ["مفرد", "مركب"], key="m_type")
        if mother_name_type == "مفرد":
            mother_name_part1 = st.text_input("اسم الأم:", value="", key="mn1")
            mother_name_part2 = ""
        else:
            mother_name_part1 = st.text_input("الشطر الأول من اسم الأم:", value="", key="mn1_comp")
            mother_name_part2 = st.text_input("الشطر الثاني من اسم الأم:", value="", key="mn2_comp")

        birth_date = st.date_input(
            "تاريخ الميلاد:", min_value=date(1940, 1, 1), max_value=date(2030, 1, 1), value=date(1990, 1, 1)
        )

        col_h, col_m = st.columns(2)
        with col_h:
            birth_hour = st.number_input("ساعة الميلاد (0-23):", min_value=0, max_value=23, value=12)
        with col_m:
            birth_minute = st.number_input("دقيقة الميلاد (0-59):", min_value=0, max_value=59, value=0)

        day_key = st.selectbox(
            "اليوم الحالي للحساب:", options=["احد", "اثنين", "ثلاثاء", "اربعاء", "خميس", "جمعه", "سبت"], index=3
        )

    is_night_radio = st.radio("وقت الكشف الحالي:", options=["نهار", "ليل"], horizontal=True, index=1)

    submitted = st.button("✨ إطلاق الكشفية الطاقية والتقرير القطعي الشامل", type="primary")

    if submitted:
        full_first_name = (
            first_name_part1.strip()
            if first_name_type == "مفرد"
            else f"{first_name_part1} {first_name_part2}".strip()
        )
        full_mother_name = (
            mother_name_part1.strip()
            if mother_name_type == "مفرد"
            else f"{mother_name_part1} {mother_name_part2}".strip()
        )

        val_first = calculate_name_value(first_name_part1, first_name_type == "مركب") + (
            calculate_name_value(first_name_part2, False) if first_name_type == "مركب" else 0
        )
        val_mother = calculate_name_value(mother_name_part1, mother_name_type == "مركب") + (
            calculate_name_value(mother_name_part2, False) if mother_name_type == "مركب" else 0
        )

        if not full_first_name or not full_mother_name:
            st.error("الرجاء إدخال الاسم الأول واسم الأم بشكل صحيح لإتمام الحساب الحرفي والفلكي.")
            st.stop()

        city_data = next((city for city in country_cities_data if city.name == selected_city_name), None)
        if not city_data:
            st.error("يرجى اختيار مدينة صحيحة.")
            st.stop()

        lat, lng = city_data.latitude, city_data.longitude
        tz_str = TimezoneFinder().timezone_at(lng=lng, lat=lat) or "UTC"
        jd = get_utc_julian_day(birth_date, time(hour=int(birth_hour), minute=int(birth_minute)), tz_str)
        ben_age = max(1.0, (date.today() - birth_date).days / 365.25)

        chart_reader = AutoChartReader(jd, lat, lng)
        magic = chart_reader.analyze_magic_perpetrator(
            ben_gender=ben_gender, ben_age=ben_age, city_name=selected_city_name, country_name=selected_country_name
        )
        treatment = suggest_spiritual_treatment(val_first, val_mother, magic["h12_element"])

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

        st.success("تم إتمام التحليل الفلكي والحرفي وكشف الفاعل والعلاج الروحاني بنجاح!")
        st.markdown("---")
        st.subheader("📊 ملخص العناصر الفلكية والحرفية الثمانية")

        c_r1, c_r2 = st.columns(2)
        with c_r1:
            st.write(f"1. **الاسم الأول:** {full_first_name} (قيمة الجُمّل: {val_first})")
            st.write(f"2. **اسم الأم:** {full_mother_name} (قيمة الجُمّل: {val_mother})")
            st.write(f"3. **مجموع خانات تاريخ الميلاد:** {digits_sum}")
            st.write(f"4. **البرج الباطني:** {zodiac_name} (قيمة: {val_zodiac_name})")
        with c_r2:
            st.write(f"5. **النوء الفلكي:** {current_naw_name} (قيمة: {val_naw})")
            st.write(f"6. **اليوم:** {day_info['day_name']} (قيمة: {val_day})")
            st.write(f"7. **الكوكب:** {planet_name} (قيمة: {val_planet})")
            st.write(f"8. **وقت الكشف:** {time_label} (قيمة: {time_val})")

        st.info(
            f"✨ **الطالع الفلكي:** {asc_sign} | **حاكم البيت 12 (دليل الفاعل):** {magic['h12_ruler']} "
            f"(في البيت {magic['h12_ruler_house']}، {magic['ruler_dignity']}) | **المجموع الكلي:** `{total_sum}` | **المفتاح النهائي:** `{final_result_num}`"
        )

        # ---------- ملف الفاعل القطعي ----------
        st.markdown("---")
        st.subheader("🕵️‍♂️ الهوية القطعية للفاعل وصلة القرابة ومكان الإقامة")
        kin = magic["kin"]
        loc = magic["location"]
        phys = magic["physiognomy"]

        k1, k2 = st.columns(2)
        with k1:
            st.error(f"🧬 **القرابة بالدم:** {kin['blood_verdict']}")
            st.error(f"🤝 **صلة القرابة بالتفصيل:** {kin['exact_label']} ({kin['degree_name']})")
            st.info(f"🧭 **جهة القرابة وتفصيل العلاقة:** {kin['side_desc']} — {kin['kinship_detail']}")
        with k2:
            st.success(f"👤 **الجنس القطعي للفاعل:** {magic['perpetrator_gender']}")
            st.success(f"🎂 **العمر المحدد:** {magic['exact_age']} سنة ({magic['age_stage']})")
            st.warning(f"🏙️ **مكان الإقامة (هل من نفس المدينة؟):** {loc['verdict']}")
            st.info(f"📍 **الاتجاه وبيئة السكن:** {loc['direction']} — {loc['environment']}")

        st.write(f"*{loc['details']}*")

        st.markdown("---")
        st.subheader("👁️ مواصفات الفراسة الجسدية والنفسية الموسعة للفاعل")
        p_col1, p_col2 = st.columns(2)
        with p_col1:
            st.info(f"📏 **الطول:** {phys['height']}")
            st.info(f"⚖️ **الوزن والبنية:** {phys['weight']}")
            st.info(f"🎨 **لون البشرة:** {phys['skin']}")
            st.info(f"🙂 **شكل الوجه:** {phys['face']}")
            st.info(f"👁️ **حجم ولون العيون:** {phys['eyes_size']} — {phys['eyes_color']}")
            st.info(f"👄 **الفم والشفاه:** {phys['lips']}")
        with p_col2:
            st.info(f"💇 **الشعر:** {phys['hair']}")
            st.info(f"💍 **الحالة الاجتماعية:** {phys['marital_status']}")
            st.info(f"🗣️ **الصوت والأسلوب:** {phys['voice']}")
            st.warning(f"🔎 **العلامة الفارقة:** {phys['mark']}")
            st.warning(f"💼 **المهنة ومصدر الدخل:** {phys['job']}")
            st.warning(f"💪 **مستوى النفوذ:** {magic['power']}")
        st.success(f"🎭 **سلوك الفاعل أمام المستفيد:** {phys['behavior']}")
        st.caption(phys["extras"])

        # ---------- الحروف ----------
        st.markdown("---")
        st.subheader("🔤 حروف اسم الفاعل الأول (من المنزلة القمرية والطبع)")
        let = magic["letters"]
        st.success(
            f"الحرف الأقوى في الاسم الأول للفاعل: **{let['primary_letter']}** | "
            f"الحروف المساندة: **{' ، '.join(let['supporting_letters'])}**"
        )
        letters_df = pd.DataFrame([
            {"الترتيب": x["rank"], "الحرف": x["letter"], "المصدر الفلكي": x["why"]}
            for x in let["top_letters"]
        ])
        st.table(letters_df)

        # ---------- طريقة الأذى والدافع ----------
        st.markdown("---")
        st.subheader("🧪 طريقة توصيل الأذى (عن بُعد أم بشيء مادي) والدافع والهدف")
        deliv = magic["delivery"]
        mot = magic["motive"]
        envy = magic["envy"]

        st.error(f"🎯 **التشخيص المعتمد:** {envy['diagnosis_type']}")
        st.error(f"📦 **طريقة توصيل الأذى (حاسمة):** {deliv['delivery_verdict']}")
        st.info(f"🧬 **الوسيلة المستخدمة:** {deliv['medium_used']}\n\n**التفصيل العملي:** {deliv['channel_detail']}")
        st.warning(f"🔍 **موضع التحقق والفحص:** {deliv['where_to_check']}")
        st.error(f"🔥 **الدافع الرئيسي للفاعل:** {mot['primary_motive']}\n\n*{mot['motive_details']}*")
        st.warning(f"🎯 **الهدف المباشر من الأذى:** {mot['goal']}")
        st.info(f"⏱️ **توقيت حدوث الأذى:** {magic['damage_timing']}")
        st.markdown("**أكثر مجالات حياة المستفيد تضرراً:**")
        for t, txt in mot["targets"]:
            st.write(f"- **البيت {t}:** {txt}")
        for star in magic["star_clues"]:
            st.error(f"⭐ {star}")

        # ---------- العلاج الموسع ----------
        st.markdown("---")
        st.subheader("🌿 العلاج الروحاني الكامل (الآيات كاملةً + الأعشاب المنزلية المتوافرة)")
        herbs = treatment["herbs"]
        st.success(f"📖 **السورة والآيات المخصصة:** {treatment['surah_name']} — ({treatment['verse_ref']})")
        st.markdown(
            f"<div style='background:#0f172a;color:#ecfdf5;padding:18px;border-radius:10px;border-right:5px solid #10b981;font-size:19px;line-height:2.1;'>{html.escape(treatment['verse_text'])}</div>",
            unsafe_allow_html=True,
        )
        st.warning(f"🔄 **التكرار اليومي:** {treatment['repetition']}")
        st.info(f"🛠️ **طريقة الاستعمال والرقية:** {treatment['method']}")

        st.markdown(f"### 🌱 الأعشاب المنزلية المتوافرة المساعدة في العلاج ({herbs['element_label']})")
        h_c1, h_c2 = st.columns(2)
        with h_c1:
            st.success(f"🥤 **المشروب العشبي المنزلي:**\n\n{herbs['drink_herb']}")
            st.info(f"🚿 **ماء الغسل والرش بالأعشاب:**\n\n{herbs['wash_herb']}")
        with h_c2:
            st.warning(f"🫒 **الدهن العشبي الموضعي:**\n\n{herbs['oil_herb']}")
            st.info(f"💨 **التبخير والتعطير الطبيعي:**\n\n{herbs['incense_herb']}")

        st.markdown("**🗓️ البرنامج اليومي العملي (14 يوماً):**")
        for step in treatment["schedule"]:
            st.write(f"- {step}")

        with st.expander("🧾 الأدلة الفلكية والحرفية التفصيلية وراء الاستنتاجات"):
            for section, lines in magic["evidence"].items():
                st.markdown(f"**{section}**")
                for line in lines:
                    st.write(f"- {line}")

        html_report_content = build_html_report({
            "magic": magic,
            "treatment": treatment,
            "first_name": full_first_name,
            "mother_name": full_mother_name,
            "ben_gender": ben_gender,
            "birth_date_str": f"{birth_date.year}-{birth_date.month:02d}-{birth_date.day:02d}",
            "country": selected_country_name,
            "city": selected_city_name,
            "asc_sign": asc_sign,
            "zodiac_name": zodiac_name,
            "naw": current_naw_name,
            "total": total_sum,
            "final": final_result_num,
        })

        st.markdown("---")
        st.download_button(
            label="📥 تحميل التقرير القطعي الشامل (HTML جاهز للطباعة / PDF)",
            data=html_report_content,
            file_name=f"Energy_Report_{full_first_name}.html",
            mime="text/html",
        )


if __name__ == "__main__":
    main()

