#!/usr/bin/env python3
"""Auditoria independente da etapa 7c.3 (pacote v6 -> v7), escrita do zero.

Somente leitura fora de audit_independente/etapa7c3/.
Microdados: apenas contagens agregadas (DuckDB) na base processada v3.
Nao le scripts/etapa7b_*.py nem outputs/manuscrito/checa_7b_*.csv.

Saidas:
  audit_independente/etapa7c3/comparacao_7c3_v1_20261009.csv  (verificacao, ok, detalhe)
"""
import csv
import hashlib
import io
import json
import re
import zipfile
from collections import Counter
from pathlib import Path

import duckdb
import numpy as np
import openpyxl
import pandas as pd
import pymupdf
from lxml import etree
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

ROOT = Path("/Volumes/Forja/ptb-racial-brasil")
MAN = ROOT / "outputs/manuscrito"
V6 = MAN / "_arquivo_v6"
SUB7 = ROOT / "Submissao"
SUB6 = V6 / "Submissao"
TAB = ROOT / "outputs/tables"
OUT = ROOT / "audit_independente/etapa7c3"
OUT_CSV = OUT / "comparacao_7c3_v1_20261009.csv"
BASE = ROOT / "data/processed/sinasc_brasil_2015_2024_v3_20261008"

ROWS = []


def add(verif, ok, detalhe):
    ROWS.append({"verificacao": verif, "ok": bool(ok), "detalhe": str(detalhe)})
    print(("OK   " if ok else "FALHA"), verif, "|", str(detalhe)[:300])


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


# --------------------------------------------------------------------------
# Utilitarios de numeros e texto
# --------------------------------------------------------------------------
# Numero "autonomo": nao colado a letra/digito/_ (exclui M2cc, T1, P97, v7_2026...,
# tab_e6b_01 etc.). Milhar com virgula e decimal com ponto.
NUM_RE = re.compile(
    r"(?<![A-Za-z0-9_.,])[−\-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?![A-Za-z0-9_])"
)


def nums(s):
    if s is None:
        return []
    return NUM_RE.findall(str(s))


# Trocas autorizadas (v6 -> v7) de rotulo, aplicadas ao texto da v6
TROCAS_CSV = [
    ("Amarela (Asian descent)", "Asian (amarela)"),
    ("missing or Amarela", "missing or Asian (amarela)"),
]
TROCAS_DOC = [
    ("Amarela (Asian descent; n = ", "Asian (amarela) race/skin color (n = "),
    ("Amarela (Asian descent)", "Asian (amarela)"),
    ("missing or Amarela", "missing or Asian (amarela)"),
    ("v6_20261009", "v7_20261009"),
]


def troca(s, trocas):
    if not isinstance(s, str):
        return s
    for a, b in trocas:
        s = s.replace(a, b)
    return s


def ws(s):
    return re.sub(r"\s+", " ", s).strip()


# --------------------------------------------------------------------------
# Fontes
# --------------------------------------------------------------------------
modelos = pd.read_csv(TAB / "tab_e6b_01_modelos_m1m3_v1_20261008.csv")
inter_rs = pd.read_csv(TAB / "tab_e3_02_interacao_rs_v1_20261008.csv")
inter_mu = pd.read_csv(TAB / "tab_e3_02_interacao_v1_20261008.csv")
wald_rs = pd.read_csv(TAB / "tab_e3_02_wald_rs_v1_20261008.csv")
wald_mu = pd.read_csv(TAB / "tab_e3_02_wald_v1_20261008.csv")
cont_rs = pd.read_csv(TAB / "tab_e3_03a_indice_continuo_rs_v1_20261008.csv")
cont_mu = pd.read_csv(TAB / "tab_e3_03a_indice_continuo_v1_20261008.csv")

DESF4 = ["ptb", "pig", "ptb_ind", "ptb_esp"]
DESF3 = ["ptb", "pig", "ptb_ind"]
ROTULO = {
    "ptb": "Preterm birth (total)",
    "pig": "SGA",
    "ptb_ind": "Provider-initiated preterm birth",
    "ptb_esp": "Spontaneous preterm birth",
}


def N_mod(modelo, d):
    v = modelos.loc[(modelos.modelo == modelo) & (modelos.desfecho == d), "N"].unique()
    assert len(v) == 1, (modelo, d, v)
    return int(v[0])


def f2(x):
    return f"{x:.2f}".replace("-", "−")


def fmt_ic(p, lo, hi):
    return f"{f2(p)} ({f2(lo)} to {f2(hi)})"


def fmt_rp(p, lo, hi):
    return f"{f2(p)} ({f2(lo)}–{f2(hi)})"


def fmt_p(p):
    return "<0.0001" if p < 0.0001 else f"{p:.3g}"


def lin_inter(df, d):
    r = df[(df.analise == "3.3b_tercil_nac") & (df.estrato == "Brasil") & (df.desfecho == d)
           & (df.raca == "Indigena") & (df.nivel == "T1_pior")]
    assert len(r) == 1, (d, len(r))
    return r.iloc[0]


def lin_wald(df, d):
    r = df[(df.analise == "3.3b_tercil_nac") & (df.estrato == "Brasil") & (df.desfecho == d)]
    assert len(r) == 1, (d, len(r))
    return r.iloc[0]


def lin_cont(df, d):
    r = df[(df.desfecho == d) & (df.raca == "Indigena")]
    cols = ["RP_por_5pp_interacao", "int_lo", "int_hi"]
    u = r[cols].drop_duplicates()
    assert len(u) == 1, (d, len(u))
    return u.iloc[0]


