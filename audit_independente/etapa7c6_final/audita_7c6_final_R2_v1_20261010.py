"""
Auditoria independente final da 7c.6 — RODADA 2 (2026-10-10/11). Acrescenta linhas R2.* ao comparacao_7c6_final_v1_20261010.csv
sem tocar nas 116 linhas da rodada 1 (confere o MD5 dessa parte antes de gravar).

Nesta rodada o coordenador LIBEROU a leitura da autoauditoria do autor (scripts/etapa7c6_02_audita_final.py e
outputs/manuscrito/audita_final_7c6_v1_20261010.csv), que é um dos objetos da rodada.

Passos feitos ANTES deste script (evidência nesta pasta):
- R2.05: cópia do gerador etapa7c6b_01_resumo.py com a saída desviada (etapa7c6b_01_resumo_copia_saida_auditor.py), rodada em
  2026-10-10 16:19:52 com o CSV desta pasta ainda no estado da rodada 1 (MD5 6e131c769b4f4e65f2a99059cd133a6c) →
  RESUMO_ETAPA7C6b_reproduzido_r2_v1_20261010.md.
- R2.02: cópia da autoauditoria com a saída desviada para esta pasta (etapa7c6_02_audita_final_copia_auditor_r2.py; troca de PROJ,
  SAIDA, tmp, status sem reescrever o índice e o arquivo de memória fora do projeto, que não foi lido); o original quebra no L4.01
  (ver R2.02.05), então a cópia exclui o gerador novo da 7c.6b do L4.01 → audita_final_reexecucao_auditor_r2_v1_20261010.csv.
- R2.01/R2.04: cópia do gerador da 7c.6 rodada de novo (etapa7c6_01_resumo_copia_saida_auditor_r2.py →
  RESUMO_ETAPA7C6_reproduzido_r2_v1_20261010.md); pack-objects --stdout (nada gravado no .git) para o tamanho empacotado.
Rodar: PYTHONDONTWRITEBYTECODE=1 python3 audit_independente/etapa7c6_final/audita_7c6_final_R2_v1_20261010.py
"""
import csv
import hashlib
import io
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.dont_write_bytecode = True
from audita_7c6_final_lib_v1_20261010 import HEAD, MS, PROJ, docx_texto, git, pdf_texto, ws, xlsx_celulas  # noqa: E402

CSV_ = AQUI / "comparacao_7c6_final_v1_20261010.csv"
MD5_R1 = "6e131c769b4f4e65f2a99059cd133a6c"
ROWS = []


def reg(vid, ok, det):
    ROWS.append(dict(verificacao=vid, ok=bool(ok), detalhe=str(det)))
    print(f"{'OK   ' if ok else 'FALHA'} {vid}: {str(det)[:200]}", flush=True)


ler = lambda p: Path(p).read_text(encoding="utf-8")
md5 = lambda b: hashlib.md5(b).hexdigest()
R6B = ler(PROJ / "outputs/RESUMO_ETAPA7C6b_v1_20261010.md")
TXT6B = ler(MS / "_resumo7c6b_texto_v1_20261010.md")
AU = list(csv.DictReader(io.StringIO(ler(MS / "audita_final_7c6_v1_20261010.csv"))))
AUd = {r["verificacao"].split()[0]: r for r in AU}
WEB = json.loads(ler(AQUI / "web_7c6_final_v1_20261010.json"))
R1 = {r["verificacao"]: r for r in csv.DictReader(io.StringIO(CSV_.read_text(encoding="utf-8"))) if not r["verificacao"].startswith("R2")}

# ===================================================== R2.01 ATRIBUICAO.txt
novo = ler(PROJ / "docs/referencias/ATRIBUICAO.txt")
velho = git("show", f"{HEAD}:docs/referencias/ATRIBUICAO.txt")
d = [l for l in git("diff", "-U0", HEAD, "--", "docs/referencias/ATRIBUICAO.txt").splitlines() if l.startswith("@@")]
ini_lic = [i + 1 for i, l in enumerate(velho.splitlines()) if l.startswith("Licença:")][0]
hunks = [tuple(int(x) for x in re.match(r"@@ -(\d+)", h).groups()) for h in d]
reg("R2.01.01", all(h[0] > ini_lic for h in hunks) and velho.splitlines()[:ini_lic] == novo.splitlines()[:ini_lic]
    and novo.splitlines()[ini_lic + 2:ini_lic + 7] == velho.splitlines()[ini_lic + 1:ini_lic + 6],
    f"diff contra {HEAD}: {len(d)} trechos ({d}); a linha 'Licença:' é a {ini_lic}; as {ini_lic} primeiras linhas (arquivo, MD5, uso, fonte, obra, "
    f"linha da licença) estão iguais; mudam só a nota entre parênteses (1 linha → 2) e 2 linhas novas depois da citação do artigo")
