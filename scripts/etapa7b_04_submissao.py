"""
7b.4 Pasta Submissao/ (só figuras finais .tif e ESM) e MANIFEST.md (arquivos, origem, script, data, mapa S → ESM).
  Fig1–Fig4.tif = cópias de outputs/manuscrito/figuras/fig0N_*.tif
  ESM_1.xlsx = S1, S1b, S2, S3, S4, S4b, S5, S6 (S5b do Centro-Oeste fica FORA: interno até conversa com os orientadores)
  ESM_2.pdf = S7 = Online Resource 2 (S7a variáveis e códigos, RECORD 6.1 [7c.1]; S7b dicionário operacional; código 8);
  ESM_3.pdf = S8 (STROBE + RECORD); ESM_4.pdf = S9 (caterpillar MAIHDA)
  7c.5: dot_clean -m antes e depois da montagem; Submissao/ não pode ter arquivos ._* (AppleDouble do exFAT)
  7c.7: o MANIFEST deixa fora as autoauditorias das etapas (audita_*.csv, gravadas depois do pacote) e escapa o | dentro das células
  8: S2b com a cobertura da Atenção Básica (colunas d e e); MANIFEST com a v13 no histórico
  8b: Wald de 6 gl das colunas d e e na S2b; MANIFEST com a v14 no histórico
  7d (v15): Submissao/ final = Title_Page.docx, Manuscript.docx, Cover_Letter.docx, Fig1–4.tif, ESM_1.pdf (OR1, STROBE + RECORD com página e
  linha), ESM_2.pdf (OR2, S7), ESM_3.pdf (OR3, Supplementary Methods), ESM_4.xlsx (OR4, tabelas S com a S3b), ESM_5.pdf (OR5, Fig. S9).
  Os .docx e os PDFs do ESM_1 e do ESM_3 vêm de outputs/manuscrito/montagem (etapa7d_01_montagem.py, que roda antes deste script);
  o Title_Page.docx e a Cover_Letter.docx são cópias byte a byte de manuscrito/. Arquivo de Submissao/ fora dessa lista vai para a
  lixeira (trash), nunca rm; a v14 de Submissao/ está em outputs/manuscrito/_arquivo_v14/Submissao.
"""
import base64
import hashlib
import shutil
import subprocess
from datetime import date

import etapa7b_lib as B
import etapa0_lib as L

log = L.Logger("7b_04_submissao", etapa="etapa7b")
V = B.V


def limpa_macos(pasta):
    """7c.5: no exFAT, o macOS guarda xattrs (ex.: com.apple.quarantine dos PDFs) em arquivos ._*; dot_clean -m os remove junto com os
    xattrs. .DS_Store não é tocado, só avisado no log. Falha se sobrar algum ._*."""
    subprocess.run(["dot_clean", "-m", str(pasta)], check=True)
    sobra = sorted(str(x.relative_to(pasta)) for x in pasta.rglob("._*"))
    if sobra:                                              # 7c.6: raise, e não assert (o python -O desliga assert)
        raise RuntimeError(f"._* em {pasta}: {sobra}")
    ds = sorted(str(x.relative_to(pasta)) for x in pasta.rglob(".DS_Store"))
    if ds:
        log(f"aviso: .DS_Store em {pasta} (não enviar): {ds}")


limpa_macos(B.SUB)                                   # antes de montar
MONT = B.MS / "montagem"                             # 7d: saídas do etapa7d_01_montagem.py
FINAL = ["Cover_Letter.docx", "ESM_1.pdf", "ESM_2.pdf", "ESM_3.pdf", "ESM_4.xlsx", "ESM_5.pdf", "Fig1.tif", "Fig2.tif", "Fig3.tif", "Fig4.tif",
         "Manuscript.docx", "Title_Page.docx"]
for x in sorted(B.SUB.iterdir()):                    # 7d: o que não pertence à Submissao final vai para a lixeira (trash, recuperável)
    if not x.name.startswith("._") and x.name not in FINAL:
        subprocess.run(["trash", str(x)], check=True)
        log(f"lixeira: Submissao/{x.name} (cópia em _arquivo_v14/Submissao)")