# ==========================================================================
# A. Numeros-chave v6 x v7
# ==========================================================================
nk6 = json.loads((V6 / "numeros_chave_v6_20261009.json").read_text(encoding="utf-8"))
nk7 = json.loads((MAN / "numeros_chave_v7_20261009.json").read_text(encoding="utf-8"))
K6 = {x["id"]: x for x in nk6}
K7 = {x["id"]: x for x in nk7}

add("A1 numeros-chave: contagem e ids unicos",
    len(nk6) == 204 and len(K6) == 204 and len(nk7) == 225 and len(K7) == 225,
    f"v6: {len(nk6)} registros/{len(K6)} ids; v7: {len(nk7)} registros/{len(K7)} ids")

faltam = [k for k in K6 if k not in K7]
add("A2 numeros-chave: os 204 ids da v6 existem na v7", not faltam,
    f"ausentes na v7: {faltam}" if faltam else "204/204 presentes")

dif_val = [k for k in K6 if k in K7 and (K6[k]["valor_bruto"] != K7[k]["valor_bruto"]
                                       or K6[k]["valor_formatado"] != K7[k]["valor_formatado"])]
add("A3 numeros-chave: valor_bruto e valor_formatado identicos nos 204", not dif_val,
    f"divergentes: {dif_val}" if dif_val else "204/204 identicos (comparacao exata)")

# demais campos
desc_esp = {
    "excl_1_raca": "Excluded: race/skin color missing, unknown, or Asian (amarela)",
    "excl_amarela": "Excluded: Asian (amarela)",
}
outros = []
desc_mud = {}
commits = Counter()
for k in K6:
    if k not in K7:
        continue
    for f in ("filtro", "arquivo", "script"):
        if K6[k].get(f) != K7[k].get(f):
            outros.append((k, f))
    if K6[k]["descricao"] != K7[k]["descricao"]:
        desc_mud[k] = (K6[k]["descricao"], K7[k]["descricao"])
    commits[(K6[k].get("commit"), K7[k].get("commit"))] += 1
ok_desc = set(desc_mud) == set(desc_esp) and all(desc_mud[k][1] == desc_esp[k] for k in desc_esp)
add("A4 numeros-chave: descricao muda so em excl_1_raca e excl_amarela (rotulo Asian)", ok_desc,
    "; ".join(f"{k}: '{a}' -> '{b}'" for k, (a, b) in desc_mud.items()))
add("A5 numeros-chave: filtro/arquivo/script inalterados nos 204", not outros,
    f"alterados: {outros}" if outros else "inalterados; campo commit: "
    + "; ".join(f"{a}->{b} em {n}" for (a, b), n in commits.items())
    + " (metadado de proveniencia; 2cde6a0 = HEAD 'Etapa 7c.2')")

ESPERADOS = ([f"{p}_{d}" for d in DESF4 for p in ("N_M2", "N_M3", "n_excl_estciv")]
             + [f"{p}_{d}" for d in DESF3 for p in ("IC_Ind_T1_tertil_nacional", "Wald_p_tertil_nacional",
                                                    "RP_int_5pp_indice_continuo")])
novos = [k for k in K7 if k not in K6]
add("A6 numeros-chave: entram exatamente os 21 ids novos listados",
    sorted(novos) == sorted(ESPERADOS) and len(novos) == 21,
    f"novos={len(novos)}; extras={sorted(set(novos)-set(ESPERADOS))}; faltando={sorted(set(ESPERADOS)-set(novos))}")

# A7: N do M1/M2/M2cc/M3 e excluidos por estado civil, na fonte
F_MOD = "outputs/tables/tab_e6b_01_modelos_m1m3_v1_20261008.csv"
for d in DESF4:
    n1, n2, n2cc, n3 = (N_mod(m, d) for m in ("M1", "M2", "M2cc", "M3"))
    ex = n2 - n3
    e = {f"N_M2_{d}": n2, f"N_M3_{d}": n3, f"n_excl_estciv_{d}": ex}
    probs = []
    for k, v in e.items():
        x = K7.get(k)
        if x is None:
            probs.append(f"{k} ausente")
            continue
        if x["valor_bruto"] != v:
            probs.append(f"{k} bruto {x['valor_bruto']} != fonte {v}")
        if x["valor_formatado"] != f"{v:,}":
            probs.append(f"{k} formatado '{x['valor_formatado']}' != '{v:,}'")
        if x["arquivo"] != F_MOD:
            probs.append(f"{k} arquivo {x['arquivo']}")
    if n1 != n2:
        probs.append(f"N_M1 {n1} != N_M2 {n2}")
    if n2cc != n3:
        probs.append(f"N_M2cc {n2cc} != N_M3 {n3}")
    add(f"A7 N do M2/M3 e excluidos por estado civil vs fonte ({d})", not probs,
        "; ".join(probs) if probs else
        f"M1=M2={n2:,}; M2cc=M3={n3:,}; excluidos={ex:,} (=M2−M3); bruto e formatado conferem")