tdoc = docx_texto(str(PROJ / "docs/referencias/RECORD_checklist_acesso20261009.docx"))
plos = WEB["record_artigo_plos_licenca"]
cita = re.search(r'no artigo: "(.*?)"', ws(novo)).group(1)
ok_cita = ws(cita) in ws(plos["texto"]).replace(" ,", ",")
reg("R2.01.02", ("CC BY" in tdoc and "4.0" not in tdoc) and "http://creativecommons.org/licenses/by/4.0/" in WEB["record_pagina"]["links_cc"]
    and plos["href"] == ["http://creativecommons.org/licenses/by/4.0/"] and WEB["record_artigo_pmc"]["licenca_xlink"] == ["http://creativecommons.org/licenses/by/4.0/"]
    and ok_cita and "PMC4595218" in novo,
    f"conferido contra a fonte (GETs públicos de 2026-10-10 {WEB['quando'][11:16]}, web_7c6_final_v1_20261010.json): docx só 'CC BY' (sem '4.0'): True; página do "
    f"checklist liga a {WEB['record_pagina']['links_cc']}; PLOS: declaração de copyright liga a {plos['href']}; XML do PMC PMC4595218: <license xlink:href="
    f"{WEB['record_artigo_pmc']['licenca_xlink']}>; a citação 'no artigo' do ATRIBUICAO é o texto da PLOS: {ok_cita} (o texto do XML do PMC diz 'open-access' e "
    f"'properly credited'; o ATRIBUICAO só afirma que o PMC traz a mesma URL, o que é verdade)")
chk_ok = all(x in novo for x in ["doi:10.1371/journal.pmed.1001885", "Creative Commons Attribution (CC BY)", "https://creativecommons.org/licenses/by/4.0/",
                                 "https://www.record-statement.org/Files/checklist/RECORD%20Checklist.docx", "Benchimol EI",
                                 "d50bd10feb3c20398ccce6f3c27b7777"])
rep76 = (AQUI / "RESUMO_ETAPA7C6_reproduzido_r2_v1_20261010.md").read_text()
com76 = git("show", f"{HEAD}:outputs/RESUMO_ETAPA7C6_v1_20261009.md")
dl = [l for l in __import__("difflib").unified_diff(com76.splitlines(), rep76.splitlines(), lineterm="", n=0) if l.startswith("@@")]
reg("R2.01.03", chk_ok, f"efeitos: a checagem de RECORD do etapa7b_checa (L609–L613: DOI, 'Creative Commons Attribution (CC BY)', URLs, MD5) continua satisfeita "
                        f"pelo texto novo: {chk_ok}. O gerador do RESUMO 7c.6 rodado agora (cópia com saída desviada, 17:57) difere do commit em {len(dl)} trechos "
                        f"{dl}: o bloco do ATRIBUICAO (seção 2) e a lista de scripts/resumos (seção 5, agora com etapa7c6b_01_resumo.py)")

# ===================================================== R2.02 autoauditoria
csv_t = (MS / "audita_final_7c6_v1_20261010.csv").stat().st_mtime
atr_t = (PROJ / "docs/referencias/ATRIBUICAO.txt").stat().st_mtime
src = ler(PROJ / "scripts/etapa7c6_02_audita_final.py")
fixa = ['gitb("show", f"{HEAD}:docs/referencias/ATRIBUICAO.txt")' in src,
        '"(B.PROJ / \'docs/referencias/ATRIBUICAO.txt\').read_text()", "ATRIB_HEAD"' in src]
reg("R2.02.01", all(fixa) and atr_t > csv_t,
    f"fixação do ATRIBUICAO em {HEAD} (L244 para o L4.03; L308 troca a leitura do disco no L7.01): legítima para auditar o estado commitado — o objeto é {HEAD} e o "
    f"RESUMO 7c.6 traz o ATRIBUICAO de {HEAD}. Não mascarou nada: o CSV da autoauditoria foi gravado às 11:22:31 e o ATRIBUICAO só mudou às 11:22:44 "
    f"(13 s depois), então no momento da execução o disco ainda era igual ao commit. Ressalva: o rótulo do L7.01 ('RESUMO regenerado agora = commitado') não diz que o "
    f"ATRIBUICAO foi trocado pelo de {HEAD}; isso só está na docstring")
