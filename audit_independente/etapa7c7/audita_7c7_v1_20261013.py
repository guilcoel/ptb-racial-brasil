"""
Auditor independente da Etapa 7c.7 (pacote v12_20261013), rodada 1. Código próprio: não importa etapa7b_lib, etapa0_lib nem o checa.
  A  integridade do repositório e da árvore desde dc9328d (git só leitura, GIT_OPTIONAL_LOCKS=0)
  B  pacote v11 (arquivado) × v12, arquivo por arquivo; recontagem de CE/DF na base territorial
  C  código: diffs revisados linha a linha, AST do etapa2_03, checa (estático aqui; dinâmico no módulo de sandbox), script novo,
     LEIAME (dinâmico no sandbox)
  D  logs de 2026-10-13 (ordem e horários × mtimes). As linhas do checa só por horário e nome nesta rodada.
  E  microdados e git: o que iria para o commit
Lê sandbox_7c7_v1_20261013.json (gerado por audita_7c7_sandbox_v1_20261013.py) para os testes dinâmicos (C3, C4, C6).
Não lê o CSV da autoauditoria (audita_7c7_v1_20261013.csv) nem o checa_7b_v12_20261013.csv: a comparação com eles fica em
audita_7c7_comparacao_v1_20261013.py, rodado depois. Microdados: data/ só por nome (os.listdir em data/processed).
Grava só em audit_independente/etapa7c7/: comparacao_7c7_v1_20261013.csv.
Rodar: python3 audit_independente/etapa7c7/audita_7c7_v1_20261013.py
"""
import ast
import difflib
import hashlib
import io
import json
import os
import re
import subprocess
import time
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path

import docx
import openpyxl
import pandas as pd
import pymupdf
from PIL import Image

PROJ = Path("/Volumes/Forja/ptb-racial-brasil")
OUTD = PROJ / "audit_independente" / "etapa7c7"
MS, SUB = PROJ / "outputs" / "manuscrito", PROJ / "Submissao"
A10, A11 = MS / "_arquivo_v10", MS / "_arquivo_v11"
V10, V11, V12 = "v10_20261009", "v11_20261009", "v12_20261013"
HEAD_FULL, HEAD = "dc9328d9d652146341efdc6286462668c2a64a02", "dc9328d"
FRASE = "Joint Wald tests were not computed for the multiple-imputation analysis."
ANTES = "combined with Rubin's rules."
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
LISTA36 = Path("/private/tmp/claude-501/-Users-guilherme/e1c712c9-85af-4f6d-89f1-cb28b034e571/scratchpad/apple_double_7c7.txt")
R = []
T0 = time.strftime("%Y-%m-%d %H:%M:%S")


def ok(vid, desc, cond, det=""):
    R.append(dict(verificacao=f"{vid} {desc}", ok=bool(cond), detalhe=str(det)[:1800]))
    print(f"{'OK   ' if cond else 'FALHA'} {vid} {desc[:90]} | {str(det)[:160]}", flush=True)


def git(*a, check=True):
    r = subprocess.run(["git", "-C", str(PROJ), *a], capture_output=True, text=True, env=ENV)
    if check and r.returncode:
        raise RuntimeError(f"git {a}: {r.stderr}")
    return r.stdout


def gitb(*a):
    return subprocess.run(["git", "-C", str(PROJ), *a], capture_output=True, env=ENV, check=True).stdout


md5b = lambda b: hashlib.md5(b).hexdigest()
md5f = lambda p: md5b(Path(p).read_bytes())
hora = lambda t: datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S")


def arvore_disco():
    """Arquivos do projeto fora de data/ e .git/ (caminhos relativos)."""
    out = []
    for raiz, dirs, fs in os.walk(PROJ):
        rel = Path(raiz).relative_to(PROJ)
        if rel == Path("."):
            dirs[:] = [d for d in dirs if d not in ("data", ".git")]
        out += [str((rel / f)) if rel != Path(".") else f for f in fs]
    return sorted(out)


def snapshot():
    """MD5 de tudo o que o pacote e os scripts têm hoje (para detectar mudanças durante a auditoria)."""
    alvo = [p for p in arvore_disco() if p.startswith(("outputs/manuscrito/", "Submissao/", "scripts/", "outputs/tables/tab_e7c7"))]
    return {p: md5f(PROJ / p) for p in alvo}


SNAP0 = snapshot()

# =============================================================== A. integridade
TCOMMIT = int(git("log", "-1", "--format=%ct", HEAD).strip())
ok("A1.01", "HEAD = dc9328d (hash completo), branch main, sem HEAD destacado",
   git("rev-parse", "HEAD").strip() == HEAD_FULL and git("symbolic-ref", "HEAD").strip() == "refs/heads/main",
   f"HEAD {git('rev-parse', 'HEAD').strip()}; {git('symbolic-ref', 'HEAD').strip()}")
refs = git("for-each-ref", "--format=%(refname) %(objectname)").split("\n")
refs = [r for r in refs if r]
novos = [l for l in git("rev-list", "--all", "--reflog", "--format=%H %ct", "--no-commit-header").splitlines() if int(l.split()[1]) > TCOMMIT]
ok("A1.02", "nenhum commit novo: só refs/heads/main → dc9328d; nenhum commit (refs nem reflog) posterior a dc9328d; stash vazio",
   refs == [f"refs/heads/main {HEAD_FULL}"] and not novos and not git("stash", "list").strip(), f"refs {refs}; commits posteriores {novos[:3]}")
ok("A1.03", "sem remoto", not git("remote").strip() and not git("for-each-ref", "refs/remotes").strip(), git("remote").strip() or "nenhum")
ok("A1.04", "sem tag", not git("tag", "-l").strip() and not git("for-each-ref", "refs/tags").strip(), git("tag", "-l").strip() or "nenhuma")

arv0 = {}
for l in git("ls-tree", "-r", HEAD).splitlines():
    meta, p = l.split("\t", 1)
    arv0[p] = meta.split()[2]
MOV = sorted(p for p in arv0 if p.startswith("outputs/manuscrito/") and not p.startswith("outputs/manuscrito/_arquivo_") and V11 in p)
DEST = {p: p.replace("outputs/manuscrito/", "outputs/manuscrito/_arquivo_v11/", 1) for p in MOV}
cached = [l.split("\t") for l in git("diff", "--cached", "--name-status", "-M", HEAD).splitlines()]
ok("A1.05", "índice: só as 38 renomeações R100 (pacote v11 → _arquivo_v11/), nada mais em stage",
   len(MOV) == 38 and len(cached) == 38 and all(x[0] == "R100" and DEST.get(x[1]) == x[2] for x in cached),
   f"{len(cached)} entradas em stage; status {dict(Counter(x[0] for x in cached))}")

dif = [l.split("\t") for l in git("diff", "--no-renames", "--name-status", HEAD).splitlines()]
M_ESP = {"Submissao/ESM_1.xlsx", "Submissao/ESM_2.pdf", "Submissao/ESM_3.pdf", "Submissao/ESM_4.pdf", "outputs/manuscrito/MANIFEST.md",
         "outputs/manuscrito/data_code_availability.md", "outputs/manuscrito/legendas_figuras.md", "scripts/etapa2_03_indice_acesso.py",
         "scripts/etapa7b_lib.py", "scripts/etapa7b_01_tabelas.py", "scripts/etapa7b_02_suplementar.py", "scripts/etapa7b_04_submissao.py",
         "scripts/etapa7b_checa.py", "scripts/resumos/LEIAME.md"}
por = {s: {p for st, p in dif if st == s} for s in ("M", "D", "A")}
ok("A2.01", "rastreados modificados (--no-renames, árvore × dc9328d) = os 14 descritos (pacote, Submissao/ESM_1–4, 6 scripts e o LEIAME)",
   por["M"] == M_ESP and set(s for s, _ in dif) <= {"M", "D", "A"}, f"M {len(por['M'])}; fora do descrito {sorted(por['M'] - M_ESP)}; "
   f"faltando {sorted(M_ESP - por['M'])}; status {dict(Counter(s for s, _ in dif))}")
ok("A2.02", "rastreados apagados/adicionados = as 38 origens e os 38 destinos da renomeação",
   por["D"] == set(MOV) and por["A"] == set(DEST.values()), f"D {len(por['D'])}; A {len(por['A'])}")
untr = sorted(p for p in git("ls-files", "-o", "--exclude-standard", "-z").split("\0") if p)
U_V12 = {p.replace(V11, V12) for p in MOV}
U_COP = {f"outputs/manuscrito/_arquivo_v11/{x}" for x in [f"MANIFEST_{V11}.md", f"data_code_availability_{V11}.md", f"legendas_figuras_{V11}.md"]
         + [f"Submissao/{y}" for y in ["ESM_1.xlsx", "ESM_2.pdf", "ESM_3.pdf", "ESM_4.pdf", "Fig1.tif", "Fig2.tif", "Fig3.tif", "Fig4.tif"]]}
U_OUT = {"outputs/manuscrito/audita_7c7_v1_20261013.csv", "scripts/etapa7c7_01_regsaude_uf.py", "scripts/etapa7c7_02_audita.py"}
docs_u = [p for p in untr if p.startswith("docs/referencias/")]
meus = [p for p in untr if p.startswith("audit_independente/etapa7c7/")]
extra_all = sorted(set(untr) - U_V12 - U_COP - U_OUT - set(docs_u) - set(meus))
RESUMO7 = {"outputs/manuscrito/_resumo7c7_texto_v1_20261013.md", "scripts/resumos/etapa7c7_01_resumo.py", "outputs/RESUMO_ETAPA7C7_v1_20261013.md"}
extra = [p for p in extra_all if p not in RESUMO7]
res7 = [p for p in extra_all if p in RESUMO7]
ok("A2.03", "não rastreados previstos presentes: 38 da v12, 11 cópias em _arquivo_v11/, os 2 scripts novos e o CSV da autoauditoria",
   U_V12 <= set(untr) and U_COP <= set(untr) and U_OUT <= set(untr),
   f"v12 {len(U_V12 & set(untr))}/38; cópias {len(U_COP & set(untr))}/11; novos {sorted(U_OUT & set(untr))}")
ok("A2.04", "não rastreados fora do descrito: nenhum (afora docs/referencias, a pasta deste auditor e o RESUMO da etapa, em A2.07)", not extra,
   "; ".join(f"{p} (mtime {hora((PROJ / p).stat().st_mtime)})" for p in extra) or "nenhum")
ok("A2.07", "(informativo) RESUMO da 7c.7 em preparação: não descrito na tarefa, criado durante a auditoria; conteúdo não auditado", True,
   "; ".join(f"{p} (mtime {hora((PROJ / p).stat().st_mtime)})" for p in res7) or "nenhum")
m4 = pd.read_csv(PROJ / "audit_independente/etapa7c6_final/m4_referencias_nao_rastreadas_7c6_final_v1_20261010.csv")
mt_docs = [(PROJ / p).stat().st_mtime for p in docs_u]
ok("A2.05", "os 93 não rastreados de docs/referencias já existiam: mtime anterior a dc9328d e mesma lista da auditoria final da 7c.6",
   len(docs_u) == 93 and max(mt_docs) < TCOMMIT and set(docs_u) == set(m4.arquivo),
   f"{len(docs_u)} arquivos; mtime máx {hora(max(mt_docs))}; commit {hora(TCOMMIT)}; = lista m4 7c.6_final: {set(docs_u) == set(m4.arquivo)}")
ign = sorted(p for p in git("ls-files", "-o", "-i", "--exclude-standard", "-z", "--", "outputs", "scripts", "docs", "audit_independente",
                              "Submissao").split("\0") if p)
ign += [f for f in os.listdir(PROJ) if (PROJ / f).is_file() and f not in (".gitignore",) and subprocess.run(
    ["git", "-C", str(PROJ), "check-ignore", "-q", f], env=ENV).returncode == 0]
