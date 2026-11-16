"""
7d.2 Conferência final dos documentos da Submissao (pacote v15). Só lê; grava outputs/manuscrito/montagem/confere_7d_{V}.csv e o log.
  A. Números: todo número (e todo trio estimativa (IC)) do Manuscript montado (Abstract, Methods, Results, Discussion, legendas e títulos
     das tabelas), da Cover_Letter e do ESM_3 é casado com o v15 (255 números-chave; células das Tabelas 1–4 e das S1–S7; texto do ESM_2;
     tab_e6b_01_ptb_raca_metodo, fonte da Fig. 4a). O casamento automático não vê contexto; por isso os parágrafos que mudaram depois da
     conferência manual da 7d-1 (Manuscript da 7d-1 = Manuscript_v4_20261115 do Drive, MD5 a4415273…) têm cada número conferido contra o
     número-chave certo (bloco A2). Os parágrafos que não mudaram já foram conferidos um a um na 7d-1 contra a v14, e os valores da v15
     são idênticos aos da v14 (checa, bloco 9k).
  B. Citações: Figs. 1–4, Tabelas 1–4 e Online Resources 1–5 existem e são citadas pela 1ª vez em ordem; toda "Table S…" citada existe
     no ESM_4; figura inserida logo depois do parágrafo da 1ª citação.
  C. Marcadores: nenhum "[…]" que não seja citação numérica, intervalo de confiança ou forma de referência (Vancouver), fora [repository],
     [tag] e [DOI] (Manuscript) e [Date] (Cover_Letter).
Rodar da raiz: python3 scripts/etapa7d_02_confere.py
"""
import csv
import json
import re

import docx
import openpyxl
import pandas as pd
import pymupdf

import etapa7b_lib as B
import etapa0_lib as L

log = L.Logger("7d_02_confere", etapa="etapa7d")
V = B.V
MONT = B.MS / "montagem"
R = []


def ok(vid, desc, cond, det=""):
    R.append(dict(verificacao=f"{vid} {desc}", ok=bool(cond), detalhe=str(det)))
    log(f"{'OK ' if cond else 'FALHA'} {vid} {desc}: {str(det)[:300]}")


nz = lambda s: s.replace("−", "-").replace(",", "")
J = json.load(open(B.MS / f"numeros_chave_{V}.json"))
K = {i["id"]: i for i in J}

# ---------------- corpus do v15
TOK, TRI = {}, {}
RX_TRI = re.compile(r"(−?-?\d[\d,]*\.?\d*)\s*[\(\[]\s*(?:95% CI\s*)?(−?-?\d[\d,]*\.?\d*)\s*(?:–|to|-)\s*(−?-?\d[\d,]*\.?\d*)\s*[\)\];]")


def add(t, onde):
    t = str(t)
    for m in RX_TRI.finditer(t):
        TRI.setdefault(tuple(nz(x) for x in m.groups()), onde)
    for m in re.finditer(r"−?\d[\d,]*(?:\.\d+)?", t):
        TOK.setdefault(nz(m.group()), onde)


for i in J:
    add(i["valor_formatado"], "id:" + i["id"])
for f in sorted(B.TABD.glob(f"*_{V}.csv")) + sorted(B.SUPD.glob(f"*_{V}.csv")):
    if "INTERNAL" in f.name:
        continue
    for k, row in enumerate(csv.reader(open(f, encoding="utf-8"))):
        for c in row:
            add(c, f"{f.name.replace('_' + V + '.csv', '')}:L{k + 1}")
for f in [B.TABD / f"tabelas_principais_{V}.xlsx", B.SUPD / f"ESM_4_tables_S1_S6_{V}.xlsx"]:
    for ws in openpyxl.load_workbook(f, read_only=True).worksheets:
        for k, r in enumerate(ws.iter_rows(values_only=True)):
            for c in r:
                if c is not None:
                    add(c, f"{ws.title}:L{k + 1}")
for k, pg in enumerate(pymupdf.open(B.SUPD / f"S7_variables_codes_{V}.pdf")):
    add(pg.get_text(), f"ESM_2:p{k + 1}")
for r in pd.read_csv(B.TB / f"tab_e6b_01_ptb_raca_metodo_v1_{B.S}.csv").itertuples():
    add(f"{r.pct:.1f}", "tab_e6b_01_ptb_raca_metodo (Fig. 4a)")

# ---------------- A. extração
SECOES = {"Abstract", "Introduction", "Methods", "Results", "Discussion", "References", "Statements and Declarations", "Tables",
          "Figure Legends", "Electronic Supplementary Material"}
FORA = {"References", "Statements and Declarations", "Introduction", "Electronic Supplementary Material"}


def paragrafos(f):
    sec = "?"
    for i, p in enumerate(docx.Document(f).paragraphs):
        t = p.text.strip()
        if t in SECOES:
            sec = t
            continue
        if t:
            yield i, sec, p.text


