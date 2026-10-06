import os, sqlite3, hashlib, secrets, json
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Header
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
import nlp
from extract import extract, ExtractError
BASE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.join(BASE, "..", "database", "docuvoice.db"); MAX_MB = 15
app = FastAPI(title="DocuVoice")
def db():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c
with db() as c:
    c.executescript("""CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT,email TEXT UNIQUE,password_hash TEXT);
    CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INT);
    CREATE TABLE IF NOT EXISTS documents(id INTEGER PRIMARY KEY,user_id INT,title TEXT,filename TEXT,text TEXT,analysis TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);""")
def hp(pw, salt=None):
    salt = salt or secrets.token_hex(8); return salt + "$" + hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 120000).hex()
def user(authorization: str = Header(None)):
    r = db().execute("SELECT user_id FROM sessions WHERE token=?", ((authorization or "").replace("Bearer ", ""),)).fetchone()
    if not r: raise HTTPException(401, "Please log in to continue.")
    return r[0]
class Reg(BaseModel): name: str; email: EmailStr; password: str
class Log(BaseModel): email: EmailStr; password: str

@app.post("/api/auth/register")
def register(b: Reg):
    if len(b.password) < 8: raise HTTPException(400, "Password must be at least 8 characters.")
    try:
        with db() as c: c.execute("INSERT INTO users(name,email,password_hash) VALUES(?,?,?)", (b.name.strip(), b.email.lower(), hp(b.password)))
    except sqlite3.IntegrityError: raise HTTPException(400, "An account with this email already exists.")
    return {"ok": True}
@app.post("/api/auth/login")
def login(b: Log):
    r = db().execute("SELECT * FROM users WHERE email=?", (b.email.lower(),)).fetchone()
    if not r or hp(b.password, r["password_hash"].split("$")[0]) != r["password_hash"]: raise HTTPException(401, "Incorrect email or password.")
    t = secrets.token_urlsafe(32)
    with db() as c: c.execute("INSERT INTO sessions VALUES(?,?)", (t, r["id"]))
    return {"token": t, "name": r["name"]}
@app.post("/api/auth/logout")
def logout(authorization: str = Header(None)):
    with db() as c: c.execute("DELETE FROM sessions WHERE token=?", ((authorization or "").replace("Bearer ", ""),))
    return {"ok": True}

@app.post("/api/documents")
async def create(title: str = Form(""), text: str = Form(""), file: UploadFile | None = File(None), uid: int = Depends(user)):
    fn = "pasted text"
    if not text.strip():
        if not file: raise HTTPException(400, "Upload a document or paste some text.")
        data = await file.read(); fn = file.filename or "document"
        if not data: raise HTTPException(400, "The file is empty.")
        if len(data) > MAX_MB * 1048576: raise HTTPException(400, f"File is too large (max {MAX_MB} MB).")
        try: text = extract(fn, data)
        except ExtractError as e: raise HTTPException(400, str(e))
    text = text.replace("\r", "").strip()
    if len(text.split()) < 30: raise HTTPException(400, "The document has too little text to analyze (30+ words needed).")
    a = nlp.analyze(text)
    with db() as c:
        did = c.execute("INSERT INTO documents(user_id,title,filename,text,analysis) VALUES(?,?,?,?,?)", (uid, (title or os.path.splitext(fn)[0])[:200], fn, text, json.dumps(a))).lastrowid
    return {"id": did}
@app.get("/api/documents")
def lst(uid: int = Depends(user)):
    return [{"id": r["id"], "title": r["title"], "filename": r["filename"], "created_at": r["created_at"], **{k: json.loads(r["analysis"])[k] for k in ("type", "words")}} for r in db().execute("SELECT * FROM documents WHERE user_id=? ORDER BY id DESC", (uid,))]
@app.get("/api/documents/{did}")
def get(did: int, uid: int = Depends(user)):
    r = db().execute("SELECT * FROM documents WHERE id=? AND user_id=?", (did, uid)).fetchone()
    if not r: raise HTTPException(404, "Document not found.")
    return {"id": did, "title": r["title"], "filename": r["filename"], "text": r["text"], "analysis": json.loads(r["analysis"])}
@app.delete("/api/documents/{did}")
def delete(did: int, uid: int = Depends(user)):
    with db() as c: c.execute("DELETE FROM documents WHERE id=? AND user_id=?", (did, uid))
    return {"ok": True}
app.mount("/", StaticFiles(directory=os.path.join(BASE, "..", "frontend"), html=True))
