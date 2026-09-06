/* Three languages, and a direction that changes with them.
 *
 * COUNSEL's record has to read as one document whatever language a turn was
 * authored in, so the UI ships all three rather than translating on demand.
 * The strings are deliberately few: a boardroom tool's chrome should be almost
 * invisible next to the text it holds. */

export const LANGS = ["en", "hi", "ar"] as const;
export type Lang = (typeof LANGS)[number];

export const DIR: Record<Lang, "ltr" | "rtl"> = { en: "ltr", hi: "ltr", ar: "rtl" };
export const LANG_LABEL: Record<Lang, string> = { en: "EN", hi: "हि", ar: "ع" };

type Dict = {
  brand: string;
  tagline: string;
  nav: { documents: string; ask: string; security: string };
  documents: {
    title: string;
    lede: string;
    drop: string;
    dropHint: string;
    empty: string;
    chunks: string;
    findings: string;
    languages: string;
    untrusted: string;
    uploading: string;
  };
  ask: {
    title: string;
    lede: string;
    placeholder: string;
    submit: string;
    searching: string;
    empty: string;
    noCorpus: string;
    lexical: string;
    semantic: string;
    both: string;
    degraded: string;
  };
  security: {
    title: string;
    lede: string;
    placeholder: string;
    submit: string;
    clean: string;
    tryAttack: string;
    tryGovernance: string;
    fenced: string;
  };
  theme: { light: string; dark: string };
};

const en: Dict = {
  brand: "COUNSEL",
  tagline: "Five mandates argue. The record outlives the argument.",
  nav: { documents: "Documents", ask: "Ask", security: "Security" },
  documents: {
    title: "Documents",
    lede: "What the board has read. Every upload is treated as something a stranger wrote.",
    drop: "Add a document",
    dropHint: "PDF, DOCX, Markdown or plain text",
    empty: "Nothing on the table yet.",
    chunks: "passages",
    findings: "flagged spans",
    languages: "languages",
    untrusted: "untrusted",
    uploading: "Reading",
  },
  ask: {
    title: "Ask",
    lede: "Search the record. Every passage returned can be cited to an exact span.",
    placeholder: "Why did the CFO object to the payback period?",
    submit: "Search",
    searching: "Searching",
    empty: "No passage matched.",
    noCorpus: "Add a document first — there is nothing to search.",
    lexical: "wording",
    semantic: "meaning",
    both: "wording + meaning",
    degraded: "Vector search was skipped",
  },
  security: {
    title: "Security",
    lede: "Paste anything. This is the scanner every uploaded document and search result passes through.",
    placeholder: "Paste text to scan…",
    submit: "Scan",
    clean: "Nothing flagged. This text reads as prose, not as an instruction.",
    tryAttack: "Try an attack",
    tryGovernance: "Try a real policy",
    fenced: "How the model would see it",
  },
  theme: { light: "Light", dark: "Dark" },
};

const hi: Dict = {
  brand: "COUNSEL",
  tagline: "पाँच अधिदेश बहस करते हैं। अभिलेख बहस से अधिक टिकता है।",
  nav: { documents: "दस्तावेज़", ask: "पूछें", security: "सुरक्षा" },
  documents: {
    title: "दस्तावेज़",
    lede: "बोर्ड ने क्या पढ़ा है। हर अपलोड को किसी अजनबी का लिखा माना जाता है।",
    drop: "दस्तावेज़ जोड़ें",
    dropHint: "PDF, DOCX, Markdown या सादा पाठ",
    empty: "मेज़ पर अभी कुछ नहीं है।",
    chunks: "अंश",
    findings: "चिह्नित अंश",
    languages: "भाषाएँ",
    untrusted: "अविश्वसनीय",
    uploading: "पढ़ा जा रहा है",
  },
  ask: {
    title: "पूछें",
    lede: "अभिलेख खोजें। लौटाया गया हर अंश सटीक स्थान से उद्धृत किया जा सकता है।",
    placeholder: "सीएफओ ने भुगतान अवधि पर आपत्ति क्यों जताई?",
    submit: "खोजें",
    searching: "खोज जारी",
    empty: "कोई अंश मेल नहीं खाया।",
    noCorpus: "पहले दस्तावेज़ जोड़ें — खोजने के लिए कुछ नहीं है।",
    lexical: "शब्द",
    semantic: "अर्थ",
    both: "शब्द + अर्थ",
    degraded: "सदिश खोज छोड़ दी गई",
  },
  security: {
    title: "सुरक्षा",
    lede: "कुछ भी चिपकाएँ। हर दस्तावेज़ और खोज परिणाम इसी स्कैनर से गुज़रता है।",
    placeholder: "स्कैन करने के लिए पाठ चिपकाएँ…",
    submit: "स्कैन",
    clean: "कुछ चिह्नित नहीं। यह पाठ निर्देश नहीं, गद्य है।",
    tryAttack: "हमला आज़माएँ",
    tryGovernance: "वास्तविक नीति आज़माएँ",
    fenced: "मॉडल इसे कैसे देखेगा",
  },
  theme: { light: "उजला", dark: "गहरा" },
};

const ar: Dict = {
  brand: "COUNSEL",
  tagline: "خمسة تفويضات تتجادل. والسجل يبقى بعد الجدال.",
  nav: { documents: "المستندات", ask: "اسأل", security: "الأمن" },
  documents: {
    title: "المستندات",
    lede: "ما قرأه المجلس. كل ملف مرفوع يُعامل كنص كتبه شخص غريب.",
    drop: "أضف مستنداً",
    dropHint: "PDF أو DOCX أو Markdown أو نص عادي",
    empty: "لا شيء على الطاولة بعد.",
    chunks: "مقاطع",
    findings: "مقاطع مُعلَّمة",
    languages: "لغات",
    untrusted: "غير موثوق",
    uploading: "جارٍ القراءة",
  },
  ask: {
    title: "اسأل",
    lede: "ابحث في السجل. كل مقطع يُعاد يمكن الاستشهاد به إلى موضعه بالضبط.",
    placeholder: "لماذا اعترض المدير المالي على فترة الاسترداد؟",
    submit: "ابحث",
    searching: "جارٍ البحث",
    empty: "لا يوجد مقطع مطابق.",
    noCorpus: "أضف مستنداً أولاً — لا يوجد ما يمكن البحث فيه.",
    lexical: "اللفظ",
    semantic: "المعنى",
    both: "اللفظ والمعنى",
    degraded: "تم تخطي البحث الدلالي",
  },
  security: {
    title: "الأمن",
    lede: "الصق أي نص. هذا هو الماسح الذي يمر به كل مستند وكل نتيجة بحث.",
    placeholder: "الصق نصاً لفحصه…",
    submit: "افحص",
    clean: "لم يُعلَّم شيء. هذا النص نثر، وليس تعليمات.",
    tryAttack: "جرّب هجوماً",
    tryGovernance: "جرّب سياسة حقيقية",
    fenced: "كيف سيراه النموذج",
  },
  theme: { light: "فاتح", dark: "داكن" },
};

export const DICT: Record<Lang, Dict> = { en, hi, ar };
export type { Dict };
