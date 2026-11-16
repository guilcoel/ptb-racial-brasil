"""
Autoauditoria da Etapa 7b (asserts; falha = exceção). Saída: outputs/manuscrito/checa_7b_v1_20261009.csv e log.
  1. cada número do numeros_chave_*.json = arquivo de origem (valor bruto presente na tabela de origem, ou recomputado
     dela; tolerância de arredondamento) e o valor formatado = formatação do bruto
  2. Σ n da Tabela 1 (raças) = 25,808,740; total da coluna Total = 25,808,740
  3. n da análise robusta = 10,607,946
  4. nenhum número com EP por município: (a) scripts da 7b não citam tabelas com cluster por município; (b) IC das
     Tabelas 2, 3 e 4 = arquivos por região de saúde e ≠ arquivos por município
  5. figuras TIFF: resolução (600 dpi; fluxograma 1,200), largura 174 mm, compressão LZW; Submissao/ só com Fig1–4 e ESM_1–4
  6–8. checagens das Etapas 7b.1–7b.3; 9. Etapa 7c.1 (v5 = v4 só com rótulos novos; ver o bloco 9)
  9i. Etapa 8 (v12 × v13, arquivadas): S2b com a cobertura da Atenção Básica, nota "n.a." da Tabela 4, números-chave novos
  9j. Etapa 8b (v13 × v14, arquivadas): Wald de 6 gl das colunas (d) e (e) da S2b
  9k. Etapa 7d (v14 arquivada × v15): Submissao/ final, Online Resources renumeradas, Tabela 3b → S3b, TIFF RGB, manuscrito montado
"""
import hashlib
import json
import re

import numpy as np
import pandas as pd
from PIL import Image

import etapa7b_lib as B
import etapa0_lib as L

log = L.Logger("7b_checa", etapa="etapa7b")
res = []


def ok(nome, cond, valor=""):
    res.append(dict(verificacao=nome, ok=bool(cond), valor=str(valor)))
    log(f"{'OK ' if cond else 'FALHA'} {nome}: {valor}")
    assert cond, nome


# 1
J = json.load(open(B.MS / f"numeros_chave_{B.V}.json"))
nfalha, nderiv = 0, 0
DERIV = set()
for it in J:
    src = pd.read_csv(B.PROJ / it["arquivo"])
    v = it["valor_bruto"]
    vals = v if isinstance(v, list) else [v]
    achou = all(np.isclose(src.select_dtypes("number").to_numpy(dtype=float), x, rtol=1e-9, atol=1e-12).any() for x in vals)
    if not achou:                                             # 7c.6: derivado no pacote (usado no commit_analise, bloco 9g)
        DERIV.add(it["id"])
    if not achou and it["id"].startswith("prev_"):          # prevalência = casos/n do arquivo (Total = soma das raças)
        d_, g = re.match(r"prev_(.+)_(Branca|Parda|Preta|Indigena|Total)$", it["id"]).groups()
        x = src[(src.desfecho == d_) & (src.ig_metodo == "todos")]
        x = x if g == "Total" else x[x.raca == g]
        achou = np.isclose(100 * x.casos.sum() / x.n.sum(), v)
        nderiv += 1
    if not achou and it["id"].startswith("naoclass_"):        # total = soma das raças na amostra indicada
        amo = "analitica" if it["id"].endswith("analitica") else "com_regiao_saude"
        achou = int(src[src.amostra == amo].nao_classificados.sum()) == v
        nderiv += 1
    if not achou and it["id"].startswith("n_excl_estciv_"):    # 7c.3: N(M2) − N(M3) no mesmo arquivo
        d_ = it["id"].replace("n_excl_estciv_", "")
        x = src[(src.desfecho == d_)].groupby("modelo").N.first()
        achou = int(x["M2"] - x["M3"]) == v
        nderiv += 1
    if not achou and it["id"] == "pct_amarela_fonte":          # 7c.5: 100 × Asian (tab07, motivo 3) / nascidos vivos da fonte (tab06)
        f6_ = pd.read_csv(B.TB / f"tab06_fluxograma_regiao_v1_{B.S}.csv").query("regiao == 'Brasil' and passo == '0_fonte'")
        f7_ = pd.read_csv(B.TB / f"tab07_fluxograma_motivos_v1_{B.S}.csv", dtype={"motivo": str}).query(
            "regiao == 'Brasil' and passo == '1_raca' and motivo == '3'")
        achou = np.isclose(100 * f7_.n.iloc[0] / f6_.restante.iloc[0], v, rtol=1e-12)
        nderiv += 1
    if not achou and it["id"].startswith("limites_"):
        x = src[src.desfecho == it["id"].split("_", 1)[1]].RP_M2_corrigida
        achou = np.isclose([x.min(), x.max()], vals).all()
        nderiv += 1
    lead = re.sub(r"[%,]", "", it["valor_formatado"].replace("−", "-").split(" ")[0].split(":")[-1].strip() or "")
    if it["id"].startswith(("MAIHDA_top", "limites_")):
        lead = None
    fmt_ok = True
    if lead not in (None, "") and not isinstance(v, list):
        try:
            casas = len(lead.split(".")[1]) if "." in lead else 0
            fmt_ok = abs(float(lead) - round(float(v), casas)) <= 0.5 * 10 ** -casas + 1e-12
        except ValueError:
            fmt_ok = True
    if not (achou and fmt_ok):
        nfalha += 1
        log(f"  divergente: {it['id']} bruto={v} fmt={it['valor_formatado']} arquivo={it['arquivo']}")
ok("números-chave = arquivo de origem (bruto e formatado)", nfalha == 0, f"{len(J)} números; {nderiv} recomputados (casos/n, mín/máx); falhas {nfalha}")

# 2
nk = {i["id"]: i["valor_bruto"] for i in J}
soma = sum(nk[f"n_{g}"] for g in B.RACES)
ok("Tabela 1: Σ n por raça = 25,808,740 = coluna Total", soma == 25808740 == nk["n_Total"], f"{soma:,}")
t1 = pd.read_csv(B.TABD / f"tab01_characteristics_{B.V}.csv").fillna("")
def num0(s):
    return int(s.split(" ")[0].replace(",", ""))
for bl in ["Maternal age group", "Maternal education", "Macroregion"]:
    i = t1.index[t1.Characteristic.str.startswith(bl)][0]
    k = i + 1
    tot = 0
    while k < len(t1) and t1.Characteristic[k].startswith("  "):
        tot += num0(t1.Total[k])
        k += 1
    ok(f"Tabela 1: Σ categorias de '{bl}' = 25,808,740", tot == 25808740, f"{tot:,}")

# 3
ok("n da análise robusta à datação = 10,607,946", nk["N_robusta"] == 10607946, nk["N_robusta"])

# 4
scripts = "".join((B.PROJ / "scripts" / f).read_text() for f in
                  ["etapa7b_01_tabelas.py", "etapa7b_02_suplementar.py", "etapa7b_03_figuras.py", "etapa7b_04_submissao.py"])
cit = sorted({m for m in re.findall(r'rd\("([a-z0-9_]+)"\)', scripts)})
ok("scripts 7b só leem tabelas da lista de permissão (EP por região de saúde)", all(c in B.SRC and c not in B.PROIBIDAS for c in cit),
   f"{len(cit)} tabelas lidas")
mun = pd.read_csv(B.TB / f"tab_e3_02_interacao_v1_{B.S}.csv").query("analise == '3.2_tercil_reg' and estrato == 'Brasil'")
rs = pd.read_csv(B.TB / f"tab_e6_01a_interacao_v1_{B.S}.csv")
t3 = pd.read_csv(B.TABD / f"tab03_knol_tercile_{B.V}.csv").fillna("")
ic3 = set(t3["IC per 100 (95% CI)"]) - {""}
ic_rs = {B.rd_(r.ICR_pp, r.ICR_lo, r.ICR_hi) for _, r in rs.iterrows()}
ic_mun = {B.rd_(r.ICR_pp, r.ICR_lo, r.ICR_hi) for _, r in mun.iterrows()}
ok("Tabela 3: todos os IC (interaction contrast, com IC 95%) = arquivo por região de saúde e nenhum = arquivo por município",
   ic3 <= ic_rs and not (ic3 & ic_mun), f"{len(ic3)} IC")
e2m = pd.read_csv(B.TB / f"tab_e2_04_modelos_long_v1_{B.S}.csv").query("regiao == 'Brasil'")
t2 = pd.read_csv(B.TABD / f"tab02_models_m1m3_{B.V}.csv").fillna("")
pr2 = set(t2[["M1 PR (95% CI)", "M2 PR (95% CI)", "M3 PR (95% CI)"]].to_numpy().ravel()) - {"", "1.00"}
b6 = pd.read_csv(B.TB / f"tab_e6b_01_modelos_m1m3_v1_{B.S}.csv")
pr_rs = {B.pr(r.PR, r.PR_lo, r.PR_hi) for _, r in b6.iterrows()}
mm_ = b6.merge(e2m[["modelo", "desfecho", "raca", "RP_lo", "RP_hi"]], on=["modelo", "desfecho", "raca"])
# com IC estreitos, as duas versões podem coincidir na 2ª casa (arredondamento); o teste é sobre os limites brutos
ok("Tabela 2: todo PR (IC) = arquivo por região de saúde; limites brutos ≠ versão por município",
   pr2 <= pr_rs and (np.abs(mm_.PR_lo - mm_.RP_lo) > 1e-6).all() and (np.abs(mm_.PR_hi - mm_.RP_hi) > 1e-6).all(),
   f"{len(pr2)} PR; mín |Δ limite bruto| {min(np.abs(mm_.PR_lo - mm_.RP_lo).min(), np.abs(mm_.PR_hi - mm_.RP_hi).min()):.4f}")
t4 = pd.read_csv(B.TABD / f"tab04_sensitivity_{B.V}.csv").fillna("")
pr4 = {c for c in t4.filter(like="PR M2").to_numpy().ravel() if "(" in c and c[:1].isdigit()}
fontes4 = pr_rs | {B.pr(r.PR, r.PR_lo, r.PR_hi) for f in ["tab_e6b_01_m2_cenarios", "tab_e4_06_mi_m2_rubin_rs", "tab_e7b1_04_m2", "tab_e7b2_01_m2", "tab_e7b2_02_reclass_m2"]
                   for _, r in pd.read_csv(B.TB / f"{f}_v1_{B.S}.csv").iterrows()} | \
    {B.pr(r.RP, r.RP_lo, r.RP_hi) for f, q in [("tab_e6_01a_m2", "cluster == 'regsaude'"), ("tab_e6_04_m2", "raca == raca")]
     for _, r in pd.read_csv(B.TB / f"{f}_v1_{B.S}.csv").query(q).iterrows()}
ok("Tabela 4: todo PR M2 (IC) vem de arquivo por região de saúde", pr4 <= fontes4, f"{len(pr4)} PR")

# 5
for f in sorted(B.FIGD.glob(f"*_{B.V}.tif")) + sorted(B.SUPD.glob(f"*_{B.V}.tif")):
    im = Image.open(f)
    dpi = round(im.info["dpi"][0])
    larg = im.size[0] / dpi * 25.4
    alvo = 1200 if "flowchart" in f.name else 600
    ok(f"TIFF {f.name}: {alvo} dpi, 174 mm, LZW", dpi == alvo and abs(larg - 174) < 0.5 and im.info.get("compression") == "tiff_lzw",
       f"{dpi} dpi; {larg:.1f} mm; {im.info.get('compression')}")
sub = sorted(x.name for x in B.SUB.iterdir() if not x.name.startswith("._"))
SUB_FINAL = ["Cover_Letter.docx", "ESM_1.pdf", "ESM_2.pdf", "ESM_3.pdf", "ESM_4.xlsx", "ESM_5.pdf", "Fig1.tif", "Fig2.tif", "Fig3.tif", "Fig4.tif",
             "Manuscript.docx", "Title_Page.docx"]                       # 7d (v15)
ok("Submissao/ só com Title_Page, Manuscript, Cover_Letter (.docx), Fig1–4 (.tif), ESM_1–3 e ESM_5 (.pdf) e ESM_4 (.xlsx)", sub == SUB_FINAL, sub)
for k in range(1, 5):
    a, b = Image.open(B.SUB / f"Fig{k}.tif"), Image.open(sorted(B.FIGD.glob(f"fig0{k}_*_{B.V}.tif"))[0])
    ok(f"Submissao/Fig{k}.tif = figura versionada", a.size == b.size and a.info["dpi"] == b.info["dpi"], f"{a.size}")
# 6. Etapa 7b.1
ok("7b.1 Tabela 4: nenhuma célula pendente", not t4.isin(["not estimated (pending)"]).any().any())
blk = t2["Outcome / race"].tolist()
i_ptb = blk.index("Preterm birth (total)")
preta_ptb = t2.iloc[next(k for k in range(i_ptb + 1, len(t2)) if t2["Outcome / race"].iloc[k].strip() == "Black")]
ok("7b.1 Tabela 2: ΔPR para todos; atenuação n.a. quando |PR_M2cc − 1| < 0.10 (Black PTB total = n.a.)",
   preta_ptb["Outcome / race"].strip() == "Black" and preta_ptb["Attenuation, % (95% CI)"] == "n.a." and
   (t2[t2["M1 PR (95% CI)"].str.contains(r"\(")]["ΔPR M2→M3 (95% CI)"] != "n.a.").all(), preta_ptb["Attenuation, % (95% CI)"])
at = pd.read_csv(B.TB / f"tab_e3_00b_atenuacao_ic_rs_v1_{B.S}.csv")
n_mostra = int(((np.abs(at.RP_M2cc - 1) >= 0.10) & at.desfecho.isin(B.ORDER)).sum())
n_tab = int((t2["Attenuation, % (95% CI)"].fillna("").str.contains(r"\(")).sum())
ok("7b.1 Tabela 2: nº de atenuações mostradas = nº com |PR_M2cc − 1| ≥ 0.10 (4 desfechos)", n_mostra == n_tab, f"{n_tab}")
rr = pd.read_csv(B.TB / f"tab_e7b1_05_reri_recod_v1_{B.S}.csv").set_index(["raca", "nivel"])
alvo = {("Indigena", "T1"): -0.59, ("Indigena", "T2"): -0.67, ("Parda", "T1"): -0.17}
ok("7b.1 RERI recodificado (PTB indicado) = valores esperados ± 0.02", all(abs(rr.RERI_recod[k] - v) <= 0.02 for k, v in alvo.items()),
   {f"{k[0]}×{k[1]}": round(rr.RERI_recod[k], 3) for k in alvo})
col = [c for c in t3.columns if c.startswith("RERI, recoded")][0]
ok("7b.1 Tabela 3: coluna de RERI recodificado só no painel de PTB indicado (6 células)", int((t3[col] != "").sum()) == 6)
s1r = pd.read_csv(B.TB / f"tab_e7b1_02_s1_restrito_v1_{B.S}.csv").query("regiao == 'Brasil' and grupo == 'excluidos'").iloc[0]
ok("7b.1 S1 restrito: excluídos com IG 22–44 = 143,071/1,239,937 (11.54%, auditor da 7b)",
   (int(s1r.n_ptb_22_44), int(s1r.n_ig_22_44)) == (143071, 1239937), f"{s1r.ptb_pct_22_44:.2f}%")
af = pd.read_csv(B.TB / f"tab_e7b1_03_auc_fixa_v1_{B.S}.csv").set_index("modelo").loc["m2"]
ok("7b.1 AUC só da parte fixa do M2 ≈ 0.5609 (auditor da 7b; |dif| < 1e-4)", abs(af.AUC_parte_fixa - 0.5609) < 1e-4, f"{af.AUC_parte_fixa:.5f}")
ok("7b.1 não classificados: 131,809 (analítica) − 131,801 (com região) = 8", nk["naoclass_analitica"] - nk["naoclass_com_regiao"] == 8,
   f"{nk['naoclass_analitica']:,} − {nk['naoclass_com_regiao']:,}")
# 7. Etapa 7b.2
row2 = t4[t4.Scenario.str.startswith("Other method: code 2 only")]
rowr = t4[t4.Scenario.str.startswith("Weight >P97 preterm reclassified")]
c2 = pd.read_csv(B.TB / f"tab_e7b2_01_m2_v1_{B.S}.csv").query("cenario == 'codigo_2' and raca == 'Indigena' and desfecho == 'ptb'").iloc[0]
rm = pd.read_csv(B.TB / f"tab_e7b2_02_reclass_m2_v1_{B.S}.csv").query("desfecho == 'ptb_reclass' and raca == 'Indigena'").iloc[0]
ok("7b.2 Tabela 4: linhas 'code 2 only' e 'weight >P97 reclassified' presentes e iguais às fontes (PR PTB total)",
   len(row2) == 1 and len(rowr) == 1 and row2.iloc[0]["Preterm birth (total): PR M2 (95% CI)"] == B.pr(c2.PR, c2.PR_lo, c2.PR_hi)
   and rowr.iloc[0]["Preterm birth (total): PR M2 (95% CI)"] == B.pr(rm.PR, rm.PR_lo, rm.PR_hi),
   f"code 2 {B.pr(c2.PR, c2.PR_lo, c2.PR_hi)}; reclass {B.pr(rm.PR, rm.PR_lo, rm.PR_hi)}")