ign_novos = sorted(p for p in ign if (PROJ / p).stat().st_mtime > TCOMMIT and "__pycache__" not in p and not p.startswith("audit_independente/etapa7c7/"))
IGN_ESP = {"outputs/tables/tab_e7c7_01_regsaude_uf_v1_20261008.csv", "outputs/logs/etapa7b_20261008.log", "outputs/logs/etapa7c7_20261008.log",
           "outputs/logs/etapa7c6_20261008.log"}
ok("A2.06", "ignorados pelo git criados/alterados depois de dc9328d (fora de data/): só a tabela nova e os logs",
   set(ign_novos) <= IGN_ESP and "outputs/tables/tab_e7c7_01_regsaude_uf_v1_20261008.csv" in ign_novos,
   "; ".join(f"{p} ({hora((PROJ / p).stat().st_mtime)[11:]})" for p in ign_novos))

idx = {}
for l in git("ls-files", "-s").splitlines():
    meta, p = l.split("\t", 1)
    idx[p] = meta.split()[1]


def hash_disco(paths):
    if not paths:
        return {}
    r = subprocess.run(["git", "-C", str(PROJ), "hash-object", "--stdin-paths"], input="\n".join(paths), capture_output=True, text=True,
                       env=ENV, check=True)
    return dict(zip(paths, r.stdout.split()))


hd = hash_disco([DEST[p] for p in MOV])
iguais38 = [p for p in MOV if arv0[p] == idx.get(DEST[p]) == hd[DEST[p]]]
ok("A3.01", "os 38 movidos: blob em dc9328d = blob no índice (destino) = bytes no disco (git hash-object)", len(iguais38) == 38,
   f"{len(iguais38)}/38; divergentes {sorted(set(MOV) - set(iguais38))[:3]}")
resto_v11 = [p for p in arvore_disco() if V11 in p and not p.startswith("outputs/manuscrito/_arquivo_v11/")
             and not p.startswith(("audit_independente/", "outputs/RESUMO", "scripts/"))]
ok("A3.02", "nenhum arquivo com rótulo v11 ficou fora de _arquivo_v11/ (na raiz do pacote e em Submissao/)", not resto_v11, resto_v11[:5] or "0")

est = lambda d, v: sorted(str(x.relative_to(d)).replace(v, "VV") for x in d.rglob("*") if x.is_file() and not x.name.startswith("._"))
e10, e11 = est(A10, V10), est(A11, V11)
ok("A4.01", "_arquivo_v11/ com a mesma estrutura de _arquivo_v10/ (nomes com a versão normalizada)", e10 == e11 and len(e11) == 49,
   f"v10 {len(e10)}; v11 {len(e11)}; só na v10 {sorted(set(e10) - set(e11))[:3]}; só na v11 {sorted(set(e11) - set(e10))[:3]}")
COP = {f"_arquivo_v11/MANIFEST_{V11}.md": "outputs/manuscrito/MANIFEST.md",
       f"_arquivo_v11/data_code_availability_{V11}.md": "outputs/manuscrito/data_code_availability.md",
       f"_arquivo_v11/legendas_figuras_{V11}.md": "outputs/manuscrito/legendas_figuras.md",
       **{f"_arquivo_v11/Submissao/{y}": f"Submissao/{y}" for y in ["ESM_1.xlsx", "ESM_2.pdf", "ESM_3.pdf", "ESM_4.pdf", "Fig1.tif", "Fig2.tif",
                                                                  "Fig3.tif", "Fig4.tif"]}}
hc = hash_disco([f"outputs/manuscrito/{k}" for k in COP])
cop_ok = [k for k, v in COP.items() if hc[f"outputs/manuscrito/{k}"] == arv0[v]]
ok("A4.02", "as 11 cópias de _arquivo_v11/ (MANIFEST, disponibilidade, legendas, Submissao/×8) = arquivos de dc9328d, byte a byte",
   len(cop_ok) == 11, f"{len(cop_ok)}/11; divergentes {sorted(set(COP) - set(cop_ok))}")
arv_b9 = {l.split("\t", 1)[1]: l.split()[2] for l in git("ls-tree", "-r", "b9d6272").splitlines()}
arv_83 = {l.split("\t", 1)[1]: l.split()[2] for l in git("ls-tree", "-r", "8314417").splitlines()}
cop10 = {k.replace("_arquivo_v11", "_arquivo_v10").replace(V11, V10): v for k, v in COP.items()}
igual10 = [k for k, v in cop10.items() if arv_b9.get(f"outputs/manuscrito/{k}") == arv_83.get(v)]
ok("A4.03", "mesmo método da _arquivo_v10: lá as 11 cópias também são os arquivos do commit anterior (8314417), byte a byte",
   len(igual10) == 11, f"{len(igual10)}/11")

lixo = [p for p in arvore_disco() if Path(p).name.startswith("._")]
ok("A5.01", "._*: nenhum no projeto fora de data/ (inclui a raiz, .gitignore à parte)", not lixo, lixo[:5] or "0")
nomes_proc = os.listdir(PROJ / "data" / "processed")                # só nomes
ad_proc = [n for n in nomes_proc if n.startswith("._")]
ok("A5.02", "o ._* de data/processed continua (só o nome, nada aberto)", ad_proc == ["._pig_grade_intergrowth_v1_20261008.parquet"], ad_proc)
l36 = [l.strip() for l in LISTA36.read_text().splitlines() if l.strip()]
ok("A5.03", "lista dos 36: 36 caminhos, todos fora de data/, nenhum existe mais", len(l36) == 36 and not any(p.startswith("data/") for p in l36)
   and not any((PROJ / p).exists() for p in l36), f"{len(l36)} na lista; ainda existem {[p for p in l36 if (PROJ / p).exists()]}; "
   f"por pasta {dict(Counter(str(Path(p).parent).split('/_arquivo_')[0] for p in l36))}")

disco = set(arvore_disco())
sumiu = sorted(p for p in arv0 if p not in disco and not p.startswith("data/"))
ok("A6.01", "nenhum arquivo de dc9328d sumiu: os únicos ausentes são as 38 origens movidas (presentes em _arquivo_v11/)",
   set(sumiu) == set(MOV) and all(DEST[p] in disco for p in MOV), f"ausentes {len(sumiu)}; fora dos 38 {sorted(set(sumiu) - set(MOV))[:5]}")
presentes = sorted(p for p in arv0 if p in disco)
hp = hash_disco(presentes)
mud = sorted(p for p in presentes if hp[p] != arv0[p])
ok("A6.02", "conteúdo (git hash-object) de todo arquivo de dc9328d presente no disco: só os 14 descritos mudaram",
   set(mud) == M_ESP, f"{len(presentes)} arquivos conferidos; mudaram {len(mud)}; fora do descrito {sorted(set(mud) - M_ESP)}")

# =============================================================== B. pacote v11 × v12
nb1 = 0
for sub in ("tabelas", "suplementar"):
    for f in sorted((A11 / sub).glob(f"*_{V11}.csv")):
        g = MS / sub / f.name.replace(V11, V12)
        nb1 += 1
        ok(f"B1.{nb1:02d}", f"CSV {sub}/{f.name.replace(V11, 'vXX')}: v11 = v12 byte a byte", g.exists() and f.read_bytes() == g.read_bytes(),
           f"{f.stat().st_size} B; md5 {md5f(f)[:12]}")
csv_v12 = sorted(x.name for s in ("tabelas", "suplementar") for x in (MS / s).glob(f"*_{V12}.csv"))
ok("B1.99", "conjunto de CSVs da v12 = o da v11 (nenhum a mais ou a menos)",
   csv_v12 == sorted(x.name.replace(V11, V12) for s in ("tabelas", "suplementar") for x in (A11 / s).glob(f"*_{V11}.csv")), f"{len(csv_v12)} CSVs")


def celulas(f):
    wb = openpyxl.load_workbook(f)
    return [(ws.title, {(c.row, c.column): c.value for row in ws.iter_rows() for c in row if c.value is not None}) for ws in wb.worksheets]


def zip_dif(a, b):
    za, zb = zipfile.ZipFile(a), zipfile.ZipFile(b)
    na, nb = set(za.namelist()), set(zb.namelist())
    return sorted(n for n in na | nb if n not in na or n not in nb or za.read(n) != zb.read(n))


xa, xb = celulas(A11 / "tabelas" / f"tabelas_principais_{V11}.xlsx"), celulas(MS / "tabelas" / f"tabelas_principais_{V12}.xlsx")
difx = [(ta, k) for (ta, ca), (tb, cb) in zip(xa, xb) for k in set(ca) | set(cb) if ca.get(k) != cb.get(k)]
t4a = dict(xa)["tab04_sensitivity"][(18, 1)] if "tab04_sensitivity" in dict(xa) else ""
t4b = dict(xb)["tab04_sensitivity"][(18, 1)] if "tab04_sensitivity" in dict(xb) else ""
ok("B2.01", "xlsx tabelas principais, célula a célula em todas as abas: só o rodapé da Tabela 4 muda, e só pela frase nova logo depois de "
   "\"combined with Rubin's rules.\"", [t for t, _ in xa] == [t for t, _ in xb] and difx == [("tab04_sensitivity", (18, 1))]
   and t4a.count(ANTES) == 1 and t4b == t4a.replace(ANTES, ANTES + " " + FRASE),
   f"abas {[t for t, _ in xb]}; células diferentes {difx}; {sum(len(c) for _, c in xb)} células na v12")
i_t4 = [t for t, _ in xb].index("tab04_sensitivity") + 1
ok("B2.02", "xlsx tabelas principais: partes do zip que mudam = só a planilha da Tabela 4 e os metadados (docProps/core.xml)",
   set(zip_dif(A11 / "tabelas" / f"tabelas_principais_{V11}.xlsx", MS / "tabelas" / f"tabelas_principais_{V12}.xlsx")) == {f"xl/worksheets/sheet{i_t4}.xml", "docProps/core.xml"},
   zip_dif(A11 / "tabelas" / f"tabelas_principais_{V11}.xlsx", MS / "tabelas" / f"tabelas_principais_{V12}.xlsx"))
ea, eb = celulas(A11 / "suplementar" / f"ESM_1_tables_S1_S6_{V11}.xlsx"), celulas(MS / "suplementar" / f"ESM_1_tables_S1_S6_{V12}.xlsx")
ok("B2.03", "xlsx ESM_1 do pacote, célula a célula em todas as abas: v11 = v12", ea == eb,
   f"{len(eb)} abas; {sum(len(c) for _, c in eb)} células; zip muda em {zip_dif(A11 / 'suplementar' / f'ESM_1_tables_S1_S6_{V11}.xlsx', MS / 'suplementar' / f'ESM_1_tables_S1_S6_{V12}.xlsx')}")
es = celulas(SUB / "ESM_1.xlsx")
ok("B2.04", "Submissao/ESM_1.xlsx = ESM_1 da v12 (bytes) e, célula a célula, = Submissao/ESM_1 da v11",
   (SUB / "ESM_1.xlsx").read_bytes() == (MS / "suplementar" / f"ESM_1_tables_S1_S6_{V12}.xlsx").read_bytes() and es == celulas(A11 / "Submissao/ESM_1.xlsx")
   and not any("S5b" in t or "INTERNAL" in t for t, _ in es), f"abas {[t for t, _ in es]}")
ok("B2.05", "_arquivo_v11/Submissao/ESM_1.xlsx = ESM_1 da v11 arquivada (bytes)",
   (A11 / "Submissao/ESM_1.xlsx").read_bytes() == (A11 / "suplementar" / f"ESM_1_tables_S1_S6_{V11}.xlsx").read_bytes())

