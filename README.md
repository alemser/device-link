# amp-link

O que liga os amplificadores modificados aos outros aparelhos: o contrato e a app Android.

Uma **ponte** é a placa instalada dentro do amp, que lê o que ele mostra e publica na rede. Um **cliente** é quem usa
esses dados: a app Android, o groove-rig, um `curl`.

| Onde | O quê |
|---|---|
| [docs/contrato.md](docs/contrato.md) | O contrato entre pontes e clientes (rascunho) |
| `android/` | A app Android |

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
