"""Bloco B — bruto da cobertura e cobertura região × ano recalculada por DuckDB (read_json), mapa lido da base territorial
(docs/referencias/territorio_dez24/rl_municip_regsaud.csv), sem os scripts do projeto. Só agregados nas saídas."""
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, "/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa8")
import re

import duckdb
import numpy as np
import pandas as pd

from comum_v1_20261013 import PROJ, RAW, PROC, TB, AUD, Res, md5

R = Res("B")
con = duckdb.connect()
con.execute(f"SET temp_directory='{AUD}/duck_tmp_v1_20261013'")   # nunca fora do Forja (não deve ser usado: tudo cabe em memória)
con.execute("SET threads=4")

# B1 bruto × ACESSO.txt × manifesto
acc = (PROJ / "docs/referencias/aps_cobertura_ab/ACESSO.txt").read_text()
pares = re.findall(r"^(\S+ \S+) -03  (\S+)  \((\d+) bytes\)\nMD5 \((\S+)\) = ([0-9a-f]{32})$", acc, flags=re.M)
arqs = sorted(p.name for p in RAW.glob("cobertura_ab_uf*.json"))
ok_md5 = [(a, int(b) == (RAW / a).stat().st_size and h == md5(RAW / a)) for _, _, b, a, h in pares]
R.ok("B1.01 27 JSON: nomes = ACESSO.txt; tamanho e MD5 de cada um = ACESSO.txt", len(pares) == 27 and sorted(a for a, _ in ok_md5) == arqs
     and all(o for _, o in ok_md5), f"{len(pares)} no ACESSO; {len(arqs)} no disco; divergentes {[a for a, o in ok_md5 if not o]}")
man = pd.read_csv(RAW / "manifesto_cobertura_ab_v1_20261013.csv", dtype=str)
R.ok("B1.02 manifesto = ACESSO.txt (arquivo, bytes, MD5, URL, data) e status 'baixado' nas 27 UFs",
     sorted(zip(man.arquivo, man.bytes, man.md5, man.url)) == sorted((a, b, h, u) for _, u, b, a, h in pares)
     and (man.status == "baixado").all() and sorted(man.quando) == sorted(q for q, *_ in pares), man.status.value_counts().to_dict())
urls_ok = all(re.fullmatch(rf"https://relatorioaps-prd\.saude\.gov\.br/cobertura/ab\?unidadeGeografica=MUNICIPIO&coUf={int(a[15:17])}"
                           r"&nuCompInicio=201401&nuCompFim=202012", u) for _, u, _, a, _ in pares)
R.ok("B1.03 URL de cada UF = consulta municipal 201401–202012 da UF do nome do arquivo", urls_ok)
tot = re.search(r"Total: 27 UFs; ([\d,]+) registros; ([\d,]+) municípios; ([\d,]+) bytes", acc).groups()

glob = str(RAW / "cobertura_ab_uf*_201401_202012.json")
con.execute(f"""CREATE TABLE j AS SELECT *, filename AS arq FROM read_json('{glob}', format='array', columns={{
  nuComp:'VARCHAR', coUfIbge:'VARCHAR', coMunicipioIbge:'VARCHAR', qtPopulacao:'VARCHAR', pcCoberturaAb:'VARCHAR',
  qtCoberturaAb:'VARCHAR', qtEsf:'VARCHAR', qtEAbParametrizada:'VARCHAR', qtEAbEquivalenteCh:'VARCHAR', qtCoberturaSf:'VARCHAR',
  pcCoberturaSf:'VARCHAR', nuAnoPopulacaoConsiderada:'VARCHAR'}}, filename=true)""")
con.execute("""CREATE TABLE c AS SELECT nuComp, CAST(substr(nuComp,1,4) AS INT) ano, coUfIbge uf, coMunicipioIbge mun, arq,
  CAST(replace(qtPopulacao, ',', '') AS DOUBLE) pop, CAST(replace(pcCoberturaAb, ',', '') AS DOUBLE) pc,
  CAST(replace(qtCoberturaAb, ',', '') AS DOUBLE) qcob, CAST(replace(qtEsf, ',', '') AS DOUBLE) esf,
  CAST(replace(qtEAbParametrizada, ',', '') AS DOUBLE) eabp, CAST(replace(qtEAbEquivalenteCh, ',', '') AS DOUBLE) eabeq,
  qtCoberturaAb qcob_txt, qtPopulacao pop_txt FROM j""")