ok("7b.2 reclassificação: PR Indígena PTB total na ordem da Etapa 4b (1.05)", abs(rm.PR - 1.05) < 0.01, f"{rm.PR:.3f}")
import openpyxl
abas = openpyxl.load_workbook(B.SUB / "ESM_4.xlsx").sheetnames           # 7d: o xlsx das tabelas S é o ESM_4 (Online Resource 4)
ok("7b.2 ESM_4 (antigo ESM_1) com a aba S5c e sem S5b", "S5c_other_method_by_code" in abas and not any("S5b" in a for a in abas), abas)
cc = pd.read_csv(B.TB / f"tab_e7b2_01_casos_ind_v1_{B.S}.csv")
s5c = pd.read_csv(B.SUPD / f"S5c_other_method_by_code_{B.V}.csv").fillna("")
n_inst = int(s5c["Indigenous cases by tertile"].str.contains("UNSTABLE").sum())
n_esp = int(cc.groupby(["codigo", "desfecho"]).instavel.any().sum())
ok("7b.2 S5c: marcação de instabilidade (<30 casos indígenas num tercil) = fonte", n_inst == n_esp, f"{n_inst} estratos instáveis")
# 8. Etapa 7b.3
w2s = pd.read_csv(B.TB / f"tab_e7b3_02_wald_ind_v1_{B.S}.csv").set_index(["cenario", "desfecho"])
col2 = "Preterm birth (total): Wald p, Indigenous terms (2 df)"
mapa = {"Main analysis": "principal", "LMP-dated births only (code 8)": "codigo_8", "Other-method dating only (codes 1\u20132)": "outro_metodo_1_2",
        "Excluding CE and DF": "sem_CE_DF", "Weight >P97 preterm reclassified as non-cases (all methods)": "reclass_p97"}   # 7c.1: sem 2024 retirada
okw = col2 in t4.columns and all(t4.set_index("Scenario").loc[k, col2] == B.pval(w2s.p_ind_2gl[(v, "ptb")]) for k, v in mapa.items())
ok("7b.3 Tabela 4: coluna 'Wald p, Indigenous terms (2 df)' = fonte", okw, {k[:25]: t4.set_index("Scenario").loc[k, col2] for k in mapa} if col2 in t4.columns else "ausente")
ok("7b.3 Wald de 6 gl reproduzidos = publicados (onde existiam)", bool(w2s.wald6_conferido.sum() >= 20), f"{int(w2s.wald6_conferido.sum())}/{len(w2s)} conferidos")
abas = openpyxl.load_workbook(B.SUB / "ESM_4.xlsx").sheetnames
ok("7b.3 ESM_4 (antigo ESM_1) com a aba S5d", "S5d_spontaneous_by_code_wald" in abas, abas[-3:])
aud3 = B.PROJ / "audit_independente" / "etapa7b3" / "comparacao_7b3_v1_20261009.csv"
if aud3.exists():
    cp = pd.read_csv(aud3)
    dr = pd.to_numeric(cp.dif_rel, errors="coerce").abs().fillna(0)
    lim_ = cp.item.str.contains(r"_(?:lo|hi)(?:_|\[|$)")
    tab_ = cp.tarefa.astype(str).str.startswith("C")          # P97 pela tabela oficial: só quantificação
    ok("independente 7b.3 (R + DuckDB): A e B idênticos (pontos < 1e-5; limites < 2e-4)",
       (dr[~lim_ & ~tab_] < 1e-5).all() and (dr[lim_ & ~tab_] < 2e-4).all(),
       f"{len(cp)} itens; máx pontos {dr[~lim_ & ~tab_].max():.1e}; limites {dr[lim_ & ~tab_].max():.1e}")
aud2 = B.PROJ / "audit_independente" / "etapa7b2" / "comparacao_7b2_v1_20261009.csv"
if aud2.exists():
    cp = pd.read_csv(aud2)
    dr = pd.to_numeric(cp.dif_rel, errors="coerce").abs().fillna(0)
    eq = cp.item.str.contains("[eq]", regex=False)
    lim_ = cp.item.str.contains(r"_(?:lo|hi)(?:_|\[|$)")   # limites de IC (nomes ..._lo_..., ..._hi[eq], ..._lo)
    a_ = cp.tarefa.str.startswith("A")
    # A: idêntico (limites com z 1.96 × 1.959964); B/C: linhas [eq] (P97 pela equação, como no pacote) idênticas;
    # linhas pela tabela oficial do P97 só quantificam a diferença tabela × equação (não entram no critério)
    okA = (dr[a_ & ~lim_] < 1e-5).all() and (dr[a_ & lim_] < 2e-4).all()
    okE = (dr[eq & ~lim_] < 1e-5).all() and (dr[eq & lim_] < 2e-4).all()
    ok("independente 7b.2 (R + DuckDB): A idêntico; B/C idênticos com o P97 pela equação (linhas [eq])",
       okA and okE and eq.sum() > 0, f"{len(cp)} itens; A máx {dr[a_ & ~lim_].max():.1e}; [eq] máx {dr[eq & ~lim_].max():.1e}; "
                                     f"tabela oficial × equação: máx {dr[~a_ & ~eq].max():.3f} (quantificação)")
aud = B.PROJ / "audit_independente" / "etapa7b1" / "comparacao_7b1_v1_20261009.csv"
if aud.exists():
    cp = pd.read_csv(aud)
    dr = pd.to_numeric(cp.dif_rel, errors="coerce").abs().fillna(0)
    lim_ = cp.item.str.contains(r"_(lo|hi)$")
    # limites de IC: o auditor usou z = 1.96 (pacote: 1.959964) → diferença relativa até ~1e-4 nos limites
    ok("independente 7b.1 (R + DuckDB): pontos e contagens iguais (dif rel < 1e-6); limites de IC < 1e-4 (z 1.96 × 1.959964)",
       (dr[~lim_] < 1e-6).all() and (dr[lim_] < 1e-4).all(), f"{len(cp)} itens; máx dif rel pontos {dr[~lim_].max():.1e}; limites {dr[lim_].max():.1e}")
# 9. Etapa 7c.1: v5 = v4 com rótulos novos (IC, Brown, M3 'extended model'), sem a sensibilidade 'Excluding 2024', com a S7a
import ast
import subprocess
from collections import Counter

import pymupdf

NUM = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")      # números (milhar com vírgula, decimal com ponto)
import openpyxl


def abas(f):
    wb = openpyxl.load_workbook(f, read_only=True)
    out = {}
    for ws in wb.worksheets:
        vals = [c for row in ws.iter_rows(values_only=True) for c in row if c is not None]
        out[ws.title] = (str(vals[0]), str(vals[-1]))     # título (1ª célula) e rodapé (última célula)
    return out


def white_primeiro(x):
    out, bloco = [], []
    for _, r in x.iterrows():
        if not str(r.iloc[0]).startswith("  "):
            out += bloco
            bloco = [r]
        elif str(r.iloc[0]).strip() == "White (reference)":
            bloco.insert(1, r)
        else:
            bloco.append(r)
    return pd.DataFrame(out + bloco).reset_index(drop=True)


def compara(dA, vA, dB, vB, norm, prep=lambda x, nome: x, livre=lambda nome, linha, col: False, renome=lambda n: n, novas_cols=frozenset()):
    """Célula a célula: CSVs de tabelas/ e suplementar/ da versão A × B. norm = trocas de rótulo autorizadas (aplicadas ao texto de A);
    prep = ajustes autorizados de linhas (remoção/ordem); livre = células em que o texto/número pode mudar por decisão registrada;
    novas_cols = colunas que só existem em B (Etapa 8: S2b), conferidas à parte."""
    pares = [(dA / "tabelas" / f"{n}_{vA}.csv", dB[0] / f"{n}_{vB}.csv") for n in
             ["tab01_characteristics", "tab02_models_m1m3", "tab03_knol_tercile", "tab03b_terciles_region", "tab04_sensitivity"]]
    pares += [(f, dB[1] / renome(f.name.replace(vA, vB))) for f in sorted((dA / "suplementar").glob(f"*_{vA}.csv")) if not f.name.startswith("._")]
    ncel, dnum, dtxt, livres = 0, [], [], []
    for a, b in pares:
        x, y = pd.read_csv(a, dtype=str).fillna(""), pd.read_csv(b, dtype=str).fillna("")
        y = y.drop(columns=[c for c in y.columns if c in novas_cols])
        x = prep(x, b.name)
        if [norm(c, b.name) for c in x.columns] != list(y.columns) or x.shape != y.shape:
            dtxt.append(f"{b.name}: forma/colunas {x.shape}→{y.shape}")
            continue
        for i in range(len(x)):
            for j in range(x.shape[1]):
                ncel += 1
                u, v = x.iat[i, j], y.iat[i, j]
                if livre(b.name, y.iloc[i], y.columns[j]):
                    if u != v:
                        livres.append(f"{b.name}[{i},{y.columns[j]}]")
                    continue
                if NUM.findall(u) != NUM.findall(v):
                    dnum.append(f"{b.name}[{i},{y.columns[j]}]")
                elif norm(u, b.name) != v:
                    dtxt.append(f"{b.name}[{i},{y.columns[j]}]: {u[:40]!r}→{v[:40]!r}")
    return len(pares), ncel, dnum, dtxt, livres


def compara_xlsx(dA, vA, dB, vB, extra_ok, novas=frozenset()):
    falt = []
    for a, b in [(dA / "tabelas" / f"tabelas_principais_{vA}.xlsx", dB[0] / f"tabelas_principais_{vB}.xlsx"),
                 (dA / "suplementar" / f"ESM_1_tables_S1_S6_{vA}.xlsx", dB[1] / f"ESM_1_tables_S1_S6_{vB}.xlsx")]:
        x, y = abas(a), abas(b)
        assert set(y) - set(x) <= set(novas) and set(x) <= set(y), (a.name, set(x) ^ set(y))   # 7c.4: abas novas autorizadas
        for k in x:
            for parte in (0, 1):
                c4, c5 = Counter(NUM.findall(x[k][parte])), Counter(NUM.findall(y[k][parte]))
                if (c4 - c5) or not ((c5 - c4) <= extra_ok):
                    falt.append(f"{b.name}/{k}/{'título' if parte == 0 else 'rodapé'}: some {dict(c4 - c5)}; novo {dict(c5 - c4)}")
    return falt


def tira_2024(x, nome):
    return x[~x.Scenario.astype(str).str.startswith("Excluding 2024")].reset_index(drop=True) if "Scenario" in x.columns else x


Jcur = {i["id"]: i for i in J}
A4, V4 = B.MS / "_arquivo_v4", "v4_20261009"
A5, V5 = B.MS / "_arquivo_v5", "v5_20261009"
A6, V6 = B.MS / "_arquivo_v6", "v6_20261009"
A7, V7 = B.MS / "_arquivo_v7", "v7_20261009"
A8, V8 = B.MS / "_arquivo_v8", "v8_20261009"
A9, V9 = B.MS / "_arquivo_v9", "v9_20261009"
A10, V10 = B.MS / "_arquivo_v10", "v10_20261009"
A11, V11 = B.MS / "_arquivo_v11", "v11_20261009"
A12, V12 = B.MS / "_arquivo_v12", "v12_20261013"
A13, V13 = B.MS / "_arquivo_v13", "v13_20261013"
A14, V14 = B.MS / "_arquivo_v14", "v14_20261026"
J4 = {i["id"]: i for i in json.load(open(A4 / f"numeros_chave_{V4}.json"))}
J5 = {i["id"]: i for i in json.load(open(A5 / f"numeros_chave_{V5}.json"))}
J6 = {i["id"]: i for i in json.load(open(A6 / f"numeros_chave_{V6}.json"))}
J7 = {i["id"]: i for i in json.load(open(A7 / f"numeros_chave_{V7}.json"))}
J8 = {i["id"]: i for i in json.load(open(A8 / f"numeros_chave_{V8}.json"))}
J9 = {i["id"]: i for i in json.load(open(A9 / f"numeros_chave_{V9}.json"))}
J10 = {i["id"]: i for i in json.load(open(A10 / f"numeros_chave_{V10}.json"))}
J11l = json.load(open(A11 / f"numeros_chave_{V11}.json"))
J11 = {i["id"]: i for i in J11l}
J12l = json.load(open(A12 / f"numeros_chave_{V12}.json"))
J12 = {i["id"]: i for i in J12l}
J13l = json.load(open(A13 / f"numeros_chave_{V13}.json"))
J13 = {i["id"]: i for i in J13l}
J14l = json.load(open(A14 / f"numeros_chave_{V14}.json"))
J14 = {i["id"]: i for i in J14l}


def pacote_esperado(versao):
    """7c.7: commit_pacote = HEAD ao gerar o pacote. Antes do commit que versiona o JSON da versão, é o HEAD atual; depois dele, o pai
    desse commit (a checagem da 7c.6 exigia sempre o HEAD atual e falhava se o checa fosse reexecutado depois do commit da etapa)."""
    add = subprocess.run(["git", "-C", str(B.PROJ), "log", "--diff-filter=A", "--format=%h", "--", f"outputs/manuscrito/numeros_chave_{versao}.json"],
                         capture_output=True, text=True).stdout.split()
    if not add:
        return B.COMMIT
    return subprocess.run(["git", "-C", str(B.PROJ), "rev-parse", "--short", f"{add[-1]}^"], capture_output=True, text=True).stdout.strip()


# ---- 9a. Etapa 7c.1: v4 × v5 (as duas versões arquivadas)
TIRADOS = {"ICR_Ind_T1_ptb_sem_2024", "Wald_p_ptb_sem_2024", "Wald2_ind_sem_2024_ptb"}
iguais = [k for k in J5 if k in J4 and J5[k]["valor_bruto"] == J4[k]["valor_bruto"] and J5[k]["valor_formatado"] == J4[k]["valor_formatado"]]
ok("7c.1 números-chave: os da v5 são idênticos aos da v4 (bruto e formatado); só saem os 3 da sensibilidade sem 2024",
   set(J4) - set(J5) == TIRADOS and set(J5) <= set(J4) and len(iguais) == len(J5) == len(J4) - 3,
   f"v4 {len(J4)}; v5 {len(J5)}; idênticos {len(iguais)}; retirados {sorted(set(J4) - set(J5))}")
n_ruim = lambda js: sum(bool(re.search(r"\bICR\b|\bParda\b", i["descricao"])) for i in js)
ok("7c.1 números-chave: descrições sem 'ICR' e sem 'Parda'", n_ruim(J) == 0, f"descrições com ICR/Parda: v4 {n_ruim(J4.values())} → atual {n_ruim(J)}")
NORM1 = lambda t, nome="": re.sub(r"\bParda\b", "Brown", re.sub(r"\bICR\b", "IC", str(t)))
np_, nc_, dn_, dt_, _ = compara(A4, V4, (A5 / "tabelas", A5 / "suplementar"), V5, NORM1,
                                prep=lambda x, nome: white_primeiro(tira_2024(x, nome)) if nome.startswith("tab02") else tira_2024(x, nome),
                                renome=lambda n: n.replace("S7_dictionary_", "S7b_dictionary_"))
ok("7c.1 v4 × v5 célula a célula (tabelas e suplementares CSV): números idênticos; texto = v4 com ICR→IC e Parda→Brown",
   not dn_ and not dt_, f"{np_} pares; {nc_:,} células; dif números {dn_[:3]}; dif texto {dt_[:3]}")
falt = compara_xlsx(A4, V4, (A5 / "tabelas", A5 / "suplementar"), V5, Counter(NUM.findall(B.NOTE_IC + " " + B.NOTE_BROWN)))
ok("7c.1 títulos e rodapés (xlsx): nenhum número da v4 some; os novos vêm só das notas acrescentadas", not falt, falt[:3] or "ok")

# ---- 9b. Etapa 7c.2: v5 × v6 (as duas versões arquivadas)
iguais2 = [k for k in J6 if k in J5 and J6[k]["valor_bruto"] == J5[k]["valor_bruto"] and J6[k]["valor_formatado"] == J5[k]["valor_formatado"]]
ok("7c.2 números-chave: mesmos ids e valores idênticos à v5 (bruto e formatado); nenhum alterado pela recodificação do SEXO do SIM",
   set(J6) == set(J5) and len(iguais2) == len(J6), f"v5 {len(J5)}; v6 {len(J6)}; idênticos {len(iguais2)}")
TERT = lambda t: str(t).replace("tercile", "tertile").replace("Tercile", "Tertile")
NORM2 = lambda t, nome="": (TERT(t).replace("3 Amarela (Asian descent)", "3 Asian (amarela)") if nome.startswith("S7a") else TERT(t))
SEXO_SIM = lambda nome, linha, col: nome.startswith("S7a") and linha.get("System") == "SIM" and linha.get("Variable") == "SEXO" and col.startswith("Codes")
np2, nc2, dn2, dt2, lv2 = compara(A5, V5, (A6 / "tabelas", A6 / "suplementar"), V6, NORM2, livre=SEXO_SIM)
ok("7c.2 v5 × v6 célula a célula: números idênticos; texto = v5 com tercile→tertile e, na S7a, 'Asian (amarela)'; só a célula do SEXO do SIM "
   "na S7a reescrita", not dn2 and not dt2 and lv2 == [c for c in lv2 if c.startswith("S7a")] and len(lv2) == 1,
   f"{np2} pares; {nc2:,} células; dif números {dn2[:3]}; dif texto {dt2[:3]}; células reescritas {lv2}")
