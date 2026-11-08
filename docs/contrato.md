# Contrato entre pontes e clientes

**Rascunho, `api` 1.** Escrito a partir do firmware do SP103 e conferido na ponte real em 2026-11-04. Só um amp o
implementa até agora, então os campos podem mudar quando o Magnat MR 780 for aberto.

Uma **ponte** é a placa dentro do amp. Um **cliente** é quem a consulta. A ponte é pequena: tem pouca memória e atende
poucas conexões, e um cliente mal comportado pode travar o display. Por isso as regras de [Para o cliente](#para-o-cliente)
fazem parte do contrato.

## Rotas

O **núcleo** vale para toda ponte. As outras rotas só existem se a ponte listar a capacidade em `features`.

| Rota | Grupo | Situação no SP103 |
|---|---|---|
| `GET /device` | Núcleo | Existe |
| `GET /state` | Núcleo | Existe |
| `GET /events` | Núcleo | Existe |
| `GET /names`, `PUT /names` | `config` | Existe |
| `POST /control`, `POST /ir/send` | `control` | Existe |
| `GET /bus.json`, `GET /bus.csv`, `POST /bus/clear` | `bus_log` | Existe |
| `GET /update` e as rotas de envio | `update` | Existe; fora da app (`tools/enviar.py`) |
| `GET /wifi`, `GET /wifi/networks`, `PUT /wifi`, `POST /wifi/setup`, `DELETE /wifi` | `wifi_setup` | Existe (2026-11-08) |

## Transporte

- HTTP/1.1 sem TLS, só na rede local. O cliente acha a ponte pela [descoberta](#wi-fi-e-descoberta-wifi_setup) e guarda
  o IP; se ele parar de responder, procura de novo. Não conte com nomes `.local`.
- A ponte só tem API. A única página é a de configuração do Wi-Fi, e só com a rede de configuração aberta.
- Sem autenticação, com exceção das rotas de envio do `update`, que pedem o cabeçalho `x-password`.
- Cada resposta fecha a conexão (`Connection: close`), com exceção de `/events`.
- Respostas em JSON, com `Cache-Control: no-store` e `Access-Control-Allow-Origin: *`.
- Erro: `400` ou `403` com `{"error": "texto"}`. Rota desconhecida: `404` em texto puro.

## `GET /device`

Quem é a ponte e o que ela sabe fazer. Não muda enquanto a ponte roda, então o cliente lê uma vez ao conectar e guarda.

```json
{"api": 1, "model": "Acoustic Solutions SP103", "bridge_version": "eb50a51b",
 "volume_db": {"min": -78.75, "max": 0, "step": 1.25},
 "tone_db": {"min": -14, "max": 14, "step": 2},
 "inputs": [{"id": "phono", "name": "PHONO"}, {"id": "tuner", "name": "TUNER"}, {"id": "tape_aux", "name": "TAPE/AUX"},
            {"id": "cd", "name": "CD"}, {"id": "dvd", "name": "DVD"}, {"id": "dab", "name": "DAB"}],
 "display": {"columns": 16, "rows": 2},
 "features": ["tone", "balance", "loudness", "speakers", "config", "vu", "info_screens", "bus_log", "update", "wifi_setup",
              "control"]}
```

| Campo | Significado |
|---|---|
| `api` | Versão do contrato. Só muda quando algo deixa de ser compatível; campos novos não mudam a versão |
| `model` | Nome para mostrar |
| `bridge_version` | Versão do firmware da ponte (a `version` do `GET /update`). Não é o `firmware` do estado, que é o do amp |
| `volume_db`, `tone_db` | Faixa e passo. `tone_db` é `null` se o amp não tem tom |
| `inputs` | `id` estável e `name` original no amp, na ordem do amp |
| `display` | Tamanho do display, ou `null` se a ponte não tem display |
| `features` | O que existe nesta ponte. Um cliente ignora o que não conhece e esconde o que não está na lista |

| Capacidade | O que indica |
|---|---|
| `tone`, `balance`, `loudness`, `speakers` | O amp tem esse controle e o estado traz o campo |
| `config` | `GET` e `PUT /names` |
| `vu`, `info_screens` | A ponte tem VU e telas de informação; exigem `config` |
| `bus_log` | As rotas `/bus.*` |
| `control` | Comandos ao amp, por `POST /control` e `POST /ir/send` |
| `update` | Atualização pela rede |

## `GET /state` e `GET /events`

As duas trazem o mesmo JSON. `/events` é Server-Sent Events: um `data: {json}` ao conectar e outro a cada mudança,
mais um comentário `: ping` a cada 1 s.

```json
{"power": "on", "volume_db": -20.0, "input": "DAB", "input_id": "dab", "input_name": "AirPlay/BT",
 "bass_db": 2, "treble_db": 0, "balance": {"side": "L", "db": -5.0}, "loudness": false, "speakers": true,
 "screen": "normal", "firmware": "1.0", "lcd": ["Volume -20.00 dB", "DAB             "],
 "updated_at": 3747990, "version": 5}
```

`null` ou campo ausente quer dizer **não se sabe**, nunca desligado ou zero. A ponte só conhece um valor depois que o
amp o mostra.

Os campos que o groove-rig lê (`power`, `volume_db`, `input_id`, `bass_db`, `treble_db`, `balance`, `loudness`,
`speakers`) seguem o `docs/state-provider.md` do groove-rig, que é o texto oficial deles. Os significados e valores no
SP103 estão em `docs/api-estado.md` do `sp103-display-proxy`. Os demais são extras:

| Campo | Significado |
|---|---|
| `input`, `input_name` | Nome original e nome personalizado da entrada |
| `screen` | A tela que o amp mostra agora. Os valores dependem do amp |
| `firmware` | Versão do firmware do amp, se ele mostrar |
| `lcd` | As linhas originais do display |
| `updated_at`, `version` | Relógio e contador da ponte. Voltam a 0 quando ela reinicia e só servem para comparar entre si |

## `GET /names` e `PUT /names` (`config`)

`GET` traz a configuração e o estado do que ela liga:

```json
{"config": {"inputs": {"TUNER": "Rega Planar 2"}, "boot": ["", ""], "about": ["Oceano Amp", "AS SP103"],
            "vu": {"on": true, "auto": true, "layout": "deck", "relay": "192.168.178.99"},
            "info": {"on": true, "mode": "temp", "show": ["stylus", "quality"],
                     "secs": 8, "clock": true, "utc_offset": 0, "eu_dst": true,
                     "source": "", "turntable": ["PHONO", "TUNER", "CD"]}},
 "inputs": ["PHONO", "TUNER", "TAPE/AUX", "CD", "DVD", "DAB"],
 "defaults": {"boot": ["ACOUSTIC", "SOLUTIONS"], "about": ["Amplifier SP103", "SW version 1.0"]},
 "proxy": {"reads": 11968, "writes": 11968, "busy_high": 0},
 "vu": {"on": true, "auto": true, "layout": "deck", "floor": -42, "top": -22, "frames": 139405, "last_frame_ms": 21,
        "music": false, "showing": false, "error": null},
 "info": {"on": true, "packets": 29362, "last_packet_ms": 578, "playing": false, "stream": null},
 "screens": {"on": true, "mode": "temp", "showing": null, "error": null}}
```

`PUT` recebe o objeto `config` e responde igual ao `GET`, ou `400` com `{"error": "..."}`, em inglês, pronto para mostrar.

**O `PUT` substitui tudo.** O que faltar no corpo volta ao padrão: mandar só `{"inputs": {...}}` desliga o VU e as telas
de informação. Para mudar um campo, o cliente lê o `config`, altera o campo e manda o `config` inteiro.

Regras de `config`:

| Campo | Regra |
|---|---|
| `inputs` | Chaves são os nomes **originais** (`"TAPE/AUX"`), não os `id`. Texto vazio = nome original |
| `boot`, `about` | Lista com 2 linhas. Texto vazio = texto original |
| Todos os textos do LCD | Até 16 caracteres, ASCII de `" "` a `"}"`, sem `"\"` e sem acentos |
| `vu.on` | Booleano |
| `vu.layout` | `bars`, `deck`, `scale` ou `kx393` |
| `vu.relay` | IPv4 da fonte do VU. Vem vazio; com `vu.on` verdadeiro, é obrigatório |
| `vu.auto` | Sempre `true`; a ponte ignora o valor enviado |
| `info.on`, `clock`, `eu_dst` | Booleanos |
| `info.mode` | `temp` (cada tela entra por `secs`) ou `fixed` (a tela da entrada de agora o tempo todo; sem VU) |
| `info.show` | Lista com `stylus` (entradas de `turntable`) e/ou `quality` (Bluetooth na DAB). `track`, `pos` e `side` (telas que saíram em 2026-11-07) são aceitos e ignorados, e também `fixed`, `alert` e `scroll` |
| `info.secs` | Inteiro de 3 a 60 |
| `info.utc_offset` | Horas de −12 a 14, em quartos de hora |
| `info.source` | IPv4, ou vazio para usar o mesmo de `vu.relay` |
| `info.turntable` | Lista de entradas, pelos nomes originais |

## `control`

O cliente pede o resultado, e a ponte cuida dos cliques no amp.

| Rota | O que faz |
|---|---|
| `POST /control?target=<t>&dir=<up ou down>` | Um passo. `t`: `volume`, `bass`, `treble` ou `balance` |
| `POST /control?target=<t>&on=<1 ou 0>` | Liga ou desliga. `t`: `loudness` ou `speakers` |
| `POST /control?target=key&name=<tecla>` | Uma tecla do controle, como `power_toggle` ou `select_cd`. Vale também em standby |
| `POST /ir/send?cmd=<comando>` | Uma tecla do controle, como `power_toggle` ou `select_cd`. A lista está em `GET /ir` |

`/control` responde com o estado depois da mudança, ou `400` com `{"error": "..."}`, em inglês, pronto para mostrar. A
resposta pode levar alguns segundos: balance, loudness e speakers andam pelo menu do amp, e o volume espera um menu
aberto fechar. Só um pedido por vez, e, com exceção de `target=key`, só com `power` = `on`. Passos seguidos reaproveitam
o menu aberto.

`power_toggle` liga e desliga: o cliente deve conferir o `power` antes. No SP103, um clique no menu às vezes também troca
a entrada para PHONO por cerca de 1 s, até a ponte devolver a anterior.

## `bus_log`

| Rota | O quê |
|---|---|
| `GET /bus.json` | Estatísticas do barramento do display |
| `GET /bus.csv?tz=<minutos>` | As últimas palavras lidas, em CSV (até 8192 linhas, sem `Content-Length`) |
| `POST /bus/clear` | Zera o registro e as estatísticas |

```json
{"since_s": 146828, "words": 23936, "writes": 11968, "reads": 11968, "power_ons": 0, "screens": 172,
 "unknown_screens": 0, "last_screen_s": 299, "max_gap_ms": 10033, "max_batch": 1152, "maybe_lost": false,
 "log_words": 8192, "log_size": 8192, "log_span_s": 7586, "clock": "2026-11-04 14:21:35.236",
 "lcd": ["Volume -38.75 dB", "DAB             "]}
```

`max_gap_ms` é a maior pausa do laço da ponte. Perto de 10000 é o travamento de 10 s do lwIP.

## Wi-Fi e descoberta (`wifi_setup`)

Para configurar o Wi-Fi da ponte sem cabo e achá-la sem IP digitado. Decidido e testado na bancada em 2026-11-08; os
detalhes do lado da ponte estão em `docs/wifi.md`, no repositório sp103-display-proxy.

**Descoberta.** O cliente manda `AMPLINK?` por broadcast UDP na porta **47800**, três vezes em uns 2 s (o primeiro
pacote às vezes se perde), e cada ponte responde ao remetente:

```json
{"name": "SP103-D85E", "model": "sp103", "ip": "192.168.1.77"}
```

**A rede de configuração.** Sem rede salva, ou sem conseguir conectar por 2 minutos, a ponte abre a própria rede
`AmpLink-<name>` (por exemplo `AmpLink-SP103-D85E`), WPA2, senha fixa **`amplink-setup`**, e continua tentando a rede de
casa. Nela, a ponte é `192.168.4.1`. Todas as redes de configuração começam com `AmpLink-`: no Android, a app pede uma
rede com esse começo (`WifiNetworkSpecifier`) e o sistema mostra as que servem, sem permissão de localização.

| Rota | O quê |
|---|---|
| `GET /wifi` | `{"state", "detail", "ip", "ssid", "setup": {"open", "ssid"}}`. `state` e `detail`: a última tentativa (`idle`, `connecting`, `connected`, ou `failed` com o motivo, para mostrar como está). `ip`: o endereço de agora na rede de casa. `ssid`: a rede salva |
| `GET /wifi/networks` | As redes que a ponte vê, `[{"ssid", "rssi", "secure"}]`, da mais forte para a mais fraca, até 20. Leva ~1 s |
| `PUT /wifi` | `{"ssid", "psk"}` (`psk` vazio = rede aberta; senão de 8 a 63 caracteres). `202` na hora; o resultado sai no `GET /wifi`. Só com a rede de configuração aberta, senão `403` |
| `POST /wifi/setup` | Abre a rede de configuração por 10 minutos, sem largar a rede de casa. Para trocar de rede com a ponte conectada |
| `DELETE /wifi` | Esquece a rede salva. Só com a rede de configuração aberta |

**O fluxo da app:**

1. Entrar na rede `AmpLink-…` e ler `GET /wifi/networks`.
2. `PUT /wifi` com a rede escolhida, e ler `GET /wifi` a cada segundo até `connected` ou `failed`. Algumas respostas se
   perdem no meio: o rádio da ponte muda para o canal da rede de casa, e a rede de configuração vai junto. A ponte
   desiste de uma rede em 15 s e então volta para a anterior; espere até uns 40 s.
3. Com `connected`, guardar o `ip`, sair da rede de configuração (ela fecha sozinha 60 s depois) e conferir o
   `GET /device` nesse IP. Se não responder, achar a ponte pela descoberta, pelo `name`.
4. Com `failed`, mostrar o `detail` e deixar escolher de novo: a ponte voltou para a rede anterior, e a de configuração
   continua aberta.

## Para o cliente

1. **Uma conexão `/events` por cliente**, e só na tela que mostra o estado ao vivo. A ponte guarda uma conexão por IP e
   poucas no total (3 no SP103): uma conexão nova do mesmo IP derruba a antiga, e com o teto cheio sai a mais antiga.
2. **Feche o `/events` quando a app for para segundo plano.** Uma conexão morta, como a de um celular dormindo, prende a
   memória de rede da ponte e pode travar o display por 10 s.
3. **Sem nada por 5 s, considere o estado desconhecido** e reconecte com espera crescente, de 1 s a 30 s.
4. **As outras rotas são sob demanda:** um pedido ao abrir a seção, sem repetição. A exceção é `/bus.json`, no máximo a
   cada 2 s enquanto a tela estiver aberta.
5. **Espere ao menos 1 s depois da última alteração antes do `PUT /names`.** Cada `PUT` grava na flash e redesenha o
   display, então a ponte não deve receber um por toque.
6. **Baixe o `/bus.csv` só a pedido.** É a resposta mais pesada da ponte.
7. **Não trate `null` como desligado.** Depois de a ponte reiniciar com o amp em standby, `power` fica `null`.
8. **A descoberta é a pedido:** ao abrir a app sem o IP guardado responder, ou quando a pessoa pede. Não fique mandando
   broadcast em segundo plano.

## Em aberto

Decidir quando o MR 780 for aberto, porque dependem de haver um segundo amp:

- **`/names`:** o nome e a estrutura são do SP103. Pode virar `/config`, com as entradas pelo `id`.
- **`/bus.*`:** o formato vem do HD44780, e o MR 780 pode ter outro display.
- **`screen`:** os valores são do SP103.