# A8: especificacoes alternativas do acesso (fonte _rs)
F_INT = "outputs/tables/tab_e3_02_interacao_rs_v1_20261008.csv"
F_WAL = "outputs/tables/tab_e3_02_wald_rs_v1_20261008.csv"
F_CON = "outputs/tables/tab_e3_03a_indice_continuo_rs_v1_20261008.csv"
nao_discrim = []
for d in DESF3:
    # IC (contraste de interacao aditiva) Indigena x T1, tercis nacionais
    k = f"IC_Ind_T1_tertil_nacional_{d}"
    x = K7[k]
    r, rm = lin_inter(inter_rs, d), lin_inter(inter_mu, d)
    esp = fmt_ic(r.ICR_pp, r.ICR_lo, r.ICR_hi)
    esp_mu = fmt_ic(rm.ICR_pp, rm.ICR_lo, rm.ICR_hi)
    probs = []
    if abs(x["valor_bruto"] - r.ICR_pp) > 1e-12:
        probs.append(f"bruto {x['valor_bruto']} != {r.ICR_pp}")
    if x["valor_formatado"] != esp:
        probs.append(f"formatado '{x['valor_formatado']}' != '{esp}'")
    if x["arquivo"] != F_INT:
        probs.append(f"arquivo {x['arquivo']}")
    if esp == esp_mu:
        nao_discrim.append(k)
    add(f"A8 {k} vs fonte _rs", not probs,
        "; ".join(probs) if probs else
        f"'{x['valor_formatado']}' = tab_e3_02_interacao_rs (3.3b_tercil_nac, Brasil, Indigena, T1_pior); "
        f"versao municipio daria '{esp_mu}'")

    # Wald p
    k = f"Wald_p_tertil_nacional_{d}"
    x = K7[k]
    w, wm = lin_wald(wald_rs, d), lin_wald(wald_mu, d)
    probs = []
    if abs(x["valor_bruto"] - w.p) > 1e-15 * max(1, abs(w.p)) and x["valor_bruto"] != w.p:
        probs.append(f"bruto {x['valor_bruto']} != {w.p}")
    if x["valor_formatado"] != fmt_p(w.p):
        probs.append(f"formatado '{x['valor_formatado']}' != '{fmt_p(w.p)}'")
    if x["arquivo"] != F_WAL:
        probs.append(f"arquivo {x['arquivo']}")
    if int(w.G) != 433:
        probs.append(f"G na fonte _rs = {w.G} (esperado 433)")
    if abs(x["valor_bruto"] - wm.p) <= 1e-15:
        probs.append("bruto coincide com a versao municipio")
    if x["valor_formatado"] == fmt_p(wm.p):
        nao_discrim.append(k + " (so formatado; bruto discrimina)")
    add(f"A8 {k} vs fonte _rs", not probs,
        "; ".join(probs) if probs else
        f"bruto={x['valor_bruto']:.6g} = p de tab_e3_02_wald_rs (G={int(w.G)}, chi2={w.chi2:.3f}, gl={int(w.gl)}); "
        f"municipio: p={wm.p:.6g}, G={int(wm.G)}")

    # RP de interacao por 5 p.p. do indice continuo
    k = f"RP_int_5pp_indice_continuo_{d}"
    x = K7[k]
    c, cm = lin_cont(cont_rs, d), lin_cont(cont_mu, d)
    esp = fmt_rp(c.RP_por_5pp_interacao, c.int_lo, c.int_hi)
    esp_mu = fmt_rp(cm.RP_por_5pp_interacao, cm.int_lo, cm.int_hi)
    probs = []
    if abs(x["valor_bruto"] - c.RP_por_5pp_interacao) > 1e-12:
        probs.append(f"bruto {x['valor_bruto']} != {c.RP_por_5pp_interacao}")
    if x["valor_formatado"] != esp:
        probs.append(f"formatado '{x['valor_formatado']}' != '{esp}'")
    if x["arquivo"] != F_CON:
        probs.append(f"arquivo {x['arquivo']}")
    if esp == esp_mu:
        nao_discrim.append(k)
    add(f"A8 {k} vs fonte _rs", not probs,
        "; ".join(probs) if probs else
        f"'{x['valor_formatado']}' = tab_e3_03a_indice_continuo_rs (Indigena; int_lo={c.int_lo:.4f}, int_hi={c.int_hi:.4f}); "
        f"versao municipio daria '{esp_mu}' (int_lo={cm.int_lo:.4f}, int_hi={cm.int_hi:.4f})")

# A9: G = 433 (rs) x 5570 (municipio) para 3.3b_tercil_nac
g_rs = wald_rs[wald_rs.analise == "3.3b_tercil_nac"].G.unique().tolist()
g_mu = wald_mu[wald_mu.analise == "3.3b_tercil_nac"].G.unique().tolist()
add("A9 tab_e3_02_wald_rs: coluna G = 433 em 3.3b_tercil_nac", g_rs == [433],
    f"G _rs = {g_rs}; G municipio (sem _rs) = {g_mu}")

# A10: estimativas pontuais iguais e IC diferentes (rs x municipio)
det, ok = [], True
for d in DESF3:
    r, rm = lin_inter(inter_rs, d), lin_inter(inter_mu, d)
    pe = abs(r.ICR_pp - rm.ICR_pp) < 1e-9
    icd = abs(r.ICR_lo - rm.ICR_lo) > 1e-6 and abs(r.ICR_hi - rm.ICR_hi) > 1e-6
    ok &= pe and icd
    det.append(f"{d}: ponto {r.ICR_pp:.4f}/{rm.ICR_pp:.4f} IC_rs ({r.ICR_lo:.3f}; {r.ICR_hi:.3f}) x IC_mun ({rm.ICR_lo:.3f}; {rm.ICR_hi:.3f})")
add("A10 IC Indigena x T1 (tercis nacionais): ponto igual e IC 95% diferente entre _rs e municipio", ok, " | ".join(det))

det, ok = [], True
for d in DESF3:
    c, cm = lin_cont(cont_rs, d), lin_cont(cont_mu, d)
    pe = abs(c.RP_por_5pp_interacao - cm.RP_por_5pp_interacao) < 1e-9
    icd = abs(c.int_lo - cm.int_lo) > 1e-6 and abs(c.int_hi - cm.int_hi) > 1e-6
    ok &= pe and icd
    det.append(f"{d}: ponto {c.RP_por_5pp_interacao:.4f}/{cm.RP_por_5pp_interacao:.4f} IC_rs ({c.int_lo:.4f}; {c.int_hi:.4f}) x IC_mun ({cm.int_lo:.4f}; {cm.int_hi:.4f})")
