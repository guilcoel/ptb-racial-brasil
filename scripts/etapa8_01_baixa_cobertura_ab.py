"""
8.1 Baixa a cobertura da Atenção Básica por município, competências 201401–202012, das 27 UFs.
Fonte oficial: Ministério da Saúde, relatório público "Cobertura da Atenção Básica (2007 - 2020)"
(https://relatorioaps.saude.gov.br/cobertura/ab), pela API que a própria página usa:
  https://relatorioaps-prd.saude.gov.br/cobertura/ab?unidadeGeografica=MUNICIPIO&coUf=UU&nuCompInicio=201401&nuCompFim=202012
(a mesma consulta do APS-CLIMA, R/03_baixar_cobertura_ab.R, lá com 2010–2019). Dado público agregado por município: sem microdados.
Guarda o JSON exatamente como veio, um arquivo por UF, em data/raw/aps_cobertura_ab/ (fora do git); nunca sobrescreve: se o
arquivo já existe, só confere. Confere que cada arquivo é uma lista com os campos esperados, só da UF pedida, com as 84 competências.
Saídas: data/raw/aps_cobertura_ab/cobertura_ab_uf{UU}_201401_202012.json, manifesto_cobertura_ab_v1_20261013.csv (mesma pasta) e
docs/referencias/aps_cobertura_ab/ACESSO.txt (URL, data, bytes e MD5 de cada UF; só metadados).
Rodar da raiz: python3 scripts/etapa8_01_baixa_cobertura_ab.py
"""
import hashlib
import json
import time
import urllib.request
from datetime import datetime

import pandas as pd

import etapa0_lib as L

log = L.Logger("8_01_baixa_cobertura_ab", etapa="etapa8")
API = "https://relatorioaps-prd.saude.gov.br/cobertura/ab"
INI, FIM = "201401", "202012"
COMPS = [f"{a}{m:02d}" for a in range(2014, 2021) for m in range(1, 13)]
CAMPOS = {"nuComp", "coUfIbge", "sgUf", "coMunicipioIbge", "qtPopulacao", "pcCoberturaAb", "pcCoberturaSf", "qtCoberturaAb",
          "qtEsf", "qtEAbParametrizada", "nuAnoPopulacaoConsiderada"}
DEST = L.PROJ / "data" / "raw" / "aps_cobertura_ab"
DEST.mkdir(parents=True, exist_ok=True)
REF = L.PROJ / "docs" / "referencias" / "aps_cobertura_ab"
REF.mkdir(parents=True, exist_ok=True)
md5 = lambda b: hashlib.md5(b).hexdigest()


def baixa(url, tentativas=3):
    for k in range(tentativas):
        try:
            with urllib.request.urlopen(url, timeout=900) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 — registra e tenta de novo
            log(f"falhou ({k + 1}/{tentativas}): {type(e).__name__}: {e}")
            time.sleep(30)
    raise RuntimeError(f"não baixou: {url}")


man = []
for uf in sorted(L.UF_SIGLA):
    arq = DEST / f"cobertura_ab_uf{uf}_{INI}_{FIM}.json"
    url = f"{API}?unidadeGeografica=MUNICIPIO&coUf={int(uf)}&nuCompInicio={INI}&nuCompFim={FIM}"
    if arq.exists():
        b, status, quando = arq.read_bytes(), "ja_existia", datetime.fromtimestamp(arq.stat().st_mtime)
    else:
        b, quando = baixa(url), datetime.now()
        tmp = arq.with_name(arq.name + ".part")
        assert not tmp.exists()
        tmp.write_bytes(b)
        tmp.rename(arq)                                   # nome final só depois do arquivo completo
        status = "baixado"
    x = json.loads(b)
    assert isinstance(x, list) and len(x) > 0, uf
    assert all(CAMPOS <= set(r) for r in x), f"UF {uf}: campos faltando"
    assert {r["coUfIbge"] for r in x} == {uf}, f"UF {uf}: veio outra UF"
    comps = {r["nuComp"] for r in x}
    assert comps == set(COMPS), f"UF {uf}: competências {sorted(set(COMPS) - comps)[:5]} faltando"
    n_mun = len({r["coMunicipioIbge"] for r in x})
    man.append(dict(uf=uf, sigla=L.UF_SIGLA[uf], url=url, arquivo=arq.name, status=status, bytes=len(b), md5=md5(b),
                    registros=len(x), municipios=n_mun, competencias=len(comps), quando=quando.strftime("%Y-%m-%d %H:%M:%S")))
    log(f"UF {uf} {L.UF_SIGLA[uf]}: {status}; {len(b):,} bytes; {len(x):,} registros; {n_mun} municípios; md5 {md5(b)}")
    if status == "baixado":
        time.sleep(2)

M = pd.DataFrame(man)
M.to_csv(DEST / "manifesto_cobertura_ab_v1_20261013.csv", index=False)
txt = ["Cobertura da Atenção Básica por município (Ministério da Saúde, relatório público 'Cobertura da Atenção Básica (2007 - 2020)',",
       "https://relatorioaps.saude.gov.br/cobertura/ab), API da própria página, competências 201401–202012, uma consulta por UF.",
       f"Arquivos em data/raw/aps_cobertura_ab/ (fora do git), gravados como vieram. Gerado por scripts/etapa8_01_baixa_cobertura_ab.py.",
       f"Total: {len(M)} UFs; {int(M.registros.sum()):,} registros; {int(M.municipios.sum()):,} municípios; {int(M.bytes.sum()):,} bytes.", ""]
txt += [f"{r.quando} -03  {r.url}  ({r.bytes} bytes)\nMD5 ({r.arquivo}) = {r.md5}" for r in M.itertuples()]
(REF / "ACESSO.txt").write_text("\n".join(txt) + "\n")
log(f"fim: {len(M)} UFs; {int(M.registros.sum()):,} registros; {int(M.municipios.sum()):,} municípios; "
    f"{int(M.bytes.sum()):,} bytes; status {M.status.value_counts().to_dict()}")