# cópias com nomes fixos: copy2 sobrescreve
FIG = {"Fig1.tif": f"fig01_flowchart_{V}.tif", "Fig2.tif": f"fig02_pr_race_m1m3_{V}.tif", "Fig3.tif": f"fig03_rd_race_tercile_{V}.tif",
       "Fig4.tif": f"fig04_dating_{V}.tif"}
for dst, src in FIG.items():
    shutil.copy2(B.FIGD / src, B.SUB / dst)
shutil.copy2(MONT / f"ESM_1_strobe_record_located_{V}.pdf", B.SUB / "ESM_1.pdf")       # OR1 (7d)
shutil.copy2(B.SUPD / f"S7_variables_codes_{V}.pdf", B.SUB / "ESM_2.pdf")               # OR2
shutil.copy2(MONT / f"ESM_3_supplementary_methods_{V}.pdf", B.SUB / "ESM_3.pdf")       # OR3 (7d)
shutil.copy2(B.SUPD / f"ESM_4_tables_S1_S6_{V}.xlsx", B.SUB / "ESM_4.xlsx")             # OR4
leg = [l for l in (B.MS / "legendas_figuras.md").read_text().split("\n\n") if l.startswith("**Online Resource 5")]
if len(leg) != 1:                                    # 7d: raise com mensagem (antes, [0] dava IndexError quando o rótulo mudava)
    raise RuntimeError(f"legenda da Online Resource 5 (Fig. S9) não encontrada em legendas_figuras.md: {len(leg)}")
leg = leg[0]
png = base64.b64encode((B.SUPD / f"S9_maihda_caterpillar_{V}.png").read_bytes()).decode()
B.html_pdf(B.HTML_CSS + f"<h1>Online Resource 5 (Fig. S9). Intersectional MAIHDA of SGA</h1><img src='data:image/png;base64,{png}' "
           f"style='width:100%'><p class='note'>{leg.split('**', 2)[2].strip()}</p>", B.SUB / "ESM_5.pdf")   # OR5
shutil.copy2(MONT / f"Manuscript_{V}.docx", B.SUB / "Manuscript.docx")
for f in ("Title_Page.docx", "Cover_Letter.docx"):
    shutil.copy2(B.PROJ / "manuscrito" / f, B.SUB / f)
import openpyxl
abas = openpyxl.load_workbook(B.SUB / "ESM_4.xlsx").sheetnames
if any("S5b" in a or "INTERNAL" in a for a in abas):  # 7c.6: raise, e não assert (o python -O desliga assert)
    raise RuntimeError(f"aba interna no ESM_4 de Submissao/: {abas}")
sub_ = sorted(x.name for x in B.SUB.iterdir() if not x.name.startswith("._"))
if sub_ != FINAL:
    raise RuntimeError(f"Submissao/ diferente da lista final: {sub_}")
limpa_macos(B.SUB)                                   # depois: os PDFs saem com com.apple.quarantine, que o exFAT grava em ._*

