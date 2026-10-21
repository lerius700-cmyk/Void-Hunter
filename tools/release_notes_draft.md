# VOID HUNTER v1.4.0 — Release Notes

> ✅ El primer release oficial del juego con sources abiertos y tagged en GitHub.
>
> Este release se construye desde el commit [`d70b8da` ("BLOQUE 71 - release v1.4.0")](https://github.com/lerius700-cmyk/Void-Hunter/releases/tag/v1.4.0).

---

## 🎮 What's in v1.4.0

<!-- USER: rellená estos bullets con la prosa final. Estructura: feature → benefit → how-to-try -->

- **Boss GOLIATH rediseñado** (BLOQUE 64.B/64.C) — 6 animaciones × 10 frames cada una, generadas con prompts pose-específicos para que cada frame capture una pose distinta en vez de crowd frames.
- **Sistema de shield + laser (BLOQUE 65)** — 20 hits al escudo del boss desencadenan un láser cargado con su propio beam. Color del escudo interpola de gris → rojo → naranja al cargarse.
- **Boss-tester dev loop (`--boss-test --easy --scale 2`)** (BLOQUE 66.3) — salta directo a la pelea de GOLIATH para iterar visuales y balance sin jugar todo el act 1.
- **Audio continuo 5:30** (BLOQUE 58.14) — las BGM streamean desde assets, pause = lowpass en vivo, sin loops visibles.
- **Star Fox 64 formations + bezier paths** (BLOQUE 58.14.x) — enemigos siguen trayectorias curvas reales, no patrones rígidos.
- **Mode roguelike con seed/RNG** (BLOQUE 58.59) — las mismas reglas generan niveles reproducibles vía seed.

## 🔧 Fixed

<!-- USER: bugs notables que arreglaron los BLOQUE 60-66 -->

- (Round de visual GOLIATH: oval-sized, hitbox pixel-perfect, eye laser mismatch)
- (Asteroid camouflage overhaul)
- (Test paths / sprite scale)
- (Sub-boss flow timing)

## ⚠️ Known limitations (not blocking play)

- **Source ↔ binary gap** (documentado en [`KNOWN_ISSUES.md`](../KNOWN_ISSUES.md) ISSUE-001): el source commiteado a la rama master está al BLOQUE 66.6 con cherry-picks; el binario `v1.4.0-win64.zip` fue construido del BLOQUE 71. La diferencia es transparente para el jugador pero la documentamos para audit purposes. El próximo BLOQUE syncea source ↔ binary.
- **Tests pre-existentes fallan** (`KNOWN_ISSUES.md` ISSUE-002): algunos tests asumen paths hardcodeados a `D:\AI\void-hunter\...` (workspace viejo). No afectan el juego.
- **`CLAUDE.md` queda stale** (`KNOWN_ISSUES.md` ISSUE-003): reporta "v1.2.5" — esto se sincroniza cuando se resyncee source ↔ binary.

## ⬇️ Cómo instalar / jugar

1. Descargá `VoidHunter-v1.4.0-win64.zip` (379 MB).
2. Extraé en cualquier carpeta.
3. Doble-click en `void-hunter.exe`.
4. Smoke-test del dev loop:
   ```powershell
   void-hunter.exe --boss-test --easy --scale 2 --duration 60
   ```
   salta directo a la pelea con GOLIATH y corre 60 segundos.

## 💻 Requisitos del sistema

- **OS**: Windows 10 / 11 (64-bit)
- **Espacio**: ~400 MB en disco después de extraer
- **RAM**: ~150 MB durante el juego
- **GPU**: cualquier GPU compatible con DirectX 9 (recomendado)
- **.NET**: bundled (no requiere instalación aparte)

## 👏 Créditos

- **Game design + code**: Lerius
- **BLOQUE 71–73 polish**: lerius700-cmyk
- **AI asset generation**: depende del frame (`docs/superpowers/specs/2026-10-12-goliath-canonical-model-design.md` documenta los prompts)
- **Software**: Python 3.12, pygame 2.6, NumPy, PyInstaller 6.x

## 🐛 Reportar bugs

Abrí un issue en https://github.com/lerius700-cmyk/Void-Hunter/issues con:
- Commit hash del binario (verificá con `void-hunter.exe --version` cuando esté implementado)
- Pasos para reproducir
- Versión de Windows
- Screenshot si aplica
