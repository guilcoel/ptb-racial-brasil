"""
7c.6 (auditoria final) Autoauditoria do estado commitado da Etapa 7c.6 (b9d6272), pedida antes de seguir para a próxima etapa:
  K  integridade do commit e do amend (a38f550 → b9d6272), trailers, histórico sem lixo nem dado individual;
  L  afirmações do RESUMO_ETAPA7C6 e do relato final, recalculadas com código próprio (não importa etapa7b_lib nem o checa),
     e reprodução do RESUMO (o gerador roda com a saída desviada para o scratch; só esse passo importa a lib);
  M  fatos por trás das decisões pendentes (só levantamento).
Audita o estado de b9d6272 em 2026-10-10: o ATRIBUICAO.txt é lido do commit (foi corrigido depois, na 7c.6b); itens que leem
o disco (._*, logs, tabelas de origem) refletem o disco nesse dia. O bloco L10 refaz, com código próprio, as falhas que o auditor
independente achou no RESUMO 7c.6 (L10.03 é conferência manual na web, só registrada aqui).
Só lê o projeto; grava outputs/manuscrito/audita_final_7c6_v1_20261010.csv. Microdados: não lê (o item dos códigos de MESPRENAT
usa a tabela agregada tab_e2_03_mesprenat_completude). Rodar da raiz: PYTHONPATH=scripts python3 scripts/etapa7c6_02_audita_final.py
"""
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd

PROJ = Path("/Volumes/Forja/ptb-racial-brasil")  # AUDITOR: cópia fora de scripts/
MS = PROJ / "outputs" / "manuscrito"
V, V10 = "v11_20261009", "v10_20261009"
HEAD, AMEND_DE, PAI = "b9d6272", "a38f550", "8314417"
RES = PROJ / "outputs" / "RESUMO_ETAPA7C6_v1_20261009.md"
SAIDA = PROJ / "audit_independente/etapa7c6_final/audita_final_reexecucao_auditor_r2_v1_20261010.csv"  # AUDITOR: saída desviada
MEU = {"scripts/etapa7c6_02_audita_final.py", "outputs/manuscrito/audita_final_7c6_v1_20261010.csv"}  # AUDITOR: mesmo conjunto do original
git = lambda *a: subprocess.run(["git", "-C", str(PROJ), *a], capture_output=True, text=True, check=True).stdout
gitb = lambda *a: subprocess.run(["git", "-C", str(PROJ), *a], capture_output=True, check=True).stdout
md5 = lambda b: hashlib.md5(b).hexdigest()
R = []


def ok(vid, desc, cond, det=""):
    R.append(dict(verificacao=f"{vid} {desc}", ok=bool(cond), detalhe=str(det)))


resumo = RES.read_text()
J = json.load(open(MS / f"numeros_chave_{V}.json"))
JD = {i["id"]: i for i in J}

# ======================= K. commit b9d6272 e amend =======================
ok("K1.01", "HEAD é b9d6272 e o pai é 8314417", git("rev-parse", "--short", "HEAD").strip() == HEAD
   and git("rev-parse", "--short", f"{HEAD}^").strip() == PAI, git("log", "-1", "--format=%h %p", HEAD).strip())
ok("K1.02", "a38f550 (antes do amend) tem o mesmo pai e a mesma mensagem", git("rev-parse", "--short", f"{AMEND_DE}^").strip() == PAI
   and git("log", "-1", "--format=%B", AMEND_DE) == git("log", "-1", "--format=%B", HEAD))
dif = [l.split("\t") for l in git("diff", "--name-status", AMEND_DE, HEAD).splitlines()]
ESP_AMEND = {"outputs/RESUMO_ETAPA7C6_v1_20261009.md", "outputs/manuscrito/_resumo7c6_texto_v1_20261009.md"}
linhas = [l for l in git("diff", "-U0", AMEND_DE, HEAD).splitlines() if l[:1] in "+-" and not l.startswith(("+++", "---"))]
ok("K1.03", "o amend só muda o RESUMO e o texto-fonte, uma linha cada: 'duas rodadas' → 'quatro rodadas'",
   {p for _, p in dif} == ESP_AMEND and all(s == "M" for s, _ in dif) and len(linhas) == 4
   and all("duas rodadas" in l for l in linhas if l[0] == "-") and all("quatro rodadas" in l for l in linhas if l[0] == "+"),
   f"{dif}; {len(linhas)} linhas ±")
msg = git("log", "-1", "--format=%B", HEAD).rstrip("\n").splitlines()
ok("K2.01", "assunto e trailers exatos", msg[0] == "Etapa 7c.6: auditoria independente 7c.5/7c.5b, RECORD e rastreabilidade"
   and msg[-2:] == ["Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>",
                    "Claude-Session: [session URL removed for publication]"], msg[-2:])
ok("K2.02", "sem remoto, sem tag, sem ref remota", not git("remote").strip() and not git("tag").strip()
   and not git("for-each-ref", "refs/remotes").strip())