n, nm, ncomp, ndup = con.execute("SELECT count(*), count(DISTINCT mun), count(DISTINCT nuComp), count(*) - count(DISTINCT mun || nuComp) FROM c").fetchone()
R.ok("B1.04 467,880 registros = 5,570 municípios × 84 competências (201401–202012), sem duplicata; = total do ACESSO.txt",
     n == 467880 and nm == 5570 and ncomp == 84 and ndup == 0 and tot[:2] == ("467,880", "5,570"), f"{n:,} registros; {nm} municípios; {ncomp} competências; dup {ndup}")
x = con.execute("""SELECT max(cnt), min(cnt) FROM (SELECT mun, count(*) cnt FROM c GROUP BY mun)""").fetchone()
y = con.execute("SELECT count(*) FROM c WHERE uf <> substr(regexp_extract(arq, 'uf(\\d\\d)_', 1), 1, 2) OR substr(mun,1,2) <> uf").fetchone()[0]
R.ok("B1.05 cada município com as 84 competências; cada arquivo só com a UF do nome", x == (84, 84) and y == 0, f"min/max {x}; fora da UF {y}")
z = con.execute("SELECT count(*) FILTER (WHERE pc IS NULL OR pc < 0 OR pc > 100), count(*) FILTER (WHERE pop IS NULL OR pop <= 0), "
                "count(*) FILTER (WHERE pc = 100), min(pc) FROM c").fetchone()
R.ok("B1.06 pcCoberturaAb sempre em 0–100 e população > 0 (teto de 100% atingido em parte dos registros)", z[0] == 0 and z[1] == 0,
     f"fora/nulos {z[0]}; pop ruim {z[1]}; registros com 100% {z[2]:,} ({100 * z[2] / n:.1f}%); mínimo {z[3]}")

# B2 qtCoberturaAb inconsistente
d = con.execute("""SELECT count(*) FILTER (WHERE abs(pc - 100*qcob/pop) > 0.5),
  median(qcob / (pc*pop/100)) FILTER (WHERE abs(pc - 100*qcob/pop) > 0.5 AND pc > 0),
  quantile_cont(qcob / (pc*pop/100), 0.1) FILTER (WHERE abs(pc - 100*qcob/pop) > 0.5 AND pc > 0),
  quantile_cont(qcob / (pc*pop/100), 0.9) FILTER (WHERE abs(pc - 100*qcob/pop) > 0.5 AND pc > 0),
  count(*) FILTER (WHERE abs(pc - 100*qcob/pop) > 0.5 AND qcob > pop) FROM c""").fetchone()
R.ok("B2.01 qtCoberturaAb inconsistente com pcCoberturaAb (|pc − 100·q/pop| > 0,5 p.p.) em 3,170 registros (0,68%)",
     d[0] == 3170 and f"{100 * d[0] / n:.2f}" == "0.68", f"{d[0]:,} ({100 * d[0] / n:.3f}%); razão q/(pc·pop) mediana {d[1]:.4f}, p10 {d[2]:.4f}, p90 {d[3]:.4f}; q > pop em {d[4]}")
R.ok("B2.02 'em geral cerca de 100 vezes menor' (razão mediana ≈ 0,01)", 0.005 < d[1] < 0.02, f"mediana {d[1]:.4f}")
# o percentual bate com as equipes? Fórmula reconstruída aqui dos próprios campos do JSON: cobertos = 3450·ESF + 3000·eAB parametrizadas
# + 3000·mín(CH médico, CH enfermeiro) quando há eAB equivalente (qtEAbEquivalenteCh > 0); pc = mín(100, 100·cobertos/pop)
con.execute("ALTER TABLE c ADD COLUMN chm DOUBLE; ALTER TABLE c ADD COLUMN che DOUBLE")
con.execute("UPDATE c SET chm = x.m, che = x.e FROM (SELECT coMunicipioIbge mun, nuComp, CAST(replace(qtChMedico, ',', '') AS DOUBLE) m, "
            "CAST(replace(qtChEnfermeiro, ',', '') AS DOUBLE) e FROM read_json('" + glob + "', format='array', columns={coMunicipioIbge:'VARCHAR', "
            "nuComp:'VARCHAR', qtChMedico:'VARCHAR', qtChEnfermeiro:'VARCHAR'})) x WHERE c.mun = x.mun AND c.nuComp = x.nuComp")