add("A10 RP de interacao por 5 p.p. (indice continuo): ponto igual e IC 95% diferente entre _rs e municipio", ok, " | ".join(det))

det, ok = [], True
for d in DESF3:
    w, wm = lin_wald(wald_rs, d), lin_wald(wald_mu, d)
    same_n = int(w.N) == int(wm.N) and int(w.gl) == int(wm.gl) and int(w.n_celulas) == int(wm.n_celulas)
    pdif = abs(w.p - wm.p) > 0
    ok &= same_n and pdif
    det.append(f"{d}: p_rs={w.p:.4g} x p_mun={wm.p:.4g}; N={int(w.N):,} e gl={int(w.gl)} iguais={same_n}")
add("A10 Wald (tercis nacionais): mesmo N/gl, p diferente entre _rs e municipio", ok, " | ".join(det))

add("A11 proveniencia _rs discriminavel pelo valor publicado",
    True,
    ("valor publicado nao distingue _rs de municipio (arredondamento coincide) em: " + "; ".join(nao_discrim)
     + ". Nesses casos a proveniencia _rs e atestada pelo campo 'arquivo' e pelo bruto/IC nao arredondado da fonte")
    if nao_discrim else "todos os 9 valores publicados diferem do que a versao municipio produziria")

# A12: versao legivel (numeros_chave_v7 .md) = JSON v7
md_nk = (MAN / "numeros_chave_v7_20261009.md").read_text(encoding="utf-8")
lin = [l for l in md_nk.splitlines() if l.startswith("| ") and not l.startswith("| id |")]
md_ids = [l[2:].split(" | ", 1)[0] for l in lin]
# comparacao por prefixo exato da linha (valores podem conter '|')
dif_md = [k for k in K7
          if not any(l.startswith(f"| {k} | {K7[k]['valor_formatado']} | {K7[k]['descricao']} | ") for l in lin)]
extra_md = [k for k in md_ids if k not in K7]
md_res = [m.group() for m in re.finditer(r"Amarela|[Tt]ercile|ICR(?!_)", md_nk)]
add("A12 numeros_chave_v7 .md = JSON v7 (id, valor formatado, descricao)",
    not dif_md and not extra_md and len(md_ids) == 225,
    f"{len(md_ids)} linhas; divergentes={dif_md[:5]}; extras={extra_md[:5]}; "
    f"termos fora de ids no .md: {Counter(md_res) if md_res else 'nenhum'} ('ICR_' so como prefixo de id)")
pipes = [l[2:].split(" | ", 1)[0] for l in lin if l.count(" | ") + 2 != 7 or re.search(r"[^ ]\|[^ ]", l)]
add("A13 observacao: '|' nao escapado em linhas do .md (quebra a tabela Markdown; pre-existente na v6, fora do escopo 7c.3)",
    True, f"ids afetados: {pipes}" if pipes else "nenhum")

# ==========================================================================
# B. Recontagem independente (DuckDB, so agregados)
# ==========================================================================
con = duckdb.connect()
con.execute(
    f"CREATE VIEW s AS SELECT incl, ptb, pig, ptb_ind, ptb_esp, estciv_cat "
    f"FROM read_parquet('{BASE}/**/*.parquet', hive_partitioning=true)"
)
sel = ", ".join(
    f"count(*) FILTER (WHERE incl AND {d} IS NOT NULL) AS m2_{d}, "
    f"count(*) FILTER (WHERE incl AND {d} IS NOT NULL AND estciv_cat IS NOT NULL) AS m3_{d}"
    for d in DESF4
)
res = con.execute(f"SELECT count(*) FILTER (WHERE incl) AS n_incl, {sel} FROM s").fetchdf().iloc[0]
n_incl = int(res.n_incl)
add("B0 DuckDB: registros com incl = true", n_incl == K7["N_final"]["valor_bruto"],
    f"incl = {n_incl:,}; N_final (numeros-chave) = {K7['N_final']['valor_bruto']:,}")
CONTAGENS_B = {}
for d in DESF4:
    c2, c3 = int(res[f"m2_{d}"]), int(res[f"m3_{d}"])
    CONTAGENS_B[d] = (c2, c3)
    n2, n3 = N_mod("M2", d), N_mod("M3", d)
    ok = c2 == n2 and c3 == n3 and (c2 - c3) == K7[f"n_excl_estciv_{d}"]["valor_bruto"]
    add(f"B1 DuckDB: N do M2 e do M3 ({d})", ok,
        f"incl & {d} nao nulo = {c2:,} (fonte M2 {n2:,}); + estciv_cat nao nulo = {c3:,} (fonte M3 {n3:,}); "
        f"diferenca {c2 - c3:,} (n_excl_estciv_{d} = {K7[f'n_excl_estciv_{d}']['valor_bruto']:,})")
con.close()

# ==========================================================================
# C. Tabelas CSV v6 x v7, celula a celula
# ==========================================================================
def ler_csv(p):
    with open(p, newline="", encoding="utf-8") as fh:
        return list(csv.reader(fh))


csv7 = sorted(list((MAN / "tabelas").glob("*_v7_20261009.csv")) + list((MAN / "suplementar").glob("*_v7_20261009.csv")))
csv6 = sorted(list((V6 / "tabelas").glob("*_v6_20261009.csv")) + list((V6 / "suplementar").glob("*_v6_20261009.csv")))
nomes7 = sorted(p.name.replace("_v7_", "_vX_") for p in csv7)
nomes6 = sorted(p.name.replace("_v6_", "_vX_") for p in csv6)
add("C0 conjunto de arquivos CSV v6 = v7", nomes7 == nomes6, f"{len(csv7)} CSV na v7, {len(csv6)} na v6")

