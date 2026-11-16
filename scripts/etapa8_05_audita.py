"""
8 Autoauditoria da Etapa 8 (sensibilidade com a cobertura da Atenção Básica; pacote v13), com código próprio: não importa etapa7b_lib,
etapa0_lib, etapa1_lib, etapa3_lib nem os scripts da etapa (o checa e os geradores só rodam, como subprocesso, em cópias descartáveis).
  A  git e árvore: HEAD, refs, remoto, tag e stash; o que mudou desde dc54fb9, arquivo por arquivo (rastreados, novos e ignorados; em
     data/, só nome e mtime); v12 arquivada byte a byte; ._* em todo o projeto;
  B  dados e análise refeitos por outro caminho: bruto (MD5, bytes, competências, municípios); cobertura por região × ano recalculada do
     JSON com o mapa lido da base territorial; controles de qualidade; tercis com implementação própria; Spearman, kappa (sklearn) e
     distribuição por raça; os 6 modelos refeitos com statsmodels (GLM Poisson com a covariância por cluster do próprio statsmodels;
     desenho, padronização e IC próprios);
  P  pacote v12 × v13: números-chave; CSVs; xlsx; células "n.a." da Tabela 4; docx; PDFs; imagens; MANIFEST; disponibilidade; legendas;
  C  scripts: lib, 01, 02, 04 e LEIAME contra dc54fb9 pela lista exata de trocas; checa por região e checa da v13; scripts da Etapa 8
     (entradas, saídas, só agregados); sandbox: checa com mutações dirigidas ao bloco 9i (com controle negativo), checa depois de um
     commit simulado (único e com um commit no meio) e as afirmações do LEIAME;
  D  logs desde dc54fb9 × mtimes;
  E  microdados e git no que vai para o commit.
Lê a amostra analítica (data/processed, parquet) só em memória, para refazer tercis e modelos; nada dela é gravado. O sandbox fica num
diretório temporário do sistema: clone git com alternates (só o que está versionado) + as mudanças da Etapa 8 + o rl_municip_regsaud.csv
e o ACESSO.txt da cobertura + links simbólicos, só para leitura, para outputs/tables, os comparacao_*.csv dos auditores e o JSON da
cobertura (dado público agregado por município); nenhum microdado. Todo Python do sandbox carrega uma guarda (sitecustomize com audit
hook) que bloqueia escrita, remoção e renomeação no Forja, testada antes do uso (C6.00a; se falhar, o sandbox para ali). O sandbox é
apagado no fim. Grava outputs/manuscrito/audita_8_v1_20261013.csv.
Rodar da raiz: python3 scripts/etapa8_05_audita.py
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

sys.dont_write_bytecode = True
import docx
import numpy as np
import openpyxl
import pandas as pd
import pymupdf
import statsmodels.api as sm
from PIL import Image
from scipy import stats
from sklearn.metrics import cohen_kappa_score

PROJ = Path(__file__).resolve().parents[1]
MS, SUB, TB, PROC = PROJ / "outputs" / "manuscrito", PROJ / "Submissao", PROJ / "outputs" / "tables", PROJ / "data" / "processed"
A11, A12 = MS / "_arquivo_v11", MS / "_arquivo_v12"
V11, V12, V13, BASE, S = "v11_20261009", "v12_20261013", "v13_20261013", "dc54fb9", "20261008"
TITULO = "Etapa 8: sensibilidade com a cobertura da Atenção Básica (pacote v13)"
SAIDA = MS / "audita_8_v1_20261013.csv"
RAW = PROJ / "data" / "raw" / "aps_cobertura_ab"
ACC = PROJ / "docs" / "referencias" / "aps_cobertura_ab" / "ACESSO.txt"
TERR = PROJ / "docs" / "referencias" / "territorio_dez24"
ENV = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
MACRO = {"1": "N", "2": "NE", "3": "SE", "4": "S", "5": "CO"}
OUTC = {"ptb": "Preterm birth (total)", "pig": "SGA", "ptb_ind": "Provider-initiated preterm birth"}
EXP = {"tercil_aps": "aps", "tercil_ind21": "indice_2015_2021"}
NOTA_NA = ("n.a., not applicable or not estimated. Gestational age in days changes SGA only; the dating-robust analysis and the weight "
           ">P97 reclassification do not apply to SGA; live-birth bounds were computed only for preterm birth (total) and SGA, as a "
           "correction of the PR M2 without a race\u00d7tertile model, so IC and Wald tests are not estimated. 'Unchanged' and 'not "
           "reclassified': the scenario does not change the outcome, so the main-analysis estimates apply; for the unclassified-preterm-"
           "birth scenarios this also holds for the Wald tests of total preterm birth. ")
ANTES_NA = "births without a health region. Sources:"


def git(*a, cwd=PROJ, b=False):
    return subprocess.run(["git", "-C", str(cwd), *a], capture_output=True, text=not b, check=True, env=ENV).stdout


md5 = lambda b: hashlib.md5(b).hexdigest()
R = []


def ok(vid, desc, cond, det=""):
    R.append(dict(verificacao=f"{vid} {desc}", ok=bool(cond), detalhe=str(det)))


# formatação própria (= regras do pacote: 2 casas, sinal de menos tipográfico; p com 3 algarismos ou <0.0001; % com 1 casa)
num2 = lambda x: f"{x:,.2f}".replace("-", "\u2212")
rd_ = lambda e, lo, hi: f"{num2(e)} ({num2(lo)} to {num2(hi)})"
pv = lambda p: "<0.0001" if p < 0.0001 else f"{p:.3g}"
pc1 = lambda x: f"{x:.1f}%"
T_BASE = int(git("log", "-1", "--format=%ct", BASE))

# ======================= A. git e árvore =======================
h = git("rev-parse", "--short", "HEAD").strip()
pos = h != BASE
head_ok = h == BASE or (git("rev-parse", "--short", "HEAD^").strip() == BASE and git("log", "-1", "--format=%s").strip() == TITULO
                        and len(git("rev-list", f"{BASE}..HEAD").split()) == 1)
refs = git("for-each-ref", "--format=%(refname)").split()
remotos, stash = git("remote").split(), git("stash", "list").strip()
ok("A0.01", "HEAD = dc54fb9 (antes do commit) ou um commit só, com o título da etapa, sobre dc54fb9; só refs/heads/main; sem remoto, "
   "sem tag, stash vazio", head_ok and refs == ["refs/heads/main"] and not remotos and not stash,
   f"HEAD {h}{' (depois do commit)' if pos else ''}; refs {refs}; remotos {remotos}; stash {stash[:40] or 'vazio'}")
_z = git("diff", "--name-status", "-z", "--no-renames", BASE).split("\0")
ns = [(_z[i], _z[i + 1]) for i in range(0, len(_z) - 1, 2)]


def st(*a):
    return [(e[:2], e[3:]) for e in git("status", "--porcelain", "-z", "--no-renames", "--untracked-files=all", *a).split("\0") if e]


naor = [p for c, p in st() if c == "??"]
VELHOS = sorted(p for p in git("ls-tree", "-r", "--name-only", BASE, "outputs/manuscrito").splitlines() if V12 in p and "/_arquivo_" not in p)
PAC13 = {p.replace(V12, V13) for p in VELHOS}
ARQ12 = {f"outputs/manuscrito/_arquivo_v12/{str(x.relative_to(A11)).replace(V11, V12)}" for x in A11.rglob("*")
         if x.is_file() and not x.name.startswith("._")}
FIXOS = {"scripts/etapa8_01_baixa_cobertura_ab.py", "scripts/etapa8_02_cobertura_regiao.py", "scripts/etapa8_03_tercis.py",
         "scripts/etapa8_04_modelos.py", "scripts/etapa8_05_audita.py", "scripts/resumos/etapa8_01_resumo.py",
         "outputs/manuscrito/_resumo8_texto_v1_20261013.md", "docs/referencias/aps_cobertura_ab/ACESSO.txt"}
OPC = {"outputs/RESUMO_ETAPA8_v1_20261013.md", "outputs/manuscrito/audita_8_v1_20261013.csv"}   # gravados depois desta autoauditoria
MOD_OK = {"Submissao/ESM_1.xlsx", "Submissao/ESM_2.pdf", "Submissao/ESM_3.pdf", "Submissao/ESM_4.pdf", "outputs/manuscrito/MANIFEST.md",
          "outputs/manuscrito/data_code_availability.md", "outputs/manuscrito/legendas_figuras.md", "scripts/etapa7b_lib.py",
          "scripts/etapa7b_01_tabelas.py", "scripts/etapa7b_02_suplementar.py", "scripts/etapa7b_04_submissao.py",
          "scripts/etapa7b_checa.py", "scripts/resumos/LEIAME.md"}
AUDRX = re.compile(r"^audit_independente/etapa8/[A-Za-z0-9_]+_v1_20261013\.(md|py|R|json)$")
apagados = sorted(p for s, p in ns if s == "D")
mods = sorted(p for s, p in ns if s == "M")
adic = sorted([p for s, p in ns if s == "A"] + naor)
docs_nr = [p for p in adic if p.startswith("docs/referencias/") and p not in FIXOS]
aud_n = [p for p in adic if p.startswith("audit_independente/")]
resto = [p for p in adic if p not in PAC13 | ARQ12 | FIXOS | OPC and p not in docs_nr and p not in aud_n]
falta = sorted((PAC13 | ARQ12 | FIXOS) - set(adic))
mt = lambda p: (PROJ / p).stat().st_mtime
ok("A1.01", "desde dc54fb9: apagados só os 38 da v12; modificados exatamente os 13 previstos; novos exatamente os 38 da v13, os 49 do "
   "_arquivo_v12, os 8 da Etapa 8 (+ RESUMO e CSV desta autoauditoria), os do auditor na pasta etapa8; em docs/referencias, fora o "
   "ACESSO.txt da cobertura, só os 93 não rastreados que já existiam (mtime antes de dc54fb9) e ficam fora do commit",
   len(VELHOS) == 38 and apagados == VELHOS and set(mods) == MOD_OK and len(PAC13) == 38 and len(ARQ12) == 49 and not resto and not falta
   and all(AUDRX.match(p) for p in aud_n) and len(docs_nr) == 93 and set(docs_nr) <= set(naor) and all(mt(p) < T_BASE for p in docs_nr),
   f"apagados {len(apagados)}; modificados {len(mods)}; novos {len(adic)} ({len(docs_nr)} em docs/referencias, {len(aud_n)} do auditor); "
   f"fora do previsto {resto[:3]}; faltando {falta[:3]}; fora do padrão do auditor {[p for p in aud_n if not AUDRX.match(p)][:3]}")
mov = [p for p in VELHOS if (A12 / p[len("outputs/manuscrito/"):]).read_bytes() == git("show", f"{BASE}:{p}", b=True)]
ok("A1.02", "os 38 arquivos da v12 estão em _arquivo_v12/ com os mesmos caminhos relativos e os mesmos bytes de dc54fb9", len(mov) == 38, f"{len(mov)}/38")
cop = {"MANIFEST_v12_20261013.md": "outputs/manuscrito/MANIFEST.md", "data_code_availability_v12_20261013.md": "outputs/manuscrito/data_code_availability.md",
       "legendas_figuras_v12_20261013.md": "outputs/manuscrito/legendas_figuras.md"}
cop.update({f"Submissao/{n}": f"Submissao/{n}" for n in ("ESM_1.xlsx", "ESM_2.pdf", "ESM_3.pdf", "ESM_4.pdf", "Fig1.tif", "Fig2.tif", "Fig3.tif", "Fig4.tif")})
cop_ok = [k for k, v in cop.items() if (A12 / k).read_bytes() == git("show", f"{BASE}:{v}", b=True)]
arq = lambda d, v: sorted(str(x.relative_to(d)).replace(v, "VX") for x in d.rglob("*") if x.is_file() and not x.name.startswith("._"))
ok("A1.03", "_arquivo_v12: MANIFEST, disponibilidade, legendas e Submissao/ iguais aos de dc54fb9; 49 arquivos, mesma estrutura do _arquivo_v11",
   len(cop_ok) == len(cop) and arq(A12, V12) == arq(A11, V11), f"cópias {len(cop_ok)}/{len(cop)}; {len(arq(A12, V12))} arquivos")
ign = [p for c, p in st("--ignored") if c == "!!"]
ign_nov = sorted(p for p in ign if not p.endswith("/") and not p.startswith("data/") and (PROJ / p).stat().st_mtime > T_BASE)
IGN_OK = re.compile(r"^(outputs/tables/tab_e8_0[234]_[a-z_]+_v1_20261008\.csv|outputs/logs/etapa(7b|8)_20261008\.log|"
                    r"(scripts/(resumos/)?|audit_independente/etapa8/)__pycache__/[^/]+\.pyc|audit_independente/etapa8/[a-z0-9_]+_v1_20261013\.csv)$")
ok("A1.04", "ignorados pelo git (fora de data/) com mtime depois de dc54fb9: só as tabelas da Etapa 8, os logs 7b e 8, __pycache__ e os "
   "CSVs do auditor da Etapa 8", ign and not [p for p in ign_nov if not IGN_OK.match(p)],
   f"{len(ign)} ignorados; novos ou alterados: {[p for p in ign_nov if '__pycache__' not in p][:12]}; fora do previsto "
   f"{[p for p in ign_nov if not IGN_OK.match(p)][:5]}")
dnov = sorted(str(Path(r).relative_to(PROJ) / f) for r, _, fs in os.walk(PROJ / "data") for f in fs
              if os.stat(Path(r) / f).st_mtime > T_BASE)                                   # só nome e mtime
DATA_OK = ({f"data/raw/aps_cobertura_ab/cobertura_ab_uf{u}_201401_202012.json" for u in
            ("11 12 13 14 15 16 17 21 22 23 24 25 26 27 28 29 31 32 33 35 41 42 43 50 51 52 53".split())}
           | {"data/raw/aps_cobertura_ab/manifesto_cobertura_ab_v1_20261013.csv", f"data/processed/cobertura_ab_regsaude_ano_v1_{S}.csv",
              f"data/processed/tercil_aps_regsaude_ano_v1_{S}.csv"})
ok("A1.05", "data/ (só nome e mtime): depois de dc54fb9, só os 27 JSON da cobertura e o manifesto, em data/raw/aps_cobertura_ab/, e as "
   "duas tabelas por região × ano em data/processed/", set(dnov) == DATA_OK, f"{len(dnov)} arquivos; fora do previsto "
   f"{sorted(set(dnov) - DATA_OK)[:3]}; faltando {sorted(DATA_OK - set(dnov))[:3]}")
lixo, em_data = [], []
for raiz, dirs, fs in os.walk(PROJ):
    rel = Path(raiz).relative_to(PROJ)
    if rel.parts[:1] == (".git",):
        dirs[:] = []
        continue
    (em_data if rel.parts[:1] == ("data",) else lixo).extend(str(rel / f) for f in fs if f.startswith("._"))
ok("A2.01", "._*: nenhum no projeto fora de data/ (inclusive na raiz); em data/, só o de data/processed (decisão 2 da 7c.6b; só o nome)",
   not lixo and em_data == ["data/processed/._pig_grade_intergrowth_v1_20261008.parquet"], f"fora de data/ {lixo[:5] or 0}; em data/ {em_data}")
apple = [l for l in git("log", "--all", "--format=", "--name-only").split() if Path(l).name.startswith("._")]
ok("A2.02", "nenhum ._* versionado no histórico nem entre os novos arquivos", not apple and not [p for p in adic if Path(p).name.startswith("._")])

# ======================= B. dados e análise refeitos por outro caminho =======================
acc = ACC.read_text()
md5_acc = dict(re.findall(r"MD5 \((cobertura_ab_uf\d{2}_201401_202012\.json)\) = ([0-9a-f]{32})", acc))
byt_acc = {f"cobertura_ab_uf{int(u):02d}_201401_202012.json": int(b) for u, b in
           re.findall(r"coUf=(\d+)&nuCompInicio=201401&nuCompFim=202012  \((\d+) bytes\)", acc)}
man = pd.read_csv(RAW / "manifesto_cobertura_ab_v1_20261013.csv", dtype=str).set_index("arquivo")
jsons = sorted(RAW.glob("cobertura_ab_uf*_201401_202012.json"))
COMPS = {f"{a}{m:02d}" for a in range(2014, 2021) for m in range(1, 13)}
partes, prob = [], []
for f in jsons:
    b_ = f.read_bytes()
    x = json.loads(b_)
    uf = f.name[15:17]
    if not (isinstance(x, list) and md5(b_) == md5_acc.get(f.name) == man.md5.get(f.name) and len(b_) == byt_acc.get(f.name)
            and {r["coUfIbge"] for r in x} == {uf} and {r["nuComp"] for r in x} == COMPS):
        prob.append(f.name)
    partes.append(pd.DataFrame(x)[["nuComp", "coMunicipioIbge", "qtPopulacao", "pcCoberturaAb", "qtCoberturaAb"]])
D = pd.concat(partes, ignore_index=True)
nmun = D.coMunicipioIbge.nunique()
ok("B1.01", "bruto da cobertura: 27 JSON (um por UF), MD5 = ACESSO.txt = manifesto, bytes = ACESSO.txt, só a UF pedida, as 84 "
   "competências 201401–202012; 467,880 registros = 5,570 municípios × 84, sem município-competência repetido",
   len(jsons) == 27 == len(md5_acc) == len(byt_acc) == len(man) and not prob and len(D) == 467880 and nmun == 5570
   and not D.duplicated(["coMunicipioIbge", "nuComp"]).any(), f"{len(jsons)} arquivos; problemas {prob}; {len(D):,} registros; {nmun:,} municípios")
nn = lambda s: pd.to_numeric(s.astype(str).str.replace(",", "", regex=False), errors="coerce")
D = D.assign(ano=D.nuComp.str[:4].astype(int), pc=nn(D.pcCoberturaAb), popu=nn(D.qtPopulacao), qc=nn(D.qtCoberturaAb), cod=D.coMunicipioIbge.astype(str))
rl = pd.read_csv(TERR / "rl_municip_regsaud.csv", dtype=str)
rl = rl[~rl.CO_MUNICIP.str.endswith("0000")]
D["reg"] = D.cod.map(dict(zip(rl.CO_MUNICIP, rl.CO_REGSAUD)))
Dm = D.dropna(subset=["reg"]).assign(w=lambda z: z.pc * z.popu)
cob = Dm.groupby(["reg", "ano"]).agg(w=("w", "sum"), p=("popu", "sum"), n_mun=("cod", "nunique"), n_reg=("cod", "size"))
cob["cob"] = cob.w / cob.p
cob["pop_media"] = Dm.groupby(["reg", "ano", "nuComp"]).popu.sum().groupby(["reg", "ano"]).mean()
cob = cob.reset_index()
P8 = pd.read_csv(PROC / f"cobertura_ab_regsaude_ano_v1_{S}.csv", dtype={"CO_REGSAUD": str})
cc = P8.merge(cob, left_on=["CO_REGSAUD", "ano"], right_on=["reg", "ano"], how="outer", indicator=True)
dmax = float((cc.cobertura_ab - cc.cob).abs().max())
ok("B2.01", "cobertura por região × ano recalculada do JSON (média do pcCoberturaAb ponderada pela qtPopulacao nos municípios e meses; "
   "mapa lido de rl_municip_regsaud) = data/processed/cobertura_ab_regsaude_ano: 3,031 pares, 433 regiões × 7 anos; cobertura, "
   "população média, municípios e registros iguais", (cc._merge == "both").all() and len(cc) == 3031 and dmax < 1e-9
   and float((cc.pop_media_x - cc.pop_media_y).abs().max()) < 1e-6 and (cc.n_municipios == cc.n_mun).all() and (cc.n_registros == cc.n_reg).all(),
   f"{len(cc)} pares; máx |Δ cobertura| {dmax:.1e}")
divd = int(((D.pc - 100 * D.qc / D.popu).abs() > 0.5).sum())
q8 = pd.read_csv(TB / f"tab_e8_02_qualidade_v1_{S}.csv", dtype={"uf": str})
sem_reg = sorted(set(rl.CO_MUNICIP) - set(D.cod))
d0 = pd.read_parquet(PROC / f"sinasc_brasil_2015_2024_v3_{S}", columns=["incl", "ano", "raca", "idade_cat", "CO_REGSAUD", "CODMUNRES",
                                                                          "ptb", "pig", "ptb_ind"], filters=[("incl", "==", True)])
n510 = int((d0.CODMUNRES.astype(str) == "510183").sum())
reg510 = rl.CO_REGSAUD[rl.CO_MUNICIP == "510183"].tolist()
inc = P8[~P8.completa]
ok("B2.02", "controles: pc em 0–100 e população > 0 em todo registro; 3,170 registros com |pc − 100·qtCoberturaAb/qtPopulacao| > 0,5 "
   "p.p. (= tab_e8_02_qualidade); 510183 é o único município do mapa sem registro, nenhum nascimento da amostra analítica tem esse "
   "código, e os 7 pares incompletos são a região dele × 7 anos",
   D.pc.between(0, 100).all() and (D.popu > 0).all() and divd == 3170 == int(q8.divergencia_pc_qt_gt_0_5pp.sum()) and sem_reg == ["510183"]
   and n510 == 0 and len(inc) == 7 and set(inc.CO_REGSAUD) == set(reg510), f"divergências {divd}; sem registro {sem_reg}; "
   f"nascimentos 510183 {n510}; incompletos {sorted(set(inc.CO_REGSAUD))}")

d0 = d0[d0.CO_REGSAUD.notna()].copy()
d0["ano"] = d0.ano.astype(int)
d0["CO_REGSAUD"] = d0.CO_REGSAUD.astype(str)
d = d0[d0.ano <= 2021].copy()
d["macro"] = d.CO_REGSAUD.str[0].map(MACRO)
ind = pd.read_csv(PROC / f"indice_acesso_regsaude_ano_v1_{S}.csv", dtype={"CO_REGSAUD": str})
pr = d.groupby(["CO_REGSAUD", "ano"]).size().rename("n").reset_index()
pr["macro"] = pr.CO_REGSAUD.str[0].map(MACRO)
pr = (pr.merge(cob.assign(ano=cob.ano + 1).rename(columns={"reg": "CO_REGSAUD"})[["CO_REGSAUD", "ano", "cob", "pop_media"]], how="left")
      .merge(ind.assign(ano=ind.ano + 1)[["CO_REGSAUD", "ano", "indice"]], how="left"))
assert pr[["cob", "indice"]].notna().all().all()


def tercis(df, col):
    """Implementação própria: dentro da macrorregião, pares ordenados pelo valor (desempate região, ano), cortes onde a fração
    acumulada de nascimentos atinge 1/3 e 2/3; T1 = valor ≤ corte 1."""
    out, cortes = [], {}
    for mac, g in df.groupby("macro"):
        g = g.sort_values([col, "CO_REGSAUD", "ano"])
        cum = g.n.cumsum().to_numpy() / g.n.sum()
        v = g[col].to_numpy()
        c1, c2 = v[np.argmax(cum >= 1 / 3)], v[np.argmax(cum >= 2 / 3)]
        out.append(g.assign(t=np.where(v <= c1, "T1", np.where(v <= c2, "T2", "T3")))[["CO_REGSAUD", "ano", "t"]])
        cortes[mac] = (c1, c2)
    return pd.concat(out), cortes


ta, ca = tercis(pr, "cob")
ti, ci = tercis(pr, "indice")
T8 = pd.read_csv(PROC / f"tercil_aps_regsaude_ano_v1_{S}.csv", dtype={"CO_REGSAUD": str})
cmp_ = T8.merge(ta.rename(columns={"t": "ta"}), on=["CO_REGSAUD", "ano"], how="outer").merge(ti.rename(columns={"t": "ti"}), on=["CO_REGSAUD", "ano"], how="outer")
C8 = pd.read_csv(TB / f"tab_e8_03_cortes_v1_{S}.csv")
ccut = all(np.isclose(C8.set_index(["medida", "regiao"]).loc[(m_, r_), ["corte_T1_T2", "corte_T2_T3"]].to_numpy(), cs[r_]).all()
           for m_, cs in (("tercil_aps", ca), ("tercil_ind21", ci)) for r_ in MACRO.values())
ok("B3.01", "tercis recalculados com implementação própria (nascimentos 2015–2021 com região de saúde; cobertura e índice t−1) = "
   "tercil_aps_regsaude_ano em todos os pares, nas duas medidas; cortes = tab_e8_03_cortes",
   len(cmp_) == len(pr) == len(T8) and (cmp_.tercil_aps == cmp_.ta).all() and (cmp_.tercil_ind21 == cmp_.ti).all() and ccut,
   f"{len(cmp_):,} pares; diferentes: aps {int((cmp_.tercil_aps != cmp_.ta).sum())}, índice {int((cmp_.tercil_ind21 != cmp_.ti).sum())}")
pr = pr.merge(ta.rename(columns={"t": "ta"}), on=["CO_REGSAUD", "ano"]).merge(ti.rename(columns={"t": "ti"}), on=["CO_REGSAUD", "ano"])
sp8 = pd.read_csv(TB / f"tab_e8_03_spearman_v1_{S}.csv").set_index(["par", "estrato"]).rho
rho_ = {("cobertura_x_indice", "Brasil"): stats.spearmanr(pr.cob, pr.indice)[0], ("cobertura_x_populacao", "Brasil"): stats.spearmanr(pr.cob, pr.pop_media)[0]}
rho_.update({(p_, m_): stats.spearmanr(g.cob, g[c_])[0] for p_, c_ in (("cobertura_x_indice", "indice"), ("cobertura_x_populacao", "pop_media"))
             for m_, g in pr.groupby("macro")})
kap = cohen_kappa_score(pr.ta, pr.ti, weights="linear", sample_weight=pr.n)
diag = 100 * pr.n[pr.ta == pr.ti].sum() / pr.n.sum()
cr8 = pd.read_csv(TB / f"tab_e8_03_concordancia_resumo_v1_{S}.csv").iloc[0]
dd = d.merge(pr[["CO_REGSAUD", "ano", "ta", "ti"]], on=["CO_REGSAUD", "ano"])
rp_ = {(m_, str(r_)): v_ for m_, c_ in (("tercil_aps", "ta"), ("tercil_ind21", "ti"))
       for r_, v_ in pd.crosstab(dd.raca.astype(str), dd[c_], normalize="index").mul(100).iterrows()}
rp8 = pd.read_csv(TB / f"tab_e8_03_raca_por_tercil_v1_{S}.csv")
drp = max(float(np.abs(rp8.set_index(["medida", "raca"]).loc[k, ["T1", "T2", "T3"]].to_numpy() - v[["T1", "T2", "T3"]].to_numpy()).max()) for k, v in rp_.items())
ok("B3.02", "descritivos recalculados: Spearman cobertura × índice e cobertura × população (Brasil e macrorregiões), kappa ponderado "
   "linear (sklearn, pesos = nascimentos), % na diagonal e distribuição de cada raça entre os tercis = tabelas do etapa8_03; N = 18,624,544",
   len(rho_) == 12 and all(abs(sp8[k] - v) < 1e-12 for k, v in rho_.items()) and abs(kap - cr8.kappa_ponderado_linear) < 1e-9
   and abs(diag - cr8.pct_diagonal) < 1e-9 and drp < 1e-9 and len(rp_) == 8 and len(dd) == len(d) == 18624544 == int(cr8.n_nasc),
   f"ρ índice {rho_[('cobertura_x_indice', 'Brasil')]:.4f}; ρ população {rho_[('cobertura_x_populacao', 'Brasil')]:.4f}; κ {kap:.4f}; "
   f"diagonal {diag:.2f}%; máx |Δ| raça {drp:.1e}")

# modelos refeitos com statsmodels: células próprias (raça × idade × ano × macrorregião × tercil × região de saúde), desenho próprio
it8 = pd.read_csv(TB / f"tab_e8_04_interacao_v1_{S}.csv").set_index(["exposicao", "desfecho", "raca", "nivel"])
wd8 = pd.read_csv(TB / f"tab_e8_04_wald_v1_{S}.csv").set_index(["exposicao", "desfecho"])
RAC = ["Parda", "Preta", "Indigena"]
Z = stats.norm.ppf(0.975)


def desenho(c, raca, ter):
    X = {"const": np.ones(len(c))}
    X.update({f"r_{g}": (raca == g) for g in RAC})
    X.update({f"i_{a}": (c.idade_cat == a) for a in sorted(c.idade_cat.unique())[1:]})
    X.update({f"a_{a}": (c.ano == a) for a in sorted(c.ano.unique())[1:]})
    X.update({f"m_{m}": (c.macro == m) for m in sorted(c.macro.unique())[1:]})
    X.update({f"t_{t}": (ter == t) for t in ("T1", "T2")})
    X.update({f"x_{g}_{t}": (raca == g) & (ter == t) for g in RAC for t in ("T1", "T2")})
    return pd.DataFrame(X).astype(float)


dd["raca"] = dd.raca.astype(str)
dd["idade_cat"] = dd.idade_cat.astype(str)
mods_ = {}
for ex_, col_ in (("tercil_aps", "ta"), ("tercil_ind21", "ti")):
    for y_ in OUTC:
        s_ = dd[dd[y_].notna()]
        c = s_.groupby(["raca", "idade_cat", "ano", "macro", col_, "CO_REGSAUD"], observed=True)[y_].agg(["sum", "size"]).reset_index()
        c = c.rename(columns={"sum": "Y", "size": "n", col_: "ter"})
        X = desenho(c, c.raca, c.ter)
        f = sm.GLM(c.Y.astype(float), X, family=sm.families.Poisson(), offset=np.log(c.n.astype(float))).fit(
            cov_type="cluster", cov_kwds={"groups": pd.factorize(c.CO_REGSAUD)[0]})
        b, V = f.params.to_numpy(), f.cov_params().to_numpy()
        n = c.n.to_numpy(float)
        P, Gr = {}, {}
        for g in ["Branca"] + RAC:
            for t in ("T1", "T2", "T3"):
                Xg = desenho(c, pd.Series(g, index=c.index), pd.Series(t, index=c.index)).to_numpy()
                mu = np.exp(Xg @ b)
                P[g, t], Gr[g, t] = (n * mu).sum() / n.sum(), (Xg * (n * mu)[:, None]).sum(0) / n.sum()
        res = {}
        for g in RAC:
            for t in ("T1", "T2"):
                v = (P[g, t] - P["Branca", t]) - (P[g, "T3"] - P["Branca", "T3"])
                gr = (Gr[g, t] - Gr["Branca", t]) - (Gr[g, "T3"] - Gr["Branca", "T3"])
                se = float(np.sqrt(gr @ V @ gr))
                res[g, t] = (100 * v, 100 * (v - Z * se), 100 * (v + Z * se))
        nm = list(X.columns)
        i2 = [nm.index(f"x_Indigena_{t}") for t in ("T1", "T2")]
        i6 = [nm.index(f"x_{g}_{t}") for g in RAC for t in ("T1", "T2")]
        w2 = float(b[i2] @ np.linalg.solve(V[np.ix_(i2, i2)], b[i2]))
        w6 = float(b[i6] @ np.linalg.solve(V[np.ix_(i6, i6)], b[i6]))
        mods_[ex_, y_] = (res, w2, w6, int(n.sum()), len(np.unique(c.CO_REGSAUD)))
for k_, (ex_, y_) in enumerate(mods_):
    res, w2, w6, N_, G_ = mods_[ex_, y_]
    dpt = max(abs(res[g, t][0] - it8.ICR_pp[(ex_, y_, g, t)]) for g, t in res)
    dci = max(max(abs(res[g, t][1] - it8.ICR_lo[(ex_, y_, g, t)]), abs(res[g, t][2] - it8.ICR_hi[(ex_, y_, g, t)])) for g, t in res)
    wr = max(abs(w2 / wd8.chi2_ind_2gl[(ex_, y_)] - 1), abs(w6 / wd8.chi2_6gl[(ex_, y_)] - 1))
    ok(f"B4.{k_ + 1:02d}", f"modelo refeito com statsmodels ({ex_}, {y_}): IC das 3 raças × T1/T2 = tab_e8_04_interacao (ponto |Δ| < 1e-5 "
       "p.p.; limites |Δ| < 0.005 p.p., a correção de pequenas amostras do statsmodels usa o nº de células); Wald de 6 gl e indígena de "
       "2 gl (|Δ| relativo < 0.002); N e G = tab_e8_04_wald",
       dpt < 1e-5 and dci < 0.005 and wr < 0.002 and N_ == int(wd8.N[(ex_, y_)]) and G_ == int(wd8.G[(ex_, y_)]) == 433,
       f"IC Indígena×T1 {res['Indigena', 'T1'][0]:.4f} ({res['Indigena', 'T1'][1]:.4f} a {res['Indigena', 'T1'][2]:.4f}); máx |Δ| ponto "
       f"{dpt:.1e}, limites {dci:.1e}; Wald |Δ| rel {wr:.1e}; N {N_:,}; G {G_}")
del d0, d, dd

# ======================= P. pacote v12 × v13 =======================
J12l = json.load(open(A12 / f"numeros_chave_{V12}.json"))
J13l = json.load(open(MS / f"numeros_chave_{V13}.json"))
J12, J13 = {i["id"]: i for i in J12l}, {i["id"]: i for i in J13l}
REG = {"n_regsaude_CE", "n_regsaude_DF"}
NOVOS = ([f"{p_}_{s_}_{y_}" for s_ in EXP.values() for y_ in OUTC for p_ in ("IC_Ind_T1", "Wald2_ind")]
         + ["N_aps_2015_2021", "rho_cobertura_x_indice", "rho_cobertura_x_populacao", "kappa_aps_indice", "pct_concordancia_aps_indice"]
         + [f"pct_Ind_{t_}_{s_}" for s_ in EXP.values() for t_ in ("T1", "T3")])
dif = {k: [c for c in J12[k] if c != "commit_pacote" and J12[k][c] != J13[k].get(c)
           and not (k in REG and c in ("commit_registro", "commit_analise") and J13[k][c] == BASE and J12[k][c] == "")] for k in J12 if k in J13}
ok("P1.01", "números-chave: 249 = os 228 da v12 (mesma ordem) + os 21 da Etapa 8 no fim; nos 228, todos os campos iguais, fora o "
   "commit_pacote e, em n_regsaude_CE/DF, commit_registro e commit_analise (vazios na v12, dc54fb9 agora que ela foi arquivada)",
   len(J13l) == 249 and [i["id"] for i in J13l[:228]] == [i["id"] for i in J12l] and [i["id"] for i in J13l[228:]] == NOVOS
   and not any(dif.values()) and all(set(J13[k]) == set(J12[k]) for k in J12)
   and all(J13[k]["commit_registro"] == J13[k]["commit_analise"] == BASE for k in REG), f"com diferença {[k for k, v in dif.items() if v][:3]}")
ok("P1.02", "commit_pacote: v13 = dc54fb9 em todos (HEAD ao gerar); v12 = dc9328d em todos",
   {i["commit_pacote"] for i in J13l} == {BASE} and {i["commit_pacote"] for i in J12l} == {"dc9328d"})
esp = {}
TXT = {"tercil_aps": "primary health care coverage tertiles", "tercil_ind21": "access index tertiles recomputed in 2015\u20132021"}
for ex_, s_ in EXP.items():
    for y_ in OUTC:
        r_ = it8.loc[(ex_, y_, "Indigena", "T1")]
        esp[f"IC_Ind_T1_{s_}_{y_}"] = (r_.ICR_pp, rd_(r_.ICR_pp, r_.ICR_lo, r_.ICR_hi), "tab_e8_04_interacao", "scripts/etapa8_04_modelos.py",
                                       f"IC Indigenous\u00d7T1, {TXT[ex_]}, births 2015\u20132021, {OUTC[y_]}",
                                       f"exposicao={ex_}, desfecho={y_}, raca=Indigena, nivel=T1")
        p_ = wd8.p_ind_2gl[(ex_, y_)]
        esp[f"Wald2_ind_{s_}_{y_}"] = (p_, pv(p_), "tab_e8_04_wald", "scripts/etapa8_04_modelos.py",
                                       f"Wald p, Indigenous terms (2 df), {TXT[ex_]}, births 2015\u20132021, {OUTC[y_]}", f"exposicao={ex_}, desfecho={y_}")
nN = int(wd8.N[("tercil_aps", "ptb")])
esp["N_aps_2015_2021"] = (nN, f"{nN:,}", "tab_e8_04_wald", "scripts/etapa8_04_modelos.py",
                          "Births 2015\u20132021 with a health region (sample of the primary health care coverage analysis, preterm birth (total))",
                          "exposicao=tercil_aps, desfecho=ptb")
for p_, t_ in (("cobertura_x_indice", "the access index"), ("cobertura_x_populacao", "the population of the health region")):
    esp[f"rho_{p_}"] = (sp8[(p_, "Brasil")], num2(sp8[(p_, "Brasil")]), "tab_e8_03_spearman", "scripts/etapa8_03_tercis.py",
                        f"Spearman correlation between primary health care coverage and {t_} (previous year), health region-years of births 2015\u20132021",
                        f"par={p_}, estrato=Brasil")
esp["kappa_aps_indice"] = (cr8.kappa_ponderado_linear, num2(cr8.kappa_ponderado_linear), "tab_e8_03_concordancia_resumo", "scripts/etapa8_03_tercis.py",
                           "Linear-weighted kappa between primary health care coverage tertiles and access index tertiles (births 2015\u20132021)", "")
esp["pct_concordancia_aps_indice"] = (cr8.pct_diagonal, pc1(cr8.pct_diagonal), "tab_e8_03_concordancia_resumo", "scripts/etapa8_03_tercis.py",
                                      "Births in the same tertile of primary health care coverage and of the access index, % (births 2015\u20132021)", "")
for ex_, s_ in EXP.items():
    for t_ in ("T1", "T3"):
        v_ = rp8.set_index(["medida", "raca"]).loc[(ex_, "Indigena"), t_]
        esp[f"pct_Ind_{t_}_{s_}"] = (v_, pc1(v_), "tab_e8_03_raca_por_tercil", "scripts/etapa8_03_tercis.py",
                                     f"Indigenous births in {t_} of {TXT[ex_]}, % (births 2015\u20132021)", f"medida={ex_}, raca=Indigena")
ruim_n = [k for k, (v_, f_, a_, s_, de_, fi_) in esp.items()
          if not (np.isclose(J13[k]["valor_bruto"], v_, rtol=1e-12, atol=0) and J13[k]["valor_formatado"] == f_
                  and J13[k]["arquivo"] == f"outputs/tables/{a_}_v1_{S}.csv" and J13[k]["script"] == s_ and J13[k]["descricao"] == de_
                  and J13[k]["filtro"] == fi_ and J13[k]["commit_registro"] == J13[k]["commit_analise"] == "")]
ok("P1.03", "os 21 da Etapa 8 = recalculados aqui das tabelas da etapa (valor bruto, formatação própria, arquivo, script, descrição e "
   "filtro); commit_registro e commit_analise vazios", len(esp) == 21 and not ruim_n, f"divergentes {ruim_n[:3]}")
pares = [(A12 / d_ / f.name, MS / d_ / f.name.replace(V12, V13)) for d_ in ("tabelas", "suplementar") for f in sorted((A12 / d_).glob(f"*_{V12}.csv"))]
ig = [b.name for a, b in pares if a.read_bytes() == b.read_bytes()]
s2a = pd.read_csv(A12 / "suplementar" / f"S2b_access_specifications_{V12}.csv", dtype=str)
s2n = pd.read_csv(MS / "suplementar" / f"S2b_access_specifications_{V13}.csv", dtype=str)
COLN = {"tercil_aps": "(d) Primary health care coverage tertiles, 2015\u20132021", "tercil_ind21": "(e) Access index tertiles, 2015\u20132021"}
NOVAS = [f"{COLN[e_]}: {k_}" for e_ in EXP for k_ in ("IC Indigenous\u00d7T1 per 100 (95% CI)", "Wald p, Indigenous terms (2 df)")]
cel_s2b = [s2n.loc[i, NOVAS[2 * j]] == esp[f"IC_Ind_T1_{s_}_{y_}"][1] and s2n.loc[i, NOVAS[2 * j + 1]] == esp[f"Wald2_ind_{s_}_{y_}"][1]
           for i, y_ in enumerate(OUTC) for j, s_ in enumerate(EXP.values())]
ok("P2.01", "CSVs de tabelas/ e suplementar/: 19 dos 20 da v13 idênticos byte a byte aos da v12; na S2b, as 5 colunas da v12 iguais e "
   "4 colunas novas no fim, com IC e Wald recalculados aqui (formatação própria)",
   len(pares) == 20 and len(ig) == 19 and [b.name for a, b in pares if b.name not in ig] == [f"S2b_access_specifications_{V13}.csv"]
   and s2n[list(s2a.columns)].equals(s2a) and list(s2n.columns) == list(s2a.columns) + NOVAS and list(s2n.Outcome) == list(OUTC.values())
   and all(cel_s2b), f"{len(ig)}/{len(pares)} idênticos; S2b {sum(cel_s2b)}/{len(cel_s2b)} células novas")


def celulas(f):
    wb = openpyxl.load_workbook(f)
    return {(ws.title, c.coordinate): c.value for ws in wb.worksheets for row in ws.iter_rows() for c in row if c.value is not None}


x12, x13 = celulas(A12 / "tabelas" / f"tabelas_principais_{V12}.xlsx"), celulas(MS / "tabelas" / f"tabelas_principais_{V13}.xlsx")
dx = sorted(k for k in set(x12) | set(x13) if x12.get(k) != x13.get(k))
ok("P2.02", "xlsx das tabelas principais: uma só célula diferente, o rodapé da Tabela 4, com a nota 'n.a.' logo antes de 'Sources:'",
   len(dx) == 1 and dx[0][0].startswith("tab04_") and str(x12[dx[0]]).count(ANTES_NA) == 1
   and x13[dx[0]] == str(x12[dx[0]]).replace(ANTES_NA, "births without a health region. " + NOTA_NA + "Sources:"), dx)
e12, e13, es = (celulas(A12 / "suplementar" / f"ESM_1_tables_S1_S6_{V12}.xlsx"), celulas(MS / "suplementar" / f"ESM_1_tables_S1_S6_{V13}.xlsx"),
                celulas(SUB / "ESM_1.xlsx"))
ABA = "S2b_access_specifications"
de = sorted(k for k in set(e12) | set(e13) if e12.get(k) != e13.get(k))
f_ = lambda k: esp[k][1]
DE8 = ("(d) Tertiles, defined within each macroregion as in (a), of primary health care coverage (Family Health Strategy teams and other primary care teams, "
       "parameterized or equivalent by professional working hours; Ministry of Health public report Cobertura da Aten\u00e7\u00e3o B\u00e1sica, 2007\u20132020) in the "
       "mother's health region of residence in the previous year: population-weighted mean of the official municipal monthly coverage "
       "over the 12 months; T1 = lowest coverage. Births 2015\u20132021 only, because the official series ends in December 2020 "
       f"({f_('N_aps_2015_2021')} births for preterm birth (total)). (e) Comparator for (d): tertiles of the access index "
       "recomputed in the same births (2015\u20132021) with the same algorithm. Primary health care coverage measures the supply of "
       "teams relative to the population, not the use of prenatal care: across health region-years it was weakly correlated with the "
       f"access index (Spearman \u03c1 = {f_('rho_cobertura_x_indice')}) and inversely with the population of the health region "
       f"(\u03c1 = {f_('rho_cobertura_x_populacao')}); coverage and access index tertiles agreed for {f_('pct_concordancia_aps_indice')} of "
       f"births (linear-weighted \u03ba = {f_('kappa_aps_indice')}); {f_('pct_Ind_T3_aps')} of Indigenous births were in the highest "
       f"coverage tertile and {f_('pct_Ind_T1_aps')} in the lowest (access index, 2015\u20132021: {f_('pct_Ind_T1_indice_2015_2021')} in T1 "
       f"and {f_('pct_Ind_T3_indice_2015_2021')} in T3). ")
R8 = [("better access). IC (interaction contrast)", "better access). " + DE8 + "IC (interaction contrast)"),
      ("The Wald test jointly tests the 6 race \u00d7 tertile interaction terms (Brown, Black, and Indigenous \u00d7 T1 and T2; 6 df). 95% CIs",
       "In (b), the Wald test jointly tests the 6 race \u00d7 tertile interaction terms (Brown, Black, and Indigenous \u00d7 T1 and T2; 6 df); "
       "in (d) and (e), it jointly tests the Indigenous \u00d7 T1 and Indigenous \u00d7 T2 terms (2 df), with the same cluster-robust covariance. 95% CIs"),
      ("(b) and (c) belong", "(b) to (e) belong"),
      ("tab_e3_03a_indice_continuo_rs.", "tab_e3_03a_indice_continuo_rs, tab_e8_04_interacao, tab_e8_04_wald, tab_e8_03_spearman, "
                                         "tab_e8_03_concordancia_resumo, tab_e8_03_raca_por_tercil.")]
k_rod = [k for k in de if k[0] == ABA and isinstance(e12.get(k), str) and "Sources:" in e12[k]]
rod_esp = e12[k_rod[0]] if k_rod else ""
um = all(rod_esp.count(a) == 1 for a, _ in R8)
for a, b_ in R8:
    rod_esp = rod_esp.replace(a, b_)
k_tit = [k for k in de if k[0] == ABA and str(e12.get(k, "")).startswith("Table S2b.")]
novas_cel = sorted(str(e13[k]) for k in de if k[0] == ABA and k not in k_rod + k_tit)
esp_cel = sorted(NOVAS + [esp[f"{p_}_{s_}_{y_}"][1] for s_ in EXP.values() for y_ in OUTC for p_ in ("IC_Ind_T1", "Wald2_ind")])
ok("P2.03", "ESM_1 (pacote e Submissao/): fora da aba S2b, todas as células iguais às da v12; na S2b, mudam só o título (novo), o rodapé "
   "(o da v12 com (d) e (e) definidos, números = números-chave recalculados aqui, Wald de 2 gl, '(b) to (e)' e as fontes novas) e entram "
   "4 cabeçalhos e 12 células novas", e13 == es and all(k[0] == ABA for k in de) and len(k_rod) == 1 and len(k_tit) == 1 and um
   and e13[k_rod[0]] == rod_esp and e13[k_tit[0]] == "Table S2b. Alternative specifications of access to early prenatal care and of primary health care coverage"
   and e12[k_tit[0]] == "Table S2b. Alternative specifications of access to early prenatal care" and novas_cel == esp_cel,
   f"{len(de)} células diferentes; rodapé {'igual' if k_rod and e13[k_rod[0]] == rod_esp else 'DIFERENTE'}; novas {len(novas_cel)}")
t4 = pd.read_csv(MS / "tabelas" / f"tab04_sensitivity_{V13}.csv", dtype=str).fillna("")


def explica(cen, col, v):                     # regra própria: a que a nota "n.a." (e a frase da imputação múltipla) descreve
    if v in ("n.a. (unchanged)", "n.a. (not reclassified)"):
        return True
    if cen.startswith("GA in days"):
        return not col.startswith("SGA")
    if cen.startswith(("Dating-robust", "Weight >P97")):
        return col.startswith("SGA")
    if cen.startswith("Live-birth bounds"):
        return col.startswith("Provider-initiated") or "IC Indigenous" in col or "Wald" in col
    if cen.startswith("Unclassified preterm births"):
        return col.startswith("Preterm birth (total)") and "Wald" in col
    if cen.startswith("Multiple imputation"):
        return "Wald" in col
    return False


na_c = [(r_.Scenario, c_, r_[c_]) for _, r_ in t4.iterrows() for c_ in t4.columns if r_[c_].startswith("n.a.")]
na_x = [(a[:30], b) for a, b, v in na_c if not explica(a, b, v)]
ok("P2.04", "Tabela 4: as 38 células 'n.a.' têm explicação no rodapé (nota geral nova ou frase da imputação múltipla, regra própria); "
   "a nota está no rodapé do xlsx e do docx", len(na_c) == 38 and not na_x and NOTA_NA in x13[dx[0]] if dx else False,
   f"{len(na_c)} células n.a.; sem explicação {na_x}")
d12, d13 = docx.Document(A12 / "tabelas" / f"tabelas_principais_{V12}.docx"), docx.Document(MS / "tabelas" / f"tabelas_principais_{V13}.docx")
p12, p13 = [p.text for p in d12.paragraphs], [p.text for p in d13.paragraphs]
c12_ = [c.text for t in d12.tables for r in t.rows for c in r.cells]
c13_ = [c.text for t in d13.tables for r in t.rows for c in r.cells]
dp = [(a, b) for a, b in zip(p12, p13) if a != b]
ok("P3.01", "docx: células iguais; parágrafos diferentes só no rótulo de versão e na nota 'n.a.' (uma vez, no rodapé da Tabela 4)",
   c12_ == c13_ and len(p12) == len(p13) and all(b == a.replace(V12, V13).replace(ANTES_NA, "births without a health region. " + NOTA_NA + "Sources:")
                                                 for a, b in dp) and sum(t.count(NOTA_NA.strip()) for t in p13) == 1, f"{len(dp)} parágrafos diferentes")
txt = lambda f: "\n".join(pg.get_text() for pg in pymupdf.open(f))
pdfs = [("suplementar", "S7_variables_codes_{}.pdf"), ("suplementar", "S8_strobe_record_checklist_{}.pdf")]
pdf_ok = [n for d_, n in pdfs if txt(A12 / d_ / n.format(V12)) == txt(MS / d_ / n.format(V13))]
esm = {2: MS / "suplementar" / f"S7_variables_codes_{V13}.pdf", 3: MS / "suplementar" / f"S8_strobe_record_checklist_{V13}.pdf"}
ok("P3.02", "PDFs: S7 e S8 com o mesmo texto da v12; ESM_2 e ESM_3 = S7 e S8 da v13 (MD5); ESM_2–4 com o mesmo texto da v12",
   len(pdf_ok) == 2 and all(md5((SUB / f"ESM_{k}.pdf").read_bytes()) == md5(f.read_bytes()) for k, f in esm.items())
   and all(txt(SUB / f"ESM_{k}.pdf") == txt(A12 / "Submissao" / f"ESM_{k}.pdf") for k in (2, 3, 4)))
pix = lambda f: (lambda im: (im.size, im.mode, im.info.get("dpi"), md5(im.tobytes())))(Image.open(f))
ims = [f for d_ in ("figuras", "suplementar") for f in sorted((A12 / d_).glob(f"*_{V12}.*")) if f.suffix in (".png", ".tif")]
im_ok = [f.name for f in ims if pix(f) == pix(MS / f.parent.name / f.name.replace(V12, V13))]
fig_sub = [k for k in range(1, 5) if pix(SUB / f"Fig{k}.tif") == pix(A12 / "Submissao" / f"Fig{k}.tif")]
ok("P3.03", "imagens: figuras 1–4 e S9 (png e tif) com os mesmos pixels, modo e dpi da v12; Fig1–4 de Submissao/ idem",
   len(ims) == 10 and len(im_ok) == 10 and len(fig_sub) == 4, f"{len(im_ok)}/{len(ims)}; Submissao {len(fig_sub)}/4")
norm = lambda t, v: [re.sub(r"\| [0-9a-f]{12} \|$", "| MD5 |", l.replace(v, "VX")) for l in t.splitlines()]
m12, m13 = norm((A12 / f"MANIFEST_{V12}.md").read_text(), V12), norm((MS / "MANIFEST.md").read_text(), V13)
dm = [(a, b) for a, b in zip(m12, m13) if a != b]
COR = ("índice contínuo; EP por região de saúde", "índice contínuo; cobertura da Atenção Básica e índice, 2015–2021; EP por região de saúde")
FON = ("tab_e3_03a_indice_continuo_rs (EP por região de saúde)", "tab_e3_03a_indice_continuo_rs, tab_e8_04_interacao, tab_e8_04_wald, "
       "tab_e8_03_spearman, tab_e8_03_concordancia_resumo, tab_e8_03_raca_por_tercil (EP por região de saúde)")
ok("P4.01", "MANIFEST (versão e MD5 normalizados): mesmas linhas da v12; mudam só o título (Etapas 7b–8), o parágrafo de abertura (data, "
   "commit dc54fb9, etapa, 'no pacote', v13), a linha da S2b na correspondência e a linha do CSV da S2b (fontes da Etapa 8)",
   len(m12) == len(m13) and len(dm) == 4 and dm[0][1] == dm[0][0].replace("Etapas 7b–7c.7", "Etapas 7b–8")
   and "v13 = v12 com a cobertura da Atenção Básica na Tabela S2b" in dm[1][1] and "Commit do repositório ao gerar o pacote: dc54fb9" in dm[1][1]
   and f"'{TITULO}'). Nenhuma análise nova no pacote" in dm[1][1] and dm[2][1] == dm[2][0].replace(*COR) and dm[3][1] == dm[3][0].replace(*FON),
   [b[:70] for a, b in dm])
lm = (MS / "MANIFEST.md").read_text().splitlines()
lin = [re.match(r"^\| ((?:manuscrito|Submissao)/\S+) \| .* \| ([0-9a-f]{12}) \|$", l) for l in lm if re.match(r"^\| (manuscrito|Submissao)/", l)]
lugar = lambda c: (MS / c[len("manuscrito/"):]) if c.startswith("manuscrito/") else PROJ / c
md_ok = [m and md5(lugar(m.group(1)).read_bytes())[:12] == m.group(2) for m in lin]
ok("P4.02", "MANIFEST: o MD5 de cada arquivo listado confere com o arquivo (calculado aqui)", bool(lin) and all(md_ok), f"{sum(map(bool, md_ok))}/{len(lin)}")
espm = []
for pasta, rot in [(MS / "tabelas", "manuscrito/tabelas"), (MS / "figuras", "manuscrito/figuras"), (MS / "suplementar", "manuscrito/suplementar"),
                   (MS, "manuscrito"), (SUB, "Submissao")]:
    espm += [f"{rot}/{f.name}" for f in sorted(pasta.iterdir()) if f.is_file() and not f.name.startswith(("._", "_", "audita_")) and f.name != "MANIFEST.md"]
lis = [m.group(1) for m in lin if m]
ok("P4.03", "MANIFEST completo: lista exatamente os arquivos das pastas do pacote, da raiz de outputs/manuscrito e de Submissao/, fora "
   "._*, _*, audita_* e ele mesmo; nenhum repetido", sorted(lis) == sorted(espm) and len(set(lis)) == len(lis),
   f"{len(lis)} listados; faltam {sorted(set(espm) - set(lis))[:3]}; sobram {sorted(set(lis) - set(espm))[:3]}")
tab = [l for l in lm if l.startswith("|")]
ok("P4.04", "MANIFEST: toda linha de tabela tem o número certo de | não escapados (4 na correspondência S → ESM, 5 nos arquivos)",
   all(len(re.findall(r"(?<!\\)\|", l)) in (4, 5) for l in tab) and all(len(re.findall(r"(?<!\\)\|", l)) == 5 for l in lm if re.match(r"^\| (manuscrito|Submissao)/", l)),
   [l[:60] for l in tab if len(re.findall(r"(?<!\\)\|", l)) not in (4, 5)][:3])
dc12 = " ".join((A12 / f"data_code_availability_{V12}.md").read_text().split())
dc13 = " ".join((MS / "data_code_availability.md").read_text().split())
tot = re.search(r"Total: 27 UFs; ([\d,]+) registros; ([\d,]+) municípios", acc).groups()
dia = sorted(set(re.findall(r"^(\d{4}-\d{2}-\d{2}) \d", acc, flags=re.M)))
FONTE = ('- **Primary health care coverage, 2014–2020** (Ministry of Health, public report "Cobertura da Atenção Básica (2007 - 2020)", '
         "https://relatorioaps.saude.gov.br/cobertura/ab), for the sensitivity analysis in Table S2b: municipal monthly coverage queried through "
         "the report's own interface (`https://relatorioaps-prd.saude.gov.br/cobertura/ab`, municipal level, January 2014 to December 2020, one "
         f"query per state) on {dia[0]}; {tot[0]} records ({tot[1]} municipalities); sizes and MD5 of the 27 files in "
         "docs/referencias/aps_cobertura_ab/ACESSO.txt. ")
DECL = (" the Ministry of Health primary > health care coverage report (Cobertura da Atenção Básica, 2007–2020), and the 2022 Census", " and the 2022 Census")
volta = (dc13.replace(FONTE, "").replace(*DECL).replace(V13, V12).replace(TITULO, "Etapa 7c.7: pacote v12 com as decisões da 7c.6b")
         .replace('`git log --grep "^Etapa 8:"`', '`git log --grep "^Etapa 7c.7:"`').replace("Etapa 8)", "Etapa 7c.7)"))
ok("P5.01", "disponibilidade: a fonte nova (data da consulta, registros e municípios = ACESSO.txt, recontados aqui) e o relatório na "
   "declaração; o resto igual à v12, fora versão, etapa e commit de referência (grep '^Etapa 8:'); legendas iguais, fora o rótulo de versão",
   tot == (f"{len(D):,}", f"{nmun:,}") and len(dia) == 1 and dc13.count(FONTE) == 1 and dc13.count(DECL[0]) == 1 and volta == dc12
   and dc13.count('`git log --grep "^Etapa 8:"`') == 1
   and (MS / "legendas_figuras.md").read_text().replace(V13, V12) == (A12 / f"legendas_figuras_{V12}.md").read_text(),
   "ok" if volta == dc12 else [i for i, (a, b) in enumerate(zip(volta, dc12)) if a != b][:1])

# ======================= C. scripts =======================
TROCAS = {   # arquivo: [(trecho em dc54fb9, trecho agora)]; cada trecho velho ocorre uma vez, e aplicar todas reproduz o arquivo atual
    "scripts/etapa7b_lib.py": [
        ('V = "v12_20261013"               # versão/data do pacote (v12 = Etapa 7c.7: rodapé da Tabela 4 e regiões de saúde de CE/DF; v1–v11 em outputs/manuscrito/_arquivo_v1.._v11)',
         'V = "v13_20261013"               # versão/data do pacote (v13 = Etapa 8: cobertura da Atenção Básica na S2b e nota "n.a." da Tabela 4; v1–v12 em outputs/manuscrito/_arquivo_v1.._v12)'),
        ('''    "tab_e7c7_01_regsaude_uf": "scripts/etapa7c7_01_regsaude_uf.py",
}''', '''    "tab_e7c7_01_regsaude_uf": "scripts/etapa7c7_01_regsaude_uf.py",
    # Etapa 8: sensibilidade com a cobertura da Atenção Básica (2015–2021), EP por região de saúde
    "tab_e8_03_concordancia_resumo": "scripts/etapa8_03_tercis.py",
    "tab_e8_03_spearman": "scripts/etapa8_03_tercis.py",
    "tab_e8_03_raca_por_tercil": "scripts/etapa8_03_tercis.py",
    "tab_e8_04_interacao": "scripts/etapa8_04_modelos.py",
    "tab_e8_04_wald": "scripts/etapa8_04_modelos.py",
}'''),
        ('md = ["# Key numbers (Etapas 7b–7c.7)"', 'md = ["# Key numbers (Etapas 7b–8)"')],
    "scripts/etapa7b_01_tabelas.py": [
        ('''        "births without a health region. "
        "Sources: tab_e6_01a_m2, tab_e6_01a_wald,''',
         '''        "births without a health region. " + NOTA_NA +
        "Sources: tab_e6_01a_m2, tab_e6_01a_wald,'''),
        ('''T4 = pd.DataFrame(rows).fillna("n.a.")
''', '''T4 = pd.DataFrame(rows).fillna("n.a.")
# Etapa 8: nota geral para as células "n.a." (decisão da 7c.6b, redação 8; aprovada na Etapa 8 para a v13)
NOTA_NA = ("n.a., not applicable or not estimated. Gestational age in days changes SGA only; the dating-robust analysis and the weight "
           ">P97 reclassification do not apply to SGA; live-birth bounds were computed only for preterm birth (total) and SGA, as a "
           "correction of the PR M2 without a race\\u00d7tertile model, so IC and Wald tests are not estimated. 'Unchanged' and 'not "
           "reclassified': the scenario does not change the outcome, so the main-analysis estimates apply; for the unclassified-preterm-"
           "birth scenarios this also holds for the Wald tests of total preterm birth. ")
'''),
        ('''B.grava_xlsx(XL, B.TABD / f"tabelas_principais_{B.V}.xlsx")''',
         '''# Etapa 8: sensibilidade com a cobertura da Atenção Básica (nascimentos de 2015–2021; S2b, colunas d e e), EP por região de saúde
e8i = B.rd("tab_e8_04_interacao").query("raca == 'Indigena' and nivel == 'T1'").set_index(["exposicao", "desfecho"])
e8w = B.rd("tab_e8_04_wald").set_index(["exposicao", "desfecho"])
assert (e8w.G == 433).all()
ROT8 = {"tercil_aps": ("aps", "primary health care coverage tertiles"),
        "tercil_ind21": ("indice_2015_2021", "access index tertiles recomputed in 2015\\u20132021")}
for ex_, (sf_, txt_) in ROT8.items():
    for d_ in ["ptb", "pig", "ptb_ind"]:
        y, w = e8i.loc[(ex_, d_)], e8w.loc[(ex_, d_)]
        R.add(f"IC_Ind_T1_{sf_}_{d_}", float(y.ICR_pp), B.rd_(y.ICR_pp, y.ICR_lo, y.ICR_hi), "tab_e8_04_interacao",
              f"IC Indigenous\\u00d7T1, {txt_}, births 2015\\u20132021, {B.OUTC[d_]}", f"exposicao={ex_}, desfecho={d_}, raca=Indigena, nivel=T1")
        R.add(f"Wald2_ind_{sf_}_{d_}", float(w.p_ind_2gl), B.pval(w.p_ind_2gl), "tab_e8_04_wald",
              f"Wald p, Indigenous terms (2 df), {txt_}, births 2015\\u20132021, {B.OUTC[d_]}", f"exposicao={ex_}, desfecho={d_}")
R.add("N_aps_2015_2021", int(e8w.N[("tercil_aps", "ptb")]), B.n_(e8w.N[("tercil_aps", "ptb")]), "tab_e8_04_wald",
      "Births 2015\\u20132021 with a health region (sample of the primary health care coverage analysis, preterm birth (total))",
      "exposicao=tercil_aps, desfecho=ptb")
sp8 = B.rd("tab_e8_03_spearman").query("estrato == 'Brasil'").set_index("par")
for par_, txt_ in (("cobertura_x_indice", "the access index"), ("cobertura_x_populacao", "the population of the health region")):
    R.add(f"rho_{par_}", float(sp8.rho[par_]), B.num(sp8.rho[par_]), "tab_e8_03_spearman",
          f"Spearman correlation between primary health care coverage and {txt_} (previous year), health region-years of births 2015\\u20132021",
          f"par={par_}, estrato=Brasil")
cr8 = B.rd("tab_e8_03_concordancia_resumo").iloc[0]
R.add("kappa_aps_indice", float(cr8.kappa_ponderado_linear), B.num(cr8.kappa_ponderado_linear), "tab_e8_03_concordancia_resumo",
      "Linear-weighted kappa between primary health care coverage tertiles and access index tertiles (births 2015\\u20132021)", "")
R.add("pct_concordancia_aps_indice", float(cr8.pct_diagonal), f"{B.pct(cr8.pct_diagonal)}%", "tab_e8_03_concordancia_resumo",
      "Births in the same tertile of primary health care coverage and of the access index, % (births 2015\\u20132021)", "")
rt8 = B.rd("tab_e8_03_raca_por_tercil").query("raca == 'Indigena'").set_index("medida")
for ex_, (sf_, txt_) in ROT8.items():
    for t_ in ("T1", "T3"):
        R.add(f"pct_Ind_{t_}_{sf_}", float(rt8.loc[ex_, t_]), f"{B.pct(rt8.loc[ex_, t_])}%", "tab_e8_03_raca_por_tercil",
              f"Indigenous births in {t_} of {txt_}, % (births 2015\\u20132021)", f"medida={ex_}, raca=Indigena")
B.grava_xlsx(XL, B.TABD / f"tabelas_principais_{B.V}.xlsx")''')],
    "scripts/etapa7b_02_suplementar.py": [
        ("import platform\nimport subprocess\n", "import platform\nimport re\nimport subprocess\n"),
        ('''assert (aw.G == 433).all() and (aw.gl == 6).all()
rows = []''', '''assert (aw.G == 433).all() and (aw.gl == 6).all()
# Etapa 8: (d) tercis da cobertura da Atenção Básica e (e) comparador, tercis do índice recalculados, nascimentos de 2015–2021
e8i = B.rd("tab_e8_04_interacao").query("raca == 'Indigena' and nivel == 'T1'").set_index(["exposicao", "desfecho"])
e8w = B.rd("tab_e8_04_wald").set_index(["exposicao", "desfecho"])
assert (e8w.G == 433).all()
sp8 = B.rd("tab_e8_03_spearman").query("estrato == 'Brasil'").set_index("par").rho
cr8 = B.rd("tab_e8_03_concordancia_resumo").iloc[0]
rt8 = B.rd("tab_e8_03_raca_por_tercil").query("raca == 'Indigena'").set_index("medida")
COL8 = {"tercil_aps": "(d) Primary health care coverage tertiles, 2015\\u20132021", "tercil_ind21": "(e) Access index tertiles, 2015\\u20132021"}
rows = []'''),
        ('''                 "(c) Continuous index: interaction PR per 5 percentage points (95% CI)": B.pr(c.RP_por_5pp_interacao, c.int_lo, c.int_hi)})''',
         '''                 "(c) Continuous index: interaction PR per 5 percentage points (95% CI)": B.pr(c.RP_por_5pp_interacao, c.int_lo, c.int_hi)})
    for ex_, col_ in COL8.items():
        y, w = e8i.loc[(ex_, d_)], e8w.loc[(ex_, d_)]
        rows[-1][f"{col_}: IC Indigenous\\u00d7T1 per 100 (95% CI)"] = B.rd_(y.ICR_pp, y.ICR_lo, y.ICR_hi)
        rows[-1][f"{col_}: Wald p, Indigenous terms (2 df)"] = B.pval(w.p_ind_2gl)'''),
        ('''guarda(pd.DataFrame(rows), "S2b_access_specifications", "Table S2b. Alternative specifications of access to early prenatal care",''',
         '''guarda(pd.DataFrame(rows), "S2b_access_specifications",
       "Table S2b. Alternative specifications of access to early prenatal care and of primary health care coverage",'''),
        ('''       "better access). IC (interaction contrast) = risk difference (Indigenous vs White) within T1 minus the same difference within "
       "T3, per 100 live births. The Wald test jointly tests the 6 race \\u00d7 tertile interaction terms (Brown, Black, and Indigenous "
       "\\u00d7 T1 and T2; 6 df). 95% CIs and Wald tests from cluster-robust variance with clustering by health region of residence "
       "(G = 433). (b) and (c) belong to the secondary family of the analysis hierarchy (no multiplicity adjustment). Sources: tab_e3_02_interacao_rs, "
       "tab_e3_02_wald_rs, tab_e3_03a_indice_continuo_rs.")''',
         '''       "better access). "
       "(d) Tertiles, defined within each macroregion as in (a), of primary health care coverage (Family Health Strategy teams and other primary care teams, "
       "parameterized or equivalent by professional working hours; Ministry of Health public report Cobertura da Aten\\u00e7\\u00e3o B\\u00e1sica, 2007\\u20132020) in the "
       "mother's health region of residence in the previous year: population-weighted mean of the official municipal monthly coverage "
       "over the 12 months; T1 = lowest coverage. Births 2015\\u20132021 only, because the official series ends in December 2020 "
       f"({B.n_(e8w.N[('tercil_aps', 'ptb')])} births for preterm birth (total)). (e) Comparator for (d): tertiles of the access index "
       "recomputed in the same births (2015\\u20132021) with the same algorithm. Primary health care coverage measures the supply of "
       "teams relative to the population, not the use of prenatal care: across health region-years it was weakly correlated with the "
       f"access index (Spearman \\u03c1 = {B.num(sp8['cobertura_x_indice'])}) and inversely with the population of the health region "
       f"(\\u03c1 = {B.num(sp8['cobertura_x_populacao'])}); coverage and access index tertiles agreed for {B.pct(cr8.pct_diagonal)}% of births "
       f"(linear-weighted \\u03ba = {B.num(cr8.kappa_ponderado_linear)}); {B.pct(rt8.loc['tercil_aps', 'T3'])}% of Indigenous births were in "
       f"the highest coverage tertile and {B.pct(rt8.loc['tercil_aps', 'T1'])}% in the lowest (access index, 2015\\u20132021: "
       f"{B.pct(rt8.loc['tercil_ind21', 'T1'])}% in T1 and {B.pct(rt8.loc['tercil_ind21', 'T3'])}% in T3). "
       "IC (interaction contrast) = risk difference (Indigenous vs White) within T1 minus the same difference within "
       "T3, per 100 live births. In (b), the Wald test jointly tests the 6 race \\u00d7 tertile interaction terms (Brown, Black, and "
       "Indigenous \\u00d7 T1 and T2; 6 df); in (d) and (e), it jointly tests the Indigenous \\u00d7 T1 and Indigenous \\u00d7 T2 terms (2 df), "
       "with the same cluster-robust covariance. 95% CIs and Wald tests from cluster-robust variance with clustering by health region of "
       "residence (G = 433). (b) to (e) belong to the secondary family of the analysis hierarchy (no multiplicity adjustment). Sources: "
       "tab_e3_02_interacao_rs, tab_e3_02_wald_rs, tab_e3_03a_indice_continuo_rs, tab_e8_04_interacao, tab_e8_04_wald, tab_e8_03_spearman, "
       "tab_e8_03_concordancia_resumo, tab_e8_03_raca_por_tercil.")'''),
        ('''ter = (B.PROJ / "docs/referencias/territorio_dez24/ACESSO.txt").read_text().strip().splitlines()''',
         '''ter = (B.PROJ / "docs/referencias/territorio_dez24/ACESSO.txt").read_text().strip().splitlines()
aps = (B.PROJ / "docs/referencias/aps_cobertura_ab/ACESSO.txt").read_text().strip().splitlines()   # Etapa 8 (etapa8_01)
aps_tot = re.match(r"Total: 27 UFs; ([\\d,]+) registros; ([\\d,]+) municípios", aps[3]).groups()
aps_dia = sorted({l[:10] for l in aps[5:] if re.match(r"\\d{4}-\\d{2}-\\d{2} ", l)})
assert len(aps_dia) == 1, aps_dia'''),
        ('''ETAPA = "Etapa 7c.7: pacote v12 com as decisões da 7c.6b"
txt = f"""# Data and code availability (draft, package {B.V}, Etapa 7c.7)''',
         '''ETAPA = "Etapa 8: sensibilidade com a cobertura da Atenção Básica (pacote v13)"
txt = f"""# Data and code availability (draft, package {B.V}, Etapa 8)'''),
        ('''- **IBGE 2022 Census, SIDRA table 9605**''',
         '''- **Primary health care coverage, 2014–2020** (Ministry of Health, public report "Cobertura da Atenção Básica (2007 - 2020)",
  https://relatorioaps.saude.gov.br/cobertura/ab), for the sensitivity analysis in Table S2b: municipal monthly coverage queried through
  the report's own interface (`https://relatorioaps-prd.saude.gov.br/cobertura/ab`, municipal level, January 2014 to December 2020, one
  query per state) on {aps_dia[0]}; {aps_tot[0]} records ({aps_tot[1]} municipalities); sizes and MD5 of the 27 files in
  docs/referencias/aps_cobertura_ab/ACESSO.txt.
- **IBGE 2022 Census, SIDRA table 9605**'''),
        ('''  "{ETAPA}" (its hash is given by `git log --grep "^Etapa 7c.7:"`; a file cannot contain the hash of the commit that adds it).''',
         '''  "{ETAPA}" (its hash is given by `git log --grep "^Etapa 8:"`; a file cannot contain the hash of the commit that adds it).'''),
        ('''> (SINASC) and Mortality Information System (SIM), distributed by DATASUS, Ministry of Health of Brazil, and the 2022 Census of the
> Brazilian Institute of Geography and Statistics (IBGE, SIDRA table 9605).''',
         '''> (SINASC) and Mortality Information System (SIM), distributed by DATASUS, Ministry of Health of Brazil, the Ministry of Health primary
> health care coverage report (Cobertura da Atenção Básica, 2007–2020), and the 2022 Census of the
> Brazilian Institute of Geography and Statistics (IBGE, SIDRA table 9605).''')],
    "scripts/etapa7b_04_submissao.py": [
        ('''  7c.7: o MANIFEST deixa fora as autoauditorias das etapas (audita_*.csv, gravadas depois do pacote) e escapa o | dentro das células
"""''', '''  7c.7: o MANIFEST deixa fora as autoauditorias das etapas (audita_*.csv, gravadas depois do pacote) e escapa o | dentro das células
  8: S2b com a cobertura da Atenção Básica (colunas d e e); MANIFEST com a v13 no histórico
"""'''),
        ('''    "S2b": ("etapa7b_02_suplementar.py", "tab_e3_02_interacao_rs, tab_e3_02_wald_rs, tab_e3_03a_indice_continuo_rs (EP por região de saúde)"),''',
         '''    "S2b": ("etapa7b_02_suplementar.py", "tab_e3_02_interacao_rs, tab_e3_02_wald_rs, tab_e3_03a_indice_continuo_rs, tab_e8_04_interacao, "
                                         "tab_e8_04_wald, tab_e8_03_spearman, tab_e8_03_concordancia_resumo, tab_e8_03_raca_por_tercil "
                                         "(EP por região de saúde)"),'''),
        ('''linhas = [f"# MANIFEST — pacote de resultados (Etapas 7b–7c.7, {V})", "",''',
         '''linhas = [f"# MANIFEST — pacote de resultados (Etapas 7b–8, {V})", "",'''),
        ('''          "'Etapa 7c.7: pacote v12 com as decisões da 7c.6b'). Nenhuma análise nova: todo número vem de "''',
         '''          "'Etapa 8: sensibilidade com a cobertura da Atenção Básica (pacote v13)'). Nenhuma análise nova no pacote: todo número vem de "'''),
        ('''          "suplementar/ sem arquivos ._* (dot_clean no 02). Scripts em scripts/.''',
         '''          "suplementar/ sem arquivos ._* (dot_clean no 02); v13 = v12 com a cobertura da Atenção Básica na Tabela S2b (colunas d e e, "
          "nascimentos de 2015–2021; tab_e8_04_*, tab_e8_03_*, Etapa 8), os números-chave da Etapa 8 e a nota geral 'n.a.' no rodapé da "
          "Tabela 4. Scripts em scripts/.'''),
        ('''          "| S2b | Especificações alternativas do acesso (tercis nacionais, índice contínuo; EP por região de saúde) | ESM_1.xlsx (S2b_access_specifications) |",''',
         '''          "| S2b | Especificações alternativas do acesso (tercis nacionais, índice contínuo; cobertura da Atenção Básica e índice, 2015–2021; EP por região de saúde) | ESM_1.xlsx (S2b_access_specifications) |",''')],
    "scripts/resumos/LEIAME.md": [
        ("o `etapa7c6_01`, o `etapa7c6b_01` e o `etapa7c7_01` foram criados aqui.",
         "o `etapa7c6_01`, o `etapa7c6b_01`, o `etapa7c7_01` e o `etapa8_01` foram criados aqui."),
        ("então param depois que ela é arquivada (a v11 foi arquivada na 7c.7). O `etapa7c7_01` fixa a v12 do mesmo jeito.",
         "então param depois que ela é arquivada (a v11 foi arquivada na 7c.7 e a v12 na Etapa 8). O `etapa7c7_01` e o `etapa8_01` fixam a v12 e a "
         "v13 do mesmo jeito; o `etapa7c7_01` já para."),
        ("O registro é o CSV dela commitado na 7c.6b;",
         "O registro é o CSV dela commitado na 7c.6b. Do mesmo modo, na Etapa 8 a v12 foi arquivada e a autoauditoria da 7c.7 "
         "(`scripts/etapa7c7_02_audita.py`) para no bloco B, porque procura a v12 na raiz; o registro é o CSV dela commitado na 7c.7;"),
        ("que o `.gitignore` exclui. Por isso não rodam num clone limpo;",
         "que o `.gitignore` exclui. Por isso não rodam num clone limpo. O `etapa8_01` lê o dele só se existir; num clone limpo ele roda, "
         "mas a seção 2 sai sem a auditoria independente;")],
}
rui = {}
for a, trocas in TROCAS.items():
    v_, n_ = git("show", f"{BASE}:{a}"), (PROJ / a).read_text()
    cont = [v_.count(x) for x, _ in trocas]
    for x, y in trocas:
        v_ = v_.replace(x, y)
    if cont != [1] * len(trocas) or v_ != n_:
        rui[a] = f"ocorrências {cont}; reproduz {v_ == n_}"
