#!/usr/bin/env python3
"""Uma ponte falsa, para testar a app sem mexer no amp.

    python3 tools/fake_bridge.py [pasta do firmware] [porta]

Usa o names.validate do firmware de verdade: o PUT /names é aceito ou recusado como no Pico.
Mostra cada PUT recebido. No emulador do Android, o computador é o IP 10.0.2.2.
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

FIRMWARE = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Projects/sp103-mod/firmware")
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
sys.path.insert(0, FIRMWARE)

import device  # noqa: E402
import names  # noqa: E402

config = names.validate({"inputs": {"TUNER": "Rega Planar 2"}, "vu": {"on": True}, "info": {"on": True}})
STATE = {"power": "on", "volume_db": -20.0, "input": "DAB", "input_id": "dab", "input_name": "AirPlay/BT",
         "bass_db": 2, "treble_db": -3, "balance": {"side": "L", "db": -5.0}, "loudness": False, "speakers": True,
         "screen": "normal", "firmware": "1.0", "lcd": ["Volume -20.00 dB", "AirPlay/BT      "], "version": 5}


def names_reply():
    return {"config": config, "inputs": list(names.INPUTS),
            "defaults": {"boot": ["ACOUSTIC", "SOLUTIONS"], "about": ["Amplifier SP103", "SW version 1.0"]},
            "vu": {"on": config["vu"]["on"], "last_frame_ms": None, "music": False, "showing": False, "error": None},
            "info": {"last_packet_ms": None, "playing": False},
            "screens": {"on": config["info"]["on"], "showing": None, "error": None}}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def answer(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/device":
            self.answer(device.describe("fake"))
        elif self.path == "/names":
            self.answer(names_reply())
        elif self.path == "/bus.json":
            self.answer({"max_gap_ms": 12, "max_batch": 40, "screens": 3})
        elif self.path == "/events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            self.wfile.write(("data: %s\n\n" % json.dumps(STATE)).encode())
            self.wfile.flush()
            try:
                while True:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    __import__("time").sleep(1)
            except OSError:
                pass
        else:
            self.send_error(404)

    def do_POST(self):
        """Só mostra o comando: a ponte falsa não muda o estado."""
        print("POST", self.path, flush=True)
        self.answer(STATE)

    def do_PUT(self):
        global config
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        try:
            config = names.validate(json.loads(body))
        except ValueError as e:
            print("PUT recusado:", e, flush=True)
            return self.answer({"error": str(e)}, 400)
        print("PUT aceito:", json.dumps(config), flush=True)
        self.answer(names_reply())


print("ponte falsa na porta", PORT, flush=True)
ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
