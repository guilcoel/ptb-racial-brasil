"""Bloco D — pacote v12 (arquivado) × v13 (atual), com leitura própria (openpyxl, python-docx, pypdf, PIL)."""
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, "/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa8")
import difflib
import hashlib
import json
import re

import docx
import openpyxl
import pandas as pd
from PIL import Image
from pypdf import PdfReader

from comum_v1_20261013 import PROJ, MS, AUD, V12, V13, Res, md5

R = Res("D")
A12 = MS / "_arquivo_v12"
MINUS = "−"


def num(x, d=2):
    return f"{x:,.{d}f}".replace("-", MINUS)


def pv(p):
    return "<0.0001" if p < 1e-4 else f"{p:.3g}"


def inserido(a, b):
    """Trechos inseridos/substituídos de a → b (por palavras)."""
    sa, sb = a.split(" "), b.split(" ")
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, sa, sb, autojunk=False).get_opcodes():
        if op != "equal":
            out.append((op, " ".join(sa[i1:i2]), " ".join(sb[j1:j2])))
    return out


# D1 CSVs
csv12 = sorted(p for d in ("tabelas", "suplementar") for p in (A12 / d).glob(f"*_{V12}.csv"))
dif_csv = []
for p in csv12:
    q = MS / p.parent.name / p.name.replace(V12, V13)
    if p.read_bytes() != q.read_bytes():
        dif_csv.append(q.name)
csv13 = sorted(p.name for d in ("tabelas", "suplementar") for p in (MS / d).glob(f"*_{V13}.csv"))
R.ok("D1.01 CSVs v12 × v13 (tabelas e suplementar): byte a byte iguais, exceto a S2b; mesmo conjunto de arquivos",
     dif_csv == [f"S2b_access_specifications_{V13}.csv"] and csv13 == sorted(p.name.replace(V12, V13) for p in csv12),
     f"{len(csv12)} pares; diferentes {dif_csv}")
s12 = pd.read_csv(A12 / "suplementar" / f"S2b_access_specifications_{V12}.csv", dtype=str)
s13 = pd.read_csv(MS / "suplementar" / f"S2b_access_specifications_{V13}.csv", dtype=str)
R.ok("D1.02 S2b: as 4 primeiras colunas (Outcome + (a)–(c)) idênticas às da v12 e 4 colunas novas no fim", s13.iloc[:, :s12.shape[1]].equals(s12)
     and s13.shape == (3, s12.shape[1] + 4), f"{s12.shape} → {s13.shape}; novas: {list(s13.columns[s12.shape[1]:])}")
M = pd.read_csv(AUD / "modelos_auditor_v1_20261013.csv")
ind = M[(M.raca == "Indigena") & (M.nivel == "T1")].set_index(["exposicao", "desfecho"])
OUTC = {"ptb": "Preterm birth (total)", "pig": "SGA", "ptb_ind": "Provider-initiated preterm birth"}
COL = {"tercil_aps": "(d) Primary health care coverage tertiles, 2015–2021", "tercil_ind21": "(e) Access index tertiles, 2015–2021"}
falt = []
for ex, c in COL.items():
    for d, o in OUTC.items():
        r = ind.loc[(ex, d)]
        row = s13[s13.Outcome == o].iloc[0]
        e_ic, e_w = f"{num(r.ICR_pp)} ({num(r.ICR_lo)} to {num(r.ICR_hi)})", pv(r.p_ind_2gl)
        if row[f"{c}: IC Indigenous×T1 per 100 (95% CI)"] != e_ic or row[f"{c}: Wald p, Indigenous terms (2 df)"] != e_w:
            falt.append((ex, d, e_ic, e_w))
R.ok("D1.03 S2b colunas (d) e (e) = IC Indígena×T1 e p de Wald 2 gl do meu R, formatados (12 células)", not falt, falt or "12/12")


# D2 xlsx
def abas(p):
    wb = openpyxl.load_workbook(p, data_only=False)
    return {ws.title: [[c.value for c in row] for row in ws.iter_rows()] for ws in wb.worksheets}


