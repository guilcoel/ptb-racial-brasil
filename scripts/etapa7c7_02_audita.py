"""
7c.7 Autoauditoria da Etapa 7c.7 (pacote v12 com as decisões da 7c.6b), com código próprio: não importa etapa7b_lib nem o checa
(o checa só roda, como subprocesso, em cópias descartáveis).
  A  git e árvore: HEAD, refs, remoto, tag e stash; o que mudou desde dc9328d, arquivo por arquivo (rastreados, novos e ignorados);
     v11 arquivada byte a byte; ._* em todo o projeto;
  B  pacote v11 × v12: números-chave; regiões de saúde recontadas e cruzadas com tb_regsaud e tb_municip; CSVs, xlsx, docx, PDFs,
     imagens; MANIFEST (o que muda, MD5, completo, tabela bem formada); disponibilidade; legendas;
  C  scripts: cada um contra dc9328d (lib, 01, 02, 04 e LEIAME pela lista exata de trocas; etapa2_03 só na docstring; checa por
     região); checa da v12; script novo; sandbox: checa com mutações, checa depois de um commit simulado (único e com um commit no
     meio) e as afirmações do LEIAME;
  D  logs de 2026-10-13 × mtimes;
  E  microdados e git no que vai para o commit.
Só lê o projeto (data/ só por nome e mtime). O sandbox fica num diretório temporário do sistema: clone git com alternates (só o que
está versionado) + as mudanças da 7c.7 + o rl_municip_regsaud.csv + links simbólicos, só para leitura, para outputs/tables e os
comparacao_*.csv do auditor; nada de data/. Todo Python do sandbox carrega uma guarda (sitecustomize com audit hook) que bloqueia
escrita, remoção e renomeação no Forja, testada antes do uso (C6.00a; se falhar, o sandbox para ali). O sandbox é apagado no fim. Grava outputs/manuscrito/audita_7c7_v1_20261013.csv.
Rodar da raiz: python3 scripts/etapa7c7_02_audita.py
"""
import ast
import concurrent.futures as cf
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import docx
import openpyxl
import pandas as pd
import pymupdf
from PIL import Image

PROJ = Path(__file__).resolve().parents[1]
MS, SUB = PROJ / "outputs" / "manuscrito", PROJ / "Submissao"
A11 = MS / "_arquivo_v11"
V11, V12, BASE = "v11_20261009", "v12_20261013", "dc9328d"
TITULO = "Etapa 7c.7: pacote v12 com as decisões da 7c.6b"
SAIDA = MS / "audita_7c7_v1_20261013.csv"
FRASE = " Joint Wald tests were not computed for the multiple-imputation analysis."
ANTES = "combined with Rubin's rules."
TERR = PROJ / "docs/referencias/territorio_dez24"
ENV = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}


def git(*a, cwd=PROJ, b=False):
    return subprocess.run(["git", "-C", str(cwd), *a], capture_output=True, text=not b, check=True, env=ENV).stdout


md5 = lambda b: hashlib.md5(b).hexdigest()
R = []


def ok(vid, desc, cond, det=""):
    R.append(dict(verificacao=f"{vid} {desc}", ok=bool(cond), detalhe=str(det)))


T_BASE = int(git("log", "-1", "--format=%ct", BASE))

# ======================= A. git e árvore =======================
h = git("rev-parse", "--short", "HEAD").strip()
pos = h != BASE                                       # depois do commit da etapa
head_ok = h == BASE or (git("rev-parse", "--short", "HEAD^").strip() == BASE and git("log", "-1", "--format=%s").strip() == TITULO
                        and len(git("rev-list", f"{BASE}..HEAD").split()) == 1)
refs = git("for-each-ref", "--format=%(refname)").split()
remotos, stash = git("remote").split(), git("stash", "list").strip()
ok("A0.01", "HEAD = dc9328d (antes do commit) ou um commit só, com o título da etapa, sobre dc9328d; só refs/heads/main; sem remoto, "
   "sem tag, stash vazio", head_ok and refs == ["refs/heads/main"] and not remotos and not stash,
   f"HEAD {h}{' (depois do commit)' if pos else ''}; refs {refs}; remotos {remotos}; stash {stash[:40] or 'vazio'}")

_z = git("diff", "--name-status", "-z", "--no-renames", BASE).split("\0")
ns = [(_z[i], _z[i + 1]) for i in range(0, len(_z) - 1, 2)]   # árvore × dc9328d (rastreados)


def st(*a):
    return [(e[:2], e[3:]) for e in git("status", "--porcelain", "-z", "--no-renames", "--untracked-files=all", *a).split("\0") if e]


naor = [p for c, p in st() if c == "??"]
VELHOS = sorted(p for p in git("ls-tree", "-r", "--name-only", BASE, "outputs/manuscrito").splitlines()
                if V11 in p and "/_arquivo_" not in p)   # a v11 em dc9328d: 35 em tabelas/figuras/suplementar + JSON, .md e checa
PAC12 = {p.replace(V11, V12) for p in VELHOS}
A10 = MS / "_arquivo_v10"
ARQ11 = {f"outputs/manuscrito/_arquivo_v11/{str(x.relative_to(A10)).replace('v10_20261009', V11)}" for x in A10.rglob("*")
         if x.is_file() and not x.name.startswith("._")}
FIXOS = {"scripts/etapa7c7_01_regsaude_uf.py", "scripts/etapa7c7_02_audita.py", "scripts/resumos/etapa7c7_01_resumo.py",
         "outputs/manuscrito/_resumo7c7_texto_v1_20261013.md", "outputs/manuscrito/audita_7c7_v1_20261013.csv"}
RESUMO = "outputs/RESUMO_ETAPA7C7_v1_20261013.md"   # o gerador roda depois desta autoauditoria
MOD_OK = {"Submissao/ESM_1.xlsx", "Submissao/ESM_2.pdf", "Submissao/ESM_3.pdf", "Submissao/ESM_4.pdf", "outputs/manuscrito/MANIFEST.md",
          "outputs/manuscrito/data_code_availability.md", "outputs/manuscrito/legendas_figuras.md", "scripts/etapa2_03_indice_acesso.py",
          "scripts/etapa7b_lib.py", "scripts/etapa7b_01_tabelas.py", "scripts/etapa7b_02_suplementar.py", "scripts/etapa7b_04_submissao.py",
          "scripts/etapa7b_checa.py", "scripts/resumos/LEIAME.md"}
AUDRX = re.compile(r"^audit_independente/etapa7c7/[a-z0-9_]*7c7[a-z0-9_]*_v1_20261013\.(md|py|json)$")
apagados = sorted(p for s, p in ns if s == "D")
mods = sorted(p for s, p in ns if s == "M")
adic = sorted([p for s, p in ns if s == "A"] + naor)
docs_nr = [p for p in adic if p.startswith("docs/referencias/")]
aud_n = [p for p in adic if p.startswith("audit_independente/")]
resto = [p for p in adic if p not in PAC12 | ARQ11 | FIXOS | {RESUMO} and p not in docs_nr and p not in aud_n]
falta = sorted((PAC12 | ARQ11 | FIXOS) - set(adic))
mt = lambda p: (PROJ / p).stat().st_mtime
ok("A1.01", "desde dc9328d: apagados só os 38 da v11; modificados exatamente os 14 previstos; novos exatamente os 38 da v12, os 49 do "
   "_arquivo_v11, os 5 da 7c.7 (+ o RESUMO), os do auditor com nome da 7c.7; em docs/referencias, só os 93 não rastreados que já "
   "existiam (mtime antes de dc9328d) e ficam fora do commit",
   len(VELHOS) == 38 and apagados == VELHOS and set(mods) == MOD_OK and len(PAC12) == 38 and len(ARQ11) == 49 and not resto and not falta
   and all(AUDRX.match(p) for p in aud_n) and len(docs_nr) == 93 and set(docs_nr) <= set(naor) and all(mt(p) < T_BASE for p in docs_nr),
   f"apagados {len(apagados)}; modificados {len(mods)}; novos {len(adic)} ({len(docs_nr)} em docs/referencias, {len(aud_n)} do auditor); "
   f"fora do previsto {resto[:3]}; faltando {falta[:3]}; fora do padrão do auditor {[p for p in aud_n if not AUDRX.match(p)][:3]}")
mov = [p for p in VELHOS if (A11 / p[len("outputs/manuscrito/"):]).read_bytes() == git("show", f"{BASE}:{p}", b=True)]
ok("A1.02", "os 38 arquivos da v11 estão em _arquivo_v11/ com os mesmos caminhos relativos e os mesmos bytes de dc9328d",
   len(mov) == 38, f"{len(mov)}/38")
