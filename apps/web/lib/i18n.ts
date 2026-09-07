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
  nav: { room: string; decide: string; ledger: string; documents: string; ask: string; security: string };
  decide: {
    title: string; lede: string; noSession: string; evidence: string; evidenceLede: string;
    addEvidence: string; remove: string; options: string; score: string; scoring: string;
    ranking: string; option: string; total: string; confidence: string; seats: string;
    counterfactual: string; flip: string; andTheRoomPrefers: string; insteadOf: string;
    ungrounded: string; argueFromMandate: string; leaningOn: string;
    writeMemo: string; writing: string; memo: string; cited: string; uncited: string;
    ungroundedMemo: string;
  };
  ledger: {
    title: string; lede: string; record: string; recordLede: string; chosen: string;
    actual: string; notes: string; save: string; calibration: string; brier: string;
    outcomes: string; hitRate: string; pending: string; needsMore: string;
    worseThanCoin: string; outcomesTitle: string; noOutcomes: string; noNotes: string;
    chose: string; wasRight: string; right: string; wrong: string;
  };
  room: {
    title: string; lede: string; question: string; stage: string; open: string;
    opened: string; round: string; runRound: string; arguing: string; stop: string;
    record: string; sealed: string; broken: string; flags: string; unsigned: string;
    unsignedNote: string; auditor: string; chair: string; chairLede: string;
    chairPlaceholder: string; speak: string; chairHeard: string;
    blindSpots: string; blindSpotsLede: string;
    chamber: string; replay: string; turn: string; of: string;
    fallbackNote: string; silent: string; speakingNow: string;
  };
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
  nav: { room: "Room", decide: "Decide", ledger: "Ledger", documents: "Documents", ask: "Ask", security: "Security" },
  decide: {
    title: "Decide",
    lede: "Name what the room may lean on, score the options, then ask what would change the answer.",
    noSession: "No session yet. Open the room first, then come back.",
    evidence: "Evidence",
    evidenceLede: "What the room is allowed to lean on. Each seat must say which of these its score rests on, and removing one is how the counterfactual works.",
    addEvidence: "Add evidence",
    remove: "Remove",
    options: "Options",
    score: "Score the options",
    scoring: "Scoring",
    ranking: "How the room scored it",
    option: "Option",
    total: "Total",
    confidence: "Confidence",
    seats: "Seats",
    counterfactual: "What would change our mind",
    flip: "flips it",
    andTheRoomPrefers: "and the room prefers",
    insteadOf: "instead of",
    ungrounded: "no evidence",
    argueFromMandate: "argued from its mandate, citing no evidence",
    leaningOn: "leaning on",
    writeMemo: "Write the memo",
    writing: "Writing",
    memo: "Decision memo",
    cited: "cited",
    uncited: "uncited",
    ungroundedMemo: "no documents in the room",
  },
  ledger: {
    title: "The Ledger",
    lede: "What the room predicted, what actually happened, and how well each seat knew its own mind.",
    record: "Record an outcome",
    recordLede: "Months later, when the world has answered. This is the only thing that turns prompt-defined expertise into a measurement.",
    chosen: "What the room chose",
    actual: "What turned out right",
    notes: "What happened",
    save: "Record it",
    calibration: "Calibration",
    brier: "Brier",
    outcomes: "outcomes",
    hitRate: "backed the right option",
    pending: "not yet scored",
    needsMore: "Needs {n} more outcomes before a score means anything.",
    worseThanCoin: "worse than a coin",
    outcomesTitle: "Outcomes",
    noOutcomes: "Nothing has been settled yet.",
    noNotes: "No notes recorded.",
    chose: "chose",
    wasRight: "right answer",
    right: "right",
    wrong: "wrong",
  },
  room: {
    title: "The Room",
    lede: "Five mandates argue the decision. You can watch them think, and you can interrupt.",
    question: "The decision",
    stage: "Stage",
    open: "Open the room",
    opened: "Room open. Nobody has spoken yet.",
    round: "Round",
    runRound: "Run a round",
    arguing: "Arguing",
    stop: "Stop",
    record: "Record",
    sealed: "sealed",
    broken: "chain broken",
    flags: "flagged",
    unsigned: "draft",
    unsignedNote: "spoken, not yet sealed",
    auditor: "What the Auditor caught",
    chair: "Speak as Chair",
    chairLede: "Your interjection is recorded as a signed turn like any other. You are a participant in the record, not an editor of it.",
    chairPlaceholder: "Assume the plant loses a shift in Q1. Re-argue.",
    speak: "Speak",
    chairHeard: "Chair recorded. The room will hear it next round.",
    blindSpots: "What each seat admits it gets wrong",
    blindSpotsLede: "Divergence only works if the room's biases are on the table. Read these before weighing anything above.",
    chamber: "The table",
    replay: "Replay the debate",
    turn: "Turn",
    of: "of",
    fallbackNote: "Drawn flat: this machine has no WebGL. Same seats, same edges, same numbers.",
    silent: "the chair",
    speakingNow: "is speaking",
  },
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
  nav: { room: "कक्ष", decide: "निर्णय", ledger: "बही", documents: "दस्तावेज़", ask: "पूछें", security: "सुरक्षा" },
  decide: {
    title: "निर्णय",
    lede: "कक्ष किस पर भरोसा कर सकता है यह बताएँ, विकल्पों को अंक दें, फिर पूछें कि उत्तर क्या बदलेगा।",
    noSession: "अभी कोई सत्र नहीं। पहले कक्ष खोलें, फिर लौटें।",
    evidence: "साक्ष्य",
    evidenceLede: "कक्ष किस पर भरोसा कर सकता है। हर पक्ष को बताना होगा कि उसका अंक किस पर टिका है, और एक हटाना ही प्रति-तथ्य की विधि है।",
    addEvidence: "साक्ष्य जोड़ें",
    remove: "हटाएँ",
    options: "विकल्प",
    score: "विकल्पों को अंक दें",
    scoring: "अंकन जारी",
    ranking: "कक्ष ने कैसे अंक दिए",
    option: "विकल्प",
    total: "कुल",
    confidence: "विश्वास",
    seats: "पक्ष",
    counterfactual: "हमारा मन क्या बदलेगा",
    flip: "पलट देता है",
    andTheRoomPrefers: "और कक्ष चुनता है",
    insteadOf: "के बजाय",
    ungrounded: "कोई साक्ष्य नहीं",
    argueFromMandate: "अपने अधिदेश से तर्क किया, कोई साक्ष्य नहीं दिया",
    leaningOn: "आधारित",
    writeMemo: "ज्ञापन लिखें",
    writing: "लिखा जा रहा",
    memo: "निर्णय ज्ञापन",
    cited: "उद्धृत",
    uncited: "अनुद्धृत",
    ungroundedMemo: "कक्ष में कोई दस्तावेज़ नहीं",
  },
  ledger: {
    title: "बही",
    lede: "कक्ष ने क्या अनुमान लगाया, वास्तव में क्या हुआ, और हर पक्ष अपने मन को कितना जानता था।",
    record: "परिणाम दर्ज करें",
    recordLede: "महीनों बाद, जब दुनिया उत्तर दे चुकी हो। यही एकमात्र चीज़ है जो प्रॉम्प्ट-आधारित विशेषज्ञता को माप में बदलती है।",
    chosen: "कक्ष ने क्या चुना",
    actual: "क्या सही निकला",
    notes: "क्या हुआ",
    save: "दर्ज करें",
    calibration: "अंशांकन",
    brier: "ब्रायर",
    outcomes: "परिणाम",
    hitRate: "सही विकल्प चुना",
    pending: "अभी अंकित नहीं",
    needsMore: "अंक सार्थक होने से पहले {n} और परिणाम चाहिए।",
    worseThanCoin: "सिक्के से भी बदतर",
    outcomesTitle: "परिणाम",
    noOutcomes: "अभी कुछ तय नहीं हुआ।",
    noNotes: "कोई टिप्पणी नहीं।",
    chose: "चुना",
    wasRight: "सही उत्तर",
    right: "सही",
    wrong: "ग़लत",
  },
  room: {
    title: "कक्ष",
    lede: "पाँच अधिदेश निर्णय पर बहस करते हैं। आप उन्हें सोचते देख सकते हैं, और बीच में बोल सकते हैं।",
    question: "निर्णय",
    stage: "चरण",
    open: "कक्ष खोलें",
    opened: "कक्ष खुला। अभी किसी ने कुछ नहीं कहा।",
    round: "दौर",
    runRound: "एक दौर चलाएँ",
    arguing: "बहस जारी",
    stop: "रोकें",
    record: "अभिलेख",
    sealed: "मुद्रित",
    broken: "शृंखला टूटी",
    flags: "चिह्नित",
    unsigned: "प्रारूप",
    unsignedNote: "कहा गया, अभी मुद्रित नहीं",
    auditor: "अंकेक्षक ने क्या पकड़ा",
    chair: "अध्यक्ष के रूप में बोलें",
    chairLede: "आपका हस्तक्षेप किसी भी अन्य की तरह हस्ताक्षरित प्रविष्टि के रूप में दर्ज होता है। आप अभिलेख के प्रतिभागी हैं, संपादक नहीं।",
    chairPlaceholder: "मान लें संयंत्र पहली तिमाही में एक पाली खो देता है। फिर से तर्क करें।",
    speak: "बोलें",
    chairHeard: "अध्यक्ष दर्ज। कक्ष अगले दौर में सुनेगा।",
    blindSpots: "हर पक्ष अपनी कौन-सी कमज़ोरी मानता है",
    blindSpotsLede: "विचलन तभी काम करता है जब कक्ष के पूर्वाग्रह सामने हों। ऊपर कुछ भी तौलने से पहले इन्हें पढ़ें।",
    chamber: "मेज़",
    replay: "बहस दोहराएँ",
    turn: "प्रविष्टि",
    of: "में से",
    fallbackNote: "सपाट चित्र: इस मशीन में WebGL नहीं है। वही पक्ष, वही रेखाएँ, वही आँकड़े।",
    silent: "अध्यक्ष",
    speakingNow: "बोल रहे हैं",
  },
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
  nav: { room: "القاعة", decide: "القرار", ledger: "السجل", documents: "المستندات", ask: "اسأل", security: "الأمن" },
  decide: {
    title: "القرار",
    lede: "حدد ما يمكن للقاعة الاستناد إليه، وقيّم الخيارات، ثم اسأل ما الذي يغيّر الإجابة.",
    noSession: "لا توجد جلسة بعد. افتح القاعة أولاً ثم عد.",
    evidence: "الأدلة",
    evidenceLede: "ما يُسمح للقاعة بالاستناد إليه. على كل مقعد أن يذكر ما يقوم عليه تقييمه، وإزالة أحدها هي طريقة التحليل المضاد.",
    addEvidence: "أضف دليلاً",
    remove: "احذف",
    options: "الخيارات",
    score: "قيّم الخيارات",
    scoring: "التقييم جارٍ",
    ranking: "كيف قيّمت القاعة",
    option: "الخيار",
    total: "المجموع",
    confidence: "الثقة",
    seats: "المقاعد",
    counterfactual: "ما الذي يغيّر رأينا",
    flip: "يقلبه",
    andTheRoomPrefers: "وتفضّل القاعة",
    insteadOf: "بدلاً من",
    ungrounded: "بلا أدلة",
    argueFromMandate: "جادل من تفويضه دون الاستناد إلى دليل",
    leaningOn: "يستند إلى",
    writeMemo: "اكتب المذكرة",
    writing: "الكتابة جارية",
    memo: "مذكرة القرار",
    cited: "موثّق",
    uncited: "غير موثّق",
    ungroundedMemo: "لا مستندات في القاعة",
  },
  ledger: {
    title: "السجل",
    lede: "ما توقعته القاعة، وما حدث فعلاً، ومدى معرفة كل مقعد بحدود يقينه.",
    record: "سجّل نتيجة",
    recordLede: "بعد أشهر، حين يجيب الواقع. هذا وحده ما يحوّل الخبرة المعرّفة بالتوجيه إلى قياس.",
    chosen: "ما اختارته القاعة",
    actual: "ما ثبت صوابه",
    notes: "ماذا حدث",
    save: "سجّل",
    calibration: "المعايرة",
    brier: "براير",
    outcomes: "نتائج",
    hitRate: "اختار الخيار الصحيح",
    pending: "لم يُقيَّم بعد",
    needsMore: "يحتاج {n} نتائج أخرى قبل أن يعني الرقم شيئاً.",
    worseThanCoin: "أسوأ من رمي عملة",
    outcomesTitle: "النتائج",
    noOutcomes: "لم يُحسم شيء بعد.",
    noNotes: "لا ملاحظات.",
    chose: "اختار",
    wasRight: "الصواب",
    right: "صائب",
    wrong: "خاطئ",
  },
  room: {
    title: "القاعة",
    lede: "خمسة تفويضات تتجادل حول القرار. يمكنك أن تراها تفكر، ويمكنك أن تقاطع.",
    question: "القرار",
    stage: "المرحلة",
    open: "افتح القاعة",
    opened: "القاعة مفتوحة. لم يتحدث أحد بعد.",
    round: "الجولة",
    runRound: "شغّل جولة",
    arguing: "الجدال جارٍ",
    stop: "أوقف",
    record: "السجل",
    sealed: "مختوم",
    broken: "السلسلة مكسورة",
    flags: "مُعلَّم",
    unsigned: "مسودة",
    unsignedNote: "قيل، ولم يُختم بعد",
    auditor: "ما التقطه المدقق",
    chair: "تحدث بصفتك الرئيس",
    chairLede: "تُسجَّل مداخلتك كمداخلة موقَّعة مثل أي مداخلة أخرى. أنت مشارك في السجل، لا محرر له.",
    chairPlaceholder: "افترض أن المصنع يفقد وردية في الربع الأول. أعد الجدال.",
    speak: "تحدث",
    chairHeard: "سُجِّل الرئيس. ستسمعه القاعة في الجولة القادمة.",
    blindSpots: "ما يعترف كل مقعد بأنه يخطئ فيه",
    blindSpotsLede: "لا ينجح التباعد إلا إذا كانت تحيزات القاعة على الطاولة. اقرأ هذه قبل أن تزن ما سبق.",
    chamber: "الطاولة",
    replay: "أعد تشغيل النقاش",
    turn: "مداخلة",
    of: "من",
    fallbackNote: "مرسومة مسطحة: لا يدعم هذا الجهاز WebGL. المقاعد نفسها والروابط نفسها والأرقام نفسها.",
    silent: "الرئيس",
    speakingNow: "يتحدث",
  },
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
