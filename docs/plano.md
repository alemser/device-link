# Plano

O caminho é o mesmo do SP103: primeiro olhar e medir, depois capturar, só então soldar. As decisões de 2026-10-28 a
2026-10-30 estão em `docs/historico/brief-2026-10.md`; este documento é o plano em vigor.

## Segurança

- O MR 780 é ligado direto na tomada (230 V) e tem válvulas: **dentro há tensões altas**, também alguns minutos depois
  de desligar (capacitores). Sempre: chave traseira em OFF, cabo fora da tomada, esperar uns 5 minutos.
- Não encostar na fonte (`MR780-SMPS-D`) nem na placa das válvulas.
- A placa do display tem a fonte do VFD (Q1, DW1, D2–D4, eletrolíticos de 50 V): **dezenas de volts**. Ligar fios só
  nas vias de lógica do cabo flat, e só depois de medir cada uma.
- O GPIO do Pico é de 3,3 V. Se o barramento do VFD for de 5 V, cada fio passa por um divisor ou conversor de nível.
- Fios só com o amp fora da tomada.

## Objetivos (dono, 2026-11-07)

1. **Saber o estado do amp**: ligado ou standby, entrada, volume, DIRECT, texto do DAB/FM.
2. **Mudar o que ele escreve no display.**
3. **Comandar sem depender do controle remoto pelo ar** (sem Broadlink).
4. ~~Um Raspberry Pi Zero 2 WH dentro do amp~~: **descartado** (dono, 2026-11-08). Ver abaixo.
5. Bônus: **grave e agudo** pelo Wi-Fi, e **ligar ou desligar o DIRECT**.

O que as fotos já dizem sobre cada um:

| Objetivo | Como | Situação |
|---|---|---|
| 1. Estado | O Pico escuta as vias de dados do VFD no cabo flat e remonta as telas, como no SP103. Ligado ou standby por um sinal da placa principal (`APD`, `SYS` ou `POW/OF`) | Viável. Falta medir as vias |
| 2. Mudar o display | O Pico no meio das vias de dados, entre duas extensões do flat | Viável, depende do protocolo (capturas) |
| 3. Comandos sem IR pelo ar | (a) Mandar os códigos do controle remoto **por fio**, direto na saída do receptor de IR, como no SP103 (não passa pelo ar). (b) Imitar os botões do painel (ON/STBY, DIM, DIRECT, ◄◄, ►►, MONO). (c) Imitar o giro dos botões SOURCE e VOLUME, se forem encoders | (a) é o caminho que já funciona no SP103. (b) e (c) dependem de como os botões chegam à placa principal: quase certo que pelo mesmo cabo flat |
| 4. Pi Zero dentro do amp | — | Descartado (2026-11-08) |
| 5a. DIRECT | O controle remoto não tem DIRECT, então é imitar o botão do painel (3b). O estado já aparece no display ("DIRECT ON") | Provável |
| 5b. Grave, médio, agudo | Ver abaixo | Difícil |

### Sem Pi Zero dentro do amp (dono, 2026-11-08)

Diferente do SP103, o MR 780 **não leva um Raspberry Pi Zero 2 W dentro**. Dois motivos:

- **Alimentação:** não entra fonte nova no amp, e puxar 2 a 3 W da linha `VCC` da placa principal (por um DC-DC)
  arrisca a folga do transformador e da parte digital do Magnat.
- **Interferência:** um computador com Wi-Fi e clock de GHz dentro de um amp com válvulas, phono e controle de tom
  analógico pode meter ruído no som ou atrapalhar a eletrônica.

Fica só o **Pico 2 W**, que gasta pouco (uns 50 a 100 mA em 5 V, com Wi-Fi) e é alimentado pelo `D5V`, a linha que
fica ligada em standby. Ainda assim, medir a folga do `D5V` antes (passo 2, item 5) e testar se o Wi-Fi do Pico
interfere no som (passo 2b).

### Grave, médio e agudo

Os botões BASS, MID, TREBLE e BALANCE estão numa placa comprida no painel, cheia de capacitores de áudio. Isso indica
um controle de tom analógico, com os potenciômetros direto no sinal (diferente do volume, que é lido pelo
microcontrolador). Se for isso, comandar pelo Wi-Fi exige trocar os potenciômetros por potenciômetros digitais de
áudio que aguentem ±12 V: dá, mas mexe no caminho do som e é um projeto à parte. Confirmar com fotos dessa placa.