cop = {"MANIFEST_v11_20261009.md": "outputs/manuscrito/MANIFEST.md", "data_code_availability_v11_20261009.md": "outputs/manuscrito/data_code_availability.md",
       "legendas_figuras_v11_20261009.md": "outputs/manuscrito/legendas_figuras.md"}
cop.update({f"Submissao/{n}": f"Submissao/{n}" for n in ("ESM_1.xlsx", "ESM_2.pdf", "ESM_3.pdf", "ESM_4.pdf", "Fig1.tif", "Fig2.tif", "Fig3.tif", "Fig4.tif")})
cop_ok = [k for k, v in cop.items() if (A11 / k).read_bytes() == git("show", f"{BASE}:{v}", b=True)]
arq = lambda d, v: sorted(str(x.relative_to(d)).replace(v, "VX") for x in d.rglob("*") if x.is_file() and not x.name.startswith("._"))
ok("A1.03", "_arquivo_v11: MANIFEST, disponibilidade, legendas e Submissao/ iguais aos de dc9328d; 49 arquivos, mesma estrutura do _arquivo_v10",
   len(cop_ok) == len(cop) and arq(A11, V11) == arq(A10, "v10_20261009"), f"cópias {len(cop_ok)}/{len(cop)}; {len(arq(A11, V11))} arquivos")
ign = [p for c, p in st("--ignored") if c == "!!"]
ign_nov = sorted(p for p in ign if not p.endswith("/") and (PROJ / p).stat().st_mtime > T_BASE)
IGN_OK = re.compile(r"^(outputs/tables/tab_e7c7_01_regsaude_uf_v1_20261008\.csv|outputs/logs/etapa7(b|c6|c7)_20261008\.log|"
                    r"(scripts/(resumos/)?|audit_independente/etapa7c7/)__pycache__/[^/]+\.pyc|audit_independente/etapa7c7/[a-z0-9_]*7c7[a-z0-9_]*_v1_20261013\.csv)$")
ok("A1.04", "ignorados pelo git com mtime depois de dc9328d: só a tabela nova, os logs (7b, 7c6, 7c7), __pycache__ (scripts/ e pasta do auditor) e os CSVs do auditor "
   "da 7c.7; nada em data/ (só nome e mtime)", ign and not [p for p in ign_nov if not IGN_OK.match(p)],
   f"{len(ign)} ignorados; novos ou alterados: {[p for p in ign_nov if '__pycache__' not in p]}; fora do previsto "
   f"{[p for p in ign_nov if not IGN_OK.match(p)][:5]}")
lixo, em_data = [], []
for raiz, dirs, fs in os.walk(PROJ):
    rel = Path(raiz).relative_to(PROJ)
    if rel.parts[:1] == (".git",):
        dirs[:] = []
        continue
    (em_data if rel.parts[:1] == ("data",) else lixo).extend(str(rel / f) for f in fs if f.startswith("._"))
ok("A2.01", "._*: nenhum no projeto fora de data/ (inclusive na raiz); em data/, só o de data/processed (decisão 2; só o nome)",
   not lixo and em_data == ["data/processed/._pig_grade_intergrowth_v1_20261008.parquet"], f"fora de data/ {lixo[:5] or 0}; em data/ {em_data}")
apple = [l for l in git("log", "--all", "--format=", "--name-only").split() if Path(l).name.startswith("._")]
ok("A2.02", "nenhum ._* versionado no histórico nem entre os novos arquivos", not apple and not [p for p in adic if Path(p).name.startswith("._")])

# ======================= B. pacote v11 × v12 =======================
J11 = {i["id"]: i for i in json.load(open(A11 / f"numeros_chave_{V11}.json"))}
J12l = json.load(open(MS / f"numeros_chave_{V12}.json"))
J12 = {i["id"]: i for i in J12l}
NOVOS = {"n_regsaude_CE", "n_regsaude_DF"}
dif = {k: [c for c in J11[k] if c != "commit_pacote" and J11[k][c] != J12[k].get(c)] for k in J11 if k in J12}
ok("B1.01", "números-chave: 228 = os 226 da v11 (mesma ordem) + n_regsaude_CE e n_regsaude_DF no fim; nos 226, todos os campos iguais, "
   "exceto commit_pacote", len(J12l) == 228 and [i["id"] for i in J12l[:226]] == list(J11) and [i["id"] for i in J12l[226:]] == sorted(NOVOS)
   and not any(dif.values()) and all(set(J12[k]) == set(J11[k]) for k in J11), f"com diferença {[k for k, v in dif.items() if v][:3]}")
ok("B1.02", "commit_pacote: v12 = dc9328d em todos (HEAD ao gerar); v11 = 8314417 em todos",
   {i["commit_pacote"] for i in J12l} == {BASE} and {i["commit_pacote"] for i in J11.values()} == {"8314417"})
rl = pd.read_csv(TERR / "rl_municip_regsaud.csv", dtype=str)
conta = {u: rl.loc[rl.CO_MUNICIP.str.startswith(c), "CO_REGSAUD"].nunique() for u, c in (("CE", "23"), ("DF", "53"))}
ficha = (MS / "ficha_metodos_7c0_v1_20261009.md").read_text()
n2 = {u: J12[f"n_regsaude_{u}"] for u in conta}
ok("B2.01", "n_regsaude_CE = 5 e n_regsaude_DF = 1, recontados aqui em rl_municip_regsaud; 5 + 1 = 433 − 427 (ficha 7c.0: 'sem CE/DF: 427')",
   conta == {"CE": 5, "DF": 1} and all(n2[u]["valor_bruto"] == conta[u] and n2[u]["valor_formatado"] == str(conta[u]) for u in conta)
   and "sem CE/DF: 427" in ficha, f"recontado {conta}")
DESC = "Health regions in {} in the municipality-to-health-region map used for the access index (DATASUS territorial base, December 2024)"
ok("B2.02", "os dois: descrição 'in the municipality-to-health-region map used for the access index'; origem tab_e7c7_01_regsaude_uf / "
   "scripts/etapa7c7_01_regsaude_uf.py; filtro uf=; commit_registro e commit_analise vazios",
   all(n2[u]["descricao"] == DESC.format(nm) and n2[u]["arquivo"] == "outputs/tables/tab_e7c7_01_regsaude_uf_v1_20261008.csv"
       and n2[u]["script"] == "scripts/etapa7c7_01_regsaude_uf.py" and n2[u]["filtro"] == f"uf={u}" and not n2[u]["commit_registro"]
       and not n2[u]["commit_analise"] for u, nm in (("CE", "Ceará"), ("DF", "Federal District"))), {u: n2[u]["descricao"][:60] for u in conta})
t7 = pd.read_csv(PROJ / "outputs/tables/tab_e7c7_01_regsaude_uf_v1_20261008.csv", dtype={"cod_uf": str})
uf_ = pd.read_csv(TERR / "tb_uf.csv", dtype=str)
sig = dict(zip(uf_.CO_UF, uf_.DS_SIGLA))
mun = ~rl.CO_MUNICIP.str.endswith("0000")
eu = (rl.assign(cod_uf=rl.CO_MUNICIP.str[:2], m=mun).groupby("cod_uf").agg(n_regioes_saude=("CO_REGSAUD", "nunique"), n_municipios=("m", "sum"))
      .reset_index())
eu["uf"] = eu.cod_uf.map(sig)
eu = pd.concat([eu, pd.DataFrame([dict(cod_uf=float("nan"), uf="Brasil", n_regioes_saude=rl.CO_REGSAUD.nunique(), n_municipios=int(mun.sum()))])],
               ignore_index=True)
eu["municipios_por_regiao"] = (eu.n_municipios / eu.n_regioes_saude).round(1)
eu = eu[t7.columns.tolist()]
res2 = pd.read_csv(PROJ / "outputs/tables/tab_e2_02_regsaude_resumo_v1_20261008.csv").iloc[0]
ok("B2.03", "tab_e7c7_01 inteira (28 linhas × 5 colunas) = recálculo próprio (siglas pela tb_uf); Brasil 433 regiões = n_regioes do "
   "tab_e2_02_regsaude_resumo; municípios = códigos da tabela − o 530000",
   t7.shape == (28, 5) and t7.fillna("").astype(str).equals(eu.fillna("").astype(str)) and int(t7.n_regioes_saude.iloc[-1]) == res2.n_regioes == 433
   and int(t7.n_municipios.iloc[-1]) == res2.n_municipios_tabela - 1, f"Brasil {t7.iloc[-1].tolist()}; CE {t7[t7.uf == 'CE'].iloc[0].tolist()}")
