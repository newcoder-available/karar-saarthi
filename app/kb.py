"""Curated "Fairness Benchmark" knowledge base.

Every risk flag the product raises is anchored to one of these entries, so the
legal reference shown to the user is curated text, never model-invented.
The LLM may add context, but may only cite a `law` string from this file.

Scope: India. Tenancy is a state subject, so tenancy entries describe the
Model Tenancy Act, 2021 as a benchmark and tell the user to check their
state's own law. Last reviewed: Sept 2026.
"""

from __future__ import annotations

from dataclasses import dataclass, field

RENTAL, GIG, JOB = "rental", "gig", "employment"
ANY = (RENTAL, GIG, JOB)

HIGH, MEDIUM, LOW, INFO = "high", "medium", "low", "info"
SEVERITY_ORDER = {HIGH: 0, MEDIUM: 1, LOW: 2, INFO: 3}

MTA = "Model Tenancy Act, 2021 (benchmark; applies only where your state has adopted it — otherwise your state's Rent Control Act applies)"


@dataclass(frozen=True)
class Rule:
    id: str
    types: tuple[str, ...]
    category: str
    title: str
    severity: str
    patterns: tuple[str, ...]
    explain_en: str
    explain_hi: str
    law: str
    ask_lawyer: str
    negotiate: str
    all_of: tuple[str, ...] = field(default_factory=tuple)  # every regex here must also match
    none_of: tuple[str, ...] = field(default_factory=tuple)  # any match here suppresses the flag


