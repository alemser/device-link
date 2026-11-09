"""GET /device: quem é esta ponte e o que ela sabe fazer.

O contrato está no repositório amp-link (docs/contrato.md). Tudo aqui é fixo enquanto o programa roda: o cliente lê
uma vez ao conectar. A versão é a mesma do GET /update.

Por enquanto (2026-11-09) a ponte do MR 780 só sabe se atualizar e configurar o Wi-Fi: o estado do amp depende das
capturas do display (docs/plano.md, passo 3). Cada capacidade nova entra em FEATURES quando existir de verdade.

describe() roda igual no MicroPython (Pico) e no Python do computador (tools/test_device.py).
"""

API = 1                         # só muda quando algo deixa de ser compatível
MODEL = "Magnat MR 780"
COLUMNS, ROWS = 16, 2           # o VFD: 2 linhas de 16 caracteres (docs/pesquisa-display.md)
FEATURES = ("update", "wifi_setup")

# As entradas na ordem do botão SOURCE e do controle remoto, com os ids do groove-rig
# (internal/catalog/profiles/magnat_mr780.yaml). Os nomes são os do manual; os do display vêm das capturas.
INPUTS = (("usb_audio", "USB"), ("bluetooth", "BT"), ("phono", "PHONO"), ("cd", "CD"), ("dvd", "DVD"),
          ("aux1", "AUX 1"), ("aux2", "AUX 2"), ("tape", "TAPE"), ("line_in", "LINE IN"), ("fm", "FM"),
          ("dab", "DAB"), ("opt1", "OPT 1"), ("opt2", "OPT 2"), ("coax1", "COAX 1"), ("coax2", "COAX 2"))


def describe(version):
    return {"api": API, "model": MODEL, "bridge_version": version,
            "inputs": [{"id": i, "name": name} for i, name in INPUTS],
            "display": {"columns": COLUMNS, "rows": ROWS},
            "features": list(FEATURES)}


async def handle(req, writer):
    """Rota /device (ver web.Publisher)."""
    import ota
    from web import reply, reply_json
    if req.path != "/device":
        return await reply(writer, "404 Not Found", "text/plain", b"not found\n")
    await reply_json(writer, describe(await ota.current_version()))