mine = {"L8.01": "L5.03", "L10.01": "L1.49", "L10.02": "L1.53", "L10.03": "L2c.05", "L10.04": "L1.09 (ressalva)", "L10.05": "L1.13 (ressalva)",
        "L4.05": "M1.01 (fato)"}
conf = {k: AUd[k]["ok"] == "False" for k in mine}
reg("R2.02.02", all(conf.values()) and "linhas com B.COMMIT no checa: [526]; aviso: nenhum" in AUd["L8.01"]["detalhe"]
    and "if aud76.exists()" in AUd["L10.01"]["detalhe"] and "tab_e3_03a_indice_continuo_rs" in AUd["L10.02"]["detalhe"]
    and "41 vezes" in AUd["L10.05"]["detalhe"],
    f"L8.01 e bloco L10 conferem com os meus achados: { {k: v for k, v in mine.items()} }. L8.01 agora exige 'checa' + 'HEAD/commit_pacote' + 'falh/reexecut' na mesma "
    f"linha e dá False (sem aviso), = meu L5.03. L10.01–L10.05 refazem com código próprio as minhas 3 falhas e 2 ressalvas; o L10.03 é conferência manual, "
    f"gravado como False fixo (o rótulo diz 'conferência manual')")
falsos = [r["verificacao"].split()[0] for r in AU if r["ok"] == "False"]
reg("R2.02.03", sorted(falsos) == sorted(mine),
    f"os 7 False ({falsos}) correspondem a erros reais do RESUMO 7c.6: 3 que eu dei como falha (L10.01–L10.03), 2 que dei como ressalva e são imprecisões literais "
    f"(L10.04: 12 arquivos diferem em bytes; L10.05: o 02 chama B.rd() 41 vezes antes da S8), 1 omissão (L8.01: nenhum aviso de que o checa falha depois do commit) e "
    f"1 omissão de escopo (L4.05: 'Fora dela: 36' sem dizer que exclui data/; são 37 no projeto). Nenhum é erro de número do pacote")
problemas = {
    "M3.01": ("'objetos soltos 741 (748.0 MB comprimidos)'", "o 'size' do count-objects é espaço alocado no exFAT (cluster de 1 MB); os 741 objetos somam 22.45 MB "
              "(stat); e 'dos quais _arquivo_v* 33.4 MB' atribui cada blob ao 1º caminho que o rev-list mostra, não a bytes exclusivos (que são 0)"),
    "M4.01": ("'lidos por script': 14 arquivos", "só 5 são lidos (sidra JSON, INTERGROWTH CSV, rl_municip_regsaud.csv, tb_regsaud.csv, tb_municip.csv); a busca por "
              "nome/radical em todo o texto dos scripts conta citações em docstring/MANIFEST e o próprio etapa7c6_02 (que cita os nomes), e pega .txt/.xml pelo radical"),
    "M5.01": ("'lido por script: True'", "falso positivo: o único script com 'evans2024' é o próprio etapa7c6_02_audita_final.py (grep -rl evans2024 scripts)"),
}
ress = {"M1.02": "rótulo 'dot_clean só no etapa7b_04', mas o detalhe lista também o etapa7b_checa (que só menciona o comando)",
        "L1.04": "confere só que o texto da verificação aparece no RESUMO, não o valor (o meu L2b.05 conferiu os dois)",
        "L9.01": "lê ~/.claude/…/memory (fora do projeto): não verificado por regra; não roda num clone",
        "K4.01": "verdadeiro às 11:22:31; falso hoje (ver R2.02.05)"}
reg("R2.02.04", False,
    "dos 50 True, 44 conferem com a minha evidência da rodada 1 (K1–K4, L1–L7, M1.01, M2.01, M3.02, M6.01, M7.01, M8.01, M9.01, M10.01, nos respectivos corpora). "
    "Três trazem FATO ERRADO no detalhe (ok=True porque são levantamento): " + "; ".join(f"{k} {a} — {b}" for k, (a, b) in problemas.items())
    + ". O RESUMO 7c.6b não usou esses três detalhes (usou os números do auditor), mas o CSV vai para o git. Ressalvas: " + "; ".join(f"{k}: {v}" for k, v in ress.items()))