ns = [l.split("\t") for l in git("diff", "--name-status", "-M", PAI, HEAD).splitlines()]
ok("K3.01", "arquivos do commit em relação a 8314417 (status)", True, dict(Counter(x[0][0] for x in ns)))
todos = set(git("log", "--all", "--format=", "--name-only").split())
lixo = sorted(p for p in todos if Path(p).name.startswith("._") or Path(p).name == ".DS_Store")
ok("K3.02", "nenhum ._* ou .DS_Store em todo o histórico", not lixo, lixo[:5])
brutos = sorted(p for p in todos if re.search(r"\.(parquet|dbc|dbf|csv\.gz)$|(^|/)data/", p))
ok("K3.03", "nenhum parquet/dbc/dbf/csv.gz nem data/ em todo o histórico", not brutos, brutos[:5])
ID_RX = re.compile(r"^(DTNASC|HORANASC|NUMERODN|NUMERODO|CODESTAB|DTOBITO|DTNASCMAE|DTULTMENST|CNS|CPF|NUMEROLOTE|DTCADASTRO|DTRECEBIM)$", re.I)
mudados = [x[-1] for x in ns if x[0][0] in "AMR"]
susp = []
for p in mudados:
    if p.endswith(".csv"):
        h = pd.read_csv(PROJ / p, nrows=0).columns
        n = sum(1 for _ in open(PROJ / p, errors="ignore")) - 1
        if any(ID_RX.match(str(c).strip()) for c in h) or n > 5000:
            susp.append((p, n, [c for c in h if ID_RX.match(str(c).strip())]))
ok("K3.04", "arquivos novos/modificados no commit: nenhum CSV com coluna identificadora nem com > 5,000 linhas",
   not susp, f"{len(mudados)} arquivos; suspeitos {susp}")
st = [l for l in git("--no-optional-locks", "status", "--porcelain", "--untracked-files=all").splitlines()]  # AUDITOR: sem reescrever o índice
rastreados_mod = [l for l in st if not l.startswith("??")]
nao_rastr = [l[3:] for l in st if l.startswith("??")]
extra = [p for p in nao_rastr if not p.startswith(("docs/referencias/", "audit_independente/etapa7c6_final/")) and p not in MEU]
ok("K4.01", "árvore: nenhum arquivo rastreado alterado; não rastreados só em docs/referencias (+ esta auditoria)",
   not rastreados_mod and not extra, f"modificados {rastreados_mod[:3]}; docs/referencias {sum(p.startswith('docs/referencias/') for p in nao_rastr)}; "
   f"outros {extra[:3]}")

# ======================= L. afirmações do RESUMO =======================
# L1. auditoria independente: 178/178 e tabela por bloco
cp = pd.read_csv(PROJ / "audit_independente/etapa7c6/comparacao_7c6_v1_20261009.csv")
cp["ok_"] = cp.ok.astype(str).str.lower().isin(["true", "1"])
blo = cp.groupby(cp.verificacao.str[0]).ok_.agg(["size", "sum"])
tab_res = dict(re.findall(r"^\|\s*([A-J])\.\s[^|]*\|\s*(\d+)\s*\|\s*\d+\s*\|$", resumo, re.M))   # to_markdown alinha com espaços
ok("L1.01", "auditor: 178/178 no CSV e tabela por bloco do RESUMO igual ao CSV", len(cp) == 178 and cp.ok_.all()
   and {k: int(v) for k, v in tab_res.items()} == blo["size"].to_dict() and (blo["size"] == blo["sum"]).all(),
   blo["size"].to_dict())
rel = (PROJ / "audit_independente/etapa7c6/relatorio_7c6_v1_20261009.md").read_text()
ok("L1.02", "relatório do auditor registra as rodadas 2, 3 e 4 e as falhas H4.06 e I1.08",
   all(s in rel for s in ("H4.06", "I1.08")) and all(re.search(rf"[Rr]odada {k}", rel) for k in (2, 3, 4)))
chk = pd.read_csv(pd.io.common.BytesIO(gitb("show", f"{HEAD}:outputs/manuscrito/checa_7b_{V}.csv")))
ok("L1.03", "checa commitado: 100/100 OK e igual ao arquivo em disco", len(chk) == 100 and chk.ok.all()
   and gitb("show", f"{HEAD}:outputs/manuscrito/checa_7b_{V}.csv") == (MS / f"checa_7b_{V}.csv").read_bytes())
c76 = chk[chk.verificacao.str.contains("7c.6")]
ok("L1.04", "linhas 7c.6 do checa no RESUMO = CSV commitado", all(v in resumo for v in c76.verificacao), f"{len(c76)} linhas")

# L2. números-chave: 226 ids, vazios, distribuições
ok("L2.01", "226 números-chave; commit_analise e commit_registro sem vazio", len(J) == 226
   and all(i["commit_analise"] for i in J) and all(i["commit_registro"] for i in J))