da_, db_ = docx.Document(A11 / "tabelas" / f"tabelas_principais_{V11}.docx"), docx.Document(MS / "tabelas" / f"tabelas_principais_{V12}.docx")
pa, pb = [p.text for p in da_.paragraphs], [p.text for p in db_.paragraphs]
dp = [i for i, (u, v) in enumerate(zip(pa, pb)) if u != v]
ta_ = [[[c.text for c in r.cells] for r in t.rows] for t in da_.tables]
tb_ = [[[c.text for c in r.cells] for r in t.rows] for t in db_.tables]
ok("B3.01", "docx: tabelas idênticas; parágrafos: só o rótulo de versão (parágrafo 0) e a frase nova no rodapé da Tabela 4",
   len(pa) == len(pb) and ta_ == tb_ and len(dp) == 2 and pb[dp[0]] == pa[dp[0]].replace(V11, V12) and V11 in pa[dp[0]]
   and pb[dp[1]] == pa[dp[1]].replace(ANTES, ANTES + " " + FRASE) and "Multiple imputation" in pa[dp[1]],
   f"{len(pb)} parágrafos; mudam {dp}; parágrafo {dp[0] if dp else '-'}: {pa[dp[0]][:60]!r} → {pb[dp[0]][:60]!r}")
zd = zip_dif(A11 / "tabelas" / f"tabelas_principais_{V11}.docx", MS / "tabelas" / f"tabelas_principais_{V12}.docx")
xa_ = zipfile.ZipFile(A11 / "tabelas" / f"tabelas_principais_{V11}.docx").read("word/document.xml").decode()
xb_ = zipfile.ZipFile(MS / "tabelas" / f"tabelas_principais_{V12}.docx").read("word/document.xml").decode()
apos = "combined with Rubin&apos;s rules." if "Rubin&apos;s" in xa_ else ANTES
ok("B3.02", "docx no nível do XML: só word/document.xml muda, e = XML da v11 com o rótulo de versão trocado e a frase inserida "
   "(formatação, runs e metadados iguais)", zd == ["word/document.xml"] and xa_.replace(V11, V12).replace(apos, apos + " " + FRASE) == xb_,
   f"partes que mudam {zd}; core: {da_.core_properties.created} = {db_.core_properties.created}")


def txt_pdf(f):
    return [pg.get_text() for pg in pymupdf.open(f)]


def render(f):
    return [md5b(pg.get_pixmap(dpi=50).samples) for pg in pymupdf.open(f)]


def meta_sem_data(f):
    """Metadados do PDF sem datas, sem o título (nome do HTML temporário que o Chrome imprime) e sem a versão do Chrome."""
    m = dict(pymupdf.open(f).metadata)
    return {k: v for k, v in m.items() if k not in ("creationDate", "modDate", "title", "creator", "producer")}


def meta_dif(a, b):
    x, y = pymupdf.open(a).metadata, pymupdf.open(b).metadata
    return {k: (x[k], y.get(k)) for k in x if x[k] != y.get(k) and k not in ("creationDate", "modDate")}


PDFS = [(A11 / "suplementar" / f"S7_variables_codes_{V11}.pdf", MS / "suplementar" / f"S7_variables_codes_{V12}.pdf"),
        (A11 / "suplementar" / f"S8_strobe_record_checklist_{V11}.pdf", MS / "suplementar" / f"S8_strobe_record_checklist_{V12}.pdf")] + \
       [(A11 / "Submissao" / f"ESM_{k}.pdf", SUB / f"ESM_{k}.pdf") for k in (2, 3, 4)]
for nb4, (a, b) in enumerate(PDFS, 1):
    ta, tb = txt_pdf(a), txt_pdf(b)
    ok(f"B4.{nb4:02d}", f"PDF {b.relative_to(PROJ)}: texto de cada página = v11; páginas renderizadas (50 dpi) iguais; metadados iguais fora "
       "datas, título (HTML temporário) e versão do Chrome",
       ta == tb and render(a) == render(b) and meta_sem_data(a) == meta_sem_data(b),
       f"{len(tb)} páginas; texto igual {ta == tb}; render igual {render(a) == render(b)}; datas {pymupdf.open(a).metadata.get('creationDate')} → "
       f"{pymupdf.open(b).metadata.get('creationDate')}; outros metadados que mudam: {meta_dif(a, b)}")


def px(f):
    im = Image.open(f)
    return (im.size, im.mode, im.info.get("dpi"), im.info.get("compression"), md5b(im.tobytes()))


IMGS = [f for f in sorted((A11 / "figuras").iterdir())] + sorted((A11 / "suplementar").glob("S9_*"))
for nb5, f in enumerate(IMGS, 1):
    g = MS / f.parent.name / f.name.replace(V11, V12)
    ok(f"B5.{nb5:02d}", f"imagem {f.parent.name}/{f.name.replace(V11, 'vXX')}: pixels, modo, dpi e compressão = v11 (e bytes iguais)",
       px(f) == px(g) and f.read_bytes() == g.read_bytes(), f"{px(g)[:4]}")
for k in range(1, 5):
    ok(f"B5.{len(IMGS) + k:02d}", f"Submissao/Fig{k}.tif: pixels e dpi = _arquivo_v11/Submissao/Fig{k}.tif (e bytes iguais)",
       px(SUB / f"Fig{k}.tif") == px(A11 / "Submissao" / f"Fig{k}.tif") and (SUB / f"Fig{k}.tif").read_bytes() == (A11 / "Submissao" / f"Fig{k}.tif").read_bytes(),
       px(SUB / f"Fig{k}.tif")[:4])

subs = sorted(os.listdir(SUB))
ok("B6.01", "Submissao/ só com Fig1–4.tif e ESM_1–4 (sem ._*, sem .DS_Store)",
   subs == ["ESM_1.xlsx", "ESM_2.pdf", "ESM_3.pdf", "ESM_4.pdf", "Fig1.tif", "Fig2.tif", "Fig3.tif", "Fig4.tif"], subs)
FIGN = {1: "fig01_flowchart", 2: "fig02_pr_race_m1m3", 3: "fig03_rd_race_tercile", 4: "fig04_dating"}
for k, n in FIGN.items():
    ok(f"B6.{k + 1:02d}", f"Submissao/Fig{k}.tif = figuras/{n}_v12.tif (bytes)", (SUB / f"Fig{k}.tif").read_bytes() == (MS / "figuras" / f"{n}_{V12}.tif").read_bytes())
ok("B6.06", "Submissao/ESM_2.pdf = suplementar/S7_variables_codes_v12.pdf (bytes)",
   (SUB / "ESM_2.pdf").read_bytes() == (MS / "suplementar" / f"S7_variables_codes_{V12}.pdf").read_bytes())
ok("B6.07", "Submissao/ESM_3.pdf = suplementar/S8_strobe_record_checklist_v12.pdf (bytes)",
   (SUB / "ESM_3.pdf").read_bytes() == (MS / "suplementar" / f"S8_strobe_record_checklist_{V12}.pdf").read_bytes())
e4 = pymupdf.open(SUB / "ESM_4.pdf")
imgs4 = e4[0].get_images(full=True)
s9 = Image.open(MS / "suplementar" / f"S9_maihda_caterpillar_{V12}.png")
leg = [l for l in (MS / "legendas_figuras.md").read_text().split("\n\n") if l.startswith("**Online Resource 4")][0]
leg_txt = " ".join(leg.split("**", 2)[2].split())
t4pdf = " ".join(e4[0].get_text().split())
dims4 = [(i[2], i[3]) for i in imgs4]
ok("B6.08", "Submissao/ESM_4.pdf: 1 página com a imagem do S9 v12 (mesmas dimensões) e a legenda do Online Resource 4 das legendas v12",
   len(e4) == 1 and (s9.size in dims4) and leg_txt in t4pdf, f"imagens {dims4}; S9 {s9.size}; legenda presente {leg_txt in t4pdf}")
ok("B6.09", "Submissao/ESM_1.xlsx = suplementar/ESM_1_tables_S1_S6_v12.xlsx (bytes)",
   (SUB / "ESM_1.xlsx").read_bytes() == (MS / "suplementar" / f"ESM_1_tables_S1_S6_{V12}.xlsx").read_bytes())


def manifest(f):
    L = f.read_text().splitlines()
    rows = {}
    for l in L:
        if l.startswith(("| manuscrito/", "| Submissao/")):
            c = [x.strip() for x in l.strip().strip("|").split("|")]    # a origem pode ter '|' (|PR_M2cc − 1|): MD5 = último campo
            rows[c[0]] = [c[1], "|".join(c[2:-1]).strip(), c[-1]]
    return L, rows


L11, M11 = manifest(A11 / f"MANIFEST_{V11}.md")
L12, M12 = manifest(MS / "MANIFEST.md")
M11n = {k.replace(V11, V12): v for k, v in M11.items()}
md5_mud = sorted(k for k in M11n if k in M12 and M11n[k][2] != M12[k][2])
outra_col = sorted(k for k in M11n if k in M12 and M11n[k][:2] != M12[k][:2])
novas, sairam = sorted(set(M12) - set(M11n)), sorted(set(M11n) - set(M12))
MD5_ESP = {f"manuscrito/tabelas/tabelas_principais_{V12}.docx", f"manuscrito/tabelas/tabelas_principais_{V12}.xlsx",
           f"manuscrito/suplementar/ESM_1_tables_S1_S6_{V12}.xlsx", f"manuscrito/suplementar/S7_variables_codes_{V12}.pdf",
           f"manuscrito/suplementar/S8_strobe_record_checklist_{V12}.pdf", f"manuscrito/checa_7b_{V12}.csv", "manuscrito/data_code_availability.md",
           "manuscrito/legendas_figuras.md", f"manuscrito/numeros_chave_{V12}.json", f"manuscrito/numeros_chave_{V12}.md",
           "Submissao/ESM_1.xlsx", "Submissao/ESM_2.pdf", "Submissao/ESM_3.pdf", "Submissao/ESM_4.pdf"}
SENT12 = ("; v12 = v11 com o rodapé da Tabela 4 dizendo que os testes de Wald conjuntos não foram calculados na imputação múltipla, os "
          "números-chave n_regsaude_CE e n_regsaude_DF (regiões de saúde na base territorial, tab_e7c7_01_regsaude_uf) e suplementar/ sem "
          "arquivos ._* (dot_clean no 02)")
l3_11 = (L11[2].replace(V11, V12).replace("2026-10-09", "2026-10-13").replace("8314417", HEAD)
         .replace("'Etapa 7c.6: auditoria independente 7c.5/7c.5b, RECORD e rastreabilidade'", "'Etapa 7c.7: pacote v12 com as decisões da 7c.6b'")
         .replace("nos números-chave. Scripts", "nos números-chave" + SENT12 + ". Scripts"))
fora_tab = [i for i, (a, b) in enumerate(zip(L11, L12)) if not a.startswith("| ") and a.replace(V11, V12) != b]
ok("B7.01", "MANIFEST × v11 (versão normalizada): fora da tabela de arquivos, só o título (7b–7c.7) e o parágrafo do topo (data, commit "
   "dc9328d, nome do commit da 7c.7 e a frase da v12)",
   fora_tab == [0, 2] and L12[0] == L11[0].replace("7b–7c.6", "7b–7c.7").replace(V11, V12) and L12[2] == l3_11,
   f"linhas fora da tabela que mudam: {fora_tab}")
ok("B7.02", "MANIFEST: na tabela de arquivos, origem e script iguais; MD5 muda só nos 14 arquivos regenerados (xlsx, docx, PDFs, md, json, checa, "
   "Submissao/ESM_1–4); nenhuma linha some", not outra_col and set(md5_mud) == MD5_ESP and not sairam,
   f"MD5 mudou em {len(md5_mud)}; fora do previsto {sorted(set(md5_mud) - MD5_ESP)}; não mudou e devia {sorted(MD5_ESP - set(md5_mud))}; saíram {sairam}")