tr = pd.read_csv(TERR / "tb_regsaud.csv", dtype=str)
tm = pd.read_csv(TERR / "tb_municip.csv", sep=";", dtype=str)
sem_mun = {u: sorted(set(tr.REGSAUD[tr.REGSAUD.str[:2] == c]) - set(rl.CO_REGSAUD)) for u, c in (("CE", "23"), ("DF", "53"))}
nt = {u: int((tr.REGSAUD.str[:2] == c).sum()) for u, c in (("CE", "23"), ("DF", "53"))}
ativos = tm[tm.CO_STATUS == "S"].groupby("SG_UF").size()
ok("B2.04", "cruzamento: toda região do mapa está na tb_regsaud; a tb_regsaud lista 460 (todas ATIVO), CE 25 e DF 8, das quais 20 do CE e 7 "
   "do DF sem município no mapa (por isso a descrição diz 'municipality-to-health-region map'); municípios por UF = ativos da tb_municip",
   set(rl.CO_REGSAUD) <= set(tr.REGSAUD) and len(tr) == 460 and set(tr.CO_STATUS) == {"ATIVO"} and nt == {"CE": 25, "DF": 8}
   and {u: len(v) for u, v in sem_mun.items()} == {"CE": 20, "DF": 7} and len(set(tr.REGSAUD) - set(rl.CO_REGSAUD)) == 27
   and all(int(t7.set_index("uf").n_municipios[u]) == int(ativos[u]) for u in ativos.index) and len(ativos) == 27,
   f"tb_regsaud CE {nt['CE']}, DF {nt['DF']}; sem município {dict((u, len(v)) for u, v in sem_mun.items())}; ativos tb_municip {int(ativos.sum())}")
pares = [(A11 / d / f.name, MS / d / f.name.replace(V11, V12)) for d in ("tabelas", "suplementar") for f in sorted((A11 / d).glob(f"*_{V11}.csv"))]
ig = [b.name for a, b in pares if a.read_bytes() == b.read_bytes()]
ok("B3.01", "CSVs de tabelas/ e suplementar/: os 20 da v12 idênticos byte a byte aos da v11", len(pares) == 20 and len(ig) == 20, f"{len(ig)}/{len(pares)}")


def celulas(f):
    wb = openpyxl.load_workbook(f)
    return {(ws.title, c.coordinate): c.value for ws in wb.worksheets for row in ws.iter_rows() for c in row if c.value is not None}


x11, x12 = celulas(A11 / "tabelas" / f"tabelas_principais_{V11}.xlsx"), celulas(MS / "tabelas" / f"tabelas_principais_{V12}.xlsx")
dx = sorted(k for k in set(x11) | set(x12) if x11.get(k) != x12.get(k))
ok("B4.01", "xlsx das tabelas principais: uma só célula diferente, o rodapé da Tabela 4, com a frase depois de \"Rubin's rules.\"",
   len(dx) == 1 and dx[0][0].startswith("tab04_") and str(x11[dx[0]]).count(ANTES) == 1
   and x12[dx[0]] == str(x11[dx[0]]).replace(ANTES, ANTES + FRASE), dx)
e11, e12, es = (celulas(A11 / "suplementar" / f"ESM_1_tables_S1_S6_{V11}.xlsx"), celulas(MS / "suplementar" / f"ESM_1_tables_S1_S6_{V12}.xlsx"),
                celulas(SUB / "ESM_1.xlsx"))
ok("B4.02", "ESM_1 (pacote e Submissao/): todas as células iguais às da v11", e11 == e12 == es, f"{len(e12)} células")
t4 = pd.read_csv(MS / "tabelas" / f"tab04_sensitivity_{V12}.csv", dtype=str)
mi = t4[t4.Scenario.str.startswith("Multiple imputation")]
wcols = [c for c in t4.columns if "Wald" in c]
na_out = t4[t4[wcols].eq("n.a.").any(axis=1)].Scenario.tolist()
ok("B4.03", "Tabela 4: na linha da imputação múltipla, as colunas de Wald estão 'n.a.' (o que o rodapé novo explica); outras 5 linhas "
   "também têm 'n.a.' (registradas no detalhe, para a redação)", len(mi) == 1 and wcols and all(mi.iloc[0][c] == "n.a." for c in wcols)
   and len(na_out) == 6, [s[:40] for s in na_out if not s.startswith("Multiple")])
d11, d12 = docx.Document(A11 / "tabelas" / f"tabelas_principais_{V11}.docx"), docx.Document(MS / "tabelas" / f"tabelas_principais_{V12}.docx")
p11, p12 = [p.text for p in d11.paragraphs], [p.text for p in d12.paragraphs]
c11 = [c.text for t in d11.tables for r in t.rows for c in r.cells]
c12 = [c.text for t in d12.tables for r in t.rows for c in r.cells]
dp = [(a, b) for a, b in zip(p11, p12) if a != b]
ok("B5.01", "docx: células iguais; parágrafos diferentes só no rótulo de versão e na frase nova (uma vez)",
   c11 == c12 and len(p11) == len(p12) and all(b == a.replace(V11, V12).replace(ANTES, ANTES + FRASE) for a, b in dp)
   and sum(t.count(FRASE.strip()) for t in p12) == 1, f"{len(dp)} parágrafos diferentes")
txt = lambda f: "\n".join(pg.get_text() for pg in pymupdf.open(f))
pdfs = [("suplementar", "S7_variables_codes_{}.pdf"), ("suplementar", "S8_strobe_record_checklist_{}.pdf")]
pdf_ok = [n for d, n in pdfs if txt(A11 / d / n.format(V11)) == txt(MS / d / n.format(V12))]
esm = {2: MS / "suplementar" / f"S7_variables_codes_{V12}.pdf", 3: MS / "suplementar" / f"S8_strobe_record_checklist_{V12}.pdf"}
ok("B6.01", "PDFs: S7 e S8 com o mesmo texto da v11; ESM_2 e ESM_3 = S7 e S8 da v12 (MD5); ESM_2–4 com o mesmo texto da v11",
   len(pdf_ok) == 2 and all(md5((SUB / f"ESM_{k}.pdf").read_bytes()) == md5(f.read_bytes()) for k, f in esm.items())
   and all(txt(SUB / f"ESM_{k}.pdf") == txt(A11 / "Submissao" / f"ESM_{k}.pdf") for k in (2, 3, 4)))
pix = lambda f: (lambda im: (im.size, im.mode, im.info.get("dpi"), md5(im.tobytes())))(Image.open(f))
ims = [f for d in ("figuras", "suplementar") for f in sorted((A11 / d).glob(f"*_{V11}.*")) if f.suffix in (".png", ".tif")]
im_ok = [f.name for f in ims if pix(f) == pix(MS / f.parent.name / f.name.replace(V11, V12))]
fig_sub = [k for k in range(1, 5) if (SUB / f"Fig{k}.tif").read_bytes() == git("show", f"{BASE}:Submissao/Fig{k}.tif", b=True)]
ok("B7.01", "imagens: figuras 1–4 e S9 (png e tif) com os mesmos pixels, modo e dpi da v11; Fig1–4 de Submissao/ com os mesmos bytes de dc9328d",
   len(ims) == 10 and len(im_ok) == 10 and len(fig_sub) == 4, f"{len(im_ok)}/{len(ims)}; Submissao {len(fig_sub)}/4")
norm = lambda t, v: [re.sub(r"\| [0-9a-f]{12} \|$", "| MD5 |", l.replace(v, "VX")) for l in t.splitlines()]
m11, m12 = norm((A11 / f"MANIFEST_{V11}.md").read_text(), V11), norm((MS / "MANIFEST.md").read_text(), V12)
dm = [(a, b) for a, b in zip(m11, m12) if a != b]
T2 = "(atenuação só com |PR_M2cc − 1| ≥ 0.10)"
ok("B8.01", "MANIFEST (versão e MD5 normalizados): mesmas linhas da v11; mudam só o título, o parágrafo de abertura (data, commit, "
   "etapa, v12, autoauditorias fora da lista) e a linha da Tabela 2 (o | escapado)", len(m11) == len(m12) and len(dm) == 3
   and dm[0][1] == dm[0][0].replace("Etapas 7b–7c.6", "Etapas 7b–7c.7") and "v12 = v11 com o rodapé da Tabela 4" in dm[1][1]
   and "Commit do repositório ao gerar o pacote: dc9328d" in dm[1][1] and "As autoauditorias das etapas (audita_*.csv" in dm[1][1]
   and T2 in dm[2][0] and dm[2][1] == dm[2][0].replace(T2, T2.replace("|", "\\|")), [b[:70] for a, b in dm])