for campo, vid in (("commit_analise", "L2.02"), ("commit_registro", "L2.03")):
    dist = Counter(i[campo] for i in J)
    no_res = {c: int(n) for c, n in re.findall(r"^\|\s*([0-9a-f]{7})\s*\|\s*Etapa[^|]+\|\s*(\d+)\s*\|$",
                                               resumo.split(f"**`{campo}`**")[1].split("**")[0], re.M)}
    ok(vid, f"distribuição de {campo} no RESUMO = JSON", no_res == dict(dist), dict(dist))


def na_tab(it):   # mesmo critério do checa 1 (célula numérica, rtol 1e-9), com código próprio
    t = pd.read_csv(PROJ / it["arquivo"])
    x = t.select_dtypes("number").to_numpy(dtype=float).ravel()
    vs = it["valor_bruto"] if isinstance(it["valor_bruto"], list) else [it["valor_bruto"]]
    return all(np.any(np.abs(x - v) <= 1e-12 + 1e-9 * np.abs(v)) for v in vs)


direto = {k: na_tab(i) for k, i in JD.items()}
ok("L2.04", "11 derivados no pacote e 215 lidos direto da tabela", sum(not d for d in direto.values()) == 11,
   sorted(k for k, d in direto.items() if not d))


# commit_registro recalculado: versões arquivadas, caminho original do JSON de cada versão
def igual(a, b):
    a, b = (a if isinstance(a, list) else [a]), (b if isinstance(b, list) else [b])
    return len(a) == len(b) and all(np.isclose(float(x), float(y), rtol=1e-12, atol=0) for x, y in zip(a, b))


vers = []
for d in MS.glob("_arquivo_v*"):
    f = next(d.glob("numeros_chave_v*.json"))
    orig = f"outputs/manuscrito/{f.name}"
    add = git("log", "--diff-filter=A", "--format=%h", "--", orig).split()
    vers.append((int(d.name.split("_v")[1]), {i["id"]: i for i in json.load(open(f))}, add[-1] if add else ""))
vers.sort(key=lambda x: -x[0])
reg = {}
for k, it in JD.items():
    c = ""
    for _, JJ, a in vers:
        x = JJ.get(k)
        if x is None or x["valor_formatado"] != it["valor_formatado"] or not igual(x["valor_bruto"], it["valor_bruto"]):
            break
        c = a
    reg[k] = c
ok("L2.05", "commit_registro recalculado = JSON (226)", all(reg[k] == JD[k]["commit_registro"] for k in JD),
   [k for k in JD if reg[k] != JD[k]["commit_registro"]][:5])

# commit_analise recalculado: derivado → registro; direto → commit cujo intervalo (pai, commit] contém o mtime da tabela,
# exigindo que seja o último commit do script até o registro
lin = [l.split() for l in git("log", "--format=%h %ct %p", HEAD).splitlines()]
tempo = {h: int(t) for h, t, *_ in lin}
pai = {h: (p[0] if p else "") for h, t, *p in lin}


def ca_de(k):
    it = JD[k]
    if not direto[k]:
        return reg[k]
    mt = (PROJ / it["arquivo"]).stat().st_mtime
    cand = [h for h in tempo if tempo[h] >= mt and (not pai[h] or tempo[pai[h]] < mt)]
    ult = git("log", "-1", "--format=%h", reg[k], "--", it["script"].split()[0]).strip()
    return cand[0] if len(cand) == 1 and cand[0] == ult else ""


ca = {k: ca_de(k) for k in JD}
ok("L2.06", "commit_analise recalculado = JSON (226)", all(ca[k] == JD[k]["commit_analise"] for k in JD),
   [k for k in JD if ca[k] != JD[k]["commit_analise"]][:5])
anc = [k for k, i in JD.items() if subprocess.run(["git", "-C", str(PROJ), "merge-base", "--is-ancestor", i["commit_analise"],
                                                    i["commit_registro"]]).returncode != 0]
ok("L2.07", "todo commit_analise é ancestral (ou igual) do commit_registro", not anc, anc[:5])

# terceira fonte: log do script de origem com horário a ±3 s do mtime da tabela
logs = []
for f in (PROJ / "outputs" / "logs").glob("*.log"):
    if f.name.startswith("._"):
        continue
    for l in open(f, errors="ignore"):
        m = re.match(r"\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\] \[([^\]]+)\]", l)
        if m:
            logs.append((datetime.fromisoformat(m.group(1)).timestamp(), m.group(2)))   # o Logger grava hora local