O DIRECT desliga o controle de tom. Então "ligar e desligar o tom" pelo Wi-Fi já vem com o DIRECT.

## Fases (decisão do dono, 2026-10-30)

**Fase 1: ler o estado.** Saber o que vai para o display e se o amp está ligado ou em standby. Um Pico 2 W dentro do
amp, só escutando o cabo flat. Nada cortado.

**Fase 2: escrever no display e comandar.** O Pico no meio das vias de dados do VFD: lê o que a placa principal manda
e escreve a sua versão no display. As outras vias passam direto. Como o VFD tem fonte própria e (pelas fotos)
controlador próprio, dá para escrever qualquer texto. Junto: os comandos (IR por fio e os botões do painel).

~~**Fase 3: Pi Zero 2 WH dentro do amp**~~: **descartada** em 2026-11-08 (ver "Sem Pi Zero dentro do amp"). O
projeto termina na fase 2, só com o Pico.

## O cabo flat (medido em 2026-10-30)

- 21 vias, passo de 1,0 mm, ~22 mm de largura.
- **Comprados em 2026-11-08** (a caminho): a extensão e o flat.
- Material escolhido: uma **extensão FFC 22P de 1,0 mm** (existe pronta), com o flat de 21 encostado no pino 1 e a
  folga do pino 22 calçada com plástico ou kapton. **Testar a continuidade via a via antes de ligar.** Flats de 21P,
  1,0 mm, ~10 cm, dos dois tipos (A e B), porque não dá para ver de que lado estão os contatos.
- Para a fase 2: duas extensões, com o Pico entre elas.
- Os fios do Pico vão soldados na extensão, nunca na placa do Magnat.

## Passo 1: fotos

**Feito** (2026-10-30 e 2026-11-07, `docs/img/`, resumo em `pesquisa-display.md`).

**Ainda falta, de perto e com luz:**

- A marca no vidro do VFD (canto direito, parece "CN20-..." ou "CN23"): pode dar o modelo e a pinagem.
- As legendas dos pinos do flat, dos dois lados (placa do display e a placa principal).
- O texto do microcontrolador U17 (64 pernas) e do U15 (ao lado do flat).
- A placa dos botões BASS, MID, TREBLE e BALANCE, dos dois lados (para saber se o tom é analógico).
- Os botões SOURCE e VOLUME por trás: encoder (gira sem fim, com cliques, 3 pernas e às vezes mais 2) ou
  potenciômetro.

## Passo 2: multímetro

**Fora da tomada: feito em 2026-11-07** (`docs/medicoes.md`): itens 1 e 6. Do item 4 já se sabe o pino (o sinal do
receptor vai ao pino 21); falta a tensão. Os itens 2 a 5 são com o amp ligado.

1. Amp fora da tomada: continuidade de cada via do flat com o GND.
2. Amp **em standby** e depois **ligado**: tensão de cada via do flat contra o GND. Anotar numa tabela de 21 linhas.
   Isso separa as vias de lógica (0 V, 3,3 V ou 5 V) das de tensão alta.
3. Os fios `D+5V`, `APD`, `SYS` e `POW/OF`: qual tem 5 V em standby (para alimentar o Pico) e qual muda ao ligar
   (para o Pico saber se o amp está ligado).
4. A saída do receptor do controle remoto (para comandar o amp pelo Wi-Fi, como no SP103).
5. O conector de força da placa principal: a tensão do `D5V` em standby e ligado (para alimentar o Pico). O `VCC`
   não precisa mais (era para o Pi Zero, descartado em 2026-11-08).
6. Os botões do painel: em quais vias do flat eles aparecem, e se cada botão tem o seu fio ou se vários dividem um fio
   com resistores diferentes (escada de resistores lida pelo microcontrolador). Muda o jeito de imitá-los.

## Passo 2b: teste de interferência do Wi-Fi (dono, 2026-11-08)

Antes de ligar qualquer fio no Magnat: ver se o Wi-Fi do Pico atrapalha o som, e achar o melhor lugar para ele.

**Montagem:**

- O Pico alimentado por um **power bank**, sem nenhum fio até o amp.
- Um programa de teste que fique **transmitindo sem parar** pelo Wi-Fi (por exemplo, mandando pacotes UDP para o Mac),
  para o pior caso.
- O Pico **dentro de um saquinho ou caixinha de plástico**, preso na ponta de um palito ou régua de madeira: com o amp
  aberto e ligado, nenhum pino pode encostar em nada, e a mão fica longe. Não chegar perto da fonte
  (`MR780-SMPS-D`) nem da placa das válvulas.

