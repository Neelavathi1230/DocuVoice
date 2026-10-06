"""Text extraction from TXT / DOCX (stdlib only) / PDF (pypdf)."""
import io, re, zipfile
from xml.etree import ElementTree as ET
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
class ExtractError(Exception): pass
def from_docx(data):
    try:
        root = ET.fromstring(zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml"))
    except Exception: raise ExtractError("This DOCX file could not be read. It may be corrupted.")
    out = []
    for p in root.iter(W + "p"):
        t = "".join(x.text or "" for x in p.iter(W + "t")); st = p.find(f"{W}pPr/{W}pStyle")
        if t.strip(): out.append(("# " if st is not None and st.get(W + "val", "").lower().startswith(("heading", "title")) else "") + t)
    return "\n".join(out)
def from_pdf(data):
    try: from pypdf import PdfReader
    except ImportError: raise ExtractError("PDF support needs the pypdf package. Run: pip install pypdf")
    try: txt = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
    except Exception: raise ExtractError("This PDF could not be read. It may be encrypted or damaged.")
    if not txt.strip(): raise ExtractError("No text found. This PDF may be a scanned image (OCR is not included).")
    return txt
def extract(name, data):
    ext = name.lower().rsplit(".", 1)[-1] if "." in name else ""
    if ext == "txt" or ext == "md": return data.decode("utf-8", "ignore")
    if ext == "docx": return from_docx(data)
    if ext == "pdf": return from_pdf(data)
    raise ExtractError("Unsupported file type. Please upload a TXT, MD, DOCX or PDF file.")