LG = pd.DataFrame(logs, columns=["t", "tag"])
tabs = sorted({JD[k]["arquivo"] for k in JD if direto[k]})
sem_log = []
for a in tabs:
    scr = Path(next(JD[k]["script"] for k in JD if JD[k]["arquivo"] == a).split()[0]).stem
    mt = (PROJ / a).stat().st_mtime
    hit = LG[(LG.t - mt).abs() <= 3]
    # etiqueta do Logger = nome do script sem "etapaX_" ou sem "etapa"; três etiquetas são abreviadas (as duas rodadas com --rs e o 6_07)
    ALIAS = {"etapa3_02_knol": "3.2-3.6_knol_rs", "etapa3_00b_bootstrap_atenuacao": "6b_bootstrap_atenuacao_rs",
             "etapa6_07_tempo_nascidos_vivos": "07_tempo_nv"}
    if not {scr.split("_", 1)[1], scr[len("etapa"):], ALIAS.get(scr)} & set(hit.tag):
        sem_log.append(a)
ok("L2.08", "tabelas de origem lidas direto: o log do próprio script registra horário a ±3 s do mtime da tabela",
   not sem_log, f"{len(tabs)} tabelas; sem log {sem_log[:3]}")

# as 21 da 7c.3
v6 = next(J for n, J, _ in vers if n == 6)
v7 = next(J for n, J, _ in vers if n == 7)
c73 = sorted(k for k in JD if JD[k]["commit_registro"] == "3092186")
novos7 = sorted(set(v7) - set(v6))
mud7 = sorted(k for k in set(v7) & set(v6) if v7[k]["valor_formatado"] != v6[k]["valor_formatado"])
ca73 = Counter(JD[k]["commit_analise"] for k in c73)
ok("L2.09", "7c.3: 21 ids registrados em 3092186 (= ids novos na v7); só 4 calculados lá (n_excl_estciv_*), 9 na Etapa 6, 8 na 6b",
   len(c73) == 21 and set(c73) == set(novos7) | set(mud7) and ca73 == Counter({"3092186": 4, "2285207": 9, "6905d9d": 8})
   and {k for k in c73 if JD[k]["commit_analise"] == "3092186"} == {k for k in JD if k.startswith("n_excl_estciv_")},
   f"novos v7 {len(novos7)}, mudados v7 {len(mud7)}; {dict(ca73)}")
assunto = {h: git("log", "-1", "--format=%s", h).split(":")[0] for h in ("2285207", "6905d9d", "3092186")}
ok("L2.10", "2285207 = Etapa 6, 6905d9d = Etapa 6b, 3092186 = Etapa 7c.3", assunto == {"2285207": "Etapa 6", "6905d9d": "Etapa 6b",
                                                                                     "3092186": "Etapa 7c.3"}, assunto)
ex = dict(re.findall(r"^\|\s*`([^`]+)`\s*\|\s*([0-9a-f]{7}) \(", resumo, re.M))
ok("L2.11", "tabela de exemplos do RESUMO = JSON", ex and all(JD[k]["commit_analise"] == v for k, v in ex.items()), ex)

# L3. nenhum número mudou: v10 × v11
J10 = {i["id"]: i for i in json.load(open(MS / "_arquivo_v10" / f"numeros_chave_{V10}.json"))}
ok("L3.01", "números-chave v10 = v11 (ids, valores, descrição, filtro, arquivo, script)", set(J10) == set(JD)
   and all(J10[k][c] == JD[k][c] for k in JD for c in ("valor_bruto", "valor_formatado", "descricao", "filtro", "arquivo", "script")))
dif_csv = []
for sub in ("tabelas", "suplementar"):
    for f in sorted((MS / sub).glob(f"*_{V}.csv")):
        g = MS / "_arquivo_v10" / sub / f.name.replace(V, V10)
        if not g.exists() or f.read_bytes() != g.read_bytes():
            dif_csv.append(f.name)
ok("L3.02", "CSVs de tabelas e suplementares v11 byte a byte iguais aos da v10", not dif_csv,
   f"{len(list((MS / 'tabelas').glob(f'*_{V}.csv'))) + len(list((MS / 'suplementar').glob(f'*_{V}.csv')))} arquivos; diferentes {dif_csv}")

# L4. geradores, RECORD, ._*
movidos = sorted(p.name for p in (PROJ / "scripts/resumos").glob("*.py") if p.name not in ("etapa7c6_01_resumo.py", "etapa7c6b_01_resumo.py"))  # AUDITOR: contorno — o original quebra com o gerador novo da 7c.6b
iguais = [n for n in movidos if (PROJ / "scripts/resumos" / n).read_bytes() == gitb("show", f"{PAI}:scripts/{n}")]
ok("L4.01", "10 geradores em scripts/resumos idênticos aos de 8314417; nenhum *_resumo.py sobrou em scripts/",
   len(movidos) == 10 and iguais == movidos and not list((PROJ / "scripts").glob("*_resumo.py")), f"{len(iguais)}/{len(movidos)}")