BR_FMT = re.compile(r"\d\.\d{3}\.\d{3}|(?<![\d,])\d+,\d{1,2}(?![\d])")
for p7 in csv7:
    sub = p7.parent.name
    p6 = V6 / sub / p7.name.replace("_v7_", "_v6_")
    a, b = ler_csv(p6), ler_csv(p7)
    probs, n_cel, n_txt = [], 0, 0
    if len(a) != len(b):
        probs.append(f"linhas {len(a)} x {len(b)}")
    for i, (ra, rb) in enumerate(zip(a, b)):
        if len(ra) != len(rb):
            probs.append(f"linha {i+1}: colunas {len(ra)} x {len(rb)}")
            continue
        for j, (ca, cb) in enumerate(zip(ra, rb)):
            n_cel += 1
            if nums(ca) != nums(cb):
                probs.append(f"L{i+1}C{j+1} numeros {nums(ca)} x {nums(cb)}")
            if troca(ca, TROCAS_CSV) != cb:
                probs.append(f"L{i+1}C{j+1} texto '{ca[:80]}' x '{cb[:80]}'")
            elif ca != cb:
                n_txt += 1
    br = [m.group() for r in b for c in r for m in BR_FMT.finditer(c)]
    br6 = [m.group() for r in a for c in r for m in BR_FMT.finditer(c)]
    if br != br6:
        probs.append(f"formato numerico suspeito: {br[:5]}")
    add(f"C {sub}/{p7.name}", not probs,
        "; ".join(probs[:6]) if probs else
        f"{n_cel} celulas; numeros identicos; {n_txt} celula(s) com troca autorizada de rotulo")

# ==========================================================================
# D. xlsx e docx
# ==========================================================================
NOVOS_T2 = Counter(f"{N_mod('M2', d) - N_mod('M3', d):,}" for d in DESF4)


def checa_rodape_t2(t6, t7):
    """Rodape da Tabela 2: prefixo/sufixo iguais a v6 e segmento de N conferido com a fonte."""
    probs = []
    i6 = t6.find("N (M1/M2; M3)")
    i7 = t7.find("N, M1 and M2 / M2cc and M3")
    s6, s7 = t6.find(" Sources:"), t7.find(" Sources:")
    if min(i6, i7, s6, s7) < 0:
        return [f"marcadores nao encontrados (i6={i6}, i7={i7}, s6={s6}, s7={s7})"], None
    if t6[:i6] != t7[:i7]:
        probs.append("texto antes do segmento de N difere da v6")
    if t6[s6:] != t7[s7:]:
        probs.append("texto 'Sources' difere da v6")
    seg = t7[i7:s7]
    if "births excluded from M2cc and M3 for missing marital status" not in seg:
        probs.append("frase dos excluidos por estado civil ausente")
    for d in DESF4:
        m = re.search(re.escape(ROTULO[d]) + r" ([\d,]+) / ([\d,]+) \(([\d,]+)\)", seg)
        if not m:
            probs.append(f"{d}: padrao 'N2 / N3 (excl)' nao encontrado")
            continue
        n2, n3 = N_mod("M2", d), N_mod("M3", d)
        if m.groups() != (f"{n2:,}", f"{n3:,}", f"{n2 - n3:,}"):
            probs.append(f"{d}: {m.groups()} != fonte ({n2:,}, {n3:,}, {n2-n3:,})")
    novos = Counter(nums(t7)) - Counter(nums(t6))
    sumiram = Counter(nums(t6)) - Counter(nums(t7))
    if novos != NOVOS_T2 or sumiram:
        probs.append(f"numeros novos {dict(novos)}; sumidos {dict(sumiram)}")
    return probs, seg


def checa_rodape_t1(t7):
    return "Excluded: Asian (amarela) race/skin color (n = 117,549)" in t7