ok("C1.01", "lib, 01, 02, 04 e LEIAME: o arquivo atual = o de dc54fb9 com exatamente estas trocas (cada trecho velho ocorre uma vez): "
   "versão, tabelas da Etapa 8 na lista de permissão, nota 'n.a.', números-chave novos, colunas (d) e (e) e rodapé da S2b, fonte nova "
   "na disponibilidade, grep '^Etapa 8:', MANIFEST, LEIAME", not rui, rui or {a: len(t) for a, t in TROCAS.items()})
c13 = pd.read_csv(MS / f"checa_7b_{V13}.csv")
c12 = pd.read_csv(A12 / f"checa_7b_{V12}.csv")
r12, r13 = set(c12.verificacao.str.replace(V12, "VX")), set(c13.verificacao.str.replace(V13, "VX"))
ok("C2.01", "checa da v13: 128/128; as 113 verificações da v12 continuam com os mesmos rótulos; as 15 novas são da Etapa 8 ('8 ')",
   len(c13) == 128 and c13.ok.astype(bool).all() and len(c12) == 113 and r12 <= r13 and len(r13 - r12) == 15
   and all(x.startswith("8 ") for x in r13 - r12), f"sumiram {sorted(r12 - r13)[:2]}; novas {len(r13 - r12)}")