**O que ouvir:** só o **PHONO** (decisão do dono, 2026-11-08), sem disco e com o volume alto, com o Pico perto de
cada placa (phono, tom, principal, display) e depois longe de tudo. Procurar chiado, estalos ou zumbido que mudem
quando o Pico chega perto. O phono é a entrada mais sensível: se ali não aparece nada, nas outras (CD, AUX, entradas
digitais) também não deve aparecer. A exceção possível é o FM e o DAB, que sofrem por outro motivo (harmônicos do
clock do Pico na faixa do rádio); se um dia uma estação piorar com o Pico instalado, a suspeita é essa.

**Anotar** em `docs/medicoes.md`: em que lugar apareceu algo, o quê, e a potência do sinal do Wi-Fi do Pico
(RSSI) com a tampa fechada. O chassi de metal funciona como blindagem: se o sinal ficar fraco lá dentro, o Pico
retransmite mais, o que piora a interferência e a estabilidade.

**Como ler o resultado:**

- Nada aparece: seguir. Se depois, com o Pico alimentado pelo `D5V`, aparecer ruído, o culpado é o terra ou a
  alimentação, não o rádio (ligar só no `D5V`/`DGND`, nunca no `AGND`, com um capacitor na entrada do Pico).
- Aparece só perto de uma placa: o Pico fica longe dela.
- Aparece em todo lugar: pensar em antena externa ou outro jeito antes de seguir.

## Passo 3: analisador lógico

O mesmo Pico com o LogicAnalyzer usado no SP103, nas vias de lógica:

- Telas: ligar (contagem do aquecimento), volume, cada entrada, DIM, DIRECT, INFO no DAB e no FM, Bluetooth.
- O controle remoto: só o que falta. O `groove-rig` já tem códigos do MR 780
  (`internal/catalog/profiles/magnat_mr780.yaml`): **NEC, endereço 40/BF**, com `next_input` (cmd 1A), `prev_input`
  (1E) e `volume_down` (1F), no formato do Broadlink. Faltam lá o power e o volume up (nunca capturados limpos;
  podem estar aprendidos só no oceano) e o ◄◄ e ►► (anterior e próxima no Bluetooth), mais o que mais o controle
  tiver. Como o controle não precisa do amp, dá para capturar na mesa, com um receptor de IR de 38 kHz.

Decodificar e documentar em `docs/descobertas-protocolo.md`, com as capturas em `captures/`.

## Passo 4: o programa (fase 1)

Aproveitar do `sp103-display-proxy` o que não depende do display:

- Wi-Fi e atualização pelo Wi-Fi com volta automática (`ota.py`, `tools/enviar.py`).
- O estado e o contrato da app Amp Link (`/state`, `/device`, `/names`), com campos novos: fonte DAB/BT/USB, estação,
  texto do DAB/RDS.
- Os testes no Mac, usando as capturas reais.

Novo: o sniffer do VFD serial (PIO) e o leitor das telas do MR 780.

**Feito em 2026-11-09, sem o amp: a base** (`firmware/ponte.py`). O Wi-Fi sem cabo (`wifi.py`, a mesma configuração
do SP103: rede `AmpLink-MR780-XXXX`, senha fixa, descoberta por broadcast UDP; detalhes em
`sp103-display-proxy/docs/wifi.md`), a atualização pelo Wi-Fi (`ota.py`, `main.py`, `tools/enviar.py`, que também acha
o Pico pela descoberta) e o `/device` (15 entradas com os ids do groove-rig). O `/state` existe, todo `null`. Falta:
o sniffer, o leitor das telas e os comandos.

Lições do SP103 que já valem aqui:

- Sem página web no Pico: a app Android faz esse papel. A exceção é a página de configuração do Wi-Fi, que só existe
  com a rede de configuração aberta.
- Evitar conexões longas (`/events`) e respostas grandes: elas travam o Wi-Fi do Pico (lwIP sem memória).
- Copiar cada parte do SP103 só quando ela for usada, para não carregar código morto.

## O que a app Amp Link precisa ganhar

O `GET /device` já descreve o aparelho. O MR 780 vai ser um segundo aparelho na mesma app, com a sua lista de entradas
e sem ajuste de grave, médio, agudo e balanço (são botões giratórios no MR 780).

## Perguntas em aberto

- O que mostrar no display na fase 2: os mesmos objetivos do SP103 (nomes, VU, agulha, qualidade do Bluetooth) ou
  outros?
