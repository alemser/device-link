#!/usr/bin/env python3
"""Envia o programa novo para o Pico pelo Wi-Fi (firmware/ota.py) e acompanha até ele confirmar.

Este arquivo é da base comum (amp-link, firmware-base/): mude lá e copie com o copiar.py, nunca aqui.

    python3 tools/enviar.py                    # envia o que mudou em firmware/, apaga do Pico
                                               # os .py que não existem mais e aplica
    python3 tools/enviar.py ponte.py web.py    # só esses arquivos (se mudaram)
    python3 tools/enviar.py --estado           # só mostra a versão e o estado do Pico
    python3 tools/enviar.py --voltar           # volta para a versão anterior (guardada no Pico)

Opções: --host, --forcar (envia mesmo sem mudança) e --publish (release no GitHub para a app DeviceLink). O nome da ponte vem do NAME de firmware/device.py (por
exemplo "mr780"): o host padrão é <nome>.local, ou a variável <NOME>_HOST. Se o host não responder, procura o Pico
pela descoberta (broadcast UDP, como a app).
Sem senha (contract v2). Pontes com o ota.py antigo ainda pedem o UPDATE_PASSWORD de firmware/secrets.py.

Nunca envia main.py nem secrets.py: esses só pelo cabo, com o mpremote.
"""

import argparse
import glob
import hashlib
import http.client
import json
import os
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
FIRMWARE = os.path.join(HERE, "..", "firmware")
LOCKED = ("main.py", "secrets.py")

sys.path.insert(0, FIRMWARE)
from device import NAME   # noqa: E402  (o nome desta ponte na descoberta e na rede)
TRIAL_S = 180                   # o mesmo do main.py
WAIT_S = TRIAL_S + 90           # reinício + Wi-Fi + teste


def password():
    """Only for bridges still running the old ota.py, which asked for one; the current one takes no password.
    Sent when firmware/secrets.py (or <NAME>_PASSWORD) has it, ignored by bridges that don't need it."""
    if os.environ.get(NAME.upper() + "_PASSWORD"):
        return os.environ[NAME.upper() + "_PASSWORD"]
    values = {}
    try:
        with open(os.path.join(FIRMWARE, "secrets.py")) as f:
            exec(f.read(), values)
    except OSError:
        pass
    return values.get("UPDATE_PASSWORD") or None


def request(host, method, path, body=None, pw=None, timeout=10):
    req = urllib.request.Request("http://%s%s" % (host, path), data=body, method=method)
    if pw:
        req.add_header("X-Password", pw)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            msg = json.load(e).get("error", e.reason)
        except (ValueError, OSError):   # o Pico responde antes de ler tudo e fecha a conexão
            msg = e.reason
        sys.exit("O Pico recusou (%d): %s" % (e.code, msg))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def version(files):
    """O mesmo código de versão do ota.version()."""
    h = hashlib.sha256()
    for name in sorted(files):
        if name in LOCKED:
            continue
        h.update((name + files[name]).encode())
    return h.hexdigest()[:8]


def show(st):
    print("Versão no Pico: %s   estado: %s%s" % (
        st["version"], st["state"], "  (%s)" % st["why"] if st.get("why") else ""))
    print("Versão anterior guardada: %s" % (st["previous"] or "nenhuma"))
    if not st["enabled"]:
        print("This bridge runs the old ota.py, which needs UPDATE_PASSWORD in its secrets.py.")


def publish(repo):
    """Publishes firmware/ as a GitHub release of repo, for the DeviceLink app (docs/contract-v2.md, Updates):
    tag = the version, assets = the program files and firmware.json {"version", "files": {name: sha256}}."""
    import subprocess
    import tempfile
    files = local_files(None)
    digests = {n: sha(d) for n, d in files.items()}
    ver = version(digests)
    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for name, data in files.items():
            path = os.path.join(tmp, name)
            with open(path, "wb") as f:
                f.write(data)
            paths.append(path)
        manifest = os.path.join(tmp, "firmware.json")
        with open(manifest, "w") as f:
            json.dump({"version": ver, "files": digests}, f, indent=1, sort_keys=True)
        subprocess.run(["gh", "release", "create", ver, "--repo", repo, "--title", "Firmware " + ver,
                        "--notes", "Bridge firmware %s (%d files)." % (ver, len(files)), manifest] + paths,
                       check=True)
    print("Published %s as release %s of %s." % (", ".join(sorted(files)), ver, repo))


