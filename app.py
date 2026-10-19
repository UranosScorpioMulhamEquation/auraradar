from datetime import datetime
import streamlit as st

# إعدادات صفحة ستريمليت
st.set_page_config(
    page_title="برنامج الكشف الروحي",
    page_icon="🔮",
    layout="centered"
)

# 1. جدول الحروف الأبجدية وما يقابلها من قيم (الجمل الكبير)
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

# 2. خريطة الأبراج الباطنية (من 1 إلى 12)
ZODIAC_MAP = {
    1: 'حمل',
    2: 'ثور',
    3: 'جوزاء',
    4: 'سرطان',
    5: 'أسد',
    6: 'عذراء',
    7: 'ميزان',
    8: 'عقرب',
    9: 'قوس',
    10: 'جدي',
    11: 'دلو',
    12: 'حوت'
}

# 3. أيام الأسبوع وما يقابلها من كواكب
DAYS_PLANETS = {
    'احد': {'planet': 'شمس', 'day_name': 'احد'},
    'اثنين': {'planet': 'قمر', 'day_name': 'اثنين'},
    'ثلاثاء': {'planet': 'مريخ', 'day_name': 'ثلاثاء'},
    'اربعاء': {'planet': 'عطارد', 'day_name': 'اربعاء'},
    'خميس': {'planet': 'مشتري', 'day_name': 'خميس'},
    'جمعه': {'planet': 'زهره', 'day_name': 'جمعه'},
    'سبت': {'planet': 'زحل', 'day_name': 'سبت'}
}


def calculate_text_value(text):
    """حساب القيمة العددية لأي نص بناءً على جدول الجمل الكبير مع استبعاد الهمزة المتطرفة"""
    total = 0
    text = text.strip()
    for char in text:
        if char in ['ء']:
            continue
        if char in ABJAD_DICT:
            total += ABJAD_DICT[char]
    return total


def reduce_to_12(number):
    """طرح الرقم 12 بشكل متكرر حتى يبقى الناتج بين 1 و 12"""
    while number > 12:
        number -= 12
    if number <= 0:
        number = ((number - 1) % 12) + 1
    return number


def get_current_naw(check_date=None):
    """تحديد النوء الفلكي الحالي بناءً على التاريخ"""
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


# --- تصميم الواجهة باستخدام Streamlit ---
st.title("🔮 نظام كشف الطاقات الروحانية")
st.markdown("أدخل البيانات المطلوبة أدناه بدقة لإجراء الحسابات واستخراج التفسير:")

with st.form("spiritual_analysis_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        first_name = st.text_input("الاسم الأول (باللغة العربية حصراً):", value="رشا")
        mother_name = st.text_input("اسم الأم (باللغة العربية حصراً):", value="مها")
        
    with col2:
        birth_date_str = st.text_input("تاريخ الميلاد (مثال: 1.1.2000):", value="1.1.2000")
        day_key = st.selectbox(
            "اليوم الحالي:",
            options=["احد", "اثنين", "ثلاثاء", "اربعاء", "خميس", "جمعه", "سبت"],
            index=3  # الافتراضي اربعاء
        )
        
    is_night_radio = st.radio(
        "الوقت الحالي:",
        options=["نهار (بعد شروق الشمس إلى قبل غروبها)", "ليل (بعد غروب الشمس إلى قبل شروقها)"],
        index=1  # الافتراضي ليل
    )
    
    submitted = st.form_submit_button("✨ تنفيذ الكشف الروحي")

if submitted:
    if not first_name or not mother_name:
        st.error("الرجاء إدخال الاسم الأول واسم الأم بشكل صحيح.")
    else:
        is_night = True if "ليل" in is_night_radio else False
        
        # 1. حساب الاسم الأول
        val_first = calculate_text_value(first_name)
        
        # 2. حساب اسم الأم
        val_mother = calculate_text_value(mother_name)
        
        # 3. تبسيط تاريخ الميلاد
        digits_sum = sum(int(char) for char in birth_date_str if char.isdigit())
        
        # 4. استخراج البرج الباطني
        zodiac_calc = val_first + val_mother
        zodiac_index = reduce_to_12(zodiac_calc)
        zodiac_name = ZODIAC_MAP.get(zodiac_index, 'حمل')
        val_zodiac_name = calculate_text_value(zodiac_name)
        
        # 5. اليوم والكوكب والوقت
        day_info = DAYS_PLANETS.get(day_key.lower(), DAYS_PLANETS['اربعاء'])
        val_day = calculate_text_value(day_info['day_name'])
        planet_name = day_info['planet']
        val_planet = calculate_text_value(planet_name)
        time_val = 340 if is_night else 400
        time_label = "ليل (قمر)" if is_night else "نهار (شمس)"
        
        # 6. النجم الفلكي المسيطر (النوء)
        current_naw_name = get_current_naw()
        val_naw = calculate_text_value(current_naw_name)
        
        # 7. المجموع الكلي الثماني
        total_sum = (val_first + val_mother + digits_sum + val_zodiac_name + 
                     val_day + val_planet + time_val + val_naw)
        
        # 8. التخفيض النهائي
        final_result_num = reduce_to_12(total_sum)
        
        # --- عرض النتائج ---
        st.success("تم إجراء التحليل والحسابات بنجاح!")
        
        st.markdown("---")
        st.subheader("📊 تفاصيل القيم المحسوبة:")
        
        col_res1, col_res2 = st.columns(2)
        with col_res1:
            st.write(f"• **مجموع الاسم الأول ({first_name}):** {val_first}")
            st.write(f"• **مجموع اسم الأم ({mother_name}):** {val_mother}")
            st.write(f"• **مجموع تاريخ الميلاد:** {digits_sum}")
            st.write(f"• **البرج الباطني:** {zodiac_name} (رقم {zodiac_index} - القيمة: {val_zodiac_name})")
            
        with col_res2:
            st.write(f"• **اليوم الحاكم:** {day_info['day_name']} (القيمة: {val_day})")
            st.write(f"• **الكوكب المرتبط:** {planet_name} (القيمة: {val_planet})")
            st.write(f"• **الوقت الحالي:** {time_label} (القيمة: {time_val})")
            st.write(f"• **النجم الفلكي (النوء):** {current_naw_name} (القيمة: {val_naw})")
            
        st.markdown("---")
        
        st.metric(label="✨ المجموع الكلي الثماني", value=total_sum)
        st.metric(label="✨ الرقم النهائي بعد التخفيض (بين 1 و 12)", value=final_result_num)
        
        st.markdown("### 📜 التفسير الروحي النهائي:")
        if final_result_num == 12:
            st.error("النتيجة (12): **هالتك في هذا الوقت معرضة لمرض نفسي.**")
        elif final_result_num == 9:
            st.warning("النتيجة (9): **هالتك في هذا الوقت مرض عضوي.**")
        elif final_result_num in [2, 4]:
            st.warning(f"النتيجة ({final_result_num}): **هالتك في هذا الوقت معرضه لمرض طاقي سلبي سببه كائن مرئي.**")
        elif final_result_num in [1, 3, 5, 6, 7, 8, 10, 11]:
            st.info(f"النتيجة ({final_result_num}): **هالتك في هذا الوقت معرضة لمرض روحاني طاقي سلبي سببه كائن غير مرئي.**")