FQ = "(3450*esf + 3000*eabp + CASE WHEN eabeq > 0 THEN 3000*least(chm, che) ELSE 0 END)"
e = con.execute(f"""SELECT count(*) FILTER (WHERE abs(pc - least(100, 100*{FQ}/pop)) > 0.5), count(*) FILTER (WHERE abs(qcob - {FQ}) > 1),
  count(*) FILTER (WHERE abs(pc - least(100, 100*{FQ}/pop)) > 0.5 AND abs(pc - 100*qcob/pop) > 0.5),
  count(*) FILTER (WHERE eabeq > 0), sum(CASE WHEN eabeq > 0 THEN 3000*least(chm, che) ELSE 0 END) / sum({FQ}) FROM c""").fetchone()
R.ok("B2.03 o percentual bate com as equipes: pc = mín(100, (3450·ESF + 3000·eAB parametrizadas + 3000·mín(CH méd., CH enf.) se há eAB equivalente)/pop) "
     "a ±0,5 p.p. em ≥ 99% dos registros (fórmula reconstruída pelo auditor)", e[0] / n < 0.01,
     f"pc diverge {e[0]:,}; qtCoberturaAb ≠ fórmula em {e[1]:,}; divergem pc e q {e[2]}; registros com eAB equivalente {e[3]:,}; "
     f"parte equivalente na cobertura total {100 * e[4]:.1f}%")

# B3 mapa e cobertura região × ano
rl = pd.read_csv(PROJ / "docs/referencias/territorio_dez24/rl_municip_regsaud.csv", dtype=str)
con.register("rl", rl)
sem_reg = con.execute("SELECT count(DISTINCT mun) FROM c LEFT JOIN rl ON c.mun = rl.CO_MUNICIP WHERE rl.CO_REGSAUD IS NULL").fetchone()[0]
sem_dado = sorted(set(rl.CO_MUNICIP) - set(con.execute("SELECT DISTINCT mun FROM c").df().mun))
R.ok("B3.01 todo município do JSON tem região no mapa dez/2024; do mapa, sem registro só 510183 (MT) e o 530000 (código de ignorado do DF)",
     sem_reg == 0 and sem_dado == ["510183", "530000"], f"JSON sem região {sem_reg}; mapa sem registro {sem_dado}; regiões {rl.CO_REGSAUD.nunique()}")
# nascimentos com 510183 em toda a base v3 (todos os anos, incl ou não)
V3 = PROC / "sinasc_brasil_2015_2024_v3_20261008"
nb = con.execute(f"SELECT count(*) FILTER (WHERE CODMUNRES = '510183'), count(*) FILTER (WHERE CODMUNRES LIKE '51018%') "
                 f"FROM read_parquet('{V3}/*/*.parquet')").fetchone()
R.ok("B3.02 nenhum nascimento com CODMUNRES 510183 na base v3 (2015–2024)", nb[0] == 0, f"510183: {nb[0]}")
mp = pd.read_csv(PROC / "municipio_regsaude_dez24_v1_20261008.csv", dtype=str)
R.ok("B3.03 o mapa processado do projeto = base territorial (mesmos pares município → região)",
     set(zip(mp.CODMUNRES, mp.CO_REGSAUD)) == set(zip(rl.CO_MUNICIP, rl.CO_REGSAUD)), f"{len(mp)} × {len(rl)}")