RULES: list[Rule] = [
    # ---------------------------------------------------------------- rental
    Rule(
        "R_DEPOSIT_FORFEIT",
        (RENTAL,),
        "deposit",
        "Deposit can be kept (forfeited) or is non-refundable",
        HIGH,
        (r"non[- ]?refundable", r"forfeit", r"shall not be refunded", r"will not be returned"),
        "The landlord can keep your security deposit. A deposit is meant to be returned when you leave, minus only genuine unpaid dues or damage beyond normal wear and tear.",
        "मकान मालिक आपकी सिक्योरिटी डिपॉज़िट रख सकता है। डिपॉज़िट घर छोड़ते समय लौटानी होती है — सिर्फ़ असली बकाया या सामान्य घिसावट से ज़्यादा नुकसान काटा जा सकता है।",
        MTA + " — deposit is refundable at the time of taking back vacant possession, after lawful deductions.",
        "Is a clause letting the landlord forfeit the whole deposit enforceable under my state's rent law?",
        "Ask to replace it with: 'Deposit refundable within 30 days of handover, with a written, itemised list of any deductions.'",
        all_of=(r"deposit|advance",),
    ),
    Rule(
        "R_RENT_HIKE_ANYTIME",
        (RENTAL,),
        "rent_change",
        "Rent can be increased at the landlord's discretion",
        HIGH,
        (
            r"(increase|revise|enhance)\w*\s+(the\s+)?rent\s+(at\s+any\s+time|at\s+(his|her|its|their)\s+(sole\s+)?discretion|as\s+(he|she|they)\s+deem)",
            r"rent\s+(may|shall|can)\s+be\s+(increased|revised|enhanced)\s+(at\s+any\s+time|at\s+the\s+(sole\s+)?discretion)",
        ),
        "The rent can go up whenever the landlord decides. Normally the increase amount and timing are fixed in the agreement.",
        "मकान मालिक जब चाहे किराया बढ़ा सकता है। आम तौर पर किराया कितना और कब बढ़ेगा, यह एग्रीमेंट में पहले से तय होता है।",
        MTA + " — rent is revised as per the agreement, and otherwise only with at least three months' written notice.",
        "Can the landlord raise rent mid-term if the agreement lets him do it 'at any time'?",
        "Ask for a fixed yearly escalation (e.g. 5%) that applies only on renewal, with 3 months' written notice.",
    ),
    Rule(
        "R_ENTRY_NO_NOTICE",
        (RENTAL,),
        "entry",
        "Landlord can enter without prior notice",
        MEDIUM,
        (r"enter\w*[^.]{0,80}(at\s+any\s+time|without\s+(any\s+)?(prior\s+)?notice)",),
        "The landlord can come into your home at any time. Fair agreements require advance notice and reasonable hours, except in emergencies.",
        "मकान मालिक कभी भी घर में आ सकता है। सही एग्रीमेंट में आपातकाल छोड़कर पहले से सूचना और उचित समय ज़रूरी होता है।",
        MTA + " — landlord must give at least 24 hours' written notice before entering, between 7 am and 8 pm.",
        "What notice must my landlord give before entering the flat under my state's law?",
        "Ask to add: 'Entry only after 24 hours' written notice, between 8 am and 8 pm, except in an emergency.'",
    ),
    Rule(
        "R_SELF_HELP_EVICTION",
        (RENTAL,),
        "eviction",
        "Eviction or cutting utilities without due process",
        HIGH,
        (
            r"(disconnect|cut\s*off|stop|withhold)\w*[^.]{0,40}(electricity|water|power|gas|supply)",
            r"(lock|seal)\w*\s+the\s+(premises|flat|house|room)",
            r"remove\w*[^.]{0,40}(belongings|articles|goods)",
            r"vacate\s+(the\s+premises\s+)?(immediately|forthwith)",
        ),
        "The agreement allows the landlord to throw you out, lock the house or cut water/electricity on his own. In India a tenant can generally be evicted only through the legal process, and essential supplies cannot be cut off to force you out.",
        "एग्रीमेंट मकान मालिक को खुद ही आपको निकालने, ताला लगाने या बिजली-पानी काटने की छूट देता है। भारत में किरायेदार को आम तौर पर सिर्फ़ क़ानूनी प्रक्रिया से निकाला जा सकता है, और ज़रूरी सप्लाई काटकर दबाव नहीं डाला जा सकता।",
        MTA
        + " — eviction is through the Rent Court on specified grounds; the landlord may not withhold essential supplies such as water or electricity.",
        "If rent is delayed, can the landlord lock the flat or cut the electricity, or must he go to the Rent Authority/court?",
        "Ask to delete the clause, or replace with: 'Eviction only through the procedure established by law.'",
    ),
    Rule(
        "R_ALL_REPAIRS_TENANT",
        (RENTAL,),
        "maintenance",
        "Tenant pays for all repairs, including structural",
        MEDIUM,
        (
            r"(all|any)\s+(kinds?\s+of\s+)?repairs?[^.]{0,60}(borne|paid|done)\s+by\s+the\s+(tenant|lessee)",
            r"(structural|major)\s+repairs?[^.]{0,60}(tenant|lessee)",
        ),
        "You would pay for every repair, even structural ones like walls, roof or plumbing lines. Usually the owner handles structural repairs and the tenant handles day-to-day upkeep.",
        "आपको हर मरम्मत का खर्च उठाना होगा, दीवार, छत या पाइपलाइन जैसी बड़ी मरम्मत भी। आम तौर पर बड़ी (स्ट्रक्चरल) मरम्मत मालिक और रोज़मर्रा की देखभाल किरायेदार करता है।",
        MTA
        + " — structural repairs, whitewashing and major plumbing are the landlord's responsibility; minor day-to-day repairs are the tenant's.",
        "Who is legally responsible for structural repairs in my state if the agreement puts everything on me?",
        "Ask to split: 'Structural and major repairs by owner; minor day-to-day repairs (bulbs, taps, fuses) by tenant.'",
        none_of=(r"(structural|major)\s+repairs?[^.]{0,60}(owner|landlord|lessor)",),
    ),
    Rule(
        "R_LOCKIN_PENALTY",
        (RENTAL,),
        "lock_in",
        "Lock-in with heavy exit penalty",
        MEDIUM,
        (r"lock[- ]?in",),
        "There is a lock-in period, and leaving early means paying rent for the unused months or losing the deposit. Check the length and whether the same lock-in binds the landlord too.",
        "एग्रीमेंट में लॉक-इन पीरियड है और जल्दी छोड़ने पर बाकी महीनों का किराया या डिपॉज़िट गंवाना पड़ सकता है। देखें कि यह कितना लंबा है और क्या यही शर्त मकान मालिक पर भी लागू है।",
        "Indian Contract Act, 1872, s.74 — a penalty for breach is limited to reasonable compensation, not any sum named in the contract.",
        "Is a lock-in penalty of rent for all remaining months enforceable, or only reasonable compensation?",
        "Ask for a shorter lock-in (e.g. 3–6 months) that applies to both sides, with a one-month-rent exit fee instead.",
        all_of=(r"(remaining|balance|unexpired|entire)\s+(lock|period|term|months)|forfeit|penalt",),
    ),
    Rule(
        "R_PAINTING_DEDUCTION",
        (RENTAL,),
        "deposit",
        "Fixed painting/cleaning charges deducted from deposit",
        LOW,
        (
            r"(painting|cleaning|whitewash)\w*\s+(charges?|cost|expenses?)[^.]{0,80}(deduct|adjust)",
            r"(deduct|adjust)\w*[^.]{0,80}(painting|cleaning|whitewash)",
        ),
        "A fixed amount for painting or cleaning will be cut from your deposit no matter what condition you leave the house in.",
        "घर की हालत कैसी भी हो, पेंटिंग या सफ़ाई का तय पैसा आपकी डिपॉज़िट से काटा जाएगा।",
        "General principle — deductions should reflect actual damage beyond normal wear and tear, backed by receipts.",
        "Can a fixed painting charge be deducted even if I leave the flat in good condition?",
        "Ask to cap it or make it 'actual cost against bills, only for damage beyond normal wear and tear'.",
    ),
    Rule(
        "R_LANDLORD_TERMINATE_NO_REASON",
        (RENTAL,),
        "termination",
        "Landlord can end the tenancy without reason or notice",
        MEDIUM,
        (
            r"(landlord|lessor|owner)[^.]{0,80}terminat\w*[^.]{0,80}(without\s+(assigning\s+)?(any\s+)?(reason|notice|cause)|at\s+any\s+time)",
        ),
        "The landlord can ask you to leave at any time without giving a reason. Check that you get the same notice period the landlord demands from you.",
        "मकान मालिक बिना कारण कभी भी घर खाली करवा सकता है। देखें कि आपको उतना ही नोटिस मिले जितना मालिक आपसे मांगता है।",
        "Transfer of Property Act, 1882, s.106 (default notice rules where the lease is silent) and your state's rent law.",
        "How much notice must my landlord give me to end the tenancy, and can he do so without a reason?",
        "Ask for equal notice on both sides (e.g. one month) and no termination within the first 6 months except for breach.",
    ),
    # ---------------------------------------------------------------- gig
    Rule(
        "G_DEACTIVATE_DISCRETION",
        (GIG,),
        "termination",
        "Account can be deactivated at the platform's sole discretion",
        HIGH,
        (
            r"(deactivat|suspend|terminat|block|off[- ]?board)\w*[^.]{0,120}(sole\s+(and\s+absolute\s+)?discretion|without\s+(any\s+)?(prior\s+)?(notice|reason|cause)|for\s+any\s+reason)",
        ),
        "The platform can switch off your account, and your income, without warning or explanation. There is no right to be heard or to appeal.",
        "प्लेटफ़ॉर्म बिना चेतावनी या कारण बताए आपका अकाउंट (और कमाई) बंद कर सकता है। सुनवाई या अपील का कोई अधिकार नहीं दिया गया है।",
        "Code on Social Security, 2020 (in force 21 Nov 2025) recognises gig and platform workers; some states (e.g. Karnataka, Rajasthan) have their own gig-worker laws with grievance and transparency duties — check your state.",
        "Does my state's gig-worker law require notice, reasons or an appeal before deactivation?",
        "Ask the platform, in writing, for its deactivation policy, the specific reason for any action, and its grievance officer's contact.",
    ),
    Rule(
        "G_UNILATERAL_PAYOUT",
        (GIG,),
        "payment",
        "Payout rates or incentives can change without notice",
        HIGH,
        (
            r"(payout|fee|rate|commission|incentive|earning)s?[^.]{0,80}(change|modif|revis|alter)\w*[^.]{0,80}(at\s+any\s+time|sole\s+discretion|without\s+(prior\s+)?notice)",
            r"(change|modif|revis|alter)\w*[^.]{0,40}(payout|rate\s+card|commission|incentive)[^.]{0,60}(at\s+any\s+time|sole\s+discretion|without\s+(prior\s+)?notice)",
        ),
        "How much you earn per task can be changed at any time without telling you first.",
        "आपको हर काम के कितने पैसे मिलेंगे, यह बिना पहले बताए कभी भी बदला जा सकता है।",
        "Indian Contract Act, 1872 — a change to a core term like price generally needs the other party's consent; check your state's gig-worker law for transparency duties.",
        "Can the platform cut my per-order payout without notice, and what records should I keep to challenge it?",
        "Screenshot the rate card each week and ask for a written commitment to 7 days' notice before any payout change.",
    ),
    Rule(
        "G_DEDUCTIONS_PENALTIES",
        (GIG,),
        "payment",
        "Platform can withhold payments or impose penalties at will",
        HIGH,
        (
            r"(withhold|deduct|recover|set[- ]?off|adjust)\w*[^.]{0,80}(payment|payout|earning|amount|dues)[^.]{0,80}(discretion|any\s+reason|as\s+it\s+deems|without)",
            r"penalt\w*[^.]{0,80}(discretion|as\s+(it|the\s+company)\s+deems|determined\s+by\s+the\s+(company|platform))",
        ),
        "The platform can hold back or cut your earnings, or fine you, based on its own decision.",
        "प्लेटफ़ॉर्म अपनी मर्ज़ी से आपकी कमाई रोक सकता है, काट सकता है या जुर्माना लगा सकता है।",
        "Indian Contract Act, 1872, s.74 — penalties are limited to reasonable compensation for actual loss.",
        "Is a clause letting the platform deduct any amount it decides from my earnings enforceable?",
        "Ask for an itemised statement for every deduction and a 7-day window to dispute it.",
    ),
    Rule(
        "X_NON_COMPETE",
        (GIG, JOB),
        "non_compete",
        "Non-compete after the engagement ends",
        HIGH,
        (
            r"(shall|will)\s+not[^.]{0,120}(compet|work\s+for|join|engage\s+with|associate\s+with|provide\s+services\s+to)[^.]{0,160}(after|following|post|for\s+a\s+period\s+of)[^.]{0,60}(terminat|cessation|end|expiry|leaving|months?|years?)",
            r"non[- ]?compet\w*[^.]{0,120}(after|following|post)[^.]{0,40}(terminat|cessation|end|expiry)",
        ),
        "You would be barred from working for competitors after you leave. In India, restrictions on working after the contract ends are generally not enforceable, though confidentiality duties are.",
        "छोड़ने के बाद आप प्रतियोगी कंपनियों में काम नहीं कर सकते — ऐसी शर्त है। भारत में कॉन्ट्रैक्ट ख़त्म होने के बाद काम पर रोक आम तौर पर लागू नहीं होती, लेकिन गोपनीयता (confidentiality) की शर्तें लागू रहती हैं।",
        "Indian Contract Act, 1872, s.27 — agreements in restraint of trade are void; post-termination non-competes are generally unenforceable (confidentiality and non-solicit terms are treated differently).",
        "Is this post-exit non-compete enforceable against me, and what exactly must I still keep confidential?",
        "Ask to limit it to the period of the engagement, and keep only confidentiality and non-solicitation.",
    ),
    Rule(
        "G_UNLIMITED_INDEMNITY",
        (GIG, JOB),
        "liability",
        "You indemnify the company without any limit",
        MEDIUM,
        (r"indemnif\w*[^.]{0,200}(any\s+and\s+all|all\s+(losses|claims|damages)|without\s+limit)",),
        "You promise to cover all of the company's losses and legal costs linked to your work, with no upper limit, while the company's own liability to you is usually capped.",
        "आप कंपनी के सभी नुकसान और क़ानूनी खर्च भरने का वादा करते हैं, बिना किसी सीमा के — जबकि कंपनी की आपके प्रति ज़िम्मेदारी अक्सर सीमित रखी जाती है।",
        "Indian Contract Act, 1872, ss.124–125 (indemnity) — the scope is what the contract says, so an uncapped clause is a real exposure.",
        "How much could I realistically be liable for under this indemnity clause?",
        "Ask to cap indemnity at fees received in the last 3 months and limit it to your own proven negligence or wilful misconduct.",
    ),
    Rule(
        "G_NO_INSURANCE",
        (GIG,),
        "liability",
        "All accident / injury risk is on you",
        MEDIUM,
        (
            r"(not\s+(be\s+)?(liable|responsible)|no\s+liability)[^.]{0,120}(accident|injur|death|damage\s+to\s+(the\s+)?vehicle)",
            r"(accident|injur)\w*[^.]{0,120}(sole\s+responsibility|own\s+risk|at\s+your\s+risk)",
        ),
        "If you are hurt or have an accident on a job, the platform says it is not responsible.",
        "काम के दौरान चोट या दुर्घटना होने पर प्लेटफ़ॉर्म कहता है कि वह ज़िम्मेदार नहीं है।",
        "Code on Social Security, 2020 — schemes for gig/platform workers (including accident cover) are funded partly by aggregators; register on the e-Shram portal to be eligible.",
        "What accident or insurance cover am I entitled to as a registered platform worker?",
        "Ask the platform for its accident-insurance policy details and how to claim; register on e-Shram.",
    ),
    Rule(
        "G_NOT_EMPLOYEE",
        (GIG,),
        "benefits",
        "You are classified as an independent contractor",
        INFO,
        (r"(independent\s+contractor|not\s+an?\s+employee|no\s+employer[- ]employee|principal\s+to\s+principal)",),
        "You are not treated as an employee, so PF, ESI and gratuity for employees don't apply automatically. Gig and platform workers now have their own social security route.",
        "आपको कर्मचारी नहीं माना गया है, इसलिए कर्मचारियों वाला PF, ESI, ग्रेच्युटी अपने आप लागू नहीं होते। गिग और प्लेटफ़ॉर्म वर्कर्स के लिए अब अलग सामाजिक सुरक्षा व्यवस्था है।",
        "Code on Social Security, 2020 (in force 21 Nov 2025) — gig/platform workers are eligible for notified schemes after registering on e-Shram (eshram.gov.in).",
        "Given I'm classified as a contractor, which social security schemes can I claim and how?",
        "Register on e-Shram with your Aadhaar-linked mobile number and keep your platform ID handy.",
    ),
    Rule(
        "G_DATA_TRACKING",
        (GIG, JOB),
        "data",
        "Broad tracking or sharing of your personal data",
        LOW,
        (
            r"(share|disclose|transfer)\w*[^.]{0,80}(personal\s+data|information)[^.]{0,80}(third\s+part|affiliate|partner)",
            r"(track|monitor)\w*[^.]{0,60}(location|device|activity)[^.]{0,60}(at\s+all\s+times|continuous|even\s+when)",
        ),
        "The company can track you or pass your personal data to others fairly freely.",
        "कंपनी आपको ट्रैक कर सकती है या आपका निजी डेटा दूसरों को काफ़ी खुलकर दे सकती है।",
        "Digital Personal Data Protection Act, 2023 — consent must be specific and informed, and you can ask how your data is used.",
        "What rights do I have to limit tracking or data sharing under the DPDP Act?",
        "Ask which third parties get your data, for what purpose, and how to withdraw consent.",
    ),
    Rule(
        "G_IP_ALL",
        (GIG, JOB),
        "ip",
        "Company takes rights over all your work, including personal or prior work",
        MEDIUM,
        (
            r"(all|any)\s+(intellectual\s+property|work\s+product|inventions?|creations?)[^.]{0,160}(whether\s+or\s+not|outside\s+(working|office)\s+hours|prior|pre[- ]existing|during\s+or\s+after)",
        ),
        "The company claims ownership of everything you create — possibly even side projects or work you did before joining.",
        "कंपनी आपकी बनाई हर चीज़ पर हक़ जताती है — शायद आपके साइड प्रोजेक्ट या पहले के काम पर भी।",
        "Copyright Act, 1957, s.17 and contract terms — ownership follows the agreement, so broad wording matters.",
        "Does this IP clause cover my personal projects or work created before this contract?",
        "Ask to limit it to work created for the company during the engagement, and list your prior work as excluded.",
    ),
    # ---------------------------------------------------------------- employment
    Rule(
        "E_TRAINING_BOND",
        (JOB,),
        "bond",
        "Service bond / training-cost recovery",
        MEDIUM,
        (
            r"(service\s+(bond|agreement)|bond\s+(period|amount)|training\s+(cost|bond|expenses?))[^.]{0,160}(pay|reimburse|liable|recover|compensat)",
            r"(liquidated\s+damages)[^.]{0,120}(leave|resign|exit)",
            r"(leave|resign|exit)\w*[^.]{0,120}(liquidated\s+damages|training\s+cost|bond\s+amount)",
        ),
        "If you leave before a set period, you must pay a fixed amount. Courts usually enforce only a reasonable amount linked to real training costs, not an arbitrary penalty.",
        "तय समय से पहले नौकरी छोड़ने पर आपको एक तय रक़म देनी होगी। अदालतें आम तौर पर सिर्फ़ असली ट्रेनिंग खर्च से जुड़ी उचित रक़म ही मानती हैं, मनमाना जुर्माना नहीं।",
        "Indian Contract Act, 1872, s.74 — only reasonable compensation for actual loss; s.27 — cannot be used to bar you from working elsewhere.",
        "Is this bond amount reasonable compensation or an unenforceable penalty, given the actual training I receive?",
        "Ask for the bond to reduce pro-rata each month you serve, and for the actual training cost to be documented.",
    ),
    Rule(
        "E_ORIGINAL_DOCS",
        (JOB,),
        "documents",
        "Employer keeps your original certificates",
        HIGH,
        (
            r"original\s+(educational\s+)?(certificates?|documents?|mark\s*sheets?|degrees?)[^.]{0,120}(retain|kept|keep|deposit|submit|custody|withh)",
        ),
        "The employer will hold your original certificates. This is widely treated as coercive; courts have ordered employers to return them.",
        "नियोक्ता आपके ओरिजिनल सर्टिफ़िकेट अपने पास रखेगा। इसे आम तौर पर दबाव बनाने का तरीक़ा माना जाता है; अदालतों ने ऐसे सर्टिफ़िकेट लौटाने के आदेश दिए हैं।",
        "General principle — retaining original certificates to prevent resignation is widely viewed as coercive; seek advice if they are withheld.",
        "Can the employer legally keep my original degree certificates until I complete the bond?",
        "Offer self-attested copies and verification instead of originals.",
    ),
    Rule(
        "E_FORFEIT_SALARY",
        (JOB,),
        "notice_period",
        "Salary or full-and-final settlement forfeited on exit",
        MEDIUM,
        (
            r"(forfeit|withh[oe]ld|not\s+be\s+(paid|entitled))\w*[^.]{0,120}(salary|full\s+and\s+final|dues|wages|bonus|gratuity)",
            r"(salary|full\s+and\s+final|dues|wages|bonus)[^.]{0,120}(shall|will)\s+be\s+(forfeited|withheld)",
        ),
        "Money you have already earned can be withheld if you leave without serving full notice. Earned wages generally can't simply be forfeited.",
        "पूरा नोटिस न देने पर आपकी कमाई हुई तनख़्वाह रोकी जा सकती है। कमाया हुआ वेतन आम तौर पर यूं ही ज़ब्त नहीं किया जा सकता।",
        "Code on Wages, 2019 (wage payment and deduction rules) and Indian Contract Act, s.74 — deductions are limited to what the law allows.",
        "Can my employer hold back salary I've already earned if I don't serve the full notice period?",
        "Ask for notice buy-out at basic pay instead of forfeiture of earned salary.",
    ),
    Rule(
        "E_LONG_NOTICE",
        (JOB,),
        "notice_period",
        "Long or one-sided notice period",
        LOW,
        (
            r"(notice\s+period|notice)\s+of\s+(90|120|180|ninety|three|four|six)\s*(\(\d+\)\s*)?(days|months)",
            r"(90|120|180|ninety)\s*(\(\d+\)\s*)?days'?\s+(prior\s+)?(written\s+)?notice",
            r"(three|four|six|3|4|6)\s*(\(\d+\)\s*)?months'?\s+(prior\s+)?(written\s+)?notice",
        ),
        "The notice period is long. Check whether the company must give you the same notice if it lets you go.",
        "नोटिस पीरियड लंबा है। देखें कि क्या कंपनी को भी आपको निकालते समय उतना ही नोटिस देना होगा।",
        "Contract term — check your state's Shops & Establishments Act / standing orders for minimum notice.",
        "Is the notice period the same both ways, and can I buy it out?",
        "Ask for mutual notice and a buy-out option.",
    ),
    # ---------------------------------------------------------------- any document
    Rule(
        "X_UNILATERAL_AMEND",
        ANY,
        "amendment",
        "The other side can change the terms whenever it wants",
        MEDIUM,
        (
            r"(amend|modify|change|update|vary|alter)\w*\s+(these|this|the)\s+(terms|agreement|conditions|policy|policies)[^.]{0,120}(at\s+any\s+time|sole\s+discretion|without\s+(prior\s+)?notice|from\s+time\s+to\s+time)",
            r"(reserves?\s+the\s+right)[^.]{0,60}(amend|modify|change|vary|alter)",
        ),
        "The other party can rewrite the deal later, and continuing to use or stay may count as agreeing.",
        "सामने वाला पक्ष बाद में कभी भी शर्तें बदल सकता है, और आपका काम/रहना जारी रखना सहमति माना जा सकता है।",
        "Indian Contract Act, 1872 — a binding change generally needs agreement by both parties; one-sided change clauses are contestable.",
        "If the terms are changed later without my consent, am I bound by the new terms?",
        "Ask for written notice (e.g. 15–30 days) before any change, and the right to exit without penalty if you don't agree.",
    ),
    Rule(
        "X_BAR_COURTS",
        ANY,
        "dispute",
        "You give up the right to go to court",
        HIGH,
        (
            r"(shall|will)\s+not\s+(approach|move|file|initiate)[^.]{0,60}(any\s+)?(court|forum|authority|police|consumer)",
            r"waive\w*[^.]{0,60}(right|rights)\s+to\s+(sue|approach|file|legal\s+(action|remedy))",
        ),
        "The agreement tries to stop you from going to any court or authority. An absolute bar like this is generally void in India (arbitration clauses are a separate, allowed exception).",
        "एग्रीमेंट आपको किसी भी अदालत या अथॉरिटी में जाने से रोकने की कोशिश करता है। भारत में ऐसी पूरी रोक आम तौर पर अमान्य है (आर्बिट्रेशन क्लॉज़ अलग, मान्य अपवाद है)।",
        "Indian Contract Act, 1872, s.28 — agreements that absolutely restrict legal proceedings are void.",
        "Is the clause stopping me from approaching any court enforceable?",
        "Ask to delete it; keep a neutral dispute clause instead.",
    ),
    Rule(
        "X_ONE_SIDED_ARBITRATION",
        ANY,
        "dispute",
        "The company alone picks the arbitrator",
        MEDIUM,
        (
            r"arbitrat\w*[^.]{0,160}(appointed|nominated|chosen|selected)\s+(solely\s+)?by\s+(the\s+)?(company|landlord|lessor|platform|employer|owner|managing\s+director|first\s+party)",
            r"(company|landlord|platform|employer|managing\s+director)[^.]{0,40}(shall|will|may)\s+(appoint|nominate)[^.]{0,40}(sole\s+)?arbitrator",
        ),
        "Disputes go to an arbitrator picked only by the other side. That is not neutral.",
        "विवाद ऐसे मध्यस्थ (आर्बिट्रेटर) के पास जाएगा जिसे सिर्फ़ सामने वाला पक्ष चुनेगा। यह निष्पक्ष नहीं है।",
        "Arbitration and Conciliation Act, 1996, s.12(5) & Seventh Schedule; Supreme Court Constitution Bench in CORE v. ECI-SPIC-SMO-MCML (2024) held unilateral appointment clauses violate equal treatment of parties.",
        "Can I object to an arbitrator appointed solely by the company, and where would the arbitration take place?",
        "Ask for an arbitrator appointed jointly, or by an independent institution, seated in your city.",
    ),
    Rule(
        "X_AUTO_RENEW",
        ANY,
        "renewal",
        "Automatic renewal",
        LOW,
        (r"(automatically|auto)[- ]?(renew|extend)",),
        "The agreement renews on its own unless you cancel in time. Note the cancellation deadline.",
        "अगर आप समय पर रद्द नहीं करते, तो एग्रीमेंट अपने आप आगे बढ़ जाएगा। रद्द करने की आख़िरी तारीख़ नोट करें।",
        "Contract term — check the cancellation window and any change in price on renewal.",
        "What is my deadline to stop auto-renewal, and do terms change on renewal?",
        "Set a calendar reminder a month before the renewal date.",
    ),
    Rule(
        "X_BLANKS",
        ANY,
        "blanks",
        "Blank spaces left in the document",
        MEDIUM,
        (r"_{4,}|\.{6,}|\[\s*\]|\bxx+\b",),
        "Parts of the document are left blank. Never sign with blanks — they can be filled in later without you.",
        "दस्तावेज़ में कुछ जगहें खाली छोड़ी गई हैं। खाली जगह के साथ कभी साइन न करें — बाद में इन्हें आपके बिना भरा जा सकता है।",
        "General practice — fill or strike through every blank and initial each page before signing.",
        "Which of these blanks must be completed before I sign?",
        "Fill in or strike through every blank, initial each page and keep a signed copy.",
    ),
]

