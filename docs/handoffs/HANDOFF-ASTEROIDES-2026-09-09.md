# HANDOFF — Trabajo futuro en asteroides (void-hunter)

> **Para el siguiente agente que trabaje en asteroides / MINE-ASTEROID.**
> **Fecha:** 2026-09-09 17:13 GMT-5
> **Contexto:** sesión cerrada por Lerius después de BLOQUE 70 (release v1.3.0).

---

## TL;DR

v1.3.0 está en GitHub. La regla 25% minas / 75% indestructibles **ahora funciona en gameplay** (estaba rota por un `NameError` silencioso). 44/44 tests MINE-ASTEROID pass. 1,639 pass en suite completa + 6 pre-existing failures (sin nuevas). El trabajo de asteroides está cerrado en su mayoría — lo que queda son **pulidos y decisiones de diseño**, no bugs.

**Si vas a trabajar en asteroides, lee este documento completo. Si vas a hacer otra cosa (GOLIATH, ship redesign, etc.), ve a la sección "Other BLOQUE work" al final.**

---

## 1. Estado actual del proyecto

| Item | Valor |
|---|---|
| **Path** | `D:\AI\void-hunter` |
| **Versión** | v1.3.0 (commit `7198b91` pusheado) |
| **Tag** | `v1.3.0` en `origin/master` |
| **Release GitHub** | https://github.com/lerius700-cmyk/Void-Hunter/releases/tag/v1.3.0 |
| **.exe** | `D:\AI\void-hunter\dist\void-hunter.exe` (378 MB, build 3:49 PM 2026-09-09) |
| **.zip** | `D:\AI\void-hunter\dist\VoidHunter-v1.3.0-win64.zip` (377 MB) |
| **Stack** | Python 3.11 + pygame 2.6, sin numpy en runtime |
| **Tests** | 44/44 MINE-ASTEROID, 1,639 suite + 6 pre-existing failures |
| **Display** | 240×360 escalado 2.1× a 674×1011 (internal 320×480) |

---

## 2. La feature de asteroides — qué hace y qué NO hace

### Qué hace (verificado en gameplay)

- **Cada 3-5s se spawnea un obstáculo.** 25% de las veces es un MINE-ASTEROID, 75% es un regular asteroid.
- **Regular asteroid**: sprite brown/rocky (5 variantes: round/elongated/spiked/hollowed/cracked). Drifts down. **`hit()` es no-op, no se destruye.** Pasa de largo.
- **MINE-ASTEROID** (closed state): sprite brown/rocky idêntico al regular (camuflaje). Drifts down. **`hit()` retorna False — es inmune hasta que se abre.**
- **MINE-ASTEROID** abre cuando cruza `y >= 120` (primer cuarto del playfield 480px). Animación de apertura: `closed → open1 (0.2s) → open2 (0.2s) → open3 (terminal)`.
- **MINE-ASTEROID** en `open3`: vulnerable (HP=3, red flash 0.2s por hit). Dispara 3-bullet fan (±15°, 80 px/s) **cada 1.0s** mientras esté vivo.
- **Al destruirse** (HP=0): 50% chance de dropar powerup (BOMB/HP/WEAPON, no SCORE).

### Qué NO hace / no existe

- **NO hay línea amarilla visible.** El threshold es invisible.
- **NO hay powerups de regular asteroids** (indestructibles no dropean nada).
- **NO hay rotación** en los sprites (BLOQUE 61 lo quitó para hacer el camo del MINE creíble).
- **NO hay sonido** asociado al MINE abriendo o disparando (solo el generic SFX pool).
- **NO hay "asteroide que se rompe en pedazos"** — son sprites estáticos.

---

## 3. Arquitectura del sistema

### Archivos clave (lee en este orden)

