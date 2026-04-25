from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from typing import Optional
import os, base64, uuid, shutil

# ─── CONFIG ───────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://acordo_user:acordo_pass@localhost:5432/acordo_iphone")
PIN_USUARIO  = os.getenv("PIN_USUARIO", "1234")   # seu PIN de acesso completo
PIN_PATRON   = os.getenv("PIN_PATRON",  "5678")   # PIN do patrão (só visualização)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ─── DB ───────────────────────────────────────────────────────
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Registro(Base):
    __tablename__ = "registros"
    id          = Column(Integer, primary_key=True, index=True)
    tipo        = Column(String(20))       # 'sabado' ou 'feriado'
    nome        = Column(String(200))
    data        = Column(String(12))       # DD/MM/AAAA
    entrada     = Column(String(10))
    saida       = Column(String(10), nullable=True)
    valor       = Column(Float)
    lat         = Column(Float, nullable=True)
    lng         = Column(Float, nullable=True)
    obs         = Column(Text, nullable=True)
    foto_in     = Column(String(300), nullable=True)   # path do arquivo
    foto_out    = Column(String(300), nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# Inserir registro inicial do Tiradentes se banco estiver vazio
def init_db():
    db = SessionLocal()
    try:
        if db.query(Registro).count() == 0:
            r = Registro(
                tipo="feriado", nome="Tiradentes · Primeiro Pagamento",
                data="21/04/2026", entrada="08:00", saida="18:00",
                valor=150, obs="Primeiro dia"
            )
            r2 = Registro(
                tipo="sabado", nome="Sábado trabalhado",
                data="25/04/2026", entrada="08:00", saida="18:00",
                valor=150, obs=""
            )
            db.add(r); db.add(r2); db.commit()
    finally:
        db.close()

init_db()

# ─── APP ──────────────────────────────────────────────────────
app = FastAPI(title="Acordo iPhone")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verificar_pin(pin: str):
    if pin == PIN_USUARIO:
        return "usuario"
    if pin == PIN_PATRON:
        return "patron"
    raise HTTPException(status_code=401, detail="PIN inválido")

# ─── ROTAS ────────────────────────────────────────────────────

@app.post("/api/login")
def login(data: dict):
    pin = data.get("pin","")
    role = verificar_pin(pin)
    return {"role": role, "ok": True}

@app.get("/api/registros")
def listar(pin: str, db: Session = Depends(get_db)):
    verificar_pin(pin)
    regs = db.query(Registro).order_by(Registro.id).all()
    return [reg_to_dict(r) for r in regs]

@app.post("/api/registros")
def criar(data: dict, db: Session = Depends(get_db)):
    verificar_pin(data.get("pin",""))
    r = Registro(
        tipo=data["tipo"], nome=data["nome"], data=data["data"],
        entrada=data.get("entrada"), saida=data.get("saida"),
        valor=data["valor"], lat=data.get("lat"), lng=data.get("lng"),
        obs=data.get("obs","")
    )
    db.add(r); db.commit(); db.refresh(r)
    return reg_to_dict(r)

@app.patch("/api/registros/{reg_id}/saida")
def registrar_saida(reg_id: int, data: dict, db: Session = Depends(get_db)):
    verificar_pin(data.get("pin",""))
    r = db.query(Registro).filter(Registro.id == reg_id).first()
    if not r: raise HTTPException(404, "Registro não encontrado")
    r.saida = data.get("saida")
    db.commit(); db.refresh(r)
    return reg_to_dict(r)

@app.post("/api/registros/{reg_id}/foto")
async def upload_foto(
    reg_id: int,
    tipo: str = Form(...),       # 'in' ou 'out'
    pin: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    verificar_pin(pin)
    r = db.query(Registro).filter(Registro.id == reg_id).first()
    if not r: raise HTTPException(404, "Registro não encontrado")

    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    fname = f"{reg_id}_{tipo}_{uuid.uuid4().hex[:8]}.{ext}"
    fpath = os.path.join(UPLOAD_DIR, fname)
    with open(fpath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    if tipo == "in":
        r.foto_in = fname
    else:
        r.foto_out = fname
    db.commit()
    return {"foto": fname, "url": f"/uploads/{fname}"}

@app.delete("/api/registros/{reg_id}")
def deletar(reg_id: int, pin: str, db: Session = Depends(get_db)):
    role = verificar_pin(pin)
    if role != "usuario":
        raise HTTPException(403, "Sem permissão")
    r = db.query(Registro).filter(Registro.id == reg_id).first()
    if not r: raise HTTPException(404)
    db.delete(r); db.commit()
    return {"ok": True}

def reg_to_dict(r: Registro):
    return {
        "id": r.id, "tipo": r.tipo, "nome": r.nome, "data": r.data,
        "entrada": r.entrada, "saida": r.saida, "valor": r.valor,
        "lat": r.lat, "lng": r.lng, "obs": r.obs,
        "foto_in":  f"/uploads/{r.foto_in}"  if r.foto_in  else None,
        "foto_out": f"/uploads/{r.foto_out}" if r.foto_out else None,
        "created_at": r.created_at.isoformat() if r.created_at else None
    }

# Servir uploads e frontend
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/", StaticFiles(directory="static", html=True), name="static")