RULES_BY_ID = {r.id: r for r in RULES}

# Numeric / absence checks implemented in engine.py reference these entries.
DEPOSIT_CAP = Rule(
    "R_DEPOSIT_CAP",
    (RENTAL,),
    "deposit",
    "Security deposit above the 2-month benchmark",
    HIGH,
    (),
    "Your deposit is {months} months' rent. The Model Tenancy Act benchmark is at most 2 months for homes. Many states have not adopted it, but it's a strong point for negotiation.",
    "आपकी डिपॉज़िट {months} महीने के किराए के बराबर है। मॉडल टेनेंसी एक्ट का पैमाना घरों के लिए ज़्यादा से ज़्यादा 2 महीने है। कई राज्यों ने इसे लागू नहीं किया है, फिर भी बातचीत में यह मज़बूत आधार है।",
    MTA + " — residential security deposit capped at two months' rent.",
    "Does my state cap the security deposit, and can I recover the excess?",
    "Quote the Model Tenancy Act benchmark and ask to bring the deposit down to 2 months (or 3 as a compromise).",
)

LATE_FEE = Rule(
    "X_HIGH_INTEREST",
    ANY,
    "penalty",
    "Steep late-payment interest",
    MEDIUM,
    (),
    "Late payment attracts {rate}% per month (about {annual}% a year). That is steep; penalties beyond reasonable compensation are contestable.",
    "देर से भुगतान पर हर महीने {rate}% ब्याज (साल का लगभग {annual}%) है। यह काफ़ी ज़्यादा है; उचित मुआवज़े से ज़्यादा जुर्माना चुनौती दी जा सकती है।",
    "Indian Contract Act, 1872, s.74 — only reasonable compensation is recoverable, whatever the contract names.",
    "Is this late-payment interest rate enforceable?",
    "Ask for a grace period of 5–7 days and a flat, modest late fee.",
)