re_ = {r["verificacao"].split()[0]: r for r in csv.DictReader(io.StringIO(ler(AQUI / "audita_final_reexecucao_auditor_r2_v1_20261010.csv")))}
mud = [k for k in AUd if AUd[k]["ok"] != re_[k]["ok"]]
reg("R2.02.05", False,
    f"a autoauditoria não reproduz hoje: (1) o original para com CalledProcessError no L4.01 — ele pega todo scripts/resumos/*.py exceto o etapa7c6_01 e faz "
    f"'git show 8314417:scripts/<nome>'; o etapa7c6b_01_resumo.py (criado 11:29:50, depois da execução de 11:22:31) não existe em 8314417. (2) Com o contorno do "
    f"auditor (excluir também o etapa7c6b_01 no L4.01), dá {sum(r['ok'] == 'True' for r in re_.values())}/{len(re_)}: mudam {mud} — K4.01 (ATRIBUICAO modificado e 3 "
    f"arquivos novos da 7c.6b fora do conjunto MEU), L7.01 (a lista de scripts/resumos da seção 5 agora tem 12 .py, mesmo com o ATRIBUICAO fixado em {HEAD}) e "
    f"L9.01 (arquivo fora do projeto não lido pelo auditor). O 50/57 é um retrato das 11:22:31 e também não se repetirá depois do commit da 7c.6b")

# ===================================================== R2.03 errata
er = [l for l in R6B.split("## 3. Errata do RESUMO 7c.6")[1].split("## 4.")[0].splitlines() if l.startswith("| ") and not l.startswith("| Onde")]
er = [[c.strip() for c in l.strip().strip("|").split("|")] for l in er]
r1 = lambda k: R1[k]["ok"]
evid = [
    ("L1.49", r1("L1.49") == "False" and "if aud76.exists()" in er[0][2] and "outputs/tables/" in er[0][2]),
    ("L1.53", r1("L1.53") == "False" and "tab_e3_03a_indice_continuo_rs" in er[1][2] and "A contagem e o commit estão certos" in er[1][2]),
    ("L2c.05", r1("L2c.05") == "False" and "PMC4595218" in er[2][2] and "não muda" in er[2][2]),
    ("L1.09/L1.06", "12 arquivos diferem em bytes" in er[3][2]),
    ("L1.13", "41 vezes" in er[4][2]),
    ("L1.34", "código" in er[5][2]),
    ("M1.01", "**37**" in er[6][2] and "data/processed" in er[6][2]),
    ("L5.03", "linha 526" in er[7][2]),
]
reg("R2.03.01", len(er) == 8 and all(v for _, v in evid),
    f"errata (8 linhas) × achados: " + "; ".join(f"linha {i + 1} ↔ {k}: {v}" for i, (k, v) in enumerate(evid))
    + ". Números citados conferidos: 12 arquivos diferentes em bytes entre _arquivo_v10 e v11 (46 comparados; MANIFEST, data_code, legendas, docx, 3 xlsx, 5 PDFs); "
      "41 chamadas B.rd() em 38 linhas, todas antes da L560 (S8); 37 ._* (36 + 1 em data/processed); checa L526")
reg("R2.03.02", True,
    "nada que eu achei sobre o RESUMO 7c.6 ficou de fora: as 3 falhas, as 4 ressalvas que são imprecisões do RESUMO (L1.09, L1.13, L1.34, L5.03) e o fato do M1.01 "
    "estão na errata; o empate de colunas (L1.27), o LEIAME (L1.17) e os 4 não verificáveis estão na seção 2 do RESUMO 7c.6b. Nada exagerado: a errata não diz que "
    "algum número mudou, mantém 'a contagem e o commit estão certos' e 'a conclusão (CC BY 4.0) não muda'. Detalhe de redação na linha 4: '(12 arquivos diferem em "
    "bytes)' vem depois de 'metadados dos xlsx e PDFs', mas os 12 incluem também os 3 .md e o docx de rótulo de versão")

# ===================================================== R2.04 fatos das seções 1, 2, 4 e 5
sec = lambda n: R6B.split(f"## {n}.")[1].split("\n## ")[0]
AUc = Counter(r["verificacao"][0] for r in AU)
AUo = Counter(r["verificacao"][0] for r in AU if r["ok"] == "True")
t1 = dict(re.findall(r"^\| ([KLM])\. [^|]*\|\s*(\d+)\s*\|", sec(1), re.M))
reg("R2.04.01", "**50/57 OK**" in sec(1) and {k: int(v) for k, v in t1.items()} == dict(AUc) and sum(AUo.values()) == 50
    and all(f in sec(1) for f in ["L4.05", "L8.01", "L10.01", "L10.02", "L10.03", "L10.04", "L10.05"]),
    f"seção 1: 50/57, blocos {dict(AUc)} (OK {dict(AUo)}) e a tabela das 7 falhas = CSV da autoauditoria. Não verificáveis (versões anteriores não guardadas): "
    f"'na primeira versão fechou em 51/51', 'L8.01 dava avisado', e os 3 erros do conferidor corrigidos; o código atual é coerente com a correção (hora local via "
    f"fromisoformat sem fuso, ALIAS com 3 etiquetas, contagem em rl_municip_regsaud)")