1. `src/entities/enemies/enemy.py:108-147` — `spawn_obstacle(rng)`. Decide 25% mine / 75% regular.
2. `src/entities/enemies/enemy.py:861-990` — `_update_mine_asteroid(dt)`. State machine 4-state: closed → open1 → open2 → open3.
3. `src/entities/enemies/enemy.py:74` — `MINE_SPAWN_FRACTION: float = 1.0 / 4.0` (25%).
4. `src/entities/enemies/enemy.py:58` — `OPENING_Y_THRESHOLD: int = 120` (primer cuarto del playfield 480).
5. `src/entities/enemies/enemy.py:75-78` — `MINE_FIRE_INTERVAL_S: float = 1.0` (1Hz fire).
6. `src/entities/enemies/enemy.py:65-67` — `MINE_FAN_ANGLE_DEG = 15.0`, `MINE_FAN_BULLET_SPEED = 80.0`.
7. `src/ui/gameplay_runtime.py:1660-1730` — spawn site. **CRÍTICO**: línea 1680 importa `Asteroid`. Verificar que el import incluye `Asteroid` (este fue el bug del BLOQUE 70).
8. `src/ui/gameplay_runtime.py:1754-1780` — `_asteroid_bullet_collision`. Bullet muere al hit, asteroid no.
9. `src/ui/gameplay_runtime.py:1941-2019` — integration site de fire. Lee `enemy.on_fire`, llama `_fire_mine_bullets`.
10. `src/entities/asteroid.py:74-180` — `Asteroid` class. `hit()` no-op. **Indestructible**.
11. `src/entities/asteroid.py:243-273` — `spawn_asteroid(rng)`. Genera un regular asteroid (variant, scale, drift).
12. `src/core/settings.py:19` — `WINDOW_TITLE: str = "VOID HUNTER v1.3.0 (BLOQUE 70)"`.

### Diagrama de flujo

```
WAVE: cada 3-5s
  └─ spawn_obstacle(rng) → 25% ("mine_asteroid", payload) / 75% ("asteroid", payload)
        │
        ├─ mine_asteroid → enemy_pool.spawn(MINE_ASTEROID, x, y)
        │     └─ e.vx, e.vy from payload (BLOQUE 68 fix)
        │     └─ e.mine_variant = randint(0, 4) (BLOQUE 66 fix)
        │     └─ drifts down
        │         └─ al cruzar y=120: closed → open1 (0.2s) → open2 (0.2s) → open3 (∞)
        │             └─ open3: cada 1.0s set on_fire=True → integration site → _fire_mine_bullets (3 fan bullets)
        │             └─ vulnerable HP=3, red flash 0.2s/hit
        │             └─ HP=0: 50% powerup drop
        │
        └─ asteroid → self._asteroids.append(Asteroid(...))
              └─ drifts down
              └─ hit() = no-op (BLOQUE 64.A)
              └─ cull when y > INTERNAL_H + 32
```

---

## 4. ANTI-PATRONES aprendidos (lee esto si vas a tocar código)

**Estos 5 errores se cometieron en 4 BLOQUEs consecutivos (63-69). El BLOQUE 70 los arregló pero solo este. Si los repites, vas a fallar igual:**

### 4.1 NO confíes en unit tests aislados

El bug del `NameError` (BLOQUE 70) NO fue detectado por NINGUNO de los 38 tests de `test_mine_asteroid.py` porque todos paraban en `spawn_obstacle()` y nunca ejecutaban la línea `Asteroid(...)` en `gameplay_runtime.py:1701`.

**Regla:** cada test del state machine DEBE ejercitar el path completo: `spawn_obstacle()` → `_enemies.spawn()` o `_asteroids.append()` → `update()` → render. No setees `e.y = 190` directamente.

**Cómo hacerlo bien:** los 2 nuevos tests de BLOQUE 70 (`test_gameplay_runtime_asteroid_spawn_does_not_raise` y `test_gameplay_runtime_actual_75_25_ratio`) corren el `GameplayRuntime.update()` real por 60s y verifican el resultado. Ese es el patrón.

### 4.2 NUNCA uses `except Exception` broad en main loops

`main.py:285-292` envuelve `scene.update()` en `except Exception` que loguea a `crash.log` y CONTINÚA. Esto ocultó el `NameError` del BLOQUE 70 como si fuera un "warning benign".

**Regla:** si vas a hacer un `except`, que sea específico. Para fatal errors (NameError, AttributeError, TypeError), deja que el juego crashee. El crash log sirve para debug, NO para silenciar.