lm = (MS / "MANIFEST.md").read_text().splitlines()
lin = [re.match(r"^\| ((?:manuscrito|Submissao)/\S+) \| .* \| ([0-9a-f]{12}) \|$", l) for l in lm if re.match(r"^\| (manuscrito|Submissao)/", l)]
lugar = lambda c: (MS / c[len("manuscrito/"):]) if c.startswith("manuscrito/") else PROJ / c
md_ok = [m and md5(lugar(m.group(1)).read_bytes())[:12] == m.group(2) for m in lin]
ok("B8.02", "MANIFEST: o MD5 de cada arquivo listado confere com o arquivo (calculado aqui)", bool(lin) and all(md_ok), f"{sum(map(bool, md_ok))}/{len(lin)}")
esp = []
for pasta, rot in [(MS / "tabelas", "manuscrito/tabelas"), (MS / "figuras", "manuscrito/figuras"), (MS / "suplementar", "manuscrito/suplementar"),
                   (MS, "manuscrito"), (SUB, "Submissao")]:
    esp += [f"{rot}/{f.name}" for f in sorted(pasta.iterdir()) if f.is_file() and not f.name.startswith(("._", "_", "audita_")) and f.name != "MANIFEST.md"]
lis = [m.group(1) for m in lin if m]
ok("B8.03", "MANIFEST completo: lista exatamente os arquivos das pastas do pacote, da raiz de outputs/manuscrito e de Submissao/, fora "
   "._*, _*, audita_* e ele mesmo; nenhum repetido", sorted(lis) == sorted(esp) and len(set(lis)) == len(lis),
   f"{len(lis)} listados; faltam {sorted(set(esp) - set(lis))[:3]}; sobram {sorted(set(lis) - set(esp))[:3]}")
tab = [l for l in lm if l.startswith("|")]
ok("B8.04", "MANIFEST: toda linha de tabela tem o número certo de | não escapados (4 na correspondência S → ESM, 5 nos arquivos)",
   all(len(re.findall(r"(?<!\\)\|", l)) in (4, 5) for l in tab) and all(len(re.findall(r"(?<!\\)\|", l)) == 5 for l in lm if re.match(r"^\| (manuscrito|Submissao)/", l)),
   [l[:60] for l in tab if len(re.findall(r"(?<!\\)\|", l)) not in (4, 5)][:3])
d_11 = " ".join((A11 / f"data_code_availability_{V11}.md").read_text().split())
d_12 = " ".join((MS / "data_code_availability.md").read_text().split())
volta = (d_12.replace(V12, V11).replace("Etapa 7c.7: pacote v12 com as decisões da 7c.6b", "Etapa 7c.6: auditoria independente 7c.5/7c.5b, RECORD e rastreabilidade")
         .replace('`git log --grep "^Etapa 7c.7:"`', '`git log --grep "Etapa 7c.6"`').replace("Etapa 7c.7)", "Etapa 7c.6)"))
ok("B8.05", "disponibilidade: igual à v11, fora versão, etapa e commit de referência (grep ancorado, '^Etapa 7c.7:'); legendas: iguais, "
   "fora o rótulo de versão", volta == d_11 and d_12.count('`git log --grep "^Etapa 7c.7:"`') == 1
   and (MS / "legendas_figuras.md").read_text().replace(V12, V11) == (A11 / f"legendas_figuras_{V11}.md").read_text())

# ======================= C. scripts =======================
def corpo(src):
    m = ast.parse(src)
    m.body = m.body[1:] if isinstance(m.body[0], ast.Expr) and isinstance(m.body[0].value, ast.Constant) else m.body
    return ast.dump(m)


velho = git("show", f"{BASE}:scripts/etapa2_03_indice_acesso.py")
novo = (PROJ / "scripts/etapa2_03_indice_acesso.py").read_text()
dl = [(a, b) for a, b in zip(velho.splitlines(), novo.splitlines()) if a != b]
ok("C1.01", "etapa2_03: AST sem a docstring idêntica à de dc9328d; muda uma linha da docstring (a 5ª), com o texto aprovado na decisão 3",
   corpo(velho) == corpo(novo) and len(velho.splitlines()) == len(novo.splitlines()) and len(dl) == 1
   and "(1–9; 99, nulo e qualquer outro código ficam fora; nascimentos sem região de saúde ficam fora do índice)" in dl[0][1], dl)

INS_01 = ('# 7c.7: regiões de saúde de CE e DF na base territorial (segundo motivo da sensibilidade sem CE/DF: índice sobre poucas regiões, grandes)\n'
          'rsu = B.rd("tab_e7c7_01_regsaude_uf").set_index("uf")\n'
          'for uf_, nome_ in (("CE", "Ceará"), ("DF", "Federal District")):\n'
          '    R.add(f"n_regsaude_{uf_}", int(rsu.n_regioes_saude[uf_]), B.n_(rsu.n_regioes_saude[uf_]), "tab_e7c7_01_regsaude_uf",\n'
          '          f"Health regions in {nome_} in the municipality-to-health-region map used for the access index (DATASUS territorial base, "\n'
          '          "December 2024)", f"uf={uf_}")\n')
INS_02 = ('# 7c.7: os PDFs do Chrome saem com com.apple.quarantine, que o exFAT guarda em ._*; dot_clean -m os remove (como o 04 faz em Submissao/)\n'
          'subprocess.run(["dot_clean", "-m", str(B.SUPD)], check=True)\n'
          'if list(B.SUPD.glob("._*")):                             # raise, e não assert (o python -O desliga assert)\n'
          '    raise RuntimeError(f"._* em {B.SUPD}")\n')