falt2 = compara_xlsx(A5, V5, (A6 / "tabelas", A6 / "suplementar"), V6, Counter())
ok("7c.2 títulos e rodapés (xlsx): mesmos números da v5", not falt2, falt2[:3] or "ok")
lim_ = pd.read_csv(B.TB / f"tab_e7c2_01_limites_v1_{B.S}.csv")
lim0 = pd.read_csv(B.TB / f"tab_e6_07b_limites_v1_{B.S}.csv")
qq = pd.read_csv(B.TB / f"tab_e7c2_01_q_pig_v1_{B.S}.csv")
sx = pd.read_csv(B.TB / f"tab_e7c2_01_sexo_sim_v1_{B.S}.csv", dtype={"codigo": str})
ok("7c.2 SEXO do SIM: sem códigos em letra em 2015–2024; q do PIG e limites recalculados = publicados (o pacote segue com tab_e6_07b_limites)",
   int(sx[sx.codigo.str.upper().isin(["M", "F", "I"])].n.sum()) == 0 and qq.q_pig.nunique() == 1 and qq.n_obitos_na_grade.nunique() == 1
   and float(np.abs(lim_.RP_M2_corrigida / lim0.RP_M2_corrigida - 1).max()) < 1e-12,
   f"códigos {sorted(sx.codigo.unique())}; q {qq.q_pig.iloc[0]:.6f} (n {int(qq.n_obitos_na_grade.iloc[0]):,}); "
   f"máx dif relativa dos limites {float(np.abs(lim_.RP_M2_corrigida / lim0.RP_M2_corrigida - 1).max()):.1e}")
s7a_ = pd.read_csv(B.SUPD / f"S7a_variables_codes_{B.V}.csv")
rac = s7a_[(s7a_.System == "SINASC") & (s7a_.Variable == "RACACORMAE")].iloc[0]
sxs = s7a_[(s7a_.System == "SIM") & (s7a_.Variable == "SEXO")].iloc[0]
ok("7c.2 S7a: 'Asian (amarela)' no RACACORMAE e a recodificação M→1, F→2 no SEXO do SIM",
   "3 Asian (amarela)" in rac["Official label (English translation)"] and "Amarela (Asian descent)" not in rac["Official label (English translation)"]
   and "M → 1, F → 2" in sxs["Codes used and recoding in this study"])
legs = [l for l in B.MS.joinpath("legendas_figuras.md").read_text().split("\n\n") if l.startswith("**Fig. 1")]
ok("7c.2 legenda da Fig. 1 com a nota Brown/Black", len(legs) == 1 and B.NOTE_BROWN in legs[0])

# ---- 9c. Etapa 7c.3: v6 (arquivada) × v7 (atual)
NOVOS3 = ({f"{p}_{d}" for d in B.ORDER for p in ("N_M2", "N_M3", "n_excl_estciv")} |
          {f"{p}_{d}" for d in ("ptb", "pig", "ptb_ind") for p in ("IC_Ind_T1_tertil_nacional", "Wald_p_tertil_nacional", "RP_int_5pp_indice_continuo")})
iguais3 = [k for k in J6 if k in J7 and J7[k]["valor_bruto"] == J6[k]["valor_bruto"] and J7[k]["valor_formatado"] == J6[k]["valor_formatado"]]
ok("7c.3 números-chave: os da v6 idênticos (bruto e formatado); entram só os 21 novos (N do M2/M3, excluídos por estado civil ausente, "
   "especificações alternativas do acesso)", set(J7) - set(J6) == NOVOS3 and set(J6) <= set(J7) and len(iguais3) == len(J6),
   f"v6 {len(J6)}; v7 {len(J7)}; idênticos {len(iguais3)}; novos {len(set(J7) - set(J6))}")
alt_src = {Jcur[k]["arquivo"] for k in NOVOS3 if not k.startswith(("N_", "n_"))}
ok("7c.3 especificações alternativas lidas só de tabelas com EP por região de saúde (_rs; G = 433)",
   all("_rs_v1_" in f for f in alt_src) and (pd.read_csv(B.TB / f"tab_e3_02_wald_rs_v1_{B.S}.csv").query("analise == '3.3b_tercil_nac'").G == 433).all(),
   sorted(f.split("/")[-1] for f in alt_src))
NORM3 = lambda t, nome="": str(t).replace("Amarela (Asian descent)", "Asian (amarela)").replace("missing or Amarela", "missing or Asian (amarela)")
np3, nc3, dn3, dt3, _ = compara(A6, V6, (A7 / "tabelas", A7 / "suplementar"), V7, NORM3)
ok("7c.3 v6 × v7 célula a célula: números idênticos; texto = v6 com 'Amarela' → 'Asian (amarela)'", not dn3 and not dt3,
   f"{np3} pares; {nc3:,} células; dif números {dn3[:3]}; dif texto {dt3[:3]}")
ROT2 = "N, M1 and M2 / M2cc and M3 (births excluded from M2cc and M3 for missing marital status)"
extra3 = Counter(NUM.findall(ROT2)) + Counter(f"{int(Jcur[f'n_excl_estciv_{d}']['valor_bruto']):,}" for d in B.ORDER)
falt3 = compara_xlsx(A6, V6, (A7 / "tabelas", A7 / "suplementar"), V7, extra3)
ok("7c.3 títulos e rodapés (xlsx): nenhum número da v6 some; os novos são só os excluídos por estado civil ausente (rodapé da Tabela 2)",
   not falt3, falt3[:3] or "ok")
rod2_7 = [v[1] for k, v in abas(B.TABD / f"tabelas_principais_{B.V}.xlsx").items() if k.startswith("tab02_")][0]
ok("7c.3 Tabela 2: rodapé com N do M2 e do M2cc/M3 e os excluídos por estado civil ausente, por desfecho",
   ROT2 in rod2_7 and all(f"{B.OUTC[d]} {Jcur[f'N_M2_{d}']['valor_formatado']} / {Jcur[f'N_M3_{d}']['valor_formatado']} "
                          f"({Jcur[f'n_excl_estciv_{d}']['valor_formatado']})" in rod2_7 for d in B.ORDER),
   "; ".join(f"{d} {Jcur[f'n_excl_estciv_{d}']['valor_formatado']}" for d in B.ORDER))
ok("7c.3 'Asian (amarela)' nas descrições de excl_1_raca e excl_amarela; nenhuma descrição com 'Amarela'",
   all("Asian (amarela)" in Jcur[k]["descricao"] for k in ("excl_1_raca", "excl_amarela")) and not any("Amarela" in i["descricao"] for i in J),
   f"{Jcur['excl_amarela']['descricao']}")

# ---- 9d. Etapa 7c.4: v7 × v8 (as duas versões arquivadas): só entra a Tabela S2b
iguais4 = [k for k in J7 if k in J8 and J8[k]["valor_bruto"] == J7[k]["valor_bruto"] and J8[k]["valor_formatado"] == J7[k]["valor_formatado"]]
ok("7c.4 números-chave: os mesmos ids e valores da v7 (bruto e formatado)", set(J8) == set(J7) and len(iguais4) == len(J7),
   f"v7 {len(J7)}; v8 {len(J8)}; idênticos {len(iguais4)}")
np4, nc4, dn4, dt4, _ = compara(A7, V7, (A8 / "tabelas", A8 / "suplementar"), V8, lambda t, nome="": str(t))
ok("7c.4 v7 × v8 célula a célula: tabelas e suplementares idênticos (a S2b é arquivo novo)", not dn4 and not dt4,
   f"{np4} pares; {nc4:,} células; dif números {dn4[:3]}; dif texto {dt4[:3]}")
falt4 = compara_xlsx(A7, V7, (A8 / "tabelas", A8 / "suplementar"), V8, Counter(), novas={"S2b_access_specifications"})
ok("7c.4 xlsx: títulos e rodapés das abas existentes iguais à v7; só a aba S2b é nova", not falt4, falt4[:3] or "ok")
s2b = pd.read_csv(B.SUPD / f"S2b_access_specifications_{B.V}.csv").set_index("Outcome")
ai_ = pd.read_csv(B.TB / f"tab_e3_02_interacao_rs_v1_{B.S}.csv").query("estrato == 'Brasil' and raca == 'Indigena'")
aw_ = pd.read_csv(B.TB / f"tab_e3_02_wald_rs_v1_{B.S}.csv").query("estrato == 'Brasil' and analise == '3.3b_tercil_nac'").set_index("desfecho")
ac_ = pd.read_csv(B.TB / f"tab_e3_03a_indice_continuo_rs_v1_{B.S}.csv").query("raca == 'Indigena'").drop_duplicates("desfecho").set_index("desfecho")
conf = []
for d_ in ["ptb", "pig", "ptb_ind"]:
    r = s2b.loc[B.OUTC[d_]]
    a_ = ai_[(ai_.analise == "3.2_tercil_reg") & (ai_.nivel == "T1") & (ai_.desfecho == d_)].iloc[0]
    n_ = ai_[(ai_.analise == "3.3b_tercil_nac") & (ai_.nivel == "T1_pior") & (ai_.desfecho == d_)].iloc[0]
    c_ = ac_.loc[d_]
    conf += [r.iloc[0] == B.rd_(a_.ICR_pp, a_.ICR_lo, a_.ICR_hi) == B.rd_(*[pd.read_csv(B.TB / f"tab_e6_01a_interacao_v1_{B.S}.csv")
             .query("raca == 'Indigena' and nivel == 'T1' and desfecho == @d_").iloc[0][k] for k in ("ICR_pp", "ICR_lo", "ICR_hi")]),
             r.iloc[1] == B.rd_(n_.ICR_pp, n_.ICR_lo, n_.ICR_hi), r.iloc[2] == B.pval(aw_.p[d_]),
             r.iloc[3] == B.pr(c_.RP_por_5pp_interacao, c_.int_lo, c_.int_hi),
             r.iloc[1] == Jcur[f"IC_Ind_T1_tertil_nacional_{d_}"]["valor_formatado"], r.iloc[3] == Jcur[f"RP_int_5pp_indice_continuo_{d_}"]["valor_formatado"]]
ok("7c.4 S2b = fontes _rs (a = Tabela 3 e tab_e6_01a; b e c = números-chave da 7c.3); Wald com 6 gl e G = 433",
   all(conf) and (aw_.gl == 6).all() and (aw_.G == 433).all() and list(s2b.index) == [B.OUTC[d] for d in ["ptb", "pig", "ptb_ind"]],
   f"{sum(conf)}/{len(conf)} células conferidas")
rod_s2b = abas(B.SUPD / f"ESM_4_tables_S1_S6_{B.V}.xlsx")["S2b_access_specifications"][1]
ok("7c.4 S2b: rodapé com G = 433, definição do IC, Wald de 6 gl e as 3 fontes; aba presente no ESM_4 (antigo ESM_1) de Submissao/",
   all(x in rod_s2b for x in ["(G = 433)", "IC (interaction contrast) = risk difference", "6 df", "tab_e3_02_interacao_rs", "tab_e3_02_wald_rs",
                               "tab_e3_03a_indice_continuo_rs"]) and "S2b_access_specifications" in openpyxl.load_workbook(B.SUB / "ESM_4.xlsx").sheetnames)

# ---- 9e. Etapa 7c.5: v8 × v9 (as duas versões arquivadas): justificativa Asian na S1 e na disponibilidade; Submissao/ sem ._*
FRASE_AM = ("excluded because this small group (0.43% of registered births) would not yield stable estimates in analyses stratified by "
            "access tertile within macroregion, and to keep the eligibility criteria of our regional study")   # texto aprovado (7c.5)
pa = J9.get("pct_amarela_fonte", {})
iguais5 = [k for k in J8 if k in J9 and J9[k]["valor_bruto"] == J8[k]["valor_bruto"] and J9[k]["valor_formatado"] == J8[k]["valor_formatado"]]
ok("7c.5 números-chave: os 225 da v8 idênticos (bruto e formatado); entra só pct_amarela_fonte = excl_amarela / N_fonte = 0.43%",
   set(J9) - set(J8) == {"pct_amarela_fonte"} and set(J8) <= set(J9) and len(iguais5) == len(J8)
   and abs(pa["valor_bruto"] - 100 * J9["excl_amarela"]["valor_bruto"] / J9["N_fonte"]["valor_bruto"]) < 1e-12 and pa["valor_formatado"] == "0.43%",
   f"v8 {len(J8)}; v9 {len(J9)}; idênticos {len(iguais5)}; {J9['excl_amarela']['valor_formatado']} / {J9['N_fonte']['valor_formatado']} = "
   f"{pa.get('valor_bruto', float('nan')):.4f}% → {pa.get('valor_formatado')}")
np5, nc5, dn5, dt5, _ = compara(A8, V8, (A9 / "tabelas", A9 / "suplementar"), V9, lambda t, nome="": str(t))
ok("7c.5 v8 × v9 célula a célula: tabelas e suplementares CSV idênticos", not dn5 and not dt5,
   f"{np5} pares; {nc5:,} células; dif números {dn5[:3]}; dif texto {dt5[:3]}")
falt5 = compara_xlsx(A8, V8, (A9 / "tabelas", A9 / "suplementar"), V9, Counter(["0.43"]))
ok("7c.5 xlsx: títulos e rodapés iguais à v8; o único número novo é o 0.43 da justificativa", not falt5, falt5[:3] or "ok")
FRASE_S1 = f"Births to mothers of Asian (amarela) race/skin color were {FRASE_AM}. "
r8, r9 = abas(A8 / "suplementar" / f"ESM_1_tables_S1_S6_{V8}.xlsx"), abas(A9 / "suplementar" / f"ESM_1_tables_S1_S6_{V9}.xlsx")
difabas = sorted(k for k in r8 if r8[k] != r9[k])
ok("7c.5 S1: rodapé = rodapé da v8 + a frase aprovada (inserida após a 1ª frase); nenhuma outra aba muda; idem no ESM_1 de Submissao/",
   difabas == ["S1_flow_excluded"] and FRASE_S1 in r9["S1_flow_excluded"][1] and r9["S1_flow_excluded"][1].replace(FRASE_S1, "") == r8["S1_flow_excluded"][1]
   and abas(A9 / "Submissao" / "ESM_1.xlsx")["S1_flow_excluded"] == r9["S1_flow_excluded"], f"abas alteradas {difabas}")
d8 = " ".join((A8 / f"data_code_availability_{V8}.md").read_text().split())
d9 = " ".join((A9 / f"data_code_availability_{V9}.md").read_text().split())
SEC = (f"## Eligibility (STROBE 6a) - Births to mothers of Asian (amarela) race/skin color were {FRASE_AM} (0.43% = 117,549 / 27,489,150 "
       "live births to residents, 2015–2024; Table S1; tab07_fluxograma_motivos, tab06_fluxograma_regiao). ")
volta = (d9.replace(SEC, "").replace(V9, V8).replace("Etapa 7c.5: limpeza da Submissao e justificativa Asian", "Etapa 7c.4: Tabela S2b e conferências")
         .replace('"Etapa 7c.5"', '"Etapa 7c.4"').replace("Etapa 7c.5)", "Etapa 7c.4)"))
ok("7c.5 data_code_availability: seção de elegibilidade com a frase aprovada e 117,549 / 27,489,150; o resto igual à v8 (fora versão e commit)",
   SEC in d9 and volta == d8, "ok" if volta == d8 else [i for i, (a, b) in enumerate(zip(volta, d8)) if a != b][:1])
gi = (B.PROJ / ".gitignore").read_text().splitlines()
src4 = (B.PROJ / "scripts" / "etapa7b_04_submissao.py").read_text()
lixo = sorted(str(x.relative_to(B.SUB)) for x in B.SUB.rglob("*") if x.name.startswith("._") or x.name == ".DS_Store")
ok("7c.5 Submissao/ sem ._* e sem .DS_Store; .gitignore com ._* e .DS_Store; dot_clean -m antes e depois da montagem",
   not lixo and "._*" in gi and ".DS_Store" in gi and src4.count('"dot_clean", "-m"') == 1 and src4.count("\nlimpa_macos(B.SUB)") == 2,
   lixo or f"{len(list(B.SUB.iterdir()))} arquivos")
px = lambda f: (lambda im: (im.size, im.info.get("dpi"), hashlib.md5(im.tobytes()).hexdigest()))(Image.open(f))
txt_pdf = lambda f: "\n".join(pg.get_text() for pg in pymupdf.open(f))
ok("7c.5 Submissao/: Fig1–4 com os mesmos pixels e dpi da v8; ESM_2–4 com o mesmo texto da v8",
   all(px(A9 / "Submissao" / f"Fig{k}.tif") == px(A8 / "Submissao" / f"Fig{k}.tif") for k in range(1, 5))
   and all(txt_pdf(A9 / "Submissao" / f"ESM_{k}.pdf") == txt_pdf(A8 / "Submissao" / f"ESM_{k}.pdf") for k in (2, 3, 4)))

# ---- 9f. Etapa 7c.5b: v9 × v10 (as duas versões arquivadas): denominador do índice explícito nos rodapés; referências e auditorias no git
DEN_ANT = "initiated in the first trimester in the mother's health region"
DEN_NOVO = "initiated in the first trimester, among births with known month of prenatal care initiation, in the mother's health region"
iguais6 = [k for k in J9 if k in J10 and J10[k]["valor_bruto"] == J9[k]["valor_bruto"] and J10[k]["valor_formatado"] == J9[k]["valor_formatado"]]
ok("7c.5b números-chave: os mesmos ids e valores da v9 (bruto e formatado)", set(J10) == set(J9) and len(iguais6) == len(J9),
   f"v9 {len(J9)}; v10 {len(J10)}; idênticos {len(iguais6)}")
np6, nc6, dn6, dt6, _ = compara(A9, V9, (A10 / "tabelas", A10 / "suplementar"), V10, lambda t, nome="": str(t))
ok("7c.5b v9 × v10 célula a célula: tabelas e suplementares CSV idênticos", not dn6 and not dt6,
   f"{np6} pares; {nc6:,} células; dif números {dn6[:3]}; dif texto {dt6[:3]}")