reg("R2.04.02", "**113/116 OK.**" in sec(2) and "| K. Integridade do commit b9d6272 e do amend    | 11 " in sec(2),
    "seção 2 = CSV da rodada 1 (113/116; 11/11, 80/77, 25/25; as 3 falhas; ressalvas e não verificáveis). Omissões menores: das exceções à independência, cita 2 das 4 "
    "registradas no meu relatório (faltam a leitura interna do checa pelo gerador no L3 e a contagem de etiquetas de log do L1.54). Ao regenerar depois desta rodada, "
    "'sem ler os resultados da autoauditoria' deixa de valer para a rodada 2, em que a leitura foi liberada")
pack = int(subprocess.run("git -C /Volumes/Forja/ptb-racial-brasil rev-list --objects --all | git -C /Volumes/Forja/ptb-racial-brasil pack-objects --stdout -q | wc -c",
                          shell=True, capture_output=True, text=True).stdout.strip())
arv = {c: sum(int(l.split()[3]) for l in git("ls-tree", "-r", "-l", c).splitlines()) for c in ("c8eddce", "8314417", HEAD)}
reg("R2.04.03", False,
    f"seção 4, item 3: '9.5 MB empacotado' confere ({pack:,} bytes por git pack-objects --stdout, sem gravar no .git); 22.45 MB e 44.7 MB conferem (44.7 com --all; "
    f"44.8 incluindo os commits só do reflog); 4.8 MB e 0 bytes exclusivos dos _arquivo_v* conferem. ERRADO: 'os \"~131 MB\" anotados antes são efeito do cluster "
    f"de 1 MB do exFAT'. O ~131 MB do RESUMO 7c.5b ('o conteúdo atual soma cerca de 131 MB') é o tamanho lógico real da árvore versionada naquele momento: soma dos "
    f"arquivos de c8eddce = {arv['c8eddce'] / 1e6:.1f} MB (8314417: {arv['8314417'] / 1e6:.1f} MB; {HEAD}: {arv[HEAD] / 1e6:.1f} MB). Só os 748 MiB são efeito do exFAT. "
    f"Um clone faz checkout de ~166 MB; o histórico é que comprime para 9.5 MB")
ig = [PROJ / p for p in git("ls-files", "-o", "-i", "--exclude-standard", "audit_independente").split() if p.endswith(".csv") and "etapa7c6_final" not in p]
comp = sorted(p for p in ig if p.name.startswith("comparacao"))
reg("R2.04.04", False,
    f"seção 4, item 6 e seção 5, decisão 4: (a) '113,540 células com contagem 1' é ERRO MEU (relatório e resposta da rodada 1), que o RESUMO copiou: o número somava a "
    f"coluna 'k' de etapa3/boot_contagens_r1a20 (vezes que um município foi sorteado num bootstrap, não uma contagem de nascimentos). O valor certo, que já estava no "
    f"meu CSV (M6.03), é 72,415 células com contagem 1 em 43 arquivos com coluna n/N: 65,178 no único arquivo municipal (etapa2/agregado_m2_raca_idade_ano_macro_mun.csv) "
    f"e 7,237 em arquivos por região de saúde (etapa6/cel_*). Logo 'em nível de município' (decisão 4) vale para 65,178. (b) 'os 10 comparacao_*.csv … (até 34 KB)': "
    f"fora da minha pasta são {len(comp)} ({', '.join(p.parent.name + '/' + p.name.replace('_v1_20261009', '') for p in comp)}), até "
    f"{max(p.stat().st_size for p in comp):,} bytes; com o desta auditoria, 12 (o meu tem {(AQUI / 'comparacao_7c6_final_v1_20261010.csv').stat().st_size:,} bytes). "
    f"(c) 'o checa lê 8, sempre com if exists()' confere; 'o gerador da 7c.6 lê 1, sem condição' confere, mas falta o gerador novo da 7c.6b, que lê sem condição o CSV "
    f"desta auditoria (ignorado pelo .gitignore) e portanto também falha num clone limpo")
