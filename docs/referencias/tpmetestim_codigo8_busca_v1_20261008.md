# TPMETESTIM = 8 — busca de documentação oficial (Etapa 6.2c, 2026-10-08)

## Fontes consultadas

| Fonte | URL | Acesso | Conteúdo sobre TPMETESTIM |
|---|---|---|---|
| CGIAE/SVS/MS, "SINASC: Estrutura de 1996 a 2019 — Dicionário de Dados" (cópia salva: `SINASC_Estrutura_CGIAE_diaad_acesso20261008.pdf`, MD5 c93cc52553678e5aeb6a8ecb76c6a39a) | https://diaad.s3.sa-east-1.amazonaws.com/sinasc/SINASC+-+Estrutura.pdf | 2026-10-08 | Campo 48: "Método utilizado. Valores: 1– Exame físico; 2– Outro método; 9– Ignorado." O código 8 não aparece. |
| CGIAE, estrutura já no projeto (`SINASC_Estrutura_2024.pdf`) | (Etapa 0) | — | Mesmo texto: só 1, 2 e 9. |
| MS/SVS/DAENT, "Declaração de Nascido Vivo — Manual de instruções para preenchimento", 4ª ed., Brasília, 2022 (cópia salva: `Manual_preenchimento_DN_govbr_acesso20261008.pdf`, MD5 c23e29dc812dc6b605acef679d51b535) | https://www.gov.br/saude/pt-br/centrais-de-conteudo/publicacoes/svsa/vigilancia/declaracao-de-nascido-vivo-manual-de-instrucoes-para-preenchimento | 2026-10-08 | Campo 31, DUM. Campo 32: "Número de semanas de gestação, se a DUM for 'Ignorada' … só é necessário quando a DUM for ignorada". "Método utilizado para estimar … quando a DUM for ignorada. As opções são exame físico, outro método e ignorado. Se o método adotado … for ultrassonografia, usar a categoria 'Outro método'". O código 8 não aparece. |
| microdatasus (R), `process_sinasc.R` | https://raw.githubusercontent.com/rfsaldanha/microdatasus/master/R/process_sinasc.R | 2026-10-08 | TPMETESTIM só é convertido para numérico, sem rótulos. |
| Dicionários municipais e estaduais (São Paulo, ES) e PCDaS/Fiocruz | resultados de busca web ("SINASC TPMETESTIM código 8 DUM") | 2026-10-08 | Só 1, 2 e 9. |
| PySUS | não consultado diretamente; o pacote baixa os .dbc sem rotular TPMETESTIM (pela documentação conhecida) | — | — |

**Resultado:** nenhuma documentação oficial do código 8 foi encontrada.

## Evidência empírica (tab_e6_02a/b)

- **2013–2024:** DTULTMENST está preenchida em 100% dos registros com código 8 (99.998% válidas) e em 0% dos registros com códigos 1, 2 e 9.
  - O código 8 aparece em 2013. Nesse ano, os 1,799,677 registros com código 8 são exatamente os 1,799,677 com DTULTMENST preenchida.
  - Em 2010–2012, TPMETESTIM é quase sempre nulo, e a DUM aparece sem código.
- **Concordância com a IG pela DUM:** com floor((DTNASC − DTULTMENST)/7), a concordância com SEMAGESTAC é 79.0% exata e 99.98% em ±1 semana (dif. média −0.02, DP 0.47).
  - A concordância exata varia com o resto de dias mod 7 (54% a 99.9%) e é menor nos anos bissextos. Isso indica que o sistema calcula as semanas a partir da DUM por um algoritmo próprio, não documentado.
  - Na fronteira de 37 semanas, as reclassificações são simétricas: a prevalência de PTB muda ≤ 0.11 p.p. em todas as raças.
- **Leitura operacional:** código 8 = "DUM informada; semanas calculadas pelo sistema", conforme o manual (o método só é preenchido quando a DUM é ignorada). "Outro método" (2) inclui ultrassonografia.
