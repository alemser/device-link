# amp-link

O que liga os amplificadores modificados aos outros aparelhos: o contrato e a app Android.

Uma **ponte** é a placa instalada dentro do amp, que lê o que ele mostra, publica na rede e recebe comandos. Um
**cliente** é quem usa a ponte: a app Android, o groove-rig, um `curl`.

| Onde | O quê |
|---|---|
| [docs/contrato.md](docs/contrato.md) | O contrato entre pontes e clientes (rascunho) |
| `android/` | A app Android |

A app acha a ponte sozinha na rede, sem IP digitado, e configura o Wi-Fi de uma ponte nova pela rede `AmpLink-…` que ela
abre (contrato, "Wi-Fi e descoberta"). O IP ainda pode ser digitado, em "Type the address".

O firmware de cada amp fica no repositório dele. O do Acoustic Solutions SP103 está em `sp103-display-proxy`. O Magnat
MR 780 ainda não foi modificado.

Projeto pessoal: a app é só para Android, sem publicação na Play Store.

## Compilar

Precisa do JDK 17 (`brew install openjdk@17`) e do Android SDK, com `sdk.dir` em `android/local.properties`.

```sh
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
android/gradlew -p android testDebugUnitTest assembleDebug
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
```

`tools/fake_bridge.py` é uma ponte falsa para testar a app sem mexer no amp. Ela usa o `names.validate` do firmware de
verdade. No emulador, o computador é o IP `10.0.2.2`, e a ponte falsa precisa estar na porta 80.