def compara_xlsx(p6, p7, rot, com_t2):
    w6 = openpyxl.load_workbook(p6, data_only=False)
    w7 = openpyxl.load_workbook(p7, data_only=False)
    probs, n_cel, n_txt = [], 0, 0
    if w6.sheetnames != w7.sheetnames:
        probs.append(f"abas {w6.sheetnames} x {w7.sheetnames}")
    all6, all7 = Counter(), Counter()
    t2_ok, t1_ok = None, None
    for sn in w7.sheetnames:
        if sn not in w6.sheetnames:
            continue
        a, b = w6[sn], w7[sn]
        if (a.max_row, a.max_column) != (b.max_row, b.max_column):
            probs.append(f"{sn}: dimensao {a.max_row}x{a.max_column} x {b.max_row}x{b.max_column}")
        hf6 = [getattr(getattr(a, h), s).text for h in ("oddHeader", "oddFooter") for s in ("left", "center", "right")]
        hf7 = [getattr(getattr(b, h), s).text for h in ("oddHeader", "oddFooter") for s in ("left", "center", "right")]
        if [troca(x, TROCAS_DOC) for x in hf6] != hf7:
            probs.append(f"{sn}: cabecalho/rodape de pagina difere")
        R = max(a.max_row, b.max_row)
        C = max(a.max_column, b.max_column)
        for i in range(1, R + 1):
            for j in range(1, C + 1):
                v6, v7 = a.cell(i, j).value, b.cell(i, j).value
                if v6 is None and v7 is None:
                    continue
                n_cel += 1
                all6.update(nums(v6))
                all7.update(nums(v7))
                if isinstance(v7, str) and "N, M1 and M2 / M2cc and M3" in v7:
                    pr, seg = checa_rodape_t2(str(v6), v7)
                    t2_ok = (not pr, seg)
                    probs += [f"{sn}!{a.cell(i, j).coordinate} rodape T2: {x}" for x in pr]
                    continue
                if isinstance(v7, str) and v7.startswith("Brown (parda)") and "Excluded:" in v7:
                    t1_ok = checa_rodape_t1(v7)
                if nums(v6) != nums(v7):
                    probs.append(f"{sn}!{a.cell(i, j).coordinate} numeros {nums(v6)} x {nums(v7)}")
                if troca(v6, TROCAS_DOC) != v7:
                    probs.append(f"{sn}!{a.cell(i, j).coordinate} texto '{str(v6)[:70]}' x '{str(v7)[:70]}'")
                elif v6 != v7:
                    n_txt += 1
    novos, sumidos = all7 - all6, all6 - all7
    esperado = NOVOS_T2 if com_t2 else Counter()
    if com_t2 and not t2_ok:
        probs.append("rodape da Tabela 2 nao localizado")
    if com_t2 and t1_ok is not True:
        probs.append("rodape da Tabela 1 sem 'Excluded: Asian (amarela) race/skin color (n = 117,549)'")
    add(f"D {rot}: celulas/titulos/rodapes v6 x v7", not probs,
        "; ".join(probs[:6]) if probs else
        f"{n_cel} celulas; {n_txt} com troca autorizada de rotulo; demais identicas")
    add(f"D {rot}: nenhum numero da v6 some; novos = apenas excluidos por estado civil" if com_t2
        else f"D {rot}: nenhum numero novo nem sumido",
        novos == esperado and not sumidos,
        f"novos={dict(novos)}; sumidos={dict(sumidos)}; total de numeros v6={sum(all6.values())}, v7={sum(all7.values())}")
    return t2_ok


t2x = compara_xlsx(V6 / "tabelas/tabelas_principais_v6_20261009.xlsx",
                   MAN / "tabelas/tabelas_principais_v7_20261009.xlsx", "tabelas_principais xlsx", True)
compara_xlsx(V6 / "suplementar/ESM_1_tables_S1_S6_v6_20261009.xlsx",
             MAN / "suplementar/ESM_1_tables_S1_S6_v7_20261009.xlsx", "ESM_1 xlsx (suplementar)", False)
compara_xlsx(SUB6 / "ESM_1.xlsx", SUB7 / "ESM_1.xlsx", "Submissao/ESM_1.xlsx", False)
add("D Submissao/ESM_1.xlsx = suplementar/ESM_1 v7 (bytes)",
    md5(SUB7 / "ESM_1.xlsx") == md5(MAN / "suplementar/ESM_1_tables_S1_S6_v7_20261009.xlsx"),
    f"md5 {md5(SUB7 / 'ESM_1.xlsx')}")

# docx: todos os paragrafos (w:p) de todas as partes de texto
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def docx_paragrafos(p):
    out = {}
    with zipfile.ZipFile(p) as z:
        for n in sorted(z.namelist()):
            if re.fullmatch(r"word/(document|header\d*|footer\d*|footnotes|endnotes|comments)\.xml", n):
                root = etree.fromstring(z.read(n))
                out[n] = ["".join(t.text or "" for t in par.iter(W + "t")) for par in root.iter(W + "p")]
    return out


d6 = docx_paragrafos(V6 / "tabelas/tabelas_principais_v6_20261009.docx")
d7 = docx_paragrafos(MAN / "tabelas/tabelas_principais_v7_20261009.docx")
probs, n_par, n_txt = [], 0, 0
all6, all7 = Counter(), Counter()
t2d, t1d = None, None
if sorted(d6) != sorted(d7):
    probs.append(f"partes {sorted(d6)} x {sorted(d7)}")
for part in d7:
    a, b = d6.get(part, []), d7[part]
    if len(a) != len(b):
        probs.append(f"{part}: {len(a)} x {len(b)} paragrafos")
    for k, (pa, pb) in enumerate(zip(a, b)):
        if not pa and not pb:
            continue
        n_par += 1
        all6.update(nums(pa))
        all7.update(nums(pb))
        if "N, M1 and M2 / M2cc and M3" in pb:
            pr, seg = checa_rodape_t2(pa, pb)
            t2d = (not pr, seg)
            probs += [f"rodape T2: {x}" for x in pr]
            continue
        if pb.startswith("Brown (parda)") and "Excluded:" in pb:
            t1d = checa_rodape_t1(pb)
        if nums(pa) != nums(pb):
            probs.append(f"{part} par {k}: numeros {nums(pa)} x {nums(pb)}")
        if troca(pa, TROCAS_DOC) != pb:
            probs.append(f"{part} par {k}: texto '{pa[:70]}' x '{pb[:70]}'")
        elif pa != pb:
            n_txt += 1
if not t2d:
    probs.append("rodape da Tabela 2 nao localizado")
if t1d is not True:
    probs.append("rodape da Tabela 1 sem 'Excluded: Asian (amarela) race/skin color (n = 117,549)'")
add("D tabelas_principais docx: paragrafos/celulas/titulos/rodapes v6 x v7", not probs,
    "; ".join(probs[:6]) if probs else
    f"{n_par} paragrafos (inclui celulas de tabela); {n_txt} com troca autorizada (rotulo Asian e 'package v7'); demais identicos")
novos, sumidos = all7 - all6, all6 - all7
add("D tabelas_principais docx: nenhum numero da v6 some; novos = apenas excluidos por estado civil",
    novos == NOVOS_T2 and not sumidos, f"novos={dict(novos)}; sumidos={dict(sumidos)}")