md5 = lambda p: hashlib.md5(p.read_bytes()).hexdigest()
ORIG = {  # arquivo do pacote → (script do pacote, tabelas de origem)
    "tab01": ("etapa7b_01_tabelas.py", "tab_e1_03_tabela1_long, tab_e3_01_n_casos_raca_tercil_regiao, tab_e3_00a_ig_metodo_raca, tab_e6b_01_ptb_raca_metodo"),
    "tab02": ("etapa7b_01_tabelas.py", "tab_e6b_01_modelos_m1m3, tab_e3_00b_atenuacao_ic_rs (atenuação só com |PR_M2cc − 1| ≥ 0.10)"),
    "tab03_": ("etapa7b_01_tabelas.py", "tab_e6_01a_{conjunto,dentro,interacao,wald}, tab_e3_01_n_casos_raca_tercil_regiao, tab_e7b1_05_reri_recod"),
    "tab04": ("etapa7b_01_tabelas.py", "tab_e6_01a_m2, tab_e6_01a_interacao, tab_e6b_01_m2_cenarios, tab_e6_01b_interacao, tab_e6_04_m2, "
                                       "tab_e6_04_interacao, tab_e4_06_mi_m2_rubin_rs, tab_e4_06_mi_rubin_rs, tab_e6_07b_limites, "
                                       "tab_e7b1_01_cenarios_{interacao,wald}, tab_e6_01a_wald, tab_e6_04_wald, tab_e7b1_04_{m2,interacao}, "
                                       "tab_e7b2_01_{m2,interacao,wald}, tab_e7b2_02_reclass_{m2,interacao,wald}, tab_e7b3_02_wald_ind"),
    "tabelas_principais": ("etapa7b_01_tabelas.py", "Tables 1, 2, 3, 4"),
    "S1_": ("etapa7b_02_suplementar.py", "tab06_fluxograma_regiao, tab07_fluxograma_motivos, tab_e7b1_02_s1_restrito, tab08_ptb_incluidos_excluidos, tab_e7b1_04_naoclass"),
    "S1b": ("etapa7b_02_suplementar.py", "tab01_completude_ano, tab_e2_01_tpmetestim_ano_regiao, tab_e6_03a_robson"),
    "S2_": ("etapa7b_02_suplementar.py", "tab_e6_01a_* (ptb_esp), tab_e3_01_n_casos_raca_tercil_regiao, tab_e7b1_04_{m2,interacao,naoclass}"),
    "S2b": ("etapa7b_02_suplementar.py", "tab_e3_02_interacao_rs, tab_e3_02_wald_rs, tab_e3_03a_indice_continuo_rs, tab_e8_04_interacao, "
                                         "tab_e8_04_wald, tab_e8_03_spearman, tab_e8_03_concordancia_resumo, tab_e8_03_raca_por_tercil "
                                         "(EP por região de saúde)"),
    "S3_": ("etapa7b_02_suplementar.py", "tab_e6_03b_rrr"),
    "S3b": ("etapa7b_02_suplementar.py", "tab_e3_01_tercis_regiao_cortes, tab_e3_01_n_casos_raca_tercil_regiao (antiga Tabela 3b)"),
    "S4": ("etapa7b_02_suplementar.py", "tab_e6_05_multiplicidade"),
    "S5_": ("etapa7b_02_suplementar.py", "tab_e4b_01_implausivel_brasil"),
    "S5b": ("etapa7b_02_suplementar.py", "tab_e4b_04_co_estratos_rs (INTERNAL)"),
    "S5c": ("etapa7b_02_suplementar.py", "tab_e7b2_01_{dist,dist_tercil,m2,interacao,wald,p97,casos_ind}"),
    "S5d": ("etapa7b_02_suplementar.py", "tab_e7b3_01_esp_{m2,interacao}, tab_e7b3_02_wald_ind, tab_e7b2_02_reclass_interacao"),
    "S6_": ("etapa7b_02_suplementar.py", "tab_e5_02_modelos, tab_e6_06_maihda_area, tab_e6b_02_auc_area, tab_e7b1_03_auc_fixa, tab_e5_03_predicoes"),
    "S7_": ("etapa7b_02_suplementar.py", "S7a (docs/referencias/SINASC_Estrutura_2024.pdf, Dicionario_SIM_2025.pdf; códigos da ficha 7c.0), "
                                         "dicionario_variaveis_v3, tab_e6_02a_concordancia, tab_e6_02b_tpmetestim_2010_2014"),
    "S7a": ("etapa7b_02_suplementar.py", "docs/referencias/SINASC_Estrutura_2024.pdf, Dicionario_SIM_2025.pdf; códigos da ficha 7c.0; "
                                         "tab_e6_02a_concordancia, tab_e6_02b_tpmetestim_2010_2014"),
    "S7b": ("etapa7b_02_suplementar.py", "dicionario_variaveis_v3"),
    "S8_": ("etapa7b_02_suplementar.py", "docs/referencias/RECORD_checklist_acesso20261009.docx (CC BY; ver docs/referencias/ATRIBUICAO.txt)"),
    "S9_": ("etapa7b_03_figuras.py", "tab_e5_03_predicoes"),
    "ESM_4_": ("etapa7b_02_suplementar.py", "S1–S6 com S3b (sem S5b)"),
    "Manuscript_": ("etapa7d_01_montagem.py", "manuscrito/Manuscript.docx + Tabelas 1–4 (tabelas/) + Figs. 1–4 (figuras/, PNG); PDF pelo Microsoft Word"),
    "ESM_3_": ("etapa7d_01_montagem.py", "manuscrito/ESM_3_Supplementary_Methods.docx + URL de docs/referencias/aps_cobertura_ab/ACESSO.txt; PDF pelo Microsoft Word"),
    "ESM_1_": ("etapa7d_01_montagem.py", "S8 + página e linha do Manuscript (PDF do Word)"),
    "S8_strobe_record_located": ("etapa7d_01_montagem.py", "S8 + página e linha do Manuscript (PDF do Word)"),
    "fig01": ("etapa7b_03_figuras.py", "tab06, tab07, tab_e6_01a_wald, tab_e6b_01_ptb_raca_metodo, tab_e6_04_m2, tab_e3_00a_ig_metodo_raca"),
    "fig02": ("etapa7b_03_figuras.py", "tab_e6b_01_modelos_m1m3"),
    "fig03": ("etapa7b_03_figuras.py", "tab_e6_01a_conjunto, tab_e6_01a_interacao"),
    "fig04": ("etapa7b_03_figuras.py", "tab_e6b_01_ptb_raca_metodo, tab_e4b_01_implausivel_brasil, tab_e6b_01_m2_cenarios, tab_e6_01a_m2, tab_e6_04_m2"),
    "numeros_chave": ("etapa7b_01_tabelas.py", "ver cada item"),
    "legendas": ("etapa7b_03_figuras.py", "—"), "data_code": ("etapa7b_02_suplementar.py", "docs/referencias/*/ACESSO.txt"),
}