falt6 = compara_xlsx(A9, V9, (A10 / "tabelas", A10 / "suplementar"), V10, Counter())
ok("7c.5b xlsx: nenhum número entra ou sai de títulos e rodapés", not falt6, falt6[:3] or "ok")
mud6, ruim6 = [], []
for a_, b_ in [(A9 / "tabelas" / f"tabelas_principais_{V9}.xlsx", A10 / "tabelas" / f"tabelas_principais_{V10}.xlsx"),
               (A9 / "suplementar" / f"ESM_1_tables_S1_S6_{V9}.xlsx", A10 / "suplementar" / f"ESM_1_tables_S1_S6_{V10}.xlsx")]:
    x_, y_ = abas(a_), abas(b_)
    for k in x_:
        mud6 += [k] if x_[k] != y_[k] else []
        ruim6 += [k] if (x_[k][0], x_[k][1].replace(DEN_ANT, DEN_NOVO)) != y_[k] or DEN_ANT in y_[k][1] else []
ok("7c.5b rodapés: só muda a definição do índice (+ 'among births with known month of prenatal care initiation'), nas 11 abas que a trazem; "
   "ESM_1 de Submissao/ = ESM_1 da v10", not ruim6 and len(mud6) == 11 and abas(A10 / "Submissao" / "ESM_1.xlsx") == abas(A10 / "suplementar" / f"ESM_1_tables_S1_S6_{V10}.xlsx"),
   ruim6 or f"{len(mud6)} abas: {mud6}")
import docx as _dx
dtx = " ".join(p_.text for p_ in _dx.Document(A10 / "tabelas" / f"tabelas_principais_{V10}.docx").paragraphs)
ok("7c.5b docx: definição nova em todo rodapé que define o índice; nenhuma ocorrência da antiga", DEN_ANT not in dtx and DEN_NOVO in dtx,
   f"{dtx.count(DEN_NOVO)} ocorrências")
d9b = " ".join((A9 / f"data_code_availability_{V9}.md").read_text().split())
d10 = " ".join((A10 / f"data_code_availability_{V10}.md").read_text().split())
volta6 = (d10.replace(V10, V9).replace("Etapa 7c.5b: pontas soltas (referências, auditorias, denominador do índice)",
                                       "Etapa 7c.5: limpeza da Submissao e justificativa Asian")
          .replace('"Etapa 7c.5b"', '"Etapa 7c.5"').replace("Etapa 7c.5b)", "Etapa 7c.5)"))
ok("7c.5b data_code_availability: igual à v9, fora versão e commit de referência", volta6 == d9b,
   "ok" if volta6 == d9b else [i for i, (a, b) in enumerate(zip(volta6, d9b)) if a != b][:1])
trk = set(subprocess.run(["git", "-C", str(B.PROJ), "ls-files", "docs/referencias", "audit_independente"], capture_output=True, text=True).stdout.splitlines())
aud_txt = sorted(str(x.relative_to(B.PROJ)) for x in (B.PROJ / "audit_independente").rglob("*.txt") if not x.name.startswith("._"))
ACESSOS = {"docs/referencias/censo2022/ACESSO.txt", "docs/referencias/territorio_dez24/ACESSO.txt"}
ok("7c.5b git: os 2 ACESSO.txt lidos pela disponibilidade e todos os .txt de audit_independente estão versionados",
   ACESSOS <= trk and set(aud_txt) <= trk, f"{len(aud_txt)} .txt de auditoria; faltam {sorted((ACESSOS | set(aud_txt)) - trk)[:3]}")
ok("7c.5b Submissao/: Fig1–4 com os mesmos pixels e dpi da v9; ESM_2–4 com o mesmo texto da v9",
   all(px(A10 / "Submissao" / f"Fig{k}.tif") == px(A9 / "Submissao" / f"Fig{k}.tif") for k in range(1, 5))
   and all(txt_pdf(A10 / "Submissao" / f"ESM_{k}.pdf") == txt_pdf(A9 / "Submissao" / f"ESM_{k}.pdf") for k in (2, 3, 4)))

# ---- 9g. Etapa 7c.6: v10 × v11 (as duas versões arquivadas): commit_pacote (antigo commit) e commit_analise nos números-chave; nada mais muda
CAMPOS10 = {k for i in J10.values() for k in i}
CAMPOS11 = {k for i in J11l for k in i}
iguais7 = [k for k in J10 if k in J11 and J11[k]["valor_bruto"] == J10[k]["valor_bruto"] and J11[k]["valor_formatado"] == J10[k]["valor_formatado"]
           and all(J11[k][c] == J10[k][c] for c in ("descricao", "filtro", "arquivo", "script"))]
ok("7c.6 números-chave: mesmos ids, valores, descrições e origens da v10; 'commit' vira 'commit_pacote' (= HEAD ao gerar; 7c.7: "
   "pai do commit que versionou o JSON); entram 'commit_registro' e 'commit_analise'",
   set(J11) == set(J10) and len(iguais7) == len(J10)
   and CAMPOS11 == (CAMPOS10 - {"commit"}) | {"commit_pacote", "commit_registro", "commit_analise"}
   and all(i["commit_pacote"] == pacote_esperado(V11) for i in J11l), f"v10 {len(J10)}; v11 {len(J11)}; idênticos {len(iguais7)}; campos novos {sorted(CAMPOS11 - CAMPOS10)}")
# recálculo próprio do commit_registro: versão mais antiga de onde o valor atual vem sem mudança; commit que adicionou o JSON dessa versão
_add = lambda n: subprocess.run(["git", "-C", str(B.PROJ), "log", "--diff-filter=A", "--format=%h", "--", f"outputs/manuscrito/numeros_chave_v{n}_20261009.json"],
                                capture_output=True, text=True).stdout.split()[-1]
HV = {n: {i["id"]: i for i in json.load(open(B.MS / f"_arquivo_v{n}" / f"numeros_chave_v{n}_20261009.json"))} for n in range(1, 11)}
ADD = {n: _add(n) for n in range(1, 11)}
def _ca(it):
    c = ""
    for n in range(10, 0, -1):
        x = HV[n].get(it["id"])
        if x is None or x["valor_formatado"] != it["valor_formatado"] or not B._mesmo_valor(x["valor_bruto"], it["valor_bruto"]):
            break
        c = ADD[n]
    return c
dif_cr = [i["id"] for i in J11l if _ca(i) != i["commit_registro"]]
validos = all(subprocess.run(["git", "-C", str(B.PROJ), "cat-file", "-e", f"{c}^{{commit}}"]).returncode == 0 for c in set(ADD.values()))
distr = Counter(i["commit_registro"] for i in J11l)
ok("7c.6 commit_registro = commit que versionou pela 1ª vez o valor atual (recalculado aqui); todos são commits válidos",
   not dif_cr and validos, f"divergentes {dif_cr[:3]}; vazios {sum(1 for i in J11l if not i['commit_registro'])}; "
   + "; ".join(f"{c or '(vazio)'} {n}" for c, n in sorted(distr.items(), key=lambda x: -x[1])))
# recálculo próprio do commit_analise. Derivado no pacote (checagem 1): = commit_registro. Lido direto da tabela: (a) git rev-list --since
# na data de modificação da tabela (o mais antigo) e (b) último commit do script até o commit_registro, exigindo (a) == (b)
def _calc(it):
    if it["id"] in DERIV:
        return _ca(it)
    mt = int((B.PROJ / it["arquivo"]).stat().st_mtime)
    a = subprocess.run(["git", "-C", str(B.PROJ), "rev-list", "--reverse", f"--since={mt}", "--abbrev-commit", "HEAD"],
                       capture_output=True, text=True).stdout.split()
    b = subprocess.run(["git", "-C", str(B.PROJ), "log", "-1", "--format=%h", _ca(it), "--", it["script"].split()[0]],
                       capture_output=True, text=True).stdout.strip()
    return a[0] if a and a[0] == b else ""
dif_ca = [i["id"] for i in J11l if _calc(i) != i["commit_analise"]]
vazios = [i["id"] for i in J11l if not i["commit_analise"]]
dist = Counter(i["commit_analise"] for i in J11l)
ok("7c.6 commit_analise = commit do cálculo (recalculado aqui: derivado no pacote → commit_registro; lido da tabela → etapa que a gerou, "
   "com data da tabela e histórico do script concordando); nenhum posterior ao commit_registro",
   not dif_ca and all(subprocess.run(["git", "-C", str(B.PROJ), "merge-base", "--is-ancestor", i["commit_analise"], i["commit_registro"]]).returncode == 0
                      for i in J11l if i["commit_analise"]),
   f"divergentes {dif_ca[:3]}; derivados {len(DERIV)}; vazios {len(vazios)}; "
   + "; ".join(f"{c or '(vazio)'} {n}" for c, n in sorted(dist.items(), key=lambda x: -x[1])))
# congelamento do commit_analise (teste sintético em pasta temporária; os JSON falsos não estão no git, então sem herança o resultado é vazio)
import tempfile
from pathlib import Path
def _cong(versoes):
    with tempfile.TemporaryDirectory() as td:
        ms0, B.MS = B.MS, Path(td)
        try:
            for n, x in versoes.items():
                (B.MS / f"_arquivo_v{n}").mkdir()
                json.dump([x], open(B.MS / f"_arquivo_v{n}" / f"numeros_chave_v{n}_20261009.json", "w"), default=float)
            return B.commits_analise([it0])[it0["id"]][1]
        finally:
            B.MS = ms0
it0 = next(i for i in J if not isinstance(i["valor_bruto"], list))
arq = lambda ca, **k: dict(it0, commit_analise=ca, **k)
CASOS = {"mesmo valor → herda": ({99: arq("abc1234")}, "abc1234"),
         "formatado mudou → não herda": ({99: arq("abc1234", valor_formatado=it0["valor_formatado"] + "x")}, ""),
         "bruto mudou, formatado igual → não herda": ({99: arq("abc1234", valor_bruto=it0["valor_bruto"] * 1.001 + 1)}, ""),
         "v98 e v99 com o mesmo valor → herda o da v99": ({98: arq("aaa9898"), 99: arq("abc1234")}, "abc1234"),
         "v99 mudou, v98 igual → não herda": ({98: arq("aaa9898"), 99: arq("abc1234", valor_formatado=it0["valor_formatado"] + "x")}, ""),
         "v99 com campo vazio, v98 igual → herda o da v98": ({98: arq("aaa9898"), 99: arq("")}, "aaa9898")}
res_cong = {k: _cong(v) for k, (v, _) in CASOS.items()}
ok("7c.6 commit_analise congelado (teste sintético, 6 casos): herda da versão arquivada mais nova com o mesmo valor (formatado e bruto); "
   "não herda se o valor muda; campo vazio não congela", all(res_cong[k] == e for k, (_, e) in CASOS.items()),
   "; ".join(f"{k}: '{res_cong[k]}'" for k in CASOS))
np7, nc7, dn7, dt7, _ = compara(A10, V10, (A11 / "tabelas", A11 / "suplementar"), V11, lambda t, nome="": str(t))
ok("7c.6 v10 × v11 célula a célula: tabelas e suplementares CSV idênticos", not dn7 and not dt7,
   f"{np7} pares; {nc7:,} células; dif números {dn7[:3]}; dif texto {dt7[:3]}")
difx7 = [k for a_, b_ in [(A10 / "tabelas" / f"tabelas_principais_{V10}.xlsx", A11 / "tabelas" / f"tabelas_principais_{V11}.xlsx"),
                          (A10 / "suplementar" / f"ESM_1_tables_S1_S6_{V10}.xlsx", A11 / "suplementar" / f"ESM_1_tables_S1_S6_{V11}.xlsx"),
                          (A10 / "Submissao" / "ESM_1.xlsx", A11 / "Submissao" / "ESM_1.xlsx")]
         for x_, y_ in [(abas(a_), abas(b_))] for k in set(x_) | set(y_) if x_.get(k) != y_.get(k)]
ok("7c.6 xlsx (tabelas principais, ESM_1 e ESM_1 de Submissao/): títulos e rodapés idênticos aos da v10", not difx7, difx7[:3] or "ok")
d10c = " ".join((A10 / f"data_code_availability_{V10}.md").read_text().split())
d11 = " ".join((A11 / f"data_code_availability_{V11}.md").read_text().split())
volta7 = (d11.replace(V11, V10).replace("Etapa 7c.6: auditoria independente 7c.5/7c.5b, RECORD e rastreabilidade",
                                       "Etapa 7c.5b: pontas soltas (referências, auditorias, denominador do índice)")
          .replace('"Etapa 7c.6"', '"Etapa 7c.5b"').replace("Etapa 7c.6)", "Etapa 7c.5b)"))
ok("7c.6 data_code_availability: igual à v10, fora versão e commit de referência", volta7 == d10c,
   "ok" if volta7 == d10c else [i for i, (a, b) in enumerate(zip(volta7, d10c)) if a != b][:1])
rec = B.PROJ / "docs/referencias/RECORD_checklist_acesso20261009.docx"
atr = (B.PROJ / "docs/referencias/ATRIBUICAO.txt").read_text()
trk7 = set(subprocess.run(["git", "-C", str(B.PROJ), "ls-files", "docs/referencias"], capture_output=True, text=True).stdout.splitlines())
ok("7c.6 RECORD: docx e ATRIBUICAO.txt versionados; MD5 do docx = o registrado; atribuição com obra, DOI, licença CC BY e URLs",
   {"docs/referencias/RECORD_checklist_acesso20261009.docx", "docs/referencias/ATRIBUICAO.txt"} <= trk7
   and hashlib.md5(rec.read_bytes()).hexdigest() == "d50bd10feb3c20398ccce6f3c27b7777" and "d50bd10feb3c20398ccce6f3c27b7777" in atr
   and all(x in atr for x in ["doi:10.1371/journal.pmed.1001885", "Creative Commons Attribution (CC BY)", "https://creativecommons.org/licenses/by/4.0/",
                              "https://www.record-statement.org/Files/checklist/RECORD%20Checklist.docx", "Benchimol EI"]))
RES = ["etapa7b_05_resumo.py", "etapa7b1_03_resumo.py", "etapa7b2_02_resumo.py", "etapa7b3_02_resumo.py", "etapa7c1_02_resumo.py",
       "etapa7c2_02_resumo.py", "etapa7c3_01_resumo.py", "etapa7c4_01_resumo.py", "etapa7c5_01_resumo.py", "etapa7c5b_01_resumo.py"]
iguais_res = [f for f in RES if (B.PROJ / "scripts/resumos" / f).read_bytes() == subprocess.run(
    ["git", "-C", str(B.PROJ), "show", f"8314417:scripts/{f}"], capture_output=True).stdout and not (B.PROJ / "scripts" / f).exists()]
ok("7c.6 geradores de RESUMO em scripts/resumos/ com conteúdo idêntico ao do commit 8314417; nenhum ficou em scripts/",
   len(iguais_res) == len(RES) and not list((B.PROJ / "scripts").glob("*_resumo.py")), f"{len(iguais_res)}/{len(RES)}")
ok("7c.6 Submissao/: Fig1–4 com os mesmos pixels e dpi da v10; ESM_2–4 com o mesmo texto da v10",
   all(px(A11 / "Submissao" / f"Fig{k}.tif") == px(A10 / "Submissao" / f"Fig{k}.tif") for k in range(1, 5))
   and all(txt_pdf(A11 / "Submissao" / f"ESM_{k}.pdf") == txt_pdf(A10 / "Submissao" / f"ESM_{k}.pdf") for k in (2, 3, 4)))

# ---- 9h. Etapa 7c.7: v11 × v12 (as duas versões arquivadas; até a Etapa 8, v12 = atual): rodapé da Tabela 4 (Wald na imputação múltipla), n_regsaude_CE/DF, dot_clean no
# 02 e ._* fora de Submissao/ na lixeira (decisões da 7c.6b); nada mais muda
NOVOS12 = {"n_regsaude_CE", "n_regsaude_DF"}
CAMPOS12 = {k for i in J12l for k in i}
iguais8 = [k for k in J11 if k in J12 and all(J12[k][c] == J11[k][c] for c in ("valor_bruto", "valor_formatado", "descricao", "filtro",
                                                                                 "arquivo", "script", "commit_registro", "commit_analise"))]
ok("7c.7 números-chave: os da v11 com valor, descrição, origem, commit_registro e commit_analise idênticos; entram só n_regsaude_CE e "
   "n_regsaude_DF; mesmos campos", set(J12) - set(J11) == NOVOS12 and set(J11) <= set(J12) and len(iguais8) == len(J11)
   and CAMPOS12 == CAMPOS11, f"v11 {len(J11)}; v12 {len(J12)}; idênticos {len(iguais8)}; novos {sorted(set(J12) - set(J11))}")
esp12 = pacote_esperado(V12)
ok("7c.7 commit_pacote = HEAD ao gerar o pacote (antes do commit da etapa, o HEAD atual; depois, o pai do commit que versionou o JSON)",
   all(i["commit_pacote"] == esp12 for i in J12l), f"esperado {esp12}; no JSON {sorted({i['commit_pacote'] for i in J12l})}")