ok("B7.03", "MANIFEST (informativo): linhas novas na tabela de arquivos", True,
   f"linhas novas: {novas} — CSV da autoauditoria da 7c.6b, criado depois do MANIFEST da v11; o 04 lista tudo o que está na raiz de "
   "outputs/manuscrito, não só o pacote")
abs_ = lambda k: (MS / k.split("/", 1)[1]) if k.startswith("manuscrito/") else (PROJ / k)
md5_ok = [k for k, v in M12.items() if abs_(k).exists() and md5f(abs_(k))[:12] == v[2]]
ok("B7.04", "MANIFEST: o MD5 de cada arquivo listado confere com o disco", len(md5_ok) == len(M12),
   f"{len(md5_ok)}/{len(M12)}; divergentes {sorted(set(M12) - set(md5_ok))}")
lista_atual = sorted([f"manuscrito/{d}/{f.name}" for d in ("tabelas", "figuras", "suplementar") for f in (MS / d).iterdir() if f.is_file()
                      and not f.name.startswith(("._", "_"))] + [f"manuscrito/{f.name}" for f in MS.iterdir() if f.is_file()
                      and not f.name.startswith(("._", "_")) and f.name != "MANIFEST.md"] + [f"Submissao/{f.name}" for f in SUB.iterdir() if not f.name.startswith("._")])
falta_m = sorted(set(lista_atual) - set(M12))
ok("B7.05", "MANIFEST lista todo arquivo que o 04 listaria hoje (pastas do pacote, raiz de outputs/manuscrito e Submissao/)", not falta_m,
   f"não listados: {[(x, hora(abs_(x).stat().st_mtime)[11:]) for x in falta_m]}; MANIFEST gravado {hora((MS / 'MANIFEST.md').stat().st_mtime)[11:]}")

d11 = (A11 / f"data_code_availability_{V11}.md").read_text()
d12 = (MS / "data_code_availability.md").read_text()
volta = (d12.replace(V12, V11).replace("Etapa 7c.7: pacote v12 com as decisões da 7c.6b", "Etapa 7c.6: auditoria independente 7c.5/7c.5b, RECORD e rastreabilidade")
         .replace('"Etapa 7c.7"', '"Etapa 7c.6"').replace("Etapa 7c.7)", "Etapa 7c.6)"))
dl = [l for l in difflib.unified_diff(d11.splitlines(), d12.splitlines(), lineterm="", n=0) if l[:1] in "+-" and not l.startswith(("+++", "---"))]
ok("B8.01", "disponibilidade: v12 = v11 fora versão, etapa e commit de referência (byte a byte depois de normalizar; 2 linhas mudam)",
   volta == d11 and len(dl) == 4, f"{len(dl)} linhas ±: " + " | ".join(l[:90] for l in dl))
ok("B8.02", "disponibilidade e MANIFEST citam o mesmo nome de commit ('Etapa 7c.7: pacote v12 com as decisões da 7c.6b') e o git log --grep 'Etapa 7c.7'",
   '"Etapa 7c.7: pacote v12 com as decisões da 7c.6b"' in d12 and 'git log --grep "Etapa 7c.7"' in d12
   and "'Etapa 7c.7: pacote v12 com as decisões da 7c.6b'" in L12[2])
lg11, lg12 = (A11 / f"legendas_figuras_{V11}.md").read_text(), (MS / "legendas_figuras.md").read_text()
ok("B8.03", "legendas: v12 = v11 fora o rótulo de versão (byte a byte depois de normalizar)", lg12.replace(V12, V11) == lg11,
   f"ocorrências do rótulo: {lg11.count(V11)} → {lg12.count(V12)}")

J11 = json.load(open(A11 / f"numeros_chave_{V11}.json"))
J12 = json.load(open(MS / f"numeros_chave_{V12}.json"))
CAMPOS = ["id", "valor_formatado", "valor_bruto", "descricao", "filtro", "arquivo", "script", "commit_registro", "commit_analise"]
dif_j = [(a["id"], c) for a, b in zip(J11, J12) for c in set(a) | set(b) if c != "commit_pacote" and a.get(c) != b.get(c)]
ok("B9.01", "números-chave: os 226 da v11 na v12, na mesma ordem, com todos os campos iguais exceto commit_pacote (valor bruto com tipo igual)",
   len(J11) == 226 and [i["id"] for i in J12[:226]] == [i["id"] for i in J11] and not dif_j
   and all(type(a["valor_bruto"]) is type(b["valor_bruto"]) for a, b in zip(J11, J12)) and set(J11[0]) == set(J12[0]),
   f"v11 {len(J11)}; v12 {len(J12)}; campos divergentes {dif_j[:3]}; campos {sorted(J12[0])}")
cp11, cp12 = Counter(i["commit_pacote"] for i in J11), Counter(i["commit_pacote"] for i in J12)
ok("B9.02", "commit_pacote: v11 = 8314417 (pai de b9d6272) em todos; v12 = dc9328d (HEAD ao gerar) em todos",
   cp11 == Counter({"8314417": 226}) and cp12 == Counter({HEAD: 228}) and git("rev-parse", "--short", "b9d6272^").strip() == "8314417",
   f"v11 {dict(cp11)}; v12 {dict(cp12)}")
nv = {i["id"]: i for i in J12[226:]}
ok("B9.03", "entram só n_regsaude_CE = 5 e n_regsaude_DF = 1, no fim, com origem tab_e7c7_01 e script etapa7c7_01; commit_registro e "
   "commit_analise vazios (ainda não estão em versão arquivada)",
   list(nv) == ["n_regsaude_CE", "n_regsaude_DF"] and nv["n_regsaude_CE"]["valor_bruto"] == 5 and nv["n_regsaude_DF"]["valor_bruto"] == 1
   and type(nv["n_regsaude_CE"]["valor_bruto"]) is int and [nv[k]["valor_formatado"] for k in nv] == ["5", "1"]
   and all(nv[k]["arquivo"] == "outputs/tables/tab_e7c7_01_regsaude_uf_v1_20261008.csv" and nv[k]["script"] == "scripts/etapa7c7_01_regsaude_uf.py"
           and nv[k]["filtro"] == f"uf={k[-2:]}" and not nv[k]["commit_registro"] and not nv[k]["commit_analise"] for k in nv),
   "; ".join(f"{k}: {v['valor_formatado']} — {v['descricao']}" for k, v in nv.items()))
m11, m12 = (A11 / f"numeros_chave_{V11}.md").read_text().splitlines(), (MS / f"numeros_chave_{V12}.md").read_text().splitlines()
rows11, rows12 = [l for l in m11 if l.startswith("| ") and not l.startswith(("| id ", "|---"))], [l for l in m12 if l.startswith("| ") and not l.startswith(("| id ", "|---"))]
cab11, cab12 = [l for l in m11 if not (l.startswith("| ") and l not in m11[:6])], [l for l in m12 if not (l.startswith("| ") and l not in m12[:6])]
hdr_ok = (m12[0] == m11[0].replace("7b–7c.6", "7b–7c.7") and m12[2] == m11[2].replace(V11, V12).replace("commit_pacote 8314417", f"commit_pacote {HEAD}")
          and m12[1] == m11[1] and m12[3:6] == m11[3:6])
ok("B9.04", "numeros_chave .md: cabeçalho igual fora etapa, versão e commit_pacote; 226 linhas da v11 idênticas; 2 linhas novas",
   hdr_ok and rows12[:226] == rows11 and len(rows12) == 228 and all(r.startswith(f"| {k} | ") for r, k in zip(rows12[226:], nv)),
   f"linhas da tabela v11 {len(rows11)}; v12 {len(rows12)}; cabeçalho ok {hdr_ok}")


def textos_v12():
    out = {}
    for s in ("tabelas", "suplementar"):
        for f in (MS / s).glob(f"*_{V12}.csv"):
            out[f"{s}/{f.name}"] = f.read_text()
    for f in [MS / "tabelas" / f"tabelas_principais_{V12}.xlsx", MS / "suplementar" / f"ESM_1_tables_S1_S6_{V12}.xlsx", SUB / "ESM_1.xlsx"]:
        out[str(f.relative_to(PROJ))] = "\n".join(str(v) for _, c in celulas(f) for v in c.values())
    D = docx.Document(MS / "tabelas" / f"tabelas_principais_{V12}.docx")
    out["docx"] = "\n".join([p.text for p in D.paragraphs] + [c.text for t in D.tables for r in t.rows for c in r.cells])
    for f in list((MS / "suplementar").glob(f"*_{V12}.pdf")) + sorted(SUB.glob("ESM_*.pdf")):
        out[str(f.relative_to(PROJ))] = " ".join(" ".join(txt_pdf(f)).split())
    for f in [MS / "MANIFEST.md", MS / "data_code_availability.md", MS / "legendas_figuras.md", MS / f"numeros_chave_{V12}.md", MS / f"numeros_chave_{V12}.json"]:
        out[f.name] = f.read_text()
    return out


TX = textos_v12()
oc = {k: v.count(FRASE) for k, v in TX.items() if FRASE in v}
oc11 = sum((A11 / "tabelas" / f"tabelas_principais_{V11}.xlsx").read_bytes().count(b"Joint Wald tests") for _ in [0]) + \
    sum(p.text.count(FRASE) for p in docx.Document(A11 / "tabelas" / f"tabelas_principais_{V11}.docx").paragraphs)
ok("B10.01", "a frase nova aparece só no rodapé da Tabela 4 (xlsx e docx das tabelas principais), uma vez em cada; nenhuma na v11",
   oc == {f"outputs/manuscrito/tabelas/tabelas_principais_{V12}.xlsx": 1, "docx": 1} and oc11 == 0, f"ocorrências {oc}; v11 {oc11}")
t4 = pd.read_csv(MS / "tabelas" / f"tab04_sensitivity_{V12}.csv", dtype=str).fillna("")
wcol = [c for c in t4.columns if "Wald" in c]
mi = t4[t4.Scenario.str.contains("imputation", case=False)]
ok("B10.02", "Tabela 4: a linha da imputação múltipla existe uma vez e as colunas de Wald dela são 'n.a.'",
   len(mi) == 1 and len(wcol) == 2 and all(mi.iloc[0][c] == "n.a." for c in wcol), f"{mi.Scenario.tolist()}; {[mi.iloc[0][c] for c in wcol] if len(mi) else ''}")
na_w = t4[(t4[wcol] == "n.a.").any(axis=1)].Scenario.tolist()
ok("B10.03", "Tabela 4 (informativo): outras linhas com Wald 'n.a.' — a frase nova só explica a da imputação múltipla", True,
   f"{len(na_w)} linhas com Wald n.a.: {na_w}")

fmi = {f: list(pd.read_csv(PROJ / "outputs/tables" / f, nrows=0).columns) for f in ["tab_e4_06_mi_m2_rubin_rs_v1_20261008.csv", "tab_e4_06_mi_rubin_rs_v1_20261008.csv"]}
s406 = (PROJ / "scripts/etapa4_06_imputacao_raca.py").read_text()
ok("B10.04", "imputação múltipla: Wald conjunto não foi calculado de fato (tabelas de origem _rs sem coluna de Wald/χ²; etapa4_06 sem Wald)",
   not any(re.search(r"wald|chi2|^p$", c, re.I) for cs in fmi.values() for c in cs) and not re.search(r"wald|chi2|wald_test", s406, re.I),
   "; ".join(f"{k}: {v}" for k, v in fmi.items()))

TER = PROJ / "docs/referencias/territorio_dez24"
rl = pd.read_csv(TER / "rl_municip_regsaud.csv", dtype=str)
uf_ = rl.CO_MUNICIP.str[:2]
ce, df_ = rl[uf_ == "23"].CO_REGSAUD.nunique(), rl[uf_ == "53"].CO_REGSAUD.nunique()
ok("B11.01", "recontagem própria em rl_municip_regsaud.csv: CE = 5 regiões de saúde, DF = 1", (ce, df_) == (5, 1),
   f"CE {ce} {sorted(rl[uf_ == '23'].CO_REGSAUD.unique())}; DF {df_} {rl[uf_ == '53'].values.tolist()}")
