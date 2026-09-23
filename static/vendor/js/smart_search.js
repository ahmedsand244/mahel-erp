/**
 * =========================================================================
 * MAHEL ERP - Universal Arabic NLP & Smart Search Engine
 * =========================================================================
 * Provides phonetics, vowel skeleton reduction, typo tolerance (Levenshtein),
 * and comprehensive Arabic character normalization across all modules.
 */

(function(window) {
    'use strict';

    /**
     * 1. Arabic Text Normalization
     * Normalizes all variations of Alef, Yaa, Taa Marbuta, Hamzas, Tashkeel, etc.
     */
    function normalizeArabic(str) {
        if (str === null || str === undefined) return '';
        return str
            .toString()
            .toLowerCase()
            .trim()
            .replace(/[\u064B-\u065F\u0670\u0640]/g, '') // Remove Arabic Diacritics (Tashkeel) & Tatweel
            .replace(/[أإآٱ]/g, 'ا') // Normalize all Alef forms to plain ا
            .replace(/ة/g, 'ه') // Normalize Taa Marbuta to Haa
            .replace(/ى/g, 'ي') // Normalize Alef Maksura to Yaa
            .replace(/[ؤئ]/g, 'ء') // Normalize Hamzas
            .replace(/[٠-٩]/g, d => d.charCodeAt(0) - 1632) // Convert Eastern Arabic digits to standard ASCII 0-9
            .replace(/[۰-۹]/g, d => d.charCodeAt(0) - 1776) // Convert Persian digits to standard ASCII 0-9
            .replace(/گ/g, 'ك')
            .replace(/پ/g, 'ب')
            .replace(/چ/g, 'ج')
            .replace(/ژ/g, 'ز')
            .replace(/ڤ/g, 'ف')
            .replace(/[\s\-_/\\,.]+/g, ' '); // Clean excess symbols
    }

    /**
     * 2. Arabic Consonant & Phonetic Skeleton
     * Drops long vowels (ا, و, ي, ه, a, e, i, o, u) and collapses duplicate letters.
     * Examples:
     *   "تانك"  -> "تنك"
     *   "تنك"   -> "تنك"  (Exact skeleton match!)
     *   "بوجيه" -> "بج"
     *   "بوجي"  -> "بج"   (Exact skeleton match!)
     *   "ماطور" -> "مطر"
     *   "موتور" -> "مطر"  (Exact skeleton match!)
     *   "فيلتر" -> "فلتر"
     *   "فلتر"  -> "فلتر" (Exact skeleton match!)
     *   "كابل"  -> "كبل"
     *   "كبل"   -> "كبل"  (Exact skeleton match!)
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
     * 4. Smart Single Text Matcher with Scoring
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

        // Tier 4: Vowel Skeleton Match on entire string
        const skelTarget = getArabicSkeleton(normTarget);
        const skelQuery = getArabicSkeleton(normQuery);
        if (skelQuery && skelTarget) {
            if (skelTarget === skelQuery) {
                return { match: true, score: 850 };
            }
            if (skelQuery.length >= 2 && skelTarget.includes(skelQuery)) {
                return { match: true, score: 800 };
            }
        }

        // Tier 5: Multi-word Token Matching with Phonetic and Typo Tolerance
        const qTokens = normQuery.split(' ').filter(Boolean);
        const targetTokens = normTarget.split(' ').filter(Boolean);

        if (qTokens.length === 0) return { match: true, score: 100 };

        let totalMatchedTokens = 0;
        let cumulativeScore = 0;

        for (const qTok of qTokens) {
            let tokMatched = false;
            let bestTokScore = 0;
            const qTokSkel = getArabicSkeleton(qTok);

            for (const tTok of targetTokens) {
                const tTokSkel = getArabicSkeleton(tTok);

                // Exact token
                if (tTok === qTok) {
                    tokMatched = true;
                    bestTokScore = Math.max(bestTokScore, 300);
                }
                // Token starts with query token
                else if (tTok.startsWith(qTok)) {
                    tokMatched = true;
                    bestTokScore = Math.max(bestTokScore, 240);
                }
                // Token contains query token
                else if (tTok.includes(qTok)) {
                    tokMatched = true;
                    bestTokScore = Math.max(bestTokScore, 180);
                }
                // Vowel skeleton match (تانك == تنك, ماطور == موتور, بوجيه == بوجي)
                else if (qTokSkel && tTokSkel && (qTokSkel === tTokSkel || (qTokSkel.length >= 2 && tTokSkel.includes(qTokSkel)))) {
                    tokMatched = true;
                    bestTokScore = Math.max(bestTokScore, 200);
                }
                // Typo / Levenshtein Tolerance
                else if (qTok.length >= 3) {
                    const maxDist = qTok.length <= 4 ? 1 : 2;
                    const dist = levenshteinDist(qTok, tTok);
                    if (dist <= maxDist) {
                        tokMatched = true;
                        bestTokScore = Math.max(bestTokScore, 140 - (dist * 20));
                    }
                }
            }

            if (tokMatched) {
                totalMatchedTokens++;
                cumulativeScore += bestTokScore;
            }
        }

        // All query tokens must match for multi-token queries
        if (totalMatchedTokens === qTokens.length) {
            return { match: true, score: 400 + cumulativeScore };
        }

        // Character subsequence fallback for quick typing
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
     * 5. Smart Product Matcher
     * Matches across Product Name, SKU, Barcode, and Category.
     */
    function smartMatchProduct(product, query) {
        if (!query || !query.toString().trim()) {
            return { match: true, score: 100 };
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
     * 6. Universal Smart List Filter
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
     * 7. Simple Boolean Checker
     * Convenient single-line check: window.smartMatchText("تانك بنزين", "تنك") -> true
     */
    function smartMatchText(target, query) {
        return calculateArabicMatchScore(target, query).match;
    }

    // Expose all utilities globally
    window.ArabicSmartSearch = {
        normalize: normalizeArabic,
        getSkeleton: getArabicSkeleton,
        levenshtein: levenshteinDist,
        calculateScore: calculateArabicMatchScore,
        matchProduct: smartMatchProduct,
        filterList: smartFilterList,
        matchText: smartMatchText
    };

    // Global Top-Level Shorthands for convenient use in Alpine.js / vanilla JS
    window.normalizeArabicText = normalizeArabic;
    window.getArabicVowelSkeleton = getArabicSkeleton;
    window.calculateProductMatchScore = smartMatchProduct;
    window.calculateArabicMatchScore = calculateArabicMatchScore;
    window.smartFilterProducts = (list, q) => smartFilterList(list, q, null);
    window.smartFilterList = smartFilterList;
    window.smartMatchText = smartMatchText;

})(window);
