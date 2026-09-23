import re
from django.db.models import Q

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
    Generates all common spelling variants of a search query in Arabic.
    Handles:
    - Tanak vs Tank (تانك / تنك)
    - Motor vs Mator (موتور / ماطور / مطور)
    - Bougie vs Bougy (بوجيه / بوجي / بجه)
    - Filter vs Fylter (فلتر / فيلتر)
    - Cable vs Kbl (كابل / كبل)
    - Alef variants (احمد / أحمد / إحمد / آحمد)
    - Taa Marbuta variants (ماكينة / ماكينه / مكنة / مكنه)
    - Yaa variants (علي / على)
    """
    if not query:
        return []
    
    clean_q = query.strip()
    norm_q = normalize_arabic(clean_q)
    
    variants = set()
    variants.add(clean_q)
    variants.add(norm_q)

    # 1. Alef variants at start
    if norm_q.startswith('ا'):
        rest = norm_q[1:]
        variants.add('أ' + rest)
        variants.add('إ' + rest)
        variants.add('آ' + rest)
    elif norm_q.startswith(('أ', 'إ', 'آ')):
        rest = norm_q[1:]
        variants.add('ا' + rest)

    # 2. Endings (ة vs ه vs ي vs ى)
    if norm_q.endswith('ه'):
        variants.add(norm_q[:-1] + 'ة')
    elif norm_q.endswith('ة'):
        variants.add(norm_q[:-1] + 'ه')
    
    if norm_q.endswith('ي'):
        variants.add(norm_q[:-1] + 'ى')
    elif norm_q.endswith('ى'):
        variants.add(norm_q[:-1] + 'ي')

    # 3. Long Vowels expansion/collapse (Phonetic variants)
    # E.g., 'تنك' -> 'تانك', 'تونك', 'تينك'
    # E.g., 'تانك' -> 'تنك'
    # E.g., 'موتور' -> 'ماطور', 'مطور'
    # E.g., 'بوجيه' -> 'بوجي', 'بجه'
    # E.g., 'كبل' -> 'كابل'
    # E.g., 'فلتر' -> 'فيلتر'
    # Strip internal 'ا', 'و', 'ي' to create root skeleton
    vowels_stripped = re.sub(r'[اوية]', '', norm_q)
    if vowels_stripped and len(vowels_stripped) >= 2:
        variants.add(vowels_stripped)

    # Insert Alif between 1st and 2nd char if 3+ chars: e.g. تنك -> تانك, كبل -> كابل, شنش -> شانش
    if len(norm_q) >= 3 and 'ا' not in norm_q:
        variants.add(norm_q[0] + 'ا' + norm_q[1:])
    # Remove Alif after 1st char: e.g. تانك -> تنك, كابل -> كبل
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
