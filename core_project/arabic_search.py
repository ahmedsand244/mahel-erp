import re
from django.db.models import Q

# Domain Synonyms Dictionary for Equipment & Spare Parts
SYNONYM_GROUPS = [
    ['بخاخة', 'بخاخ', 'رشاش', 'رشاشة', 'طلمبة رش', 'بشبوري', 'فونية', 'نوزل'],
    ['بستم', 'بيستم', 'مكبس', 'شمبر', 'شنابر', 'حلقات مكبس'],
    ['موبينة', 'موبينا', 'مبينة', 'مبينه', 'ملف اشعال', 'ملف الاشعال', 'كويل', 'بوبينة', 'بوبينا'],
    ['كربراتير', 'كاربراتير', 'كربيراتير', 'كاربيراتير', 'مغذي وقود', 'كربوريتر'],
    ['بوجيه', 'بوجي', 'بواجي', 'شمعة احتراق', 'شمعات احتراق', 'شمعة'],
    ['تانك', 'تنك', 'خزان', 'تانكي', 'تنكي', 'خزان وقود'],
    ['دينامو', 'دينمو', 'دنمو', 'مولد', 'جنريتر', 'مولد كهرباء'],
    ['مارش', 'سلف', 'موتور تشغيل', 'ستارتر', 'بادئ حركة'],
    ['اويل سيل', 'اويلسيل', 'اولسيل', 'مانع تسريب', 'مانع زيت', 'صوفة', 'صوفه'],
    ['جوان', 'جوانات', 'كشكيت', 'جاسكيت', 'حشوة', 'جوان وش سلندر', 'جوان كارتيرة'],
    ['بلية', 'بيلية', 'بلي', 'رمان بلي', 'رولمان', 'بيرنج', 'رولمان بلي'],
    ['سوستة', 'سوسته', 'ياي', 'يايات', 'زنبرك', 'زمبرك', 'سبرنج'],
    ['خرطوم', 'خراطيم', 'هوز', 'لي', 'انبوب', 'وصلة خرطوم'],
    ['شنيور', 'دريل', 'مثقاب', 'هيلتي', 'دقاق'],
    ['صاروخ', 'جلخ', 'صاروخ جلخ', 'قطعية', 'قرص قطعية', 'حجر جلخ'],
    ['صباب', 'صبابات', 'صمام', 'صمامات', 'فالف'],
    ['سير', 'سيور', 'قشاط', 'حزام'],
    ['طلمبة', 'طرمبة', 'مضخة', 'بمب', 'طلمبه', 'طرمبه'],
    ['عصفورة', 'عصفوره', 'تاكيه', 'تاكيهات', 'شواكيش', 'شاكوش'],
    ['كرنك', 'عمود كرنك', 'عامود كرنك', 'كردان', 'عمود مرفق'],
    ['كامة', 'كامه', 'عمود كامات', 'عامود كامات', 'شجرة كامات'],
    ['طنبورة', 'طنبوره', 'بكرة', 'بكره', 'بولي'],
    ['حبل شداد', 'شداد', 'هندل', 'منافيل', 'مانفيل', 'منفيل', 'حبل تشغيل'],
    ['فلتر', 'فيلتر', 'منقي', 'مصفاة', 'مصفاه', 'فلتر زيت', 'فلتر بنزين', 'فلتر هواء'],
    ['شاحن', 'ادابتر', 'شاحنة', 'ترانس', 'محول'],
    ['مفتاح', 'لقمة', 'بنسة', 'زرادية', 'كماشة', 'مفك'],
    ['ماطور', 'موتور', 'مطور', 'محرك', 'انجير'],
    ['غاطس', 'طلمبة غاطسة', 'موتور غاطس', 'غطاس'],
    ['منشار', 'شجر', 'منشار شجر', 'شاكي', 'منشار بنزين', 'منشار كهرباء']
]