rl2 = rl[~rl.CO_MUNICIP.str.endswith("0000")]
con.register("rl2", rl2)
A = con.execute("""WITH k AS (SELECT c.*, rl2.CO_REGSAUD reg FROM c JOIN rl2 ON c.mun = rl2.CO_MUNICIP),
  m AS (SELECT reg, ano, nuComp, sum(pop) pm FROM k GROUP BY ALL)
  SELECT k.reg CO_REGSAUD, k.ano, sum(pc*pop)/sum(pop) cob, count(DISTINCT mun) nmun, count(*) nreg,
         (SELECT avg(pm) FROM m WHERE m.reg = k.reg AND m.ano = k.ano) popm
  FROM k GROUP BY k.reg, k.ano""").df()
nm_map = rl2.groupby("CO_REGSAUD").CO_MUNICIP.nunique()
A["completa"] = (A.nmun == A.CO_REGSAUD.map(nm_map)) & (A.nreg == 12 * A.CO_REGSAUD.map(nm_map))
P = pd.read_csv(PROC / "cobertura_ab_regsaude_ano_v1_20261008.csv", dtype={"CO_REGSAUD": str})
m = P.merge(A, on=["CO_REGSAUD", "ano"], how="outer", indicator=True)
dc, dp = (m.cobertura_ab - m.cob).abs().max(), (m.pop_media - m.popm).abs().max()
R.ok("B3.04 cobertura região × ano recalculada (DuckDB, média de pc ponderada por qtPopulacao nos municípios × 12 meses) = arquivo do projeto",
     (m._merge == "both").all() and len(m) == 3031 and dc < 1e-9 and dp < 1e-6 and (m.n_municipios == m.nmun).all()
     and (m.completa_x == m.completa_y).all(), f"{len(m)} pares; {m.CO_REGSAUD.nunique()} regiões; anos {m.ano.min()}–{m.ano.max()}; "
     f"dif. máx. cobertura {dc:.1e}; pop {dp:.1e}")
inc = m[~m.completa_y]
R.ok("B3.05 7 pares incompletos = região do 510183 × 7 anos", len(inc) == 7 and inc.CO_REGSAUD.nunique() == 1
     and inc.CO_REGSAUD.iloc[0] == rl.set_index("CO_MUNICIP").CO_REGSAUD["510183"], f"{len(inc)} pares; região {sorted(inc.CO_REGSAUD.unique())}")
pv = con.execute("SELECT count(*) FROM (SELECT mun, ano FROM c GROUP BY mun, ano HAVING count(DISTINCT pop) > 1)").fetchone()[0]
R.ok("B3.06 [descritivo] município-ano com população variando entre os meses (afeta só o peso)", True, f"{pv:,} de {5570 * 7:,}")
pa = con.execute("SELECT substr(nuComp,1,4) ano, list(DISTINCT nuAnoPopulacaoConsiderada ORDER BY nuAnoPopulacaoConsiderada) FROM j GROUP BY 1 ORDER BY 1").fetchall()
R.ok("B3.07 [descritivo] ano da população considerada pelo relatório, por ano de competência", True, "; ".join(f"{a}: {'/'.join(v)}" for a, v in pa))
B = A.assign(macro=A.CO_REGSAUD.str[0])
T = pd.read_csv(TB / "tab_e8_02_cobertura_distribuicao_macro_ano_v1_20261008.csv")
br = B.groupby("ano").apply(lambda g: np.average(g.cob, weights=g.popm), include_groups=False)
tb = T[T.macro == "Brasil"].set_index("ano").media_pond
R.ok("B3.08 tab_e8_02_cobertura_distribuicao: média Brasil por ano ponderada pela população = recalculada", (br - tb).abs().max() < 0.006,
     "; ".join(f"{a} {v:.1f}" for a, v in br.items()))
Q = pd.read_csv(TB / "tab_e8_02_qualidade_v1_20261008.csv")
R.ok("B3.09 tab_e8_02_qualidade: totais = recalculados (registros, municípios, divergência 3,170, mapa sem registro 1)",
     Q.registros.sum() == n and Q.municipios.sum() == nm and Q.divergencia_pc_qt_gt_0_5pp.sum() == 3170
     and Q.municipios_do_mapa_sem_registro.sum() == 1 and Q.registros_sem_regiao_de_saude.sum() == 0, Q.drop(columns=["uf", "sigla"]).sum().to_dict())
R.grava()
