"""
etapa7b_lib.py — pacote de resultados para o manuscrito (Etapa 7b). Não estima nada: lê saídas existentes, formata
(inglês americano) e registra a origem (arquivo, script, commit) de cada número.
EP principal = clusterizado por região de saúde (Etapas 6/6b). Tabelas com cluster por município não são lidas aqui.
"""
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

import etapa0_lib as L

PROJ = L.PROJ
TB = L.TAB
S = L.STAMP                      # carimbo das saídas de origem (20261008)
V = "v15_20261115"               # versão/data do pacote (v15 = Etapa 7d: montagem da Submissao, OR renumeradas, Tabela 3b → S3b, TIFF RGB; v1–v14 em outputs/manuscrito/_arquivo_v1.._v14)
MS = PROJ / "outputs" / "manuscrito"
TABD, FIGD, SUPD = MS / "tabelas", MS / "figuras", MS / "suplementar"
SUB = PROJ / "Submissao"
for p in (TABD, FIGD, SUPD, SUB):
    p.mkdir(parents=True, exist_ok=True)
COMMIT = subprocess.run(["git", "-C", str(PROJ), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()

RACE = {"Branca": "White", "Parda": "Brown", "Preta": "Black", "Indigena": "Indigenous"}   # 7c.1: Parda → Brown
RACES = ["Branca", "Parda", "Preta", "Indigena"]
OUTC = {"ptb": "Preterm birth (total)", "pig": "SGA", "ptb_ind": "Provider-initiated preterm birth",
        "ptb_esp": "Spontaneous preterm birth"}
ORDER = ["ptb", "pig", "ptb_ind", "ptb_esp"]
TERC = {"T1": "T1 (worst access)", "T2": "T2", "T3": "T3 (best access)"}
REG = {"N": "North", "NE": "Northeast", "SE": "Southeast", "S": "South", "CO": "Center-West"}
MINUS = "−"
# 7c.1: nota obrigatória na 1ª ocorrência de cada tabela com rótulos de raça (inserida por grava_tabela quando falta)
NOTE_BROWN = ("Brown (parda) and Black (preta) follow the Brazilian Institute of Geography and Statistics categories; race/skin "
              "color is analyzed as a marker of exposure to structural racism.")
NOTE_RACE = (NOTE_BROWN + " Race/skin color is the mother's race/skin color recorded on the Live Birth Declaration (in principle "
             "self-reported), not a biological attribute. Excluded: "
             "Asian (amarela) race/skin color (n = 117,549) and missing race/skin color (n = 964,890); multiple imputation of "
             "missing race/skin color is a sensitivity analysis.")
NOTE_IC = ("IC = risk difference (group vs White) within tertile k minus the same difference within T3, per 100 live births; "
           "RERI = relative excess risk due to interaction.")
NOTE_TERC = ("Tertiles of prenatal care access are defined within each macroregion from the percentage of births with "
             "prenatal care initiated in the first trimester, among births with known month of prenatal care initiation, in the "
             "mother's health region of residence in the previous year; T1 = worst access (lowest percentage), T3 = best access.")
NOTE_CLUSTER = ("95% CIs from cluster-robust (sandwich) variance with clustering by health region of residence "
                "(433 health regions; births with unknown municipality form one cluster per state).")
SRC = {  # tabela de origem → script que a gera (comando quando há opção)
    "tab_e1_03_tabela1_long": "scripts/etapa1_03_tabela1.py",
    "tab_e1_04_prevalencias": "scripts/etapa1_04_prevalencias.py",
    "tab06_fluxograma_regiao": "scripts/etapa0_04_fluxograma.py",
    "tab07_fluxograma_motivos": "scripts/etapa0_04_fluxograma.py",
    "tab08_ptb_incluidos_excluidos": "scripts/etapa0_04_fluxograma.py",
    "tab09_n_final_raca": "scripts/etapa0_04_fluxograma.py",
    "tab01_completude_ano": "scripts/etapa0_03_completude.py",
    "tab_e2_01_tpmetestim_ano_regiao": "scripts/etapa2_01b_tpmetestim.py",
    "tab_e3_00a_ig_metodo_raca": "scripts/etapa3_00a_ig_metodo.py",
    "tab_e3_01_n_casos_raca_tercil_regiao": "scripts/etapa3_01_tercis_regiao.py",
    "tab_e3_01_tercis_regiao_cortes": "scripts/etapa3_01_tercis_regiao.py",
    "tab_e3_00b_atenuacao_ic_rs": "scripts/etapa3_00b_bootstrap_atenuacao.py 500 --rs",
    "tab_e4_06_mi_rubin_rs": "scripts/etapa4_06_imputacao_raca.py 10 --rs --m2",
    "tab_e4_06_mi_m2_rubin_rs": "scripts/etapa4_06_imputacao_raca.py 10 --rs --m2",
    "tab_e4b_01_implausivel_brasil": "scripts/etapa4b_01_plausibilidade.py",
    "tab_e4b_04_co_estratos_rs": "scripts/etapa4b_04_co_metodo.py --rs",
    "tab_e4b_04_co_wald_rs": "scripts/etapa4b_04_co_metodo.py --rs",
    "tab_e5_02_modelos": "scripts/etapa5_02_maihda.R",
    "tab_e5_03_predicoes": "scripts/etapa5_02_maihda.R",
    "tab_e6_01a_m2": "scripts/etapa6_01_cluster_rs.py",
    "tab_e6_01a_conjunto": "scripts/etapa6_01_cluster_rs.py",
    "tab_e6_01a_dentro": "scripts/etapa6_01_cluster_rs.py",
    "tab_e6_01a_interacao": "scripts/etapa6_01_cluster_rs.py",
    "tab_e6_01a_wald": "scripts/etapa6_01_cluster_rs.py",
    "tab_e6_01b_interacao": "scripts/etapa6_01_cluster_rs.py",
    "tab_e6_02a_concordancia": "scripts/etapa6_02_tpmetestim.py",
    "tab_e6_02b_tpmetestim_ano": "scripts/etapa6_02_tpmetestim.py",
    "tab_e6_02b_tpmetestim_2010_2014": "scripts/etapa6_02_tpmetestim.py",
    "tab_e6_03a_robson": "scripts/etapa6_03_ptb_indicado.py",
    "tab_e6_03b_rrr": "scripts/etapa6_03_ptb_indicado.py",
    "tab_e6_04_m2": "scripts/etapa6_04_robusta_datacao.py",
    "tab_e6_04_interacao": "scripts/etapa6_04_robusta_datacao.py",
    "tab_e6_04_wald": "scripts/etapa6_04_robusta_datacao.py",
    "tab_e6_05_multiplicidade": "scripts/etapa6_05_multiplicidade.py",
    "tab_e6_06_maihda_area": "scripts/etapa6_06_maihda_area.R",
    "tab_e6_06_u_estrato": "scripts/etapa6_06_maihda_area.R",
    "tab_e6_07b_limites": "scripts/etapa6_07_tempo_nascidos_vivos.py",
    "tab_e6b_01_modelos_m1m3": "scripts/etapa6b_01_modelos_rs.py",
    "tab_e6b_01_m2_cenarios": "scripts/etapa6b_01_modelos_rs.py",
    "tab_e6b_01_ptb_raca_metodo": "scripts/etapa6b_01_modelos_rs.py",
    "tab_e6b_02_auc_area": "scripts/etapa6b_02_auc_area.R",
    "dicionario_variaveis_v3": "scripts/etapa2_01_base_v3.py",
    "tab_e7b1_01_cenarios_interacao": "scripts/etapa7b1_01_analises.py",
    "tab_e7b1_01_cenarios_wald": "scripts/etapa7b1_01_analises.py",
    "tab_e7b1_02_s1_restrito": "scripts/etapa7b1_01_analises.py",
    "tab_e7b1_03_auc_fixa": "scripts/etapa7b1_02_auc_fixa.R",
    "tab_e7b1_04_m2": "scripts/etapa7b1_01_analises.py",
    "tab_e7b1_04_interacao": "scripts/etapa7b1_01_analises.py",
    "tab_e7b1_04_wald": "scripts/etapa7b1_01_analises.py",
    "tab_e7b1_04_naoclass": "scripts/etapa7b1_01_analises.py",
    "tab_e7b1_05_reri_recod": "scripts/etapa7b1_01_analises.py",
    "tab_e7b2_01_dist": "scripts/etapa7b2_01_datacao.py",
    "tab_e7b2_01_dist_tercil": "scripts/etapa7b2_01_datacao.py",
    "tab_e7b2_01_m2": "scripts/etapa7b2_01_datacao.py",
    "tab_e7b2_01_interacao": "scripts/etapa7b2_01_datacao.py",
    "tab_e7b2_01_wald": "scripts/etapa7b2_01_datacao.py",
    "tab_e7b2_01_p97": "scripts/etapa7b2_01_datacao.py",
    "tab_e7b2_01_casos_ind": "scripts/etapa7b2_01_datacao.py",
    "tab_e7b2_02_reclass_m2": "scripts/etapa7b2_01_datacao.py",
    "tab_e7b2_02_reclass_interacao": "scripts/etapa7b2_01_datacao.py",
    "tab_e7b2_02_reclass_wald": "scripts/etapa7b2_01_datacao.py",
    "tab_e7b3_01_esp_m2": "scripts/etapa7b3_01_esp_wald.py",
    "tab_e7b3_01_esp_interacao": "scripts/etapa7b3_01_esp_wald.py",
    "tab_e7b3_02_wald_ind": "scripts/etapa7b3_01_esp_wald.py",
    # 7c.3: especificações alternativas do acesso (3.3a índice contínuo, 3.3b tercil nacional), EP por região de saúde
    "tab_e3_02_interacao_rs": "scripts/etapa3_02_knol.py --rs",
    "tab_e3_02_wald_rs": "scripts/etapa3_02_knol.py --rs",
    "tab_e3_03a_indice_continuo_rs": "scripts/etapa3_02_knol.py --rs",
    # 7c.7: regiões de saúde e municípios por UF na base territorial (contagem descritiva; segundo motivo da sensibilidade sem CE/DF)
    "tab_e7c7_01_regsaude_uf": "scripts/etapa7c7_01_regsaude_uf.py",
    # Etapa 8: sensibilidade com a cobertura da Atenção Básica (2015–2021), EP por região de saúde
    "tab_e8_03_concordancia_resumo": "scripts/etapa8_03_tercis.py",
    "tab_e8_03_spearman": "scripts/etapa8_03_tercis.py",
    "tab_e8_03_raca_por_tercil": "scripts/etapa8_03_tercis.py",
    "tab_e8_04_interacao": "scripts/etapa8_04_modelos.py",
    "tab_e8_04_wald": "scripts/etapa8_04_modelos.py",
}
# tabelas com EP clusterizado por município: nunca lidas pelo pacote (o SRC acima é a lista de permissão)
PROIBIDAS = {"tab_e2_04_modelos_long", "tab_e2_04_modelos_brasil_fmt", "tab_e3_02_interacao", "tab_e3_02_conjunto",
             "tab_e3_02_dentro", "tab_e3_02_wald", "tab_e3_00b_atenuacao_ic", "tab_e4_01b_interacao", "tab_e4_02_interacao",
             "tab_e4b_03_interacao", "tab_e4b_03_m2", "tab_e4_06_mi_rubin", "tab_e4b_04_co_estratos", "tab_e1_05c_rp_or_da_brutas"}
LIDAS = []


def rd(nome):
    """Lê outputs/tables/<nome>_v1_20261008.csv (ou o nome exato, para arquivos sem sufixo de versão)."""
    assert nome in SRC, f"origem não mapeada (só tabelas da lista de permissão SRC): {nome}"
    assert nome not in PROIBIDAS, nome
    f = TB / (f"{nome}_v1_{S}.csv" if not nome.startswith("dicionario") else f"{nome}_{S}.csv")
    LIDAS.append(nome)
    return pd.read_csv(f)


def origem(nome):
    f = f"outputs/tables/{nome}_v1_{S}.csv" if not nome.startswith("dicionario") else f"outputs/tables/{nome}_{S}.csv"
    return dict(arquivo=f, script=SRC[nome], commit_pacote=COMMIT)


# ---------- formatação (inglês americano)
def num(x, d=2):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "n.a."
    s = f"{x:,.{d}f}"
    return s.replace("-", MINUS)


def n_(x):
    return f"{int(round(x)):,}"


def pr(e, lo, hi):
    return f"{num(e)} ({num(lo)}–{num(hi)})"


def rd_(e, lo, hi):
    return f"{num(e)} ({num(lo)} to {num(hi)})"


def pval(p):
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return "n.a."
    if p < 0.0001:
        return "<0.0001"
    return f"{p:.3g}"


def pct(x, d=1):
    return f"{x:.{d}f}"


# ---------- registro de números-chave
def _mesmo_valor(a, b):
    if isinstance(a, list) or isinstance(b, list):
        return isinstance(a, list) and isinstance(b, list) and len(a) == len(b) and all(_mesmo_valor(x, y) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return bool(np.isclose(a, b, rtol=1e-12, atol=0))
    return a == b


def na_tabela(it):
    """True se o valor bruto está numa célula numérica da tabela de origem (lido direto); False se foi derivado no pacote
    (razão, soma, diferença, mín/máx de células). Mesmo critério da checagem 1 do etapa7b_checa.py."""
    src = pd.read_csv(PROJ / it["arquivo"]).select_dtypes("number").to_numpy(dtype=float)
    v = it["valor_bruto"]
    return all(np.isclose(src, x, rtol=1e-9, atol=1e-12).any() for x in (v if isinstance(v, list) else [v]))


def commits_analise(itens):
    """7c.6. Devolve {id: (commit_registro, commit_analise)}.
    commit_registro: commit que versionou pela 1ª vez o valor atual. Percorre as versões arquivadas da mais nova para a mais antiga
    enquanto o id existe com o mesmo valor (formatado igual; bruto igual até 1e-12 relativo) e pega o commit que adicionou o JSON da
    versão mais antiga dessa sequência (git log --diff-filter=A no caminho original). Vazio se o id não está em versão arquivada.
    commit_analise: commit em que o número foi calculado.
    - Lido direto da tabela de origem (outputs/tables, fora do git): commit da etapa que gerou a tabela, aceito só quando duas fontes
      independentes concordam: (a) o 1º commit posterior à data de modificação da tabela; (b) o último commit do script de origem até o
      commit_registro.
    - Derivado no pacote: o commit_registro.
    Vazio sem commit_registro ou quando (a) e (b) discordam.
    Congelado: se a versão arquivada mais nova com o mesmo valor já tem commit_analise, ele é herdado (a data de modificação das tabelas
    não está no git e muda se outputs/tables for copiado ou reexecutado). Um campo vazio não congela: herda da versão mais antiga, na
    mesma sequência de valor igual, que tiver o campo; se nenhuma tiver, recalcula."""
    vers = []
    for d in MS.glob("_arquivo_v*"):
        js = sorted(d.glob("numeros_chave_v*_*.json"))
        if d.is_dir() and len(js) == 1:
            add = subprocess.run(["git", "-C", str(PROJ), "log", "--diff-filter=A", "--format=%h", "--", f"outputs/manuscrito/{js[0].name}"],
                                 capture_output=True, text=True).stdout.split()
            vers.append((int(d.name.split("_v")[1]), {i["id"]: i for i in json.load(open(js[0]))}, add[-1] if add else ""))
    vers.sort(key=lambda x: -x[0])
    git = lambda *a: subprocess.run(["git", "-C", str(PROJ), *a], capture_output=True, text=True).stdout
    hist = sorted((int(t), h) for h, t in (x.split() for x in git("log", "--format=%h %ct").splitlines()))
    out = {}
    for it in itens:
        cr, herda = "", ""
        for _, J, c in vers:
            x = J.get(it["id"])
            if x is None or x["valor_formatado"] != it["valor_formatado"] or not _mesmo_valor(x["valor_bruto"], it["valor_bruto"]):
                break
            cr = c
            herda = herda or x.get("commit_analise", "")
        if herda:
            ca = herda
        elif not cr or not it["script"]:
            ca = ""
        elif na_tabela(it):
            mt = (PROJ / it["arquivo"]).stat().st_mtime
            a = next((h for t, h in hist if t >= mt), "")
            b = git("log", "-1", "--format=%h", cr, "--", it["script"].split()[0]).strip()
            ca = a if a and a == b else ""
        else:
            ca = cr
        out[it["id"]] = (cr, ca)
    return out


class Registro:
    def __init__(self):
        self.itens = []

    def add(self, id_, bruto, fmt, nome, descricao, filtro=""):
        o = origem(nome) if nome in SRC else dict(arquivo=nome, script="", commit_pacote=COMMIT)
        self.itens.append(dict(id=id_, valor_formatado=fmt, valor_bruto=bruto, descricao=descricao, filtro=filtro, **o))

    def grava(self):
        ca = commits_analise(self.itens)
        for i in self.itens:
            i["commit_registro"], i["commit_analise"] = ca[i["id"]]
        js = MS / f"numeros_chave_{V}.json"
        json.dump(self.itens, open(js, "w"), ensure_ascii=False, indent=1, default=float)
        md = ["# Key numbers (Etapas 7b–7d)", "", f"Package {V}; commit_pacote {COMMIT} (repository HEAD when the package was generated). "
              "commit_registro = commit in which the current value of each number first entered the key-number inventory. "
              "commit_analise = commit in which the number was calculated: for a value read directly from its source table, the commit "
              "of the step that produced the table (first commit after the table's modification time, accepted only when it is also the "
              "last commit of the source script up to commit_registro); for a value derived in the package (ratio, sum, difference, "
              "min/max of table cells), commit_registro. Empty: not determined. Each value comes from the file/script shown. "
              "IC = interaction contrast (ids starting with ICR_ are internal identifiers kept from earlier versions).", "",
              "| id | value | description | source file | script | filter | commit_analise | commit_registro |",
              "|---|---|---|---|---|---|---|---|"]
        esc = lambda t: str(t).replace("|", "\\|")          # 7c.3: '|' do id de estrato do MAIHDA quebrava a tabela markdown
        for i in self.itens:
            md.append(f"| {i['id']} | {esc(i['valor_formatado'])} | {esc(i['descricao'])} | `{i['arquivo']}` | `{i['script']}` | {esc(i['filtro'])} "
                      f"| {i['commit_analise']} | {i['commit_registro']} |")
        (MS / f"numeros_chave_{V}.md").write_text("\n".join(md) + "\n")


# ---------- gravação de tabelas
def tem_raca(df):
    """True se a tabela mostra rótulos de raça/cor (colunas ou células com 'Brown')."""
    return any("Brown" in str(c) for c in df.columns) or df.astype(str).apply(lambda s: s.str.contains("Brown")).any().any()


def com_nota_raca(df, rodape):
    """7c.1: a nota Brown/Black (IBGE) abre o rodapé de toda tabela com rótulos de raça, se ainda não estiver lá."""
    return rodape if (NOTE_BROWN in rodape or not (tem_raca(df) or "Brown" in rodape)) else NOTE_BROWN + " " + rodape


def _par_italico(p, texto, size):
    """Parágrafo do docx com 'parda', 'preta' e 'amarela' em itálico (termos em português)."""
    import re as _re
    for k, pedaco in enumerate(_re.split(r"\b(parda|preta|amarela)\b", texto)):
        run = p.add_run(pedaco)
        run.italic = k % 2 == 1
        if size is not None:
            run.font.size = size


def grava_tabela(df, nome, titulo, rodape, pasta=TABD, xlsx_conjunto=None, docx_doc=None):
    """CSV + aba no xlsx do conjunto + tabela no docx; devolve o caminho do csv."""
    rodape = com_nota_raca(df, rodape)
    csv = pasta / f"{nome}_{V}.csv"
    df.to_csv(csv, index=False)
    if xlsx_conjunto is not None:
        xlsx_conjunto.append((nome[:31], titulo, df, rodape))
    if docx_doc is not None:
        from docx.shared import Pt
        docx_doc.add_paragraph().add_run(titulo).bold = True
        t = docx_doc.add_table(rows=1, cols=len(df.columns))
        t.style = "Table Grid"
        for j, c in enumerate(df.columns):
            t.rows[0].cells[j].text = str(c)
        for _, r in df.iterrows():
            cells = t.add_row().cells
            for j, v in enumerate(r):
                cells[j].text = "" if (isinstance(v, float) and np.isnan(v)) else str(v)
        for row in t.rows:
            for c in row.cells:
                for p in c.paragraphs:
                    for run in p.runs:
                        run.font.size = Pt(7)
        _par_italico(docx_doc.add_paragraph(), rodape, Pt(7))
        docx_doc.add_page_break()
    return csv


def grava_xlsx(conjunto, caminho):
    with pd.ExcelWriter(caminho, engine="openpyxl") as w:
        for aba, titulo, df, rodape in conjunto:
            pd.DataFrame([[titulo]]).to_excel(w, sheet_name=aba, index=False, header=False, startrow=0)
            df.to_excel(w, sheet_name=aba, index=False, startrow=2)
            pd.DataFrame([[rodape]]).to_excel(w, sheet_name=aba, index=False, header=False, startrow=len(df) + 4)


def painel_knol(d_, cj, dn, it, wd, cnt, reg=None):
    """Linhas de um painel Knol & VanderWeele (formato da Tabela 3) para o desfecho d_ (fontes tab_e6_01a_* e tab_e3_01)."""
    rows = []
    w = wd[wd.desfecho == d_].iloc[0]
    assert int(cnt.loc[d_].n.sum()) == int(w.N)
    rows.append({"Race / tertile": f"{OUTC[d_]} (N = {n_(w.N)}; Wald test of the 6 interaction terms: χ² = {w.chi2:.1f}, "
                                   f"{int(w.gl)} df, p = {pval(w.p)})"})
    for g in RACES:
        for t in ["T1", "T2", "T3"]:
            c = cj[(cj.desfecho == d_) & (cj.raca == g) & (cj.nivel == t)].iloc[0]
            k = cnt.loc[(d_, g, t)]
            r = {"Race / tertile": f"  {RACE[g]} – {TERC[t]}", "Cases": n_(k.casos), "Non-cases": n_(k.n - k.casos),
                 "Joint PR vs White–T3 (95% CI)": "1.00 (reference)" if (g, t) == ("Branca", "T3") else pr(c.RP, c.RP_lo, c.RP_hi),
                 "Joint RD per 100 vs White–T3 (95% CI)": "0.00 (reference)" if (g, t) == ("Branca", "T3") else rd_(c.DR_pp, c.DR_lo, c.DR_hi)}
            if g != "Branca":
                x = dn[(dn.desfecho == d_) & (dn.raca == g) & (dn.nivel == t)].iloc[0]
                r["Within-tertile PR vs White (95% CI)"] = pr(x.RP, x.RP_lo, x.RP_hi)
                r["Within-tertile RD per 100 (95% CI)"] = rd_(x.DR_pp, x.DR_lo, x.DR_hi)
                if t != "T3":
                    y = it[(it.desfecho == d_) & (it.raca == g) & (it.nivel == t)].iloc[0]
                    r["IC per 100 (95% CI)"] = rd_(y.ICR_pp, y.ICR_lo, y.ICR_hi)
                    r["IC p"] = pval(y.ICR_p)
                    r["RERI (95% CI)"] = rd_(y.RERI, y.RERI_lo, y.RERI_hi)
                    r["Multiplicative interaction (95% CI)"] = pr(y.int_mult, y.int_mult_lo, y.int_mult_hi)
            rows.append(r)
    return rows


def html_pdf(html, pdf):
    """Imprime HTML em PDF com o Chrome headless (sem cabeçalho/rodapé do navegador)."""
    import subprocess
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as fh:
        fh.write(html)
        src = fh.name
    chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    r = subprocess.run([chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf}", f"file://{src}"],
                       capture_output=True, text=True, timeout=120)
    assert Path(pdf).exists() and Path(pdf).stat().st_size > 1000, r.stderr[-500:]


HTML_CSS = ("<style>body{font-family:Arial,Helvetica,sans-serif;font-size:9pt;color:#000;margin:18mm}"
            "h1{font-size:13pt}h2{font-size:11pt;margin-top:14pt}table{border-collapse:collapse;width:100%;margin:6pt 0}"
            "td,th{border:0.5pt solid #555;padding:2pt 4pt;vertical-align:top;text-align:left}th{background:#eee}"
            "p.note{font-size:8pt}</style>")