def local_files(names):
    paths = [os.path.join(FIRMWARE, n) for n in names] if names else \
        sorted(glob.glob(os.path.join(FIRMWARE, "*.py")))
    out = {}
    for path in paths:
        name = os.path.basename(path)
        if not name[:-3].replace("_", "").isalnum():
            continue                        # secrets.example.py e afins: não são do programa
        if name in LOCKED:
            if names:
                print("%s fica de fora: só pelo cabo (.venv/bin/mpremote cp firmware/%s :%s)" % (
                    name, name, name))
            continue
        with open(path, "rb") as f:
            data = f.read()
        try:
            compile(data, name, "exec")     # erro de digitação: melhor descobrir aqui
        except SyntaxError as e:
            sys.exit("Erro de sintaxe em %s, linha %s: %s" % (name, e.lineno, e.msg))
        out[name] = data
    return out


def rollback_trial(host, timeout=60):
    """Pede a volta se o teste iniciou, mesmo quando a resposta do POST se perdeu."""
    try:
        request(host, "POST", "/update/rollback", b"", password())
    except (http.client.RemoteDisconnected, ConnectionError, OSError, urllib.error.URLError):
        pass                            # confirma pelo estado abaixo; a resposta pode ter se perdido
    started = time.time()
    while time.time() - started < timeout:
        time.sleep(2)
        try:
            st = request(host, "GET", "/update", timeout=5)
        except (OSError, urllib.error.URLError):
            continue
        if st["state"] == "rolled_back":
            return st
    return None


def wait(host, expected, expected_files, started):
    """Acompanha o reinício e o teste da versão nova, até confirmar ou voltar."""
    last = None
    while time.time() - started < WAIT_S:
        time.sleep(2)
        try:
            st = request(host, "GET", "/update", timeout=5)
        except (OSError, urllib.error.URLError):
            msg = "Pico reiniciando (ainda sem resposta)..."
        else:
            if st["state"] == "ok" and st["version"] == expected:
                mismatched = sorted(n for n, digest in expected_files.items()
                                    if st["files"].get(n) != digest)
                if mismatched:
                    print("\nVersão tem o código esperado, mas os hashes não conferem: %s." %
                          ", ".join(mismatched))
                    return False
                print("\nPronto: versão %s confirmada. A anterior (%s) fica guardada no Pico." % (
                    expected, st["previous"]))
                return True
            if st["state"] == "rolled_back":
                print("\nA versão nova FALHOU e o Pico voltou para a anterior (%s): %s." % (
                    st["version"], st["why"]))
                print("Veja o erro pelo cabo: .venv/bin/mpremote (o Pico mostra o erro ao ligar).")
                return False
            if st["state"] == "trial":
                mismatched = sorted(n for n, digest in expected_files.items()
                                    if st["files"].get(n) != digest)
                if mismatched:
                    print("\nHash remoto diferente durante o teste: %s. Pedindo rollback..." %
                          ", ".join(mismatched))
                    old = rollback_trial(host)
                    if old:
                        print("Pico voltou com segurança para a versão %s." % old["version"])
                    else:
                        print("Não consegui confirmar o rollback; confira com --estado antes de novo deploy.")
                    return False
                msg = "Versão %s em teste; hashes conferem (o Pico confirma depois de 20 s funcionando)..." % st["version"]
            else:
                msg = "Estado: %s, versão %s" % (st["state"], st["version"])
        if msg != last:
            print("  %3d s  %s" % (time.time() - started, msg))
            last = msg
    print("\nO Pico não confirmou em %d s. Ele volta sozinho para a versão anterior;" % WAIT_S)
    print("confira com: python3 tools/enviar.py --estado")
    return False