def dif_abas(a, b):
    out = []
    for k in sorted(set(a) | set(b)):
        if a.get(k) != b.get(k):
            A_, B_ = a.get(k) or [], b.get(k) or []
            cel = [(i, j) for i in range(max(len(A_), len(B_))) for j in range(max(len(A_[i]) if i < len(A_) else 0, len(B_[i]) if i < len(B_) else 0))
                   if (A_[i][j] if i < len(A_) and j < len(A_[i]) else None) != (B_[i][j] if i < len(B_) and j < len(B_[i]) else None)]
            out.append((k, cel))
    return out


x12, x13 = abas(A12 / "tabelas" / f"tabelas_principais_{V12}.xlsx"), abas(MS / "tabelas" / f"tabelas_principais_{V13}.xlsx")
dx = dif_abas(x12, x13)
ok_t4 = len(dx) == 1 and dx[0][0].startswith("tab04") and len(dx[0][1]) == 1
if ok_t4:
    i, j = dx[0][1][0]
    old, new = str(x12[dx[0][0]][i][j]), str(x13[dx[0][0]][i][j])
    ins = inserido(old, new)
    NOTA = ins[0][2] if len(ins) == 1 and ins[0][0] == "insert" else ""
else:
    NOTA, ins = "", []
R.ok("D2.01 tabelas principais (xlsx): só 1 célula muda, o rodapé da Tabela 4, por uma inserção única (a nota 'n.a.') antes de 'Sources:'",
     ok_t4 and NOTA.startswith("n.a., not applicable or not estimated.") and new.count("Sources:") == 1 and new.index(NOTA) < new.index("Sources:"),
     f"abas diferentes {[(k, len(c)) for k, c in dx]}; inserção de {len(NOTA)} caracteres")
# D3 a nota explica toda célula n.a. da Tabela 4 (leitura minha das regras)
t4 = pd.read_csv(MS / "tabelas" / f"tab04_sensitivity_{V13}.csv", dtype=str)
na = [(r.Scenario, c, r[c]) for _, r in t4.iterrows() for c in t4.columns if str(r[c]).startswith("n.a")]
RODA = new if ok_t4 else ""
regras = {  # cenário → (condição sobre a coluna, frase do rodapé que explica)
    "Dating-robust": (lambda c: c.startswith("SGA"), "the dating-robust analysis and the weight >P97 reclassification do not apply to SGA"),
    "Weight >P97": (lambda c: c.startswith("SGA"), "the dating-robust analysis and the weight >P97 reclassification do not apply to SGA"),
    "Multiple imputation": (lambda c: "Wald" in c, "Joint Wald tests were not computed for the multiple-imputation analysis."),
    "GA in days": (lambda c: not c.startswith("SGA"), "Gestational age in days changes SGA only"),
    "Live-birth bounds": (lambda c: c.startswith("Provider") or "IC Indigenous" in c or "Wald" in c,
                          "live-birth bounds were computed only for preterm birth (total) and SGA, as a correction of the PR M2 without a race×tertile model, so IC and Wald tests are not estimated"),
    "Unclassified": (lambda c: "Wald" in c and c.startswith("Preterm birth (total)"),
                     "for the unclassified-preterm-birth scenarios this also holds for the Wald tests of total preterm birth"),
}
sem = []
for cen, col, v in na:
    if v in ("n.a. (unchanged)", "n.a. (not reclassified)"):
        frase = "'Unchanged' and 'not reclassified': the scenario does not change the outcome, so the main-analysis estimates apply"
        if frase not in RODA:
            sem.append((cen[:25], col[:30], v))
        continue
    k = [k for k in regras if cen.startswith(k)]
    if not k or not regras[k[0]][0](col) or regras[k[0]][1] not in RODA:
        sem.append((cen[:25], col[:30], v))
R.ok("D3.01 Tabela 4: as 38 células 'n.a.' têm explicação no rodapé v13 (SGA na datação robusta e no >P97; Wald da imputação múltipla; "
     "IG em dias; limites de nascidos vivos; Wald dos cenários de não classificados; 'unchanged'/'not reclassified')",
     not sem and len(na) > 0, f"{len(na)} células n.a.; sem explicação {sem[:4]}")