ck = (PROJ / "scripts/etapa7b_checa.py").read_text()
ck0 = git("show", f"{BASE}:scripts/etapa7b_checa.py")
cab = git("diff", "-U0", BASE, "--", "scripts/etapa7b_checa.py")
rem_l, add_l = set(), set()
for m in re.finditer(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", cab, re.M):
    a, b, c, d_ = int(m.group(1)), int(m.group(2) if m.group(2) is not None else 1), int(m.group(3)), int(m.group(4) if m.group(4) is not None else 1)
    rem_l |= set(range(a, a + b))
    add_l |= set(range(c, c + d_))
L0, L1 = ck0.splitlines(), ck.splitlines()
lin_de = lambda L, s: [i + 1 for i, l in enumerate(L) if l.startswith(s)]
h0 = (lin_de(L0, "# ---- 9h.")[0], lin_de(L0, "# sem 'ICR'")[0] - 1)
cmp0 = (lin_de(L0, "def compara(")[0], lin_de(L0, "def compara(")[0] + 2)
x0 = lin_de(L0, "        x = prep(x, b.name)")
p0 = [i + 1 for i, l in enumerate(L0) if '"173fecd", "Etapa 7b.2", "Etapa 7c.7",' in l]
rem_fora = sorted(i for i in rem_l if not (h0[0] <= i <= h0[1]) and not (cmp0[0] <= i <= cmp0[1]) and i not in p0 + x0)
reg = [(lin_de(L1, "  9i. Etapa 8")[0],) * 2,
       (lin_de(L1, "def compara(")[0], lin_de(L1, "def compara(")[0] + 3),
       (lin_de(L1, "        y = y.drop(columns=")[0], lin_de(L1, "        x = prep(x, b.name)")[0]),
       (lin_de(L1, 'A12, V12 = B.MS / "_arquivo_v12"')[0],) * 2,
       (lin_de(L1, "J12l = json.load")[0], lin_de(L1, "J12 = {")[0]),
       (lin_de(L1, "# ---- 9h.")[0], lin_de(L1, "# sem 'ICR'")[0] - 1),
       ([i + 1 for i, l in enumerate(L1) if '"173fecd", "Etapa 7b.2", "Etapa 8",' in l][0],) * 2]
add_fora = sorted(i for i in add_l if not any(a <= i <= b for a, b in reg))
g9h = ck[ck.index("# ---- 9h."):ck.index("# ---- 9i.")].replace(
    '''subprocess.run(["dot_clean", "-m", str(B.SUPD)], check=True)''', "")   # texto procurado no 02, não uso do B.SUPD
ok("C2.02", "checa: toda linha removida é do bloco 9h, da assinatura do compara, da linha do prep ou da lista da disponibilidade; toda linha "
   "acrescentada cai na docstring (9i), no compara (novas_cols), em A12/J12, nos blocos 9h/9i ou na lista ('Etapa 8'); o 9h compara v11 × v12 "
   "arquivadas (sem Jcur, B.TABD, B.SUPD, B.SUB, B.V nem B.COMMIT) e confere commit_pacote pelo pacote_esperado(V12)",
   rem_l and not rem_fora and not add_fora and not any(x in g9h for x in ("Jcur", "B.TABD", "B.SUPD", "B.SUB", "B.V", "B.COMMIT"))
   and "pacote_esperado(V12)" in g9h, f"{len(rem_l)} removidas, {len(add_l)} acrescentadas; fora das regiões: removidas {rem_fora[:3]}, "
                                      f"acrescentadas {add_fora[:3]}")
src8 = {k: (PROJ / f"scripts/etapa8_0{k}_{n}.py").read_text() for k, n in ((1, "baixa_cobertura_ab"), (2, "cobertura_regiao"), (3, "tercis"), (4, "modelos"))}
grava = {k: sorted(set(re.findall(r'(?:out_name\("|PROC / f"|DEST / "|REF / "|tmp\.|\.rename\()([a-z0-9_]*)', s))) for k, s in src8.items()}
le_mic = {k: "read_parquet" in s or "T.load(" in s or "S4.carrega(" in s for k, s in src8.items()}
ok("C3.01", "scripts da Etapa 8: o 01 só grava em data/raw/aps_cobertura_ab (nome final só depois do .part) e o ACESSO.txt, e não "
   "sobrescreve; o 02 não lê microdados; o 03 e o 04 leem a amostra analítica e gravam só tabelas agregadas (tab_e8_03_*, tab_e8_04_*, "
   "tercis por região × ano); o 03 confere o algoritmo dos tercis e o 04 confere o motor contra a análise publicada (assert)",
   "if arq.exists():" in src8[1] and "tmp.rename(arq)" in src8[1] and src8[1].count("write_bytes(") == 1 and not le_mic[1] and not le_mic[2]
   and le_mic[3] and le_mic[4] and "assert (cc._merge == \"both\").all() and (cc.tercil_reg == cc.tercil_reg_e3).all()" in src8[3]
   and "assert dif < 1e-9 and abs(w2 - pw.chi2_ind_2gl[desf]) < 1e-6" in src8[4], grava)
IDS = re.compile(r"(?i)^(NUMERODN|NUMERODV|DTNASC|DTNASCMAE|DTCADASTRO|DTRECEBIM|CODMUNRES|CODMUNNASC|CODESTAB|CONTADOR|CODINST|NUDIASOBIN|coMunicipioIbge)$")
saidas8 = sorted(TB.glob(f"tab_e8_0*_v1_{S}.csv")) + [PROC / f"cobertura_ab_regsaude_ano_v1_{S}.csv", PROC / f"tercil_aps_regsaude_ano_v1_{S}.csv"]
lin8 = {f.name: len(pd.read_csv(f)) for f in saidas8}
col8 = [f"{f.name}:{c}" for f in saidas8 for c in pd.read_csv(f, nrows=0).columns if IDS.match(c)]
ok("C3.02", "saídas da Etapa 8 (tab_e8_02–04 e as duas por região × ano): só agregados — nenhuma coluna identificadora, no máximo 3,031 "
   "linhas (região × ano)", len(saidas8) == 14 and max(lin8.values()) <= 3031 and not col8, f"{lin8}; colunas {col8}")

# ---- sandbox: checa com mutações, commit simulado, LEIAME
class GuardaFalhou(Exception):
    pass


TMP = Path(tempfile.mkdtemp(prefix="audita8_"))
BASE_SBX = TMP / "base"
tab_antes = {f.name: (f.stat().st_size, f.stat().st_mtime) for f in TB.iterdir()}
SEM_ASSERT = ("import sys; sys.path.insert(0, 'scripts'); src = open('scripts/etapa7b_checa.py').read(); "
              "assert src.count('    assert cond, nome\\n') == 1; "
              "exec(compile(src.replace('    assert cond, nome\\n', '    pass\\n'), 'scripts/etapa7b_checa.py', 'exec'), {'__name__': '__main__'})")
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
            raise PermissionError(f"guarda 8: {ev} no Forja bloqueado: {alvo}")
    finally:
        _dentro[0] = False
sys.addaudithook(_guarda)
"""


def monta():
    GUARDA.mkdir()
    (GUARDA / "sitecustomize.py").write_text(GUARDA_PY)
    subprocess.run(["git", "clone", "-q", "-s", str(PROJ), str(BASE_SBX)], check=True, env=ENV)
    for s_, p in ns:                                       # as mudanças rastreadas da Etapa 8 (inclusive as renomeações)
        if s_ == "D":
            (BASE_SBX / p).unlink()
        else:
            (BASE_SBX / p).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(PROJ / p, BASE_SBX / p)
    for p in naor:                                         # novos não ignorados; de docs/referencias, só o mapa e o ACESSO da cobertura
        if not p.startswith("docs/referencias/") or p.endswith(("territorio_dez24/rl_municip_regsaud.csv", "aps_cobertura_ab/ACESSO.txt")):
            (BASE_SBX / p).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(PROJ / p, BASE_SBX / p)
    (BASE_SBX / "outputs/tables").mkdir(parents=True, exist_ok=True)
    for f in TB.iterdir():                                 # ignorados: só links simbólicos (leitura), nenhuma cópia
        (BASE_SBX / "outputs/tables" / f.name).symlink_to(f)
    for f in (PROJ / "audit_independente").rglob("comparacao_*.csv"):
        if not f.name.startswith("._") and not (BASE_SBX / f.relative_to(PROJ)).exists():
            (BASE_SBX / f.relative_to(PROJ)).parent.mkdir(parents=True, exist_ok=True)
            (BASE_SBX / f.relative_to(PROJ)).symlink_to(f)
    (BASE_SBX / "data/raw/aps_cobertura_ab").mkdir(parents=True)
    for f in RAW.glob("cobertura_ab_uf*_201401_202012.json"):     # dado público agregado por município (o checa confere o MD5)
        (BASE_SBX / "data/raw/aps_cobertura_ab" / f.name).symlink_to(f)
    (BASE_SBX / "outputs/logs").mkdir(parents=True, exist_ok=True)


def roda(dirr, codigo=None, script=None, env=None):
    """Todo Python do sandbox carrega a guarda (sitecustomize com audit hook): nada de escrita, remoção ou renomeação no Forja."""
    cmd = [sys.executable, "-c", codigo] if codigo else [sys.executable, script]
    e = {**ENV, **(env or {})}
    e["PYTHONPATH"] = os.pathsep.join([str(GUARDA)] + ([e["PYTHONPATH"]] if e.get("PYTHONPATH") else []))
    e["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(cmd, cwd=dirr, capture_output=True, text=True, env=e, timeout=1800)


def falhas(dirr, r, pai=""):
    f = dirr / f"outputs/manuscrito/checa_7b_{V13}.csv"
    if r.returncode or not f.exists():
        return dict(rc=r.returncode, n=0, fl=[r.stderr.strip()[-300:]], rot=set(), pai=pai)
    c = pd.read_csv(f)
    return dict(rc=0, n=len(c), fl=sorted(c.verificacao[~c.ok.astype(bool)]), rot=set(c.verificacao), pai=pai)


def jmuda(fun, rel=f"outputs/manuscrito/numeros_chave_{V13}.json"):
    def f(d):
        p = d / rel
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


def xl_troca(rel, aba, a, b):
    def f(d):
        wb = openpyxl.load_workbook(d / rel)
        ws = [w for w in wb.worksheets if w.title.startswith(aba)][0]
        c = [c for row in ws.iter_rows() for c in row if c.value and a in str(c.value)][0]
        c.value = str(c.value).replace(a, b)
        wb.save(d / rel)
    return f


def dx_muda(d):
    p = d / f"outputs/manuscrito/tabelas/tabelas_principais_{V13}.docx"
    D_ = docx.Document(p)
    par = [q for q in D_.paragraphs if NOTA_NA.strip() in q.text][0]
    par.text = par.text.replace(NOTA_NA, "")
    D_.save(p)


def px_muda(d):
    p = d / f"outputs/manuscrito/figuras/fig02_pr_race_m1m3_{V13}.png"
    im = Image.open(p)
    dpi = im.info.get("dpi")
    im = im.convert("RGB")
    im.putpixel((5, 5), (1, 2, 3))
    im.save(p, dpi=dpi)


def csv_muda(rel):
    def f(d):
        p = d / rel
        L_ = p.read_text().split("\n")
        k = [j for j, l in enumerate(L_) if j and re.search(r"\d", l)][0]
        i = re.search(r"\d", L_[k]).start()
        L_[k] = L_[k][:i] + str((int(L_[k][i]) + 1) % 10) + L_[k][i + 1:]
        p.write_text("\n".join(L_))
    return f


def md5_muda(d):
    p = d / "docs/referencias/aps_cobertura_ab/ACESSO.txt"
    t = p.read_text()
    m = re.search(r"\) = ([0-9a-f])", t)
    p.write_text(t[:m.start(1)] + ("0" if m.group(1) != "0" else "1") + t[m.start(1) + 1:])


S2B13 = f"outputs/manuscrito/suplementar/S2b_access_specifications_{V13}.csv"
MUT = [   # (nome, mutação, rótulo da verificação do checa que tem de falhar, mexe só na v13?)
    ("célula (d) da S2b (CSV)", troca_txt(S2B13, "\u22123.11 (\u22126.30 to 0.07)", "\u22123.12 (\u22126.30 to 0.07)"), "8 S2b: colunas (d) e (e)", True),
    ("ρ no rodapé da S2b (ESM_1 do pacote)", xl_troca(f"outputs/manuscrito/suplementar/ESM_1_tables_S1_S6_{V13}.xlsx", "S2b_", "\u03c1 = \u22120.10", "\u03c1 = \u22120.11"),
     "8 S2b (ESM_1", True),
    ("rodapé da S2b no ESM_1 de Submissao/", xl_troca("Submissao/ESM_1.xlsx", "S2b_", "(b) to (e) belong", "(b) and (c) belong"), "8 S2b (ESM_1", True),
    ("nota 'n.a.' tirada da Tabela 4 (xlsx)", xl_troca(f"outputs/manuscrito/tabelas/tabelas_principais_{V13}.xlsx", "tab04_", NOTA_NA, ""),
     "8 tabelas principais (xlsx)", True),
    ("célula 'n.a.' sem explicação na Tabela 4 (CSV)", troca_txt(f"outputs/manuscrito/tabelas/tab04_sensitivity_{V13}.csv", "4.46 (2.75 to 6.18)", "n.a."),
     "8 Tabela 4: toda célula", True),
    ("valor formatado de Wald2_ind_aps_pig", jmuda(lambda J: [i.update(valor_formatado="0.508") for i in J if i["id"] == "Wald2_ind_aps_pig"]),
     "8 números-chave da Etapa 8", True),
    ("commit_analise de n_regsaude_CE", jmuda(lambda J: [i.update(commit_analise="") for i in J if i["id"] == "n_regsaude_CE"]), "8 números-chave: os da v12", True),
    ("descrição de um número da v12 no JSON da v13", jmuda(lambda J: J[0].update(descricao=J[0]["descricao"] + " x")), "8 números-chave: os da v12", True),
    ("registros na fonte nova da disponibilidade", troca_txt("outputs/manuscrito/data_code_availability.md", "467,880 records", "467,881 records"),
     "8 data_code_availability", True),
    ("MD5 de um arquivo no ACESSO.txt da cobertura", md5_muda, "8 bruto da cobertura", True),
    ("um pixel da figura 2 (png) da v13", px_muda, "8 figuras", True),
    ("a legenda da Fig. 2", troca_txt("outputs/manuscrito/legendas_figuras.md", "**Fig. 2.**", "**Fig. 2.** x"), "8 legendas", True),   # a da Fig. 1 o 7c.2 também lê
    ("nota 'n.a.' tirada do docx", dx_muda, "8 docx", True),
    ("um dígito de um CSV da v12 arquivada", csv_muda(f"outputs/manuscrito/_arquivo_v12/tabelas/tab02_models_m1m3_{V12}.csv"), "7c.7 v11 × v12 célula a célula", False),
    ("descrição na v12 arquivada (9h)", jmuda(lambda J: J[0].update(descricao=J[0]["descricao"] + " x"), f"outputs/manuscrito/_arquivo_v12/numeros_chave_{V12}.json"),
     "7c.7 números-chave", False),
]
GIT_ID = ["-c", "user.name=audita8", "-c", "user.email=audita8@local"]


def caso(k, mut=None, commit=None):
    d = TMP / f"m{k:02d}"
    subprocess.run(["cp", "-cR", str(BASE_SBX), str(d)], check=True)
    try:
        if commit == "unico":
            git(*GIT_ID, "add", "-A", cwd=d)
            git(*GIT_ID, "commit", "-q", "-m", TITULO, cwd=d)
            (d / f"outputs/manuscrito/checa_7b_{V13}.csv").unlink()
            r = roda(d, script="scripts/etapa7b_checa.py")   # o checa de verdade, com assert
            return falhas(d, r, git("rev-parse", "--short", "HEAD^", cwd=d).strip())
        if commit == "meio":
            git(*GIT_ID, "add", "scripts/etapa8_01_baixa_cobertura_ab.py", cwd=d)
            git(*GIT_ID, "commit", "-q", "-m", "download da cobertura", cwd=d)
            git(*GIT_ID, "add", "-A", cwd=d)
            git(*GIT_ID, "commit", "-q", "-m", TITULO, cwd=d)
        if mut:
            mut(d)
        (d / f"outputs/manuscrito/checa_7b_{V13}.csv").unlink()
        r = roda(d, codigo=SEM_ASSERT)
        return falhas(d, r)
    finally:
        shutil.rmtree(d, ignore_errors=True)


try:
    monta()
    alvo_t = sorted(f.name for f in (BASE_SBX / "outputs/tables").iterdir())[0]
    alvo_j = sorted(f.name for f in (BASE_SBX / "data/raw/aps_cobertura_ab").iterdir())[0]
    g1 = roda(BASE_SBX, codigo=f"open('outputs/tables/{alvo_t}', 'a')")
    g2 = roda(BASE_SBX, codigo="import os; os.remove('outputs/tables/" + alvo_t + "')")
    g3 = roda(BASE_SBX, codigo=f"open('data/raw/aps_cobertura_ab/{alvo_j}', 'r+')")
    g4 = roda(BASE_SBX, codigo="open('outputs/logs/teste_guarda.txt', 'w').write('x')")
    ok("C6.00a", "guarda do sandbox: escrever ou remover pelo link de outputs/tables e escrever pelo link do JSON da cobertura é bloqueado "
       "(PermissionError); escrever dentro do sandbox funciona", all(r.returncode != 0 and "guarda 8" in r.stderr for r in (g1, g2, g3))
       and g4.returncode == 0 and (BASE_SBX / "outputs/tables" / alvo_t).is_symlink() and (BASE_SBX / "data/raw/aps_cobertura_ab" / alvo_j).is_symlink(),
       f"{[r.returncode for r in (g1, g2, g3, g4)]}; {g1.stderr.strip().splitlines()[-1][:80] if g1.stderr.strip() else ''}")
    (BASE_SBX / "outputs/logs/teste_guarda.txt").unlink(missing_ok=True)
    if not R[-1]["ok"]:
        raise GuardaFalhou("a guarda do sandbox não funcionou: nenhuma mutação, commit simulado ou teste do LEIAME roda")
    with cf.ThreadPoolExecutor(4) as ex:
        fb = ex.submit(caso, 0)
        fm = [ex.submit(caso, k + 1, m) for k, (_, m, _, _) in enumerate(MUT)]
        fu = ex.submit(caso, 90, commit="unico")
        fi = ex.submit(caso, 91, commit="meio")
        rb, fm, ru, ri = fb.result(), [f.result() for f in fm], fu.result(), fi.result()
    ok("C6.00", "sandbox: o checa (sem o assert, para rodar até o fim) dá 128/128, com os mesmos rótulos do checa da v13",
       rb["rc"] == 0 and rb["n"] == 128 and not rb["fl"] and rb["rot"] == set(c13.verificacao), f"código {rb['rc']}; {rb['n']} verificações; "
       f"falhas {[x[:60] for x in rb['fl']][:2]}; rótulos diferentes {sorted(rb['rot'] ^ set(c13.verificacao))[:2]}")
    for k, ((nome, _, alvo, so13), r_) in enumerate(zip(MUT, fm)):
        ok(f"C6.{k + 1:02d}", f"mutação ({nome}): o checa acusa '{alvo}'" + ("; os blocos que comparam versões arquivadas (7c.x) não se mexem" if so13 else ""),
           r_["rc"] == 0 and any(x.startswith(alvo) for x in r_["fl"]) and (not so13 or not any(x.startswith("7c.") for x in r_["fl"])),
           f"código {r_['rc']}; {r_['n']} verificações; falhas {[x[:45] for x in r_['fl']][:4]}")
    ok("C6.20", "commit único simulado (git add -A + commit com o título da etapa): o checa de verdade (com assert) roda depois do commit e "
       "dá 128/128; commit_pacote = pai do commit (dc54fb9)", ru["rc"] == 0 and ru["n"] == 128 and not ru["fl"] and ru["pai"] == BASE,
       f"código {ru['rc']}; {ru['n']} verificações; falhas {[x[:60] for x in ru['fl']][:2]}; pai {ru['pai']}")
    ok("C6.21", "com um commit no meio (o download antes), o checa acusa o commit_pacote (LEIAME: um commit só por versão)",
       ri["rc"] == 0 and any(x.startswith("8 commit_pacote") for x in ri["fl"]), f"falhas {[x[:45] for x in ri['fl']][:3]}")
    d = TMP / "leiame"
    subprocess.run(["cp", "-cR", str(BASE_SBX), str(d)], check=True)
    pp = {"PYTHONPATH": "scripts"}
    if not (d / SAIDA.relative_to(PROJ)).exists():          # 1ª rodada: o CSV desta autoauditoria ainda não existe; um provisório basta
        pd.DataFrame([dict(verificacao="A0.00 provisório do sandbox", ok=True, detalhe="")]).to_csv(d / SAIDA.relative_to(PROJ), index=False)
    l1 = roda(d, script="scripts/etapa7c7_02_audita.py")
    l2 = roda(d, script="scripts/resumos/etapa7c7_01_resumo.py", env=pp)
    l3 = roda(d, script="scripts/resumos/etapa8_01_resumo.py", env=pp)
    gerou = (d / "outputs/RESUMO_ETAPA8_v1_20261013.md").exists()
    (d / "outputs/manuscrito/_arquivo_v13").mkdir()
    for f in (d / "outputs/manuscrito").glob(f"*_{V13}.*"):                         # arquivamento simulado da v13
        f.rename(d / "outputs/manuscrito/_arquivo_v13" / f.name)
    l4 = roda(d, script="scripts/resumos/etapa8_01_resumo.py", env=pp)
    fnf = lambda r, s: r.returncode != 0 and "FileNotFoundError" in r.stderr and s in r.stderr
    ok("C6.22", "LEIAME, testado no sandbox: a autoauditoria da 7c.7 e o gerador 7c7_01 param (FileNotFoundError, v12 na raiz); o gerador "
       "8_01 roda com a v13 na raiz (e grava o RESUMO) e para depois de um arquivamento simulado da v13",
       fnf(l1, V12) and fnf(l2, V12) and l3.returncode == 0 and gerou and fnf(l4, V13),
       f"7c7_02 {l1.returncode} {l1.stderr.strip().splitlines()[-1][:70] if l1.stderr.strip() else ''}; 7c7_01 {l2.returncode}; "
       f"8_01 antes {l3.returncode} {l3.stderr.strip().splitlines()[-1][:60] if l3.returncode and l3.stderr.strip() else ''}, depois {l4.returncode}")
except GuardaFalhou as e:
    ok("C6.99", "sandbox interrompido", False, e)
finally:
    shutil.rmtree(TMP, ignore_errors=True)
tab_depois = {f.name: (f.stat().st_size, f.stat().st_mtime) for f in TB.iterdir()}
raw_ok = all(md5(f.read_bytes()) == md5_acc.get(f.name) for f in RAW.glob("cobertura_ab_uf*_201401_202012.json"))
ok("C6.23", "outputs/tables e o JSON da cobertura intactos depois do sandbox (mesmos arquivos, tamanhos e mtimes; MD5 do JSON = ACESSO.txt); "
   "sandbox apagado", tab_antes == tab_depois and raw_ok and not TMP.exists(), f"{len(tab_depois)} tabelas; JSON {'ok' if raw_ok else 'MUDOU'}")

# ======================= D. logs × mtimes =======================
ev, ini = [], {}
for nome in ("etapa7b_20261008.log", "etapa8_20261008.log"):
    for l in (PROJ / "outputs/logs" / nome).read_text(errors="ignore").splitlines():
        m = re.match(r"^\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\] \[([^\]]+)\] (.*)", l)
        if not m:
            continue
        t = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").timestamp()
        if t <= T_BASE:
            continue
        s_, msg = m.group(2), m.group(3)
        ini.setdefault(s_, []).append(t)                                   # todas as linhas, para o início de cada execução
        e = {"8_01_baixa_cobertura_ab": "8_01" if msg.startswith("fim:") else None,
             "8_02_cobertura_regiao": "8_02" if msg.startswith("cobertura por região × ano:") else None,
             "8_03_tercis": "8_03" if msg.startswith("conferência:") else None,
             "8_04_modelos": "8_04" if msg.startswith("amostra 2015–2021") else None,
             "7b_01_tabelas": "01", "7b_02_suplementar": "02", "7b_03_figuras": "03", "7b_04_submissao": "04"}.get(s_)
        if s_ == "7b_checa":
            e = ("checa_ini" if msg.startswith("OK  números-chave = arquivo de origem") else "checa_fim" if msg.startswith("autoauditoria 7b:")
                 else "checa_falha" if msg.startswith("FALHA") else None)
        if e:
            ev.append((t, e, msg))
ev.sort()
seq = [e for _, e, _ in ev]
SEQ = ["8_01", "8_02", "8_03", "8_04",                                     # 1ª rodada da análise
       "8_03", "8_04",                                                     # tercis com a população e a tabela-resumo; modelos de novo
       "01", "02", "03", "04", "checa_ini", "checa_falha",                 # pacote v13; o 1º checa caiu por erro dele (dtype da S2b)
       "checa_ini", "checa_fim", "04",                                     # checa corrigido e o 04
       "01", "02", "03", "04", "checa_ini", "checa_fim", "04"]             # 26/10, depois da rodada 1 do auditor: rodapé da S2b (equipes equivalentes)
ok("D1.01", "execuções desde dc54fb9, na ordem: as documentadas no RESUMO (download, cobertura, tercis e modelos; tercis e modelos de "
   "novo; 01–04; checa que caiu por erro dele, checa corrigido, 04; rodada final 01–04, checa, 04; os geradores do RESUMO não entram)", seq == SEQ,
   [f"{datetime.fromtimestamp(t):%H:%M:%S} {e}" for t, e, _ in ev])
if seq == SEQ:
    T_ = [t for t, _, _ in ev]
    t81, t82, t83a, t84a, t83, t84, _, _, _, _, tci1, tcf1, _, _, _ = T_[:15]
    t01, t02, t03, t04a, tci, tcf, t04 = T_[15:]                            # rodada final do pacote
    dentro = lambda f, a, b: a - 2 <= f.stat().st_mtime <= b + 2
    jan = ([(f, t81 - 600, t81) for f in RAW.glob("*")] + [(ACC, t81 - 5, t81)]
           + [(PROC / f"cobertura_ab_regsaude_ano_v1_{S}.csv", t81, t82)] + [(f, t81, t82) for f in TB.glob(f"tab_e8_02_*_v1_{S}.csv")]
           + [(PROC / f"tercil_aps_regsaude_ano_v1_{S}.csv", t83, t84)] + [(f, t83, t84) for f in TB.glob(f"tab_e8_03_*_v1_{S}.csv")]
           + [(f, t84, T_[6]) for f in TB.glob(f"tab_e8_04_*_v1_{S}.csv")]
           + [(f, T_[14], t01) for f in (MS / "tabelas").glob(f"*_{V13}.*")]
           + [(MS / f"numeros_chave_{V13}.{x}", T_[14], t01) for x in ("json", "md")]
           + [(f, t01, t02) for f in (MS / "suplementar").glob(f"*_{V13}.*") if not f.name.startswith("S9_")]
           + [(MS / "data_code_availability.md", t01, t02)]
           + [(f, t02, t03) for f in list((MS / "figuras").glob(f"*_{V13}.*")) + list((MS / "suplementar").glob(f"S9_*_{V13}.*"))]
           + [(MS / "legendas_figuras.md", t02, t03)]
           + [(MS / f"checa_7b_{V13}.csv", tci, tcf)] + [(MS / "MANIFEST.md", tcf, t04), (SUB / "ESM_4.pdf", tcf, t04)])
    ORIGEM_SUB = {**{f"Fig{k}.tif": MS / "figuras" / n for k, n in enumerate(sorted(x.name for x in (MS / "figuras").glob(f"*_{V13}.tif")), 1)},
                  "ESM_1.xlsx": MS / "suplementar" / f"ESM_1_tables_S1_S6_{V13}.xlsx", "ESM_2.pdf": MS / "suplementar" / f"S7_variables_codes_{V13}.pdf",
                  "ESM_3.pdf": MS / "suplementar" / f"S8_strobe_record_checklist_{V13}.pdf"}
    fora_j = [f"{f.name} {datetime.fromtimestamp(f.stat().st_mtime):%H:%M:%S}" for f, a, b in jan if not dentro(f, a, b)]
    fora_j += [f"Submissao/{n} ≠ origem" for n, o in ORIGEM_SUB.items() if abs((SUB / n).stat().st_mtime - o.stat().st_mtime) > 2
               or (SUB / n).read_bytes() != o.read_bytes()]
    # limite = 1ª linha de log da (última) execução do script; o 7b só loga no fim, então lib, 01–04 antes do fim do 01 menos 20 s
    SCR = {"scripts/etapa8_01_baixa_cobertura_ab.py": min(ini["8_01_baixa_cobertura_ab"]), "scripts/etapa8_02_cobertura_regiao.py": min(ini["8_02_cobertura_regiao"]),
           "scripts/etapa8_03_tercis.py": t83, "scripts/etapa8_04_modelos.py": min(ini["8_04_modelos"]), "scripts/etapa7b_lib.py": t01 - 20,
           "scripts/etapa7b_01_tabelas.py": t01 - 20, "scripts/etapa7b_02_suplementar.py": t01, "scripts/etapa7b_03_figuras.py": t01 - 20,
           "scripts/etapa7b_04_submissao.py": t01 - 20}
    tarde = [s_ for s_, lim in SCR.items() if (PROJ / s_).stat().st_mtime > lim]
    mck = (PROJ / "scripts/etapa7b_checa.py").stat().st_mtime
    ok("D1.02", "cada saída tem mtime na janela do script que a grava (JSON, manifesto e ACESSO no download; cobertura; tercis e modelos "
       "da 2ª rodada; tabelas e números-chave; suplementar e disponibilidade; figuras, S9 e legendas; checa final; MANIFEST e ESM_4 no "
       "último 04; Fig1–4 e ESM_1–3 de Submissao/ = cópias com o mtime da origem); nenhum script editado depois da sua última execução "
       "(o checa foi corrigido entre o 1º e o 2º checa)", not fora_j and not tarde and len(jan) >= 70 and tcf1 < mck < tci,
       f"{len(jan)} arquivos; fora da janela {fora_j[:4]}; scripts editados depois {tarde}; checa editado "
       f"{datetime.fromtimestamp(mck):%H:%M:%S} (entre {datetime.fromtimestamp(tcf1):%H:%M:%S} e {datetime.fromtimestamp(tci):%H:%M:%S})")
else:
    ok("D1.02", "janelas de mtime (não conferidas: a sequência do D1.01 não bate)", False)

# ======================= E. microdados e git no que vai para o commit =======================
vai = sorted(set(p for s_, p in ns if s_ != "D") | {p for p in naor if not p.startswith("docs/referencias/") or p in FIXOS})
EXT = (".parquet", ".dbc", ".dbf", ".rds", ".rda", ".rdata", ".sav", ".dta", ".feather", ".sqlite", ".db", ".gz", ".zip", ".7z")
ruim = [p for p in vai if p.startswith("data/") or p.lower().endswith(EXT) or Path(p).name.startswith("._") or Path(p).name == ".DS_Store"
        or (p.startswith("audit_independente/") and p.endswith(".csv")) or (PROJ / p).stat().st_size > 20e6]
ok("E1.01", "o que vai para o commit (rastreados alterados + novos, sem os 93 de docs/referencias; com o ACESSO.txt da cobertura): nada em "
   "data/ (o JSON da cobertura fica fora), nenhum parquet/dbc/dbf/rds/zip, nenhum ._* ou .DS_Store, nenhum CSV do auditor, nada > 20 MB",
   vai and not ruim and "docs/referencias/aps_cobertura_ab/ACESSO.txt" in vai, f"{len(vai)} arquivos; problemas {ruim[:5]}")
lin_max, col_id = {}, []
for p in vai:
    f = PROJ / p
    if p.endswith(".csv"):
        dd_ = pd.read_csv(f, dtype=str)
        lin_max[p] = len(dd_)
        col_id += [f"{p}:{c}" for c in dd_.columns if IDS.match(str(c))]
    elif p.endswith(".xlsx"):
        wb = openpyxl.load_workbook(f, read_only=True)
        lin_max[p] = max(ws.max_row or 0 for ws in wb.worksheets)
grandes = {p: n for p, n in lin_max.items() if n > 1000}
ok("E1.02", "CSVs e xlsx que vão para o commit: nenhuma coluna identificadora do SINASC/SIM e no máximo 1.000 linhas por tabela/aba (só agregados)",
   lin_max and not grandes and not col_id, f"{len(lin_max)} tabelas; maior {max(lin_max.values()) if lin_max else 0} linhas; grandes {grandes}; colunas {col_id[:3]}")
ok("E1.03", ".gitignore igual ao de dc54fb9 (data/, parquet, outputs/tables e CSVs de auditoria continuam fora)",
   (PROJ / ".gitignore").read_text() == git("show", f"{BASE}:.gitignore"))

out = pd.DataFrame(R)
out.to_csv(SAIDA, index=False)
print(out.to_string(max_colwidth=200))
print(f"\n{int(out.ok.sum())}/{len(out)} OK")