rl_ = pd.read_csv(B.PROJ / "docs/referencias/territorio_dez24/rl_municip_regsaud.csv", dtype=str)
nreg = {u: rl_[rl_.CO_MUNICIP.str[:2] == c].CO_REGSAUD.nunique() for u, c in (("CE", "23"), ("DF", "53"))}
nr_ok = all(J12[f"n_regsaude_{u}"]["valor_bruto"] == nreg[u] and J12[f"n_regsaude_{u}"]["valor_formatado"] == str(nreg[u])
            and J12[f"n_regsaude_{u}"]["arquivo"] == f"outputs/tables/tab_e7c7_01_regsaude_uf_v1_{B.S}.csv"
            and J12[f"n_regsaude_{u}"]["script"] == "scripts/etapa7c7_01_regsaude_uf.py"
            and "municipality-to-health-region map" in J12[f"n_regsaude_{u}"]["descricao"]
            and not J12[f"n_regsaude_{u}"]["commit_registro"] and not J12[f"n_regsaude_{u}"]["commit_analise"] for u in nreg)
ok("7c.7 n_regsaude_CE e n_regsaude_DF = regiões de saúde da UF em rl_municip_regsaud (recontadas aqui); somam as 6 que saem do G "
   "(433 → 427); origem tab_e7c7_01_regsaude_uf; commit_registro e commit_analise vazios até a v12 ser arquivada",
   nr_ok and sum(nreg.values()) == 433 - 427, f"recontado {nreg}; JSON {[J12[f'n_regsaude_{u}']['valor_formatado'] for u in nreg]}")
HV12, ADD12 = {**HV, 11: J11}, {**ADD, 11: _add(11)}
def _ca12(it):
    c = ""
    for n in range(11, 0, -1):
        x = HV12[n].get(it["id"])
        if x is None or x["valor_formatado"] != it["valor_formatado"] or not B._mesmo_valor(x["valor_bruto"], it["valor_bruto"]):
            break
        c = ADD12[n]
    return c
dif_cr12 = [i["id"] for i in J12l if _ca12(i) != i["commit_registro"]]
ok("7c.7 commit_registro recalculado aqui com v1–v11 = o do JSON (os novos ficam vazios)", not dif_cr12,
   f"divergentes {dif_cr12[:3]}; vazios {sorted(i['id'] for i in J12l if not i['commit_registro'])}")
np8, nc8, dn8, dt8, _ = compara(A11, V11, (A12 / "tabelas", A12 / "suplementar"), V12, lambda t, nome="": str(t))
ok("7c.7 v11 × v12 célula a célula: tabelas e suplementares CSV idênticos", not dn8 and not dt8,
   f"{np8} pares; {nc8:,} células; dif números {dn8[:3]}; dif texto {dt8[:3]}")
ANTES_MI, FRASE_MI = "combined with Rubin's rules.", " Joint Wald tests were not computed for the multiple-imputation analysis."
x11, x12 = abas(A11 / "tabelas" / f"tabelas_principais_{V11}.xlsx"), abas(A12 / "tabelas" / f"tabelas_principais_{V12}.xlsx")
mud8 = sorted(k for k in set(x11) | set(x12) if x11.get(k) != x12.get(k))
t4k = [k for k in x11 if k.startswith("tab04_")][0]
ok("7c.7 tabelas principais (xlsx): só o rodapé da Tabela 4 muda, com a frase do Wald da imputação múltipla logo depois de \"Rubin's rules\"",
   mud8 == [t4k] and x11[t4k][1].count(ANTES_MI) == 1 and x12[t4k] == (x11[t4k][0], x11[t4k][1].replace(ANTES_MI, ANTES_MI + FRASE_MI)), mud8)
ok("7c.7 ESM_1 (pacote e Submissao/): títulos e rodapés idênticos aos da v11",
   abas(A12 / "suplementar" / f"ESM_1_tables_S1_S6_{V12}.xlsx") == abas(A11 / "suplementar" / f"ESM_1_tables_S1_S6_{V11}.xlsx")
   and abas(A12 / "Submissao" / "ESM_1.xlsx") == abas(A11 / "Submissao" / "ESM_1.xlsx"))
par_ = lambda f: [p_.text for p_ in _dx.Document(f).paragraphs]
cel_ = lambda f: [c.text for t in _dx.Document(f).tables for r in t.rows for c in r.cells]
dx11, dx12 = A11 / "tabelas" / f"tabelas_principais_{V11}.docx", A12 / "tabelas" / f"tabelas_principais_{V12}.docx"
ok("7c.7 docx: células idênticas às da v11; nos parágrafos, só o rótulo de versão e a mesma frase no rodapé da Tabela 4",
   cel_(dx11) == cel_(dx12) and [t.replace(V11, V12).replace(ANTES_MI, ANTES_MI + FRASE_MI) for t in par_(dx11)] == par_(dx12)
   and sum(t.count(FRASE_MI) for t in par_(dx12)) == 1)
d11b = " ".join((A11 / f"data_code_availability_{V11}.md").read_text().split())
d12 = " ".join((A12 / f"data_code_availability_{V12}.md").read_text().split())
volta8 = (d12.replace(V12, V11).replace("Etapa 7c.7: pacote v12 com as decisões da 7c.6b", "Etapa 7c.6: auditoria independente 7c.5/7c.5b, RECORD e rastreabilidade")
          .replace('"^Etapa 7c.7:"', '"Etapa 7c.6"').replace("Etapa 7c.7)", "Etapa 7c.6)"))
ok("7c.7 data_code_availability: igual à v11, fora versão e commit de referência (o grep agora ancorado: \"^Etapa 7c.7:\")", volta8 == d11b,
   "ok" if volta8 == d11b else [i for i, (a, b) in enumerate(zip(volta8, d11b)) if a != b][:1])
ok("7c.7 legendas das figuras: iguais às da v11, fora o rótulo de versão",
   (A12 / f"legendas_figuras_{V12}.md").read_text().replace(V12, V11) == (A11 / f"legendas_figuras_{V11}.md").read_text())
figs8 = [f for f in sorted((A11 / "figuras").glob(f"*_{V11}.*")) if not f.name.startswith("._")]
ok("7c.7 figuras (png e tif) e Submissao/ (Fig1–4): mesmos pixels e dpi da v11; ESM_2–4 com o mesmo texto da v11",
   len(figs8) == 8 and all(px(A12 / "figuras" / f.name.replace(V11, V12)) == px(f) for f in figs8)
   and all(px(A12 / "Submissao" / f"Fig{k}.tif") == px(A11 / "Submissao" / f"Fig{k}.tif") for k in range(1, 5))
   and all(txt_pdf(A12 / "Submissao" / f"ESM_{k}.pdf") == txt_pdf(A11 / "Submissao" / f"ESM_{k}.pdf") for k in (2, 3, 4)), f"{len(figs8)} figuras")
# 7d: fora outputs/logs (no .gitignore), que o próprio checa escreve durante a checagem; nesse disco exFAT o macOS grava o atributo de
# proveniência do arquivo de log num ._* a cada escrita, então o ._ do log reaparece depois de qualquer dot_clean
lixo8 = sorted(str(x.relative_to(B.PROJ)) for d in ("outputs", "scripts", "audit_independente", "docs", "Submissao") for x in (B.PROJ / d).rglob("._*")
               if not str(x.relative_to(B.PROJ)).startswith("outputs/logs/"))
ok("7c.7 ._*: nenhum em outputs, scripts, audit_independente, docs e Submissao/ (os de fora de data/ foram para a lixeira; o 02 roda "
   "dot_clean -m em suplementar/)", not lixo8 and 'subprocess.run(["dot_clean", "-m", str(B.SUPD)], check=True)' in
   (B.PROJ / "scripts/etapa7b_02_suplementar.py").read_text(), lixo8[:5] or "0")

# ---- 9i. Etapa 8: v12 × v13 (as duas versões arquivadas; até a Etapa 8b, v13 = atual): cobertura da Atenção Básica na S2b (colunas d e e, nascimentos de 2015–2021), números-chave
# da Etapa 8, nota geral "n.a." no rodapé da Tabela 4 e a nova fonte na disponibilidade; nada mais muda
t4_13 = pd.read_csv(A13 / "tabelas" / f"tab04_sensitivity_{V13}.csv").fillna("")
EX8 = {"tercil_aps": "aps", "tercil_ind21": "indice_2015_2021"}
NOVOS13 = ({f"{p_}_{s_}_{d_}" for s_ in EX8.values() for d_ in ("ptb", "pig", "ptb_ind") for p_ in ("IC_Ind_T1", "Wald2_ind")}
           | {"N_aps_2015_2021", "rho_cobertura_x_indice", "rho_cobertura_x_populacao", "kappa_aps_indice", "pct_concordancia_aps_indice"}
           | {f"pct_Ind_{t_}_{s_}" for s_ in EX8.values() for t_ in ("T1", "T3")})
_add12 = subprocess.run(["git", "-C", str(B.PROJ), "log", "--diff-filter=A", "--format=%h", "--", f"outputs/manuscrito/numeros_chave_{V12}.json"],
                        capture_output=True, text=True).stdout.split()[-1]
CAMPOS13 = {k for i in J13l for k in i}
FIXOS13 = ("valor_bruto", "valor_formatado", "descricao", "filtro", "arquivo", "script")
iguais9 = [k for k in J12 if k in J13 and all(J13[k][c] == J12[k][c] for c in FIXOS13)
           and (J13[k]["commit_registro"], J13[k]["commit_analise"]) == ((_add12, _add12) if k in NOVOS12
                                                                           else (J12[k]["commit_registro"], J12[k]["commit_analise"]))]
ok(f"8 números-chave: os da v12 com valor, descrição, origem, commit_registro e commit_analise idênticos, fora n_regsaude_CE/DF, que passam "
   f"a ter os dois = commit da 7c.7 (a v12 foi arquivada); entram só os {len(NOVOS13)} da Etapa 8; mesmos campos",
   set(J13) - set(J12) == NOVOS13 and set(J12) <= set(J13) and len(iguais9) == len(J12) and CAMPOS13 == CAMPOS12,
   f"v12 {len(J12)}; v13 {len(J13)}; idênticos {len(iguais9)}; novos {len(set(J13) - set(J12))}; commit da 7c.7 {_add12}")
esp13 = pacote_esperado(V13)
ok("8 commit_pacote = HEAD ao gerar o pacote (antes do commit da etapa, o HEAD atual; depois, o pai do commit que versionou o JSON)",
   all(i["commit_pacote"] == esp13 for i in J13l), f"esperado {esp13}; no JSON {sorted({i['commit_pacote'] for i in J13l})}")
HV13, ADD13 = {**HV12, 12: J12}, {**ADD12, 12: _add12}
def _ca13(it):
    c = ""
    for n in range(12, 0, -1):
        x = HV13[n].get(it["id"])
        if x is None or x["valor_formatado"] != it["valor_formatado"] or not B._mesmo_valor(x["valor_bruto"], it["valor_bruto"]):
            break
        c = ADD13[n]
    return c
dif_cr13 = [i["id"] for i in J13l if _ca13(i) != i["commit_registro"]]
ok("8 commit_registro recalculado aqui com v1–v12 = o do JSON; os da Etapa 8 com commit_registro e commit_analise vazios até a v13 ser arquivada",
   not dif_cr13 and all(not J13[k]["commit_registro"] and not J13[k]["commit_analise"] for k in NOVOS13),
   f"divergentes {dif_cr13[:3]}; vazios {len([i for i in J13l if not i['commit_registro']])}")
e8i_ = pd.read_csv(B.TB / f"tab_e8_04_interacao_v1_{B.S}.csv").query("raca == 'Indigena' and nivel == 'T1'").set_index(["exposicao", "desfecho"])
e8w_ = pd.read_csv(B.TB / f"tab_e8_04_wald_v1_{B.S}.csv").set_index(["exposicao", "desfecho"])
c8_ = pd.read_csv(B.TB / f"tab_e8_03_cortes_v1_{B.S}.csv")
conf8 = []
for ex_, s_ in EX8.items():
    for d_ in ("ptb", "pig", "ptb_ind"):
        y_, w_ = e8i_.loc[(ex_, d_)], e8w_.loc[(ex_, d_)]
        conf8 += [J13[f"IC_Ind_T1_{s_}_{d_}"]["valor_formatado"] == B.rd_(y_.ICR_pp, y_.ICR_lo, y_.ICR_hi),
                  J13[f"Wald2_ind_{s_}_{d_}"]["valor_formatado"] == B.pval(w_.p_ind_2gl), int(w_.G) == 433]
n8 = {m_: int(g_.n_nasc.sum()) for m_, g_ in c8_.groupby("medida")}
ok("8 números-chave da Etapa 8: IC Indígena×T1 e Wald indígena de 2 gl = tab_e8_04 (2 exposições × 3 desfechos; G = 433); N da PTB total = "
   "nascimentos dos cortes dos tercis (etapa8_03), nas duas medidas; origem nos scripts etapa8_03 e etapa8_04",
   all(conf8) and n8 == {"tercil_aps": J13["N_aps_2015_2021"]["valor_bruto"], "tercil_ind21": J13["N_aps_2015_2021"]["valor_bruto"]}
   and all(J13[k]["script"] in ("scripts/etapa8_03_tercis.py", "scripts/etapa8_04_modelos.py") for k in NOVOS13),
   f"{sum(conf8)}/{len(conf8)}; N {J13['N_aps_2015_2021']['valor_formatado']}; cortes {n8}")
ok("8 tercis da Etapa 8: em cada macrorregião e medida, cada tercil com 30–37% dos nascimentos",
   bool(c8_[["pct_nasc_T1", "pct_nasc_T2", "pct_nasc_T3"]].stack().between(30, 37).all()) and len(c8_) == 10,
   f"mín {c8_[['pct_nasc_T1', 'pct_nasc_T2', 'pct_nasc_T3']].min().min():.2f}; máx {c8_[['pct_nasc_T1', 'pct_nasc_T2', 'pct_nasc_T3']].max().max():.2f}")
COL8 = {"tercil_aps": "(d) Primary health care coverage tertiles, 2015–2021", "tercil_ind21": "(e) Access index tertiles, 2015–2021"}
NOVAS_S2B = [f"{COL8[e_]}: {k_}" for e_ in EX8 for k_ in ("IC Indigenous×T1 per 100 (95% CI)", "Wald p, Indigenous terms (2 df)")]
np9, nc9, dn9, dt9, _ = compara(A12, V12, ((A13 / "tabelas"), (A13 / "suplementar")), V13, lambda t, nome="": str(t), novas_cols=frozenset(NOVAS_S2B))
ok("8 v12 × v13 célula a célula: tabelas e suplementares CSV idênticos, fora as 4 colunas novas da S2b", not dn9 and not dt9,
   f"{np9} pares; {nc9:,} células; dif números {dn9[:3]}; dif texto {dt9[:3]}")
s2b13 = pd.read_csv((A13 / "suplementar") / f"S2b_access_specifications_{V13}.csv", dtype=str).set_index("Outcome")
cel8 = [s2b13.loc[B.OUTC[d_], f"{COL8[e_]}: IC Indigenous×T1 per 100 (95% CI)"] == J13[f"IC_Ind_T1_{s_}_{d_}"]["valor_formatado"]
        and s2b13.loc[B.OUTC[d_], f"{COL8[e_]}: Wald p, Indigenous terms (2 df)"] == J13[f"Wald2_ind_{s_}_{d_}"]["valor_formatado"]
        for e_, s_ in EX8.items() for d_ in ("ptb", "pig", "ptb_ind")]
ok("8 S2b: colunas (d) e (e) = números-chave da Etapa 8, depois das 4 da v12, na ordem (d) IC, (d) Wald, (e) IC, (e) Wald",
   all(cel8) and list(s2b13.columns[4:]) == NOVAS_S2B and len(s2b13.columns) == 8, f"{sum(cel8)}/{len(cel8)} linhas")
f_ = lambda k: J13[k]["valor_formatado"]
DE8 = ("(d) Tertiles, defined within each macroregion as in (a), of primary health care coverage (Family Health Strategy teams and other primary care teams, "
       "parameterized or equivalent by professional working hours; Ministry of Health public report Cobertura da Atenção Básica, 2007–2020) in the "
       "mother's health region of residence in the previous year: population-weighted mean of the official municipal monthly coverage "
       "over the 12 months; T1 = lowest coverage. Births 2015–2021 only, because the official series ends in December 2020 "
       f"({f_('N_aps_2015_2021')} births for preterm birth (total)). (e) Comparator for (d): tertiles of the access index "
       "recomputed in the same births (2015–2021) with the same algorithm. Primary health care coverage measures the supply of "
       "teams relative to the population, not the use of prenatal care: across health region-years it was weakly correlated with the "
       f"access index (Spearman ρ = {f_('rho_cobertura_x_indice')}) and inversely with the population of the health region "
       f"(ρ = {f_('rho_cobertura_x_populacao')}); coverage and access index tertiles agreed for {f_('pct_concordancia_aps_indice')} of "
       f"births (linear-weighted κ = {f_('kappa_aps_indice')}); {f_('pct_Ind_T3_aps')} of Indigenous births were in the highest "
       f"coverage tertile and {f_('pct_Ind_T1_aps')} in the lowest (access index, 2015–2021: {f_('pct_Ind_T1_indice_2015_2021')} in T1 "
       f"and {f_('pct_Ind_T3_indice_2015_2021')} in T3). ")