tn = pd.read_csv(PROJ / "outputs/tables/tab_e7c7_01_regsaude_uf_v1_20261008.csv", dtype={"cod_uf": str})
SIG = {"11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO", "21": "MA", "22": "PI", "23": "CE", "24": "RN",
       "25": "PB", "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP", "41": "PR", "42": "SC",
       "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF"}
eh_mun = ~rl.CO_MUNICIP.str.endswith("0000")
meu = []
for c, s in SIG.items():
    x = rl[uf_ == c]
    nr, nm = x.CO_REGSAUD.nunique(), int((~x.CO_MUNICIP.str.endswith("0000")).sum())
    meu.append((c, s, nr, nm, round(nm / nr, 1)))
meu.append(("", "Brasil", rl.CO_REGSAUD.nunique(), int(eh_mun.sum()), round(eh_mun.sum() / rl.CO_REGSAUD.nunique(), 1)))
deles = [(("" if pd.isna(r.cod_uf) else str(r.cod_uf)), r.uf, int(r.n_regioes_saude), int(r.n_municipios), float(r.municipios_por_regiao)) for r in tn.itertuples()]
ok("B11.02", "tabela nova tab_e7c7_01 = recálculo próprio, linha a linha (27 UFs + Brasil; regiões, municípios e razão)", deles == meu,
   f"{len(deles)} linhas; divergentes {[a for a, b in zip(deles, meu) if a != b][:3]}")
tnu = tn.set_index("uf")
ok("B11.03", "números-chave n_regsaude_CE/DF = células da tabela nova", int(tnu.n_regioes_saude["CE"]) == nv["n_regsaude_CE"]["valor_bruto"]
   and int(tnu.n_regioes_saude["DF"]) == nv["n_regsaude_DF"]["valor_bruto"])
tm = pd.read_csv(TER / "tb_municip.csv", dtype=str, sep=";")
ativos = tm[tm.CO_STATUS == "S"].groupby("SG_UF").size()
ok("B11.04", "checagem cruzada com tb_municip.csv: municípios ativos (CO_STATUS = S) por UF = n_municipios da tabela nova (27 UFs; Brasil 5,571)",
   all(int(ativos.get(s, -1)) == int(tnu.n_municipios[s]) for s in SIG.values()) and int(ativos.sum()) == int(tnu.n_municipios["Brasil"]) == 5571,
   f"ativos {int(ativos.sum())}; divergentes {[s for s in SIG.values() if int(ativos.get(s, -1)) != int(tnu.n_municipios[s])]}; "
   f"530000 em tb_municip: {'530000' in set(tm.CO_MUNICIP)}")
tr = pd.read_csv(TER / "tb_regsaud.csv", dtype=str)
usadas = set(rl.CO_REGSAUD)
nao_us = sorted(set(tr.REGSAUD) - usadas)
ok("B11.05", "checagem cruzada com tb_regsaud.csv: as 433 regiões do mapa estão lá; as que sobram são só do CE e do DF",
   usadas <= set(tr.REGSAUD) and len(usadas) == 433 and all(r[:2] in ("23", "53") for r in nao_us),
   f"tb_regsaud {len(tr)} regiões ({dict(tr.CO_STATUS.value_counts())}); sem município no mapa {len(nao_us)}: CE {sum(r[:2] == '23' for r in nao_us)}, "
   f"DF {sum(r[:2] == '53' for r in nao_us)}. Na tb_regsaud o CE tem {sum(tr.REGSAUD.str[:2] == '23')} e o DF {sum(tr.REGSAUD.str[:2] == '53')}, "
   "todas ATIVO: 5 e 1 valem para o mapa município → região")
ficha = (MS / "ficha_metodos_7c0_v1_20261009.md").read_text()
ok("B11.06", "ficha 7c.0: '3.2 sem CE/DF: 427' e 433 − (5 + 1) = 427; '5,572 municípios formam 433 regiões'",
   "3.2 sem CE/DF: 427" in ficha and 433 - (ce + df_) == 427 and "5,572 municípios formam 433 regiões" in ficha)
rs = pd.read_csv(PROJ / "outputs/tables/tab_e2_02_regsaude_resumo_v1_20261008.csv").iloc[0]
ok("B11.07", "tab_e2_02_regsaude_resumo: 5,572 códigos na tabela de mapeamento e 433 regiões = rl_municip_regsaud",
   int(rs.n_municipios_tabela) == len(rl) == 5572 and int(rs.n_regioes) == rl.CO_REGSAUD.nunique() == 433, rs.to_dict())
ok("B11.08", "530000 (DF ignorado) → região 53001: a tabela nova conta como região, não como município (DF: 1 região, 1 município; Brasil 5,571 = 5,572 − 1)",
   rl.set_index("CO_MUNICIP").CO_REGSAUD.get("530000") == "53001" and int(tnu.n_municipios["DF"]) == 1 and int(tnu.n_regioes_saude["DF"]) == 1
   and int(tnu.n_municipios["Brasil"]) == len(rl) - 1, f"códigos UF0000 na tabela: {rl[~eh_mun].values.tolist()}")

# =============================================================== C. código (estático)
v23 = git("show", f"{HEAD}:scripts/etapa2_03_indice_acesso.py")
n23 = (PROJ / "scripts/etapa2_03_indice_acesso.py").read_text()


def corpo(src):
    m = ast.parse(src)
    doc = ast.get_docstring(m)
    if doc is not None:
        m.body = m.body[1:]
    return ast.dump(m, include_attributes=False), doc


ok("C1.01", "etapa2_03: AST sem a docstring idêntica à de dc9328d (o código não muda)", corpo(v23)[0] == corpo(n23)[0] and v23 != n23)
dl23 = [(i, a, b) for i, (a, b) in enumerate(zip(v23.splitlines(), n23.splitlines()), 1) if a != b]
NOVA5 = ("               entre os registros com MESPRENAT válido (1–9; 99, nulo e qualquer outro código ficam fora; nascimentos sem região de "
         "saúde ficam fora do índice)")
ok("C1.02", "etapa2_03: só a linha 5 (docstring) muda, para o texto aprovado na decisão 3",
   len(v23.splitlines()) == len(n23.splitlines()) and len(dl23) == 1 and dl23[0][0] == 5 and dl23[0][2] == NOVA5, dl23)
ok("C1.03", "etapa2_03: a docstring nova bate com o código (válido = mes.between(1, 9); índice só com CO_REGSAUD não nulo)",
   'mes_valido": mes.between(1, 9)' in n23 and "g = d[d.CO_REGSAUD.notna()].groupby" in n23)


def diff_linhas(rel):
    a = git("show", f"{HEAD}:{rel}").splitlines()
    b = (PROJ / rel).read_text().splitlines()
    rem, add = [], []
    for l in difflib.unified_diff(a, b, lineterm="", n=0):
        if l.startswith(("---", "+++", "@@")):
            continue
        (rem if l[0] == "-" else add).append(l[1:])
    return rem, add


def confere(rel, esp_rem, esp_add):
    rem, add = diff_linhas(rel)
    falta_r = [m for m in esp_rem if sum(m in l for l in rem) != 1]
    falta_a = [m for m in esp_add if sum(m in l for l in add) != 1]
    sobra_r = [l for l in rem if not any(m in l for m in esp_rem)]
    sobra_a = [l for l in add if not any(m in l for m in esp_add)]
    return (not falta_r and not falta_a and not sobra_r and not sobra_a and len(rem) == len(esp_rem) and len(add) == len(esp_add),
            f"-{len(rem)} +{len(add)}; marcadores sem par: {falta_r + falta_a}; linhas fora do revisado: {(sobra_r + sobra_a)[:3]}")


c_ = confere("scripts/etapa7b_lib.py",
             ['V = "v11_20261009"', 'md = ["# Key numbers (Etapas 7b–7c.6)"'],
             ['V = "v12_20261013"               # versão/data do pacote (v12 = Etapa 7c.7', "# 7c.7: regiões de saúde e municípios por UF na base territorial",
              '"tab_e7c7_01_regsaude_uf": "scripts/etapa7c7_01_regsaude_uf.py",', 'md = ["# Key numbers (Etapas 7b–7c.7)"'])
ok("C2.01", "lib: diff = versão do pacote (V), entrada nova no SRC (tab_e7c7_01) e título do .md dos números-chave; nada mais", *c_)
FR01 = "access sample, combined with Rubin's rules. Joint Wald tests were not computed for the multiple-imputation analysis. Live-birth bounds"
c_ = confere("scripts/etapa7b_01_tabelas.py",
             ["access sample, combined with Rubin's rules. Live-birth bounds"],
             [FR01, "# 7c.7: regiões de saúde de CE e DF", 'rsu = B.rd("tab_e7c7_01_regsaude_uf").set_index("uf")',
              'for uf_, nome_ in (("CE", "Ceará"), ("DF", "Federal District")):', 'R.add(f"n_regsaude_{uf_}", int(rsu.n_regioes_saude[uf_])',
              'f"Health regions in {nome_} (DATASUS territorial base, December 2024)", f"uf={uf_}")'])
r01, a01 = diff_linhas("scripts/etapa7b_01_tabelas.py")
ok("C2.02", "01: diff = frase no rodapé da Tabela 4 (só inserção) e o bloco dos 2 números-chave novos; nada mais",
   c_[0] and a01[0] == r01[0].replace(ANTES, ANTES + " " + FRASE), c_[1])
c_ = confere("scripts/etapa7b_02_suplementar.py",
             ['ETAPA = "Etapa 7c.6: auditoria independente', 'txt = f"""# Data and code availability (draft, package {B.V}, Etapa 7c.6)',
              '(its hash is given by `git log --grep "Etapa 7c.6"`'],
             ['ETAPA = "Etapa 7c.7: pacote v12 com as decisões da 7c.6b"', 'txt = f"""# Data and code availability (draft, package {B.V}, Etapa 7c.7)',
              '(its hash is given by `git log --grep "Etapa 7c.7"`', "# 7c.7: os PDFs do Chrome saem com com.apple.quarantine",
              'subprocess.run(["dot_clean", "-m", str(B.SUPD)], check=True)', 'if list(B.SUPD.glob("._*")):', 'raise RuntimeError(f"._* em {B.SUPD}")'])
s02 = (PROJ / "scripts/etapa7b_02_suplementar.py").read_text()
m02 = ast.parse(s02)
imp_sub = any(isinstance(n, (ast.Import,)) and any(a.name == "subprocess" for a in n.names) for n in m02.body)
pos_dc, pos_dca = s02.index('subprocess.run(["dot_clean"'), s02.index('(B.MS / "data_code_availability.md").write_text(txt)')
ultimos = [l for l in s02.splitlines() if l.strip()][-6:]
ok("C2.03", "02: diff = etapa/commit de referência da disponibilidade e o dot_clean -m em suplementar/ no fim (com raise, não assert); "
   "subprocess importado; dot_clean depois da última gravação", c_[0] and imp_sub and pos_dc > pos_dca and "dot_clean" in " ".join(ultimos),
   c_[1] + f"; import subprocess {imp_sub}")
c_ = confere("scripts/etapa7b_04_submissao.py",
             ['linhas = [f"# MANIFEST — pacote de resultados (Etapas 7b–7c.6, {V})", "",',
              "\"'Etapa 7c.6: auditoria independente 7c.5/7c.5b, RECORD e rastreabilidade'). Nenhuma análise nova",
              '"os campos commit_pacote (antigo commit), commit_registro e commit_analise nos números-chave. "'],
             ['linhas = [f"# MANIFEST — pacote de resultados (Etapas 7b–7c.7, {V})", "",',
              "\"'Etapa 7c.7: pacote v12 com as decisões da 7c.6b'). Nenhuma análise nova",
              '"os campos commit_pacote (antigo commit), commit_registro e commit_analise nos números-chave; v12 = v11 com o rodapé da Tabela 4 "',
              '"dizendo que os testes de Wald conjuntos não foram calculados na imputação múltipla, os números-chave n_regsaude_CE e "',
              '"n_regsaude_DF (regiões de saúde na base territorial, tab_e7c7_01_regsaude_uf) e suplementar/ sem arquivos ._* (dot_clean no 02). "'])