def orig(nome):
    for k, v in ORIG.items():
        if nome.startswith(k):
            return v
    return ("", "")


linhas = [f"# MANIFEST — pacote de resultados (Etapas 7b–7d, {V})", "",
          f"Gerado em {date.today().isoformat()}. Commit do repositório ao gerar o pacote: {B.COMMIT} (o pacote {V} entra no commit "
          "'Etapa 7d: montagem da Submissao (pacote v15)'). Nenhuma análise nova no pacote: todo número vem de "
          "outputs/tables/*_v1_20261008.csv (EP por região de saúde). v5 = v4 com rótulos novos (IC, Brown), sem a sensibilidade "
          "'Excluding 2024' e com a Tabela S7a (variáveis e códigos); v6 = v5 com 'tertile', 'Asian (amarela)' na S7a, SEXO do SIM "
          "recodificado (q do PIG idêntico) e proveniência dos dados; v7 = v6 com 'Asian (amarela)' em todo o pacote, N do M2cc/M3 no "
          "rodapé da Tabela 2 e números-chave das especificações alternativas do acesso (EP por região de saúde); v8 = v7 com a Tabela S2b "
          "(especificações alternativas do acesso) no ESM_1; v9 = v8 com a justificativa da exclusão da raça Asian (amarela) no rodapé da S1 "
          "e na disponibilidade (número-chave pct_amarela_fonte) e Submissao/ montada sem arquivos ._* (dot_clean); v10 = v9 com o "
          "denominador do índice de acesso explícito nos rodapés (nascimentos com mês de início do pré-natal conhecido); v11 = v10 com "
          "os campos commit_pacote (antigo commit), commit_registro e commit_analise nos números-chave; v12 = v11 com o rodapé da Tabela 4 "
          "dizendo que os testes de Wald conjuntos não foram calculados na imputação múltipla, os números-chave n_regsaude_CE e "
          "n_regsaude_DF (regiões de saúde no mapa município → região de saúde da base territorial, tab_e7c7_01_regsaude_uf) e "
          "suplementar/ sem arquivos ._* (dot_clean no 02); v13 = v12 com a cobertura da Atenção Básica na Tabela S2b (colunas d e e, "
          "nascimentos de 2015–2021; tab_e8_04_*, tab_e8_03_*, Etapa 8), os números-chave da Etapa 8 e a nota geral 'n.a.' no rodapé da "
          "Tabela 4; v14 = v13 com o Wald de 6 gl (termos raça × tercil) nas colunas d e e da Tabela S2b e seus 6 números-chave (Etapa 8b); "
          "v15 = v14 com a Submissao/ final (Etapa 7d): Online Resources renumeradas na ordem de 1ª citação (OR1 STROBE + RECORD, OR2 "
          "variáveis, OR3 Supplementary Methods, OR4 tabelas S, OR5 Fig. S9), a Tabela 3b movida para a S3b (ESM_4.xlsx), TIFF em RGB sem "
          "alfa (mesmos pixels), o manuscrito montado com as Tabelas 1–4 e as Figs. 1–4 e o checklist com página e linha (montagem/). "
          "Scripts em scripts/. As autoauditorias das etapas (audita_*.csv, na raiz de "
          "outputs/manuscrito/) ficam fora da lista de arquivos: são gravadas depois do pacote, para conferi-lo.", "",
          "## Correspondência material suplementar → Online Resource (Springer)", "",
          "| Suplementar | Conteúdo | Arquivo em Submissao/ |", "|---|---|---|",
          "| S8 | Online Resource 1: checklist STROBE + RECORD, com página e linha do Manuscript final | ESM_1.pdf |",
          "| S7 (S7a, S7b) | Online Resource 2: variáveis e códigos (S7a, RECORD 6.1), dicionário operacional (S7b) e código 8 | ESM_2.pdf |",
          "| — | Online Resource 3: Supplementary Methods (texto dos autores, com a URL da cobertura da Atenção Básica) | ESM_3.pdf |",
          "| S1, S1b | Online Resource 4: fluxo STROBE, excluídos × incluídos; dados faltantes | ESM_4.xlsx (abas S1_flow_excluded, S1b_missing_data) |",
          "| S2 | Online Resource 4: Knol & VanderWeele, PTB espontâneo | ESM_4.xlsx (S2_knol_spontaneous) |",
          "| S2b | Online Resource 4: especificações alternativas do acesso (tercis nacionais, índice contínuo; cobertura da Atenção Básica e índice, 2015–2021; EP por região de saúde) | ESM_4.xlsx (S2b_access_specifications) |",
          "| S3 | Online Resource 4: multinomial termo/espontâneo/indicado | ESM_4.xlsx (S3_multinomial) |",
          "| S3b | Online Resource 4: cortes dos tercis por macrorregião (antiga Tabela 3b) | ESM_4.xlsx (S3b_terciles_region) |",
          "| S4, S4b | Online Resource 4: exploratórias com p ajustado por BH | ESM_4.xlsx (S4_exploratory_strata, S4b_exploratory_family) |",
          "| S5 | Online Resource 4: plausibilidade peso × IG | ESM_4.xlsx (S5_weight_ga_plausibility) |",
          "| S5c | Online Resource 4: outro método separado em código 1 e código 2 (diagnóstico de datação) | ESM_4.xlsx (S5c_other_method_by_code) |",
          "| S5d | Online Resource 4: PTB espontâneo por código e Wald dos termos indígenas (2 gl) | ESM_4.xlsx (S5d_spontaneous_by_code_wald) |",
          "| S5b | Centro-Oeste, modelo da RSP por método | **NÃO enviado** (só em outputs/manuscrito/suplementar; aguarda orientadores) |",
          "| S6 | Online Resource 4: MAIHDA (PIG) | ESM_4.xlsx (S6_maihda) |",
          "| S9 | Online Resource 5: caterpillar MAIHDA | ESM_5.pdf |", "",
          "## Arquivos", "", "| Arquivo | Script | Origem | MD5 |", "|---|---|---|---|"]