R8 = [("better access). IC (interaction contrast)", "better access). " + DE8 + "IC (interaction contrast)"),
      ("The Wald test jointly tests the 6 race × tertile interaction terms (Brown, Black, and Indigenous × T1 and T2; 6 df). 95% CIs",
       "In (b), the Wald test jointly tests the 6 race × tertile interaction terms (Brown, Black, and Indigenous × T1 and T2; 6 df); "
       "in (d) and (e), it jointly tests the Indigenous × T1 and Indigenous × T2 terms (2 df), with the same cluster-robust covariance. 95% CIs"),
      ("(b) and (c) belong", "(b) to (e) belong"),
      ("tab_e3_03a_indice_continuo_rs.", "tab_e3_03a_indice_continuo_rs, tab_e8_04_interacao, tab_e8_04_wald, tab_e8_03_spearman, "
                                         "tab_e8_03_concordancia_resumo, tab_e8_03_raca_por_tercil.")]
S2B_ = "S2b_access_specifications"
e12_, e13_ = abas(A12 / "suplementar" / f"ESM_1_tables_S1_S6_{V12}.xlsx"), abas((A13 / "suplementar") / f"ESM_1_tables_S1_S6_{V13}.xlsx")
rod9 = e12_[S2B_][1]
um9 = all(rod9.count(a_) == 1 for a_, _ in R8)
for a_, b_ in R8:
    rod9 = rod9.replace(a_, b_)
TIT13 = "Table S2b. Alternative specifications of access to early prenatal care and of primary health care coverage"
ok("8 S2b (ESM_1 do pacote e de Submissao/): título novo e rodapé = o da v12 com (d) e (e) definidos (números = números-chave), o Wald de "
   "2 gl, '(b) to (e)' e as fontes novas; as outras abas iguais às da v12",
   um9 and e12_[S2B_][0] == "Table S2b. Alternative specifications of access to early prenatal care" and e13_[S2B_] == (TIT13, rod9)
   and {k: v for k, v in e13_.items() if k != S2B_} == {k: v for k, v in e12_.items() if k != S2B_} and abas((A13 / "Submissao") / "ESM_1.xlsx") == e13_,
   "ok" if e13_[S2B_] == (TIT13, rod9) else [i for i, (a, b) in enumerate(zip(e13_[S2B_][1], rod9)) if a != b][:1])
NOTA_NA = ("n.a., not applicable or not estimated. Gestational age in days changes SGA only; the dating-robust analysis and the weight "
           ">P97 reclassification do not apply to SGA; live-birth bounds were computed only for preterm birth (total) and SGA, as a "
           "correction of the PR M2 without a race×tertile model, so IC and Wald tests are not estimated. 'Unchanged' and 'not "
           "reclassified': the scenario does not change the outcome, so the main-analysis estimates apply; for the unclassified-preterm-"
           "birth scenarios this also holds for the Wald tests of total preterm birth. ")
ANTES_NA = "births without a health region. Sources:"
DEPOIS_NA = "births without a health region. " + NOTA_NA + "Sources:"
x12b, x13 = abas(A12 / "tabelas" / f"tabelas_principais_{V12}.xlsx"), abas((A13 / "tabelas") / f"tabelas_principais_{V13}.xlsx")
mud9 = sorted(k for k in set(x12b) | set(x13) if x12b.get(k) != x13.get(k))
t4k9 = [k for k in x12b if k.startswith("tab04_")][0]
ok("8 tabelas principais (xlsx): só o rodapé da Tabela 4 muda, com a nota 'n.a.' logo antes de 'Sources:'",
   mud9 == [t4k9] and x12b[t4k9][1].count(ANTES_NA) == 1 and x13[t4k9] == (x12b[t4k9][0], x12b[t4k9][1].replace(ANTES_NA, DEPOIS_NA)), mud9)
def na_explicada(cen, col, v):
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
na_cel = [(r_.Scenario, c_, r_[c_]) for _, r_ in t4_13.iterrows() for c_ in t4_13.columns if str(r_[c_]).startswith("n.a.")]
na_sem = [(a_[:30], b_) for a_, b_, v_ in na_cel if not na_explicada(a_, b_, v_)]
ok("8 Tabela 4: toda célula 'n.a.' tem explicação no rodapé (nota geral da Etapa 8 ou frase da imputação múltipla)",
   not na_sem and NOTA_NA in x13[t4k9][1] and FRASE_MI in x13[t4k9][1], f"{len(na_cel)} células n.a.; sem explicação {na_sem}")
dx12b, dx13 = A12 / "tabelas" / f"tabelas_principais_{V12}.docx", (A13 / "tabelas") / f"tabelas_principais_{V13}.docx"
ok("8 docx: células idênticas às da v12; nos parágrafos, só o rótulo de versão e a nota 'n.a.' no rodapé da Tabela 4",
   cel_(dx12b) == cel_(dx13) and [t.replace(V12, V13).replace(ANTES_NA, DEPOIS_NA) for t in par_(dx12b)] == par_(dx13)
   and sum(t.count(NOTA_NA) for t in par_(dx13)) == 1)
acc8 = (B.PROJ / "docs/referencias/aps_cobertura_ab/ACESSO.txt").read_text()
tot8 = re.search(r"Total: 27 UFs; ([\d,]+) registros; ([\d,]+) municípios", acc8).groups()
dia8 = sorted(set(re.findall(r"^(\d{4}-\d{2}-\d{2}) \d", acc8, flags=re.M)))
man8 = re.findall(r"MD5 \((cobertura_ab_uf\d{2}_201401_202012\.json)\) = ([0-9a-f]{32})", acc8)
raw8 = B.PROJ / "data" / "raw" / "aps_cobertura_ab"
ok("8 bruto da cobertura: 27 arquivos em data/raw/aps_cobertura_ab com o MD5 do ACESSO.txt; 467,880 registros = 5,570 municípios × 84 competências",
   len(man8) == 27 and all(hashlib.md5((raw8 / n_).read_bytes()).hexdigest() == h_ for n_, h_ in man8)
   and tot8 == ("467,880", "5,570") and 5570 * 84 == 467880 and len(dia8) == 1, f"{len(man8)} arquivos; {tot8}; consulta {dia8}")
d12d = " ".join((A12 / f"data_code_availability_{V12}.md").read_text().split())
d13 = " ".join((A13 / f"data_code_availability_{V13}.md").read_text().split())
FONTE8 = ('- **Primary health care coverage, 2014–2020** (Ministry of Health, public report "Cobertura da Atenção Básica (2007 - 2020)", '
          "https://relatorioaps.saude.gov.br/cobertura/ab), for the sensitivity analysis in Table S2b: municipal monthly coverage queried through "
          "the report's own interface (`https://relatorioaps-prd.saude.gov.br/cobertura/ab`, municipal level, January 2014 to December 2020, one "
          f"query per state) on {dia8[0]}; {tot8[0]} records ({tot8[1]} municipalities); sizes and MD5 of the 27 files in "
          "docs/referencias/aps_cobertura_ab/ACESSO.txt. ")
DECL8 = (" the Ministry of Health primary > health care coverage report (Cobertura da Atenção Básica, 2007–2020), and the 2022 Census",
         " and the 2022 Census")
volta9 = (d13.replace(FONTE8, "").replace(*DECL8).replace(V13, V12)
          .replace("Etapa 8: sensibilidade com a cobertura da Atenção Básica (pacote v13)", "Etapa 7c.7: pacote v12 com as decisões da 7c.6b")
          .replace('"^Etapa 8:"', '"^Etapa 7c.7:"').replace("Etapa 8)", "Etapa 7c.7)"))
ok("8 data_code_availability: a fonte nova (cobertura da Atenção Básica; data, registros e municípios = ACESSO.txt) e a mesma fonte na "
   "declaração; o resto igual à v12, fora versão e commit de referência (\"^Etapa 8:\")",
   d13.count(FONTE8) == 1 and d13.count(DECL8[0]) == 1 and volta9 == d12d,
   "ok" if volta9 == d12d else [i for i, (a, b) in enumerate(zip(volta9, d12d)) if a != b][:1])
ok("8 legendas das figuras: iguais às da v12, fora o rótulo de versão",
   (A13 / f"legendas_figuras_{V13}.md").read_text().replace(V13, V12) == (A12 / f"legendas_figuras_{V12}.md").read_text())
figs9 = [f for f in sorted((A12 / "figuras").glob(f"*_{V12}.*")) if not f.name.startswith("._")]
ok("8 figuras (png e tif) e Submissao/ (Fig1–4): mesmos pixels e dpi da v12; ESM_2–4 com o mesmo texto da v12",
   len(figs9) == 8 and all(px((A13 / "figuras") / f.name.replace(V12, V13)) == px(f) for f in figs9)
   and all(px((A13 / "Submissao") / f"Fig{k}.tif") == px(A12 / "Submissao" / f"Fig{k}.tif") for k in range(1, 5))
   and all(txt_pdf((A13 / "Submissao") / f"ESM_{k}.pdf") == txt_pdf(A12 / "Submissao" / f"ESM_{k}.pdf") for k in (2, 3, 4)), f"{len(figs9)} figuras")

# ---- 9j. Etapa 8b: v13 × v14 (as duas versões arquivadas; até a Etapa 7d, v14 = atual): Wald de 6 gl nas colunas (d) e (e) da S2b e seus 6 números-chave; nada mais muda
NOVOS14 = [f"Wald6_{s_}_{d_}" for s_ in EX8.values() for d_ in ("ptb", "pig", "ptb_ind")]
_add13 = subprocess.run(["git", "-C", str(B.PROJ), "log", "--diff-filter=A", "--format=%h", "--", f"outputs/manuscrito/numeros_chave_{V13}.json"],
                        capture_output=True, text=True).stdout.split()[-1]
CAMPOS14 = {k for i in J14l for k in i}
iguais10 = [k for k in J13 if k in J14 and all(J14[k][c] == J13[k][c] for c in FIXOS13)
            and (J14[k]["commit_registro"], J14[k]["commit_analise"]) == ((_add13, _add13) if k in NOVOS13
                                                                            else (J13[k]["commit_registro"], J13[k]["commit_analise"]))]
ok("8b números-chave: os 249 da v13 (mesma ordem) com valor, descrição, origem e campos de commit idênticos, fora os 21 da Etapa 8, que passam "
   "a ter commit_registro e commit_analise = commit da Etapa 8 (a v13 foi arquivada); entram só os 6 Wald de 6 gl, no fim; mesmos campos",
   [i["id"] for i in J14l][:len(J13l)] == [i["id"] for i in J13l] and [i["id"] for i in J14l][len(J13l):] == NOVOS14
   and len(iguais10) == len(J13) and CAMPOS14 == CAMPOS13, f"v13 {len(J13)}; v14 {len(J14)}; idênticos {len(iguais10)}; commit da Etapa 8 {_add13}")
esp14 = pacote_esperado(V14)
ok("8b commit_pacote = HEAD ao gerar o pacote (antes do commit da etapa, o HEAD atual; depois, o pai do commit que versionou o JSON)",
   all(i["commit_pacote"] == esp14 for i in J14l), f"esperado {esp14}; no JSON {sorted({i['commit_pacote'] for i in J14l})}")
HV14, ADD14 = {**HV13, 13: J13}, {**ADD13, 13: _add13}
def _ca14(it):
    c = ""
    for n in range(13, 0, -1):
        x = HV14[n].get(it["id"])
        if x is None or x["valor_formatado"] != it["valor_formatado"] or not B._mesmo_valor(x["valor_bruto"], it["valor_bruto"]):
            break
        c = ADD14[n]
    return c
dif_cr14 = [i["id"] for i in J14l if _ca14(i) != i["commit_registro"]]
w6_ = pd.read_csv(B.TB / f"tab_e8_04_wald_v1_{B.S}.csv").set_index(["exposicao", "desfecho"])
v6 = [J14[f"Wald6_{s_}_{d_}"]["valor_formatado"] == B.pval(w6_.p_6gl[(e_, d_)]) and J14[f"Wald6_{s_}_{d_}"]["arquivo"].endswith(f"tab_e8_04_wald_v1_{B.S}.csv")
      and J14[f"Wald6_{s_}_{d_}"]["script"] == "scripts/etapa8_04_modelos.py" and not J14[f"Wald6_{s_}_{d_}"]["commit_registro"]
      for e_, s_ in EX8.items() for d_ in ("ptb", "pig", "ptb_ind")]
ok("8b commit_registro recalculado aqui com v1–v13 = o do JSON; os 6 Wald de 6 gl = tab_e8_04_wald (p_6gl), origem etapa8_04, campos de commit vazios",
   not dif_cr14 and all(v6), f"divergentes {dif_cr14[:3]}; Wald 6 gl {sum(v6)}/{len(v6)}")
COL6 = {e_: f"{COL8[e_]}: Wald p, 6 race\u00d7tertile terms (6 df)" for e_ in EX8}
np10, nc10, dn10, dt10, _ = compara(A13, V13, ((A14 / "tabelas"), (A14 / "suplementar")), V14, lambda t, nome="": str(t), novas_cols=frozenset(COL6.values()))
ok("8b v13 × v14 célula a célula: tabelas e suplementares CSV idênticos, fora as 2 colunas novas da S2b", not dn10 and not dt10,
   f"{np10} pares; {nc10:,} células; dif números {dn10[:3]}; dif texto {dt10[:3]}")
s2b14 = pd.read_csv((A14 / "suplementar") / f"S2b_access_specifications_{V14}.csv", dtype=str).set_index("Outcome")
s2b13_ = pd.read_csv(A13 / "suplementar" / f"S2b_access_specifications_{V13}.csv", dtype=str).set_index("Outcome")
ordem14 = []
for c_ in s2b13_.columns:
    ordem14.append(c_)
    ordem14 += [COL6[e_] for e_ in EX8 if c_ == f"{COL8[e_]}: Wald p, Indigenous terms (2 df)"]
cel10 = [s2b14.loc[B.OUTC[d_], COL6[e_]] == J14[f"Wald6_{s_}_{d_}"]["valor_formatado"] for e_, s_ in EX8.items() for d_ in ("ptb", "pig", "ptb_ind")]
ok("8b S2b: colunas novas com o Wald de 6 gl de (d) e de (e), cada uma logo depois do Wald indígena de 2 gl, = números-chave",
   list(s2b14.columns) == ordem14 and all(cel10), f"{sum(cel10)}/{len(cel10)} células; {len(s2b14.columns)} colunas")
W2A = ("in (d) and (e), it jointly tests the Indigenous \u00d7 T1 and Indigenous \u00d7 T2 terms (2 df), with the same cluster-robust covariance.",
       "in (d) and (e), it jointly tests the Indigenous \u00d7 T1 and Indigenous \u00d7 T2 terms (2 df) and, separately, the 6 race \u00d7 "
       "tertile terms of its own tertiles (6 df), with the same cluster-robust covariance.")
e13b, e14 = abas(A13 / "suplementar" / f"ESM_1_tables_S1_S6_{V13}.xlsx"), abas((A14 / "suplementar") / f"ESM_1_tables_S1_S6_{V14}.xlsx")
ok("8b ESM_1 (pacote e Submissao/): na S2b, título igual e rodapé = o da v13 com o Wald de 6 gl em (d) e (e); as outras abas iguais às da v13",
   e13b[S2B_][1].count(W2A[0]) == 1 and e14[S2B_] == (e13b[S2B_][0], e13b[S2B_][1].replace(*W2A))
   and {k: v for k, v in e14.items() if k != S2B_} == {k: v for k, v in e13b.items() if k != S2B_} and abas((A14 / "Submissao") / "ESM_1.xlsx") == e14)
dx13b, dx14 = A13 / "tabelas" / f"tabelas_principais_{V13}.docx", (A14 / "tabelas") / f"tabelas_principais_{V14}.docx"
ok("8b tabelas principais: xlsx com títulos e rodapés iguais aos da v13; docx com células iguais e parágrafos só com o rótulo de versão trocado",
   abas(A13 / "tabelas" / f"tabelas_principais_{V13}.xlsx") == abas((A14 / "tabelas") / f"tabelas_principais_{V14}.xlsx")
   and cel_(dx13b) == cel_(dx14) and [t.replace(V13, V14) for t in par_(dx13b)] == par_(dx14))
d13b = " ".join((A13 / f"data_code_availability_{V13}.md").read_text().split())
d14 = " ".join((A14 / f"data_code_availability_{V14}.md").read_text().split())
volta10 = (d14.replace(V14, V13).replace("Etapa 8b: Wald de 6 gl da cobertura na S2b (pacote v14)", "Etapa 8: sensibilidade com a cobertura da Atenção Básica (pacote v13)")
           .replace('"^Etapa 8b:"', '"^Etapa 8:"').replace("Etapa 8b)", "Etapa 8)"))
ok("8b data_code_availability: igual à v13, fora versão e commit de referência (\"^Etapa 8b:\"); legendas iguais, fora o rótulo de versão",
   volta10 == d13b and d14.count('`git log --grep "^Etapa 8b:"`') == 1 and d14.count('"Etapa 8b: Wald de 6 gl da cobertura na S2b (pacote v14)"') == 1
   and "Etapa 8: sensibilidade" not in d14 and (A14 / f"legendas_figuras_{V14}.md").read_text().replace(V14, V13) == (A13 / f"legendas_figuras_{V13}.md").read_text(),
   "ok" if volta10 == d13b else [i for i, (a, b) in enumerate(zip(volta10, d13b)) if a != b][:1])
figs10 = [f for f in sorted((A13 / "figuras").glob(f"*_{V13}.*")) if not f.name.startswith("._")]
ok("8b figuras (png e tif) e Submissao/ (Fig1–4): mesmos pixels e dpi da v13; ESM_2–4 com o mesmo texto da v13",
   len(figs10) == 8 and all(px((A14 / "figuras") / f.name.replace(V13, V14)) == px(f) for f in figs10)
   and all(px((A14 / "Submissao") / f"Fig{k}.tif") == px(A13 / "Submissao" / f"Fig{k}.tif") for k in range(1, 5))
   and all(txt_pdf((A14 / "Submissao") / f"ESM_{k}.pdf") == txt_pdf(A13 / "Submissao" / f"ESM_{k}.pdf") for k in (2, 3, 4)), f"{len(figs10)} figuras")