def discover(model=NAME, tries=3, listen_s=0.7):
    """O IP do Pico pela descoberta do wifi.py (broadcast UDP "AMPLINK?", porta 47800), ou None."""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(listen_s)
    try:
        for _ in range(tries):
            sock.sendto(b"AMPLINK?", ("255.255.255.255", 47800))
            try:
                while True:
                    data, _addr = sock.recvfrom(256)
                    answer = json.loads(data)
                    if answer.get("model") == model and answer.get("ip"):
                        return answer["ip"]
            except (socket.timeout, ValueError):
                pass
    finally:
        sock.close()
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("files", nargs="*", help="arquivos de firmware/ (padrão: todos os .py)")
    ap.add_argument("--host", default=os.environ.get(NAME.upper() + "_HOST", NAME + ".local"))
    ap.add_argument("--estado", action="store_true", help="só mostra o estado")
    ap.add_argument("--voltar", action="store_true", help="volta para a versão anterior")
    ap.add_argument("--forcar", action="store_true", help="envia mesmo os arquivos sem mudança")
    ap.add_argument("--publish", action="store_true",
                    help="publish firmware/ as a GitHub release (device.FIRMWARE repo), for the DeviceLink app")
    args = ap.parse_args()
    if args.publish:
        from device import FIRMWARE as repo
        return publish(repo)
    host = args.host

    try:
        st = request(host, "GET", "/update")
    except (OSError, urllib.error.URLError) as e:
        found = discover()
        if not found:
            sys.exit("Não achei o Pico em %s (%s), nem pela descoberta. Ele está ligado e no Wi-Fi? "
                     "Tente --host com o IP." % (host, getattr(e, "reason", e)))
        host = found
        print("Achei o Pico pela descoberta: %s" % host)
        st = request(host, "GET", "/update")
    show(st)
    if args.estado:
        return

    pw = password()
    if args.voltar:
        if not st["previous"]:
            sys.exit("Não há versão anterior guardada no Pico.")
        if st["previous"] == st["version"]:
            sys.exit("O Pico já está na versão guardada (%s): não há para onde voltar." % st["version"])
        request(host, "POST", "/update/rollback", b"", pw)
        print("Voltando para a versão %s..." % st["previous"])
        started = time.time()
        while time.time() - started < 60:
            time.sleep(2)
            try:
                st = request(host, "GET", "/update", timeout=5)
            except (OSError, urllib.error.URLError):
                continue
            if st["state"] == "rolled_back":
                print("Pronto: o Pico está na versão %s." % st["version"])
                return
        sys.exit("O Pico não respondeu em 60 s.")

    if st["state"] == "trial":
        sys.exit("A última atualização ainda está em teste. Espere uns minutos e tente de novo.")

    files = local_files(args.files)
    if not args.files:
        with open(os.path.join(FIRMWARE, "main.py"), "rb") as f:
            if sha(f.read()) != st["files"].get("main.py"):
                print("Aviso: o main.py do Pico é diferente do firmware/main.py. Ele não vai pelo "
                      "Wi-Fi;\n       se precisar, pelo cabo: .venv/bin/mpremote cp firmware/main.py :main.py")
    send = {n: d for n, d in files.items() if args.forcar or sha(d) != st["files"].get(n)}
    # Só com o firmware/ inteiro dá para saber o que sobrou no Pico.
    remove = [] if args.files else sorted(n for n in st["files"] if n not in LOCKED and n not in files)
    if remove and not st.get("can_delete"):
        print("No Pico sobraram %s, mas o ota.py dele ainda não sabe apagar.\n"
              "Envie esta versão e rode de novo para apagar." % ", ".join(remove))
        remove = []
    if not send and not remove:
        print("Nada mudou: o Pico já tem esses arquivos.")
        return

    if send:
        print("\nEnviando %d arquivo(s):" % len(send))
    request(host, "POST", "/update/cancel", b"", pw)
    for name, data in send.items():
        try:
            got = request(host, "PUT", "/update/" + name, data, pw, timeout=30)
        except (http.client.RemoteDisconnected, ConnectionError, OSError, urllib.error.URLError) as e:
            # Alguns MicroPython fecham a conexão depois de gravar o corpo, antes de a
            # resposta JSON chegar ao computador. O nome staged prova apenas que chegou
            # ao arquivo temporário; a integridade será conferida pelos SHA-256 ativos
            # durante o trial, antes de deixar a atualização confirmar.
            check = request(host, "GET", "/update", timeout=5)
            if name not in check["staged"]:
                sys.exit("Resposta perdida ao enviar %s e o arquivo não apareceu no staging (%s). "
                         "Nada foi aplicado." % (name, e))
            print("  %-20s resposta HTTP perdida; staging presente, hash será conferido no trial" % name)
        else:
            if got["sha256"] != sha(data):
                sys.exit("%s chegou diferente; nada foi aplicado. Tente de novo." % name)
            print("  %-20s %6d bytes  ok" % (name, len(data)))
    if remove:
        print("\nApagando do Pico %d arquivo(s) que não existem mais em firmware/:" % len(remove))
        for name in remove:
            request(host, "DELETE", "/update/" + name, None, pw)
            print("  %-20s marcado" % name)

    expected_files = dict(st["files"])
    expected_files.update({n: sha(d) for n, d in send.items()})
    for name in remove:
        del expected_files[name]
    expected = version(expected_files)
    try:
        request(host, "POST", "/update/apply", b"", pw)
    except (http.client.RemoteDisconnected, ConnectionError, OSError, urllib.error.URLError):
        # A resposta pode sumir se o Pico iniciar o reset logo após aceitar o apply.
        pass
    print("\nAplicado. Versão nova: %s. O Pico reinicia e testa a versão nova:" % expected)
    sys.exit(0 if wait(host, expected, expected_files, time.time()) else 1)


if __name__ == "__main__":
    main()
