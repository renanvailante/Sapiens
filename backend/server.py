from dotenv import load_dotenv
from pathlib import Path
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
import uuid

import bcrypt
import jwt
from bson import ObjectId
from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, Body
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
import io
import csv

# --- Setup ---
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

app = FastAPI(title="Sapiens Dashboard API")
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("sapiens")


# --- Auth helpers ---
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email,
               "exp": datetime.now(timezone.utc) + timedelta(minutes=60),
               "type": "access"}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {"sub": user_id,
               "exp": datetime.now(timezone.utc) + timedelta(days=7),
               "type": "refresh"}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    response.set_cookie(key="access_token", value=access, httponly=True,
                        secure=True, samesite="none", max_age=3600, path="/")
    response.set_cookie(key="refresh_token", value=refresh, httponly=True,
                        secure=True, samesite="none", max_age=604800, path="/")


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Token inválido")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="Usuário não encontrado")
        user["id"] = str(user["_id"])
        user.pop("_id", None)
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")


# --- Auth models ---
class RegisterInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str


class LoginInput(BaseModel):
    email: EmailStr
    password: str


# --- Auth endpoints ---
@api_router.post("/auth/register")
async def register(body: RegisterInput, response: Response):
    email = body.email.strip().lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    doc = {
        "email": email,
        "password_hash": hash_password(body.password),
        "name": body.name.strip(),
        "role": "teacher",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db.users.insert_one(doc)
    user_id = str(result.inserted_id)
    access = create_access_token(user_id, email)
    refresh = create_refresh_token(user_id)
    set_auth_cookies(response, access, refresh)
    return {"id": user_id, "email": email, "name": body.name, "role": "teacher"}


@api_router.post("/auth/login")
async def login(body: LoginInput, response: Response):
    email = body.email.strip().lower()
    password = body.password.strip()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    user_id = str(user["_id"])
    access = create_access_token(user_id, email)
    refresh = create_refresh_token(user_id)
    set_auth_cookies(response, access, refresh)
    return {"id": user_id, "email": email, "name": user.get("name", ""), "role": user.get("role", "teacher")}


@api_router.post("/auth/logout")
async def logout(response: Response):
    response.set_cookie(key="access_token", value="", httponly=True,
                        secure=True, samesite="none", max_age=0, path="/")
    response.set_cookie(key="refresh_token", value="", httponly=True,
                        secure=True, samesite="none", max_age=0, path="/")
    return {"ok": True}


@api_router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user


# --- Import model (data snapshots from Sapiens ecosystem) ---
class ErroPorNo(BaseModel):
    no_id: Optional[str] = None
    no_label: Optional[str] = None
    taxa_erro: Optional[float] = None
    num_questoes: Optional[int] = None
    disciplina: Optional[str] = None


class AlunoData(BaseModel):
    aluno_id: str
    nome: Optional[str] = None
    erros_por_no: List[ErroPorNo] = []


class ImportInput(BaseModel):
    turma: str
    periodo: str
    versao_taxonomia: str
    data_processamento: Optional[str] = None
    modelo_analise: Optional[str] = None
    ano_escolar: Optional[str] = None
    banca: Optional[str] = None
    prova: Optional[str] = None
    alunos: List[AlunoData]


# --- Data ingestion ---
@api_router.post("/imports")
async def create_import(body: ImportInput, user: dict = Depends(get_current_user)):
    doc = body.model_dump()
    doc["_ingested_at"] = datetime.now(timezone.utc).isoformat()
    doc["_ingested_by"] = user["email"]
    doc["import_id"] = str(uuid.uuid4())
    await db.imports.insert_one(doc)
    return {"import_id": doc["import_id"], "turma": doc["turma"], "periodo": doc["periodo"]}


@api_router.get("/imports")
async def list_imports(user: dict = Depends(get_current_user)):
    cursor = db.imports.find({}, {"_id": 0, "alunos": 0}).sort("_ingested_at", -1)
    docs = await cursor.to_list(500)
    return docs


@api_router.delete("/imports/{import_id}")
async def delete_import(import_id: str, user: dict = Depends(get_current_user)):
    r = await db.imports.delete_one({"import_id": import_id})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Import não encontrado")
    return {"ok": True}


# --- Filters ---
@api_router.get("/filters")
async def get_filters(user: dict = Depends(get_current_user)):
    imports = await db.imports.find({}, {"_id": 0}).to_list(1000)
    turmas = sorted({i.get("turma") for i in imports if i.get("turma")})
    periodos = sorted({i.get("periodo") for i in imports if i.get("periodo")})
    anos = sorted({i.get("ano_escolar") for i in imports if i.get("ano_escolar")})
    bancas = sorted({i.get("banca") for i in imports if i.get("banca")})
    provas = sorted({i.get("prova") for i in imports if i.get("prova")})
    versoes = sorted({i.get("versao_taxonomia") for i in imports if i.get("versao_taxonomia")})
    disciplinas = set()
    for imp in imports:
        for aluno in imp.get("alunos", []):
            for no in aluno.get("erros_por_no", []):
                if no.get("disciplina"):
                    disciplinas.add(no["disciplina"])
    return {
        "turmas": turmas,
        "periodos": periodos,
        "anos_escolares": anos,
        "bancas": bancas,
        "provas": provas,
        "disciplinas": sorted(disciplinas),
        "versoes_taxonomia": versoes,
    }


# --- Helpers to fetch filtered imports ---
async def fetch_imports(turma: Optional[str] = None,
                       periodo: Optional[str] = None,
                       ano: Optional[str] = None,
                       banca: Optional[str] = None,
                       prova: Optional[str] = None) -> List[dict]:
    query: Dict[str, Any] = {}
    if turma: query["turma"] = turma
    if periodo: query["periodo"] = periodo
    if ano: query["ano_escolar"] = ano
    if banca: query["banca"] = banca
    if prova: query["prova"] = prova
    return await db.imports.find(query, {"_id": 0}).to_list(1000)


def filter_disciplina(alunos: List[dict], disciplina: Optional[str]) -> List[dict]:
    if not disciplina:
        return alunos
    out = []
    for a in alunos:
        nos = [n for n in a.get("erros_por_no", []) if n.get("disciplina") == disciplina]
        out.append({**a, "erros_por_no": nos})
    return out


# --- Turma view: matrix aluno x nó ---
@api_router.get("/views/turma")
async def view_turma(turma: str, periodo: str,
                     disciplina: Optional[str] = None,
                     user: dict = Depends(get_current_user)):
    imports = await fetch_imports(turma=turma, periodo=periodo)
    if not imports:
        raise HTTPException(status_code=404, detail="Sem dado para os filtros informados")
    imp = imports[0]
    alunos = filter_disciplina(imp.get("alunos", []), disciplina)

    # Collect all unique nós
    nos_map: Dict[str, dict] = {}
    for a in alunos:
        for n in a.get("erros_por_no", []):
            nid = n.get("no_id")
            if nid and nid not in nos_map:
                nos_map[nid] = {"no_id": nid, "no_label": n.get("no_label"),
                                "disciplina": n.get("disciplina")}
    nos_list = sorted(nos_map.values(), key=lambda x: (x.get("disciplina") or "", x.get("no_label") or ""))

    # Build matrix: for each aluno, taxa_erro per nó
    rows = []
    total_questoes = 0
    for a in alunos:
        cell = {n["no_id"]: None for n in nos_list}
        for n in a.get("erros_por_no", []):
            if n.get("no_id") in cell:
                cell[n["no_id"]] = {
                    "taxa_erro": n.get("taxa_erro"),
                    "num_questoes": n.get("num_questoes"),
                }
                total_questoes += n.get("num_questoes") or 0
        rows.append({"aluno_id": a.get("aluno_id"), "nome": a.get("nome"), "cells": cell})

    return {
        "turma": imp.get("turma"),
        "periodo": imp.get("periodo"),
        "versao_taxonomia": imp.get("versao_taxonomia"),
        "data_processamento": imp.get("data_processamento"),
        "modelo_analise": imp.get("modelo_analise"),
        "total_alunos": len(alunos),
        "total_questoes": total_questoes,
        "nos": nos_list,
        "rows": rows,
    }


# --- Processo cognitivo view ---
@api_router.get("/views/processo")
async def view_processo(turma: str, periodo: str, no_id: str,
                        user: dict = Depends(get_current_user)):
    imports = await fetch_imports(turma=turma, periodo=periodo)
    if not imports:
        raise HTTPException(status_code=404, detail="Sem dado")
    imp = imports[0]
    alunos_data = []
    taxas = []
    label = None
    disciplinas = set()
    total_q = 0
    for a in imp.get("alunos", []):
        for n in a.get("erros_por_no", []):
            if n.get("no_id") == no_id:
                label = label or n.get("no_label")
                if n.get("disciplina"): disciplinas.add(n["disciplina"])
                taxa = n.get("taxa_erro")
                alunos_data.append({
                    "aluno_id": a.get("aluno_id"),
                    "nome": a.get("nome"),
                    "taxa_erro": taxa,
                    "num_questoes": n.get("num_questoes"),
                })
                if taxa is not None: taxas.append(taxa)
                total_q += n.get("num_questoes") or 0
    media = round(sum(taxas) / len(taxas), 4) if taxas else None
    # Bins for distribution
    bins = {"0-20%": 0, "20-40%": 0, "40-60%": 0, "60-80%": 0, "80-100%": 0, "Sem dado": 0}
    for a in alunos_data:
        t = a["taxa_erro"]
        if t is None: bins["Sem dado"] += 1
        elif t < 0.2: bins["0-20%"] += 1
        elif t < 0.4: bins["20-40%"] += 1
        elif t < 0.6: bins["40-60%"] += 1
        elif t < 0.8: bins["60-80%"] += 1
        else: bins["80-100%"] += 1
    return {
        "no_id": no_id,
        "no_label": label,
        "disciplinas": sorted(disciplinas),
        "versao_taxonomia": imp.get("versao_taxonomia"),
        "turma": imp.get("turma"),
        "periodo": imp.get("periodo"),
        "media_taxa_erro": media,
        "total_alunos": len(alunos_data),
        "total_questoes": total_q,
        "distribuicao": [{"faixa": k, "alunos": v} for k, v in bins.items()],
        "alunos": alunos_data,
    }


# --- Aluno view (compared to turma average) ---
@api_router.get("/views/aluno")
async def view_aluno(turma: str, periodo: str, aluno_id: str,
                     disciplina: Optional[str] = None,
                     user: dict = Depends(get_current_user)):
    imports = await fetch_imports(turma=turma, periodo=periodo)
    if not imports:
        raise HTTPException(status_code=404, detail="Sem dado")
    imp = imports[0]
    alunos = filter_disciplina(imp.get("alunos", []), disciplina)
    aluno = next((a for a in alunos if a.get("aluno_id") == aluno_id), None)
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    # Compute turma average per nó
    per_no: Dict[str, List[float]] = {}
    labels: Dict[str, str] = {}
    disciplinas: Dict[str, str] = {}
    for a in alunos:
        for n in a.get("erros_por_no", []):
            nid = n.get("no_id")
            if not nid: continue
            labels[nid] = n.get("no_label")
            disciplinas[nid] = n.get("disciplina")
            if n.get("taxa_erro") is not None:
                per_no.setdefault(nid, []).append(n["taxa_erro"])
    media_turma = {nid: round(sum(v) / len(v), 4) for nid, v in per_no.items()}

    rows = []
    for n in aluno.get("erros_por_no", []):
        nid = n.get("no_id")
        rows.append({
            "no_id": nid,
            "no_label": n.get("no_label") or labels.get(nid),
            "disciplina": n.get("disciplina") or disciplinas.get(nid),
            "taxa_erro_aluno": n.get("taxa_erro"),
            "media_turma": media_turma.get(nid),
            "num_questoes": n.get("num_questoes"),
        })
    rows.sort(key=lambda r: (r["disciplina"] or "", r["no_label"] or ""))
    return {
        "aluno_id": aluno.get("aluno_id"),
        "nome": aluno.get("nome"),
        "turma": imp.get("turma"),
        "periodo": imp.get("periodo"),
        "versao_taxonomia": imp.get("versao_taxonomia"),
        "rows": rows,
    }


@api_router.get("/views/alunos")
async def list_alunos(turma: str, periodo: str, user: dict = Depends(get_current_user)):
    imports = await fetch_imports(turma=turma, periodo=periodo)
    if not imports:
        return {"alunos": []}
    imp = imports[0]
    return {"alunos": [{"aluno_id": a.get("aluno_id"), "nome": a.get("nome")}
                       for a in imp.get("alunos", [])]}


# --- Evolução temporal ---
@api_router.get("/views/evolucao")
async def view_evolucao(turma: str,
                        no_id: Optional[str] = None,
                        aluno_id: Optional[str] = None,
                        disciplina: Optional[str] = None,
                        user: dict = Depends(get_current_user)):
    imports = await fetch_imports(turma=turma)
    imports.sort(key=lambda i: i.get("periodo") or "")
    versoes_encontradas = sorted({i.get("versao_taxonomia") for i in imports if i.get("versao_taxonomia")})
    series = []
    for imp in imports:
        alunos = imp.get("alunos", [])
        if aluno_id:
            alunos = [a for a in alunos if a.get("aluno_id") == aluno_id]
        # Aggregate taxa_erro
        taxas = []
        total_q = 0
        for a in alunos:
            for n in a.get("erros_por_no", []):
                if no_id and n.get("no_id") != no_id: continue
                if disciplina and n.get("disciplina") != disciplina: continue
                if n.get("taxa_erro") is not None:
                    taxas.append(n["taxa_erro"])
                total_q += n.get("num_questoes") or 0
        media = round(sum(taxas) / len(taxas), 4) if taxas else None
        series.append({
            "periodo": imp.get("periodo"),
            "versao_taxonomia": imp.get("versao_taxonomia"),
            "media_taxa_erro": media,
            "num_alunos": len(alunos),
            "num_questoes": total_q,
        })
    return {
        "turma": turma,
        "no_id": no_id,
        "aluno_id": aluno_id,
        "disciplina": disciplina,
        "series": series,
        "versoes_multiplas": len(versoes_encontradas) > 1,
        "versoes_encontradas": versoes_encontradas,
    }


# --- Taxonomia tree ---
@api_router.get("/taxonomia")
async def taxonomia(versao: Optional[str] = None, user: dict = Depends(get_current_user)):
    q = {"versao_taxonomia": versao} if versao else {}
    imports = await db.imports.find(q, {"_id": 0}).to_list(1000)
    versoes_disponiveis = sorted({i.get("versao_taxonomia") for i in imports if i.get("versao_taxonomia")})
    # Build tree: disciplina -> nó
    tree: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for imp in imports:
        for a in imp.get("alunos", []):
            aluno_id = a.get("aluno_id")
            for n in a.get("erros_por_no", []):
                disc = n.get("disciplina") or "Sem disciplina"
                nid = n.get("no_id")
                if not nid: continue
                label = n.get("no_label") or nid
                d = tree.setdefault(disc, {})
                node = d.setdefault(nid, {"no_id": nid, "no_label": label,
                                          "num_questoes": 0, "alunos_ids": set()})
                node["num_questoes"] += n.get("num_questoes") or 0
                if aluno_id: node["alunos_ids"].add(aluno_id)
    result = []
    for disc, nodes in sorted(tree.items()):
        children = []
        for nid, node in sorted(nodes.items(), key=lambda x: x[1]["no_label"]):
            children.append({
                "no_id": node["no_id"],
                "no_label": node["no_label"],
                "num_questoes": node["num_questoes"],
                "num_alunos": len(node["alunos_ids"]),
            })
        result.append({"disciplina": disc, "nos": children})
    return {"versao_selecionada": versao, "versoes_disponiveis": versoes_disponiveis, "arvore": result}


# --- CSV export helpers ---
def csv_response(rows: List[List[Any]], filename: str) -> StreamingResponse:
    buf = io.StringIO()
    w = csv.writer(buf)
    for r in rows:
        w.writerow(["" if v is None else v for v in r])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@api_router.get("/export/turma.csv")
async def export_turma_csv(turma: str, periodo: str, disciplina: Optional[str] = None,
                           user: dict = Depends(get_current_user)):
    data = await view_turma(turma=turma, periodo=periodo, disciplina=disciplina, user=user)
    headers = ["aluno_id", "nome"] + [f'{n["no_label"]} (taxa_erro)' for n in data["nos"]]
    rows = [headers]
    for r in data["rows"]:
        row = [r["aluno_id"], r["nome"]]
        for n in data["nos"]:
            cell = r["cells"].get(n["no_id"])
            row.append(cell["taxa_erro"] if cell else "Sem dado")
        rows.append(row)
    return csv_response(rows, f"turma_{turma}_{periodo}.csv")


# --- Seed sample data ---
SAMPLE_NOS = [
    {"no_id": "MAT.NUM.01", "no_label": "Interpretação de números racionais", "disciplina": "Matemática"},
    {"no_id": "MAT.ALG.01", "no_label": "Resolução de equações do 1º grau", "disciplina": "Matemática"},
    {"no_id": "MAT.GEO.01", "no_label": "Áreas de figuras planas", "disciplina": "Matemática"},
    {"no_id": "POR.INT.01", "no_label": "Inferência textual", "disciplina": "Português"},
    {"no_id": "POR.GRA.01", "no_label": "Concordância verbal", "disciplina": "Português"},
    {"no_id": "CIE.BIO.01", "no_label": "Cadeias alimentares", "disciplina": "Ciências"},
    {"no_id": "CIE.FIS.01", "no_label": "Leis de Newton", "disciplina": "Ciências"},
]

SAMPLE_ALUNOS = [
    ("A001", "Ana Silva"), ("A002", "Bruno Costa"), ("A003", "Camila Souza"),
    ("A004", "Diego Almeida"), ("A005", "Elisa Rocha"), ("A006", "Felipe Lima"),
    ("A007", "Gabriela Nunes"), ("A008", "Henrique Dias"),
]


async def seed_sample_data():
    import random
    random.seed(42)
    if await db.imports.count_documents({}) > 0:
        return
    for turma_name in ["9º A", "9º B"]:
        for i, periodo in enumerate(["2024.1", "2024.2", "2025.1"]):
            alunos = []
            for aluno_id, nome in SAMPLE_ALUNOS:
                erros = []
                for no in SAMPLE_NOS:
                    # Randomly some students miss some nós
                    if random.random() < 0.15:
                        continue
                    base = 0.15 + i * 0.02 * (1 if turma_name == "9º A" else -1)
                    taxa = max(0.0, min(1.0, base + random.uniform(-0.15, 0.35)))
                    num_q = random.choice([4, 5, 6, 8])
                    erros.append({
                        "no_id": no["no_id"], "no_label": no["no_label"],
                        "disciplina": no["disciplina"],
                        "taxa_erro": round(taxa, 3), "num_questoes": num_q,
                    })
                # Some students missing "taxa_erro"
                if random.random() < 0.1 and erros:
                    erros[0]["taxa_erro"] = None
                alunos.append({"aluno_id": aluno_id, "nome": nome, "erros_por_no": erros})
            doc = {
                "turma": turma_name,
                "periodo": periodo,
                "versao_taxonomia": "Taxonomia Sapiens v0.8 (Experimental)" if i < 2 else "Taxonomia Sapiens v0.9 (Experimental)",
                "data_processamento": f"2024-0{i+3}-15T10:00:00Z",
                "modelo_analise": "sapiens-cognitive-v1.2",
                "ano_escolar": "9º ano",
                "banca": "Simulado Sapiens",
                "prova": f"Prova bimestral {periodo}",
                "alunos": alunos,
                "_ingested_at": datetime.now(timezone.utc).isoformat(),
                "_ingested_by": "seed",
                "import_id": str(uuid.uuid4()),
            }
            await db.imports.insert_one(doc)
    logger.info("Sample data seeded.")


async def seed_admin():
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@sapiens.edu")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        await db.users.insert_one({
            "email": admin_email,
            "password_hash": hash_password(admin_password),
            "name": "Administrador Sapiens",
            "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("Admin user seeded.")
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one({"email": admin_email},
                                  {"$set": {"password_hash": hash_password(admin_password)}})


@app.on_event("startup")
async def on_startup():
    await db.users.create_index("email", unique=True)
    await db.imports.create_index([("turma", 1), ("periodo", 1)])
    await seed_admin()
    await seed_sample_data()


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()


@api_router.get("/")
async def root():
    return {"message": "Sapiens Dashboard API", "status": "ok"}


app.include_router(api_router)

# CORS — explicit origins with credentials
allowed_origins = [FRONTEND_URL, "http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
