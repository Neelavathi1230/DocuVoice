"""Document analysis: summary, keywords, key information, structure, readability (local, replaceable)."""
import re, math
from collections import Counter
STOP = set("a an the and or but if of to in on at for with by from as is are was were be been it its this that these those i we you they he she our your their there so than then not no do does did have has had will would can could should may might about into also just very more some such what which who how when where why shall must".split())
def sents(t): return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n{2,}|\n(?=#)", t) if len(s.split()) >= 4]
def toks(t): return [w for w in re.findall(r"[a-z][a-z'-]+", t.lower()) if w not in STOP and len(w) > 2]
def keywords(t, n=12):
    k = toks(t); c = Counter(k); c.update({f"{a} {b}": v * 1.8 for (a, b), v in Counter(zip(k, k[1:])).items() if v >= 2})
    return [w for w, _ in c.most_common(n)]
def summary(t, k):
    ss = sents(t)
    if len(ss) <= k: return " ".join(ss)
    kw = Counter(toks(t)); sc = []
    for i, s in enumerate(ss):
        w = toks(s); sc.append((sum(kw[x] for x in w) / math.sqrt(len(w) or 1) * (1.4 if i < 2 else 1), i))
    return " ".join(ss[i] for _, i in sorted(sorted(sc, reverse=True)[:k], key=lambda x: x[1]))
def key_info(t):
    f = lambda p, fl=0: list(dict.fromkeys(m.group(0).strip() for m in re.finditer(p, t, fl)))[:8]
    return {"dates": f(r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.? \d{1,2}(?:st|nd|rd|th)?,? \d{4}|\d{1,2}(?:st|nd|rd|th)? (?:of )?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*,? \d{4})\b"),
            "amounts": f(r"(?:[$€£₹]|Rs\.?\s?)\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:million|billion|lakh|crore|k))?|\b\d+(?:\.\d+)?\s?%"),
            "emails": f(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "phones": [p for p in f(r"(?<![\d,.$])\+?\d[\d ()-]{8,16}\d(?![\d%])") if 10 <= len(re.sub(r"\D", "", p)) <= 13], "urls": f(r"https?://[^\s)>\"]+"),
            "names": [n for n, _ in Counter(m.group(1) for m in re.finditer(r"(?<![.!?]\s)(?<!^)\b([A-Z][a-z]+(?: [A-Z][a-z]+){1,3})\b", t)).most_common(8)]}
def outline(t):
    h = [l.lstrip("# ").strip() for l in t.splitlines() if l.startswith("#")]
    h += [l.strip() for l in t.splitlines() if 2 <= len(l.split()) <= 8 and not l.rstrip().endswith((".", ",", ";", ":")) and (l.isupper() or re.match(r"^(\d+(\.\d+)*[.)]?\s+|(chapter|section|part)\s+\w+)", l.strip(), re.I))]
    return list(dict.fromkeys(h))[:15]
def doc_type(t):
    low = t.lower(); sc = {"Contract / legal": len(re.findall(r"\b(agreement|party|parties|hereby|liability|clause|terms|governing law)\b", low)), "Invoice / financial": len(re.findall(r"\b(invoice|total|payment|amount due|tax|balance|receipt)\b", low)),
          "Academic / research": len(re.findall(r"\b(abstract|methodology|results|conclusion|references|study|hypothesis)\b", low)), "Resume / CV": len(re.findall(r"\b(experience|education|skills|objective|certification)\b", low)),
          "Report / business": len(re.findall(r"\b(report|quarter|revenue|strategy|stakeholders|recommend)\b", low))}
    k, v = max(sc.items(), key=lambda x: x[1]); return k if v >= 3 else "General document"
def readability(t):
    ss, w = sents(t), re.findall(r"[A-Za-z']+", t)
    if not ss or not w: return {"score": 0, "level": "n/a"}
    syl = sum(max(1, len(re.findall(r"[aeiouy]+", x.lower()))) for x in w); f = round(max(0, min(100, 206.835 - 1.015 * len(w) / len(ss) - 84.6 * syl / len(w))))
    return {"score": f, "level": "Easy" if f >= 70 else "Standard" if f >= 50 else "Difficult"}
def analyze(t):
    w = len(t.split())
    return {"summary_short": summary(t, 2), "summary_medium": summary(t, 5), "summary_long": summary(t, 9), "keywords": keywords(t), "key_info": key_info(t), "outline": outline(t),
            "type": doc_type(t), "readability": readability(t), "words": w, "sentences": len(sents(t)), "read_minutes": max(1, round(w / 200)), "listen_minutes": max(1, round(w / 150))}