# 9j, reforço da rodada 1 do auditor independente da 8b: xlsx célula a célula, S9 e a v13 arquivada byte a byte
def cels_(f):
    wb = openpyxl.load_workbook(f, read_only=True)
    return {ws.title: [list(r) for r in ws.iter_rows(values_only=True)] for ws in wb.worksheets}
c13t, c14t = cels_(A13 / "tabelas" / f"tabelas_principais_{V13}.xlsx"), cels_((A14 / "tabelas") / f"tabelas_principais_{V14}.xlsx")
c13e, c14e = cels_(A13 / "suplementar" / f"ESM_1_tables_S1_S6_{V13}.xlsx"), cels_((A14 / "suplementar") / f"ESM_1_tables_S1_S6_{V14}.xlsx")
cab14 = next(r for r in c14e[S2B_] if COL6[next(iter(EX8))] in r)
i6 = {e_: cab14.index(COL6[e_]) for e_ in EX8}
sem6 = [[v for j, v in enumerate(r) if j not in i6.values()] for r in c14e[S2B_]]
com6 = [[v.replace(*W2A) if isinstance(v, str) else v for v in r] for r in c13e[S2B_]]
lin6 = {r[0]: r for r in c14e[S2B_] if r and r[0] in B.OUTC.values()}
cx6 = [lin6[B.OUTC[d_]][i6[e_]] == J14[f"Wald6_{s_}_{d_}"]["valor_formatado"] for e_, s_ in EX8.items() for d_ in ("ptb", "pig", "ptb_ind")]
ok("8b xlsx célula a célula: tabelas principais e ESM_1 iguais à v13, fora a S2b; na S2b, sem as 2 colunas novas = v13 com o rodapé novo; "
   "colunas novas = números-chave; ESM_1 de Submissao/ = o do pacote",
   c13t == c14t and {k: v for k, v in c13e.items() if k != S2B_} == {k: v for k, v in c14e.items() if k != S2B_}
   and sem6 == com6 and all(cx6) and cels_((A14 / "Submissao") / "ESM_1.xlsx") == c14e, f"{sum(cx6)}/{len(cx6)} células novas")
s9 = [f for f in sorted((A13 / "suplementar").glob(f"S9_*_{V13}.*")) if not f.name.startswith("._")]
ok("8b S9 (png e tif): mesmos pixels e dpi da v13", len(s9) == 2 and all(px((A14 / "suplementar") / f.name.replace(V13, V14)) == px(f) for f in s9), f"{len(s9)} arquivos")
COP13 = {f"MANIFEST_{V13}.md": "outputs/manuscrito/MANIFEST.md", f"data_code_availability_{V13}.md": "outputs/manuscrito/data_code_availability.md",
         f"legendas_figuras_{V13}.md": "outputs/manuscrito/legendas_figuras.md"}
arq13 = [f for f in sorted(A13.rglob("*")) if f.is_file() and not f.name.startswith("._")]
def _orig13(f):
    r = str(f.relative_to(A13))
    return COP13.get(r) or (r if r.startswith("Submissao/") else f"outputs/manuscrito/{r}")
dif13 = [str(f.relative_to(A13)) for f in arq13 if f.read_bytes() != subprocess.run(
    ["git", "-C", str(B.PROJ), "show", f"{_add13}:{_orig13(f)}"], capture_output=True).stdout]
ok("8b _arquivo_v13: os 49 arquivos com os bytes do commit da Etapa 8 (38 da v13, MANIFEST, disponibilidade, legendas e Submissao/)",
   len(arq13) == 49 and not dif13, f"{len(arq13)} arquivos; divergentes {dif13[:3]}")

# ---- 9k. Etapa 7d: v14 (arquivada) × v15 (atual): Submissao/ final (Online Resources renumeradas na ordem de 1ª citação), Tabela 3b → S3b
# (ESM_4.xlsx), TIFF em RGB sem alfa (mesmos pixels), manuscrito montado com as Tabelas 1–4 e as Figs. 1–4, ESM_3 com a URL da cobertura,
# checklist com página e linha. Nenhum número muda.
_add14 = subprocess.run(["git", "-C", str(B.PROJ), "log", "--diff-filter=A", "--format=%h", "--", f"outputs/manuscrito/numeros_chave_{V14}.json"],
                        capture_output=True, text=True).stdout.split()[-1]
_add8 = _add13                                                        # commit da Etapa 8 (cálculo dos Wald de 6 gl, tab_e8_04_wald)
md5 = lambda f: hashlib.md5(f.read_bytes()).hexdigest()
CAMPOS15 = {k for i in J for k in i}
iguais11 = [k for k in J14 if k in Jcur and all(Jcur[k][c] == J14[k][c] for c in FIXOS13)
            and (Jcur[k]["commit_registro"], Jcur[k]["commit_analise"]) == ((_add14, _add8) if k in NOVOS14
                                                                            else (J14[k]["commit_registro"], J14[k]["commit_analise"]))]
ok("7d números-chave: os 255 da v14, na mesma ordem, com valor, descrição, origem e campos de commit idênticos, fora os 6 Wald de 6 gl, que "
   "passam a ter commit_registro = commit da 8b (a v14 foi arquivada) e commit_analise = commit da Etapa 8 (que gerou tab_e8_04_wald); "
   "nenhum id novo; mesmos campos",
   [i["id"] for i in J] == [i["id"] for i in J14l] and len(iguais11) == len(J14l) and CAMPOS15 == CAMPOS14,
   f"v14 {len(J14l)}; v15 {len(J)}; idênticos {len(iguais11)}; commit da 8b {_add14}; da Etapa 8 {_add8}")
esp15 = pacote_esperado(B.V)
ok("7d commit_pacote = HEAD ao gerar o pacote (antes do commit da etapa, o HEAD atual; depois, o pai do commit que versionou o JSON)",
   all(i["commit_pacote"] == esp15 for i in J), f"esperado {esp15}; no JSON {sorted({i['commit_pacote'] for i in J})}")
HV15, ADD15 = {**HV14, 14: J14}, {**ADD14, 14: _add14}
def _ca15(it):
    c = ""
    for n in range(14, 0, -1):
        x = HV15[n].get(it["id"])
        if x is None or x["valor_formatado"] != it["valor_formatado"] or not B._mesmo_valor(x["valor_bruto"], it["valor_bruto"]):
            break
        c = ADD15[n]
    return c
dif_cr15 = [i["id"] for i in J if _ca15(i) != i["commit_registro"]]
ok("7d commit_registro recalculado aqui com v1–v14 = o do JSON", not dif_cr15, f"divergentes {dif_cr15[:3]}")
# CSV: byte a byte (a S3b da v15 = a tab03b da v14)
pares15 = [(A14 / "tabelas" / f"{n}_{V14}.csv", B.TABD / f"{n}_{B.V}.csv") for n in
           ["tab01_characteristics", "tab02_models_m1m3", "tab03_knol_tercile", "tab04_sensitivity"]]
pares15 += [(f, B.SUPD / f.name.replace(V14, B.V)) for f in sorted((A14 / "suplementar").glob(f"*_{V14}.csv")) if not f.name.startswith("._")]
pares15 += [(A14 / "tabelas" / f"tab03b_terciles_region_{V14}.csv", B.SUPD / f"S3b_terciles_region_{B.V}.csv")]
dif15 = [b_.name for a_, b_ in pares15 if a_.read_bytes() != b_.read_bytes()]
csv15 = sorted(x.name for x in list(B.TABD.glob(f"*_{B.V}.csv")) + list(B.SUPD.glob(f"*_{B.V}.csv")))
ok("7d CSV das tabelas e suplementares idênticos byte a byte aos da v14; a S3b = a antiga Tabela 3b; nenhum CSV a mais ou a menos",
   not dif15 and csv15 == sorted(b_.name for _, b_ in pares15), f"{len(pares15)} pares; diferentes {dif15}")
c14t_, c15t_ = cels_(A14 / "tabelas" / f"tabelas_principais_{V14}.xlsx"), cels_(B.TABD / f"tabelas_principais_{B.V}.xlsx")
c14e_, c15e_ = cels_(A14 / "suplementar" / f"ESM_1_tables_S1_S6_{V14}.xlsx"), cels_(B.SUPD / f"ESM_4_tables_S1_S6_{B.V}.xlsx")
T3B = "tab03b_terciles_region"
s3b_ = c15e_.get("S3b_terciles_region", [])
ok("7d xlsx célula a célula: tabelas principais = as da v14 sem a aba da Tabela 3b; ESM_4 = ESM_1 da v14 com a aba S3b depois da S3, igual à "
   "antiga Tabela 3b fora o título (\"Table S3b.\"); ESM_4 de Submissao/ = o do pacote",
   c15t_ == {k: v for k, v in c14t_.items() if k != T3B} and list(c15e_) == [*list(c14e_)[:5], "S3b_terciles_region", *list(c14e_)[5:]]
   and {k: v for k, v in c15e_.items() if k != "S3b_terciles_region"} == c14e_
   and s3b_[1:] == c14t_[T3B][1:] and s3b_[0] == [c14t_[T3B][0][0].replace("Table 3b.", "Table S3b.")] + c14t_[T3B][0][1:]
   and cels_(B.SUB / "ESM_4.xlsx") == c15e_, list(c15e_))
dx14_, dx15_ = A14 / "tabelas" / f"tabelas_principais_{V14}.docx", B.TABD / f"tabelas_principais_{B.V}.docx"
tb14_ = [[c.text for r in t.rows for c in r.cells] for t in _dx.Document(dx14_).tables]
tb15_ = [[c.text for r in t.rows for c in r.cells] for t in _dx.Document(dx15_).tables]
p14_ = [t.replace(V14, B.V) for t in par_(dx14_)]
i3b = next(k for k, t in enumerate(p14_) if t.startswith("Table 3b."))
ok("7d docx das tabelas principais: as tabelas da v14 sem a 3b; os parágrafos da v14 sem o título e o rodapé da 3b, fora o rótulo de versão",
   tb15_ == tb14_[:3] + tb14_[4:] and par_(dx15_) == p14_[:i3b] + p14_[i3b + 3:], f"{len(tb15_)} tabelas")
# figuras: PNG com os mesmos pixels; TIFF em RGB com os mesmos valores RGB da v14 (RGBA com alfa 255), mesmo dpi, LZW
tif15 = [f for f in sorted((A14 / "figuras").glob(f"*_{V14}.tif")) + sorted((A14 / "suplementar").glob(f"S9_*_{V14}.tif")) if not f.name.startswith("._")]
def _rgb_igual(a_, b_):
    x, y = Image.open(a_), Image.open(b_)
    return (x.mode == "RGBA" and x.getchannel("A").getextrema() == (255, 255) and y.mode == "RGB" and x.convert("RGB").tobytes() == y.tobytes()
            and x.info["dpi"] == y.info["dpi"] and y.info.get("compression") == "tiff_lzw")
png15 = [f for f in sorted((A14 / "figuras").glob(f"*_{V14}.png")) + sorted((A14 / "suplementar").glob(f"S9_*_{V14}.png")) if not f.name.startswith("._")]
ok("7d TIFF (Figs. 1–4 e S9): RGB sem alfa, com os mesmos valores RGB, dpi e compressão LZW da v14 (RGBA com alfa = 255 em todo pixel); "
   "PNG com os mesmos pixels; Submissao/Fig1–4.tif = TIFF do pacote byte a byte",
   len(tif15) == 5 and all(_rgb_igual(f, (B.FIGD if "fig0" in f.name else B.SUPD) / f.name.replace(V14, B.V)) for f in tif15)
   and len(png15) == 5 and all(px(f) == px((B.FIGD if "fig0" in f.name else B.SUPD) / f.name.replace(V14, B.V)) for f in png15)
   and all(md5(B.SUB / f"Fig{k}.tif") == md5(sorted(B.FIGD.glob(f"fig0{k}_*_{B.V}.tif"))[0]) for k in range(1, 5)), f"{len(tif15)} TIFF; {len(png15)} PNG")
OR4_5 = ("Online Resource 4 (Fig. S9)", "Online Resource 5 (Fig. S9)")
ok("7d legendas: iguais às da v14, fora o rótulo de versão e a S9, que passa de Online Resource 4 a 5",
   B.MS.joinpath("legendas_figuras.md").read_text() == (A14 / f"legendas_figuras_{V14}.md").read_text().replace(V14, B.V).replace(*OR4_5))
d14_ = " ".join((A14 / f"data_code_availability_{V14}.md").read_text().split())
d15_ = " ".join(B.MS.joinpath("data_code_availability.md").read_text().split())
volta11 = (d15_.replace(B.V, V14).replace("Etapa 7d: montagem da Submissao (pacote v15)", "Etapa 8b: Wald de 6 gl da cobertura na S2b (pacote v14)")
           .replace('"^Etapa 7d:"', '"^Etapa 8b:"').replace("Etapa 7d)", "Etapa 8b)"))
ok("7d data_code_availability: igual à v14, fora versão e commit de referência (\"^Etapa 7d:\")", volta11 == d14_,
   "ok" if volta11 == d14_ else [i for i, (a, b) in enumerate(zip(volta11, d14_)) if a != b][:1])
t7_ = lambda v_, d_: txt_pdf(d_ / f"S7_variables_codes_{v_}.pdf")
t8a, t8b = txt_pdf(A14 / "suplementar" / f"S8_strobe_record_checklist_{V14}.pdf"), txt_pdf(B.SUPD / f"S8_strobe_record_checklist_{B.V}.pdf")
NOTA8 = ("Location column to be completed at manuscript drafting.", "Location column completed from the final manuscript (etapa7d_01_montagem.py; Submissao/ESM_1.pdf).")
ok("7d PDFs do pacote: S7 com o mesmo texto da v14 (fora o rótulo de versão); S8 = v14 com 'Online Resource 1' no lugar de 'Online Resource 3' "
   "e a nota da coluna de localização",
   t7_(B.V, B.SUPD).replace(B.V, V14) == t7_(V14, A14 / "suplementar")
   and " ".join(t8b.split()) == " ".join(t8a.replace("Online Resource 3 (S8)", "Online Resource 1 (S8)").split()).replace(*NOTA8))
# Submissao/
MONT = B.MS / "montagem"
ok("7d Submissao/: ESM_1.pdf = checklist com página e linha (montagem); ESM_2.pdf = S7; ESM_3.pdf = Supplementary Methods (montagem); "
   "ESM_4.xlsx = tabelas S do pacote; Manuscript.docx = montagem; Title_Page e Cover_Letter = manuscrito/ byte a byte",
   md5(B.SUB / "ESM_1.pdf") == md5(MONT / f"ESM_1_strobe_record_located_{B.V}.pdf") and md5(B.SUB / "ESM_2.pdf") == md5(B.SUPD / f"S7_variables_codes_{B.V}.pdf")
   and md5(B.SUB / "ESM_3.pdf") == md5(MONT / f"ESM_3_supplementary_methods_{B.V}.pdf") and md5(B.SUB / "ESM_4.xlsx") == md5(B.SUPD / f"ESM_4_tables_S1_S6_{B.V}.xlsx")
   and md5(B.SUB / "Manuscript.docx") == md5(MONT / f"Manuscript_{B.V}.docx")
   and all(md5(B.SUB / f) == md5(B.PROJ / "manuscrito" / f) for f in ("Title_Page.docx", "Cover_Letter.docx")))
e5_, e4_ = " ".join(txt_pdf(B.SUB / "ESM_5.pdf").split()), " ".join(txt_pdf(A14 / "Submissao" / "ESM_4.pdf").split())
ok("7d ESM_5.pdf (Online Resource 5, Fig. S9) = o ESM_4.pdf da v14 com 'Online Resource 5' no lugar de 'Online Resource 4'",
   e5_ == e4_.replace("Online Resource 4", "Online Resource 5") and "Online Resource 4" not in e5_)
cab_or = {"ESM_1.pdf": "Online Resource 1", "ESM_2.pdf": "Online Resource 2", "ESM_3.pdf": "Online Resource 3", "ESM_5.pdf": "Online Resource 5"}
ok("7d cabeçalho de cada ESM em PDF (primeiras linhas) = a sua Online Resource (ESM_k ↔ OR k)",
   all(o in " ".join(txt_pdf(B.SUB / f).split("\n")[:4]) for f, o in cab_or.items()), {f: txt_pdf(B.SUB / f)[:45] for f in cab_or})
# _arquivo_v14: 49 arquivos com os bytes do commit da 8b
COP14 = {f"MANIFEST_{V14}.md": "outputs/manuscrito/MANIFEST.md", f"data_code_availability_{V14}.md": "outputs/manuscrito/data_code_availability.md",
         f"legendas_figuras_{V14}.md": "outputs/manuscrito/legendas_figuras.md"}
arq14 = [f for f in sorted(A14.rglob("*")) if f.is_file() and not f.name.startswith("._")]
def _orig14(f):
    r = str(f.relative_to(A14))
    return COP14.get(r) or (r if r.startswith("Submissao/") else f"outputs/manuscrito/{r}")
dif14 = [str(f.relative_to(A14)) for f in arq14 if f.read_bytes() != subprocess.run(
    ["git", "-C", str(B.PROJ), "show", f"{_add14}:{_orig14(f)}"], capture_output=True).stdout]