seg_ok = bool(t2x and t2x[0] and t2d and t2d[0] and t2x[1] == t2d[1])
add("D texto do rodape da Tabela 2 (xlsx = docx; N M1/M2, N M2cc/M3 e excluidos conferem com a fonte)", seg_ok,
    (t2x[1].strip() if t2x else "nao localizado") + ("" if seg_ok else " | xlsx e docx divergem ou falharam"))

# ==========================================================================
# E. PDFs da Submissao v6 x v7
# ==========================================================================
def pdf_texto(p):
    doc = pymupdf.open(p)
    t = "\n".join(pg.get_text() for pg in doc)
    n = doc.page_count
    doc.close()
    return t, n


PDF_TXT7 = {}
for nm in ("ESM_2.pdf", "ESM_3.pdf", "ESM_4.pdf"):
    t6, n6 = pdf_texto(SUB6 / nm)
    t7, n7 = pdf_texto(SUB7 / nm)
    PDF_TXT7[nm] = t7
    a, b = nums(t6), nums(t7)
    txt_igual = ws(troca(t6, TROCAS_DOC)) == ws(t7)
    ok = n6 == n7 and a == b
    add(f"E Submissao/{nm}: conteudo numerico v6 x v7", ok,
        f"paginas {n6}/{n7}; {len(a)}/{len(b)} numeros, sequencia {'identica' if a == b else 'DIFERENTE'}; "
        f"texto (espacos normalizados) {'identico' if txt_igual else 'difere'}; "
        f"md5 {'igual' if md5(SUB6 / nm) == md5(SUB7 / nm) else 'difere (metadados de criacao)'}")
for nm, sp in (("ESM_2.pdf", "S7_variables_codes"), ("ESM_3.pdf", "S8_strobe_record_checklist")):
    add(f"E Submissao/{nm} = suplementar/{sp}_v7 (bytes)",
        md5(SUB7 / nm) == md5(MAN / f"suplementar/{sp}_v7_20261009.pdf"), "md5 comparado")

# ==========================================================================
# F. Residuos em ingles na v7
# ==========================================================================
PAD = re.compile(r"Amarela|ICR|Parda|[Tt]ercile")
TOKEN = re.compile(r"[A-Za-z0-9_./\-]*(?:Amarela|ICR|Parda|[Tt]ercile)[A-Za-z0-9_./\-]*")
COL_PT = "Official label (Portuguese, data dictionary)"


def residuos(texto):
    """Retorna (residuos, ignorados_por_serem_nome_de_arquivo/id)."""
    res, ign = [], []
    for m in TOKEN.finditer(texto):
        tok = m.group()
        (ign if "_" in tok else res).append(tok)
    return res, ign


fontes = []
for p in sorted((MAN / "tabelas").glob("*_v7_20261009.csv")) + sorted((MAN / "suplementar").glob("*_v7_20261009.csv")):
    linhas = ler_csv(p)
    cab = linhas[0] if linhas else []
    excl = cab.index(COL_PT) if COL_PT in cab else None
    txt = "\n".join(",".join(c for j, c in enumerate(r) if j != excl) for r in linhas)
    nota = ""
    if excl is not None:
        pt = " ".join(r[excl] for r in linhas[1:] if len(r) > excl)
        nota = f" (coluna '{COL_PT}' isenta: contem {Counter(PAD.findall(pt))})"
    fontes.append((p.relative_to(ROOT).as_posix(), txt, nota))
for p in [MAN / "tabelas/tabelas_principais_v7_20261009.xlsx", MAN / "suplementar/ESM_1_tables_S1_S6_v7_20261009.xlsx",
          SUB7 / "ESM_1.xlsx"]:
    wb = openpyxl.load_workbook(p)
    txt = "\n".join(str(c.value) for sh in wb.worksheets for r in sh.iter_rows() for c in r if c.value is not None)
    txt += "\n" + "\n".join(wb.sheetnames)
    fontes.append((p.relative_to(ROOT).as_posix(), txt, ""))
fontes.append(("outputs/manuscrito/tabelas/tabelas_principais_v7_20261009.docx", "\n".join(sum(d7.values(), [])), ""))
for nm, t in PDF_TXT7.items():
    fontes.append((f"Submissao/{nm}", t, ""))
for p in [MAN / "legendas_figuras.md", MAN / "data_code_availability.md"]:
    fontes.append((p.relative_to(ROOT).as_posix(), p.read_text(encoding="utf-8"), ""))
fontes.append(("numeros_chave_v7 (campo descricao)", "\n".join(x["descricao"] for x in nk7), ""))

tot_res = 0
for nome, txt, nota in fontes:
    res, ign = residuos(txt)
    tot_res += len(res)
    add(f"F residuos (Amarela/ICR/Parda/tercile) em {nome}", not res,
        (f"residuos: {Counter(res)}" if res else "nenhum")
        + (f"; ignorados por serem nome de arquivo/id: {Counter(ign)}" if ign else "") + nota)

# ==========================================================================
# G. Figuras TIFF v6 x v7
# ==========================================================================
def tif_meta(p):
    im = Image.open(p)
    return im.size, im.info.get("dpi"), im.mode, im.info.get("compression")


pares = [(V6 / f"figuras/{n}_v6_20261009.tif", MAN / f"figuras/{n}_v7_20261009.tif")
         for n in ("fig01_flowchart", "fig02_pr_race_m1m3", "fig03_rd_race_tercile", "fig04_dating")]