dx = PROJ / "docs/referencias/RECORD_checklist_acesso20261009.docx"
ok("L4.02", "RECORD docx: 17,088 bytes, MD5 d50bd10f…, versionado e igual ao HEAD", dx.stat().st_size == 17088
   and md5(dx.read_bytes()) == "d50bd10feb3c20398ccce6f3c27b7777"
   and gitb("show", f"{HEAD}:docs/referencias/RECORD_checklist_acesso20261009.docx") == dx.read_bytes())
at = gitb("show", f"{HEAD}:docs/referencias/ATRIBUICAO.txt").decode().rstrip()   # versão de b9d6272 (corrigida depois, na 7c.6b)
ok("L4.03", "ATRIBUICAO.txt de b9d6272 = bloco do RESUMO; tem CC BY 4.0, DOI e URL da licença", at in resumo
   and all(s in at for s in ("CC BY 4.0", "10.1371/journal.pmed.1001885", "creativecommons.org/licenses/by/4.0")))
fora = [x for d in ("outputs", "scripts", "audit_independente", "docs") for x in (PROJ / d).rglob("._*")]
porp = Counter(str(x.parent.relative_to(PROJ)) for x in fora)
tab_p = {p: int(n) for p, n in re.findall(r"^\|\s*(outputs/\S+)\s*\|\s*(\d+)\s*\|$", resumo, re.M)}
ok("L4.04", "._* nas pastas outputs, scripts, audit_independente e docs: 0 em Submissao/, 36 fora, tabela por pasta do RESUMO = disco",
   not list((PROJ / "Submissao").rglob("._*")) and len(fora) == 36 and tab_p == dict(porp), f"{len(fora)} em {len(porp)} pastas")
em_data = [x.name for x in (PROJ / "data").rglob("._*")]   # só nomes; nada é aberto em data/
ok("L4.05", "RESUMO: 'Fora dela: 36' vale para o projeto inteiro? (conta também data/)", len(fora) + len(em_data) == 36,
   f"{len(fora) + len(em_data)} no projeto: {len(fora)} fora de data/ + {len(em_data)} em data/ ({em_data})")

# L5. código do índice citado no RESUMO
src = (PROJ / "scripts/etapa2_03_indice_acesso.py").read_text().splitlines()
ok("L5.01", "linhas citadas do etapa2_03 (L4–5, L36, L39, L40, L51, L74) dizem o que o RESUMO diz",
   "MESPRENAT 1–3" in src[3] and "(1–9; 99 = ignorado e nulo ficam fora)" in src[4] and "CODMUNRES" in src[35]
   and '"mes_valido": mes.between(1, 9).fillna(False), "tri1": mes.between(1, 3).fillna(False),' in src[38]
   and '"mes_nulo": mes.isna(), "mes_99": (mes == 99).fillna(False),' in src[39]
   and src[50].strip() == 'A["indice"] = 100 * A.tri1 / A.mes_valido' and "ano + 1" in src[73])
comp = pd.read_csv(PROJ / "outputs/tables/tab_e2_03_mesprenat_completude_v1_20261008.csv")
b14 = comp[(comp.macro == "Brasil") & (comp.ano == 2014)].iloc[0]
outros14 = int(b14.n - b14.n_valido - b14.n_nulo - b14.n_99)
outros = comp[comp.macro == "Brasil"].assign(o=lambda x: x.n - x.n_valido - x.n_nulo - x.n_99).set_index("ano").o
ok("L5.02", "2014: 2,607 registros com MESPRENAT fora de 1–9, 99 e nulo (tabela agregada); demais anos", outros14 == 2607,
   f"2014 {outros14}; outros anos com código fora: {outros[outros > 0].drop(2014, errors='ignore').to_dict()}")
ok("L5.03", "Asian: 117,549 / 27,489,150 = 0.4276% → 0.43% = pct_amarela_fonte", round(100 * 117549 / 27489150, 4) == 0.4276
   and JD["pct_amarela_fonte"]["valor_formatado"] == "0.43%", f"{100 * 117549 / 27489150:.4f}%; JSON {JD['pct_amarela_fonte']['valor_bruto']}")


def frase(t):   # o texto aprovado, de "Births to mothers of Asian" até "regional study"
    t = " ".join(t.split())
    m = re.search(r"Births to mothers of Asian.*?regional study", t)
    return m.group(0) if m else None


def texto_xlsx(p):   # células de todas as abas (o xlsx usa strings inline; o sharedStrings fica vazio)
    wb = openpyxl.load_workbook(p, read_only=True)
    return " ".join(str(c) for ws in wb.worksheets for r in ws.iter_rows(values_only=True) for c in r if c is not None)


fr = {"ESM_1 pacote": frase(texto_xlsx(MS / "suplementar" / f"ESM_1_tables_S1_S6_{V}.xlsx")),
      "ESM_1 Submissao": frase(texto_xlsx(PROJ / "Submissao" / "ESM_1.xlsx")) if (PROJ / "Submissao/ESM_1.xlsx").exists() else None,
      "disponibilidade": frase((MS / "data_code_availability.md").read_text())}