**Si necesitas tocar `main.py:285-292`:** considera agregar un counter de exceptions consecutivas (e.g., 10 en 5s = game over) en vez de seguir silenciando.

### 4.3 NO marques "done" sin captura visual del juego real

BLOQUE 65, 66, 67, 68, 69 dijeron "listo" basándose en conteo de tests. Ninguno ejecutó el juego. El user perdió 11+ horas de paciencia por esto.

**Regla:** antes de decir "listo" o "fixed", TIENES que:
1. Inicializar el `GameplayRuntime` real (`from src.ui.gameplay_runtime import GameplayRuntime; g = GameplayRuntime(transition_to=lambda *a, **k: None)`)
2. Correr `g.update(1/60, 160, 400, 0)` por al menos 60s simulados
3. Verificar que el comportamiento esperado ocurre (asteroides visibles, minas abriendo, ratio correcto)
4. Guardar una captura PNG en `tools/playtest_out/` con un label que muestre el estado

**Si no puedes hacer estos 4 pasos, NO digas "listo".**

### 4.4 NO asumas que un test que pasa significa que el código funciona en gameplay

Hay una diferencia entre:
- **Test unitario**: testea UNA función en aislamiento. Útil para lógica pura.
- **Test de integración**: testea la interacción entre módulos. Necesario para spawn, rendering, etc.
- **Test end-to-end (e2e)**: corre el sistema completo. **Imprescindible para features visibles al usuario.**

El bug del BLOQUE 70 necesitó un e2e (correr `GameplayRuntime.update()` 60s) para detectarse. Ningún unit test lo habría detectado.

### 4.5 NO uses thresholds hardcoded sin pensar en la fracción del playfield

El playfield es 480px de alto. "Primer cuarto" = y=120 (480/4). "Tercio" = y=160. "Mitad" = y=240. Siempre calcula el threshold desde la fracción, no hardcodees un número mágico.

**Regla:** si el user dice "primera mitad" o "primer cuarto", escribe `INTERNAL_H / 2` o `INTERNAL_H / 4` en el código con un comment explicando.

---

## 5. Trabajo pendiente en asteroides (decisiones de diseño, no bugs)

### 5.1 `MINE_FIRE_INTERVAL_S = 1.0` — ¿se siente bien en gameplay?

**Estado:** funcional, 1 fan cada 1.0s.
**Pendiente:** el user no confirmó si 1Hz es el rate correcto. Si el juego se siente muy fácil (minas lentas disparando) o muy difícil (minas spamming), ajustar.
- Más fácil: subir a `MINE_FIRE_INTERVAL_S = 1.5` o `2.0`
- Más difícil: bajar a `0.5`

**Cómo probar:** jugar 5 runs de 2 minutos cada una. Si el user sobrevive consistentemente > 3 minutos, subir. Si muere consistentemente en < 1 minuto, bajar.

### 5.2 `open1` y `open2` son composites, no AI-gen puros

**Estado:** las frames intermedias (`Assets/sprites/enemies/mine_asteroid/open1/frame_00.png` y `open2/frame_00.png`) son composites hechos con PIL: el closed round + un crack/gap pintado. NO son AI-gen.

**Razón:** el worker de BLOQUE 65 intentó AI-gen primero, salió con un patrón damero (checkerboard) baked into the asteroid body. Los composites se ven más limpios.

**Pendiente:** si el user quiere AI-gen puro, hay que iterar con prompts mejores. Si está OK con composites, dejarlos así.

**Cómo mejorar:** regenerar con `tools/redesign_asteroids/` (puede que ya no exista) o crear `tools/regen_open1_open2.py` con un prompt específico. Pegar en `mcode-tools` con un prompt tipo:
```
16-bit pixel art, transparent background, no 3/4 angle, locked palette
Subject: a rocky asteroid (round, brown) with a horizontal crack splitting at the equator
```

### 5.3 Regular asteroids NO dropean powerups (decisión BLOQUE 64.A)

**Estado:** los asteroids regulares son indestructibles, no dropean nada. Los powerups vienen SOLO de MINE-ASTEROID kills (50% rate).