R.ok("D3.02 a Tabela 4 v13 (CSV) não mudou: as células n.a. são as mesmas da v12",
     t4.equals(pd.read_csv(A12 / "tabelas" / f"tab04_sensitivity_{V12}.csv", dtype=str)), f"{len(na)} n.a.")
e12 = abas(A12 / "suplementar" / f"ESM_1_tables_S1_S6_{V12}.xlsx")
e13 = abas(MS / "suplementar" / f"ESM_1_tables_S1_S6_{V13}.xlsx")
de = dif_abas(e12, e13)
R.ok("D4.01 ESM_1: só a aba S2b muda", [k for k, _ in de] == ["S2b_access_specifications"], [(k, len(c)) for k, c in de])
s2b = e13["S2b_access_specifications"]
flat = [str(v) for row in s2b for v in row if v is not None]
tit = [v for v in flat if v.startswith("Table S2b")]
rod = [v for v in flat if "(d) Tertiles" in v]
hdr_ok = all(c in flat for c in s13.columns) and all(v in flat for v in s13.iloc[:, 1:].to_numpy().ravel())
R.ok("D4.02 aba S2b: título novo; cabeçalhos e as 24 células de dados = CSV v13", tit == ["Table S2b. Alternative specifications of access to early "
     "prenatal care and of primary health care coverage"] and hdr_ok, tit)
t1 = pd.read_csv(AUD / "terc_auditor_v1_20261013.csv")  # só para garantir que o c1 rodou
J = {i["id"]: i for i in json.load(open(MS / f"numeros_chave_{V13}.json"))}
esperado_rod = ["N_aps_2015_2021", "rho_cobertura_x_indice", "rho_cobertura_x_populacao", "pct_concordancia_aps_indice", "kappa_aps_indice",
                "pct_Ind_T3_aps", "pct_Ind_T1_aps", "pct_Ind_T1_indice_2015_2021", "pct_Ind_T3_indice_2015_2021"]
c1 = {i["verificacao"][:5]: i["detalhe"] for i in json.load(open(AUD / f"res_c1_{__import__('os').environ.get('RODADA', 'r1')}_v1_20261013.json"))}
meus = {"N_aps_2015_2021": "18,624,544", "rho_cobertura_x_indice": "−0.10", "rho_cobertura_x_populacao": "−0.49",
        "pct_concordancia_aps_indice": "33.2%", "kappa_aps_indice": "0.05", "pct_Ind_T3_aps": "47.5%", "pct_Ind_T1_aps": "16.2%",
        "pct_Ind_T1_indice_2015_2021": "53.2%", "pct_Ind_T3_indice_2015_2021": "16.4%"}   # valores do meu C1 (C1.02, C1.06, C1.08, C1.09)
rodx = rod[0] if len(rod) == 1 else ""
seq = [rodx.find(meus[k] + ("" if k.startswith(("N_", "rho", "kappa")) else "")) for k in esperado_rod]
R.ok("D4.03 rodapé da S2b com os descritivos certos (meus valores do C1): N 18,624,544; ρ −0.10 e −0.49; 33.2%; κ 0.05; Indígenas 47.5% T3 / 16.2% T1 "
     "na cobertura e 53.2% T1 / 16.4% T3 no índice", len(rod) == 1 and all(s >= 0 for s in seq) and all(meus[k] == J[k]["valor_formatado"] for k in meus),
     dict(zip(esperado_rod, seq)))
ins_s2b = inserido([v for v in (str(x) for row in e12["S2b_access_specifications"] for x in row if x is not None) if "(a) Main specification" in v][0], rodx)
R.ok("D4.04 rodapé da S2b: mudanças em relação à v12 limitadas a (d)/(e), o Wald de 2 gl, '(b) to (e)' e as fontes novas",
     len(ins_s2b) <= 5 and all(any(t in b for t in ("(d) Tertiles", "In (b), the", "(d) and (e)", "to (e)", "tab_e8_04_interacao", "teams relative"))
                               or b == "" for _, a, b in ins_s2b), [(op, a[:40], b[:40], len(b)) for op, a, b in ins_s2b])