ok("C2.04", "04: diff = título, nome do commit da 7c.7 e a frase da v12 no topo do MANIFEST; nada mais", *c_)

ck0 = git("show", f"{HEAD}:scripts/etapa7b_checa.py").splitlines()
ck1 = (PROJ / "scripts/etapa7b_checa.py").read_text().splitlines()
i_hdr = next(i for i, l in enumerate(ck1) if l.startswith("A11, V11 = "))
i9a = next(i for i, l in enumerate(ck1) if l.startswith("# ---- 9a."))
i9g = next(i for i, l in enumerate(ck1) if l.startswith("# ---- 9g."))
i9h = next(i for i, l in enumerate(ck1) if l.startswith("# ---- 9h."))
fim9h = next(i for i, l in enumerate(ck1) if i > i9h and l.startswith("# sem 'ICR' e sem 'Parda'"))
i9g0 = next(i for i, l in enumerate(ck0) if l.startswith("# ---- 9g."))
fim9g0 = next(i for i, l in enumerate(ck0) if i > i9g0 and l.startswith("# sem 'ICR' e sem 'Parda'"))
sm = difflib.SequenceMatcher(None, ck0, ck1, autojunk=False)
fora = []
for tag, a1, a2, b1, b2 in sm.get_opcodes():
    if tag == "equal":
        continue
    rem_, add_ = ck0[a1:a2], ck1[b1:b2]
    no_9g_old = all(i9g0 <= i < fim9g0 for i in range(a1, a2))
    no_9gh_new = all(i9g <= i < fim9h for i in range(b1, b2))
    cabec = not rem_ and all(i_hdr <= i < i9a for i in range(b1, b2))      # A11/V11, J11l/J11 e pacote_esperado, antes do 9a
    pedidos = rem_ and add_ and all('"Etapa 7c.6",' in l for l in rem_) and all('"Etapa 7c.7",' in l for l in add_)
    e23 = not rem_ and all(("23" in l or "7c.7 etapa2_03" in l or "idêntico ao do commit dc9328d" in l or "nascimentos sem região" in l) for l in add_)
    if not ((no_9g_old or not rem_) and (no_9gh_new or not add_) or cabec or pedidos or e23):
        fora.append((tag, a1 + 1, b1 + 1, (rem_ + add_)[:1]))
n9h = sum(1 for l in ck1[i9h:fim9h] if l.startswith("ok(")) + sum(1 for l in ck1[fim9h:] if l.startswith('ok("7c.7'))
ok("C2.05", "checa: toda mudança cai em A11/J11/pacote_esperado, no 9g re-apontado, no 9h novo, no 'Etapa 7c.7' da disponibilidade ou na "
   "checagem do etapa2_03; o 9h tem 13 verificações", not fora and n9h == 13,
   f"blocos fora: {fora[:3]}; verificações 7c.7: {n9h}; diff -{sum(a2 - a1 for t, a1, a2, _, _ in sm.get_opcodes() if t != 'equal')} "
   f"+{sum(b2 - b1 for t, _, _, b1, b2 in sm.get_opcodes() if t != 'equal')}")
b9g = "\n".join(ck1[i9g:i9h])
atuais = {k: len(re.findall(p, b9g)) for k, p in {"B.V": r"B\.V\b", "B.TABD": r"B\.TABD", "B.SUPD": r"B\.SUPD", "B.SUB": r"B\.SUB\b",
                                                  "Jcur": r"\bJcur\b", "J (lista atual)": r"\bin J\b|\bfor i in J\)", "B.MS.joinpath": r"B\.MS\.joinpath",
                                                  "B.FIGD": r"B\.FIGD"}.items()}
uso_J = [l.strip()[:80] for l in ck1[i9g:i9h] if re.search(r"\bin J\b", l)]
ok("C2.06", "9g re-apontado (estático): nenhuma referência a arquivos da versão atual (B.V, B.TABD, B.SUPD, B.SUB, B.FIGD, Jcur, "
   "disponibilidade da raiz); o J atual só no teste sintético do congelamento",
   all(v == 0 for k, v in atuais.items() if k != "J (lista atual)") and all("it0 = next(i for i in J" in u for u in uso_J),
   f"{atuais}; usos de J: {uso_J}")
ok("C2.07", "9g: compara A10 × A11 em números-chave (J11l), CSVs (compara(A10, …, A11 …)), xlsx, disponibilidade e Submissao/",
   "compara(A10, V10, (A11 / \"tabelas\", A11 / \"suplementar\"), V11" in b9g and "J11l" in b9g and "A11 / f\"data_code_availability_{V11}.md\"" in b9g
   and 'px(A11 / "Submissao" / f"Fig{k}.tif") == px(A10 / "Submissao" / f"Fig{k}.tif")' in b9g
   and 'A11 / "Submissao" / "ESM_1.xlsx"' in b9g and "pacote_esperado(V11)" in b9g)
s7c7 = (PROJ / "scripts/etapa7c7_01_regsaude_uf.py").read_text()
m7 = ast.parse(s7c7)
chamadas = [ast.unparse(n.func) for n in ast.walk(m7) if isinstance(n, ast.Call)]
leituras = [ast.unparse(n) for n in ast.walk(m7) if isinstance(n, ast.Call) and ast.unparse(n.func) in ("pd.read_csv", "open", "pd.read_parquet")]
escritas = [ast.unparse(n) for n in ast.walk(m7) if isinstance(n, ast.Call) and ast.unparse(n.func).endswith((".to_csv", "write_text", ".to_excel"))]
ok("C4.01", "etapa7c7_01 (estático): uma leitura (rl_municip_regsaud.csv da base territorial) e uma gravação (L.out_name(tab_e7c7_01)); "
   "sem parquet, sem data/", len(leituras) == 1 and "rl_municip_regsaud.csv" in leituras[0] and len(escritas) == 1
   and "tab_e7c7_01_regsaude_uf" in escritas[0] and "parquet" not in s7c7 and "PROC" not in s7c7 and "RAW" not in s7c7,
   f"leituras {leituras}; gravações {escritas}")
lei1 = git("show", f"{HEAD}:scripts/resumos/LEIAME.md").splitlines()
lei2 = (PROJ / "scripts/resumos/LEIAME.md").read_text().splitlines()
dlei = [(i, a, b) for i, (a, b) in enumerate(zip(lei1, lei2), 1) if a != b]
s5b = (PROJ / "scripts/resumos/etapa7c5b_01_resumo.py").read_text()
s6 = (PROJ / "scripts/resumos/etapa7c6_01_resumo.py").read_text()
s6b = (PROJ / "scripts/resumos/etapa7c6b_01_resumo.py").read_text()
saf = (PROJ / "scripts/etapa7c6_02_audita_final.py").read_text().splitlines()
ok("C6.01", "LEIAME: só 3 linhas mudam (versão do pacote nos geradores, leitura do disco da 7c.6b, checa)",
   len(lei1) == len(lei2) and [i for i, _, _ in dlei] == [6, 9, 12], [i for i, _, _ in dlei])
ok("C6.02", "LEIAME (estático): 7c5b_01 e 7c6_01 fixam V = v10/v11 e leem o pacote na raiz de outputs/manuscrito; 7c6b_01 não lê o pacote",
   'V = "v10_20261009"' in s5b and 'B.TABD / f"tabelas_principais_{V}.xlsx"' in s5b and 'V = "v11_20261009"' in s6
   and 'B.MS / f"numeros_chave_{V}.json"' in s6 and not re.search(r"numeros_chave|tabelas_principais|suplementar|Submissao|etapa7b_lib|_arquivo_v", s6b),
   "7c6b_01 lê só _resumo7c6b_texto, audita_final_7c6 e o comparacao do auditor 7c.6 final")
ok("C6.03", "LEIAME (estático): a autoauditoria da 7c.6b lê numeros_chave_v11 na raiz de outputs/manuscrito logo no começo (linha 53)",
   saf[33].strip() == 'V, V10 = "v11_20261009", "v10_20261009"' and saf[52].strip() == 'J = json.load(open(MS / f"numeros_chave_{V}.json"))', saf[52].strip())

# =============================================================== C5. autoauditoria scripts/etapa7c7_02_audita.py (revisão do código)
sa = (PROJ / "scripts/etapa7c7_02_audita.py").read_text()
ids_sa = re.findall(r'^ok\("([A-D]\d\.\d\d)"', sa, re.M)
C5 = [  # (item, mede o que diz?, o que não pega)
    ("A0.01", True, "aceita HEAD = dc9328d ou QUALQUER descendente: não vê commit a mais, remoto nem tag"),
    ("A1.01", False, "'novos só os da 7c.7' é uma regex que aceita qualquer arquivo em _arquivo_v11/, docs/referencias/ e audit_independente/etapa7c7/; "
                     "não olha ignorados (outputs/tables, logs); git status sem GIT_OPTIONAL_LOCKS=0 pode regravar o índice"),
    ("A1.02", True, "bytes dos 38 = dc9328d; não confere o blob no índice (stage)"),
    ("A1.03", True, "ok; não confere que a _arquivo_v10 foi feita do mesmo jeito"),
    ("A2.01", True, "rglob só em 5 pastas: um ._* na raiz do projeto passaria; não confere que os 36 da lista sumiram (só que não há nenhum)"),
    ("A2.02", True, "ok"),
    ("B1.01", True, "não confere ordem nem tipo do valor bruto (5 == 5.0 passa)"),
    ("B1.02", True, "ok"),
    ("B2.01", True, "ok (mesma recontagem do checa: nunique por prefixo do código)"),
    ("B2.02", True, "ok"),
    ("B2.03", True, "só totais: não confere os valores por UF (regiões, municípios, razão) nem cruza com tb_municip/tb_regsaud; não nota que a "
                    "tb_regsaud lista 25 regiões no CE e 8 no DF"),
    ("B3.01", True, "ok"),
    ("B4.01", True, "ok (todas as células); não confere ordem das abas"),
    ("B4.02", True, "ok; Submissao/ESM_1 por células, não por bytes"),
    ("B4.03", True, "ok; não lista as outras 5 linhas com Wald n.a."),
    ("B5.01", True, "texto de parágrafos e células; não vê formatação (runs/itálico) nem partes do zip"),
    ("B6.01", True, "só texto: a imagem do ESM_4 e a renderização dos PDFs não são conferidas"),
    ("B7.01", True, "pixels/modo/dpi, sem compressão do TIFF; Submissao/Fig = dc9328d, não = figuras v12"),
    ("B8.01", True, "MD5 normalizado: não diz quais MD5 mudaram (cobre-se por B3/B7)"),
    ("B8.02", True, "não confere se o MANIFEST lista todos os arquivos da pasta (o próprio audita_7c7 fica de fora)"),
    ("B8.03", True, "ok"),
    ("C1.01", True, "ok"),
    ("C2.01", False, "marcadores frouxos e sem contagem: qualquer linha nova que contenha 'Etapa 7c.7', 'dot_clean' ou 'tab_e7c7_01_regsaude_uf' passa; "
                     "não cobre o LEIAME; não confere que a mudança do 01 é só inserção"),
    ("C3.01", True, "lê o CSV do próprio checa (não é independente); não testa se as 13 novas falham quando devem (sem mutação)"),
    ("C3.02", True, "olha só linhas removidas: acréscimo fora do 9g/9h passaria; o ramo 'depois do commit' do pacote_esperado não é exercitado"),
    ("C4.01", True, "estático; não reproduz a tabela"),
    ("C5.01", False, "só procura 3 frases no LEIAME; não testa que a autoauditoria da 7c.6b e os geradores param, nem o checa depois do commit"),
    ("D1.01", True, "só presença: não confere ordem, mtimes, nem que o checa rodou 2 vezes com o script editado entre elas (e o 7c7_01 também)"),
]
ok("C5.00", "autoauditoria: os 28 itens revisados aqui são todos os do script", [i for i, _, _ in C5] == ids_sa, f"{len(ids_sa)} itens no script")
for i, m, g in C5:
    ok(f"C5.{i}", f"autoauditoria {i}: mede o que diz medir", m, g)