ok("L5.04", "frase com 0.43% idêntica nos dois ESM_1 e na disponibilidade", None not in fr.values() and len(set(fr.values())) == 1,
   {k: (v or "")[:90] for k, v in fr.items()})

# L6. os 41 .txt de auditoria
txts = sorted(p for p in git("ls-files", "audit_independente").splitlines() if p.endswith(".txt"))
nl = {p: sum(1 for _ in open(PROJ / p, errors="ignore")) for p in txts}
cel = {p: max((l.count("|") - 1 for l in open(PROJ / p, errors="ignore") if l.lstrip().startswith("|")), default=0) for p in txts}
tok = {p: max((len(l.split()) for l in open(PROJ / p, errors="ignore")), default=0) for p in txts}
mx = max(nl, key=nl.get)
ok("L6.01", "41 .txt versionados, sem mudança desde 8314417; máx. de linhas 163 em etapa7b3/relatorio_etapa7b3; máx. bruto de tokens 80",
   len(txts) == 41 and not git("diff", "--name-only", PAI, HEAD, "--", *txts).strip() and nl[mx] == 163
   and mx.endswith("etapa7b3/relatorio_etapa7b3_v1_20261009.txt") and max(tok.values()) == 80,
   f"{mx} {nl[mx]}; máx. células de tabela {max(cel.values())} em {max(cel, key=cel.get)}; máx. tokens {max(tok.values())}")

# L7. reprodução do RESUMO: gerador com a saída desviada
ger = PROJ / "scripts/resumos/etapa7c6_01_resumo.py"
alvo = '(B.PROJ / "outputs" / "RESUMO_ETAPA7C6_v1_20261009.md").write_text(out)'
code = ger.read_text()
tmp = PROJ / "audit_independente/etapa7c6_final/RESUMO_ETAPA7C6_reexec_autoaud_r2_v1_20261010.md"  # AUDITOR: saída desviada
if code.count(alvo) == 1:
    sys.path.insert(0, str(PROJ / "scripts"))
    code = code.replace("(B.PROJ / 'docs/referencias/ATRIBUICAO.txt').read_text()", "ATRIB_HEAD")   # o texto de b9d6272
    exec(compile(code.replace(alvo, f"Path({str(tmp)!r}).write_text(out)"), str(ger), "exec"),
         {"__file__": str(ger), "__name__": "repro", "ATRIB_HEAD": at + "\n"})
ok("L7.01", "RESUMO regenerado agora (saída desviada) = RESUMO commitado, byte a byte", tmp.exists()
   and tmp.read_bytes() == gitb("show", f"{HEAD}:outputs/RESUMO_ETAPA7C6_v1_20261009.md"), tmp)

# L8. checa depois do commit: verificações presas ao HEAD
csrc = (PROJ / "scripts/etapa7b_checa.py").read_text()
presas = [i + 1 for i, l in enumerate(csrc.splitlines()) if "B.COMMIT" in l]
leia = ((PROJ / "scripts/resumos/LEIAME.md").read_text() + "\n" + resumo).splitlines()
aviso = [l[:120] for l in leia if "checa" in l and ("HEAD" in l or "commit_pacote" in l) and re.search(r"falh|reexecut|rodar de novo", l)]
ok("L8.01", "o checa compara commit_pacote com o HEAD atual e falha se reexecutado depois do commit da etapa: o RESUMO ou o LEIAME avisam?",
   bool(aviso), f"linhas com B.COMMIT no checa: {presas}; aviso: {aviso or 'nenhum'}")

# L10. falhas do auditor independente no RESUMO 7c.6, refeitas aqui
ok("L10.01", "RESUMO: 'a autoauditoria ... lê o .csv do auditor, então não roda num clone limpo' (o checa exige o CSV?)",
   "if aud76.exists():" not in csrc, "o checa lê o CSV do auditor só se ele existir (if aud76.exists()); o gerador lê sem condição; "
   "o checa não roda num clone limpo por outros motivos (outputs/tables fora do git; commit_pacote = HEAD)")
nove = Counter(Path(JD[k]["arquivo"]).name for k in c73 if JD[k]["commit_analise"] == "2285207")
ok("L10.02", "RESUMO seção 4: os 9 da Etapa 6 vêm de tab_e3_02_*_rs?", all(n.startswith("tab_e3_02_") for n in nove), dict(nove))
ok("L10.03", "RESUMO e ATRIBUICAO: 'o artigo diz só CC BY' (conferência manual na web, 2026-10-10)", False,
   "a declaração de licença do artigo na PLOS liga a http://creativecommons.org/licenses/by/4.0/; o auditor achou o mesmo no XML do PMC")