R.ok("D4.05 rodapé da S2b: '(d) ... Family Health Strategy and parameterized primary care teams' — a série inclui também as equipes "
     "equivalentes por carga horária (14,8% da cobertura somada; ver B2.03) [ressalva de redação]", True, "ver H")
R.ok("D4.06 Submissao/ESM_1.xlsx = ESM_1 do pacote v13 byte a byte", md5(PROJ / "Submissao/ESM_1.xlsx") == md5(MS / "suplementar" / f"ESM_1_tables_S1_S6_{V13}.xlsx"))


# D5 docx
def doc(p):
    d = docx.Document(p)
    return [q.text for q in d.paragraphs], [c.text for t in d.tables for r in t.rows for c in r.cells]


p12, c12 = doc(A12 / "tabelas" / f"tabelas_principais_{V12}.docx")
p13, c13 = doc(MS / "tabelas" / f"tabelas_principais_{V13}.docx")
dp = [(a, b) for a, b in zip(p12, p13) if a != b]
dp_ok = len(p12) == len(p13) and all(a.replace(V12, V13) == b or (NOTA and a.replace(V12, V13).replace("Sources:", NOTA + " Sources:", 1).replace("  ", " ") == b.replace("  ", " "))
                                     for a, b in dp)
R.ok("D5.01 docx: células das tabelas idênticas; parágrafos: só o rótulo de versão e a nota 'n.a.' no rodapé da Tabela 4",
     c12 == c13 and dp_ok and sum(NOTA in t for t in p13) == 1, f"{len(c13)} células; {len(dp)} parágrafos mudam")


# D6 PDFs
def txt(p):
    return "\n".join(pg.extract_text() for pg in PdfReader(p).pages)


pdfs = [(A12 / "suplementar" / f"S7_variables_codes_{V12}.pdf", MS / "suplementar" / f"S7_variables_codes_{V13}.pdf"),
        (A12 / "suplementar" / f"S8_strobe_record_checklist_{V12}.pdf", MS / "suplementar" / f"S8_strobe_record_checklist_{V13}.pdf")] + \
       [(A12 / "Submissao" / f"ESM_{k}.pdf", PROJ / "Submissao" / f"ESM_{k}.pdf") for k in (2, 3, 4)]
dpdf = [(b.name, inserido(txt(a).replace(V12, V13), txt(b))[:2]) for a, b in pdfs if txt(a).replace(V12, V13) != txt(b)]
R.ok("D6.01 PDFs (S7, S8 e ESM_2–4): texto extraído igual ao da v12 (fora o rótulo de versão)", not dpdf, dpdf[:3] or f"{len(pdfs)} PDFs")
R.ok("D6.02 ESM_2 = S7 v13 e ESM_3 = S8 v13 byte a byte", md5(PROJ / "Submissao/ESM_2.pdf") == md5(pdfs[0][1]) and md5(PROJ / "Submissao/ESM_3.pdf") == md5(pdfs[1][1]))


# D7 figuras
def px(p):
    im = Image.open(p)
    return im.mode, im.size, hashlib.md5(im.tobytes()).hexdigest(), tuple(round(float(v)) for v in im.info.get("dpi", (0, 0)))


figs = sorted(p for d in ("figuras", "suplementar") for p in (A12 / d).glob(f"*_{V12}.*") if p.suffix in (".png", ".tif"))
dfig = [p.name for p in figs if px(p) != px(MS / p.parent.name / p.name.replace(V12, V13))]
dsub = [k for k in range(1, 5) if px(A12 / "Submissao" / f"Fig{k}.tif") != px(PROJ / "Submissao" / f"Fig{k}.tif")]
R.ok("D7.01 figuras png/tif (4 figuras + S9) e Submissao/Fig1–4: mesmos pixels, modo, tamanho e dpi da v12", len(figs) == 10 and not dfig and not dsub,
     f"{len(figs)} figuras; diferentes {dfig + dsub}")