reg("R2.04.05", True,
    "seção 4, itens 1, 2, 4, 5, 7, 8 e 9 conferem: 37 ._* = 34 PDF + 1 CSV + 1 log + 1 parquet em data/processed; nenhum versionado; .gitignore cobre; 34 PDFs com "
    "com.apple.quarantine; dot_clean só no etapa7b_04 sobre Submissao/; docstring (2,607 de 2014; sem região); nenhum número-chave do etapa2_03; 93 arquivos, 23.8 MB, "
    "5 lidos; só a licença do RECORD registrada; Evans (SSM Popul Health 2024;26:101664; PMC CC BY 4.0; nenhum script lê); 'among births with known month of prenatal "
    "care initiation' 22 vezes em 4 arquivos; 'first visit' 0; CE 17.5%, DF 16.9%, PB 7.8%; CE 5 regiões com município (184 municípios), DF 1; 6 de 433; 433 → 427; "
    "25/8 em tb_regsaud; Tabela 4 com os 2 Wald da PTB total em 'n.a.' sem explicação no rodapé. Omissão menor no item 1: o gerador da 7c.5 também conta os ._* "
    "(scripts/resumos/etapa7c5_01_resumo.py:25), não só o da 7c.6")
reg("R2.04.06", False,
    "seção 4, item 10: PR 379, RR 0, mesma definição de 'provider-initiated' conferem. Redação errada: 'SGA aparece 592 vezes, das quais só 3 por extenso' — as 3 "
    "ocorrências de 'small for gestational age' não estão entre as 592 de 'SGA' (contagens separadas: 592 siglas e mais 3 por extenso)")
reg("R2.04.07", False,
    "seção 5, decisão 1: 'nas 35 tabelas lidas direto, o log do próprio script tem o mesmo segundo da tabela' vale para 34; em tab07_fluxograma_motivos o log do "
    "04_fluxograma está 2 s antes do mtime (todas a ≤3 s, como no meu L1.32). Os outros fatos da decisão 1 conferem (226 ids reproduzidos; 3092186 como commit_registro)")
reg("R2.04.08", False,
    "seção 5, decisão 4 (INTERGROWTH): 'Ele só valida o PIG, que é calculado pelo pacote gigs' é incompleto: o CSV também define a variável de sensibilidade "
    "pig_tabela_oficial (etapa1_01_base_v2.py L78–L80; usada no etapa1_05b e listada na S7b como 'sensitivity') e é entrada obrigatória do etapa1_02b_pig_grade.R "
    "(L22, stopifnot), que gera a grade de centis usada pelo PIG principal. O PIG principal é mesmo calculado pelo gigs (centil_k3). Demais fatos da decisão 4 "
    "conferem: 9.5 MB, nenhum blob > 5 MB, hashes citados no JSON e na disponibilidade, 3 arquivos da base territorial + SIDRA lidos, Evans não lido")
reg("R2.04.09", False,
    "seção 5, decisão 7: 'O gerador lê o ATRIBUICAO.txt e os ._* do disco, por isso já não reproduz o RESUMO 7c.6 … depois da correção do ATRIBUICAO' e 'a "
    "autoauditoria confere contra o texto de b9d6272'. Incompleto/desatualizado: o gerador também lista scripts/resumos/*.py (seção 5 do RESUMO), e com o "
    "etapa7c6b_01_resumo.py novo a linha 245 muda mesmo com o ATRIBUICAO de b9d6272 (R2.01.03; reexecução da autoauditoria: L7.01 False). E a autoauditoria, como "
    "está, nem roda (R2.02.05)")
reg("R2.04.10", True,
    "seção 5, demais fatos conferem: decisão 2 (36 fora de data/; o ._*.csv de outputs/tables casa com glob('*.csv') do pathlib; o gerador da 7c.6 passaria a mostrar "
    "0); decisão 3 (o Online Resource 2/S7 cita scripts/etapa2_03_indice_acesso.py e diz 'Codes as implemented in the analysis scripts'; nenhum número nem campo de "
    "commit muda — meu M2.03); decisão 6 (checa L526); redação 1 (22 vezes); redação 3 (Res. CNS 510/2016, art. 1º, parágrafo único: 'Não serão registradas nem "
    "avaliadas pelo sistema CEP/CONEP' — incisos II, informações de acesso público, e V, bancos de dados agregados sem identificação individual; texto oficial "
    "baixado do gov.br em 2026-10-10); redação 5 (nascidos vivos; PR em todo o pacote); redação 7 (as tabelas de origem da imputação, tab_e4_06_mi_*_rubin_rs, não "
    "têm Wald; PR e IC estão na Tabela 4); redação 8 (5 no CE, 1 no DF). Não verificáveis: RSP 2026;60:e44 e 'a mesma [redação] da RSP 2026'")
