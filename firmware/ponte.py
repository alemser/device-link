"""A ponte do MR 780: o programa que o main.py importa ao ligar o Pico.

Hoje (2026-11-09), sem o amp: Wi-Fi sem cabo (wifi.py), atualização pelo Wi-Fi (ota.py) e o /device. O /state existe,
mas com tudo desconhecido (null): ler o display e comandar o amp vêm depois das medições e das capturas
(docs/plano.md). Mesmo assim, o Pico já pode ir para dentro do amp e receber o resto pelo Wi-Fi.

Rodar pelo computador:  .venv/bin/mpremote run firmware/ponte.py   (ou instalar e reiniciar: ver README)
"""

import time
import asyncio

import device
import ota
from web import Publisher
from wifi import Wifi


class State:
    """O estado do amp no contrato (GET /state e /events). null = ainda não se sabe."""

    def __init__(self):
        self.version = 0

    def to_dict(self):
        return {"power": None, "volume_db": None, "input": None, "input_id": None, "lcd": [],
                "updated_at": time.ticks_ms(), "version": self.version}


state = State()
net = Wifi(model="mr780", hostname="mr780", prefix="MR780")
pub = None
wifi_ok = False


def wifi_result(ok, info):
    global wifi_ok
    wifi_ok = ok
    if not ok:
        print("Wi-Fi:", info)


async def confirm_update():
    """Versão nova em teste (ota.py): confirma quando ela se mostra saudável. Sem isso, o main.py volta para a versão
    anterior. Saudável = o Wi-Fi conectou e o servidor respondeu a alguém (o tools/enviar.py pergunta a cada 2 s),
    por 20 s seguidos."""
    if not ota.in_trial():
        return
    start = time.ticks_ms()
    while True:
        await asyncio.sleep(2)
        if not (net.sta is not None and net.sta.isconnected() and pub.served):
            start = time.ticks_ms()
        elif time.ticks_diff(time.ticks_ms(), start) > 20000:
            ota.confirm()
            return


async def main():
    global pub
    pub = Publisher(state, routes={"/update": ota.handle, "/device": device.handle,
                                   "/wifi": net.handle, "/": net.page})
    asyncio.create_task(net.task(wifi_result))
    await asyncio.sleep(0.1)            # o Wi-Fi liga antes do servidor abrir o socket
    await pub.serve()
    asyncio.create_task(confirm_update())
    while True:
        await asyncio.sleep(60)


asyncio.run(main())