REGISTRATION = Rule(
    "R_REGISTRATION",
    (RENTAL,),
    "registration",
    "Registration and stamp duty",
    INFO,
    (),
    "Leases longer than 11 months generally must be registered; that's why many agreements are 11 months. Stamp duty varies by state. A registered or properly stamped agreement is much stronger evidence if there's a dispute.",
    "11 महीने से लंबे किराया एग्रीमेंट आम तौर पर रजिस्टर कराने होते हैं; इसी वजह से कई एग्रीमेंट 11 महीने के होते हैं। स्टाम्प ड्यूटी हर राज्य में अलग है। विवाद होने पर रजिस्टर्ड या सही स्टाम्प वाला एग्रीमेंट ज़्यादा मज़बूत सबूत होता है।",
    "Registration Act, 1908, s.17 (leases beyond one year compulsorily registrable) and your state's Stamp Act; "
    + MTA
    + " requires reporting tenancies to the Rent Authority.",
    "Should this agreement be registered or stamped in my state, and who pays for it?",
    "Agree in writing who pays stamp duty and registration charges.",
)

# Protections a fair document of each type usually contains. Absence => "missing" flag.
EXPECTED: dict[str, list[dict]] = {
    RENTAL: [
        {
            "id": "M_DEPOSIT_REFUND",
            "label": "When and how the deposit is refunded",
            "hi": "डिपॉज़िट कब और कैसे लौटेगी",
            "pattern": r"(refund|return)\w*[^.]{0,80}(deposit|advance)|(deposit|advance)[^.]{0,120}(refund|return)",
        },
        {
            "id": "M_NOTICE_BOTH",
            "label": "Notice period to end the tenancy",
            "hi": "किराया ख़त्म करने का नोटिस पीरियड",
            "pattern": r"notice",
        },
        {
            "id": "M_MAINTENANCE",
            "label": "Who pays for which repairs",
            "hi": "कौन सी मरम्मत कौन करेगा",
            "pattern": r"repair|maintenance",
        },
        {
            "id": "M_RENT_REVISION",
            "label": "How and when rent can increase",
            "hi": "किराया कब और कितना बढ़ेगा",
            "pattern": r"(increase|escalat|revis|enhance)\w*[^.]{0,40}rent|rent[^.]{0,40}(increase|escalat|revis|enhance)",
        },
        {
            "id": "M_INVENTORY",
            "label": "List of fittings / furniture handed over",
            "hi": "दिए गए सामान/फ़िटिंग की सूची",
            "pattern": r"inventory|fixtures|fittings|furniture|annexure|schedule\s+of",
        },
    ],
    GIG: [
        {
            "id": "M_PAYOUT_FORMULA",
            "label": "How your pay is calculated",
            "hi": "आपकी कमाई कैसे तय होती है",
            "pattern": r"(payout|fee|earning|rate)[^.]{0,80}(calculat|per\s+(order|trip|task|delivery|km)|rate\s+card)",
        },
        {
            "id": "M_GRIEVANCE",
            "label": "Grievance or appeal process",
            "hi": "शिकायत या अपील की प्रक्रिया",
            "pattern": r"grievance|appeal|dispute\s+resolution\s+(team|officer|mechanism)|redress",
        },
        {
            "id": "M_INSURANCE",
            "label": "Accident or health insurance",
            "hi": "दुर्घटना या स्वास्थ्य बीमा",
            "pattern": r"insurance|accident\s+cover|medical\s+cover",
        },
        {
            "id": "M_PAYMENT_TIMING",
            "label": "When you get paid",
            "hi": "पैसा कब मिलेगा",
            "pattern": r"(paid|payment|settle)\w*[^.]{0,60}(weekly|daily|within\s+\d+|every|cycle)",
        },
    ],
    JOB: [
        {
            "id": "M_CTC",
            "label": "Salary break-up (CTC components)",
            "hi": "सैलरी का ब्रेक-अप (CTC)",
            "pattern": r"ctc|basic|annexure|break[- ]?up|components",
        },
        {"id": "M_NOTICE", "label": "Notice period", "hi": "नोटिस पीरियड", "pattern": r"notice"},
        {"id": "M_LEAVE", "label": "Leave entitlement", "hi": "छुट्टियों का हक़", "pattern": r"leave|holiday"},
        {
            "id": "M_HOURS",
            "label": "Working hours",
            "hi": "काम के घंटे",
            "pattern": r"working\s+hours|hours\s+of\s+work|work\s+hours|shift",
        },
    ],
}