n_dec = len(re.findall(r"^\d\. \*\*", R6B.split("### Decisões")[1].split("### Redação")[0], re.M))
n_red = len(re.findall(r"^\d\. \*\*", R6B.split("### Redação")[1].split("## Pendências")[0], re.M))
reg("R2.04.11", f"as {n_dec} decisões" in R6B and n_red == 8,
    f"Pendências: 'as 8 decisões e os 8 itens de redação da seção 5' — a seção 5 tem {n_dec} decisões (1–7) e {n_red} itens de redação")

# ===================================================== R2.05 gerador da 7c.6b
copia = ler(AQUI / "etapa7c6b_01_resumo_copia_saida_auditor.py")
orig = ler(PROJ / "scripts/resumos/etapa7c6b_01_resumo.py")
dif = [l for l in __import__("difflib").unified_diff(orig.splitlines(), copia.splitlines(), lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---")]
rep = (AQUI / "RESUMO_ETAPA7C6b_reproduzido_r2_v1_20261010.md").read_bytes()
reg("R2.05.01", len(dif) == 2 and rep == (PROJ / "outputs/RESUMO_ETAPA7C6b_v1_20261010.md").read_bytes(),
    f"cópia do gerador difere só na linha de saída ({len(dif)} linhas ±); rodada da raiz com PYTHONPATH=scripts em 2026-10-10 16:19:52, ANTES de acrescentar as "
    f"linhas R2, com o CSV desta pasta no estado da rodada 1 (MD5 {MD5_R1}, 116 linhas): saída idêntica byte a byte ao RESUMO 7c.6b do disco (MD5 {md5(rep)}). "
    f"O Logger acrescentou 1 linha em outputs/logs/etapa7c6_20261008.log. Depois desta rodada o gerador muda de saída (lê este CSV: entra o bloco R e as falhas R2)")

# ===================================================== R2.06 triagem do que vai para o git
st = git("--no-optional-locks", "status", "--porcelain", "--untracked-files=all").splitlines()
cand = [l[3:] for l in st if not l[3:].startswith("docs/referencias/") or l[3:] == "docs/referencias/ATRIBUICAO.txt"]
cand = [p for p in cand if subprocess.run(["git", "-C", str(PROJ), "check-ignore", "-q", p]).returncode != 0]
PAD = {"data_1900_2024": r"(?<!\d)(0[1-9]|[12]\d|3[01])/(0[1-9]|1[0-2])/(19\d\d|20[01]\d|202[0-4])(?!\d)|(?<!\d)(19\d\d|20[01]\d|202[0-4])-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])(?!\d)",
       "cns15": r"(?<![\d.,])[12789]\d{14}(?![\d.,])", "cpf": r"(?<!\d)\d{3}\.\d{3}\.\d{3}-\d{2}(?!\d)",
       "linha_de_log": r"^\[\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\] \[[^\]]+\] .*\d"}
IDC = re.compile(r"\b(DTNASC|HORANASC|NUMERODN|NUMERODO|CODESTAB|CNES|DTOBITO|DTNASCMAE|CPF|CNS)\b")
achados, cols = {}, {}
for p in cand:
    f = PROJ / p
    t = f.read_text(encoding="utf-8", errors="replace")
    h = {k: len(re.findall(v, t, re.M)) for k, v in PAD.items()}
    h = {k: v for k, v in h.items() if v}
    if h:
        achados[p] = h
    if p.endswith(".csv"):
        cols[p] = next(csv.reader(io.StringIO(t)))
susp_cols = {p: [c for c in v if IDC.search(c)] for p, v in cols.items() if any(IDC.search(c) for c in v)}
reg("R2.06.01", not susp_cols and set(achados) <= {"audit_independente/etapa7c6_final/audita_7c6_final_K_v1_20261010.py",
                                                   "audit_independente/etapa7c6_final/audita_7c6_final_excecao_L2b_v1_20261010.py",
                                                   "audit_independente/etapa7c6_final/audita_7c6_final_R2_v1_20261010.py"},
    f"{len(cand)} arquivos novos/modificados fora do .gitignore ({sum(p.startswith('audit_independente/') for p in cand)} desta pasta: .py, .md, .json; os CSV daqui "
    f"são ignorados). Padrões de data 1900–2024, CNS de 15 dígitos, CPF e linha de log com número: {achados or 'nenhum'}. CSV não ignorado: {list(cols)} com colunas {list(cols.values())}; nomes de identificador: "
    f"{susp_cols or 'nenhum'}. Nenhuma linha de microdado nem contagem fina copiada de log: as contagens citadas são agregados (ex.: 2,607 de 2014; 65,178 células "
    f"com contagem 1 descritas como número, sem as células)")

# ===================================================== R2.07 nada mais mudou; pacote intacto
mod = [l for l in st if not l.startswith("??")]
nao = sorted(l[3:] for l in st if l.startswith("??") and not l[3:].startswith(("docs/referencias/", "audit_independente/etapa7c6_final/")))
esperado = {"outputs/RESUMO_ETAPA7C6b_v1_20261010.md", "outputs/manuscrito/_resumo7c6b_texto_v1_20261010.md", "outputs/manuscrito/audita_final_7c6_v1_20261010.csv",
            "scripts/etapa7c6_02_audita_final.py", "scripts/resumos/etapa7c6b_01_resumo.py"}
n_ref = sum(1 for l in st if l.startswith("?? docs/referencias/"))
reg("R2.07.01", mod == [" M docs/referencias/ATRIBUICAO.txt"] and set(nao) == esperado and n_ref == 93
    and git("rev-parse", "--short", "HEAD").strip() == HEAD,
    f"git status: rastreados modificados {mod}; não rastreados novos {nao} (= os 5 listados pelo coordenador); docs/referencias/ não rastreados: {n_ref} (os 93 da "
    f"rodada 1); HEAD = {HEAD}; reflog sem entrada nova. Ignorados que mudaram desde {HEAD} (find -newermt): só outputs/logs/etapa7c6_20261008.log (linhas do autor "
    f"às 11:22:29 e 16:11:12; minhas às 16:19:52, 17:51:20 e 17:57:36). Nada em data/, outputs/tables/ ou Submissao/")
pac = ["outputs/manuscrito/tabelas", "outputs/manuscrito/suplementar", "outputs/manuscrito/figuras", "Submissao",
       f"outputs/manuscrito/numeros_chave_v11_20261009.json", "outputs/manuscrito/numeros_chave_v11_20261009.md"]
dq = subprocess.run(["git", "-C", str(PROJ), "--no-optional-locks", "diff", "--quiet", HEAD, "--", *pac]).returncode
extra = [p for p in git("ls-files", "-o", "--exclude-standard", *pac).split()]
ign_new = [p for p in git("ls-files", "-o", "-i", "--exclude-standard", *pac).split()
           if (PROJ / p).stat().st_mtime > int(git("log", "-1", "--format=%ct", HEAD).strip())]
reg("R2.07.02", dq == 0 and not extra and not ign_new,
    f"pacote (tabelas/, suplementar/, figuras/, numeros_chave_v11 .json/.md, Submissao/): git diff contra {HEAD} vazio: {dq == 0}; arquivos não rastreados: "
    f"{extra or 'nenhum'}; ignorados criados/alterados depois do commit: {ign_new or 'nenhum'} (os ._* existentes são anteriores)")

# ===================================================== R2.00 erro do próprio auditor (rodada 1)
reg("R2.00", False,
    "ERRATA DO AUDITOR (rodada 1): o relatório (seção M6) e a resposta final da rodada 1 disseram '113.540 células com contagem 1 em 44 arquivos'. O número vinha de "
    "uma execução intermediária que contava também a coluna 'k' de etapa3/boot_contagens_r1a20_v1_20261008.csv (vezes que um município foi sorteado num bootstrap, "
    "não nascimentos: audit_independente/etapa3/auditoria_etapa3_sorteio_v1_20261008.py). A linha M6.03 do CSV final já trazia o valor certo: 72,415 em 43 arquivos "
    "(65,178 no arquivo municipal). O RESUMO 7c.6b copiou o 113,540 (R2.04.04). As linhas da rodada 1 do CSV não foram alteradas; o relatório recebe a correção na "
    "seção Rodada 2")

# ===================================================== gravação: preserva a rodada 1 byte a byte
bruto = CSV_.read_bytes()
i = bruto.find(b"\nR2.")
r1_bytes = bruto if i < 0 else bruto[:i + 1]
assert md5(r1_bytes) == MD5_R1, "a parte da rodada 1 do CSV mudou"
buf = io.StringIO()
w = csv.DictWriter(buf, fieldnames=["verificacao", "ok", "detalhe"], lineterminator="\r\n")
ordem = lambda v: [int(x) if x.isdigit() else x for x in re.findall(r"\d+|[A-Za-z]+", v)]
w.writerows(sorted(ROWS, key=lambda r: ordem(r["verificacao"])))
CSV_.write_bytes(r1_bytes + buf.getvalue().encode("utf-8"))
print(f"rodada 2: {sum(r['ok'] for r in ROWS)}/{len(ROWS)} OK; CSV com {len(R1)} + {len(ROWS)} linhas")