TROCAS = {   # arquivo: [(trecho em dc9328d, trecho agora)]; cada trecho velho ocorre uma vez, e aplicar todas reproduz o arquivo atual
    "scripts/etapa7b_lib.py": [
        ('V = "v11_20261009"               # versão/data do pacote (v11 = Etapa 7c.6: commit_pacote/commit_registro/commit_analise; v1–v10 em '
         'outputs/manuscrito/_arquivo_v1.._v10)',
         'V = "v12_20261013"               # versão/data do pacote (v12 = Etapa 7c.7: rodapé da Tabela 4 e regiões de saúde de CE/DF; v1–v11 em '
         'outputs/manuscrito/_arquivo_v1.._v11)'),
        ('    "tab_e3_03a_indice_continuo_rs": "scripts/etapa3_02_knol.py --rs",\n',
         '    "tab_e3_03a_indice_continuo_rs": "scripts/etapa3_02_knol.py --rs",\n'
         '    # 7c.7: regiões de saúde e municípios por UF na base territorial (contagem descritiva; segundo motivo da sensibilidade sem CE/DF)\n'
         '    "tab_e7c7_01_regsaude_uf": "scripts/etapa7c7_01_regsaude_uf.py",\n'),
        ('"# Key numbers (Etapas 7b–7c.6)"', '"# Key numbers (Etapas 7b–7c.7)"')],
    "scripts/etapa7b_01_tabelas.py": [
        ("combined with Rubin's rules. Live-birth bounds", "combined with Rubin's rules." + FRASE + " Live-birth bounds"),
        ('B.grava_xlsx(XL, B.TABD / f"tabelas_principais_{B.V}.xlsx")\n', INS_01 + 'B.grava_xlsx(XL, B.TABD / f"tabelas_principais_{B.V}.xlsx")\n')],
    "scripts/etapa7b_02_suplementar.py": [
        ('ETAPA = "Etapa 7c.6: auditoria independente 7c.5/7c.5b, RECORD e rastreabilidade"', f'ETAPA = "{TITULO}"'),
        ("(draft, package {B.V}, Etapa 7c.6)", "(draft, package {B.V}, Etapa 7c.7)"),
        ('`git log --grep "Etapa 7c.6"`', '`git log --grep "^Etapa 7c.7:"`'),
        ('(B.MS / "data_code_availability.md").write_text(txt)\n', '(B.MS / "data_code_availability.md").write_text(txt)\n' + INS_02)],
    "scripts/etapa7b_04_submissao.py": [
        ("(AppleDouble do exFAT)\n", "(AppleDouble do exFAT)\n  7c.7: o MANIFEST deixa fora as autoauditorias das etapas (audita_*.csv, gravadas depois do pacote) e "
         "escapa o | dentro das células\n"),
        ("(Etapas 7b–7c.6, {V})", "(Etapas 7b–7c.7, {V})"),
        ("'Etapa 7c.6: auditoria independente 7c.5/7c.5b, RECORD e rastreabilidade'). Nenhuma", f"'{TITULO}'). Nenhuma"),
        ('nos números-chave. "\n          "Scripts em scripts/.", "",',
         'nos números-chave; v12 = v11 com o rodapé da Tabela 4 "\n'
         '          "dizendo que os testes de Wald conjuntos não foram calculados na imputação múltipla, os números-chave n_regsaude_CE e "\n'
         '          "n_regsaude_DF (regiões de saúde no mapa município → região de saúde da base territorial, tab_e7c7_01_regsaude_uf) e "\n'
         '          "suplementar/ sem arquivos ._* (dot_clean no 02). Scripts em scripts/. As autoauditorias das etapas (audita_*.csv, na raiz de "\n'
         '          "outputs/manuscrito/) ficam fora da lista de arquivos: são gravadas depois do pacote, para conferi-lo.", "",'),
        ('f.name.startswith(("._", "_"))', 'f.name.startswith(("._", "_", "audita_"))'),
        ("| {o} | {md5(f)[:12]} |", "| {o.replace('|', chr(92) + '|')} | {md5(f)[:12]} |")],
    "scripts/resumos/LEIAME.md": [
        ("o `etapa7c6_01` e o `etapa7c6b_01` foram criados aqui.", "o `etapa7c6_01`, o `etapa7c6b_01` e o `etapa7c7_01` foram criados aqui."),
        ("fixam a versão (v10 e v11), e o `etapa7c6b_01` não lê o pacote.",
         "fixam a versão (v10 e v11), mas leem os arquivos dela na raiz de `outputs/manuscrito/`, então param depois que ela é arquivada (a "
         "v11 foi arquivada na 7c.7). O `etapa7c7_01` fixa a v12 do mesmo jeito. O `etapa7c6b_01` não lê o pacote."),
        ("Isso só vale enquanto os `._*` ficarem onde estão: se forem movidos, o L4.04 e o L7.01 dessa autoauditoria passam a falhar, e o "
         "registro é o CSV dela commitado na 7c.6b;",
         "Isso só valia no estado de dc9328d. Na 7c.7, a v11 foi arquivada, os `._*` foram para a lixeira e a docstring do `etapa2_03` mudou: "
         "a autoauditoria da 7c.6b para logo no começo, porque procura a v11 na raiz de `outputs/manuscrito/`. O registro é o CSV dela "
         "commitado na 7c.6b;"),
        ("  - o `etapa7c6_01` e o `etapa7c6b_01` leem sem condição", "  - o `etapa7c6_01`, o `etapa7c6b_01` e o `etapa7c7_01` leem sem condição"),
        ("- **`etapa7b_checa.py` (7c.6b):** ele exige `commit_pacote` = HEAD atual (linha 526), então falha se for reexecutado depois do "
         "commit da etapa que gerou o pacote. O registro é o `checa_7b_*.csv` do commit.",
         "- **`etapa7b_checa.py`:** até a 7c.6b, ele exigia `commit_pacote` = HEAD atual e falhava se fosse reexecutado depois do commit da "
         "etapa que gerou o pacote. Corrigido na 7c.7 (`pacote_esperado`): antes desse commit, vale o HEAD atual; depois, o pai do commit que "
         "versionou o JSON. O registro de cada versão continua sendo o `checa_7b_*.csv` do commit. Por isso cada versão do pacote entra num "
         "commit só, o da etapa, e não é regenerada depois dele com o mesmo rótulo: com um commit no meio, ou com o pacote regerado depois "
         "do commit, o `commit_pacote` deixa de ser o pai do commit que versionou o JSON e o `checa` falha.")],
}
rui = {}
for a, trocas in TROCAS.items():
    v_, n_ = git("show", f"{BASE}:{a}"), (PROJ / a).read_text()
    cont = [v_.count(x) for x, _ in trocas]
    for x, y in trocas:
        v_ = v_.replace(x, y)
    if cont != [1] * len(trocas) or v_ != n_:
        rui[a] = f"ocorrências {cont}; reproduz {v_ == n_}"
ok("C2.01", "lib, 01, 02, 04 e LEIAME: o arquivo atual = o de dc9328d com exatamente estas trocas (cada trecho velho ocorre uma vez): "
   "versão, etapa, frase da Tabela 4, CE/DF, grep ancorado, dot_clean, descrição da v12, audita_* fora do MANIFEST, | escapado, LEIAME",
   not rui, rui or {a: len(t) for a, t in TROCAS.items()})
c12 = pd.read_csv(MS / f"checa_7b_{V12}.csv")
c11 = pd.read_csv(A11 / f"checa_7b_{V11}.csv")
r11, r12 = set(c11.verificacao.str.replace(V11, "VX")), set(c12.verificacao.str.replace(V12, "VX"))   # rótulos com o nome de arquivo da versão
so_v11, novos_c = sorted(r11 - r12), sorted(r12 - r11)
ok("C3.01", "checa da v12: 113/113; as 100 verificações da v11 continuam (só a 1ª da 7c.6 mudou de rótulo); as 13 novas são da 7c.7",
   len(c12) == 113 and c12.ok.astype(bool).all() and len(c11) == 100 and len(so_v11) == 1 and so_v11[0].startswith("7c.6 números-chave")
   and len(novos_c) == 14 and sum(x.startswith("7c.7") for x in novos_c) == 13, f"sumiram {[x[:50] for x in so_v11]}; novas {len(novos_c)}")