# Signals that the user may need a lawyer urgently rather than a document explainer.
URGENT_PATTERNS = [
    r"legal\s+notice",
    r"\bsummons\b",
    r"\bF\.?I\.?R\.?\b",
    r"eviction\s+notice",
    r"notice\s+to\s+(quit|vacate)",
    r"final\s+(notice|warning|reminder)",
    r"within\s+(\d+|seven|fifteen|three|thirty)\s+days\s+(of|from)\s+(the\s+)?(receipt|date\s+of\s+(this|receipt))",
    r"next\s+date\s+of\s+hearing",
    r"hearing\s+on\s+\d",
    r"failing\s+which[^.]{0,80}(legal|court|proceed)",
]

LEGAL_AID = {
    "en": [
        "NALSA free legal aid helpline: 15100 (toll-free).",
        "Your District Legal Services Authority (DLSA) — at the district court complex — gives free advice and, if eligible, a free lawyer.",
        "Tele-Law (via Common Service Centres) connects you to a lawyer by video/phone for free.",
        "Free legal services under the Legal Services Authorities Act, 1987, s.12 cover, among others, women, children, SC/ST members, industrial workmen and people below the notified income limit.",
    ],
    "hi": [
        "NALSA मुफ़्त क़ानूनी सहायता हेल्पलाइन: 15100 (टोल-फ़्री)।",
        "आपका ज़िला विधिक सेवा प्राधिकरण (DLSA) — ज़िला अदालत परिसर में — मुफ़्त सलाह देता है और पात्र होने पर मुफ़्त वकील भी।",
        "टेली-लॉ (कॉमन सर्विस सेंटर के ज़रिए) वीडियो/फ़ोन पर मुफ़्त वकील से जोड़ता है।",
        "विधिक सेवा प्राधिकरण अधिनियम, 1987 की धारा 12 के तहत महिलाएं, बच्चे, SC/ST, औद्योगिक कामगार और तय आय सीमा से कम आय वाले लोग मुफ़्त क़ानूनी सेवा के पात्र हैं।",
    ],
}

DISCLAIMER = {
    "en": "Karaar Saathi gives general legal information to help you understand a document. It is not legal advice and does not create a lawyer–client relationship. Laws differ by state and change; for decisions, speak to a qualified lawyer or free legal aid (NALSA 15100).",
    "hi": "करार साथी दस्तावेज़ समझने के लिए सामान्य क़ानूनी जानकारी देता है। यह क़ानूनी सलाह नहीं है। क़ानून हर राज्य में अलग हैं और बदलते रहते हैं; कोई फ़ैसला लेने से पहले योग्य वकील या मुफ़्त क़ानूनी सहायता (NALSA 15100) से बात करें।",
}