figbyte = [k for k, n in enumerate(["fig01_flowchart", "fig02_pr_race_m1m3", "fig03_rd_race_tercile", "fig04_dating"], 1)
           if md5(PROJ / "Submissao" / f"Fig{k}.tif") != md5(MS / "figuras" / f"{n}_{V13}.tif")]
R.ok("D7.02 Submissao/FigK.tif = figura TIFF v13 correspondente byte a byte", not figbyte, figbyte)
sub = sorted(p.name for p in (PROJ / "Submissao").iterdir())
R.ok("D7.03 Submissao/ só com Fig1–4 e ESM_1–4 (sem ._*)", sub == sorted([f"Fig{k}.tif" for k in range(1, 5)] + [f"ESM_{k}.{'xlsx' if k == 1 else 'pdf'}" for k in range(1, 5)]), sub)

# D8 números-chave
J12 = {i["id"]: i for i in json.load(open(A12 / f"numeros_chave_{V12}.json"))}
Jl = json.load(open(MS / f"numeros_chave_{V13}.json"))
novos = [k for k in J if k not in J12]
dif12 = {}
for k, a in J12.items():
    b = J.get(k, {})
    campos = sorted(c for c in set(a) | set(b) if a.get(c) != b.get(c))
    dif12[k] = campos
padrao = {k: c for k, c in dif12.items() if c != ["commit_pacote"]}
R.ok("D8.01 os 228 números da v12: iguais na v13 exceto commit_pacote (dc9328d → dc54fb9); n_regsaude_CE/DF também commit_registro e commit_analise ('' → dc54fb9)",
     len(J12) == 228 and len(J) == 249 and len(Jl) == 249 and set(padrao) == {"n_regsaude_CE", "n_regsaude_DF"}
     and all(padrao[k] == ["commit_analise", "commit_pacote", "commit_registro"] and J[k]["commit_registro"] == J[k]["commit_analise"] == "dc54fb9"
             and J12[k]["commit_registro"] == J12[k]["commit_analise"] == "" for k in padrao)
     and {i["commit_pacote"] for i in J12.values()} == {"dc9328d"} and {i["commit_pacote"] for i in Jl} == {"dc54fb9"},
     f"v12 {len(J12)}; v13 {len(J)}; com outras diferenças {padrao}")
c1j = json.load(open(AUD / f"res_c1_{__import__('os').environ.get('RODADA', 'r1')}_v1_20261013.json"))
esp = dict(meus)
for ex, s in (("tercil_aps", "aps"), ("tercil_ind21", "indice_2015_2021")):
    for d in OUTC:
        r = ind.loc[(ex, d)]
        esp[f"IC_Ind_T1_{s}_{d}"] = f"{num(r.ICR_pp)} ({num(r.ICR_lo)} to {num(r.ICR_hi)})"
        esp[f"Wald2_ind_{s}_{d}"] = pv(r.p_ind_2gl)
dnov = [(k, J[k]["valor_formatado"], esp.get(k)) for k in novos if J[k]["valor_formatado"] != esp.get(k)]
R.ok("D8.02 os 21 números novos: ids = esperados e valor formatado = meus resultados (R e C1)", len(novos) == 21 and set(novos) == set(esp) and not dnov,
     dnov or "21/21")
vb = [k for k in novos if k.startswith("IC_") and abs(J[k]["valor_bruto"] - 100 * 0 - ind.loc[("tercil_aps" if "aps" in k else "tercil_ind21",
      k.split("_", 4)[-1] if "aps" in k else k.split("2015_2021_")[1])].ICR_pp) > 1e-6]
R.ok("D8.03 números novos: valor_bruto do IC = meu R; arquivo/script de origem = tab_e8_03/04 e etapa8_03/04; commit_registro/analise vazios",
     not vb and all(J[k]["arquivo"].startswith("outputs/tables/tab_e8_0") and J[k]["script"] in ("scripts/etapa8_03_tercis.py", "scripts/etapa8_04_modelos.py")
                    and J[k]["commit_registro"] == J[k]["commit_analise"] == "" for k in novos), vb)
