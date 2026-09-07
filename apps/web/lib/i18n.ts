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
  nav: {
    room: string; stages: string; board: string; decide: string; ledger: string;
    report: string; crew: string; documents: string; ask: string; security: string;
  };
  crew: {
    title: string; lede: string; values: string; blindSpots: string; evidence: string;
    tools: string; noSideEffects: string; capability: string; capabilityLede: string;
    agent: string; sideEffects: string; none: string; facilitator: string;
    auditor: string; chair: string;
  };
  stages: {
    title: string; lede: string; here: string; produced: string; notYet: string;
    noArtefact: string;
  };
  board: {
    title: string; lede: string; runFramings: string; runIdeas: string; working: string;
    framings: string; framingsLede: string; ideas: string; ideasLede: string;
    whose: string; buildsOn: string; empty: string;
  };
  report: {
    title: string; lede: string; question: string; rounds: string; record: string;
    sealed: string; broken: string; build: string; building: string; copy: string;
    copied: string; copyFailed: string; print: string; exportNote: string;
    unanimous: string; noCalibration: string;
  };
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
    voiceOn: string; voiceOff: string;
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
    redteamTitle: string; redteamLede: string; redteamRun: string; redteamNoSession: string;
    step1: string; step2: string; step3: string; step4: string;
    ingested: string; detected: string; structural: string; refused: string; flagged: string;
  };
  theme: { light: string; dark: string };
};

const en: Dict = {
  brand: "COUNSEL",
  tagline: "Five mandates argue. The record outlives the argument.",
  nav: { room: "Room", stages: "Stages", board: "Board", decide: "Decide", ledger: "Ledger", report: "Report", crew: "Crew", documents: "Documents", ask: "Ask", security: "Security" },
  crew: {
    title: "The Crew",
    lede: "Who sits at the table, what each admits it gets wrong, and exactly what each one is able to do.",
    values: "What it argues from",
    blindSpots: "What it admits it under-weights",
    evidence: "What it accepts as evidence",
    tools: "Tools",
    noSideEffects: "no side effects",
    capability: "Capability",
    capabilityLede: "The whole safety claim, in one table. No tool in COUNSEL writes to the outside world, and that is asserted over the entire registry rather than reviewed by eye. Only the Facilitator can open or close a round.",
    agent: "Agent",
    sideEffects: "Side effects",
    none: "none",
    facilitator: "Facilitator",
    auditor: "Auditor",
    chair: "Chair (you)",
  },
  stages: {
    title: "Stages",
    lede: "Empathise to Learn, and what binds at each. Every rule below is enforced by a schema or flagged by the Auditor.",
    here: "you are here",
    produced: "produced",
    notYet: "nothing yet",
    noArtefact: "no artefact for this stage",
  },
  board: {
    title: "The Board",
    lede: "Framings and ideas, by seat. Nothing here is ranked: scoring an idea on the board would collapse the divergence Ideate exists to protect.",
    runFramings: "Ask for framings",
    runIdeas: "Ask for ideas",
    working: "Asking the room",
    framings: "Framings",
    framingsLede: "Define. Each seat states the problem it thinks is worth solving, as a question.",
    ideas: "Ideas",
    ideasLede: "Ideate, under the no-critique rule. Build on other seats rather than replacing them.",
    whose: "whose problem:",
    buildsOn: "builds on",
    empty: "Nothing on the board yet. Ask for framings to open Define, or for ideas to open Ideate — five seats answer at once, which takes about twenty seconds.",
  },
  report: {
    title: "Report",
    lede: "Everything the session produced, assembled for reading.",
    question: "Decision",
    rounds: "Rounds",
    record: "Record",
    sealed: "sealed",
    broken: "chain broken",
    build: "Assemble the report",
    building: "Assembling",
    copy: "Copy the memo",
    copied: "Copied",
    copyFailed: "The clipboard is not available here. Select the memo text and copy it.",
    print: "Print",
    exportNote: "COUNSEL does not send this anywhere. There is no share button and no webhook: the memo is rendered for you to read and do what you like with. An export the software performed would be the first thing an agent here did to the outside world.",
    unanimous: "every seat dissented",
    noCalibration: "No seat has {n} recorded outcomes yet, so there is nothing here worth drawing.",
  },
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
    voiceOn: "Give them voices",
    voiceOff: "Silence the room",
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
    redteamTitle: "The attack, live",
    redteamLede: "Poison a document into this session's corpus and watch what happens to it. A control nobody sees is a control nobody believes.",
    redteamRun: "Run the attack",
    redteamNoSession: "Open a room first — the attack needs a session to poison.",
    step1: "The document is taken, not refused",
    step2: "The scanner marks it",
    step3: "The tool it asked for does not exist",
    step4: "Its claim cannot reach the memo",
    ingested: "ingested",
    detected: "detected",
    structural: "structural",
    refused: "refused",
    flagged: "flagged",
  },
  theme: { light: "Light", dark: "Dark" },
};

