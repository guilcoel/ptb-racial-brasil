# Auditoria independente: Etapa 8b (Wald de 6 gl da cobertura na S2b, pacote v14)

Projeto `ptb-racial-brasil`, estado ainda não commitado sobre cdddf8f. Rodada em 26/10/2026, com código próprio e somente leitura no projeto: escrevi só em `audit_independente/etapa8b/`. O detalhe de cada verificação está em `comparacao_8b_v1_20261026.csv`.

## Resumo por bloco

| Bloco | Conteúdo | N | OK |
|---|---|---|---|
| A | Git e árvore (HEAD, refs, stash, remoto, mudanças arquivo a arquivo, v13 arquivada = cdddf8f, `._*`, diffs dos scripts) | 21 | 21 |
| B | Valores: os 6 p de 6 gl recalculados de `tab_e8_04_wald`, comparados com S2b CSV/ESM_1 (pacote e Submissao), JSON/MD e a coluna certa | 16 | 16 |
| C | v13 × v14: CSV, xlsx, docx (XML), PDFs, pixels, números-chave, MANIFEST, disponibilidade, legendas | 29 | 29 |
| D | Rodapé e cabeçalhos da S2b | 7 | 7 |
| E | Sandbox: guarda, checa, commit simulado, 15 mutações, gerador do RESUMO | 24 | 23 |
| F | Logs × mtimes | 13 | 13 |
| G | RESUMO: números e leitura | 12 | 10 |
| H | Conjunto do commit (microdados, células pequenas) | 11 | 11 |
| Z | Comparação com a autoauditoria (lida só no fim) | 4 | 4 |
| **Total** | | **137** | **134** |

## Falhas

1. **G2.04: a leitura do RESUMO vai além do que os dados mostram.** O RESUMO diz que, com a cobertura, "a modificação vem, portanto, dos termos de pardas e pretas, porque o teste só dos indígenas não é significativo". Isso é uma inferência, não um teste. Um Wald indígena de 2 gl não significativo não quer dizer que os termos indígenas não contribuem.
   - Nos termos individuais da `tab_e8_04_interacao` (multiplicativos, IC 95%), na PTB total, excluem o 1: Preta×T1, Preta×T2 e também Indígena×T1 (0,79; 0,63–0,99). Nenhum termo de Parda exclui o 1.
   - Na PTB indicada, nenhum termo exclui o 1.
   - Redação sugerida: "não é explicada pelos termos indígenas (2 gl p = 0,107 e 0,481); a decomposição não foi testada".
2. **G2.05: a seção 4 do RESUMO estende a conclusão para o índice sem base.** A frase é "o Wald de 6 gl mostra modificação em outras raças, tanto com a cobertura quanto com o índice". No índice de 2015–2021, o 2 gl indígena é significativo nos três desfechos, então o 6 gl pode vir só dos termos indígenas. Na PTB total, nenhum termo não indígena exclui o 1.
3. **E3.15: ponto cego do bloco 9j.** Pus no `data_code_availability.md` o título do commit da Etapa 8 no lugar do título da 8b, e o checa não acusou. O motivo é que o 9j normaliza o título da 8b de volta para o da 8 antes de comparar, e o 7c.1 só exige que a substring "Etapa 8b" exista, o que o grep já garante. O arquivo atual está correto (C8.01).

## Pontos cegos do checa/9j (o estado atual está correto; o checa só não o protege)

- **M02:** os p de 6 gl de (d) e (e) trocados só nas células do ESM_1 passam. O 9j compara o ESM_1 só pela 1ª e pela última célula de cada aba (`abas()`). O mesmo vale para células de outras abas do ESM_1 (M09) e do `tabelas_principais.xlsx` (M10). O meu B3 e o C2 conferem essas células agora.
- **M11:** um pixel alterado na S9 (png em `suplementar/`) passa, porque o 9j só olha `figuras/`.
- **M12, M13:** o `_arquivo_v13/MANIFEST_v13` e o `numeros_chave_v13.md` arquivados podem ser alterados sem que o checa acuse. O A3.01 confere agora que os 49 arquivos arquivados têm os bytes de cdddf8f.
- As outras 8 mutações dirigidas, entre elas a troca de (d)/(e) no CSV e um número-chave a mais, são acusadas pela verificação certa.

