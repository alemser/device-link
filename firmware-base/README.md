# A base comum das pontes

O que toda ponte tem, seja de qual aparelho for: o Wi-Fi sem cabo, a descoberta, a atualização pelo Wi-Fi e o servidor
HTTP. Fica aqui num lugar só. Cada projeto de ponte recebe uma **cópia igual**, feita pelo `copiar.py`, e o
MicroPython do Pico roda a cópia.

## O que tem

| Arquivo | O que faz |
|---|---|
| `firmware/wifi.py` | A rede de casa, a rede de configuração `AmpLink-…` e a descoberta (contrato, "Wi-Fi e descoberta") |
| `firmware/web.py` | O servidor HTTP: `/state`, `/events` e as rotas que a ponte registra |
| `firmware/listeners.py` | Quem pode ficar ligado no `/events` |
| `firmware/ota.py` | A atualização pelo Wi-Fi, com senha e volta automática |
| `firmware/main.py` | O porteiro das atualizações. Importa o `ponte.py` do projeto. Só vai ao Pico pelo cabo |
| `firmware/udp.py` | Ler um socket UDP sem esperar |
| `tools/enviar.py` | Envia o programa novo para o Pico pelo Wi-Fi |
| `tools/test_wifi.py`, `tools/test_listeners.py` | Os testes da base, no computador |

## O que cada projeto precisa ter

- `firmware/device.py` com `NAME` (por exemplo `"mr780"`): o nome da ponte na descoberta e na rede. O
  `tools/enviar.py` lê esse nome.
- `firmware/ponte.py`: o programa da ponte, que o `main.py` importa.
- `firmware/secrets.py` (fora do git), a partir do `secrets.example.py` do projeto.

## Usar

Na pasta do projeto da ponte:

```sh
python3 ../amp-link/firmware-base/copiar.py              # copia o que mudou
python3 ../amp-link/firmware-base/copiar.py --conferir   # só confere
```

Depois, os testes do projeto e o commit das cópias no repositório dele.

**Mudar um arquivo da base:** mudar aqui, rodar os testes daqui (`python3 firmware-base/tools/test_wifi.py` e
`test_listeners.py`), e copiar para cada projeto. Nunca mudar a cópia: a próxima cópia apaga a mudança, e o
`--conferir` acusa.

## Quem usa

| Projeto | Situação |
|---|---|
| `mr780-mod` | Usa a base (2026-11-16) |
| `cds300-mod` | Usa a base (2026-11-16) |
| `sp103-display-proxy` | **Ainda não.** A base saiu dos arquivos dele, mas o `web.py` de lá tem o `/names` dentro e o `main.py` importa o `escuta.py` e escreve no LCD. O `wifi.py`, o `ota.py`, o `udp.py` e o `listeners.py` só diferem em comentários |