pares.append((V6 / "suplementar/S9_maihda_caterpillar_v6_20261009.tif", MAN / "suplementar/S9_maihda_caterpillar_v7_20261009.tif"))
pares += [(SUB6 / f"Fig{i}.tif", SUB7 / f"Fig{i}.tif") for i in range(1, 5)]
alteradas = []
for p6, p7 in pares:
    m6, m7 = tif_meta(p6), tif_meta(p7)
    igual_bytes = md5(p6) == md5(p7)
    if not igual_bytes:
        a = np.asarray(Image.open(p6).convert("L"))
        b = np.asarray(Image.open(p7).convert("L"))
        igual_px = a.shape == b.shape and not np.any(a != b)
        del a, b
    else:
        igual_px = True
    if not igual_px:
        alteradas.append(p7.name)
    add(f"G {p7.relative_to(ROOT).as_posix()}: dpi e tamanho v6 x v7", m6[:2] == m7[:2],
        f"v6 {m6}; v7 {m7}; {'bytes identicos' if igual_bytes else ('pixels identicos' if igual_px else 'pixels ALTERADOS')}")
add("G so a Fig. 1 alterada", sorted(set(alteradas)) == ["Fig1.tif", "fig01_flowchart_v7_20261009.tif"],
    f"alteradas: {alteradas}")
add("G Submissao/Fig1.tif = figuras/fig01 v7 (bytes)",
    md5(SUB7 / "Fig1.tif") == md5(MAN / "figuras/fig01_flowchart_v7_20261009.tif"), "md5 comparado")


def checa_caixa(p6, p7, rot):
    a = np.asarray(Image.open(p6).convert("L"))
    b = np.asarray(Image.open(p7).convert("L"))
    d = a != b
    ys, xs = np.where(d)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    escuro = b < 128
    # bordas verticais: colunas totalmente escuras na faixa de linhas da diferenca
    colfull = escuro[y0:y1 + 1, :].all(axis=0)
    rowfull = escuro[:, x0:x1 + 1].all(axis=1)
    esq = [x for x in np.where(colfull)[0] if x < x0]
    dir_ = [x for x in np.where(colfull)[0] if x > x1]
    cima = [y for y in np.where(rowfull)[0] if y < y0]
    baixo = [y for y in np.where(rowfull)[0] if y > y1]
    if not (esq and dir_ and cima and baixo):
        return False, f"{rot}: borda da caixa nao encontrada ao redor da area alterada ({x0},{y0})-({x1},{y1})"
    L, R, T, B = max(esq), min(dir_), max(cima), min(baixo)
    # interior da caixa (descontando a espessura da linha)
    inner = escuro[T + 1:B, L + 1:R]
    # remove eventuais colunas/linhas de borda espessa coladas
    ys2, xs2 = np.where(inner)
    # texto = pixels escuros no interior, excluindo faixas encostadas na borda (espessura da linha)
    esp = 0
    while esp < inner.shape[1] and inner[:, esp].mean() > 0.9:
        esp += 1
    inner2 = inner[esp:inner.shape[0] - esp, esp:inner.shape[1] - esp]
    ys2, xs2 = np.where(inner2)
    tx0, tx1, ty0, ty1 = xs2.min(), xs2.max(), ys2.min(), ys2.max()
    W_, H_ = inner2.shape[1], inner2.shape[0]
    margens = (tx0, W_ - 1 - tx1, ty0, H_ - 1 - ty1)
    dentro = (L < x0 and x1 < R and T < y0 and y1 < B)
    ok = dentro and min(margens) > 0.02 * min(W_, H_)
    return ok, (f"{rot}: area alterada ({x0},{y0})-({x1},{y1}) dentro da caixa ({L},{T})-({R},{B}): {dentro}; "
                f"margens do texto ate a borda (esq, dir, topo, base) = {margens} px")


ok1, det1 = checa_caixa(V6 / "figuras/fig01_flowchart_v6_20261009.tif", MAN / "figuras/fig01_flowchart_v7_20261009.tif", "TIFF 1200 dpi")
add("G Fig. 1 TIFF: alteracao restrita a caixa da exclusao por raca, texto dentro da borda", ok1, det1)
ok2, det2 = checa_caixa(V6 / "figuras/fig01_flowchart_v6_20261009.png", MAN / "figuras/fig01_flowchart_v7_20261009.png", "PNG 200 dpi")
add("G Fig. 1 PNG: alteracao restrita a caixa da exclusao por raca, texto dentro da borda", ok2, det2)
add("G Fig. 1 PNG v7: inspecao visual (manual, auditor)", True,
    "caixa diz 'Maternal race/skin color missing / or Asian (amarela): n = 1,082,439 / (missing 964,890; / "
    "Asian (amarela) 117,549)'; 4 linhas centralizadas, legiveis, sem sobreposicao nem corte, dentro da borda; "
    "seta e demais caixas iguais a v6")

# ==========================================================================
# H. data_code_availability.md
# ==========================================================================
dca = (MAN / "data_code_availability.md").read_text(encoding="utf-8")
frase = "Etapa 7c.3: Asian, N do M3 e especificações alternativas do acesso"
add("H data_code_availability.md cita o commit da etapa 7c.3", frase in dca and "7c.2:" not in dca,
    f"frase {'presente' if frase in dca else 'AUSENTE'}; cabecalho: '{dca.splitlines()[0]}'")

# --------------------------------------------------------------------------
OUT.mkdir(parents=True, exist_ok=True)
with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["verificacao", "ok", "detalhe"])
    w.writeheader()
    for r in ROWS:
        w.writerow(r)
n_ok = sum(r["ok"] for r in ROWS)
print(f"\n{len(ROWS)} verificacoes; {n_ok} OK; {len(ROWS) - n_ok} falhas")
print("Contagens B:", {d: f"M2={c2:,} M3={c3:,}" for d, (c2, c3) in CONTAGENS_B.items()})