const hi: Dict = {
  brand: "COUNSEL",
  tagline: "पाँच अधिदेश बहस करते हैं। अभिलेख बहस से अधिक टिकता है।",
  nav: { room: "कक्ष", stages: "चरण", board: "पटल", decide: "निर्णय", ledger: "बही", report: "रिपोर्ट", crew: "दल", documents: "दस्तावेज़", ask: "पूछें", security: "सुरक्षा" },
  crew: {
    title: "दल",
    lede: "मेज़ पर कौन बैठा है, हर कोई अपनी कौन-सी कमज़ोरी मानता है, और वास्तव में हर एक क्या कर सकता है।",
    values: "किस आधार पर तर्क करता है",
    blindSpots: "किसे कम आँकता है, यह स्वयं मानता है",
    evidence: "किसे प्रमाण मानता है",
    tools: "उपकरण",
    noSideEffects: "कोई दुष्प्रभाव नहीं",
    capability: "क्षमता",
    capabilityLede: "पूरा सुरक्षा दावा, एक तालिका में। COUNSEL का कोई उपकरण बाहरी दुनिया में नहीं लिखता, और यह पूरे रजिस्ट्री पर परखा जाता है। केवल संचालक ही दौर खोल या बंद कर सकता है।",
    agent: "एजेंट",
    sideEffects: "दुष्प्रभाव",
    none: "कोई नहीं",
    facilitator: "संचालक",
    auditor: "अंकेक्षक",
    chair: "अध्यक्ष (आप)",
  },
  stages: {
    title: "चरण",
    lede: "सहानुभूति से सीख तक, और हर चरण में क्या बाध्यकारी है। नीचे हर नियम या तो स्कीमा से लागू होता है या अंकेक्षक द्वारा चिह्नित।",
    here: "आप यहाँ हैं",
    produced: "बनाए गए",
    notYet: "अभी कुछ नहीं",
    noArtefact: "इस चरण की कोई कृति नहीं",
  },
  board: {
    title: "पटल",
    lede: "पक्ष अनुसार रूपरेखाएँ और विचार। यहाँ कुछ भी क्रमित नहीं: पटल पर विचार को अंक देना उसी विचलन को समाप्त कर देगा जिसकी रक्षा के लिए यह चरण है।",
    runFramings: "रूपरेखाएँ माँगें",
    runIdeas: "विचार माँगें",
    working: "कक्ष से पूछा जा रहा",
    framings: "रूपरेखाएँ",
    framingsLede: "परिभाषा। हर पक्ष प्रश्न के रूप में बताता है कि कौन-सी समस्या हल करने योग्य है।",
    ideas: "विचार",
    ideasLede: "विचलन, बिना आलोचना के नियम के अंतर्गत। दूसरों की जगह लेने के बजाय उन पर निर्माण करें।",
    whose: "किसकी समस्या:",
    buildsOn: "आधारित",
    empty: "पटल अभी खाली है। परिभाषा चरण के लिए रूपरेखाएँ माँगें, या विचलन के लिए विचार — पाँचों पक्ष एक साथ उत्तर देते हैं, जिसमें लगभग बीस सेकंड लगते हैं।",
  },
  report: {
    title: "रिपोर्ट",
    lede: "सत्र ने जो कुछ बनाया, पढ़ने के लिए एकत्रित।",
    question: "निर्णय",
    rounds: "दौर",
    record: "अभिलेख",
    sealed: "मुद्रित",
    broken: "शृंखला टूटी",
    build: "रिपोर्ट बनाएँ",
    building: "बनाया जा रहा",
    copy: "ज्ञापन कॉपी करें",
    copied: "कॉपी हुआ",
    copyFailed: "यहाँ क्लिपबोर्ड उपलब्ध नहीं। ज्ञापन चुनकर कॉपी करें।",
    print: "प्रिंट",
    exportNote: "COUNSEL इसे कहीं नहीं भेजता। कोई साझा बटन नहीं, कोई वेबहुक नहीं: ज्ञापन आपके पढ़ने के लिए है। सॉफ़्टवेयर द्वारा किया गया निर्यात पहला काम होता जो यहाँ कोई एजेंट बाहरी दुनिया में करता।",
    unanimous: "हर पक्ष ने असहमति जताई",
    noCalibration: "अभी किसी पक्ष के {n} परिणाम दर्ज नहीं, इसलिए यहाँ बनाने योग्य कुछ नहीं।",
  },
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
    voiceOn: "आवाज़ दें",
    voiceOff: "कक्ष शांत करें",
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
    redteamTitle: "हमला, प्रत्यक्ष",
    redteamLede: "इस सत्र के संग्रह में एक विषाक्त दस्तावेज़ डालें और देखें क्या होता है। जो नियंत्रण कोई देखता नहीं, उस पर कोई भरोसा नहीं करता।",
    redteamRun: "हमला चलाएँ",
    redteamNoSession: "पहले कक्ष खोलें — हमले को एक सत्र चाहिए।",
    step1: "दस्तावेज़ लिया जाता है, अस्वीकार नहीं",
    step2: "स्कैनर इसे चिह्नित करता है",
    step3: "जो उपकरण माँगा गया वह अस्तित्व में ही नहीं",
    step4: "इसका दावा ज्ञापन तक नहीं पहुँच सकता",
    ingested: "ग्रहण किया",
    detected: "पकड़ा गया",
    structural: "संरचनात्मक",
    refused: "अस्वीकृत",
    flagged: "चिह्नित",
  },
  theme: { light: "उजला", dark: "गहरा" },
};