ok("7d _arquivo_v14: os 49 arquivos com os bytes do commit da 8b (38 da v14, MANIFEST, disponibilidade, legendas e Submissao/)",
   len(arq14) == 49 and not dif14, f"{len(arq14)} arquivos; divergentes {dif14[:3]}")
# manuscrito montado (conferência detalhada em scripts/etapa7d_02_confere.py)
mo_ = _dx.Document(MONT / f"Manuscript_{B.V}.docx")
or_ = _dx.Document(B.PROJ / "manuscrito" / "Manuscript.docx")
MARC = "[insert from package v10]"
txt_mo = [p_.text for p_ in mo_.paragraphs]
txt_or = [p_.text.replace(" " + MARC, "").replace(MARC, "") for p_ in or_.paragraphs]
ordem_ok = [t for t in txt_mo if t in set(txt_or)] == txt_or
def _celtxt(c):
    return "".join(r.text for p_ in c.paragraphs for r in p_.runs if not r.font.superscript)
def _cel_unicas(t):
    vistos, out = set(), []
    for r in t.rows:
        for c in r.cells:
            if id(c._tc) not in vistos:
                vistos.add(id(c._tc))
                out.append(_celtxt(c))
    return out
tab_ok = []
for t_, n_ in zip(mo_.tables, ["tab01_characteristics", "tab02_models_m1m3", "tab03_knol_tercile", "tab04_sensitivity"]):
    df_ = pd.read_csv(B.TABD / f"{n_}_{B.V}.csv", dtype=str).fillna("")
    esperado = Counter(v.strip() for v in df_.to_numpy().ravel() if v.strip())
    nh_ = 2 if any(": " in c for c in df_.columns) else 1
    corpo = Counter(_celtxt(c).strip() for r in t_.rows[nh_:] for c in {id(c._tc): c for c in r.cells}.values() if _celtxt(c).strip())
    cab = [_celtxt(c) for c in t_.rows[0].cells] if nh_ == 1 else None
    tab_ok.append(corpo == esperado and (cab == list(df_.columns) if nh_ == 1 else True))
ok("7d Manuscript montado: os parágrafos dos autores na mesma ordem, idênticos fora os 4 marcadores; 4 tabelas com as células = CSV do pacote; "
   "4 figuras; nenhum marcador '[insert from package'",
   ordem_ok and len(mo_.tables) == 4 and all(tab_ok) and len(mo_.inline_shapes) == 4 and not any(MARC in t for t in txt_mo),
   f"tabelas {tab_ok}; figuras {len(mo_.inline_shapes)}")
e3o, e3m = _dx.Document(B.PROJ / "manuscrito" / "ESM_3_Supplementary_Methods.docx"), _dx.Document(MONT / f"ESM_3_supplementary_methods_{B.V}.docx")
URL8 = "https://relatorioaps.saude.gov.br/cobertura/ab"
MURL = "[URL from docs/referencias/aps_cobertura_ab/ACESSO.txt]"
ok("7d ESM_3: único parágrafo alterado = o marcador da URL trocado pela URL do relatório registrada no ACESSO.txt da cobertura",
   [p_.text.replace(MURL, URL8) for p_ in e3o.paragraphs] == [p_.text for p_ in e3m.paragraphs]
   and sum(MURL in p_.text for p_ in e3o.paragraphs) == 1 and URL8 in (B.PROJ / "docs/referencias/aps_cobertura_ab/ACESSO.txt").read_text())
chk = pd.read_csv(MONT / f"ESM_1_strobe_record_located_{B.V}.csv", dtype=str).fillna("")
s8_ = pd.read_csv(B.SUPD / f"S8_strobe_record_checklist_{B.V}.csv", dtype=str).fillna("")
pdfm = pymupdf.open(MONT / f"Manuscript_{B.V}.pdf")
marg_ = 68
nl_ = {(pg.number + 1, int(w[4])) for pg in pdfm for w in pg.get_text("words") if w[2] < marg_ and w[4].isdigit()}
refs_ = [(int(m.group(1)), int(m.group(3)), int(m.group(4)), int(m.group(2) or m.group(1)))
         for x in chk["Page/location in manuscript"] for m in re.finditer(r"pp?\. (\d+)(?:–(\d+))?, lines (\d+)–(\d+)", x)]
ok("7d checklist (OR1): as 25 linhas da S8 com a localização preenchida; cada 'p. X, lines a–b' existe no PDF do Word (linha a na página X, "
   "linha b na página final, a ≤ b)",
   chk.drop(columns="Page/location in manuscript").equals(s8_.drop(columns="Page/location in manuscript")) and (chk["Page/location in manuscript"] != "").all()
   and all((p1, a) in nl_ and (p2, b) in nl_ and a <= b for p1, a, b, p2 in refs_), f"{len(refs_)} intervalos")
lixo15 = sorted(str(x.relative_to(B.PROJ)) for d in ("outputs/manuscrito", "manuscrito", "Submissao") for x in (B.PROJ / d).rglob("*")
                if x.name.startswith(("._", "~$")) or x.name == ".DS_Store")
ok("7d sem ._*, ~$ (trava do Word) ou .DS_Store em outputs/manuscrito, manuscrito/ e Submissao/", not lixo15, lixo15[:5] or "0")


# sem 'ICR' e sem 'Parda' nas saídas em inglês (a coluna com o rótulo oficial em português da S7a é a exceção)
txts = {}
for f in list(B.TABD.glob(f"*_{B.V}.csv")) + list(B.SUPD.glob(f"*_{B.V}.csv")):
    d_ = pd.read_csv(f, dtype=str).fillna("")
    d_ = d_.drop(columns=[c for c in d_.columns if "Portuguese" in c])
    txts[f.name] = " ".join(d_.columns) + " " + " ".join(d_.to_numpy().ravel())
for f in [B.TABD / f"tabelas_principais_{B.V}.xlsx", B.SUPD / f"ESM_4_tables_S1_S6_{B.V}.xlsx"]:
    txts[f.name] = " ".join(" ".join(map(str, v)) for v in abas(f).values())
for f in [B.MS / "legendas_figuras.md", B.MS / "data_code_availability.md"]:
    txts[f.name] = f.read_text()
for f in sorted(B.SUB.glob("ESM_*.pdf")):
    txts[f.name] = "\n".join(p.get_text() for p in pymupdf.open(f))
import docx as _docx
txts["docx"] = "\n".join(p.text for p in _docx.Document(B.TABD / f"tabelas_principais_{B.V}.docx").paragraphs) + " ".join(
    c.text for t in _docx.Document(B.TABD / f"tabelas_principais_{B.V}.docx").tables for r in t.rows for c in r.cells)
ruins = {k: sorted(set(re.findall(r"\bICR\b|\bParda\b|\bAmarela\b|[Tt]hird model|(?<![_A-Za-z])[Tt]erciles?\b", v))) for k, v in txts.items()}
ruins = {k: v for k, v in ruins.items() if v}
ok("7c.1–7c.3 nenhuma ocorrência de 'ICR', 'Parda', 'Amarela', 'third model' ou 'tercile' nas saídas em inglês (CSV, xlsx, docx, PDFs, legendas, disponibilidade)",
   not ruins, ruins or f"{len(txts)} arquivos")

# nota Brown/Black: rodapé de toda tabela com rótulos de raça; todas as legendas
sem_nota = []
for f in [B.TABD / f"tabelas_principais_{B.V}.xlsx", B.SUPD / f"ESM_4_tables_S1_S6_{B.V}.xlsx"]:
    wb = openpyxl.load_workbook(f, read_only=True)
    for ws in wb.worksheets:
        vals = [str(c) for row in ws.iter_rows(values_only=True) for c in row if c is not None]
        if any("Brown" in v for v in vals[1:-1]) and B.NOTE_BROWN not in vals[-1]:
            sem_nota.append(f"{f.name}/{ws.title}")
leg = B.MS.joinpath("legendas_figuras.md").read_text().split("\n\n")
nleg = [l for l in leg if l.startswith("**")]
ok("7c.1 nota 'Brown (parda) and Black (preta)…' no rodapé de toda tabela com rótulos de raça e em toda legenda",
   not sem_nota and all(B.NOTE_BROWN in l for l in nleg) and B.NOTE_BROWN in txts["ESM_2.pdf"].replace("\n", " "),
   sem_nota or f"{len(nleg)} legendas")
r3 = abas(B.TABD / f"tabelas_principais_{B.V}.xlsx")
rod3_ = [v[1] for k, v in r3.items() if k.startswith("tab03_")][0]
ok("7c.1 Tabela 3: rodapé com a definição de IC e RERI; colunas 'IC per 100 (95% CI)' e 'IC p'",
   B.NOTE_IC in rod3_ and {"IC per 100 (95% CI)", "IC p"} <= set(t3.columns), B.NOTE_IC[:60])
rod2_ = [v[1] for k, v in r3.items() if k.startswith("tab02_")][0]
ok("7c.1 Tabela 2: M3 rotulado 'extended model'", "M3 (extended model)" in rod2_)
blk2 = t2["Outcome / race"].tolist()
ini = [k for k, v in enumerate(blk2) if not v.startswith("  ")]
ok("7c.1 Tabela 2: ordem White (reference), Brown, Black, Indigenous em cada bloco",
   all([v.strip() for v in blk2[k + 1:k + 5]] == ["White (reference)", "Brown", "Black", "Indigenous"] for k in ini), f"{len(ini)} blocos")
rod4_ = [v[1] for k, v in r3.items() if k.startswith("tab04_")][0]
ok("7c.1 Tabela 4: nota Brown/Black no rodapé (1ª ocorrência de 'Brown' é no rodapé)", rod4_.startswith(B.NOTE_BROWN))
s5d = pd.read_csv(B.SUPD / f"S5d_spontaneous_by_code_wald_{B.V}.csv", dtype=str).fillna("")
ok("7c.1 sensibilidade sem 2024 retirada: Tabela 4, S5d e números-chave", not t4.Scenario.str.contains("2024").any()
   and not s5d.Scenario.str.contains("2024").any() and not any("sem_2024" in k for k in Jcur), list(t4.Scenario)[-6:-3])

# disponibilidade de dados e código
dca = " ".join(txts["data_code_availability.md"].split())      # espaços/quebras normalizados
pedidos = ["MASS 7.3-65", "growthstandards 0.1.7", "arrow 21.0.0.1", "patsy 0.5.6", "pyarrow 16.1.0", "duckdb 1.5.6", "matplotlib 3.9.2",
           "pROC package is not used", "doi:10.1016/j.dib.2025.111920", "ftp://ftp.datasus.gov.br/dissemin/publicos/SINASC/1996_/Dados/DNRES/",
           "2026-10-02", "SIM-DOFET", "SIDRA table 9605", "territorial base", "173fecd", "Etapa 7b.2", "Etapa 7d",
           "March 6, 2026 (2014–2022), March 25, 2026 (2023), and June 27, 2026 (2024)", "October 2, 2026 (identical record counts by state and year",
           "[URL after the repository is created and tagged]"]
ok("7c.1/7c.2 data_code_availability: sem nnet; versões, proveniência (datas das cópias locais), commit e marcador do GitHub",
   "nnet" not in dca and "September 7" not in dca and "guilcoel" not in dca and all(x in dca for x in pedidos),
   [x for x in pedidos if x not in dca] or "ok")

# Online Resource 2: S7a com as variáveis pedidas
s7a = pd.read_csv(B.SUPD / f"S7a_variables_codes_{B.V}.csv")
req = {("SINASC", v) for v in ["RACACORMAE", "SEMAGESTAC", "TPMETESTIM", "DTULTMENST", "STTRABPART", "STCESPARTO", "PARTO", "MESPRENAT",
                               "GRAVIDEZ", "SEXO", "PESO", "ESCMAE", "ESTCIVMAE", "IDADEMAE", "CODMUNRES", "DTNASC"]} | \
      {("SIM", v) for v in ["TIPOBITO", "SEMAGESTAC", "GESTACAO", "PESO"]}
tem = set(zip(s7a.System, s7a.Variable))
md5 = lambda f: __import__("hashlib").md5(f.read_bytes()).hexdigest()
ok("7c.1 Online Resource 2 (ESM_2): S7a com as 20 variáveis pedidas (SINASC 16, SIM 4) e ESM_2.pdf = PDF versionado",
   req <= tem and md5(B.SUB / "ESM_2.pdf") == md5(B.SUPD / f"S7_variables_codes_{B.V}.pdf") and "Table S7a" in txts["ESM_2.pdf"],
   f"{len(tem)} variáveis ({len(tem - req)} além das pedidas: {sorted(v for _, v in tem - req)})")

# docstring da imputação: só o comentário mudou
def corpo(src):
    m = ast.parse(src)
    m.body = m.body[1:] if isinstance(m.body[0], ast.Expr) and isinstance(m.body[0].value, ast.Constant) else m.body
    return ast.dump(m)
velho = subprocess.run(["git", "-C", str(B.PROJ), "show", "1691ab8:scripts/etapa4_06_imputacao_raca.py"], capture_output=True, text=True).stdout
novo = (B.PROJ / "scripts" / "etapa4_06_imputacao_raca.py").read_text()
ok("7c.1 etapa4_06: só o docstring mudou ('Barnard–Rubin' → 'Rubin (1987)'); o código é idêntico ao do commit 1691ab8",
   corpo(velho) == corpo(novo) and "Barnard" not in novo and "Rubin (1987)" in novo)
v23 = subprocess.run(["git", "-C", str(B.PROJ), "show", "dc9328d:scripts/etapa2_03_indice_acesso.py"], capture_output=True, text=True).stdout
n23 = (B.PROJ / "scripts" / "etapa2_03_indice_acesso.py").read_text()
ok("7c.7 etapa2_03: só a docstring mudou (99, nulo e outros códigos fora; nascimentos sem região de saúde fora do índice); o código é "
   "idêntico ao do commit dc9328d", corpo(v23) == corpo(n23) and v23 != n23 and "99, nulo e qualquer outro código ficam fora" in n23
   and "nascimentos sem região de saúde ficam fora do índice" in n23)

# validação do multinomial
vm = pd.read_csv(B.TB / f"tab_e7c1_01_valida_mnl_resumo_v1_{B.S}.csv").iloc[0]
ok("7c.1 fit_mnl × statsmodels MNLogit (1%, seed 42, M2): β, EP do modelo e EP por cluster idênticos",
   vm.max_abs_dif_beta < 1e-8 and vm.max_rel_dif_ep_modelo < 1e-6 and vm.max_rel_dif_ep_cluster < 1e-6,
   f"n {int(vm.n):,}; |Δβ| {vm.max_abs_dif_beta:.1e}; EP modelo {vm.max_rel_dif_ep_modelo:.1e}; EP cluster {vm.max_rel_dif_ep_cluster:.1e}")
aud7 = B.PROJ / "audit_independente" / "etapa7c1" / "comparacao_7c1_v1_20261009.csv"
if aud7.exists():
    cp = pd.read_csv(aud7)
    ok("independente 7c.1: v4 × v5 célula a célula, só rótulos mudaram (todas as verificações do auditor OK)",
       cp.ok.astype(str).str.lower().isin(["true", "1"]).all(), f"{len(cp)} verificações; falhas {list(cp[~cp.ok.astype(str).str.lower().isin(['true', '1'])].verificacao)[:3]}")
aud76 = B.PROJ / "audit_independente" / "etapa7c6" / "comparacao_7c6_v1_20261009.csv"
if aud76.exists():
    cp = pd.read_csv(aud76)
    okc = cp.ok.astype(str).str.lower().isin(["true", "1"])
    ok("independente 7c.6: 7c.5 e 7c.5b (v8 × v10) e 7c.6 (v10 × v11) conferidas por subagente em contexto limpo", okc.all(),
       f"{len(cp)} verificações; falhas {list(cp[~okc].verificacao)[:3]}")
aud74 = B.PROJ / "audit_independente" / "etapa7c4" / "comparacao_7c4_v1_20261009.csv"
if aud74.exists():
    cp = pd.read_csv(aud74)
    okc = cp.ok.astype(str).str.lower().isin(["true", "1"])
    ok("independente 7c.4: S2b conferida nas fontes _rs; v7 × v8 só com a aba nova", okc.all(), f"{len(cp)} verificações; falhas {list(cp[~okc].verificacao)[:3]}")
aud73 = B.PROJ / "audit_independente" / "etapa7c3" / "comparacao_7c3_v1_20261009.csv"
if aud73.exists():
    cp = pd.read_csv(aud73)
    okc = cp.ok.astype(str).str.lower().isin(["true", "1"])
    ok("independente 7c.3: v6 × v7 só com as trocas autorizadas; N do M3 e especificações alternativas conferidos nas fontes",
       okc.all(), f"{len(cp)} verificações; falhas {list(cp[~okc].verificacao)[:3]}")
aud72 = B.PROJ / "audit_independente" / "etapa7c2" / "comparacao_7c2_v1_20261009.csv"
if aud72.exists():
    cp = pd.read_csv(aud72)
    okc = cp.ok.astype(str).str.lower().isin(["true", "1"])
    ok("independente 7c.2: v5 × v6 só com as trocas autorizadas; SEXO do SIM e q do PIG recalculados de forma independente",
       okc.all(), f"{len(cp)} verificações; falhas {list(cp[~okc].verificacao)[:3]}")
pd.DataFrame(res).to_csv(B.MS / f"checa_7b_{B.V}.csv", index=False)
log(f"autoauditoria 7b: {sum(r['ok'] for r in res)}/{len(res)} OK")