DOCS = {"Manuscript": MONT / f"Manuscript_{V}.docx", "Cover_Letter": B.PROJ / "manuscrito" / "Cover_Letter.docx",
        "ESM_3": MONT / f"ESM_3_supplementary_methods_{V}.docx"}
linhas = []
for dn, f in DOCS.items():
    for i, sec, t in paragrafos(f):
        if dn == "Manuscript" and sec in FORA:
            continue
        tx = re.sub(r"\[\d+(?:[,–-]\s*\d+)*\]", "", t)          # citações numéricas
        usados = set()
        for m in RX_TRI.finditer(tx):
            usados |= set(range(m.start(), m.end()))
            linhas.append(dict(doc=dn, secao=sec, par=i, tipo="trio", valor=m.group(0).strip(),
                               fonte=TRI.get(tuple(nz(x) for x in m.groups()), ""), trecho=tx[max(0, m.start() - 70):m.end() + 5]))
        for m in re.finditer(r"(?<![\w.])(−?\d[\d,]*\.?\d*)(%?)", tx):
            if m.start() in usados:
                continue
            v = nz(m.group(1)).rstrip(".")
            if re.fullmatch(r"(19|20)\d\d", v) or v in {str(n) for n in range(11)}:
                continue
            linhas.append(dict(doc=dn, secao=sec, par=i, tipo="num", valor=m.group(0), fonte=TOK.get(v, ""),
                               trecho=tx[max(0, m.start() - 60):m.end() + 25]))
sem = [l for l in linhas if not l["fonte"]]
pd.DataFrame(linhas).to_csv(MONT / f"confere_7d_numeros_{V}.csv", index=False)

# não números de resultado (datas, versões de software, ORCID, constantes de método, referência externa), conferidos na 7d-1 ou fora do pacote
NAO_RESULTADO = {
    "25.8": "25,808,740 = n_Total (arredondado em milhões)", "9605": "número da tabela SIDRA", "25,": "data (March 25)", "33": "33 semanas (padrão INTERGROWTH)",
    "92.4%": "completude do MESPRENAT 2014 (tab_e2_03_mesprenat_completude; RESUMO_ETAPA2)", "96.6%": "idem, 2024",
    "849,059": "imputados (RESUMO_ETAPA4)", "93.9%": "25,808,740/27,489,150", "56.8%": "14,664,926/25,808,740", "35.6%": "9,196,287/25,808,740",
    "1.0%": "246,827/25,808,740", "41.5%": "tab02: 41.45", "36.7": "tab02: 36.65", "48.0": "tab02: 48.00", "30.6%": "tab02: 30.56",
    "21.8": "tab02: 21.77", "57.8": "tab02: 57.82", "0.0019": "Wald_p_ptb 0.00189", "0.0023": "Wald2_ind_principal_ptb 0.00227", "145": "S4b: 145 de 390 com q < 0.05",
    "66.7%": "referência externa [20] (cesárea, White)", "0003": "ORCID", "3045": "ORCID", "4057": "ORCID", "3.12": "Python 3.12", "21.0": "versão do arrow (R)",
    "256,769": "validação do multinomial (RESUMO_ETAPA7C1)", "437": "clusters da validação do multinomial (RESUMO_ETAPA7C1)", "25": "25 pontos de quadratura",
    "29,838": "células estrato × região (RESUMO_ETAPA6)", "216,141": "padrões da imputação (ficha_metodos_7c0)", "74.8%": "PTB entre óbitos fetais (RESUMO_ETAPA6)",
    "0.51": "Wald2_ind_aps_pig 0.507", "0.48": "Wald2_ind_aps_ptb_ind 0.481", "0.016": "Wald6_aps_ptb_ind 0.0156", "0.0037": "Wald6_aps_ptb 0.00369",
    "2026 (2014–2022)": "datas das cópias locais", "13,": "data (October 13)", "0.49": "rho_cobertura_x_populacao −0.49",
}
nao_exp = [l for l in sem if l["valor"].rstrip(",") not in NAO_RESULTADO and l["valor"] not in NAO_RESULTADO]
ok("A1", "todo número sem correspondente automático no v15 está na lista de não-resultados explicados (datas, versões, ORCID, derivados "
   "aritméticos e arredondamentos conferidos)", not nao_exp, [(l["doc"], l["valor"], l["trecho"][-60:]) for l in nao_exp][:10])

# A2. parágrafos que mudaram depois da 7d-1: cada número contra o número-chave certo
def arred(texto, bruto):
    x = float(nz(texto).rstrip("%"))
    d = len(nz(texto).rstrip("%").split(".")[1]) if "." in texto else 0
    return abs(round(float(bruto), d) - x) < 1e-9


