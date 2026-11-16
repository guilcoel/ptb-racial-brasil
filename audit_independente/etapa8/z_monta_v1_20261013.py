"""Monta comparacao_8_v1_20261013.csv a partir dos res_*.json dos blocos e das linhas de revisão manual (E6, H2, Z)."""
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, "/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa8")
import csv
import json

from comum_v1_20261013 import AUD

linhas = []
for b in ("A", "B", "C1", "C2", "D", "E", "F", "G", "H", "I"):
    linhas += json.load(open(AUD / f"res_{b.lower()}_r1_v1_20261013.json"))
man = [
    ("E6.01 diff da etapa7b_lib contra dc54fb9: só V = v13, as 5 tabelas da Etapa 8 no SRC e o cabeçalho 'Etapas 7b–8' do .md dos números-chave", True, "revisão do diff"),
    ("E6.02 diff do etapa7b_01: NOTA_NA antes de 'Sources:' no rodapé da Tabela 4 e os 21 números-chave da Etapa 8 (lidos de tab_e8_03/04)", True, "revisão do diff"),
    ("E6.03 diff do etapa7b_02: colunas (d)/(e) e rodapé da S2b; fonte nova e declaração na disponibilidade (com assert de data única no ACESSO)", True, "revisão do diff"),
    ("E6.04 diff do etapa7b_04: docstring, origem da S2b, título/histórico do MANIFEST com o título exato do commit da Etapa 8", True, "revisão do diff"),
    ("E6.05 diff do checa: 9h passa a comparar v11 × v12 arquivadas; 9i novo (15 verificações); compara() com novas_cols; nada mais", True, "revisão do diff; mutações em E3"),
    ("E6.06 etapa8_01: nunca sobrescreve o bruto (se existe, só confere), grava .part e renomeia, valida campos/UF/84 competências; só metadados no ACESSO", True, "leitura do script"),
    ("E6.07 etapa8_02/03/04: só leem o bruto/parquet e gravam agregados (região × ano; estimativas); o 03 grava n e casos por macro × raça × tercil "
     "em outputs/tables (ignorado; 1 célula pequena sinalizada), como o tab_e3_01 já fazia", True, "leitura dos scripts"),
    ("H2.01 desenho = o aprovado: t−1 com média de 12 meses ponderada por qtPopulacao, mapa dez/2024, 2015–2021, tercis intra-macro (algoritmo do etapa3_01), "
     "comparador recalculado na mesma amostra, mesmo modelo/EP (G = 433), 3 desfechos, IC Ind×T1 e Wald 2 gl, S2b (d)/(e), v13, nota n.a.", True, "B3.04, C1, C2"),
    ("H2.02 [ressalva] 'cobertura mede oferta, não uso': verdadeiro por definição e apoiado (ρ −0.10; κ 0.05), mas o ρ nacional mistura macros: dentro das "
     "macros (escala dos tercis) ρ = 0.05 a 0.30 em CO/N/NE/S e −0.18 no SE; postos intra-macro 0.07", True, "C1.06, C1.07"),
    ("H2.03 [ressalva] 'a modificação de efeito indígena some' / sugestão 'were not modified by access tertile' é forte demais: IC largos (PTB −3.11, "
     "−6.30 a 0.07; PIG 1.35, −1.94 a 4.65) e só 16.2% dos indígenas no T1 da cobertura; ausência de evidência, não evidência de ausência", True, "C2, C1.09"),
    ("H2.04 [ressalva] com a cobertura, o Wald de 6 gl é significativo em PTB (p = 0.0037) e PTB indicado (p = 0.016): há modificação por cobertura em "
     "termos de outras raças; a S2b/RESUMO só mostram o Wald indígena de 2 gl", True, "tab_e8_04_wald; meu R"),
    ("H2.05 [ressalva] rodapé da S2b e RESUMO descrevem a cobertura como ESF + eAB parametrizadas; a série soma também as equipes equivalentes por carga "
     "horária (qtEAbEquivalenteCh/CH), 14.8% da população coberta somada", True, "B2.03"),
    ("H2.06 [ressalva] teto de 100%: 69.4% dos registros municipais em 100%, mas só 16% dos pares região × ano ≥ 99% e 6.3% dos nascimentos; no NE o T3 "
     "começa em 95.7% e 53% dos nascimentos do T3 estão ≥ 99% (T3 comprimido no teto)", True, "B1.06, H1.01–H1.02"),
    ("H2.07 populações: qtPopulacao = estimativa do ano anterior à competência (2014 usa 2013 ... 2020 usa 2019), constante nos 12 meses; peso populacional, "
     "não de nascimentos (decisão aprovada)", True, "B3.06, B3.07"),
    ("H2.08 mapa dez/2024 para 2014–2020: todos os 5,570 municípios do JSON mapeiam; só 510183 (criado depois, sem nascimentos) fica sem registro", True, "B3.01–B3.03"),
    ("H2.09 qtCoberturaAb descartada com razão: 3,170 registros ~100× menores; o pcCoberturaAb bate com a fórmula de equipes em 99.2%", True, "B2.01–B2.03"),
    ("H2.10 [ressalva menor] o rodapé da S2b dá o N só da PTB total (18,624,544); PIG 18,057,044 e PTB indicado 18,519,393 não aparecem", True, "tab_e8_04_wald"),
    ("H2.11 o comparador (e) reproduz a direção e a significância da principal (PIG 5.09 vs 4.44; PTB ind −1.22 vs −1.59; PTB 1.15 vs 1.47, Wald p 0.0008 vs 0.0023)",
     True, "C2.06"),
    ("Z1.01 autoauditoria lida só agora: 65/65 OK; não pega G2.07 (o LEIAME falso está codificado como troca esperada em TROCAS do etapa8_05), "
     "G1.02 (agrupamento da rodada 2 no gerador), D4.05/H2.05 (equipes equivalentes) nem as ressalvas H2.02–H2.06 e F1.07", True, "comparação manual"),
    ("Z1.02 autoauditoria refaz os 6 modelos com statsmodels e compara com tolerância (limites |Δ| até 1.2e-3 p.p.; Wald rel. 7.1e-4); meu R com a mesma "
     "correção documentada bate a < 1e-10 e também refaz a análise principal (C2.04), que a autoauditoria não refaz", True, "C2.01–C2.04"),
    ("Z1.03 audita_8_v1_20261013.csv (entra no commit): 65 linhas, só verificações e agregados; nenhuma coluna ou célula de microdado", True, "leitura no bloco Z"),
]
linhas += [dict(verificacao=v, ok=o, detalhe=d) for v, o, d in man]
with open(AUD / "comparacao_8_v1_20261013.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["verificacao", "ok", "detalhe"])
    w.writeheader()
    for l in linhas:
        w.writerow(dict(verificacao=l["verificacao"], ok=l["ok"], detalhe=l["detalhe"]))
from collections import Counter
tot = Counter(l["verificacao"][0] for l in linhas)
okc = Counter(l["verificacao"][0] for l in linhas if l["ok"])
print({k: f"{okc[k]}/{tot[k]}" for k in sorted(tot)}, f"total {sum(okc.values())}/{len(linhas)}")
print([l["verificacao"][:90] for l in linhas if not l["ok"]])