mdk = (MS / f"numeros_chave_{V13}.md").read_text()
R.ok("D8.04 numeros_chave .md v13: 249 ids, os 21 novos com o valor formatado", all(f"`{k}`" in mdk or f"| {k} |" in mdk for k in J)
     and all(J[k]["valor_formatado"] in mdk for k in novos), f"{sum(1 for k in J if k in mdk)} ids no md")

# D9 MANIFEST
man = (MS / "MANIFEST.md").read_text()
rows = re.findall(r"^\| (manuscrito/\S+|Submissao/\S+) \| [^|]*\| (?:[^|]|\\\|)*\| ([0-9a-f]{12}) \|$", man, flags=re.M)
bad = [f for f, h in rows if md5(PROJ / ("outputs/" + f if f.startswith("manuscrito/") else f))[:12] != h]
pac = sorted([f"manuscrito/{d}/{p.name}" for d in ("tabelas", "figuras", "suplementar") for p in (MS / d).glob(f"*_{V13}.*")]
             + [f"manuscrito/checa_7b_{V13}.csv", f"manuscrito/numeros_chave_{V13}.json", f"manuscrito/numeros_chave_{V13}.md",
                "manuscrito/data_code_availability.md", "manuscrito/legendas_figuras.md"] + [f"Submissao/{s}" for s in sub])
listados = sorted(f for f, _ in rows)
R.ok("D9.01 MANIFEST: MD5 (12) de cada arquivo listado = arquivo no disco; lista = pacote v13 completo (+ ficha 7c.0), sem v12 e sem audita_*",
     not bad and set(pac) <= set(listados) and not [f for f in listados if V12 in f or "audita_" in f]
     and set(listados) - set(pac) == {"manuscrito/ficha_metodos_7c0_v1_20261009.md"}, f"{len(rows)} linhas; MD5 divergente {bad}; faltam {sorted(set(pac) - set(listados))}")
m12 = (A12 / "MANIFEST_v12_20261013.md").read_text()
volta = man.replace(V13, V12)
dl = [l for l in difflib.unified_diff(m12.splitlines(), volta.splitlines(), lineterm="", n=0) if l[:1] in "+-" and not l.startswith(("+++", "---"))]
dl_md5 = [l for l in dl if not re.search(r"\| [0-9a-f]{12} \|$", l)]
R.ok("D9.02 MANIFEST v13 × v12 (com o rótulo de versão trocado): mudam só cabeçalho/histórico, a linha da S2b e MD5",
     len([l for l in dl_md5 if l.startswith("+")]) <= 5, [l[:90] for l in dl_md5 if l.startswith("+")][:6])

# D10 disponibilidade e legendas
d12 = " ".join((A12 / f"data_code_availability_{V12}.md").read_text().split())
d13 = " ".join((MS / "data_code_availability.md").read_text().split())
ins_d = inserido(d12.replace(V12, V13), d13)
acc = (PROJ / "docs/referencias/aps_cobertura_ab/ACESSO.txt").read_text()
R.ok("D10.01 disponibilidade: mudam só versão/etapa, o grep '^Etapa 8:', a fonte nova (data 2026-10-13, 467,880 registros, 5,570 municípios = ACESSO.txt) e a declaração",
     "on 2026-10-13; 467,880 records (5,570 municipalities)" in d13 and "2026-10-13 21:44:15 -03" in acc and '"^Etapa 8:"' in d13
     and "health care coverage report (Cobertura da Atenção Básica, 2007–2020)" in d13 and len(ins_d) <= 8,
     [(op, a[:50], b[:70]) for op, a, b in ins_d])
l12, l13 = (A12 / f"legendas_figuras_{V12}.md").read_text(), (MS / "legendas_figuras.md").read_text()
R.ok("D10.02 legendas das figuras: iguais às da v12, fora o rótulo de versão", l12.replace(V12, V13) == l13)
R.grava()