def trio_igual(texto, fmt):
    return re.findall(r"\d[\d,]*\.?\d*", texto) == re.findall(r"\d[\d,]*\.?\d*", fmt) and texto.count("−") == fmt.count("−")


MS_TXT = [p.text for p in docx.Document(DOCS["Manuscript"]).paragraphs]
E3_TXT = [p.text for p in docx.Document(DOCS["ESM_3"]).paragraphs]
par = lambda txts, pre: next(t for t in txts if t.startswith(pre))
p32 = par(MS_TXT, "In secondary analyses, we repeated")
p47 = par(MS_TXT, "The SGA and provider-initiated findings kept")
p48 = par(MS_TXT, "In the MAIHDA analysis of SGA")
s11 = par(E3_TXT, "Primary care coverage was taken from")
CTX = [
    (p32, "n = 18,624,544", "N_aps_2015_2021", "fmt"),
    (p47, "5.09 [3.56–6.61]", "IC_Ind_T1_indice_2015_2021_pig", "trio"),
    (p47, "−1.22 [−2.25 to −0.18]", "IC_Ind_T1_indice_2015_2021_ptb_ind", "trio"),
    (p47, "Spearman ρ = −0.10", "rho_cobertura_x_indice", "fmt"),
    (p47, "1.35 [−1.94 to 4.65]", "IC_Ind_T1_aps_pig", "trio"),
    (p47, "−0.91 [−2.43 to 0.60]", "IC_Ind_T1_aps_ptb_ind", "trio"),
    (p47, "p=0.51", "Wald2_ind_aps_pig", "arred"),
    (p47, "p=0.48", "Wald2_ind_aps_ptb_ind", "arred"),
    (p47, "provider-initiated (p=0.016)", "Wald6_aps_ptb_ind", "arred"),
    (p47, "total preterm birth (p=0.0037)", "Wald6_aps_ptb", "arred"),
    (p48, "area under the curve 0.56", "MAIHDA_AUC_M2", "arred"),
    (s11, "n = 18,624,544", "N_aps_2015_2021", "fmt"),
    (s11, "Spearman ρ = −0.10", "rho_cobertura_x_indice", "fmt"),
    (s11, "(ρ = −0.49)", "rho_cobertura_x_populacao", "fmt"),
    (s11, "33.2% of births", "pct_concordancia_aps_indice", "fmt"),
    (s11, "weighted κ = 0.05", "kappa_aps_indice", "fmt"),
]
res_ctx = []
for txt, trecho, id_, modo in CTX:
    if trecho not in txt:
        res_ctx.append((trecho, "trecho ausente"))
        continue
    it = K[id_]
    num = re.search(r"−?\d[\d,]*\.?\d*%?", trecho.split("=")[-1] if "=" in trecho else trecho).group(0)
    if modo == "trio":
        okk = trio_igual(trecho, it["valor_formatado"])
    elif modo == "arred":
        okk = arred(num.replace("−", "-"), it["valor_bruto"] if not isinstance(it["valor_bruto"], list) else it["valor_bruto"][0])
    else:
        okk = nz(num).rstrip("%") == nz(it["valor_formatado"]).rstrip("%").split(" ")[0]
    res_ctx.append((trecho, "ok" if okk else f"v15 {it['valor_formatado']}"))
ok("A2", f"{len(CTX)} números dos trechos novos (cobertura da Atenção Básica no Methods ¶32, Results ¶47–48 e ESM_3 S11) = número-chave certo",
   all(r == "ok" for _, r in res_ctx), [x for x in res_ctx if x[1] != "ok"] or f"{len(CTX)}/{len(CTX)}")
acc = (B.PROJ / "docs/referencias/aps_cobertura_ab/ACESSO.txt").read_text()
ok("A3", "ESM_3 S11: data do download (October 13, 2026) = data das 27 consultas no ACESSO.txt; G = 433",
   "downloaded on October 13, 2026" in s11 and set(re.findall(r"^(\d{4}-\d{2}-\d{2}) \d", acc, flags=re.M)) == {"2026-10-13"} and "G = 433" in s11)

# ---------------- B. citações
mdoc = docx.Document(DOCS["Manuscript"])
P = mdoc.paragraphs
i_abs = next(i for i, p in enumerate(P) if p.text.strip() == "Abstract")
i_ref = next(i for i, p in enumerate(P) if p.text.strip() == "References")
i_st = next(i for i, p in enumerate(P) if p.text.strip() == "Statements and Declarations")
i_tab = next(i for i, p in enumerate(P) if p.text.strip() == "Tables")
corpo = [(i, P[i].text) for i in list(range(i_abs, i_ref)) + list(range(i_st, i_tab))]


def primeiras(rx, txts):
    vistos = []
    for _, t in txts:
        for m in re.finditer(rx, t):
            for n in re.findall(r"\d+", m.group(0)):
                if int(n) not in vistos:
                    vistos.append(int(n))
    return vistos