for pasta, rot in [(B.TABD, "manuscrito/tabelas"), (B.FIGD, "manuscrito/figuras"), (B.SUPD, "manuscrito/suplementar"), (MONT, "manuscrito/montagem"),
                  (B.MS, "manuscrito"), (B.SUB, "Submissao")]:
    for f in sorted(pasta.iterdir()):
        if f.is_dir() or f.name.startswith(("._", "_", "audita_")) or f.name == "MANIFEST.md":
            continue
        s, o = orig(f.name) if pasta != B.SUB else ("etapa7b_04_submissao.py", "cópia de manuscrito/ (Title_Page, Cover_Letter)"
                                                   if f.name in ("Title_Page.docx", "Cover_Letter.docx") else "cópia/montagem de outputs/manuscrito")
        linhas.append(f"| {rot}/{f.name} | {s} | {o.replace('|', chr(92) + '|')} | {md5(f)[:12]} |")
(B.MS / "MANIFEST.md").write_text("\n".join(linhas) + "\n")
limpa_macos(B.MS)                                    # 7d: e em outputs/manuscrito (montagem, tabelas, figuras, MANIFEST; o Word e o PIL deixam xattrs)
log(f"Submissao: {sorted(x.name for x in B.SUB.iterdir() if not x.name.startswith('._'))}; abas ESM_4 {abas}")