## Ressalvas (não são erro)

- **D1.05:** o rodapé diz "the same 6 race × tertile terms as in (b)". A estrutura é a mesma (Brown, Black, Indigenous × T1, T2), mas os tercis são os da própria coluna. Sugestão: "the 6 race × tertile terms of its own tertiles".
- **D1.06:** o cabeçalho das colunas novas não traz "(6 df)", ao contrário do de (b) e dos de 2 gl.
- **G2.06 e G2.08:** "até a v13 a S2b só mostrava o 2 gl" vale para (d) e (e), não para (b). Os "rótulos" trocados incluem também as legendas e o docx.
- **E2.04:** depois do commit simulado, o checa regrava o próprio `checa_7b_v14.csv`, que fica modificado no status. Isso é esperado. O commit simulado dá 137/137 e o pai é cdddf8f.
- **C4.02:** os PDFs têm bytes diferentes (metadados), mas o mesmo texto, as mesmas páginas e o mesmo tamanho.
- **H2.03:** a busca por contagens de 1 a 9 é heurística. A garantia forte é o H2.04: os 19 CSVs da v14 fora da S2b e do checa têm os mesmos bytes dos já versionados em cdddf8f.
- **Lixeira:** o RESUMO menciona três arquivos de células em `~/.Trash` à espera de remoção manual. Não verifiquei, mas são células finas fora do Forja.
- As 38 renomeações estão staged (`git mv`). Os meus scripts e JSON em `audit_independente/etapa8b/` não são ignorados: um `git add -A` os levaria junto (os CSV são ignorados).

## O que confere

- **HEAD e repositório:** HEAD = cdddf8f, só `main`, stash vazio, sem remoto.
- **Mudanças desde cdddf8f:**
  - 12 modificados, exatamente os previstos;
  - 38 arquivos renomeados para `_arquivo_v13` (R100);
  - 11 cópias de arquivo;
  - 38 arquivos v14;
  - 5 arquivos da etapa;
  - os 93 de `docs/referencias`, anteriores ao commit.
- **v13 arquivada:** os 49 arquivos têm os bytes de cdddf8f. Não há `._*` novo.
- **Os 6 p:** recalculados de `chi2_6gl` com scipy e formatação própria, batem com o CSV, o ESM_1 do pacote e o de Submissao, o JSON e o MD. (d) recebe `tercil_aps` e (e) recebe `tercil_ind21`. Também batem com o R da auditoria da Etapa 8 (diferença relativa de 1,9e-9).
- **Fora a S2b, a v14 é a v13:** CSVs iguais byte a byte, xlsx com todas as células iguais, docx igual no XML fora o rótulo, PDFs iguais no texto, figuras iguais em pixels e bytes. Dos números-chave, os 249 da v13 estão iguais e na mesma ordem. Os 21 da Etapa 8 passam a ter os commits = cdddf8f, e mudam o commit_pacote e o MANIFEST (título e abertura).
- **checa:** 137/137 no sandbox, sem e com assert, com os mesmos rótulos do projeto. O gerador reproduz o RESUMO byte a byte.
- **Logs:** há duas rodadas de 01–04, checa e 04 (10:59–11:00 e 12:27–12:28), mais o gerador às 12:33:59. Nenhum `etapa8_0[1-4]` rodou depois de cdddf8f, e `data/` e `outputs/tables` estão intactos.

## O que não pôde ser verificado

- **Refit em R** (glm + `sandwich::vcovCL`): não existe um agregado já pronto por raça × idade × ano × região × região de saúde. A leitura do parquet foi negada pela permissão (dado pessoal), então não refiz o modelo. Uso o R da auditoria da Etapa 8 (B5.01) e o p a partir do χ² (B1.02).
- **Lixeira:** não tenho acesso a `~/.Trash`.

## Exceções à independência

- Os tercis e o modelo não foram refeitos. Os p partem da `tab_e8_04_wald` do projeto.
- O sandbox segue a ideia do da autoauditoria (clone -s, links simbólicos, audit hook, checa sem o assert), mas com código meu.
- Li o cabeçalho do `audita_8b` no bloco H e a tabela-resumo da autoauditoria dentro do RESUMO antes do bloco Z.
