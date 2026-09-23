/**
 * =========================================================================
 * MAHEL ERP - Universal Arabic NLP & Hybrid Smart Search Engine
 * =========================================================================
 * Designed for Agricultural / Industrial Equipment, Spare Parts & Inventory.
 * Features:
 *  1. Deep Arabic Normalization (Alef, Taa, Yaa, Hamzas, Diacritics, Digits)
 *  2. Vowel Skeleton & Consonant Reduction (تانك <-> تنك, صباب <-> صب, موبينة <-> مبينه)
 *  3. Equipment & Spare Parts Domain Synonyms Dictionary (بخاخة <-> رشاش, بستم <-> مكبس, موبينة <-> كويل)
 *  4. Typo Tolerance & Levenshtein Distance Matrix
 *  5. Multi-tiered Relevance Scoring
 * =========================================================================
 */

(function(window) {
    'use strict';

    /**
     * ── Domain Synonyms & Aliases Dictionary for Equipment & Spare Parts ──
     * Maps colloquial, market, and technical terms bidirectionally.
     */
    const SYNONYM_GROUPS = [
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
    ];

    // Build Fast Lookup Synonyms Map
    const SYNONYM_MAP = new Map();
    for (const group of SYNONYM_GROUPS) {
        const normalizedGroup = group.map(normalizeArabic);
        for (const word of normalizedGroup) {
            if (!SYNONYM_MAP.has(word)) {
                SYNONYM_MAP.set(word, new Set());
            }
            const set = SYNONYM_MAP.get(word);
            for (const syn of normalizedGroup) {
                if (syn !== word) set.add(syn);
            }
        }
    }

    /**
     * 1. Arabic Text Normalization
     */
    function normalizeArabic(str) {
        if (str === null || str === undefined) return '';
        return str
            .toString()
            .toLowerCase()
            .trim()
            .replace(/[\u064B-\u065F\u0670\u0640]/g, '') // Remove Tashkeel & Tatweel
            .replace(/[أإآٱ]/g, 'ا') // Normalize Alefs
            .replace(/ة/g, 'ه') // Normalize Taa Marbuta
            .replace(/ى/g, 'ي') // Normalize Alef Maksura
            .replace(/[ؤئ]/g, 'ء') // Normalize Hamzas
            .replace(/[٠-٩]/g, d => d.charCodeAt(0) - 1632) // Eastern Arabic digits
            .replace(/[۰-۹]/g, d => d.charCodeAt(0) - 1776) // Persian digits
            .replace(/گ/g, 'ك')
            .replace(/پ/g, 'ب')
            .replace(/چ/g, 'ج')
            .replace(/ژ/g, 'ز')
            .replace(/ڤ/g, 'ف')
            .replace(/[\s\-_/\\,.:;()[\]{}|<>+=*&^%$#@!~`"']+/g, ' ') // Punctuation & spaces
            .trim();
    }

    /**
     * 2. Vowel Skeleton & Consonant Extraction
     * Strips long vowels (ا, و, ي, ه, a, e, i, o, u) and duplicate letters.
     */
    function getArabicSkeleton(str) {
        const norm = normalizeArabic(str);
        if (!norm) return '';
        return norm
            .replace(/[اويةaeiou]/g, '') // Remove long vowels
            .replace(/(.)\1+/g, '$1')   // Collapse duplicate adjacent letters
            .trim();
    }

    /**
     * 3. Levenshtein Edit Distance Calculation
     */
    function levenshteinDist(s1, s2) {
        if (s1 === s2) return 0;
        if (!s1.length) return s2.length;
        if (!s2.length) return s1.length;
        const v0 = new Array(s2.length + 1);
        const v1 = new Array(s2.length + 1);
        for (let i = 0; i <= s2.length; i++) v0[i] = i;
        for (let i = 0; i < s1.length; i++) {
            v1[0] = i + 1;
            for (let j = 0; j < s2.length; j++) {
                const cost = (s1[i] === s2[j]) ? 0 : 1;
                v1[j + 1] = Math.min(v1[j] + 1, v0[j + 1] + 1, v0[j] + cost);
            }
            for (let j = 0; j <= s2.length; j++) v0[j] = v1[j];
        }
        return v0[s2.length];
    }

    /**
     * 4. Synonyms Expansion Helper
     * Expands a normalized token into itself + any known synonyms.
     */
    function getSynonymsForToken(tok) {
        const normTok = normalizeArabic(tok);
        const set = new Set([normTok]);
        if (SYNONYM_MAP.has(normTok)) {
            for (const syn of SYNONYM_MAP.get(normTok)) {
                set.add(syn);
            }
        }
        return Array.from(set);
    }

    /**
     * 5. Smart Single Text Matcher with Comprehensive Scoring
     * Evaluates how well target text matches query string.
     * Returns: { match: boolean, score: number }
     */
    function calculateArabicMatchScore(target, query) {
        if (!query || !query.toString().trim()) {
            return { match: true, score: 100 };
        }

        const normTarget = normalizeArabic(target || '');
        const normQuery = normalizeArabic(query || '');

        if (!normTarget) return { match: false, score: 0 };
        if (!normQuery) return { match: true, score: 100 };

        // Tier 1: Exact Match
        if (normTarget === normQuery) {
            return { match: true, score: 1500 };
        }

        // Tier 2: Starts with Query
        if (normTarget.startsWith(normQuery)) {
            return { match: true, score: 1200 };
        }

        // Tier 3: Direct Substring Match
        if (normTarget.includes(normQuery)) {
            return { match: true, score: 900 };
        }

        // Tier 4: Vowel Skeleton Match on full phrase (e.g. تانك بنزين == تنك بنزين)
        const skelTarget = getArabicSkeleton(normTarget);
        const skelQuery = getArabicSkeleton(normQuery);
        if (skelQuery && skelTarget) {
            if (skelTarget === skelQuery) {
                return { match: true, score: 850 };
            }
            if (skelQuery.length >= 2 && skelTarget.includes(skelQuery)) {
                return { match: true, score: 750 };
            }
        }

        // Tier 5: Multi-word Token Matching with Synonyms & Phonetic & Typo Tolerance
        const qTokens = normQuery.split(' ').filter(Boolean);
        const targetTokens = normTarget.split(' ').filter(Boolean);

        if (qTokens.length === 0) return { match: true, score: 100 };

        let totalMatchedTokens = 0;
        let cumulativeScore = 0;

        for (const qTok of qTokens) {
            let tokMatched = false;
            let bestTokScore = 0;
            const qTokSkel = getArabicSkeleton(qTok);
            const qTokSynonyms = getSynonymsForToken(qTok);

            for (const tTok of targetTokens) {
                const tTokSkel = getArabicSkeleton(tTok);

                // A. Exact Token
                if (tTok === qTok) {
                    tokMatched = true;
                    bestTokScore = Math.max(bestTokScore, 300);
                    break;
                }
                // B. Token starts with or contains query token
                else if (tTok.startsWith(qTok)) {
                    tokMatched = true;
                    bestTokScore = Math.max(bestTokScore, 240);
                }
                else if (tTok.includes(qTok)) {
                    tokMatched = true;
                    bestTokScore = Math.max(bestTokScore, 180);
                }
                // C. Synonyms Match (e.g. بخاخة <-> رشاش, بستم <-> مكبس, موبينة <-> كويل)
                else if (qTokSynonyms.some(syn => tTok === syn || tTok.includes(syn) || syn.includes(tTok))) {
                    tokMatched = true;
                    bestTokScore = Math.max(bestTokScore, 260);
                }
                // D. Vowel Skeleton Match (تانك == تنك, صباب == صب, ماطور == موتور, بوجيه == بوجي)
                else if (qTokSkel && tTokSkel && (qTokSkel === tTokSkel || (qTokSkel.length >= 2 && tTokSkel.includes(qTokSkel)))) {
                    tokMatched = true;
                    bestTokScore = Math.max(bestTokScore, 220);
                }
                // E. Typo Tolerance / Levenshtein Distance
                else if (qTok.length >= 3) {
                    const maxDist = qTok.length <= 4 ? 1 : 2;
                    const dist = levenshteinDist(qTok, tTok);
                    if (dist <= maxDist) {
                        tokMatched = true;
                        bestTokScore = Math.max(bestTokScore, 150 - (dist * 30));
                    }
                }
            }

            if (tokMatched) {
                totalMatchedTokens++;
                cumulativeScore += bestTokScore;
            }
        }

        // All query tokens matched
        if (totalMatchedTokens === qTokens.length) {
            return { match: true, score: 400 + cumulativeScore };
        }

        // Character subsequence fallback
        if (normQuery.length >= 3) {
            let qIdx = 0;
            for (let i = 0; i < normTarget.length && qIdx < normQuery.length; i++) {
                if (normTarget[i] === normQuery[qIdx]) {
                    qIdx++;
                }
            }
            if (qIdx === normQuery.length) {
                return { match: true, score: 250 };
            }
        }

        return { match: false, score: 0 };
    }

    /**
     * 6. Smart Product Matcher
     * Matches across Product Name, SKU, Barcode, and Category.
     */
    function smartMatchProduct(product, query) {
        if (!query || !query.toString().trim()) {
            return { match: true, score: 100 };
        }
        if (!product) {
            return { match: false, score: 0 };
        }

        const normQuery = normalizeArabic(query);
        const normBarcode = normalizeArabic(product.barcode || '');
        const normSku = normalizeArabic(product.sku || '');

        // Barcode / SKU exact priority
        if (normBarcode && normBarcode === normQuery) return { match: true, score: 3000 };
        if (normBarcode && normBarcode.includes(normQuery)) return { match: true, score: 2200 };
        if (normSku && normSku === normQuery) return { match: true, score: 2500 };
        if (normSku && normSku.includes(normQuery)) return { match: true, score: 1800 };

        // Name match score
        const nameResult = calculateArabicMatchScore(product.name || '', query);
        if (nameResult.match) {
            return nameResult;
        }

        // Category match fallback
        if (product.category) {
            const catResult = calculateArabicMatchScore(product.category, query);
            if (catResult.match) {
                return { match: true, score: catResult.score * 0.7 };
            }
        }

        return { match: false, score: 0 };
    }

    /**
     * 7. Universal Smart List Filter
     * Filters and sorts any array of objects based on smart scoring.
     */
    function smartFilterList(items, query, extractors) {
        if (!Array.isArray(items)) return [];
        if (!query || !query.toString().trim()) return items;

        const scoredItems = [];

        for (const item of items) {
            let maxScore = 0;
            let isMatched = false;

            if (typeof extractors === 'function') {
                const text = extractors(item);
                const res = calculateArabicMatchScore(text, query);
                if (res.match) {
                    isMatched = true;
                    maxScore = res.score;
                }
            } else if (Array.isArray(extractors)) {
                for (const field of extractors) {
                    const text = item[field];
                    const res = calculateArabicMatchScore(text, query);
                    if (res.match && res.score > maxScore) {
                        isMatched = true;
                        maxScore = res.score;
                    }
                }
            } else {
                // Default product matching
                const res = smartMatchProduct(item, query);
                if (res.match) {
                    isMatched = true;
                    maxScore = res.score;
                }
            }

            if (isMatched) {
                scoredItems.push({ item: item, score: maxScore });
            }
        }

        // Sort by score descending
        scoredItems.sort((a, b) => b.score - a.score);

        return scoredItems.map(entry => entry.item);
    }

    /**
     * 8. Boolean Matcher Helper
     */
    function smartMatchText(target, query) {
        return calculateArabicMatchScore(target, query).match;
    }

    // Expose Global Object
    window.ArabicSmartSearch = {
        normalize: normalizeArabic,
        getSkeleton: getArabicSkeleton,
        levenshtein: levenshteinDist,
        synonyms: SYNONYM_MAP,
        getSynonyms: getSynonymsForToken,
        calculateScore: calculateArabicMatchScore,
        matchProduct: smartMatchProduct,
        filterList: smartFilterList,
        matchText: smartMatchText
    };

    // Shorthands attached to window
    window.normalizeArabicText = normalizeArabic;
    window.getArabicVowelSkeleton = getArabicSkeleton;
    window.calculateProductMatchScore = smartMatchProduct;
    window.calculateArabicMatchScore = calculateArabicMatchScore;
    window.smartMatchProduct = smartMatchProduct;
    window.smartFilterProducts = (list, q) => smartFilterList(list, q, null);
    window.smartFilterList = smartFilterList;
    window.smartMatchText = smartMatchText;

})(typeof window !== 'undefined' ? window : this);