def normalize_arabic(text: str) -> str:
    """
    Standard Arabic normalization:
    - Strips tashkeel (diacritics) & tatweel
    - Normalizes alefs (أ, إ, آ, ٱ -> ا)
    - Normalizes taa marbuta (ة -> ه)
    - Normalizes alef maksura (ى -> ي)
    - Normalizes hamzas (ؤ, ئ -> ء)
    - Converts digits
    """
    if not text:
        return ""
    text = str(text).strip()
    # Remove diacritics & tatweel
    text = re.sub(r'[\u064B-\u065F\u0670\u0640]', '', text)
    # Normalize letters
    text = re.sub(r'[أإآٱ]', 'ا', text)
    text = re.sub(r'ة', 'ه', text)
    text = re.sub(r'ى', 'ي', text)
    text = re.sub(r'[ؤئ]', 'ء', text)
    # Digits
    eastern_digits = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
    text = text.translate(eastern_digits)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def get_arabic_variants(query: str) -> list[str]:
    """
    Generates all common spelling variants and synonyms of a search query.
    """
    if not query:
        return []
    
    clean_q = query.strip()
    norm_q = normalize_arabic(clean_q)
    
    variants = set()
    variants.add(clean_q)
    variants.add(norm_q)

    # 1. Synonyms expansion
    for group in SYNONYM_GROUPS:
        norm_group = [normalize_arabic(w) for w in group]
        if any(norm_q == w or norm_q in w or w in norm_q for w in norm_group):
            for syn in norm_group:
                variants.add(syn)

    # 2. Alef variants at start
    if norm_q.startswith('ا'):
        rest = norm_q[1:]
        variants.add('أ' + rest)
        variants.add('إ' + rest)
        variants.add('آ' + rest)
    elif norm_q.startswith(('أ', 'إ', 'آ')):
        rest = norm_q[1:]
        variants.add('ا' + rest)

    # 3. Endings (ة vs ه vs ي vs ى)
    if norm_q.endswith('ه'):
        variants.add(norm_q[:-1] + 'ة')
    elif norm_q.endswith('ة'):
        variants.add(norm_q[:-1] + 'ه')
    
    if norm_q.endswith('ي'):
        variants.add(norm_q[:-1] + 'ى')
    elif norm_q.endswith('ى'):
        variants.add(norm_q[:-1] + 'ي')

    # 4. Long Vowels expansion/collapse (Phonetic variants)
    vowels_stripped = re.sub(r'[اوية]', '', norm_q)
    if vowels_stripped and len(vowels_stripped) >= 2:
        variants.add(vowels_stripped)

    # Insert Alif between 1st and 2nd char if 3+ chars: e.g. تنك -> تانك, صب -> صباب
    if len(norm_q) >= 3 and 'ا' not in norm_q:
        variants.add(norm_q[0] + 'ا' + norm_q[1:])
    # Remove Alif after 1st char: e.g. تانك -> تنك, صباب -> صب
    if len(norm_q) >= 3 and norm_q[1] == 'ا':
        variants.add(norm_q[0] + norm_q[2:])
        
    # Insert Yaa after 1st char: e.g. فلتر -> فيلتر
    if len(norm_q) >= 3 and 'ي' not in norm_q:
        variants.add(norm_q[0] + 'ي' + norm_q[1:])
    # Remove Yaa after 1st char: e.g. فيلتر -> فلتر
    if len(norm_q) >= 3 and norm_q[1] == 'ي':
        variants.add(norm_q[0] + norm_q[2:])

    # Waw / Alif substitution: e.g. موتور <-> ماطور
    if 'و' in norm_q:
        variants.add(norm_q.replace('و', 'ا'))
        variants.add(norm_q.replace('و', ''))
    if 'ا' in norm_q:
        variants.add(norm_q.replace('ا', 'و'))

    return [v for v in variants if v]

def build_arabic_search_q(query: str, fields: list[str]) -> Q:
    """
    Builds a comprehensive Django Q object for multi-field, multi-variant Arabic search.
    """
    if not query or not query.strip() or not fields:
        return Q()
    
    variants = get_arabic_variants(query)
    combined_q = Q()
    
    for variant in variants:
        for field in fields:
            combined_q |= Q(**{f"{field}__icontains": variant})
            
    return combined_q