**Pendiente:** si el user quiere que los asteroids regulares dropeen powerups al ser destruidos, hay que revertir la decisión de BLOQUE 64.A:
1. Re-añadir `hp` field a `Asteroid` dataclass
2. Revertir `Asteroid.hit()` a algo que reste HP y dropee powerup al destruirse
3. Update tests de BLOQUE 64.A

**Trade-off:** el user dijo en su momento "asteroides indestructibles" porque queria el feel de Star Fox 64 (los asteroides son obstáculos, no targets). Si quiere revertir, el feel del juego cambia.

### 5.4 No hay SFX asociado al MINE abriendo o disparando

**Estado:** el MINE abre silenciosamente, dispara silenciosamente. Solo hay SFX del generic pool (disparo del player, hit del player, etc.).

**Pendiente:** si el user quiere feedback auditivo, agregar 2 SFX:
- `mine_open.wav` (cuando closed → open1)
- `mine_fire.wav` (cuando dispara el fan)

Ver `src/audio/sfx.py` para el catálogo de eventos. Los eventos placeholder están en `audio/sfx.py` como nombres de eventos en el pool. Si no existen como archivos .wav, hay que generarlos con `tools/synth.py` o similar.

### 5.5 La "mina" se ve igual que el "asteroide regular" en closed state (camuflaje)

**Estado:** por diseño. El camo perfecto es el chiste del feature.

**Trade-off que el user notó en sesión 13:09:** cuando arrancó el juego, los primeros 3 spawns eran minas (mala suerte con el seed `0xA57E2012`). El user pensó "todos son minas". Después de jugar más, vio el patrón real (75/25).

**Posible mejora:** cambiar el seed a algo que NO tenga los primeros 3 como minas. O agregar un "warmup" de los primeros 5 spawns = asteroids garantizados.

**Cómo cambiar el seed:** `src/ui/gameplay_runtime.py:240` — `self._asteroid_rng = random.Random(0xA57E2012)`. Probar con `0x12345678` u otro y verificar que los primeros 5 spawns sean balanceados.

### 5.6 El user observó "todos los asteroides son naves" — percepción de camuflaje

**Contexto:** el BLOQUE 70 (just landed) fixea el bug del NameError. Pero el user podría seguir percibiendo que "todos son minas" porque:
- Las minas abren y se vuelven OBVIAS (se transforman en naves con cañón)
- Los asteroids regulares pasan de largo y son INVISIBLES al ojo (se ven como el fondo)

**Sugerencia:** agregar un sutil visual marker al closed state del MINE para que el player pueda identificarlo en segunda mirada (NO rompe el camo casual, solo permite identificación al inspeccionar). Ejemplos:
- Un punto más oscuro en el centro del MINE
- Un brillo de 1px alrededor del sprite (outline verde/cyan apenas visible)
- Una pequeña sombra interna que sugiera "esto tiene algo adentro"

**Esto es decisión de diseño, no bug.** Confirmar con el user antes de implementar.

---

## 6. Trabajo NO-asteroide que el user mencionó

- **GOLIATH animation fix** (pendiente desde el BLOQUE 64.B): el user dijo "olvida lo de goliath" y nunca se retomó. La fix es 1 línea: agregar `self.update_animation(dt)` al inicio de `Boss.update()` en `src/entities/enemies/boss.py`. Pero el user dijo olvidar, así que preguntar antes de tocar.
- **Composites vs AI-gen de open1/open2**: ver sección 5.2.

---

## 7. Acceptance criteria para "done" en cualquier BLOQUE de asteroides futuro

El siguiente agente debe verificar TODOS estos antes de decir "listo":

1. ✅ `pytest tests/test_mine_asteroid.py` pasa con N tests (era 44, debe crecer o mantenerse)
2. ✅ `pytest tests/` sin regresiones nuevas (1,639 + 6 pre-existing failures)
3. ✅ **GameplayRuntime.update() corre 60s sin crash en `logs/crash.log`** (usar el patrón de `tools/verify_spawn_ratio.py` del BLOQUE 70)
4. ✅ **Captura PNG del estado real** en `tools/playtest_out/`, con label que muestre el y=120 (o lo que aplique)
5. ✅ **Comportamiento visible verificado**: el user confirma en gameplay que ve lo que debería ver
6. ✅ .exe rebuildeado con PyInstaller
7. ✅ Commit + push a `origin/master`
8. ✅ CHANGELOG actualizado

