"""
Auditoria 7c.6 final — checagens na web (só GET de páginas/APIs públicas; nada do projeto é enviado).
Itens: L2c (RECORD: material suplementar do artigo, Table 1, licença, site e MD5 do docx) e M5 (Evans 2024: referência e licença).
O docx do site é baixado só para a memória (MD5 e tamanho); nada é gravado além do JSON de resultado nesta pasta.
Saída: web_7c6_final_v1_20261010.json
"""
import hashlib
import json
import re
import urllib.request
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
UA = {"User-Agent": "curl/8.7.1", "Accept": "*/*"}     # o site do RECORD recusa (406) o User-Agent padrão do urllib


def get(u):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=90)
        return r.status, r.read()
    except Exception as e:  # registra o erro em vez de parar
        return f"erro: {e}", b""


def limpa(h):
    return " ".join(re.sub(r"<[^>]+>", " ", h).split())


R = {"quando": datetime.now().isoformat(timespec="seconds")}

# ---- RECORD: página do checklist
u = "https://www.record-statement.org/checklist.php"
s, b = get(u)
h = b.decode("utf-8", "replace")
R["record_pagina"] = dict(url=u, status=s, bytes=len(b),
                          frase_cc_by=("protected on a Creative Common Attribution (CC BY) license" in limpa(h)),
                          links_cc=sorted(set(re.findall(r"https?://creativecommons\.org/licenses/[a-z\-]+/[\d.]+/?", h))),
                          links_docx=sorted(set(re.findall(r"[^\"' >]*\.docx", h))))
m = re.search(r"[^.]{0,200}Creative Common[^.]{0,200}\.", limpa(h))
R["record_pagina"]["trecho"] = m.group(0).strip() if m else ""

# ---- RECORD: docx do site (só MD5 e tamanho, em memória)
u = "https://www.record-statement.org/Files/checklist/RECORD%20Checklist.docx"
s, b = get(u)
R["record_docx"] = dict(url=u, status=s, bytes=len(b), md5=hashlib.md5(b).hexdigest() if b else "")

# ---- RECORD: artigo (PLoS Med 2015;12(10):e1001885) — metadados (Europe PMC), XML do PMC (licença, Table 1, material suplementar)
u = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:10.1371/journal.pmed.1001885&resultType=core&format=json"
s, b = get(u)
try:
    x = json.loads(b)["resultList"]["result"][0]
    R["record_artigo_epmc"] = dict(url=u, status=s, pmcid=x.get("pmcid"), pmid=x.get("pmid"), titulo=x.get("title"),
                                   revista=x.get("journalInfo", {}).get("journal", {}).get("title"), license=x.get("license"),
                                   ano=x.get("pubYear"), volume=x.get("journalInfo", {}).get("volume"), numero=x.get("journalInfo", {}).get("issue"),
                                   pagina=x.get("pageInfo"))
except Exception as e:
    R["record_artigo_epmc"] = dict(url=u, status=s, erro=str(e))
pmc = (R["record_artigo_epmc"].get("pmcid") or "PMC4595218").replace("PMC", "")
u = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id={pmc}&rettype=xml"
s, b = get(u)
x = b.decode("utf-8", "replace")
sup = re.findall(r"<supplementary-material\b.*?</supplementary-material>", x, re.S)
R["record_artigo_pmc"] = dict(
    url=u, status=s, bytes=len(b),
    licenca=[limpa(l)[:300] for l in re.findall(r"<license\b.*?</license>", x, re.S)],
    licenca_href=sorted(set(re.findall(r"creativecommons\.org/licenses/[a-z\-]+/[\d.]+", x))),
    licenca_xlink=re.findall(r'<license[^>]*xlink:href="([^"]+)"', x),
    n_material_suplementar=len(sup),
    material_suplementar=[dict(rotulo=limpa(" ".join(re.findall(r"<label>(.*?)</label>", m, re.S))),
                               legenda=limpa(" ".join(re.findall(r"<caption>(.*?)</caption>", m, re.S)))[:200],
                               arquivos=re.findall(r'xlink:href="([^"]+)"', m)) for m in sup],
    tabelas=[dict(rotulo=limpa(" ".join(re.findall(r"<label>(.*?)</label>", t, re.S)[:1])),
                  legenda=limpa(" ".join(re.findall(r"<caption>(.*?)</caption>", t, re.S)))[:220])
             for t in re.findall(r"<table-wrap\b.*?</table-wrap>", x, re.S)])
# página da PLOS (seção Supporting information), como segunda fonte
u = "https://journals.plos.org/plosmedicine/article?id=10.1371/journal.pmed.1001885"
s, b = get(u)
h = b.decode("utf-8", "replace")
si = re.findall(r'class="siTitle[^"]*"[^>]*>(.*?)</', h, re.S) or re.findall(r"<p class=\"siTitle\">(.*?)</p>", h, re.S)
cop = re.search(r"<strong>Copyright: </strong>(.*?)</p>", h, re.S)
R["record_artigo_plos_licenca"] = dict(texto=limpa(cop.group(1))[:400] if cop else "",
                                       href=re.findall(r'href="([^"]*creativecommons[^"]*)"', cop.group(1)) if cop else [])
R["record_artigo_plos"] = dict(url=u, status=s, bytes=len(b), si_titulos=[limpa(t)[:200] for t in si],
                               tem_secao_supporting=("Supporting information" in h),
                               supp_links=sorted(set(re.findall(r"journal\.pmed\.1001885\.s\d+", h))))

# ---- Evans 2024 (PMC11059336): metadados e licença
u = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=PMCID:PMC11059336&resultType=core&format=json"
s, b = get(u)
try:
    x = json.loads(b)["resultList"]["result"][0]
    R["evans_epmc"] = dict(url=u, status=s, pmid=x.get("pmid"), pmcid=x.get("pmcid"), doi=x.get("doi"), titulo=x.get("title"),
                           autores=x.get("authorString"), revista=x.get("journalInfo", {}).get("journal", {}).get("title"),
                           ano=x.get("pubYear"), volume=x.get("journalInfo", {}).get("volume"), pagina=x.get("pageInfo"),
                           license=x.get("license"), isOpenAccess=x.get("isOpenAccess"))
except Exception as e:
    R["evans_epmc"] = dict(url=u, status=s, erro=str(e))
u = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=11059336&rettype=xml"
s, b = get(u)
x = b.decode("utf-8", "replace")
R["evans_pmc"] = dict(url=u, status=s, bytes=len(b),
                      licenca=[limpa(l)[:300] for l in re.findall(r"<license\b.*?</license>", x, re.S)],
                      licenca_href=sorted(set(re.findall(r"creativecommons\.org/licenses/[a-z\-]+/[\d.]+", x))),
                      copyright=[limpa(c)[:200] for c in re.findall(r"<copyright-statement>.*?</copyright-statement>", x, re.S)])
u = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id=PMC11059336"
s, b = get(u)
R["evans_oa_fcgi"] = dict(url=u, status=s, resposta=b.decode("utf-8", "replace")[:500])

(AQUI / "web_7c6_final_v1_20261010.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(R, ensure_ascii=False, indent=1)[:6000])