const ar: Dict = {
  brand: "COUNSEL",
  tagline: "خمسة تفويضات تتجادل. والسجل يبقى بعد الجدال.",
  nav: { room: "القاعة", stages: "المراحل", board: "اللوحة", decide: "القرار", ledger: "السجل", report: "التقرير", crew: "الفريق", documents: "المستندات", ask: "اسأل", security: "الأمن" },
  crew: {
    title: "الفريق",
    lede: "من يجلس إلى الطاولة، وما يعترف كل منهم بأنه يخطئ فيه، وما يستطيع كل منهم فعله بالضبط.",
    values: "على أي أساس يجادل",
    blindSpots: "ما يعترف بأنه يقلل من شأنه",
    evidence: "ما يقبله دليلاً",
    tools: "الأدوات",
    noSideEffects: "بلا آثار جانبية",
    capability: "الصلاحيات",
    capabilityLede: "كامل ادعاء الأمان في جدول واحد. لا أداة في COUNSEL تكتب إلى العالم الخارجي، وهذا مُتحقَّق منه على السجل بأكمله. المنسّق وحده يفتح الجولة أو يغلقها.",
    agent: "العميل",
    sideEffects: "آثار جانبية",
    none: "لا شيء",
    facilitator: "المنسّق",
    auditor: "المدقق",
    chair: "الرئيس (أنت)",
  },
  stages: {
    title: "المراحل",
    lede: "من التعاطف إلى التعلّم، وما يلزم في كل مرحلة. كل قاعدة أدناه إما يفرضها المخطط أو يعلّمها المدقق.",
    here: "أنت هنا",
    produced: "أُنتجت",
    notYet: "لا شيء بعد",
    noArtefact: "لا مخرجات لهذه المرحلة",
  },
  board: {
    title: "اللوحة",
    lede: "الصياغات والأفكار، حسب المقعد. لا ترتيب هنا: تقييم فكرة على اللوحة يُنهي التباعد الذي وُجدت مرحلة التفكير لحمايته.",
    runFramings: "اطلب صياغات",
    runIdeas: "اطلب أفكاراً",
    working: "جارٍ سؤال القاعة",
    framings: "الصياغات",
    framingsLede: "التعريف. كل مقعد يذكر المشكلة التي يراها جديرة بالحل، على هيئة سؤال.",
    ideas: "الأفكار",
    ideasLede: "التفكير التباعدي، تحت قاعدة عدم النقد. ابنِ على أفكار الآخرين بدل استبدالها.",
    whose: "مشكلة من:",
    buildsOn: "يبني على",
    empty: "اللوحة فارغة حتى الآن. اطلب صياغات لبدء مرحلة التعريف، أو أفكاراً لبدء مرحلة التفكير — تجيب المقاعد الخمسة معاً، ويستغرق ذلك نحو عشرين ثانية.",
  },
  report: {
    title: "التقرير",
    lede: "كل ما أنتجته الجلسة، مُجمّعاً للقراءة.",
    question: "القرار",
    rounds: "الجولات",
    record: "السجل",
    sealed: "مختوم",
    broken: "السلسلة مكسورة",
    build: "جمّع التقرير",
    building: "جارٍ التجميع",
    copy: "انسخ المذكرة",
    copied: "نُسخت",
    copyFailed: "الحافظة غير متاحة هنا. حدّد نص المذكرة وانسخه.",
    print: "اطبع",
    exportNote: "لا يرسل COUNSEL هذا إلى أي مكان. لا زر مشاركة ولا خطاف ويب: المذكرة معروضة لتقرأها. تصدير يقوم به البرنامج سيكون أول فعل يقوم به عميل هنا تجاه العالم الخارجي.",
    unanimous: "اعترض كل المقاعد",
    noCalibration: "لا يملك أي مقعد {n} نتائج مسجّلة بعد، فلا شيء هنا يستحق الرسم.",
  },
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
    voiceOn: "امنحهم أصواتاً",
    voiceOff: "أسكت القاعة",
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
    redteamTitle: "الهجوم، مباشرة",
    redteamLede: "أدخل مستنداً مسموماً إلى مجموعة هذه الجلسة وشاهد ما يحدث له. الضابط الذي لا يراه أحد لا يثق به أحد.",
    redteamRun: "شغّل الهجوم",
    redteamNoSession: "افتح قاعة أولاً — يحتاج الهجوم إلى جلسة.",
    step1: "يُقبل المستند ولا يُرفض",
    step2: "يعلّمه الماسح",
    step3: "الأداة التي طلبها غير موجودة أصلاً",
    step4: "لا يمكن لادعائه بلوغ المذكرة",
    ingested: "مُدخل",
    detected: "مكتشف",
    structural: "بنيوي",
    refused: "مرفوض",
    flagged: "مُعلَّم",
  },
  theme: { light: "فاتح", dark: "داكن" },
};

export const DICT: Record<Lang, Dict> = { en, hi, ar };
export type { Dict };
