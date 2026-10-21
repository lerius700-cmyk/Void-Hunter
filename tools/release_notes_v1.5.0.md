# VOID HUNTER v1.5.0 — 4-Weapon Powerup System

> Primer release que incluye el sistema completo de powerups de armas.
> Construido desde `master` @ BLOQUE 73.

---

## 🎯 Qué trae esta versión

### Sistema de 4 armas (BLOQUE 72 + 73)

El jugador ahora puede recoger y alternar entre **4 armas distintas**, cada una
con su propio comportamiento de disparo, sonido, y sprite de bullet:

| Arma | Comportamiento | Ammo por pickup |
|------|----------------|-----------------|
| **THICK** | Disparo pesado, daño alto, cadencia lenta | 100 |
| **LASER** | Rayo rápido continuo | 200 |
| **FLAME** | Fuego continuo (audio con loop dedicado) | 50 |
| **DOUBLE** | Disparo doble simultáneo | 150 |

- **Weapon slots en el HUD** — la barra inferior muestra el arma activa y el
  ammo restante. Cambia de color cuando el ammo baja.
- **POP animation** al recoger un powerup — feedback visual de 0.3s para que
  el jugador registre el cambio.
- **Input remap** — los slots respondien a teclas numericas y ciclo con una
  tecla dedicada.
- **SFX por arma** — 4 sonidos procedurales (`shoot_thick`, `laser_hum`,
  `flame_loop`, `shoot_double`) generados con el sintetizador del proyecto,
  sin assets externos.
- **Sprites de bullet procedurales** — los 4 PNGs de bullet se generan via
  PIL en tiempo de build, sin assets que mantener a mano.

### Boss GOLIATH

El jefe conserva el redesign completo (6 animaciones × 10 frames):
`phase1_idle`, `phase2_idle`, `javelin`, `laser`, `purple_bullet`, `death`.
GOLIATH aparece a los 3:40 de la canción (220s) para que el jugador
siempre lo encuentre.

### Audio

- BGM de 5:30 que streamea desde assets (no loop visible)
- Pause = lowpass real en vivo (numpy, audio unicamente)
- 24 SFX procedurales sintetizados

---

## 🔧 Fixes

- **Laser de carga del escudo removido** — el LMB max-charge laser se
  eliminó en BLOQUE 73 Fase A. El escudo dispara su propio laser al
  cargarse, no el jugador.
- **Per-weapon fire functions** — cada arma tiene su propia logica de
  disparo en lugar de compartir una generica con flags.
- **Asteroid hit feedback** — flash blanco 70% opaco que respeta la
  silueta original (v1.4.0, se mantiene aqui).

---

## ⚠️ Limitaciones conocidas

- **Source ⇔ binary**: este `.exe` fue compilado desde `master` @ BLOQUE 73,
  asi que source y binario **estan sincronizados** en esta version. Las
  issues históricas de divergencia estan documentadas en
  [`KNOWN_ISSUES.md`](https://github.com/lerius700-cmyk/Void-Hunter/blob/master/docs/KNOWN_ISSUES.md).
- **Tests pre-existentes fallan** (~31 tests) por paths hardcodeados a un
  workspace anterior. No afectan el juego — son `FileNotFoundError` de
  tiles de background. Detalle en `KNOWN_ISSUES.md` ISSUE-002.
- **CLI cambiado**: `--boss-test` ahora es `--boss {goliath,hydra,phantom,nemesis}`.

---

## ⬇️ Como jugar

1. Descargá `VoidHunter-v1.5.0-win64.zip` (~422 MB).
2. Extraé en cualquier carpeta.
3. Doble-click en `void-hunter-v1.5.0.exe`.

### Flags utiles para testeo

```powershell
# Pelea directa contra GOLIATH
void-hunter-v1.5.0.exe --boss goliath --easy --duration 60

# Act especifico
void-hunter-v1.5.0.exe --act 1

# Campaña completa (default)
void-hunter-v1.5.0.exe --campaign

# Escala de ventana
void-hunter-v1.5.0.exe --scale 2
```

> **Nota**: los flags usan el **nombre del ejecutable** como prefijo
> (`void-hunter-v1.5.0.exe --help`), no `void-hunter.exe`.

---

## 💻 Requisitos

- **OS**: Windows 10 / 11 (64-bit)
- **Espacio**: ~430 MB
- **RAM**: ~200 MB durante el juego
- **GPU**: cualquier GPU compatible con DirectX 9
- **.NET**: no requiere instalación (bundled)

---

## 📚 Documentación

- `docs/OPERATIONS.md` — guia de `gh` CLI, PAT, y workflow de releases
- `docs/KNOWN_ISSUES.md` — issues conocidos con planes de fix
- `docs/superpowers/specs/` — specs de diseño por BLOQUE
- `docs/superpowers/plans/` — planes de implementación
- `CLAUDE.md` — identidad del proyecto, arquitectura, protocolos