ok("C5.99", "autoauditoria: blocos ausentes (não pega)", False,
   "nada de microdados/git no que vai para o commit (E); remoto e tag; ignorados criados depois de dc9328d; MANIFEST incompleto; "
   "mutação do checa; LEIAME e pacote_esperado testados de fato; cruzamento com tb_municip/tb_regsaud; ._* na raiz")

# =============================================================== resultados do sandbox (C3, C4, C6 dinâmicos)
SB = json.load(open(OUTD / "sandbox_7c7_v1_20261013.json"))
base = SB.get("linha_de_base", {})
blin = dict(base.get("linhas", []))
ok("C3.00", "sandbox: cópia sem data/, índice = índice real, HEAD dc9328d; checa (cópia, assert desligado) na linha de base: tudo OK",
   SB.get("base", {}).get("indice_igual") and SB["base"]["head"] == HEAD and base.get("rc") == 0 and blin and all(blin.values()),
   f"{SB.get('base')}; {sum(blin.values())}/{len(blin)} OK; rc {base.get('rc')}; {base.get('seg')} s; sandbox apagado {SB.get('sandbox_apagado', '?')}")
n7c7 = [k for k in blin if k.startswith("7c.7")]
n7c6 = [k for k in blin if k.startswith("7c.6")]
ok("C3.01", "checa na linha de base: 13 verificações '7c.7' (12 do 9h + etapa2_03) e as do 9g '7c.6'", len(n7c7) == 13,
   f"7c.7: {len(n7c7)}; 7c.6: {len(n7c6)}; total {len(blin)}")
for mid, r in SB.get("mutacoes", {}).items():
    lin = dict(r.get("linhas", []))
    alvo = [k for k in lin if k.startswith(r["alvo"])]
    vir = sorted(k for k in lin if blin.get(k) and not lin[k])
    nome = "9g" if r["alvo"].startswith("7c.6") else "9h"
    pegou = bool(alvo) and all(not lin[k] for k in alvo)
    extra_ok = True
    if nome == "9h" and mid not in ("M04",):
        extra_ok = not any(k.startswith("7c.6") for k in vir)          # mutação só na v12: o 9g não pode mudar
    ok(f"C3.{mid}", f"mutação {mid} ({nome}): {r['desc']} → a verificação '{r['alvo']}' falha" + (" e nenhuma do 9g muda" if nome == "9h" and mid != "M04" else ""),
       r.get("rc") == 0 and pegou and extra_ok, f"falharam {len(vir)}: {[v[:70] for v in vir][:6]}; rc {r.get('rc')}; {r.get('erro', '')[:200]}")
C = SB.get("commits", {})
ok("C3.20", "pacote_esperado no repositório real (só git log/rev-parse): v11 → 8314417 (pai de b9d6272, = commit_pacote da v11); "
   "v12 sem commit → HEAD atual (dc9328d)", C.get("real_v11") == "8314417" and C.get("real_v12") == HEAD == C.get("head_real"),
   f"v11 {C.get('real_v11')}; v12 {C.get('real_v12')}")
s1 = C.get("S1", {})
s1l = dict(s1.get("checa", {}).get("linhas", []))
ok("C3.21", "clone descartável, commit único da etapa simulado: pacote_esperado(v12) = pai do commit = dc9328d = commit_pacote do JSON; "
   "a regra antiga (= HEAD atual) falharia; o checa inteiro passa depois do commit",
   s1.get("esp_v12") == HEAD == s1.get("pai") and s1.get("commit_pacote_json") == [HEAD] and s1.get("regra_antiga_passaria") is False
   and s1.get("esp_v11") == "8314417" and s1l and all(s1l.values()),
   f"HEAD simulado {s1.get('head')}; esp v12 {s1.get('esp_v12')}; esp v11 {s1.get('esp_v11')}; regra antiga passaria {s1.get('regra_antiga_passaria')}; "
   f"checa {sum(s1l.values())}/{len(s1l)}")
s2 = C.get("S2", {})
ok("C3.22", "clone descartável, docstring do etapa2_03 num commit anterior (plano antigo): pacote_esperado(v12) vira esse commit e o 9h "
   "commit_pacote falha — por isso tudo tem de ir num commit só", s2.get("esp_v12") not in (None, HEAD)
   and any(x.startswith("7c.7 commit_pacote") for x in s2.get("checa_falhas", [])),
   f"esp v12 {s2.get('esp_v12')}; falhas {[x[:60] for x in s2.get('checa_falhas', [])]}")
ok("C3.23", "antes do commit (clone com HEAD dc9328d): pacote_esperado(v12) = HEAD atual", C.get("S0_v12") == HEAD, C.get("S0_v12"))
H = SB.get("hook_7c7_01", {})
ev = H.get("eventos", [])
le = sorted({e[1] for e in ev if e[0] == "open" and (len(e) < 3 or "r" in str(e[2]) and "w" not in str(e[2]) and "a" not in str(e[2]))})
gr = sorted({e[1] for e in ev if e[0] == "open" and len(e) > 2 and any(m in str(e[2]) for m in ("w", "a", "x", "+"))})
outros = sorted({(e[0], e[1]) for e in ev if e[0] != "open"})
ok("C4.02", "etapa7c7_01 (dinâmico, audit hook na cópia): lê só rl_municip_regsaud.csv; grava só a tabela nova (e a linha do log)",
   H.get("rc") == 0 and le == ["docs/referencias/territorio_dez24/rl_municip_regsaud.csv"]
   and set(gr) == {"outputs/tables/tab_e7c7_01_regsaude_uf_v1_20261008.csv", "outputs/logs/etapa7c7_20261008.log"},
   f"leituras {le}; gravações {gr}; outros eventos {outros[:6]}")
ok("C4.03", "etapa7c7_01 reproduz a tabela real byte a byte", H.get("tabela_reproduzida") is True)
ok("C4.04", "tabela nova com o carimbo _v1_20261008 (padrão de outputs/tables), criada em 2026-10-13: só convenção de nome",
   (PROJ / "outputs/tables/tab_e7c7_01_regsaude_uf_v1_20261008.csv").exists(),
   f"mtime {hora((PROJ / 'outputs/tables/tab_e7c7_01_regsaude_uf_v1_20261008.csv').stat().st_mtime)}")
RP = SB.get("reproducao", {})
cmp_ = RP.get("comparacoes", {})
ok("C4.05", "reprodução (cópias do 01 e do 03 no sandbox): JSON, .md dos números-chave, CSVs e xlsx/docx das tabelas, legendas e figuras = v12",
   all(v.get("rc") == 0 for v in RP.get("execucoes", {}).values()) and cmp_ and all(cmp_.values()),
   f"{sum(cmp_.values())}/{len(cmp_)} iguais; diferentes {[k for k, v in cmp_.items() if not v]}; rc {[v.get('rc') for v in RP.get('execucoes', {}).values()]}")
LE = SB.get("leiame", {})
af, r6, r5, r6b = LE.get("audita_final_7c6b", {}), LE.get("resumo_7c6", {}), LE.get("resumo_7c5b", {}), LE.get("resumo_7c6b", {})
ok("C6.04", "LEIAME (dinâmico): a autoauditoria da 7c.6b (cópia, saída desviada) para logo no começo, ao abrir numeros_chave_v11 na raiz",
   af.get("rc") not in (0, None) and "FileNotFoundError" in af.get("ultima", "") and f"numeros_chave_{V11}.json" in af.get("ultima", "")
   and "line 53" in af.get("linha_erro", "") and not [n for n in af.get("novos", []) if n.startswith("_saida_auditor")],
   f"{af.get('linha_erro')}; {af.get('ultima', '')[:160]}")
ok("C6.05", "LEIAME (dinâmico): o resumos/etapa7c6_01 para ao abrir numeros_chave_v11 na raiz; o 7c5b_01 para ao abrir arquivo da v10 na raiz",
   "FileNotFoundError" in r6.get("ultima", "") and f"numeros_chave_{V11}.json" in r6.get("ultima", "") and "FileNotFoundError" in r5.get("ultima", "")
   and V10 in r5.get("ultima", ""), f"7c6_01: {r6.get('linha_erro')} {r6.get('ultima', '')[-90:]}; 7c5b_01: {r5.get('linha_erro')} {r5.get('ultima', '')[-90:]}")
ok("C6.06", "LEIAME (dinâmico): o resumos/etapa7c6b_01 não lê o pacote e continua rodando; reproduz o RESUMO 7c.6b de dc9328d byte a byte",
   r6b.get("rc") == 0 and r6b.get("igual_commitado") is True, f"rc {r6b.get('rc')}; igual {r6b.get('igual_commitado')}; {r6b.get('ultima', '')[:120]}")

# =============================================================== D. logs (horários e nomes; conteúdo do checa fica para depois)
RX = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] \[([^\]]+)\] ?(.*)$")
ev_ = []
for f in sorted((PROJ / "outputs/logs").glob("*.log")):
    for l in f.read_text(errors="replace").splitlines():
        m = RX.match(l)
        if m and m.group(1).startswith("2026-10-13"):
            # do checa só se guarda se a linha é a 1ª verificação (início de uma execução); o resultado não é lido nesta rodada
            ev_.append((m.group(1), m.group(2), f.name, m.group(3) if m.group(2) != "7b_checa" else
                        ("INICIO" if "números-chave = arquivo de origem" in m.group(3) else "")))
ev_ = sorted(ev_, key=lambda e: e[0])
corr = []
for t, n, f, msg in ev_:
    if corr and corr[-1][1] == n and n == "7b_checa" and msg != "INICIO":
        corr[-1][3] = t
        corr[-1][4] += 1
    elif corr and corr[-1][1] == n and n == "7c7_01_regsaude_uf" and t == corr[-1][3]:
        corr[-1][4] += 1
    else:
        corr.append([t, n, f, t, 1, msg])
seq = [(c[0][11:], c[1], c[3][11:], c[4]) for c in corr if c[0] > "2026-10-13 10:21"]
nomes_seq = [c[1] for c in seq]
ok("D1.01", "logs de 2026-10-13 depois de dc9328d: 7c7_01, 01, 02, 03, 04, checa, 04 — nesta ordem (o 7c7_01 e o checa aparecem 2 vezes)",
   [n for i, n in enumerate(nomes_seq) if i == 0 or n != nomes_seq[i - 1]] == ["7c7_01_regsaude_uf", "7b_01_tabelas", "7b_02_suplementar",
                                                                                "7b_03_figuras", "7b_04_submissao", "7b_checa", "7b_04_submissao"],
   "; ".join(f"{a}–{c} {b} ({d} linhas)" for a, b, c, d in seq))
st = lambda p: (PROJ / p).stat().st_mtime
T = lambda s: datetime.strptime(f"2026-10-13 {s}", "%Y-%m-%d %H:%M:%S").timestamp()
fim = {c[1]: [] for c in corr}
for c in corr:
    fim[c[1]].append((T(c[0][11:]), T(c[3][11:])))
