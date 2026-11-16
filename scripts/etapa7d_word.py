"""
etapa7d_word.py — converte .docx em PDF pelo Microsoft Word (paginação e numeração de linhas do próprio Word), para o ESM_3.pdf e para
a página/linha do checklist (Etapa 7d).
O Word é sandboxed: abrir pelo AppleScript ("open file name") falha em silêncio fora das pastas autorizadas, então o arquivo é aberto pelo
LaunchServices (open -a), que concede o acesso, e o AppleScript só salva como PDF e fecha o documento ativo, depois de conferir que o
documento ativo é o arquivo pedido (nunca fecha outro documento aberto pelo usuário).
"""
import subprocess
import time
from pathlib import Path


def _osa(*linhas):
    r = subprocess.run(["osascript", *sum((["-e", l] for l in linhas), [])], capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def docx_pdf(src, dst, espera=90):
    src, dst = Path(src).resolve(), Path(dst).resolve()
    if dst.exists():                                 # saída gerada por este script; vai para a lixeira (trash), não rm
        subprocess.run(["trash", str(dst)], check=True)
    subprocess.run(["open", "-a", "Microsoft Word", str(src)], check=True)
    t0 = time.time()
    while True:
        _, nome, _ = _osa('tell application "Microsoft Word" to get name of active document')
        _, cheio, _ = _osa('tell application "Microsoft Word" to get full name of active document')
        if nome == src.name and cheio.replace(":", "/").endswith(str(src).split("/Volumes/", 1)[-1].split("/", 1)[-1]):
            break
        if time.time() - t0 > espera:
            raise RuntimeError(f"Word não abriu {src.name} (documento ativo: {nome!r})")
        time.sleep(1)
    time.sleep(2)                                    # paginação e campos (PAGE, numeração de linhas) estáveis
    rc, out, err = _osa('tell application "Microsoft Word"',
                        f'if name of active document is "{src.name}" then',
                        f'save as active document file name "{dst}" file format format PDF',
                        "close active document saving no",
                        "end if", "end tell")
    if rc != 0:
        raise RuntimeError(f"Word: {err}")
    t0 = time.time()
    while not (dst.exists() and dst.stat().st_size > 1000):
        if time.time() - t0 > espera:
            raise RuntimeError(f"PDF não gravado: {dst}")
        time.sleep(1)
    _, nome, _ = _osa('tell application "Microsoft Word" to get name of active document')
    if nome == src.name:
        raise RuntimeError(f"{src.name} continua aberto no Word")
    return dst