ck = (PROJ / "scripts/etapa7b_checa.py").read_text()
ck0 = git("show", f"{BASE}:scripts/etapa7b_checa.py")
cab = git("diff", "-U0", BASE, "--", "scripts/etapa7b_checa.py")
rem_l, add_l = set(), set()
for m in re.finditer(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", cab, re.M):
    a, b, c, d = int(m.group(1)), int(m.group(2) if m.group(2) is not None else 1), int(m.group(3)), int(m.group(4) if m.group(4) is not None else 1)
    rem_l |= set(range(a, a + b))
    add_l |= set(range(c, c + d))
L0, L1 = ck0.splitlines(), ck.splitlines()
lin_de = lambda L, s: [i + 1 for i, l in enumerate(L) if l.startswith(s)]
g0 = (lin_de(L0, "# ---- 9g.")[0], lin_de(L0, "# sem 'ICR'")[0] - 1)
p0 = [i + 1 for i, l in enumerate(L0) if '"173fecd", "Etapa 7b.2", "Etapa 7c.6",' in l]
rem_fora = sorted(i for i in rem_l if not (g0[0] <= i <= g0[1]) and i not in p0)
reg = [(lin_de(L1, 'A11, V11 = B.MS / "_arquivo_v11"')[0],) * 2,
       (lin_de(L1, "J11l = json.load")[0], lin_de(L1, "# ---- 9a.")[0] - 1),
       (lin_de(L1, "# ---- 9g.")[0], lin_de(L1, "# sem 'ICR'")[0] - 1),
       ([i + 1 for i, l in enumerate(L1) if '"173fecd", "Etapa 7b.2", "Etapa 7c.7",' in l][0],) * 2,
       (lin_de(L1, "v23 = subprocess.run")[0], lin_de(L1, "# validação do multinomial")[0] - 1)]
add_fora = sorted(i for i in add_l if not any(a <= i <= b for a, b in reg))
g9 = ck[ck.index("# ---- 9g."):ck.index("# ---- 9h.")]
ok("C3.02", "checa: toda linha removida é do bloco 9g de dc9328d ou da lista da disponibilidade; toda linha acrescentada cai em A11, "
   "J11/pacote_esperado, 9g/9h, lista da disponibilidade ('Etapa 7c.7') ou checagem do etapa2_03; o 9g compara v10 × v11 arquivadas "
   "(sem Jcur, B.TABD, B.SUPD, B.SUB nem B.COMMIT) e confere commit_pacote pelo pacote_esperado",
   rem_l and not rem_fora and not add_fora and not any(x in g9 for x in ("Jcur", "B.TABD", "B.SUPD", "B.SUB", "B.COMMIT"))
   and "pacote_esperado(V11)" in g9, f"{len(rem_l)} removidas, {len(add_l)} acrescentadas; fora das regiões: removidas {rem_fora[:3]}, "
                                     f"acrescentadas {add_fora[:3]}; regiões {reg}")
src7 = (PROJ / "scripts/etapa7c7_01_regsaude_uf.py").read_text()
le = [l.strip()[:90] for l in src7.splitlines() if re.search(r"read_csv|read_parquet|open\(|read_text", l)]
ok("C4.01", "etapa7c7_01: lê só rl_municip_regsaud.csv (sem microdados); grava só tab_e7c7_01_regsaude_uf; a docstring registra a "
   "diferença para a tb_regsaud (CE 25, DF 8)", len(le) == 1 and "rl_municip_regsaud.csv" in le[0] and "parquet" not in src7
   and src7.count("to_csv(") == 1 and "(CE 25, DF 8)" in src7, le)

# ---- sandbox: checa com mutações, commit simulado, LEIAME
class GuardaFalhou(Exception):
    pass


TMP = Path(tempfile.mkdtemp(prefix="audita7c7_"))
BASE_SBX = TMP / "base"
tab_antes = {f.name: (f.stat().st_size, f.stat().st_mtime) for f in (PROJ / "outputs/tables").iterdir()}
LIMPA = "import sys; sys.path.insert(0, 'scripts'); "
SEM_ASSERT = (LIMPA + "src = open('scripts/etapa7b_checa.py').read(); assert src.count('    assert cond, nome\\n') == 1; "
              "exec(compile(src.replace('    assert cond, nome\\n', '    pass\\n'), 'scripts/etapa7b_checa.py', 'exec'), {'__name__': '__main__'})")


def monta():
    GUARDA.mkdir()
    (GUARDA / "sitecustomize.py").write_text(GUARDA_PY)
    subprocess.run(["git", "clone", "-q", "-s", str(PROJ), str(BASE_SBX)], check=True, env=ENV)
    for s, p in ns:                                       # as mudanças rastreadas da 7c.7 (inclusive as renomeações)
        if s == "D":
            (BASE_SBX / p).unlink()
        else:
            (BASE_SBX / p).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(PROJ / p, BASE_SBX / p)
    for p in naor:                                         # novos não ignorados; de docs/referencias, só o mapa territorial
        if not p.startswith("docs/referencias/") or p.endswith("territorio_dez24/rl_municip_regsaud.csv"):
            (BASE_SBX / p).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(PROJ / p, BASE_SBX / p)
    (BASE_SBX / "outputs/tables").mkdir(parents=True, exist_ok=True)
    for f in (PROJ / "outputs/tables").iterdir():          # ignorados: só links simbólicos (leitura), nenhuma cópia
        (BASE_SBX / "outputs/tables" / f.name).symlink_to(f)
    for f in (PROJ / "audit_independente").rglob("comparacao_*.csv"):   # só os que o checa e os geradores leem
        if not f.name.startswith("._") and not (BASE_SBX / f.relative_to(PROJ)).exists():
            (BASE_SBX / f.relative_to(PROJ)).parent.mkdir(parents=True, exist_ok=True)
            (BASE_SBX / f.relative_to(PROJ)).symlink_to(f)
    (BASE_SBX / "outputs/logs").mkdir(parents=True, exist_ok=True)


GUARDA = TMP / "guarda"
GUARDA_PY = """import os, sys
_F = "/Volumes/Forja"
_W = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC
_dentro = [False]
def _forja(p):
    if isinstance(p, int) or p is None:
        return False
    r = os.path.realpath(os.fsdecode(p))
    return r == _F or r.startswith(_F + "/")
def _guarda(ev, a):
    if _dentro[0]:
        return
    _dentro[0] = True
    try:
        alvo = []
        if ev == "open" and ((isinstance(a[1], str) and any(c in a[1] for c in "wax+")) or (isinstance(a[2], int) and a[2] & _W)):
            alvo = [a[0]]
        elif ev in ("os.remove", "os.rmdir", "os.mkdir", "os.truncate", "os.chmod", "os.utime", "shutil.rmtree"):
            alvo = [a[0]]
        elif ev in ("os.rename", "shutil.move"):
            alvo = [a[0], a[1]]
        elif ev in ("os.symlink", "os.link", "shutil.copyfile", "shutil.copytree"):
            alvo = [a[1]]
        if any(_forja(x) for x in alvo):
            raise PermissionError(f"guarda 7c.7: {ev} no Forja bloqueado: {alvo}")
    finally:
        _dentro[0] = False
sys.addaudithook(_guarda)
"""


def roda(dirr, codigo=None, script=None, env=None):
    """Todo Python do sandbox carrega a guarda (sitecustomize com audit hook): nada de escrita, remoção ou renomeação no Forja."""
    cmd = [sys.executable, "-c", codigo] if codigo else [sys.executable, script]
    e = {**ENV, **(env or {})}
    e["PYTHONPATH"] = os.pathsep.join([str(GUARDA)] + ([e["PYTHONPATH"]] if e.get("PYTHONPATH") else []))
    return subprocess.run(cmd, cwd=dirr, capture_output=True, text=True, env=e, timeout=1800)


def falhas(dirr, r, pai=""):
    f = dirr / f"outputs/manuscrito/checa_7b_{V12}.csv"
    if r.returncode or not f.exists():
        return dict(rc=r.returncode, n=0, fl=[r.stderr.strip()[-300:]], rot=set(), pai=pai)
    c = pd.read_csv(f)
    return dict(rc=0, n=len(c), fl=sorted(c.verificacao[~c.ok.astype(bool)]), rot=set(c.verificacao), pai=pai)


def jmuda(fun):
    def f(d):
        p = d / f"outputs/manuscrito/numeros_chave_{V12}.json"
        J = json.load(open(p))
        fun(J)
        p.write_text(json.dumps(J, ensure_ascii=False, indent=1))
    return f


def troca_txt(rel, a, b):
    def f(d):
        t = (d / rel).read_text()
        assert t.count(a) >= 1, (rel, a)
        (d / rel).write_text(t.replace(a, b, 1))
    return f


def xl_muda(rel, pega):
    def f(d):
        wb = openpyxl.load_workbook(d / rel)
        c = pega(wb)
        c.value = str(c.value).replace(FRASE, "") if FRASE in str(c.value) else str(c.value) + " x"
        wb.save(d / rel)
    return f


def rodape_t4(wb):
    ws = [w for w in wb.worksheets if w.title.startswith("tab04_")][0]
    return [c for row in ws.iter_rows() for c in row if c.value and FRASE in str(c.value)][0]


def dx_muda(d):
    p = d / f"outputs/manuscrito/tabelas/tabelas_principais_{V12}.docx"
    D = docx.Document(p)
    par = [q for q in D.paragraphs if FRASE.strip() in q.text][0]
    par.text = par.text.replace(FRASE, "")
    D.save(p)


def px_muda(d):
    p = d / f"outputs/manuscrito/figuras/fig02_pr_race_m1m3_{V12}.png"
    im = Image.open(p)
    dpi = im.info.get("dpi")
    im = im.convert("RGB")
    im.putpixel((5, 5), (1, 2, 3))
    im.save(p, dpi=dpi)


def j11_muda(d):
    p = d / f"outputs/manuscrito/_arquivo_v11/numeros_chave_{V11}.json"
    J = json.load(open(p))
    J[0]["descricao"] += " x"
    p.write_text(json.dumps(J, ensure_ascii=False, indent=1))


def csv_muda(d):
    p = d / f"outputs/manuscrito/tabelas/tab02_models_m1m3_{V12}.csv"
    L_ = p.read_text().split("\n")
    k = [j for j, l in enumerate(L_) if j and re.search(r"\d", l)][0]      # 1ª linha de dados com número
    i = re.search(r"\d", L_[k]).start()
    L_[k] = L_[k][:i] + str((int(L_[k][i]) + 1) % 10) + L_[k][i + 1:]
    p.write_text("\n".join(L_))


def cr_muda(J):
    it = [i for i in J if i["commit_registro"]][0]
    it["commit_registro"] = "0000000"


MUT = [   # (nome, mutação, rótulo da verificação do checa que tem de falhar)
    ("descrição de um número da v11", jmuda(lambda J: J[0].update(descricao=J[0]["descricao"] + " x")), "7c.7 números-chave"),
    ("commit_pacote de um número", jmuda(lambda J: J[0].update(commit_pacote="0000000")), "7c.7 commit_pacote"),
    ("n_regsaude_CE = 6", jmuda(lambda J: [i.update(valor_bruto=6, valor_formatado="6") for i in J if i["id"] == "n_regsaude_CE"]), "7c.7 n_regsaude"),
    ("descrição do n_regsaude_DF sem o mapa", jmuda(lambda J: [i.update(descricao="Health regions in Federal District (DATASUS territorial base, "
                                                                       "December 2024)") for i in J if i["id"] == "n_regsaude_DF"]), "7c.7 n_regsaude"),
    ("commit_registro de um número", jmuda(cr_muda), "7c.7 commit_registro"),
    ("um dígito de um CSV da v12", csv_muda, "7c.7 v11 × v12 célula a célula"),
    ("frase tirada do rodapé da Tabela 4 (xlsx)", xl_muda(f"outputs/manuscrito/tabelas/tabelas_principais_{V12}.xlsx", rodape_t4), "7c.7 tabelas principais (xlsx)"),
    ("título de aba do ESM_1 de Submissao/", xl_muda("Submissao/ESM_1.xlsx", lambda wb: wb.worksheets[0]["A1"]), "7c.7 ESM_1"),
    ("frase tirada do docx", dx_muda, "7c.7 docx"),
    ("grep da disponibilidade sem âncora", troca_txt("outputs/manuscrito/data_code_availability.md", '"^Etapa 7c.7:"', '"Etapa 7c.7"'), "7c.7 data_code_availability"),
    ("uma legenda", troca_txt("outputs/manuscrito/legendas_figuras.md", "**", "** x", ), "7c.7 legendas"),
    ("um pixel da figura 2 (png)", px_muda, "7c.7 figuras"),
    ("._* plantado em outputs/", lambda d: (d / "outputs/._teste").write_bytes(b"\0"), "7c.7 ._*"),
    ("dot_clean tirado do 02", troca_txt("scripts/etapa7b_02_suplementar.py", 'subprocess.run(["dot_clean", "-m", str(B.SUPD)], check=True)\n', ""), "7c.7 ._*"),
    ("código do etapa2_03", lambda d: (d / "scripts/etapa2_03_indice_acesso.py").write_text((d / "scripts/etapa2_03_indice_acesso.py").read_text() + "x_ = 1\n"),
     "7c.7 etapa2_03"),
    ("descrição na v11 arquivada (9g)", j11_muda, "7c.6 números-chave"),
]
GIT_ID = ["-c", "user.name=audita7c7", "-c", "user.email=audita7c7@local"]


def caso(k, mut=None, commit=None):
    d = TMP / f"m{k:02d}"
    subprocess.run(["cp", "-cR", str(BASE_SBX), str(d)], check=True)
    try:
        if commit == "unico":
            git(*GIT_ID, "add", "-A", cwd=d)
            git(*GIT_ID, "commit", "-q", "-m", TITULO, cwd=d)
            (d / f"outputs/manuscrito/checa_7b_{V12}.csv").unlink()
            r = roda(d, script="scripts/etapa7b_checa.py")   # o checa de verdade, com assert
            return falhas(d, r, git("rev-parse", "--short", "HEAD^", cwd=d).strip())
        if commit == "meio":
            git(*GIT_ID, "add", "scripts/etapa2_03_indice_acesso.py", cwd=d)
            git(*GIT_ID, "commit", "-q", "-m", "docstring do etapa2_03", cwd=d)
            git(*GIT_ID, "add", "-A", cwd=d)
            git(*GIT_ID, "commit", "-q", "-m", TITULO, cwd=d)
        if mut:
            mut(d)
        (d / f"outputs/manuscrito/checa_7b_{V12}.csv").unlink()
        r = roda(d, codigo=SEM_ASSERT)
        return falhas(d, r)
    finally:
        shutil.rmtree(d, ignore_errors=True)


try:
    monta()
    alvo_t = sorted(f.name for f in (BASE_SBX / "outputs/tables").iterdir())[0]
    g1 = roda(BASE_SBX, codigo=f"open('outputs/tables/{alvo_t}', 'a')")                 # escrita pelo link: tem de ser bloqueada
    g2 = roda(BASE_SBX, codigo="import os; os.remove('outputs/tables/" + alvo_t + "')")  # remoção pelo link: idem
    g3 = roda(BASE_SBX, codigo="open('outputs/logs/teste_guarda.txt', 'w').write('x')")  # escrita dentro do sandbox: permitida
    ok("C6.00a", "guarda do sandbox: escrever ou remover pelo link de outputs/tables é bloqueado (PermissionError); escrever dentro do "
       "sandbox funciona", all(r.returncode != 0 and "guarda 7c.7" in r.stderr for r in (g1, g2)) and g3.returncode == 0
       and (BASE_SBX / "outputs/tables" / alvo_t).is_symlink(), f"{[r.returncode for r in (g1, g2, g3)]}; "
       f"{g1.stderr.strip().splitlines()[-1][:80] if g1.stderr.strip() else ''}")
    (BASE_SBX / "outputs/logs/teste_guarda.txt").unlink(missing_ok=True)
    if not R[-1]["ok"]:
        raise GuardaFalhou("a guarda do sandbox não funcionou: nenhuma mutação, commit simulado ou teste do LEIAME roda")
    with cf.ThreadPoolExecutor(4) as ex:
        fb = ex.submit(caso, 0)
        fm = [ex.submit(caso, k + 1, m) for k, (_, m, _) in enumerate(MUT)]
        fu = ex.submit(caso, 90, commit="unico")
        fi = ex.submit(caso, 91, commit="meio")
        rb, fm, ru, ri = fb.result(), [f.result() for f in fm], fu.result(), fi.result()
    ok("C6.00", "sandbox: o checa (sem o assert, para rodar até o fim) dá 113/113, com os mesmos rótulos do checa da v12",
       rb["rc"] == 0 and rb["n"] == 113 and not rb["fl"] and rb["rot"] == set(c12.verificacao), f"código {rb['rc']}; {rb['n']} verificações; "
       f"falhas {[x[:60] for x in rb['fl']][:2]}; rótulos diferentes {sorted(rb['rot'] ^ set(c12.verificacao))[:2]}")
    for k, ((nome, _, alvo), r_) in enumerate(zip(MUT, fm)):
        ok(f"C6.{k + 1:02d}", f"mutação ({nome}): o checa acusa '{alvo}'" + ("" if alvo.startswith("7c.6") else "; o bloco 9g (7c.6) não se mexe"),
           r_["rc"] == 0 and any(x.startswith(alvo) for x in r_["fl"]) and (alvo.startswith("7c.6") or not any(x.startswith("7c.6") for x in r_["fl"])),
           f"código {r_['rc']}; {r_['n']} verificações; falhas {[x[:45] for x in r_['fl']][:4]}")
    ok("C6.20", "commit único simulado (git add -A + commit com o título da etapa): o checa de verdade (com assert) roda depois do commit e "
       "dá 113/113; commit_pacote = pai do commit (dc9328d)", ru["rc"] == 0 and ru["n"] == 113 and not ru["fl"] and ru["pai"] == BASE,
       f"código {ru['rc']}; {ru['n']} verificações; falhas {[x[:60] for x in ru['fl']][:2]}; pai {ru['pai']}")
    ok("C6.21", "com um commit no meio (a docstring antes, como no plano antigo da decisão 3), o checa acusa commit_pacote (LEIAME: um commit só)",
       ri["rc"] == 0 and any(x.startswith("7c.7 commit_pacote") for x in ri["fl"]), f"falhas {[x[:45] for x in ri['fl']][:3]}")
    d = TMP / "leiame"
    subprocess.run(["cp", "-cR", str(BASE_SBX), str(d)], check=True)
    pp = {"PYTHONPATH": "scripts"}
    l1 = roda(d, script="scripts/etapa7c6_02_audita_final.py")
    l2 = roda(d, script="scripts/resumos/etapa7c6_01_resumo.py", env=pp)
    l3 = roda(d, script="scripts/resumos/etapa7c5b_01_resumo.py", env=pp)
    r6b = "outputs/RESUMO_ETAPA7C6b_v1_20261010.md"
    (d / r6b).unlink()
    l4 = roda(d, script="scripts/resumos/etapa7c6b_01_resumo.py", env=pp)
    rep = (d / r6b).exists() and (d / r6b).read_bytes() == git("show", f"{BASE}:{r6b}", b=True)
    l5 = roda(d, script="scripts/resumos/etapa7c7_01_resumo.py", env=pp)            # com a v12 na raiz, roda
    (d / "outputs/manuscrito/_arquivo_v12").mkdir()
    for f in (d / "outputs/manuscrito").glob(f"*_{V12}.*"):                         # arquivamento simulado da v12
        f.rename(d / "outputs/manuscrito/_arquivo_v12" / f.name)
    l6 = roda(d, script="scripts/resumos/etapa7c7_01_resumo.py", env=pp)
    fnf = lambda r, s: r.returncode != 0 and "FileNotFoundError" in r.stderr and s in r.stderr
    ok("C6.22", "LEIAME, testado no sandbox: a autoauditoria da 7c.6b e o gerador 7c6_01 param (FileNotFoundError, v11 na raiz); o 7c5b_01 "
       "para (v10 na raiz); o 7c6b_01 roda e reproduz o RESUMO 7c.6b de dc9328d byte a byte; o gerador 7c7_01 roda com a v12 na raiz e "
       "para depois de um arquivamento simulado da v12",
       fnf(l1, V11) and fnf(l2, V11) and fnf(l3, "v10_20261009") and l4.returncode == 0 and rep and l5.returncode == 0 and fnf(l6, V12),
       f"7c6_02 {l1.returncode} {l1.stderr.strip().splitlines()[-1][:70] if l1.stderr.strip() else ''}; 7c6_01 {l2.returncode}; "
       f"7c5b_01 {l3.returncode}; 7c6b_01 {l4.returncode}, reproduz {rep}; 7c7_01 antes {l5.returncode}, depois {l6.returncode}")
except GuardaFalhou as e:
    ok("C6.99", "sandbox interrompido", False, e)
finally:
    shutil.rmtree(TMP, ignore_errors=True)
tab_depois = {f.name: (f.stat().st_size, f.stat().st_mtime) for f in (PROJ / "outputs/tables").iterdir()}
ok("C6.23", "outputs/tables do projeto intacta depois do sandbox (mesmos arquivos, tamanhos e mtimes); sandbox apagado",
   tab_antes == tab_depois and not TMP.exists(), f"{len(tab_depois)} arquivos")

# ======================= D. logs × mtimes =======================
ev = []
for nome in ("etapa7b_20261008.log", "etapa7c7_20261008.log", "etapa7c6_20261008.log"):
    for l in (PROJ / "outputs/logs" / nome).read_text(errors="ignore").splitlines():
        m = re.match(r"^\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\] \[([^\]]+)\] (.*)", l)
        if not m:
            continue
        t = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").timestamp()
        if t <= T_BASE:
            continue
        s, msg = m.group(2), m.group(3)
        e = {"7c7_01_regsaude_uf": "7c7_01" if msg.startswith("regiões de saúde:") else None, "7b_01_tabelas": "01", "7b_02_suplementar": "02",
             "7b_03_figuras": "03", "7b_04_submissao": "04"}.get(s)
        if s == "7b_checa":
            e = "checa_ini" if msg.startswith("OK  números-chave = arquivo de origem") else "checa_fim" if msg.startswith("autoauditoria 7b:") else None
        if s == "7c6_01_resumo":
            e = "7c6_01_resumo"
        if e:
            ev.append((t, e, msg))
ev.sort()
seq = [e for _, e, _ in ev]
SEQ = ["7c6_01_resumo",                                                     # 10:20:24, conferência do RESUMO 7c.6 depois do commit da 7c.6b
       "7c7_01", "7c7_01",                                                  # 1ª contava o 530000 como município
       "01", "02", "03", "04", "checa_ini", "checa_ini", "checa_fim", "04",  # 1ª rodada; o 1º checa parou por erro de código
       "7c7_01", "01", "02", "03", "04", "checa_ini", "checa_fim", "04"]     # rodada final (depois da auditoria independente)
ok("D1.01", "execuções desde dc9328d, na ordem: as documentadas no RESUMO (7c6_01 da conferência da 7c.6b; 7c7_01 duas vezes; 1ª rodada "
   "01–04, checa interrompido e refeito, 04; rodada final 7c7_01, 01–04, checa, 04)", seq == SEQ,
   [f"{datetime.fromtimestamp(t):%H:%M:%S} {e}" for t, e, _ in ev])
fin = {}
for t, e, _ in ev[-8:]:
    fin.setdefault(e, []).append(t)
t7c, t01, t02, t03, (t04a, t04b), tci, tcf = (fin["7c7_01"][0], fin["01"][0], fin["02"][0], fin["03"][0], fin["04"], fin["checa_ini"][0],
                                              fin["checa_fim"][0])
SCR = ["scripts/etapa0_lib.py", "scripts/etapa7b_lib.py", "scripts/etapa7c7_01_regsaude_uf.py", "scripts/etapa7b_01_tabelas.py",
       "scripts/etapa7b_02_suplementar.py", "scripts/etapa7b_03_figuras.py", "scripts/etapa7b_04_submissao.py", "scripts/etapa7b_checa.py"]
dentro = lambda f, a, b: a - 2 <= f.stat().st_mtime <= b + 2
jan = ([(PROJ / "outputs/tables/tab_e7c7_01_regsaude_uf_v1_20261008.csv", t7c - 5, t7c)]
       + [(f, t7c, t01) for f in (MS / "tabelas").glob(f"*_{V12}.*")] + [(MS / f"numeros_chave_{V12}.{x}", t7c, t01) for x in ("json", "md")]
       + [(f, t7c, t02) for f in (MS / "suplementar").glob(f"*_{V12}.*") if not f.name.startswith("S9_")]
       + [(MS / "data_code_availability.md", t01, t02)]
       + [(f, t02, t03) for f in list((MS / "figuras").glob(f"*_{V12}.*")) + list((MS / "suplementar").glob(f"S9_*_{V12}.*"))]   # o 03 grava o S9
       + [(MS / "legendas_figuras.md", t02, t03)]
       + [(MS / f"checa_7b_{V12}.csv", tci, tcf)] + [(MS / "MANIFEST.md", tcf, t04b), (SUB / "ESM_4.pdf", tcf, t04b)])
ORIGEM_SUB = {**{f"Fig{k}.tif": MS / "figuras" / n for k, n in enumerate(sorted(x.name for x in (MS / "figuras").glob(f"*_{V12}.tif")), 1)},
              "ESM_1.xlsx": MS / "suplementar" / f"ESM_1_tables_S1_S6_{V12}.xlsx", "ESM_2.pdf": MS / "suplementar" / f"S7_variables_codes_{V12}.pdf",
              "ESM_3.pdf": MS / "suplementar" / f"S8_strobe_record_checklist_{V12}.pdf"}
fora_j = [f"{f.name} {datetime.fromtimestamp(f.stat().st_mtime):%H:%M:%S}" for f, a, b in jan if not dentro(f, a, b)]
fora_j += [f"Submissao/{n} ≠ mtime da origem" for n, o in ORIGEM_SUB.items() if abs((SUB / n).stat().st_mtime - o.stat().st_mtime) > 2
           or (SUB / n).read_bytes() != o.read_bytes()]
ok("D1.02", "rodada final: todo script envolvido foi editado antes dela; cada saída tem mtime na janela do script que a grava (tabela nova; "
   "tabelas, números-chave; suplementar, disponibilidade; figuras, S9, legendas; checa; MANIFEST e ESM_4 no último 04; Fig1–4 e ESM_1–3 "
   "de Submissao/ = cópias com o mtime da origem)",
   all((PROJ / s).stat().st_mtime < t7c for s in SCR) and not fora_j and len(jan) >= 40,
   f"{len(jan)} arquivos; fora da janela {fora_j[:4]}; scripts depois do início {[s for s in SCR if (PROJ / s).stat().st_mtime >= t7c]}")

# ======================= E. microdados e git no que vai para o commit =======================
vai = sorted(set(p for s, p in ns if s != "D") | {p for p in naor if not p.startswith("docs/referencias/")})
EXT = (".parquet", ".dbc", ".dbf", ".rds", ".rda", ".rdata", ".sav", ".dta", ".feather", ".sqlite", ".db", ".gz", ".zip", ".7z")
ruim = [p for p in vai if p.startswith("data/") or p.lower().endswith(EXT) or Path(p).name.startswith("._") or Path(p).name == ".DS_Store"
        or (p.startswith("audit_independente/") and p.endswith(".csv")) or (PROJ / p).stat().st_size > 20e6]
ok("E1.01", "o que vai para o commit (rastreados alterados + novos, sem os 93 de docs/referencias): nada em data/, nenhum parquet/dbc/dbf/"
   "rds/zip, nenhum ._* ou .DS_Store, nenhum CSV do auditor, nenhum arquivo > 20 MB", vai and not ruim, f"{len(vai)} arquivos; problemas {ruim[:5]}")
IDS = re.compile(r"(?i)^(NUMERODN|NUMERODV|DTNASC|DTNASCMAE|DTCADASTRO|DTRECEBIM|CODMUNRES|CODMUNNASC|CODESTAB|CONTADOR|CODINST|NUDIASOBIN)$")
lin_max, col_id = {}, []
for p in vai:
    f = PROJ / p
    if p.endswith(".csv"):
        dd = pd.read_csv(f, dtype=str)
        lin_max[p] = len(dd)
        col_id += [f"{p}:{c}" for c in dd.columns if IDS.match(str(c))]
    elif p.endswith(".xlsx"):
        wb = openpyxl.load_workbook(f, read_only=True)
        lin_max[p] = max(ws.max_row or 0 for ws in wb.worksheets)
grandes = {p: n for p, n in lin_max.items() if n > 1000}
ok("E1.02", "CSVs e xlsx que vão para o commit: nenhuma coluna identificadora do SINASC/SIM e no máximo 1.000 linhas por tabela/aba (só agregados)",
   lin_max and not grandes and not col_id, f"{len(lin_max)} tabelas; maior {max(lin_max.values()) if lin_max else 0} linhas; grandes {grandes}; colunas {col_id[:3]}")
ok("E1.03", ".gitignore igual ao de dc9328d (data/, parquet, outputs/tables e CSVs de auditoria continuam fora)",
   (PROJ / ".gitignore").read_text() == git("show", f"{BASE}:.gitignore"))

out = pd.DataFrame(R)
out.to_csv(SAIDA, index=False)
print(out.to_string(max_colwidth=200))
print(f"\n{int(out.ok.sum())}/{len(out)} OK")