Si falta cualquiera de estos 8, NO es "listo".

---

## 8. Comandos útiles

```bash
# Activar venv
& "D:\AI\void-hunter\.venv\Scripts\python.exe" ...

# Correr tests
pytest D:\AI\void-hunter\tests\test_mine_asteroid.py -v
pytest D:\AI\void-hunter\tests\ --tb=no -q

# Verificar spawn ratio (el script del BLOQUE 70)
"D:\AI\void-hunter\.venv\Scripts\python.exe" "D:\AI\void-hunter\tools\verify_spawn_ratio.py"

# Verificar end-to-end (otro script útil)
"D:\AI\void-hunter\.venv\Scripts\python.exe" "D:\AI\void-hunter\tools\verify_mine_end_to_end.py"

# Rebuild
"D:\AI\void-hunter\.venv\Scripts\python.exe" -m PyInstaller "D:\AI\void-hunter\build.spec" --noconfirm

# Crear zip release
Compress-Archive -Path "D:\AI\void-hunter\dist\void-hunter.exe" -DestinationPath "D:\AI\void-hunter\dist\VoidHunter-v1.3.0-win64.zip" -CompressionLevel Optimal

# Publicar release (REQUIERE GITHUB_TOKEN o STELLAR_HORIZON_TOKEN env var)
"D:\AI\void-hunter\.venv\Scripts\python.exe" "D:\AI\void-hunter\tools\create_v1_3_0_release.py"

# Check crash log
Get-Content D:\AI\void-hunter\logs\crash.log -Tail 20
```

---

## 9. Si vas a empezar un nuevo BLOQUE

1. Lee este documento completo.
2. Lee el CHANGELOG actual (`docs/changelog/CHANGELOG_v1.x.md`) para entender qué BLOQUEs ya pasaron.
3. Corre el juego y juega 60s. **Esto es no-negociable.** Vas a entender el feel del juego antes de tocar nada.
4. Identifica el cambio concreto. Si es de balance (1Hz, threshold, etc.), modifica la constante. Si es visual (sprite, color, SFX), modifica el asset. Si es comportamiento (HP, fire pattern), modifica el state machine.
5. Escribe el plan con superpowers:brainstorming + prompt-weapon-definitivo **antes** de tocar código.
6. Implementa con TDD: test rojo → código → test verde.
7. Verifica con `tools/verify_*.py` Y con `GameplayRuntime.update()` real.
8. Captura visual con label de coordenadas.
9. Commit + push.
10. Rebuild + (opcional) release.

**Si haces cambios visuales, muéstrale al user la captura ANTES de rebuildar.** El user repite quejas hasta ver evidencia visual. No hay forma de evitarlo.

---

## 10. Resumen ejecutivo (para el siguiente agente en 30 segundos)

- **Proyecto:** shmup vertical 8-bit pixelart en pygame, v1.3.0 en GitHub.
- **Asteroides:** 25% MINE-ASTEROID (se abre, dispara 1Hz, vulnerable HP=3) / 75% regular (indestructible). BLOQUE 70 fixea un bug crítico (NameError silencioso). 44 tests pass, 1,639 suite pass.
- **El bug más reciente:** era un import faltante en `gameplay_runtime.py:1680`. Fix: agregar `Asteroid,` al import.
- **Pendiente:** tuning de 1Hz, decisión de SFX, posible seed change, posible visual marker para distinguir MINE de regular.
- **Anti-patrón crítico:** NUNCA digas "listo" sin ejecutar `GameplayRuntime.update()` por 60s y ver el resultado.
- **Lenguaje del user:** español colombiano, "tú" (NO voseo). Sé respetuoso de su tiempo y su paciencia. Él prefiere "listo" cuando TODO está verificado, no antes.