mud = []
for f in sorted((MS / "_arquivo_v10").rglob("*")):
    if f.is_dir() or f.name.startswith("._") or f.name.startswith(("numeros_chave_", "checa_7b_")):
        continue
    rel = f.relative_to(MS / "_arquivo_v10")
    g = (PROJ / rel) if rel.parts[0] == "Submissao" else MS / str(rel).replace(V10, V)
    if rel.parts[0] != "Submissao" and len(rel.parts) == 1:
        g = MS / rel.name.replace(f"_{V10}", "")
    if not g.exists() or g.read_bytes() != f.read_bytes():
        mud.append(str(rel))
ok("L10.04", "RESUMO: 'só o JSON e o .md dos números-chave mudam' entre v10 e v11 (bytes)", not mud, f"também diferem em bytes: {mud}")
n_rd = (PROJ / "scripts/etapa7b_02_suplementar.py").read_text().count("B.rd(")
ok("L10.05", "RESUMO: 'um clone limpo monta a S8' (o etapa7b_02 só depende do docx do RECORD?)", n_rd == 0,
   f"o etapa7b_02 chama B.rd() {n_rd} vezes (outputs/tables/, fora do git) antes da S8")

# memória do projeto
mem = Path("/nao/lido/pelo/auditor")  # AUDITOR: arquivo fora do projeto, não lido
mt = mem.read_text() if mem.exists() else ""
ok("L9.01", "memória do projeto aponta b9d6272 e não a38f550", "b9d6272" in mt and "a38f550" not in mt)

# ======================= M. fatos para as decisões =======================
globs = []
for p in sorted((PROJ / "scripts").rglob("*.py")):
    for i, l in enumerate(p.read_text().splitlines(), 1):
        if re.search(r"\.(r?glob|iterdir)\(", l) and "._" not in l:
            globs.append(f"{p.name}:{i}")
ext = Counter(Path(x).suffix for x in fora)
ok("M1.01", "._* fora de Submissao/: extensões; versionados; globs dos scripts sem filtro de ._", True,
   f"extensões {dict(ext)}; versionados {len(lixo)}; .gitignore com ._*: {'._*' in (PROJ / '.gitignore').read_text()}; "
   f"globs sem filtro {len(globs)}: {globs[:12]}")
q = subprocess.run(["xattr", "-l", *map(str, (MS / "suplementar").glob(f"*_{V}.pdf"))], capture_output=True, text=True).stdout
ok("M1.02", "PDFs do pacote com com.apple.quarantine (Chrome); dot_clean só no etapa7b_04", "com.apple.quarantine" in q,
   f"quarantine em {q.count('com.apple.quarantine')} PDFs; dot_clean em "
   f"{[p.name for p in (PROJ / 'scripts').glob('*.py') if 'dot_clean' in p.read_text() and p.name != "etapa7c6_02_audita_final.py"]}")
usa = sorted({k for k, i in JD.items() if "etapa2_03" in i["script"]})
ok("M2.01", "números-chave cujo script de origem é o etapa2_03 (afetados por um commit só de docstring?)", True,
   f"{len(usa)} ids: {usa[:6]}; commit_analise deles {dict(Counter(JD[k]['commit_analise'] for k in usa))}")