chk_runs = fim.get("7b_checa", [])
mt = {
    "tabela 7c7_01": st("outputs/tables/tab_e7c7_01_regsaude_uf_v1_20261008.csv"),
    "_arquivo_v11 (cópias)": max(st(f"outputs/manuscrito/{k}") for k in COP),
    "tabelas v12 + JSON": max([st(f"outputs/manuscrito/tabelas/{x.name}") for x in (MS / "tabelas").iterdir()] + [st(f"outputs/manuscrito/numeros_chave_{V12}.json")]),
    "suplementar v12 (fora S9) + disponibilidade": max([x.stat().st_mtime for x in (MS / "suplementar").iterdir() if not x.name.startswith("S9")] + [st("outputs/manuscrito/data_code_availability.md")]),
    "figuras v12 + S9 + legendas": max([x.stat().st_mtime for x in (MS / "figuras").iterdir()] + [x.stat().st_mtime for x in (MS / "suplementar").glob("S9*")] + [st("outputs/manuscrito/legendas_figuras.md")]),
    "checa CSV": st(f"outputs/manuscrito/checa_7b_{V12}.csv"),
    "ESM_4 + MANIFEST": max(st("Submissao/ESM_4.pdf"), st("outputs/manuscrito/MANIFEST.md")),
    "pastas dos ._* (lixeira)": max((PROJ / p).parent.stat().st_mtime for p in l36),
}
f01, f02, f03 = fim["7b_01_tabelas"][-1][1], fim["7b_02_suplementar"][-1][1], fim["7b_03_figuras"][-1][1]
f04a, f04b = fim["7b_04_submissao"][0][1], fim["7b_04_submissao"][-1][1]
coer = {"7c7_01 → tabela": abs(mt["tabela 7c7_01"] - fim["7c7_01_regsaude_uf"][-1][1]) <= 2,
        "cópias v11 antes do 01": mt["_arquivo_v11 (cópias)"] < f01,
        "tabelas/JSON até o fim do 01": f01 - 60 <= mt["tabelas v12 + JSON"] <= f01 + 1,
        "suplementar até o fim do 02": f01 < mt["suplementar v12 (fora S9) + disponibilidade"] <= f02 + 1,
        "figuras até o fim do 03": f02 < mt["figuras v12 + S9 + legendas"] <= f03 + 1,
        "lixeira entre o 1º 04 e o checa": f04a < mt["pastas dos ._* (lixeira)"] < chk_runs[0][0],
        "checa CSV no fim do último checa": abs(mt["checa CSV"] - chk_runs[-1][1]) <= 2,
        "ESM_4/MANIFEST no último 04": abs(mt["ESM_4 + MANIFEST"] - f04b) <= 2}
ok("D1.02", "mtimes coerentes com os logs (tabela nova, cópias da v11, tabelas, suplementar, figuras, lixeira, checa, 2º 04)", all(coer.values()),
   "; ".join(f"{k}: {v}" for k, v in coer.items()) + " | " + "; ".join(f"{k} {hora(v)[11:]}" for k, v in mt.items()))
SCR = {s: st(f"scripts/{s}") for s in ["etapa7b_lib.py", "etapa7b_01_tabelas.py", "etapa7b_02_suplementar.py", "etapa7b_04_submissao.py",
                                        "etapa2_03_indice_acesso.py", "etapa7b_checa.py", "etapa7c7_01_regsaude_uf.py", "etapa7c7_02_audita.py"]}
ok("D1.03", "scripts do pacote (lib, 01, 02, 04) e etapa2_03 editados antes do 01; etapa7c7_01 antes da execução que gerou a tabela",
   max(SCR[s] for s in ["etapa7b_lib.py", "etapa7b_01_tabelas.py", "etapa7b_02_suplementar.py", "etapa7b_04_submissao.py", "etapa2_03_indice_acesso.py"])
   < f01 - 10 and SCR["etapa7c7_01_regsaude_uf.py"] < fim["7c7_01_regsaude_uf"][-1][0],
   "; ".join(f"{k} {hora(v)[11:]}" for k, v in SCR.items()))
ok("D1.04", "o checa rodou uma vez só, com a versão final do script", len(chk_runs) == 1 and SCR["etapa7b_checa.py"] < chk_runs[0][0],
   f"execuções do checa: {[(hora(a)[11:], hora(b)[11:]) for a, b in chk_runs]}; checa editado às {hora(SCR['etapa7b_checa.py'])[11:]} "
   "(entre a 1ª, interrompida, e a 2ª)")
r71 = fim.get("7c7_01_regsaude_uf", [])
ok("D1.05", "etapa7c7_01: a tabela em disco vem da última execução, com a versão final do script (editado antes dela)",
   SCR["etapa7c7_01_regsaude_uf.py"] < r71[-1][0] and abs(mt["tabela 7c7_01"] - r71[-1][1]) <= 2,
   f"execuções {[(hora(a)[11:], hora(b)[11:]) for a, b in r71]}; script editado {hora(SCR['etapa7c7_01_regsaude_uf.py'])[11:]}; linhas: "
   + " | ".join(f"{c[0][11:]} {c[5][:110]}" for c in corr if c[1] == "7c7_01_regsaude_uf"))
p01 = [c[5] for c in corr if c[1].startswith("7b_0")]
ok("D1.06", "conteúdo das linhas do pacote no log (01–04): sem erro; o 01 registra 228 números-chave ou equivalente", not any("Traceback" in x or "Error" in x for x in p01),
   " | ".join(x[:140] for x in p01))
antes = [(c[0][11:], c[1]) for c in corr if c[0] <= "2026-10-13 10:21"]
ok("D1.07", "entradas de 2026-10-13 até 10:21 são da 7c.6b (geradores de RESUMO), não da 7c.7", all(n.startswith(("7c6", "7c6b")) for _, n in antes),
   f"{len(antes)} entradas; última {antes[-1] if antes else '-'} (commit dc9328d às {hora(TCOMMIT)[11:]})")

ta = st("outputs/manuscrito/audita_7c7_v1_20261013.csv")
ok("D1.08", "autoauditoria (etapa7c7_02): CSV gravado depois da última edição do script e depois do último 04 (por isso fora do MANIFEST, B7.05)",
   SCR["etapa7c7_02_audita.py"] <= ta and ta > f04b, f"script {hora(SCR['etapa7c7_02_audita.py'])[11:]}; CSV {hora(ta)[11:]}; último 04 {hora(f04b)[11:]}")

# =============================================================== E. microdados e git
para_commit = sorted(set(DEST.values()) | M_ESP | set(untr))
ID_RX = re.compile(r"^(DTNASC|HORANASC|NUMERODN|NUMERODO|CODESTAB|DTOBITO|DTNASCMAE|DTULTMENST|CNS|CPF|NUMEROLOTE|DTCADASTRO|DTRECEBIM|CODMUNRES|CODMUNNASC)$", re.I)
ruim_nome = [p for p in para_commit if p.startswith("data/") or re.search(r"\.(parquet|dbc|dbf|csv\.gz|feather|rds|sav|dta)$", p)
             or Path(p).name.startswith("._") or Path(p).name == ".DS_Store"]
ok("E1.01", "o que iria para o commit (stage + modificados + não rastreados): nada em data/, nenhum parquet/dbc/dbf/rds, nenhum ._* ou .DS_Store",
   not ruim_nome, f"{len(para_commit)} arquivos ({sum(p.startswith('docs/referencias/') for p in para_commit)} de docs/referencias); suspeitos {ruim_nome[:5]}")
susp, maxl = [], (None, 0)
for p in para_commit:
    if p.endswith(".csv") and p != "outputs/manuscrito/audita_7c7_v1_20261013.csv" and not p.startswith("docs/referencias/") and (PROJ / p).exists():
        try:
            h = pd.read_csv(PROJ / p, nrows=0, sep=None, engine="python").columns
        except UnicodeDecodeError:
            h = pd.read_csv(PROJ / p, nrows=0, sep=None, engine="python", encoding="latin-1").columns
        n = sum(1 for _ in open(PROJ / p, errors="ignore")) - 1
        if n > maxl[1]:
            maxl = (p, n)
        if any(ID_RX.match(str(c).strip()) for c in h) or n > 5000:
            susp.append((p, n))
ok("E1.02", "CSVs da etapa que iriam para o commit (fora docs/referencias, já triados na 7c.6; o da autoauditoria fica para a rodada de "
   "comparação): nenhuma coluna identificadora, nenhum com > 5,000 linhas",
   not susp, f"suspeitos {susp}; maior {maxl}")
xl_max = max(ws.max_row for f in [p for p in para_commit if p.endswith(".xlsx")] for ws in openpyxl.load_workbook(PROJ / f, read_only=True).worksheets)
ok("E1.03", "xlsx que iriam para o commit: abas pequenas (agregados)", xl_max < 1000, f"máx linhas por aba {xl_max}")
ok("E1.04", "números-chave: 228 valores agregados (escalares ou listas curtas); nenhum campo com identificador",
   all(not isinstance(i["valor_bruto"], list) or len(i["valor_bruto"]) <= 10 for i in J12) and not any(ID_RX.match(k) for i in J12 for k in i), "ok")
ign_tab = subprocess.run(["git", "-C", str(PROJ), "check-ignore", "-v", "outputs/tables/tab_e7c7_01_regsaude_uf_v1_20261008.csv"], capture_output=True,
                         text=True, env=ENV).stdout.strip()
ok("E1.05", "tabela nova fora do git (outputs/tables/ no .gitignore) e só com contagens territoriais (28 linhas × 5 colunas, sem dado individual)",
   bool(ign_tab) and tn.shape == (28, 5) and list(tn.columns) == ["cod_uf", "uf", "n_regioes_saude", "n_municipios", "municipios_por_regiao"], ign_tab)
gi = (PROJ / ".gitignore").read_text()
ok("E1.06", ".gitignore igual ao de dc9328d e ainda exclui data/, *.parquet, ._*, CSVs de auditoria",
   hash_disco([".gitignore"])[".gitignore"] == arv0[".gitignore"] and all(x in gi.splitlines() for x in ["data/", "*.parquet", "._*", "audit_independente/**/*.csv"]))
txt_commit = [p for p in para_commit if p.endswith((".md", ".py", ".json")) and (PROJ / p).exists() and not p.startswith("docs/referencias/")]
pad = re.compile(r"\b\d{6}\b.{0,3}\b(19|20)\d{2}-?\d{2}-?\d{2}\b")
hits = [p for p in txt_commit if pad.search((PROJ / p).read_text(errors="ignore"))]
ok("E1.07", "texto que iria para o commit (.md, .py, .json): nenhum padrão código de município + data completa (linha de registro)", not hits,
   f"{len(txt_commit)} arquivos; com padrão {hits[:5]}")

T_AUD = datetime.strptime("2026-10-13 10:51:00", "%Y-%m-%d %H:%M:%S").timestamp()   # antes do 1º comando deste auditor
depois_ini = sorted(p for p in arvore_disco() if (PROJ / p).stat().st_mtime >= T_AUD and not p.startswith("audit_independente/etapa7c7/"))
ok("A0.02", "desde o início desta auditoria (≈10:51), nada mudou no projeto fora desta pasta, afora o RESUMO da 7c.7 (A2.07)",
   set(depois_ini) <= RESUMO7, "; ".join(f"{p} {hora((PROJ / p).stat().st_mtime)[11:]}" for p in depois_ini))
SNAP1 = snapshot()
mudou = sorted(k for k in set(SNAP0) | set(SNAP1) if SNAP0.get(k) != SNAP1.get(k))
ok("A0.01", "estado estável durante a auditoria (MD5 de outputs/manuscrito, Submissao/, scripts/ e da tabela nova no início e no fim)", not mudou,
   f"início {T0}; fim {time.strftime('%H:%M:%S')}; mudaram {mudou[:6]}")

df = pd.DataFrame(R)
df.to_csv(OUTD / "comparacao_7c7_v1_20261013.csv", index=False)
print(f"\n{int(df.ok.sum())}/{len(df)} OK")
print(df.groupby(df.verificacao.str[0]).ok.agg(["size", "sum"]))