fig_o = primeiras(r"\bFigs?\. \d+(?:(?:,| and|–) \d+)*", corpo)
tab_o = primeiras(r"\bTables? \d+(?:(?:,| and|–) \d+)*", corpo)
or_o = primeiras(r"\bOnline Resources? \d+(?:(?:,| and|–) \d+)*", corpo)
ok("B1", "Figs. 1–4, Tabelas 1–4 e Online Resources 1–5: todas citadas no texto, 1ª citação em ordem crescente, nenhuma inexistente",
   fig_o == [1, 2, 3, 4] and tab_o == [1, 2, 3, 4] and or_o == [1, 2, 3, 4, 5], f"Figs {fig_o}; Tables {tab_o}; ORs {or_o}")
abas4 = openpyxl.load_workbook(B.SUB / "ESM_4.xlsx", read_only=True).sheetnames
ts = sorted(set(re.findall(r"Table (S\d+[a-z]?)", " ".join(t for _, t in corpo) + " ".join(p.text for p in P))))
ok("B2", "toda 'Table S…' citada no Manuscript existe como aba do ESM_4 (Online Resource 4)", all(any(a.startswith(s + "_") for a in abas4) for s in ts), ts)
leg = [p.text for p in P[i_tab:] if re.match(r"Fig\. \d ", p.text)]
tit = [p.text for p in P[i_tab:] if re.match(r"Table \d ", p.text)]
ok("B3", "4 legendas (Fig. 1–4) e 4 títulos de tabela (Table 1–4), em ordem; 4 tabelas e 4 figuras no corpo do docx",
   [l[:6] for l in leg] == [f"Fig. {k}" for k in range(1, 5)] and [t[:7] for t in tit] == [f"Table {k}" for k in range(1, 5)]
   and len(mdoc.tables) == 4 and len(mdoc.inline_shapes) == 4)
# figura logo depois do parágrafo da 1ª citação
body = list(mdoc.element.body.iterchildren())
fig_pos = [k for k, el in enumerate(body) if el.tag.endswith("}p") and el.findall(".//" + "{http://schemas.openxmlformats.org/drawingml/2006/main}blip")]
prev_txt = ["".join(t.text or "" for t in body[k - 1].iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")) for k in fig_pos]
prim = {}
for i, t in corpo:
    for n in primeiras(r"\bFigs?\. \d+(?:(?:,| and|–) \d+)*", [(i, t)]):
        prim.setdefault(n, t)
ok("B4", "cada figura está logo depois do parágrafo da sua 1ª citação, na ordem 1–4", prev_txt == [prim[k] for k in range(1, 5)],
   [x[:50] for x in prev_txt])

# ---------------- C. marcadores
def colchetes(txts):
    out = []
    for t in txts:
        for m in re.finditer(r"\[([^\]]*)\]", t):
            c = m.group(1)
            if re.fullmatch(r"\d+(?:[,–-]\s*\d+)*", c):                    # citação numérica
                continue
            if re.fullmatch(r"−?\d[\d.,]*(?:–| to )−?\d[\d.,]*", c):         # intervalo de confiança entre colchetes
                continue
            if c in ("Internet",) or c.startswith("cited "):                 # forma Vancouver
                continue
            if c == "LMP":                                                   # abreviação dentro de parênteses (legenda da Fig. 4)
                continue
            if re.fullmatch(r"P\(.*\)", c):                                  # fórmula (ESM_3 S6)
                continue
            out.append(c)
    return out


mk = colchetes([p.text for p in P])
cl = colchetes([p.text for p in docx.Document(DOCS["Cover_Letter"]).paragraphs])
e3 = colchetes(E3_TXT)
tp = colchetes([p.text for p in docx.Document(B.SUB / "Title_Page.docx").paragraphs])
ok("C1", "nenhum marcador entre colchetes, fora [repository], [tag] e [DOI] no Manuscript e [Date] na Cover_Letter; nenhum no ESM_3 e na Title_Page",
   sorted(mk) == ["DOI", "repository", "tag"] and cl == ["Date"] and not e3 and not tp, f"Manuscript {mk}; Cover {cl}; ESM_3 {e3}; Title {tp}")
ok("C2", "nenhum '[insert from package' nem '[URL from' em nenhum documento da Submissao",
   not any("[insert from package" in t or "[URL from" in t for t in [p.text for p in P] + E3_TXT))

pd.DataFrame(R).to_csv(MONT / f"confere_7d_{V}.csv", index=False)
log(f"conferência 7d: {sum(r['ok'] for r in R)}/{len(R)} OK; números extraídos {len(linhas)} (sem correspondente automático {len(sem)}, "
    f"todos explicados: {not nao_exp})")