cnt = dict(l.split(": ") for l in git("count-objects", "-v").splitlines())
blobs = [l.split(" ", 1) for l in git("rev-list", "--objects", "--all").splitlines() if " " in l]
tam = {}
for linha in subprocess.run(["git", "-C", str(PROJ), "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
                            input="\n".join(b[0] for b in blobs), capture_output=True, text=True).stdout.splitlines():
    h, t, s = linha.split()
    if t == "blob":
        tam[h] = int(s)
cam = {}
for b in blobs:
    if b[0] in tam:
        cam.setdefault(b[0], b[1] if len(b) > 1 else "")
arq = sum(s for h, s in tam.items() if "/_arquivo_v" in cam.get(h, ""))
top = sorted(tam.items(), key=lambda x: -x[1])[:5]
ok("M3.01", "tamanho do repositório e maiores blobs (limite do GitHub: aviso 50 MB, bloqueio 100 MB por arquivo)",
   max(tam.values()) < 50e6, f"objetos soltos {cnt['count']} ({int(cnt['size']) / 1024:.1f} MB comprimidos), pack {int(cnt['size-pack']) / 1024:.1f} MB; blobs únicos {sum(tam.values()) / 1e6:.1f} MB, "
   f"dos quais _arquivo_v* {arq / 1e6:.1f} MB; maiores {[(cam[h], round(s / 1e6, 1)) for h, s in top]}")
csvs_hist = sorted(p for p in todos if p.endswith(".csv"))
ok("M3.02", "CSVs em todo o histórico: nomes de coluna identificadores (cabeçalho atual ou do último commit)", True,
   f"{len(csvs_hist)} caminhos .csv já versionados")
refs = sorted(p[len("docs/referencias/"):] for p in nao_rastr if p.startswith("docs/referencias/"))
scr_txt = " ".join(p.read_text() for p in (PROJ / "scripts").rglob("*.py"))
lidos = [r for r in refs if Path(r).name in scr_txt or Path(r).stem in scr_txt]
tam_ref = sum((PROJ / "docs/referencias" / r).stat().st_size for r in refs)
ok("M4.01", "docs/referencias não rastreados: quantos, tamanho, quais algum script lê", True,
   f"{len(refs)} arquivos, {tam_ref / 1e6:.1f} MB; lidos por script: {lidos}")
ev = (PROJ / "docs/referencias/evans2024_maihda_tutorial_PMC11059336.txt").read_text(errors="ignore")
lic = re.findall(r"[^.\n]*(?:Creative Commons|CC BY[^ ]*|licen[cs]e)[^.\n]*", ev)[:3]
ok("M5.01", "Evans 2024 (PMC11059336): licença declarada no próprio texto; algum script lê", True,
   f"trechos de licença: {lic}; lido por script: {'evans2024' in scr_txt}")
acsv = sorted(p for p in (PROJ / "audit_independente").rglob("*.csv") if not p.name.startswith("._"))
leitores = sorted({p.name for p in (PROJ / "scripts").rglob("*.py") if "audit_independente" in p.read_text() and ".csv" in p.read_text()
                   and p.name != "etapa7c6_02_audita_final.py"})
susp_a = []
for p in acsv:
    try:
        h = pd.read_csv(p, nrows=0).columns
    except Exception:
        continue
    n = sum(1 for _ in open(p, errors="ignore")) - 1
    if any(ID_RX.match(str(c).strip()) for c in h):
        susp_a.append((str(p.relative_to(PROJ)), n))
nmax = max(acsv, key=lambda p: sum(1 for _ in open(p, errors="ignore")))
ok("M6.01", "CSVs de auditoria ignorados: quantos, tamanho, quem lê, colunas identificadoras", True,
   f"{len(acsv)} CSVs, {sum(p.stat().st_size for p in acsv) / 1e6:.1f} MB; maior em linhas {nmax.relative_to(PROJ)} "
   f"({sum(1 for _ in open(nmax, errors='ignore')) - 1}); leitores {leitores}; com coluna identificadora {susp_a[:5]}")
pac = " ".join([" ".join(p.read_text(errors="ignore").split()) for p in list((MS / "tabelas").glob(f"*_{V}.csv"))
                + list((MS / "suplementar").glob(f"*_{V}.csv")) + [MS / "data_code_availability.md", MS / "legendas_figuras.md"]]
               + [" ".join(texto_xlsx(p).split()) for p in MS.rglob(f"*_{V}.xlsx")])
frs = {f: pac.count(f) for f in ("known month of prenatal care initiation", "known month of first visit", "first visit",
                                 "prenatal care initiation", "month of first prenatal")}
ok("M7.01", "formulações do denominador do índice no pacote v11 (CSV, xlsx, disponibilidade, legendas)", True, frs)
dv = pd.read_csv(PROJ / "docs/referencias/territorio_dez24/rl_municip_regsaud.csv", dtype=str)   # o mesmo arquivo que o etapa2_02 lê
nreg = {uf: dv[dv.CO_MUNICIP.str[:2] == c].CO_REGSAUD.nunique() for uf, c in (("CE", "23"), ("DF", "53"))}
nmun = {uf: int((dv.CO_MUNICIP.str[:2] == c).sum()) for uf, c in (("CE", "23"), ("DF", "53"))}
ficha = (MS / "ficha_metodos_7c0_v1_20261009.md").read_text()
ok("M8.01", "regiões de saúde de CE e DF na base territorial usada (rl_municip_regsaud, dez/2024); G 433 → 427 sem CE/DF (ficha 7c.0)",
   sum(nreg.values()) == 433 - 427 and "sem CE/DF: 427" in ficha, f"regiões {nreg}; municípios {nmun}; Brasil {dv.CO_REGSAUD.nunique()} regiões")
t4 = (MS / "tabelas" / f"tab04_sensitivity_{V}.csv").read_text()
x4 = " ".join(texto_xlsx(MS / "tabelas" / f"tabelas_principais_{V}.xlsx").split())
rod4 = [s.strip()[:200] for s in re.findall(r"[^.]*(?:mput|n\.a\.)[^.]*\.", x4)][:4]
ok("M9.01", "Tabela 4: n.a. e imputação múltipla", True,
   f"n.a. no CSV {t4.count('n.a.')}; linhas com imput: {[l[:60] for l in t4.splitlines() if 'mput' in l]}; rodapés (xlsx): {rod4}")
ok("M10.01", "termos no pacote v11", True, {t: len(re.findall(t, pac)) for t in
                                           (r"prevalence ratio", r"\bPR\b", r"risk ratio", r"\bRR\b", r"[Pp]rovider-initiated", r"\bSGA\b",
                                            r"\bindicated\b")})

out = pd.DataFrame(R)
out.to_csv(SAIDA, index=False)
print(out.to_string(max_colwidth=230))
print(f"\n{int(out.ok.sum())}/{len(out)} OK")
