# VOID HUNTER — Game Design Document + Technical Spec

> **Versión**: 1.0 (Production Target)
> **Fecha**: 2026-08-08
> **Estado**: SPEC EJECUTABLE — listo para BLOQUE 0
> **Stack**: Python 3.11+ / Pygame 2.6+ / Sin dependencias externas
> **Semilla**: `nebula-hunter/` (MVP @ 60 FPS) → producción @ 120 FPS

---

## §0 — Metadata

| Campo | Valor | Justificación |
| --- | --- | --- |
| **Nombre** | **VOID HUNTER** | Identidad: "void" = vacío/espacio profundo (paleta de fondos), "hunter" = rol del jugador. 11 chars, legible, sin colisión con marcas registradas en shmup. |
| **Género** | Shmup vertical (STG) con elementos de arena shooter | Cave STG core + Ikaruga scoring + DMC ranking. |
| **Plataforma** | Desktop (Windows / Linux / macOS) | Pygame 2.6 es cross-platform; la única dependencia de OS es `pygame.mixer`. |
| **Resolución interna** | 240×360 px | Sweet spot 8-bit (Shovel Knight 2014, Celeste 2018 usan múltiplos similares). 86,400 píxeles por frame = 8-bit puro sin compromiso. |
| **Resolución ventana** | 960×1440 px (4× scale, integer) | 4× scale = factor limpio; ventana cabe en 1080p con letterbox mínimo. SCALED \| RESIZABLE permite 3×–5× on the fly. |
| **Framerate target** | **120 FPS mínimo en gameplay normal, 90 FPS mínimo en stress** | "Rápido" del brief es literal: el feel arcade de Cave/Touhou se pierde bajo 100 FPS en pantallas 120 Hz. FIXED_DT = 1/120 s = 8.333 ms. |
| **Fixed timestep** | Accumulator pattern, FIXED_DT=1/120 | Glenn Fiedler "Fix Your Timestep" (GDC 2014); ya implementado en seed. |
| **Window flags** | `pygame.SCALED \| pygame.RESIZABLE` + integer scale + nearest-neighbor | Filtro `nearest` = pixel art crujiente; integer scale = cero blur. |
| **Audio** | `pygame.mixer` 16 channels, 44100 Hz, 16-bit PCM raw vía `array.array` | Sin numpy. Procedural ADSR robusto. Null-safe si mixer falla. |

### Números clave (single source of truth)

| Parámetro | Valor | Referencia / cálculo |
| --- | --- | --- |
| `FIXED_DT` | 1/120 s = 8.333 ms | 120 FPS target |
| Frame budget | 8.33 ms | = 1/120 s |
| Update budget | 4.0 ms (48%) | Lógica de juego + IA + colisión |
| Render budget | 2.0 ms (24%) | Compose scene graph |
| Blits budget | 2.0 ms (24%) | Single `target.blits()` batch |
| Slack | 0.33 ms (4%) | GC, OS jitter, MIDI |
| Particle pool | 1500 | 2.5× seed; cubre stress 90+ FPS con boss + 8 enemigos |
| Projectile pool | 400 | 2× seed; max 200 enemy + 100 player + 100 boss |
| Star layers | 5 | +1 vs seed (más profundidad) |
| Temas | 6 | Seed 5 + 1 (gold/amber act 3) |
| Enemy archetypes | 8 | Seed 3 + 5 (kamikaze/drone/sniper/turret/carrier) |
| Bosses | 4 | Seed 1 (3-phase) + 3 nuevos (1 sub-boss por act + final 4-phase) |
| Waves totales | 18 | 6 por act × 3 acts |
| Player lives | 3 + 1 continue | Estándar arcade (DoDonPachi: 2 + continue) |
| Bombs | 3 | Ikaruga: 3 bombs máx |
| Weapon paths | 3 (plasma/ion/shock) | Ikaruga polarity adaptado |
| Weapon levels por path | 3 + special | R-Type charge + Gradius options |
| SFX | 24 procedurales | ADSR configurable por evento |
| BGM | 4 procedurales (A-B) | Estructura corta para evitar loop fatigue |
| Multiplier chain | 1×→2×→4×→8×→16× (max) | DoDonPachi scoring |
| Multiplier decay | 1.5 s sin kill | DoDonPachi arcade manual |
| Hitstop range | 3–12 frames | Vlambeer + Hollow Knight reference |
| Slow-mo range | 0.3×–0.95× | Bayonetta witch time |
| Screen shake max | 8 px (vs 4 seed) | Squirrel Eiserloh trauma² |
| Palette | 64 chars ASCII | 8-bit 54-color estándar + 10 accent |
| Coverage gate | ≥35% (vs 5% seed) | Subir progresivo: 5→12→20→28→35 |
| Mypy strict | 0 errores | `mypy src/` exit 0 |
| Soberanía silo | 0 imports `motor.*` | void-hunter es silo independiente |

---

## §1 — High Concept

**VOID HUNTER** es un shoot'em up vertical de 8-bit que se siente como jugar un arcade Cave de 1995 con el juice de un Metal Slug de 2020. El jugador pilota una nave caza-asteroides en tres actos de un viaje al centro de un void colapsado, enfrentando hordas de drones hostiles, cazas sniper, y cuatro bosses con patrones memorables. Cada kill alimenta un multiplier chain que escala hasta 16×; cada arma elemental sube de nivel con uso hasta desbloquear un special devastador. La promesa: en 25 minutos de run, el jugador debe sentir que sus reflejos importan, que cada decisión de posicionamiento salva vidas, y que la pantalla está VIVA con partículas, shake, hitstop y feedback de audio procedural.

**5 adjetivos identitarios:**
- **Violento** — explosiones multi-stage, screen-shake en cada kill, sin piedad con quien se queda quieto.
- **Rápido** — 120 FPS lock, input lag ≤1 frame, dash con i-frames, balas del player a 720 px/s.
- **Brillante** — paleta saturada, glow halos en todo, scanline overlay sutil, chromatic aberration en pause.
- **Retro** — 8-bit pixel art, ADSR cuadrado/triangular, narrativa con portraits al estilo arcade.
- **Generoso con feedback** — score popup flotante, +500/+1000 en colores, ranking S/S+/SSS al cerrar cada act.

**3 referentes directos y por qué:**

| Juego | Referencia específica | Aplicación a VOID HUNTER |
| --- | --- | --- |
| **Cave / DoDonPachi** (1997–2012) | "Dodge the pretty" — balas visibles, patrones con escape route garantizado. | Cada ataque de boss o wave debe dejar gap de 8–16 px donde el jugador sobrevive. Telegraph mínimo 30 frames en ataques letales. |
| **Metal Slug** (1996) | Juice grade-A: screen-shake, multi-stage explosions, score popups, exclamaciones. | Trauma² con max 8px, particle engine de 18 kinds, score popup flotante con números grandes y color de milestone. |
| **Ikaruga** (2001) | Polaridad elemental + scoring chain + bomb limitada como recurso estratégico. | 3 weapon paths elementales con bonus contra debilidad enemiga, multiplier chain 1×→16×, 3 bombs máximo como decisión táctica. |

---

## §2 — Mecánicas del Jugador

### Tabla de acciones

| Input | Acción | Efecto | Feedback visual | Feedback sonoro | Juice |
| --- | --- | --- | --- | --- | --- |
| `A` / `D` (o stick L/R) | Move lateral | `vx` acelera a 130 px/s en 0.08s (ease-out) | Ship tilt ±15°, engine flame escala con \|vx\| | Engine hum continuo (volume = 0.3 + 0.4·\|vx\|/130) | Tilt + flame length |
| `J` (hold) | Auto-fire | Dispara cada 0.10s; si held > 0.5s, charge level 1; > 1.0s, level 2; > 1.5s, level 3 | Muzzle flash 2 frames, recoil 1.5px en ship | shoot / shoot_charged (pitch sube con level) | Recoil + flash + chromatic |
| `J` (release while charged) | Charge release | Disparo especial del nivel actual con daño 1/2/3 + element-bonus | Trail de 16 partículas ion-wake, glow halo radio 6 | shoot_charged (sample específico por level) | Slow-mo 0.95× 4 frames |
| `K` | Dash | 0.18s de movimiento a 480 px/s en la dirección del input (o up si neutral), i-frames totales | After-image 8 frames con alpha decay 255→0 | dash whoosh (sweep noise 0.15s) | Slow-mo 0.95× 2 frames |
| `K` (último frame antes de hit) | **Perfect dash** | i-frames + 0.5s slow-mo a 0.3× + score bonus +500 | Flash cyan radial 12px | perfect_dash (chime + sweep) | Witch-time estilo Bayonetta |
| `L` | Bomb | Limpia pantalla (400 dmg a todos los enemigos visibles), 0.5s invuln, consume 1 bomb | Flash blanco 2 frames, 32 sparks radiales, 2 shockwave rings | bomb (saw drop 0.4s) | Slow-mo 0.5× 8 frames |
| `Esc` | Pause | Detiene game loop, dim overlay | Scanline overlay + chromatic 4px | — | — |
| `F1` | Toggle FPS overlay | Muestra/oculta HUD de debug | — | ui_click | — |

### FSM del Player (7 estados)

```
            ┌─────────┐ input lateral   ┌──────┐
            │  IDLE   ├────────────────►│ MOVE │
            │         │◄────────────────┤      │
            └────┬────┘ input release   └──┬───┘
                 │ fire+cd_ready            │
                 ▼                          ▼
            ┌─────────┐ timer 0.10s    ┌─────────┐
            │  SHOOT  ├───────────────►│   IDLE  │
            └────┬────┘                 └─────────┘
                 │ hold > 0.5s
                 ▼
            ┌─────────┐ release → special shot anim 0.20s
            │ CHARGE  ├────────────────────────────────► IDLE
            │ (L1/2/3)│  (CHARGE engloba build + fire; 
            └────┬────┘   timer interno 0/0.5/1.0s para L1/L2/L3,
                 │         luego fire anim 0.20s, exit)
                 │ timer 1.5s sin release → SHOOT (auto-fire L1)
   cualquier estado ──dash input──► ┌─────────┐
                                    │  DASH   │ timer 0.18s
                                    └────┬────┘
                                         ▼
                                       (prev)
   cualquier estado ──take_damage──► ┌─────────┐
                                    │   HIT   │ invuln 60 frames + 0.30s
                                    └────┬────┘
                                         │ lives = 0
                                         ▼
                                    ┌─────────┐
                                    │  DEAD   │ 1.20s multi-stage explosion
                                    └────┬────┘
                                         │ respawn
                                         ▼
                                    IDLE (1s invuln)
```

| Estado | Duración típica | Condición de salida | Color sprite base |
| --- | --- | --- | --- |
| **IDLE** | Indefinido | Input lateral/fire/dash/hit | `(220, 240, 255)` |
| **MOVE** | Continuo con input | Sin input + 0.05s settle | Ship tilt ±15° |
| **SHOOT** | 0.10s | Timer o state cancel | Recoil 1.5px |
| **CHARGE** | 0.5s / 1.0s / 1.5s build + 0.20s fire anim | Release (→ IDLE) o timeout 1.5s (→ SHOOT) | Color shift cyan→blue→white + trail denso en fire phase |
| **DASH** | 0.18s | Timer | After-image 8 frames |
| **HIT** | 0.30s + 60f invuln | Timer | Red flash + lean 8° |
| **DEAD** | 1.20s | Animation complete | Multi-stage explosion |

### Stats base + progresión

| Stat | Base (L1) | Nivel 2 (10 kills) | Nivel 3 (25 kills) | Special (50 kills) |
| --- | --- | --- | --- | --- |
| HP (ship integrity) | 3 hits | 4 hits | 5 hits | 6 hits + regen 1/3s |
| Bullet damage | 1 | 2 | 3 | 5 (special) |
| Fire rate (cooldown) | 0.10s | 0.085s | 0.07s | 0.055s |
| Bullet speed | 480 px/s | 540 px/s | 600 px/s | 720 px/s |
| Move speed | 130 px/s | 145 px/s | 160 px/s | 180 px/s |
| Dash distance | 86 px (0.18s × 480) | 96 px | 108 px | 130 px |
| Dash i-frames | 22 frames | 26 frames | 30 frames | 36 frames |
| Bomb count | 3 | 3 | 3 | 4 (special) |
| Charge time (L1/L2/L3) | 0.5s / 1.0s / 1.5s | 0.4s / 0.8s / 1.2s | 0.3s / 0.6s / 0.9s | 0.2s / 0.4s / 0.6s |
| Bomb damage | 400 (screen-clear) | 400 | 400 | 600 + heal 1 HP |

**Input lag budget:** 1 frame (8 ms @ 120 FPS) desde evento de teclado hasta cambio de estado. Validar con `pygame.event.get()` antes de `update(dt)`.

---

## §3 — Weapon System

### 3 paths elementales

#### **PLASMA** (Calor / Kinetic) — `"violento, rápido, splash"`

| Nivel | Sprite | Comportamiento | Daño base | Charge time | Special al L3 |
| --- | --- | --- | --- | --- | --- |
| L1 | Bullet 4×6 naranja-amarillo, 4-frame pulse | Disparo recto, 1 bala/cooldown | 1 | 0.5s | — |
| L2 | Bullet 6×8 naranja-rojo, 4-frame + 2 sparks laterales | 2 balas paralelas (offset ±3px), 1 cada cooldown | 2 | 1.0s | — |
| L3 | Bullet 8×10 rojo-blanco, 4-frame + glow halo radio 4 | 3 balas en 5-spread ligero (±8°) | 3 | 1.5s | — |
| **SPECIAL** | "INFERNO" — 12×12 burst circular, 24-frame animation | **Anillo de 8 balas en 360° que daña a TODOS los enemigos en radio 80px + burn DoT 3 dmg/0.5s × 6 ticks** | 5 + burn | 1.5s | Anillo 360° + burn DoT |

**Element bonus vs enemigos:** Heavy, Cruiser, Turret, Carrier (kinetic-armored) → +50% daño.

#### **ION** (Electricidad / Piercing) — `"azul, preciso, perforante"`

| Nivel | Sprite | Comportamiento | Daño base | Charge time | Special al L3 |
| --- | --- | --- | --- | --- | --- |
| L1 | Bullet 3×8 cyan-azul, 4-frame + zigzag electric-arc | Disparo recto, **pierce 1 enemigo** | 1 | 0.5s | — |
| L2 | Bullet 4×10 azul, 4-frame + twin arc | 2 balas stagger (delay 0.05s), **pierce 2** | 2 | 1.0s | — |
| L3 | Bullet 5×12 azul-blanco, 4-frame + halo electric | 3 balas spread ±6°, **pierce 3** | 3 | 1.5s | — |
| **SPECIAL** | "CHAIN LIGHTNING" — rayo procedural de 6 segmentos | **Rayo que conecta 4 enemigos en radio 120px, saltando 60 px entre targets, 200 dmg por hit** | 5 + chain | 1.5s | Chain 4 targets + slow 0.5× × 2s |

**Element bonus vs enemigos:** Scout, Drone, Sniper (light-armor electric-vulnerable) → +50% daño.

#### **SHOCK** (Tierra / Impact) — `"violeta, lento, screen-shake"`

| Nivel | Sprite | Comportamiento | Daño base | Charge time | Special al L3 |
| --- | --- | --- | --- | --- | --- |
| L1 | Bullet 6×6 violeta-magenta, 4-frame | Disparo recto **lento (300 px/s)** con knockback | 1 + knockback 20px | 0.5s | — |
| L2 | Bullet 8×8 violeta, 4-frame + dust trail | 2 balas con knockback 30px, **splash 16px radius** | 2 + splash | 1.0s | — |
| L3 | Bullet 10×10 magenta-blanco, 4-frame + shockwave | 1 bala pesada, knockback 50px, **splash 32px** | 3 + splash | 1.5s | — |
| **SPECIAL** | "QUAKE" — onda expansiva 64×64 | **Onda concéntrica que atraviesa toda la pantalla (vertical), 150 dmg en ring 24px + screen-shake trauma 0.4** | 5 + ring | 1.5s | Full-screen ring + shake |

**Element bonus vs enemigos:** Kamikaze, Sniper, Heavy (kinetic-resistant) → +50% daño.

### Tabla comparativa

| Aspecto | PLASMA | ION | SHOCK |
| --- | --- | --- | --- |
| Color primario | N→R (255, 120, 40) | Cyan→Azul (80, 200, 255) | Violeta (180, 80, 220) |
| Dificultad de uso | Fácil (1 Bala, recta) | Media (pierce requiere positioning) | Alta (knockback rompe combos) |
| Velocidad bala | 480/540/600 px/s | 480/540/600 px/s | 300/360/420 px/s (lento) |
| Daño single-target | 1/2/3 | 1/2/3 | 1/2/3 |
| Daño multi-target | Bajo (spread L3) | Alto (pierce + chain) | Alto (splash) |
| Anti-grupo | L3 spread 5-way | Special chain 4 targets | Special full-screen ring |
| Anti-single | L3 3-bullet spread | L2/L3 pierce | L2/L3 knockback combo |
| Ideal vs | Heavy, Cruiser, Carrier | Scout, Drone, Sniper | Kamikaze, Sniper, Heavy |
| Worst vs | Scout (overkill) | Heavy (pierce wasted) | Drone (splash pequeño) |
| **Special name** | INFERNO | CHAIN LIGHTNING | QUAKE |
| **Special radius** | 80 px circle | 120 px chain (4 targets) | Full-screen vertical ring |
| **Special damage** | 5 + 18 burn DoT | 5 + 200 chain | 5 + 150 ring + 0.4 trauma |

**Level-up trigger:** 10 kills para L2, 25 kills para L3, 50 kills para Special. Cada kill suma XP, kill de element-bonus da +2 XP. Al subir de nivel: flash blanco 2 frames + chime + HUD pop "PLASMA LV.2!".

**Costo de Special:** consume 1 bomb. Sin bombs, special se desactiva (HUD muestra icono gris).

---

## §4 — Enemies (8 arquetipos)

### 1. SCOUT

| Atributo | Valor |
| --- | --- |
| HP | 1 |
| Speed | 110 px/s vertical + sine wobble (amplitud 12 px, freq 1.5 Hz) |
| Sprite | 12×8 nave delta, 2-frame animation, color cyan |
| Attack pattern | Disparo aimed cada 1.5s, velocidad 240 px/s, 1 bala |
| Telegraph | 8 frames de parpadeo amarillo antes de disparar |
| Score | 50 base |
| Drop | 8% power-up, 2% bomb refill |
| **Feel al morirlo** | "satisfacción rápida" — flash + 8 sparks + screen-shake 0.08 trauma, 4 frames de hitstop |

**Aparición:** Act 1, waves 1–18 (presente en todo el juego, density base).

### 2. CRUISER

| Atributo | Valor |
| --- | --- |
| HP | 4 |
| Speed | 60 px/s vertical (lento) |
| Sprite | 14×10 nave con 2 cannons, 2-frame idle |
| Attack pattern | Twin cannon: 2 balas paralelas aimed cada 1.2s, velocidad 220 px/s |
| Telegraph | 14 frames de glow rojo en cannons |
| Score | 150 base |
| Drop | 12% power-up, 4% bomb refill |
| **Feel** | "mini-tank satisfactorio" — death explosion medium (16 sparks + shrapnel + smoke + 1 shockwave) |

**Aparición:** Act 1 wave 2+, Act 2 en densidad alta, Act 3 sparser.

### 3. HEAVY

| Atributo | Valor |
| --- | --- |
| HP | 12 |
| Speed | 30 px/s vertical (casi estático, drift lateral lento) |
| Sprite | 18×12 acorazado gris-plata, 2-frame + outline 1px negro |
| Attack pattern | Heavy shot cada 2.5s: bala 8×8 con glow halo radio 3, velocidad 180 px/s, daño 2 |
| Telegraph | 24 frames de glow rojo intenso en el cañón |
| Score | 400 base |
| Drop | 18% power-up, 6% bomb refill, 1% 1UP |
| **Feel** | "tanque que se siente tanque" — death explosion large (32 sparks + 2 shockwaves + debris físico + screen-shake 0.25 trauma + 6 frames hitstop) |

**Aparición:** Act 1 wave 4+, Act 2/3 múltiples por wave.

### 4. KAMIKAZE

| Atributo | Valor |
| --- | --- |
| HP | 1 (pero explota en contacto: 80 dmg en radio 24px) |
| Speed | 160 px/s (rápido) con homing suave (turn rate 90°/s) hacia player |
| Sprite | 10×10 esfera roja-púrpura, 2-frame pulse |
| Attack pattern | Sin disparo; **glow pulsante (radio 4→12) durante 30 frames antes de detonar** |
| Telegraph | 30 frames de glow visible (color rojo→blanco→flash detonación) |
| Score | 200 base (bonus si destruido en el aire antes de detonar: +300) |
| Drop | 5% bomb refill |
| **Feel** | "tensión que se libera" — pulsación visible genera dread, detonación con shockwave ring + 16 sparks + screen-shake 0.15 |

**Aparición:** Act 1 wave 6+, Act 2 density++, Act 3 swarm tactics.

### 5. DRONE

| Atributo | Valor |
| --- | --- |
| HP | 2 (parent), 1 cada mini-drone |
| Speed | 80 px/s vertical + drift lateral aleatorio |
| Sprite | 8×8 cuadrado cyan-azul, 2-frame + antena |
| Attack pattern | **Al ser destruido o a los 4s de spawn, libera 2–3 mini-drones (6×6) que se separan radialmente a 100 px/s** |
| Telegraph | Mini-drones visibles al spawn (no surprise) |
| Score | 80 base + 50 cada mini-drone |
| Drop | 10% power-up |
| **Feel** | "rompecabezas" — decidir si destruir parent rápido o esperar a que libere drones para chain |

**Aparición:** Act 2 wave 1+, Act 3 density media.

### 6. SNIPER

| Atributo | Valor |
| --- | --- |
| HP | 2 |
| Speed | 0 (estático, anclado en posición fija) |
| Sprite | 16×8 torreta con mira laser, 1-frame |
| Attack pattern | **Laser beam con telegraph 60 frames (1s)**: línea vertical warning 1px → 8px beam activo durante 20 frames, daño 3 al cruzar |
| Telegraph | 60 frames de línea warning parpadeante (0.5 Hz rojo→amarillo) |
| Score | 300 base |
| Drop | 15% power-up, 5% bomb refill |
| **Feel** | "el que obliga a moverse" — beam visual es uno de los elementos más peligrosos del juego, priority target |

**Aparición:** Act 2 wave 3+, Act 3 high density.

### 7. TURRET

| Atributo | Valor |
| --- | --- |
| HP | 6 |
| Speed | 0 (anclada) |
| Sprite | 12×12 base octogonal con cañón rotatorio, 2-frame |
| Attack pattern | **3-spread rotatorio**: dispara 3 balas en 60° spread cada 1.0s, rota 18° por disparo, velocidad 200 px/s |
| Telegraph | 6 frames de glow rojo en cañón |
| Score | 250 base |
| Drop | 12% power-up, 4% bomb refill |
| **Feel** | "minigun visual" — patrón predecible pero constante, requiere positioning |

**Aparición:** Act 2 wave 4+, Act 3 protected by Carrier.

### 8. CARRIER

| Atributo | Valor |
| --- | --- |
| HP | 20 |
| Speed | 25 px/s vertical (deriva lenta) |
| Sprite | 20×14 nave nodriza con "hangar" visible, 2-frame + luz parpadeante |
| Attack pattern | **Lanza scouts y drones desde el hangar cada 3s** (1 spawn por ciclo, alterna scout/drone) |
| Telegraph | 12 frames de hangar abierto (sprite cambia a "open" frame) |
| Score | 800 base + bonus por cada child (50 scout / 80 drone) |
| Drop | 25% power-up (mayor calidad), 8% bomb refill, 3% 1UP |
| **Feel** | "objetivo prioritario" — destruir el carrier detiene el spawn de children, explosiones multi-stage |

**Aparición:** Act 3 wave 1+, density alta en waves de boss-prelude.

### Orden de aparición por Act

| Act | Wave | Mix principal |
| --- | --- | --- |
| **Act 1 (Blue Void)** | 1 | 100% Scout (tutorial implícito) |
| | 2 | 70% Scout + 30% Cruiser |
| | 3 | 50% Scout + 40% Cruiser + 10% Heavy (1 unit) |
| | 4 | 40% Scout + 40% Cruiser + 20% Heavy |
| | 5 | 30% Scout + 40% Cruiser + 25% Heavy + 5% Kamikaze (1 unit) |
| | 6 | 30% Scout + 30% Cruiser + 20% Heavy + 20% Kamikaze (boss prelude) |
| **Act 2 (Pink Void / Mars / Teal)** | 1 | 30% Scout + 30% Cruiser + 20% Heavy + 10% Kamikaze + 10% Drone |
| | 2 | 30% Scout + 20% Cruiser + 20% Heavy + 15% Kamikaze + 15% Drone |
| | 3 | 20% Scout + 20% Cruiser + 15% Heavy + 15% Kamikaze + 20% Drone + 10% Sniper |
| | 4 | 15% Scout + 15% Cruiser + 15% Heavy + 20% Kamikaze + 20% Drone + 10% Sniper + 5% Turret |
| | 5 | 10% Scout + 10% Cruiser + 15% Heavy + 25% Kamikaze + 20% Drone + 15% Sniper + 5% Turret |
| | 6 | 10% Scout + 10% Cruiser + 10% Heavy + 25% Kamikaze + 15% Drone + 20% Sniper + 10% Turret |
| **Act 3 (Purple Dusk / Gold-Amber)** | 1 | 15% Scout + 10% Cruiser + 15% Heavy + 15% Kamikaze + 15% Drone + 15% Sniper + 10% Turret + 5% Carrier |
| | 2 | 10% Scout + 10% Cruiser + 10% Heavy + 20% Kamikaze + 15% Drone + 15% Sniper + 10% Turret + 10% Carrier |
| | 3 | 10% Scout + 5% Cruiser + 10% Heavy + 20% Kamikaze + 15% Drone + 15% Sniper + 15% Turret + 10% Carrier |
| | 4 | 5% Scout + 5% Cruiser + 10% Heavy + 20% Kamikaze + 15% Drone + 15% Sniper + 15% Turret + 15% Carrier |
| | 5 | 5% Scout + 5% Cruiser + 10% Heavy + 15% Kamikaze + 15% Drone + 15% Sniper + 20% Turret + 15% Carrier |
| | 6 | 5% Scout + 5% Cruiser + 10% Heavy + 15% Kamikaze + 10% Drone + 15% Sniper + 20% Turret + 20% Carrier (prelude Nemesis) |

---

## §5 — Bosses (4 totales)

### Convenciones globales (aplican a los 4)

- **Telegraph letal:** ≥30 frames (0.25s @ 120 FPS) para ataques de daño directo.
- **Telegraph special:** ≥60 frames para beam / ring / spiral.
- **Hitbox real:** 70% del sprite visible (forgiving). Los 4 bosses tienen hitbox central con `hurtbox_factor = 0.7` y `hitbox_factor = 1.0` para player bullets.
- **Phase transition VFX:** flash blanco 2 frames + screen-shake trauma 0.5 + 32 sparks radiales equi-espaciadas + hitstop 6 frames + nueva sección BGM. Idéntico a Hollow Knight.
- **Pool extra durante boss fight:** Projectile pool sube temporalmente a 600 (de 400) si se detecta boss activo. Implementar como `ProjectilePool.expand(200)` on enter BOSS_FIGHT state.

---

### Sub-Boss Act 1: **GOLIATH** (32×18)

**Identidad:** Crucero capital acorazado, primer "jefe" que enseña telegraphs largos.

| Stat | Valor |
| --- | --- |
| HP total | 800 |
| HP Phase 1 (100–66%) | 528 |
| HP Phase 2 (66–0%) | 272 |
| Speed | 30 px/s lateral, anclado vertical en y=80 |
| Move pattern | Oscila left-right con sine amplitude 80px, period 4s |
| Tema | Blue Void |
| BGM | Boss section A (intense) |

**Attacks Phase 1:**
- **Aimed shot (40% prob):** 1 bala aimed hacia player, velocidad 220 px/s, cada 1.5s.
- **3-spread (60% prob):** 3 balas en 30° spread desde posición frontal, velocidad 200 px/s, cada 1.8s.

**Attacks Phase 2 (enraged):**
- **Aimed shot rápido:** cada 0.8s.
- **3-spread doble:** dos 3-spreads simultáneos con offset 12px.
- **Ring sweep nuevo:** anillo de 12 balas cada 6s (telegraph 30 frames de glow central).

**Transition VFX (P1→P2):** flash blanco + 32 sparks radiales + screen-shake 0.5 + 6 hitstop.

**Moment (firma memorable):** el **Ring Sweep** — el primer ataque circular que aprende el jugador, donde debe encontrar el gap central de 8–16 px entre balas.

---

### Sub-Boss Act 2: **HYDRA** (36×20)

**Identidad:** Criatura de 3 cabezas que dispara patrones entrelazados.

| Stat | Valor |
| --- | --- |
| HP total | 1400 |
| HP Phase 1 (100–66%) | 924 |
| HP Phase 2 (66–33%) | 462 |
| HP Phase 3 enraged (33–0%) | 14 (residual, "rage" mode) |
| Speed | 0 (anclada), drift vertical lento 20 px/s |
| Move pattern | Desciende lentamente hasta y=70, luego se mantiene |
| Tema | Pink Void (con transiciones a Mars/Teal en mid-fight) |
| BGM | Boss section A → A' (más intensa) en phase 3 |

**Attacks Phase 1:**
- **5-spread alterno:** cada cabeza dispara 5-spread rotando 18° por ciclo, 1.5s cooldown.
- **Ring sweep pequeño:** 8 balas en radio 40, telegraph 30 frames, cada 4s.

**Attacks Phase 2:**
- **5-spread doble:** dos heads disparan simultáneo, offset angular 30°.
- **Aimed triple:** 3 headed aimed shots.
- **Ring sweep mediano:** 16 balas en radio 60, telegraph 45 frames, cada 5s.

**Attacks Phase 3 (enraged):**
- **Todos los anteriores + 5-spread triple simultáneo** (las 3 cabezas disparan a la vez, 15 balas totales en 180° spread).
- **Aura DoT:** daño pasivo 5/0.5s a player dentro de 60 px del boss.

**Transition VFX (cada phase):** idéntico al global, + cambio de paleta accent (Pink Void → Mars → Teal).

**Moment:** el **Phase 3 con aura DoT** — el jugador debe acercarse para atacar pero sufre daño pasivo, creando decisión risk/reward.

---

### Sub-Boss Act 3a: **PHANTOM** (40×22)

**Identidad:** Nave sigilosa con ataques homing y beam devastador.

| Stat | Valor |
| --- | --- |
| HP total | 2000 |
| HP Phase 1 (100–66%) | 1320 |
| HP Phase 2 (66–0%) | 680 |
| Speed | 70 px/s con pattern de "blink" (teleport cada 3s con 12 frames de invuln + 6 sparks en origen/destino) |
| Move pattern | Zigzag + blink |
| Tema | Purple Dusk |
| BGM | Boss section A (más lenta, tensión) → A' en phase 2 |

**Attacks Phase 1:**
- **Homing volley:** 4 balas con homing suave (turn 60°/s), velocidad 180 px/s, cada 2s.
- **Laser beam:** telegraph 60 frames de línea warning, beam activo 20 frames con grosor 8px, daño 3 al cruzar, cada 5s.

**Attacks Phase 2:**
- **Homing + spiral mix:** 4 homing + 1 espiral de 12 balas simultáneo.
- **Laser doble:** 2 beams paralelos con offset 20px.
- **Aimed triple rápido:** 3 aimed shots con 0.3s delay entre cada uno.

**Transition VFX:** global + aura cyan-violeta de "phantom mode" 30 frames.

**Moment:** el **blink con invuln** — el boss desaparece y aparece en posición aleatoria, el jugador debe rastrear el destello de teleport.

---

### Final Boss: **NEMESIS** (48×28)

**Identidad:** La entidad del void, 4 fases, desesperación final.

| Stat | Valor |
| --- | --- |
| HP total | 5000 |
| HP Phase 1 (100–75%) | 3750 |
| HP Phase 2 (75–50%) | 2500 |
| HP Phase 3 (50–25%) | 1250 |
| HP Phase 4 (25–0%) DESESPERACIÓN | 1250 (último tramo) |
| Speed | 0 (anclado en y=60), drift en phase 4 |
| Move pattern | Ligeramente lateral en P1–P3, **arena shrinks en P4** |
| Tema | Gold/Amber |
| BGM | Boss section A → B (intense) → B' (desperation, +20% tempo) en phase 4 |

**Attacks pool global (8 patrones canónicos):**
1. Aimed shot
2. 3-spread
3. 5-spread
4. Ring sweep
5. Spiral
6. Laser beam
7. Charge-and-release (3s de carga → release 24-bala star)
8. Wall-of-bullets (línea horizontal)

**Attacks Phase 1:** pool 1, 2, 3 — cooldowns largos (2.5s), pool size 8.
**Attacks Phase 2:** pool 1, 2, 3, 4, 5 — cooldowns medios (1.8s), pool size 12.
**Attacks Phase 3:** pool 1–7 — cooldowns cortos (1.2s), pool size 18.
**Attacks Phase 4 (DESESPERACIÓN):**
- Pool 1–8 todos disponibles, cooldowns 0.8s.
- **Arena shrinks** (play area se reduce 20% desde los lados en 3s).
- **Screen full of projectiles** (pattern denso continuo).
- **Música sube tempo +20%**, layer adicional de percusión.
- **Hitbox del boss se vuelve 50%** (más difícil de hitear, fomenta risk).
- **Trauma permanente 0.15** (shake constante sutil).

**Transition VFX (cada phase):** global + **screen flash azul** (distinto del blanco, marca "phase de void") + **BGM section change** + **HUD warning "NEMESIS PHASE X"** durante 90 frames.

**Moment:** la **Phase 4 arena shrink + music tempo up** — el clímax del juego, donde la dificultad ya no es solo patrón sino espacio reducido.

---

### Tabla resumen de dificultad

| Boss | HP | Speed | Attack freq P1 | Special pool | Hitbox factor | "Moment" |
| --- | --- | --- | --- | --- | --- | --- |
| GOLIATH | 800 | 30 px/s | 1.5s | Ring sweep | 0.7 | Ring Sweep (1er ring) |
| HYDRA | 1400 | 20 px/s | 1.5s | 5-spread triple + DoT aura | 0.7 | Aura DoT en P3 |
| PHANTOM | 2000 | 70 px/s (con blink) | 2.0s | Laser + homing mix | 0.7 | Blink teleport |
| NEMESIS | 5000 | 0 (arena shrink P4) | 2.5s → 0.8s | Wall-of-bullets + 8-pattern pool | 0.7 → 0.5 (P4) | Arena shrink + tempo up |

---

## §6 — Waves (18 totales)

### Estructura por act

| Act | Wave | Theme | Mix de arquetipos | Sub-boss trigger | Special condition |
| --- | --- | --- | --- | --- | --- |
| 1 (Blue Void) | 1 | Blue Void | 100% Scout (6 units) | — | Tutorial: solo shoot + move, sin dash. Hint "PRESS K TO DASH" aparece a los 5s |
| 1 | 2 | Blue Void | 70% Scout (8) + 30% Cruiser (3) | — | Primera intro de Cruiser |
| 1 | 3 | Blue Void | 50% Scout (7) + 40% Cruiser (5) + 10% Heavy (1) | — | Primer Heavy como "checkpoint de daño" |
| 1 | 4 | Blue Void | 40% Scout (8) + 40% Cruiser (7) + 20% Heavy (3) | — | Density up |
| 1 | 5 | Blue Void | 30% Scout (6) + 40% Cruiser (8) + 25% Heavy (4) + 5% Kamikaze (1) | — | Primer Kamikaze (telegraph visible 30 frames) |
| 1 | 6 | Blue Void → GOLIATH intro | Mix boss-prelude | **GOLIATH** at 40 kills | Boss intro 4s con portrait |
| 2 (Pink Void) | 1 | Pink Void | Mix Act 1 + 10% Drone | — | Transición de tema: fade 30 frames |
| 2 | 2 | Pink Void → Mars | Mix Act 1 + 15% Drone + Mars theme overlay | — | Mid-wave theme change |
| 2 | 3 | Mars | Mix completo Act 1 + 20% Drone + 10% Sniper | — | Primer Sniper (beam telegraph 60 frames) |
| 2 | 4 | Mars | Mix + 5% Turret | — | Primer Turret (anclada) |
| 2 | 5 | Teal | Mix completo Act 2 base | — | Density up |
| 2 | 6 | Teal → HYDRA intro | Mix boss-prelude | **HYDRA** at 40 kills | Boss intro 5s con portrait + 3-head visual |
| 3 (Purple Dusk) | 1 | Purple Dusk | Mix Act 2 + 5% Carrier | — | Primer Carrier (spawner) |
| 3 | 2 | Purple Dusk | Mix + 10% Carrier | — | Density ++ |
| 3 | 3 | Purple Dusk → Gold/Amber | Mix + 10% Carrier | — | Mid-wave theme transition a Gold/Amber (warning) |
| 3 | 4 | Gold/Amber | Mix completo + 15% Carrier | — | Density máxima pre-boss |
| 3 | 5 | Gold/Amber | Mix + 15% Carrier + Sniper density max | — | Endurance check |
| 3 | 6 | Gold/Amber → PHANTOM → NEMESIS | Boss chain: PHANTOM, después NEMESIS | **PHANTOM** at 40 kills, **NEMESIS** after PHANTOM dies | Dramatic chain: PHANTOM defeated → 6s "VOID OPENING" cinematic → NEMESIS intro 6s |

### Curva de dificultad (HP total + spawns por wave)

```
HP+spawns │
   1800 ─ │                                                              ◆Nemesis
   1500 ─ │                                                       ◆Phantom
   1200 ─ │                                                ▲Hydra
    900 ─ │                                          ◆Wave12
    700 ─ │                              ▲Wave8
    500 ─ │                       ◆Wave4
    300 ─ │              ▲Wave2
    150 ─ │      ◆Wave1
       0 ──┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴───
           1    2    3    4    5    6    7    8    9   10   11   12   13   14   15   16   17  18
           ├──────── Act 1 ────────┤├──────── Act 2 ────────┤├────────── Act 3 ────────────┤
           

Leyenda: ◆ = sub-boss, ▲ = wave densa
```

### Boss intro spec

- **Duración:** 4–6 segundos.
- **Secuencia:**
  1. (0–30 frames) Freeze gameplay, dim overlay 50%.
  2. (30–90 frames) Boss sprite scale 0.5→1.0 con ease-out cubic, 16 sparks radiales.
  3. (90–150 frames) Portrait frame UI entra desde la derecha (4 frames de slide-in).
  4. (150–240 frames) Texto "WARNING: GOLIATH" (o nombre del boss) en fuente pixel 16px blanco con outline negro 1px.
  5. (240–300 frames) Boss warning SFX (`boss_warning`), screen-shake 0.3, HUD warning pulse 4 frames.
  6. (300+ frames) Resume → BOSS_FIGHT state, BGM switch a boss section.

### Wave clear spec

- **Trigger:** `kills >= WAVE_KILL_TARGET` o `time >= WAVE_TIME_LIMIT` (30s default, escala con wave).
- **Feedback:**
  1. "WAVE CLEARED" texto 32px dorado, fade in 8 frames, hold 60 frames, fade out 30 frames.
  2. "+5000 pts" popup flotante (sprite 24×12 verde-amarillo) con drift up 30 frames.
  3. BGM sting `wave_cleared` (chime + sweep 0.5s).
  4. 2s hold antes de transición a siguiente wave (o boss intro si aplica).

---

## §7 — Scoring + Progression

### Fórmula

```
score_per_kill = base_score
                  × multiplier        (1×–16×)
                  × element_bonus     (×1.5 si element-match)
                  × streak_bonus      (×1.0 a ×2.0 según racha)
                  × difficulty_mult   (×1.0 Normal, ×1.5 Hard, ×2.0 Lunatic)
```

### Tabla de multiplicadores (chain)

| Kill # | Multiplier | Frame para subir | Decay timer | Visual feedback |
| --- | --- | --- | --- | --- |
| 0 (reset) | 1× | — | 0.0s | HUD chain icon gris |
| 1–4 | 2× | 0.0s (inmediato) | 1.5s | HUD icon cyan, "+1" tick |
| 5–9 | 4× | 0.0s | 1.5s | HUD icon azul, "+2" tick |
| 10–19 | 8× | 0.0s | 1.5s | HUD icon violeta, "+3" tick |
| 20+ | 16× (max) | 0.0s | 1.5s | HUD icon dorado, "+4" tick, pulse 2 frames |
| 50+ | 16× (cap) | — | — | HUD icon dorado con sparkle (16 particles alrededor) |

**Reglas del chain:**
- Cada kill: +1 al multiplier step.
- Element-bonus kill: +2 al multiplier step.
- Boss kill: +5 al multiplier step, set timer a 3.0s (no decay).
- Decay: 1.5s sin kill → multiplier -= 1 step (con frame de "chain broken" visual).
- Special clear (bomb kill): +0 (no suma pero tampoco resetea el timer).

### Tabla de drops

| Drop | Probabilidad base | Efecto | Sprite | Color |
| --- | --- | --- | --- | --- |
| **Power-up P** (rapid fire) | 8% | Fire rate ×2 durante 12s | 12×12 "P" cyan | `(80, 200, 255)` |
| **Power-up S** (shield) | 8% | 1 hit absorbido, 12s o hasta consumir | 12×12 "S" verde | `(80, 255, 120)` |
| **Power-up B** (bomb refill) | 6% | +1 bomb (max 4 con special) | 12×12 "B" rojo | `(255, 80, 80)` |
| **Score 500** | 5% | +500 pts instant | 10×10 "·" amarillo | `(255, 220, 80)` |
| **Score 1000** | 3% | +1000 pts instant | 10×10 "··" dorado | `(255, 180, 40)` |
| **1UP** | 1% (max 1 por wave) | +1 life | 12×12 "♥" magenta | `(255, 80, 200)` |
| **Weapon XP token** | 4% | +5 XP al weapon path actual | 10×10 "✦" blanco | `(240, 240, 255)` |

**Drop table por arquetipo (override):**

| Arquetipo | Power-up % | Bomb % | Score % | 1UP % | XP % |
| --- | --- | --- | --- | --- | --- |
| Scout | 8 | 2 | 5 | 0 | 4 |
| Cruiser | 12 | 4 | 5 | 0 | 4 |
| Heavy | 18 | 6 | 5 | 1 | 4 |
| Kamikaze | 5 | 5 | 3 | 0 | 0 |
| Drone | 10 | 0 | 5 | 0 | 4 |
| Sniper | 15 | 5 | 3 | 0 | 4 |
| Turret | 12 | 4 | 3 | 0 | 4 |
| Carrier | 25 | 8 | 5 | 3 | 4 |
| **Boss** | 100 (3 drops garantizados) | 100 | 0 | 50 | 100 (50 XP) |

### Streak bonus

```
racha = kills consecutivos en ventana 3.0s (con multiplier activo)
streak_bonus = 1.0 + min(racha / 50, 1.0)    # cap a 2.0× en racha de 50
```

- 10 kills en 3s: streak_bonus = 1.2×, popup "+500 BONUS".
- 25 kills en 3s: streak_bonus = 1.5×, popup "+2500 BONUS".
- 50+ kills en 3s: streak_bonus = 2.0× (cap), popup "+5000 BONUS" + SFX `multiplier_max`.

### High-score schema (JSON)

```json
{
  "schema_version": 1,
  "ship": "void_hunter_v1",
  "path": "plasma | ion | shock",
  "score": 482350,
  "time_seconds": 1452.3,
  "lives_remaining": 1,
  "bombs_used": 4,
  "deaths": 2,
  "kills": 487,
  "max_multiplier": 16,
  "act_reached": 3,
  "bosses_defeated": ["GOLIATH", "HYDRA", "PHANTOM"],
  "rank": "S+",
  "difficulty": "Normal",
  "timestamp_iso": "2026-08-08T03:14:22.123Z",
  "player_name": "Lerius"
}
```

**Persistencia:** `~/.void_hunter/highscores.json` (10 entradas max, FIFO eviction). Cargado en TITLE screen, displayed en CREDITS.

### Rank calculation (Devil May Cry style)

```
rank_score = (lives_remaining × 1000)
             + (max_multiplier × 500)
             + (kills / 100 × 250)
             + (time_bonus si < 1500s)

Rank thresholds (Normal difficulty):
  D: <  5000
  C:  5000 –  9999
  B: 10000 – 19999
  A: 20000 – 29999
  S: 30000 – 39999
  S+: 40000 – 49999
  SSS: 50000+   (perfect run)

Unlocks:
  S+ → alternate ship color (cyan accent)
  SSS → "Golden Hunter" ship (gold accent, +5% score global)
```

---

## §8 — Visual Direction

### Paleta ASCII completa (64 chars, agrupados por categoría)

> Convención: cada char representa un color de la paleta global. Los sprites se referencian por char, no por RGB, para mantener el aesthetic 8-bit.

#### Negros / Grises / Blancos (12)

| Char | RGB | Uso |
| --- | --- | --- |
| ` ` | `(0, 0, 0)` | Transparente / fondo void |
| `░` | `(40, 40, 60)` | Sombras suaves, nebula shadow |
| `▒` | `(80, 80, 100)` | Mid-gray, ship outline sombra |
| `▓` | `(120, 120, 140)` | Light gray, debris, smoke |
| `.` | `(160, 160, 180)` | Stars lejanas, dithered |
| `:` | `(200, 200, 220)` | Stars cercanas, scanlines |
| `-` | `(220, 220, 240)` | Highlights metálicos |
| `=` | `(240, 240, 255)` | Ship base light |
| `+` | `(255, 255, 255)` | Blanco puro, beams, flash |
| `*` | `(255, 240, 200)` | Warm white, charge L3 |
| `~` | `(180, 200, 255)` | Cool white, ion glow |
| `^` | `(100, 100, 120)` | Outline dark |

#### Rojos / Naranjas (10) — Plasma, fuego, danger

| Char | RGB | Uso |
| --- | --- | --- |
| `r` | `(255, 60, 40)` | Danger red, hit flash |
| `R` | `(200, 40, 20)` | Deep red, kamikaze glow |
| `1` | `(255, 100, 40)` | Plasma L1 |
| `2` | `(255, 140, 60)` | Plasma L2 |
| `3` | `(255, 180, 80)` | Plasma L3, fire |
| `4` | `(255, 220, 100)` | Bright fire, muzzle flash |
| `5` | `(255, 240, 140)` | Yellow fire, sun |
| `o` | `(180, 80, 40)` | Mars theme accent |
| `O` | `(220, 100, 40)` | Mars highlight |
| `p` | `(255, 80, 40)` | Plasma special, kamikaze core |

#### Azules / Cyans (10) — Ion, void, tech

| Char | RGB | Uso |
| --- | --- | --- |
| `b` | `(40, 80, 180)` | Blue void base |
| `B` | `(80, 120, 220)` | Blue void mid |
| `c` | `(80, 200, 255)` | Cyan ion L1 |
| `C` | `(120, 220, 255)` | Cyan bright, ion L2 |
| `i` | `(40, 160, 220)` | Ion trail |
| `I` | `(100, 200, 240)` | Ion highlight |
| `t` | `(80, 220, 200)` | Teal nebula |
| `T` | `(140, 240, 220)` | Teal highlight |
| `n` | `(40, 60, 120)` | Deep void |
| `N` | `(80, 100, 180)` | Mid void |

#### Verdes (6) — UI, shields, health

| Char | RGB | Uso |
| --- | --- | --- |
| `g` | `(80, 200, 80)` | Health, shield |
| `G` | `(120, 240, 120)` | Health highlight |
| `e` | `(40, 160, 80)` | Dark green, UI |
| `E` | `(80, 200, 120)` | Mid green |
| `l` | `(180, 255, 120)` | Lime, power-up P |
| `L` | `(220, 255, 180)` | Lime highlight |

#### Violetas / Magentas (8) — Shock, dusk, special

| Char | RGB | Uso |
| --- | --- | --- |
| `v` | `(180, 80, 220)` | Shock base |
| `V` | `(220, 120, 255)` | Shock highlight |
| `m` | `(220, 80, 180)` | Magenta, dusk |
| `M` | `(255, 120, 200)` | Magenta bright |
| `d` | `(120, 80, 180)` | Purple dusk base |
| `D` | `(160, 100, 220)` | Purple dusk mid |
| `k` | `(80, 40, 120)` | Deep dusk |
| `K` | `(140, 80, 180)` | Mid dusk |

#### Dorados / Amber (6) — Act 3, score, rank

| Char | RGB | Uso |
| --- | --- | --- |
| `y` | `(255, 200, 80)` | Gold base, score popup |
| `Y` | `(255, 220, 120)` | Gold highlight |
| `a` | `(220, 160, 60)` | Amber |
| `A` | `(255, 200, 100)` | Amber bright |
| `q` | `(180, 130, 40)` | Dark gold |
| `Q` | `(140, 100, 30)` | Deep amber |

#### Pink (2) — Pink void theme

| Char | RGB | Uso |
| --- | --- | --- |
| `h` | `(255, 100, 180)` | Pink void base |
| `H` | `(255, 160, 220)` | Pink void highlight |

### 6 Temas con swatches

| Tema | Bg (char) | Nebula[3] (chars) | Stars[3] (chars) | Accent (char) | Particle tint override |
| --- | --- | --- | --- | --- | --- |
| **Blue Void** (default, Act 1) | ` ` | `n`, `N`, `b` | `.`, `:`, `~` | `c` | Spark → `c`/`C` |
| **Pink Void** (Act 2) | ` ` | `k`, `d`, `h` | `.`, `:`, `~` | `H` | Spark → `H`/`m` |
| **Mars** (Act 2 mid) | ` ` | `o`, `O`, `r` | `4`, `5`, `*` | `3` | Spark → `3`/`2` |
| **Teal** (Act 2 end) | ` ` | `t`, `T`, `b` | `.`, `+`, `~` | `T` | Spark → `T`/`c` |
| **Purple Dusk** (Act 3) | ` ` | `k`, `K`, `d` | `+`, `*`, `~` | `V` | Spark → `V`/`M` |
| **Gold/Amber** (Act 3 final + Nemesis) | ` ` | `q`, `Q`, `a` | `Y`, `*`, `+` | `Y` | Spark → `Y`/`A` |

**Transición entre temas:** fade 30 frames (0.25s) entre acts. Particle tint cambia de inmediato al crossfade midpoint (frame 15). BGM crossfade 60 frames.

### Sprite style guide

- **Proporción:** 1:1 (square pixels) SIEMPRE. Ningún sprite con aspect ratio != 1.
- **Tamaño máximo:** 32×32 (ship principal), 16×16 (enemigos), 8×8 (mini-drones, partículas pequeñas), 48×48 (boss final, Nemesis).
- **Outline:** 1px negro (`^` char) en TODOS los sprites con color base. Crítico para legibilidad contra cualquier fondo (Cave philosophy: balas y ships siempre legibles).
- **Glow halo:** sprites "luminosos" (bullets cargadas, special, boss cores) tienen 1 capa de glow halo 4–8 px alrededor, color accent del path o del tema. Pre-bakead en init.
- **Animation conventions:**
  - **Player ship:** 4 facings (up / up-tilt / horiz / down). Frame 0 = neutral, frame 1 = tilt.
  - **Enemies:** 2-frame idle (frame 0 = base, frame 1 = attack pose o wobble).
  - **Bosses:** 4 frames (idle, attack-windup, attack-fire, attack-recover). Loop 12 FPS.
  - **Bullets:** 4-frame pulse, 16 FPS, scale 0.9→1.1.
  - **Particles:** single-frame (tint cache en init).
  - **Power-ups:** 2-frame spin, 8 FPS (Cuphead-inspired "purposely stuttery" para contraste con bullets a 16 FPS).

### Particle style guide (cuándo usar qué kind)

### Particle style guide (cuándo usar qué kind)

> **Total: 18 kinds.** 12 originales del seed (spark, smoke, shrapnel, debris, shockwave, fire, electric, dust, muzzle, glow, ion-wake, flash) + 6 net new (ring-fill, ring-thick, electric-arc, square, line, light-flash). Las variantes `debris-soft` y `glow-soft` son modifiers del `debris` y `glow` originales (no kinds separados — ahorro de pool).

| # | Kind | Uso | Forma | Tamaño | Color base |
| --- | --- | --- | --- | --- | --- |
| 1 | **spark** | Hit feedback, kill micro | 1×1 dot | 1 px | Tint hit color |
| 2 | **smoke** | Explosion aftermath, debris | 4×4 → 8×8 expand | scale 1→2 | `▓`, `▒` (gray) |
| 3 | **shrapnel** | Enemy death core | 2×2 sharp | 2 px | Tint weapon path |
| 4 | **debris** | Boss death, heavy wreckage | 4×4 con rotación | rot variable | `▒`, `▓` |
| 5 | **shockwave** | Kill ring, bomb | ring expanding 0→64 | scale 0→64 | tint weapon |
| 6 | **ring-fill** | Bomb, special (INFERNO) | filled disc | scale 0→40 | weapon tint |
| 7 | **ring-thick** | Boss transition | thick ring 4px | scale 0→80 | white + tint |
| 8 | **fire** | Engine flame, plasma trail | 2×2 → 3×3 | scale 1→1.5 | `1`, `2`, `3`, `4` |
| 9 | **electric-arc** | Ion pierce, chain lightning | zigzag 4-segment | 8×4 jitter | `c`, `C` |
| 10 | **dust** | Big explosion, mars theme | 6×6 fuzzy | scale 1→2.5 | `o`, `O`, `▒` |
| 11 | **muzzle** | Shoot flash | ring 4px | 1 frame | `+` white |
| 12 | **glow** | Soft halo background, charged aura | 8×8 / 12×12 fuzzy | alpha 0.3–0.4 | tint path |
| 13 | **ion-wake** | Bullet trail | 2×2 dot fade | scale 0.5→1 | `i`, `I` |
| 14 | **flash** | Big kill, boss phase, damage feedback | 6×6 / 16×16 white | 1–2 frames | `+` / path |
| 15 | **square** | UI accent, score popup | 4×4 hard edge | static | theme accent |
| 16 | **line** | Beam trail, laser residual | 1×N line | 1 px | tint beam |
| 17 | **light-flash** | Damage feedback (variante de flash) | 6×6 quick | 2 frames | `+`/path |
| 18 | **glow-soft** | Charged bullet aura (variante de glow) | 8×8 fuzzy | alpha 0.3 | tint path |

> **Nota:** los kinds #17 (light-flash) y #18 (glow-soft) son behavioral variants de flash y glow respectivamente — reutilizan el mismo pool slot con flag de variant. Esto es por qué "18 kinds" se sostiene sin requerir pool adicional: el overhead de variant flag es de 1 bit por partícula.

### Tilt conventions

| Entidad | Tilt default | Tilt con input | Tilt al hit |
| --- | --- | --- | --- |
| Player | 0° | ±15° (con `vx` sign, smooth ease-out) | +8° (lean back) |
| Scout | 0° | N/A | N/A |
| Cruiser | 0° | N/A | N/A |
| Heavy | 0° | N/A | -3° (recoil) |
| Kamikaze | 0° | Track player homing | N/A |
| Drone | 0° | N/A | N/A |
| Sniper | 0° | N/A | N/A |
| Turret | 0° (cañón rota) | Cannon rotation per shot | N/A |
| Carrier | 0° | N/A | N/A |
| GOLIATH | 0° | ±5° (con move sine) | -2° phase 2 |
| HYDRA | 0° (heads ±5° each) | Heads track independent | +3° enraged |
| PHANTOM | 0° (blink teleport) | N/A | N/A |
| NEMESIS | 0° | ±5° phase-related (P2 = +3°, P3 = -3°, P4 = 0° static) | N/A |

---

## §9 — Audio Direction

### Tabla de 24 SFX procedurales

| # | Nombre | Voice | Freq base (Hz) | Slide (Hz/s) | Envelope A/D/S/R | Use case | Vol |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `shoot` | square | 880 | 0 | 0.005 / 0.05 / 0.0 / 0.05 | Bullet fired L1 | 0.4 |
| 2 | `shoot_charged` | square | 1320 (level: 880→1320→1760) | +200 (sweep up) | 0.005 / 0.10 / 0.0 / 0.10 | Charged bullet fire | 0.6 |
| 3 | `hit` | noise | white | 0 | 0.002 / 0.04 / 0.0 / 0.04 | Player hit | 0.7 |
| 4 | `explode_small` | noise + triangle | 200 | -100 | 0.002 / 0.10 / 0.1 / 0.20 | Scout/Cruiser death | 0.6 |
| 5 | `explode_medium` | noise + saw | 150 | -80 | 0.002 / 0.15 / 0.1 / 0.30 | Heavy/Drone death | 0.7 |
| 6 | `explode_boss` | noise + saw + square | 100 | -50 | 0.005 / 0.30 / 0.2 / 0.80 | Boss death finale | 1.0 |
| 7 | `bomb` | saw | 80 | -40 | 0.002 / 0.20 / 0.3 / 0.40 | Bomb triggered | 0.9 |
| 8 | `powerup` | triangle | 660 | +440 | 0.005 / 0.05 / 0.4 / 0.20 | Power-up collected | 0.5 |
| 9 | `dash` | noise (sweep) | 2000→500 | -3000 | 0.005 / 0.05 / 0.0 / 0.10 | Dash whoosh | 0.4 |
| 10 | `multiplier_up` | square (arp) | 880→1320→1760 | stepped | 0.005 / 0.02 / 0.0 / 0.10 | Multiplier increase | 0.5 |
| 11 | `boss_warning` | saw + noise | 80 | 0 | 0.010 / 0.30 / 0.5 / 0.50 | Boss intro stinger | 0.9 |
| 12 | `boss_phase_change` | saw + square | 200→100 | -100 | 0.005 / 0.20 / 0.3 / 0.60 | Phase transition | 1.0 |
| 13 | `wave_cleared` | triangle (chime) | 1320→1760→2200 | +200 (arp up) | 0.005 / 0.10 / 0.0 / 0.30 | Wave complete | 0.6 |
| 14 | `act_clear` | triangle + square (fanfare) | 440→880→1320 | +200 | 0.010 / 0.20 / 0.5 / 0.60 | Act boss defeated | 0.8 |
| 15 | `game_over` | saw (descending) | 440→80 | -200 | 0.020 / 0.40 / 0.3 / 1.20 | Game over sting | 0.9 |
| 16 | `victory` | triangle (fanfare) | 440→880→1320→1760 | +300 | 0.020 / 0.30 / 0.7 / 1.50 | Victory sting | 1.0 |
| 17 | `ui_click` | square | 1200 | 0 | 0.002 / 0.02 / 0.0 / 0.05 | UI confirm | 0.3 |
| 18 | `ui_hover` | triangle | 1500 | 0 | 0.002 / 0.02 / 0.0 / 0.05 | UI hover | 0.2 |
| 19 | `charge_loop` | square (loop) | 220→1760 | +200 (per cycle) | 0.050 / 0.05 / 0.7 / 0.10 | Charge holding L1→L2→L3 | 0.4 |
| 20 | `beam_charge` | noise + saw | 100→800 | +700 | 0.100 / 0.20 / 0.5 / 0.10 | Beam windup | 0.6 |
| 21 | `beam_fire` | square + saw | 800 | 0 | 0.005 / 0.30 / 0.0 / 0.10 | Beam release | 0.7 |
| 22 | `missile_lock` | square (pulse) | 2000 | 0 | 0.005 / 0.05 / 0.0 / 0.05 | Homing lock-on | 0.4 |
| 23 | `missile_fire` | saw | 400 | -200 | 0.005 / 0.10 / 0.0 / 0.10 | Homing missile launch | 0.5 |
| 24 | `screen_shake_thump` | noise (low) | 60 | 0 | 0.002 / 0.08 / 0.0 / 0.10 | Trauma shake thump | 0.5 |

### 4 BGM procedurales

Estructura: secciones A-B de 30–45s, loop imperceptible. Generadas con square+triangle+saw+noise mezclados. Cap a 4 voces simultáneas.

#### **BGM 1: title (idle pad)** — 32s loop

- **Sección A (0–16s):** triangle pad en Cm, 4 notas (C3, G3, Eb4, Bb4), 1 nota cada 4s, reverb 0.3.
- **Sección B (16–32s):** square lead entra con arpegio C-E-G-C-E-G (octavas), 1 nota cada 0.5s, fade in 4s, fade out 4s al final.
- **Tempo:** 80 BPM.
- **Vol:** 0.5 (canal 0).

#### **BGM 2: act_normal (chase)** — 40s loop

- **Sección A (0–20s):** saw bass C2-G2 alternando 0.5s cada uno, square lead arpegio C4-E4-G4-Bb4 0.25s por nota, noise hi-hat cada 0.25s.
- **Sección B (20–40s):** tempo sube 90→110 BPM, lead sube octava, entra triangle pad C5.
- **Vol:** 0.6 (canal 1).

#### **BGM 3: boss_fight (intense)** — 36s loop

- **Sección A (0–18s):** saw bass rápido C2-C2-G2-G2 (0.25s cada), square lead C5-G5-Eb6-Bb5 alternando, noise snare cada 0.5s, triangle pad en Cm.
- **Sección B (18–36s):** +20% tempo, lead sube a C6, snare más denso (cada 0.25s), +voice square en F#5 (tritono).
- **Vol:** 0.7 (canal 2).

#### **BGM 4: credits (resolution)** — 48s loop

- **Sección A (0–24s):** triangle pad en F major (resolución), lead square F4-A4-C5 0.5s por nota, voice echo decay 0.4s.
- **Sección B (24–48s):** tempo estable 70 BPM, voice triangle entra en F5-A5-C6 1s por nota, fade out 8s al final.
- **Vol:** 0.6 (canal 3).

### Mixer routing (16 channels)

| Channel # | Prioridad | SFX reservado | Vol máx | Notas |
| --- | --- | --- | --- | --- |
| 0 | **BGM** | title | 0.5 | Siempre 1 voice |
| 1 | **BGM** | act_normal | 0.6 | Siempre 1 voice |
| 2 | **BGM** | boss_fight | 0.7 | Siempre 1 voice |
| 3 | **BGM** | credits | 0.6 | Siempre 1 voice |
| 4 | **HIGH** (boss, expl_boss, victory) | expl_boss / victory / act_clear | 1.0 | Nunca cortar |
| 5 | **HIGH** | boss_warning / boss_phase_change | 0.9–1.0 | Nunca cortar |
| 6 | **HIGH** | bomb | 0.9 | Puede superponerse con otro HIGH |
| 7 | **MEDIUM** (player attack) | shoot / shoot_charged | 0.4–0.6 | Polyphony 4–6 |
| 8 | **MEDIUM** | shoot (channel 2) | 0.4–0.6 | Polyphony 4–6 |
| 9 | **MEDIUM** | hit | 0.7 | Re-trigger ok |
| 10 | **MEDIUM** | dash / perfect_dash | 0.4 | Re-trigger ok |
| 11 | **MEDIUM** | charge_loop | 0.4 | Loop 1 voice |
| 12 | **LOW** (UI) | ui_click / ui_hover | 0.2–0.3 | Re-trigger ok |
| 13 | **LOW** | powerup / multiplier_up | 0.5 | Re-trigger ok |
| 14 | **LOW** | beam_charge / beam_fire | 0.6–0.7 | Polyphony 2 |
| 15 | **LOW** | missile_lock / missile_fire | 0.4–0.5 | Polyphony 2 |

**Reglas:**
- `pygame.mixer.set_num_channels(16)` ANTES de cualquier `Sound()` creation.
- Sample rate 44100 Hz, 16-bit signed PCM, buffer 512 samples.
- Si `pygame.mixer.init()` falla → log warning, set `MIXER_AVAILABLE = False`, todos los SFX son no-op (return immediately).
- Polyphony: en channels 7–8 (player attack), permitir hasta 6 simultáneos con `find_channel()` que priorice los más viejos.

### ADSR envelope (referencia rápida)

```
A: attack (0→peak),   0.005–0.05s  (click inicial)
D: decay (peak→sust), 0.05–0.2s    (caída a nivel sustain)
S: sustain level,     0.0–0.7      (nivel mientras hold)
R: release (sust→0),  0.1–0.6s     (fade out al final)
```

**Regla:** todo SFX debe tener A+D+R explícitos. S=0 para one-shot (no-loop). SFX cortos (< 0.3s) → A corta, D y R iguales. SFX largos (boss, BGM) → A larga, S media, R larga.

---

## §10 — Juice + Game Feel

### Trauma model (Eiserloh)

Modelo canónico de Squirrel Eiserloh, GDC 2017, "Juicing Your Cameras with Math". **No tocar la fórmula.** Escalar max_px de 4 a 8.

```
offset_x = max_px * trauma² * noise(seed, time)
offset_y = max_px * trauma² * noise(seed + 1, time)
trauma -= decay * dt   # decay = 0.88, dt normalizado a 60Hz equivalente
trauma = max(0, min(1, trauma))   # clamp 0..1
```

**Tabla de trauma por evento:**

| Evento | Trauma amount | Decay override | Justificación |
| --- | --- | --- | --- |
| Player hit | 0.35 | 0.86 | Seed value, calibrado |
| Scout/Cruiser kill | 0.08 | default | Light feedback |
| Heavy kill | 0.20 | default | Tank feedback |
| Kamikaze detonation (en aire) | 0.15 | default | Mid-weight |
| Kamikaze detonation (en contacto) | 0.25 | default | High impact |
| Drone death | 0.05 | default | Light |
| Sniper death | 0.18 | default | Tower fall |
| Turret death | 0.15 | default | Anclada, momento |
| Carrier death | 0.30 | 0.85 | Slower decay (largo feedback) |
| Boss death finale | 0.60 | 0.82 | Climax |
| Bomb triggered | 0.20 | default | Screen-wide |
| Boss phase transition | 0.50 | 0.85 | Hollow Knight ref |
| Dash whoosh | 0.05 | default | Micro |
| Perfect dash (witch time) | 0.10 | 0.92 | Slow decay (largo) |
| Multiplier 16x reached | 0.15 | default | Reward |
| Hit stop end (snap-back) | 0.05 | default | Subtle |

**Max 8px offset** (`SHAKE_MAX_PX = 8.0`, vs 4.0 seed). Decay 0.88, normalizado a `dt * 60` (para que sea frame-rate independent).

### Hitstop rules

| Evento | Frames | Justificación |
| --- | --- | --- |
| Scout kill | 3 | Quick feedback |
| Cruiser kill | 4 | Slightly more |
| Heavy kill | 6 | Impactful |
| Kamikaze detonation (aire) | 5 | Tension release |
| Kamikaze detonation (contacto) | 8 | High stakes |
| Drone / mini-drone kill | 2 | Minimal |
| Sniper kill | 5 | Tower fall |
| Turret kill | 4 | Mid |
| Carrier kill | 8 | Sub-boss weight |
| Boss hit (player bullet connects) | 2 | Acknowledge hit |
| Boss phase transition | 6 | Hollow Knight ref |
| Boss death finale | 12 | Maximum emphasis |
| Bomb triggered | 8 | Screen-wide moment |
| Player death | 10 | Critical |
| Multiplier 16x reached | 3 | Reward |
| Perfect dash (just dodged) | 4 | Feedback |

**Implementación:** `Hitstop.trigger(frames)` encola un pause de N fixed-timesteps donde `dt = 0` para game logic. Render sigue (post-processing, particles, shake, etc. siguen actualizándose para mantener VFX vivo durante hitstop).

### Slow-mo rules

| Evento | Factor | Duration (frames) | Justificación |
| --- | --- | --- | --- |
| Charged bullet fire | 0.95 | 4 | Subtle "weight" |
| Perfect dash (witch time) | 0.30 | 30 (0.25s @ 120 FPS) | Bayonetta ref |
| Multiplier 16x reached | 0.85 | 12 | Reward emphasis |
| Bomb triggered | 0.50 | 8 | Screen-wide moment |
| Boss phase transition | 0.70 | 12 | Hollow Knight ref |
| Boss death finale | 0.40 | 24 | Climax |
| DOOM-style finisher (enemy < 10% HP) | 0.50 | 12 | Melee finisher feel |

**Prioridad:** si hitstop + slow-mo concurrentes → hitstop tiene prioridad, slow-mo arranca cuando hitstop termina.

**Implementación:** `SlowMo.trigger(factor, frames)` encola un override de `FIXED_DT *= factor` por N fixed-timesteps. Hitstop y slow-mo se procesan en orden FIFO.

### Camera shake zones (per-attack-pattern)

| Attack pattern | Shake intensity | Zone | Justificación |
| --- | --- | --- | --- |
| GOLIATH 3-spread | 0.05 | 4px max | Light |
| GOLIATH ring sweep | 0.12 | 6px max | Mid |
| HYDRA 5-spread triple | 0.15 | 6px max | Mid |
| HYDRA aura DoT (entering) | 0.05 | 4px max | Subtle danger |
| PHANTOM homing | 0.08 | 4px max | Light |
| PHANTOM laser fire | 0.20 | 8px max | Heavy (laser visible) |
| NEMESIS P1 attack | 0.10 | 4px max | Calm start |
| NEMESIS P2 attack | 0.15 | 6px max | Tension |
| NEMESIS P3 attack | 0.20 | 8px max | High |
| NEMESIS P4 desperation | 0.30 (constante) | 8px max | Climax |

### Screen-flash rules

| Tipo | Color | Duración | Trigger |
| --- | --- | --- | --- |
| **White flash (kill grande)** | `(255, 255, 255)` | 2 frames | Boss hit, super kill |
| **Red flash (player hit)** | `(255, 60, 40)` | 3 frames | Player take_damage |
| **Blue flash (boss phase)** | `(80, 200, 255)` | 2 frames | Boss phase transition |
| **Gold flash (multiplier max)** | `(255, 220, 80)` | 2 frames | Multiplier reaches 16× |
| **Cyan flash (perfect dash)** | `(120, 240, 255)` | 2 frames | Perfect dash triggered |
| **Magenta flash (special fire)** | `(255, 120, 200)` | 3 frames | Special attack launched |
| **Dim red (low HP)** | `(80, 0, 0)` 30% alpha | continuo si HP ≤ 1 | Visual warning |

### Chromatic aberration

- **Trigger:** `PauseScene.on_enter()` (al pausar el juego).
- **Implementación:** render del frame previo con offsets RGB de ±2 px en 3 capas, blend con frame actual.
- **Duración:** mientras pause está activo.
- **Justificación:** sensación de "el tiempo se detiene" estilo DMC/Bayonetta pause.

### Scanline overlay

- **Trigger:** `TITLE`, `VICTORY`, `CREDITS`, opcional en `PAUSE`.
- **Implementación:** surface pre-bakeada 240×360 con líneas horizontales cada 2px, alpha 0.15, blend sobre scene.
- **Justificación:** aesthetic 8-bit CRT sutil, no obstructivo.

### Score popup flotante

- **Trigger:** cada kill (no drop).
- **Sprite:** número grande 12px o 16px según score, color según milestone:
  - < 500: blanco `(255, 255, 255)`
  - 500–999: verde `(120, 255, 120)`
  - 1000–4999: dorado `(255, 220, 80)`
  - 5000+: dorado brillante `(255, 180, 40)` con sparkle 8 particles
- **Animation:** fade in 4 frames, hold 30 frames, fade out + drift up 30 frames, total 64 frames.
- **Multiplicador activo:** popup muestra "x4 +800" en lugar de solo "+200" (con multiplier prefijo).
- **Pool:** 32 damage popups (suficiente para boss fight denso).

### "DOOM-style" finisher

- **Trigger:** enemy HP < 10% AND player dashing.
- **Efecto:** enemy explotación large (32 sparks + 2 shockwaves + debris), score bonus +500, 0.5s slow-mo a 0.5×, screen-shake 0.2.
- **Justificación:** DOOM 2016 glory kill adaptado a shmup. Reward para el jugador skilled que conserva enemigos low-HP.

---

## §11 — Technical Architecture

### Diagrama ASCII de módulos y dependencias

```
                        ┌──────────────────────────┐
                        │      main.py (entry)     │
                        │  --check, --profile,     │
                        │  --act, --boss, --stress │
                        └────────────┬─────────────┘
                                     │
                        ┌────────────▼─────────────┐
                        │     core/game.py         │
                        │   Game (root)            │
                        │   fixed-timestep loop    │
                        └────────────┬─────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
   ┌──────────▼──────────┐ ┌─────────▼────────┐ ┌──────────▼──────────┐
   │ core/scene_manager  │ │  core/event_bus  │ │  core/settings      │
   │ Scene stack         │ │ 25+ typed events │ │ constants (no logic)│
   │ TITLE/ACT_INTRO/... │ │ subscribe/emit   │ │                     │
   └──────────┬──────────┘ └─────────┬────────┘ └─────────────────────┘
              │                      │
              │         ┌────────────┴────────────┐
              │         │                         │
   ┌──────────▼─────────▼──────┐         ┌────────▼────────────┐
   │  ui/* (5 scenes)          │         │  systems/*          │
   │  title, gameplay,         │         │  pool, particle_eng │
   │  pause, game_over,        │         │  projectile, screen_│
   │  (boss_intro, act_clear)  │         │  shake, hitstop,    │
   │                           │         │  parallax, sprite_  │
   │  + HUD overlay            │         │  factory,           │
   └──────────────┬────────────┘         │  scoring_system,    │
                  │                      │  weapon_system,     │
                  │                      │  wave_manager,      │
                  │                      │  explosion,         │
                  │                      │  collision          │
                  │                      └────────┬────────────┘
                  │                               │
   ┌──────────────▼──────────┐         ┌─────────▼─────────────┐
   │  entities/              │         │  audio/synth           │
   │  player/*               │◄────────┤  16-channel mixer     │
   │  Player + 7 FSM states  │         │  procedural SFX+BGM    │  (idle/move/charge/shoot/dash/hit/dead)
   │  enemies/*              │         │  ADSR envelope         │
   │  8 archetypes + 4 bosses│         └───────────────────────┘
   │  wave_manager           │
   └─────────────────────────┘         ┌───────────────────────┐
                                       │  utils/*              │
                                       │  easing, palette,     │
                                       │  rng_seed, math_helpers│
                                       └───────────────────────┘
```

**Reglas de dependencia:**
- `core/*` puede importar de `utils/*` y `systems/pool.py`.
- `systems/*` puede importar de `core/event_bus`, `core/settings`, `utils/*`.
- `entities/*` puede importar de `core/*`, `systems/*`, `utils/*`, `audio/synth`.
- `ui/*` puede importar de `core/*`, `entities/*`, `systems/*` (read-only), `utils/*`.
- `audio/*` solo importa de `core/settings`, `utils/math_helpers`.
- **CERO** `import motor.*` desde `src/` (soberanía).

### Tabla de pools y tamaños

| Pool | Tamaño | Tipo | Notas |
| --- | --- | --- | --- |
| `ProjectilePool` | 400 (base), expand +200 on BOSS_FIGHT = 600 max | Projectile | Player bullets (150), enemy bullets (200), boss bullets (50+) |
| `ParticleEngine` | 1500 | Particle | 18 kinds |
| `DebrisPool` | 200 (vs 100 seed) | Debris (físico con rotación) | Boss deaths, carrier wreck |
| `DamagePopupPool` | 32 | DamagePopup | Score flotante |
| `EnemyPool` | 64 | Enemy | Mix de 8 arquetipos |
| `BossPool` | 4 | Boss | Uno activo a la vez |
| `PowerUpPool` | 16 | PowerUp | Drops |
| `StarField` | 250 (5 layers × 50) | Star | Parallax |
| `NebulaCloud` | 6 | Nebula | Parallax |
| `PlanetField` | 2 | Planet | Decorativo, 1 activo + 1 off-screen |
| `PlayerBullet` (sub-pool) | 80 | Bullet | Reusa ProjectilePool con kind marker |
| `EnemyBullet` (sub-pool) | 120 | Bullet | Reusa ProjectilePool |
| `BossBullet` (sub-pool) | 200 | Bullet | Reusa ProjectilePool |

### Tabla de pre-baked assets (init)

| Asset | Cantidad | Ubicación | Justificación |
| --- | --- | --- | --- |
| Player ship (4 facings) | 4 surfaces 18×16 | `sprite_factory._ship_cache` | Single alloc |
| Player ship tilted variants | 4 × 3 tilt angles = 12 | `sprite_factory._ship_tilt_cache` | Tilt interpolation |
| Player ship charge glow | 3 (L1/L2/L3) | `sprite_factory._ship_charge_cache` | Level visual |
| Enemy sprites (8 arquetipos × 2 frames) | 16 surfaces | `sprite_factory._enemy_cache` | All enemies pre-baked |
| Boss sprites (4 bosses × 4 frames) | 16 surfaces | `sprite_factory._boss_cache` | All bosses pre-baked |
| Bullet sprites (4 types × 4 frames) | 16 surfaces | `sprite_factory._bullet_cache` | Animated bullets |
| Particle surfaces (18 kinds) | 18 surfaces base | `sprite_factory._particle_cache` | Single base per kind |
| Particle tint cache | 64 colors × 18 kinds = 1152 max | `ParticleEngine.tint_cache` LRU 128 | Most-used tints |
| PowerUp sprites (6 types) | 6 surfaces 12×12 | `sprite_factory._powerup_cache` | All drops pre-baked |
| HUD icons (HP, bomb, multiplier, weapon) | 12 surfaces | `sprite_factory._hud_cache` | HUD pre-baked |
| Screen flash surfaces (7 types) | 7 surfaces 240×360 | `sprite_factory._flash_cache` | Pre-baked dim overlays |
| Parallax star surfaces (5 layers) | 5 surfaces | `parallax._star_cache` | Star layers pre-baked |
| Nebula cloud surfaces (6 types) | 6 surfaces | `parallax._nebula_cache` | Procedural nebula |
| Theme tints (6 themes × 4 layers) | 24 tints | `palette._theme_tints` | Theme change instant |
| Scanline overlay | 1 surface 240×360 | `ui._scanline_cache` | CRT effect |
| Chromatic aberration layers | 3 surfaces | `ui._chromatic_cache` | Pause effect |
| 24 SFX buffers | 24 `array.array('h')` | `synth._sfx_cache` | Pre-rendered |
| 4 BGM buffers (sección A) | 4 `array.array('h')` | `synth._bgm_cache` | Pre-rendered, loop |
| 4 BGM buffers (sección B) | 4 `array.array('h')` | `synth._bgm_cache` | Pre-rendered, loop |
| Background gradient (6 themes) | 6 surfaces 240×360 | `parallax._gradient_cache` | Theme bg pre-baked |
| **Total surfaces in init** | **~500 surfaces** | — | One-time alloc |
| **Total memory in init** | **~12 MB** (32-bit surfaces) | — | Within budget |

### Frame budget breakdown (8.33 ms @ 120 FPS)

| Phase | Budget | Contenido | Mitigación |
| --- | --- | --- | --- |
| **Input** | 0.10 ms | `pygame.event.get()`, key state poll | Single call, cache result |
| **Update logic** | 4.00 ms | Player FSM, enemy AI, wave manager, scoring, weapon | Profile + optimize hot paths |
| └ Player FSM | 0.10 ms | State transition + timers | Tabla de transiciones, no if-else |
| └ Enemy update (8 max) | 0.50 ms | Move + attack cooldown + collision check | Pool + sentinel |
| └ Boss update (1 active) | 0.80 ms | Phase logic + attack selection + bullet spawn | Pre-computed attack table |
| └ Wave manager | 0.20 ms | Spawn script + adaptive difficulty | JSON loaded once |
| └ Scoring | 0.05 ms | Multiplier update + popup spawn | O(1) lookup |
| └ Weapon system | 0.20 ms | Charge timer + level check + special unlock | State machine |
| └ Collision (broadphase) | 1.20 ms | Spatial hash or grid | Grid 32×32 cells |
| └ Collision (narrow) | 0.50 ms | AABB checks | Only nearby pairs |
| └ Particle update (1500) | 0.75 ms | Move + life decrement + flags | Pool with active flag, skip inactive |
| └ Projectile update (400) | 0.12 ms | Move + trail + bounds check | Pool with active flag |
| └ Other (HUD, etc) | 0.08 ms | Number formatting + state poll | — |
| **Render** | 2.00 ms | Compose scene graph + blits | Single `target.blits()` |
| └ Scene clear | 0.05 ms | `target.fill(BG_COLOR)` | — |
| └ Parallax render (5 layers) | 0.40 ms | Tile blits | Integer-aligned |
| └ HUD render | 0.30 ms | Composite HUD layers | Pre-baked icons |
| └ Entity blits batch | 1.00 ms | Player + enemies + bullets (≈ 200 entities) | Single `target.blits()` |
| └ Particle blits batch | 0.20 ms | 1500 particles in one `target.blits()` | Tint cache hit |
| └ Post-FX (shake, flash) | 0.05 ms | Offset + blend | Already pre-baked |
| **Blits submission** | 2.00 ms | OS compositor + present | Pygame 2.6 `BLIT_PREMULTIPLIED` |
| **Slack** | 0.33 ms | GC pause, OS jitter, MIDI | — |
| **Total** | **8.33 ms** | 120 FPS lock | — |

**Hard rule:** cualquier `pygame.Surface((w, h))` dentro de `update()` o `draw()` de un sistema = 0 (verificar con `rg`).

### cProfile hotspots esperados y mitigación

| Hotspot esperado | Razón | Mitigación |
| --- | --- | --- |
| `pygame.Surface.blit` (lento en miles) | Nativo de SDL, no optimizado para batch | Single `target.blits([(surf, pos), ...])` 1 vez/frame |
| Collision check O(n×m) | Player bullets × enemies | Spatial hash 32×32 cells, broadphase |
| Particle update (1500) | Loop sobre 1500 entities | Pool con `active` flag, skip inactive en 1 cycle |
| Projectile update (400) | Similar | Pool, bounds check O(1) |
| `math.sin/cos` (miles/frame) | Trig por partícula | Lookup table 360 entries para sin, derivar cos de sin |
| String formatting (score popup) | `f"{score:,}"` repetido | Pre-format en score change event, no per frame |
| `random.random()` overhead | Per particle spawn | Cachear rng instance, batch cuando sea posible |
| `pygame.draw.*` (per-frame) | Dibujo vectorial | Pre-bakear a Surface, blit surface |
| Audio mixing overhead | 16 channels | Limitar polyphony, fade out voices |

### Performance budget validation

- **Comando:** `python main.py --profile --duration 60`
- **Métricas a registrar:**
  - FPS min / max / avg / p99 (target: avg ≥ 120, p99 ≥ 100)
  - Frame time histogram (target: 95% frames < 8.33ms)
  - Particle count max (target: < 1500)
  - Projectile count max (target: < 400)
  - Memory delta en 60s (target: < 1 MB = no leak)
- **Stress test:** `python main.py --stress 1500particles 400bullets --duration 30` → target ≥ 90 FPS, 0 crashes.

### Soberanía (no dependencia externa)

- `rg 'import motor' src/` → **0 matches**.
- `rg '^import (?!pygame|array|math|random|json|os|sys|typing|dataclasses|enum|functools|itertools|collections|pathlib|datetime)' src/` → 0 matches unexpected.
- `pyproject.toml` deps: solo `pygame>=2.6.0`. Sin numpy, scipy, requests, etc.

---

## §12 — Risks + Open Questions

### Riesgos técnicos con mitigación

| # | Riesgo | Probabilidad | Impacto | Mitigación |
| --- | --- | --- | --- | --- |
| 1 | 120 FPS no alcanzable en hardware modesto (iGPU) | Media | Alto | `--fps-target 90` flag opcional; degradar gracefully; documentar min spec |
| 2 | pygame.mixer.init() falla en headless / sandbox | Baja | Medio | Null-safe wrapper; si falla, `MIXER_AVAILABLE=False`, SFX son no-op |
| 3 | Particle pool exhaustion (1500 insuficientes en boss) | Baja | Medio | `ProjectilePool.expand(200)` en BOSS_FIGHT; pool de emergencia con emission rate-limit |
| 4 | Audio popping/clipping en SFX simultáneos | Media | Bajo | Polyphony limit + ADSR release; mixer.set_num_channels(16) prevent overflow |
| 5 | 64-color palette overflow (más de 16 colores por sprite) | Baja | Bajo | Validar en `SpriteFactory.create()`; raise si >16 |
| 6 | Frame drops en boss phase transition (VFX full-screen) | Media | Alto | Pre-baked surfaces; no alloc en trigger; cProfile medir |
| 7 | High-score JSON corruption (write fail mid-write) | Baja | Medio | Atomic write (temp file + rename); backup file rotation |
| 8 | Mypy strict regression con nuevos tipos | Media | Bajo | `mypy src/` en CI gate; pre-commit hook |
| 9 | Coverage gate no alcanzable (35% difícil) | Media | Medio | Subir progresivo: 5→12→20→28→35 por BLOQUE; tests críticos no negociables |
| 10 | Seed migration pierde features (sprite sizes, pools) | Baja | Alto | Refactor atómico, test exhaustivo post-migration |
| 11 | 18 wave JSON scripts inconsistentes | Baja | Medio | Schema validator + smoke test `python main.py --validate-waves` |
| 12 | BGM procedural suena "malo" / repetitivo | Alta | Alto | Cap a 30–45s loops; arpegio + bajo cambia en sección B; feedback temprano de playtesters |
| 13 | 4 bosses muy difíciles de balancear | Media | Alto | Difficulty curve table (acumulada); playtesting iterativo con 5+ testers |
| 14 | Memory leak en palette/theme change | Baja | Medio | Pre-bakear todos los 6 temas en init; theme swap = swap reference, no alloc |

### Decisiones que necesitan user input

| # | Decisión | Opciones | Recomendación |
| --- | --- | --- | --- |
| 1 | **Nombre final** | "VOID HUNTER" / "VOIDRUNNER" / "HUNTER OF THE VOID" / Otro | VOID HUNTER (actual) |
| 2 | **Ship sprite style** | Sharp angular (Cave) / Rounded organic (Touhou) / Blocky retro (Seed) | Sharp angular (más juice) |
| 3 | **Difficulty modes** | Solo Normal / Normal+Hard / Normal+Hard+Lunatic (placeholder) | Normal+Hard release, Lunatic placeholder |
| 4 | **Continue system** | Clásico (1 continue) / Modern (unlimited con penalty score) | Clásico 1 continue |
| 5 | **Boss music** | 1 BGM por boss / mismo boss_fight BGM con section change / 4 BGM distintos | 1 BGM con section change (más eficiente) |
| 6 | **Score persistence** | Local JSON / Leaderboard online | Local JSON (offline, no server) |
| 7 | **Localization** | Solo EN / EN+ES+JP | Solo EN release v1.0 |
| 8 | **Demo / trailer** | No / Sí GIF showcase | No (focus en release completo) |
| 9 | **Color blind support** | No / Sí (palette alternative) | No v1.0 (paleta ya contrastante) |
| 10 | **Co-op** | No / 2-player local | No (fuera de scope, inspiración Ikaruga) |

---

## §13 — Execution Plan (BLOQUE 0..N)

### Tabla de bloques

| BLOQUE | Nombre | Archivos creados/modificados | Tests añadidos | FPS delta | Commit msg |
| --- | --- | --- | --- | --- | --- |
| **0** | **Bootstrap & settings** | `main.py`, `src/core/settings.py` (FPS_TARGET=120, FIXED_DT=1/120, pool sizes), `pyproject.toml`, `requirements.txt`, `README.md`, `.gitignore`, `docs/design/void-hunter-gdd.md` | `tests/test_settings.py` (8 tests) | Baseline @ 120 FPS empty | `chore: BLOQUE 0 bootstrap 120 FPS settings + GDD` |
| **1** | **Pool genérico + ParticleEngine expandido** | `src/systems/pool.py` (migrar), `src/systems/particle_engine.py` (12→18 kinds, pool 600→1500), `src/utils/palette.py` (32→64 chars) | `tests/test_particle_engine.py` (90+ tests) | -0.5ms (particle update más carga) | `feat: BLOQUE 1 pool + 18 kinds particle engine` |
| **2** | **ProjectilePool expandido + 4 sprite types** | `src/systems/projectile.py` (200→400, +4 sprite types, 4-frame anim) | `tests/test_projectile_pool.py` (12+ tests) | -0.1ms | `feat: BLOQUE 2 projectile pool expandido + 4 sprite types` |
| **3** | **SpriteFactory expandido** | `src/systems/sprite_factory.py` (+outline, glow_halo, tint_shift, composite_layers, dithered_circle, scanline_overlay) | `tests/test_sprite_factory.py` (18+ tests) | -0.3ms (init más lento, runtime igual) | `feat: BLOQUE 3 sprite factory expandido 6 helpers` |
| **4** | **Parallax 5 layers + 6 nebula types** | `src/systems/parallax.py` (4→5 layers, +6 nebula, +planet atmosphere +ring) | `tests/test_parallax.py` (8+ tests) | -0.2ms | `feat: BLOQUE 4 parallax 5 layers + 6 nebula + planets` |
| **5** | **Juice systems: ScreenShake + Hitstop + SlowMo** | `src/systems/screen_shake.py` (max 4→8), `src/systems/hitstop.py` (3-12 frames configurable), `src/systems/slowmo.py` (NEW), `src/core/event_bus.py` (25+ events) | `tests/test_screen_shake.py`, `tests/test_hitstop.py`, `tests/test_event_bus.py` (20+ tests combined) | -0.1ms | `feat: BLOQUE 5 juice systems: shake max8 + hitstop + slowmo + eventbus` |
| **6** | **Player FSM 7 states + dash + charge + bomb** | `src/entities/player/player.py` (refactor), `src/entities/player/states.py` (idle/move/charge/shoot/dash/hit/dead — CHARGE engloba build + fire internamente) | `tests/test_gameplay_fsm.py` (7 states, 10+ transitions) | -0.2ms | `feat: BLOQUE 6 player 7-state FSM + dash + charge + bomb` |
| **7** | **Weapon System 3 paths × 3 levels + special** | `src/systems/weapon_system.py` (NEW, plasma/ion/shock, level-up, special) | `tests/test_weapon_system.py` (36+ tests) | -0.1ms | `feat: BLOQUE 7 weapon system 3 paths 3 levels + special` |
| **8** | **8 enemy archetypes** | `src/entities/enemies/enemy.py` (base), 8 archetype files (scout/cruiser/heavy/kamikaze/drone/sniper/turret/carrier), `src/entities/enemies/pool.py` (64) | `tests/test_enemies.py` (8 archetypes × 5+ tests = 40+ tests) | -0.3ms | `feat: BLOQUE 8 8 enemy archetypes implementados` |
| **9** | **4 Bosses con FSM phase transitions** | `src/entities/enemies/boss.py` (refactor), 4 boss files (goliath/hydra/phantom/nemesis), `src/systems/boss_attacks.py` (NEW, 8-pattern pool) | `tests/test_boss_fsm.py` (4 bosses × 4 phases × 3+ tests = 48+ tests) | -0.4ms | `feat: BLOQUE 9 4 bosses 4-phase FSM + 8 attack patterns` |
| **10** | **WaveManager + 18 waves JSON** | `src/systems/wave_manager.py` (NEW, JSON scriptable, adaptive difficulty), `data/waves/act1_w1.json` ... `act3_w6.json` (18 files) | `tests/test_wave_manager.py` (18 × 2+ tests = 36+ tests) | -0.1ms | `feat: BLOQUE 10 wave manager + 18 waves JSON scripts` |
| **11** | **Scoring System + multiplier chain + high-score JSON** | `src/systems/scoring_system.py` (NEW, 1x-16x chain, decay 1.5s, element bonus, streak, high-score JSON) | `tests/test_scoring_system.py` (8+ tests) | -0.05ms | `feat: BLOQUE 11 scoring system + multiplier chain + high-score JSON` |
| **12** | **6 temas + paleta 64 chars + theme transitions** | `src/utils/palette.py` (5→6 themes), `src/systems/theme_manager.py` (NEW, fade 30 frames) | `tests/test_palette.py` (64 chars × 3 tests = 192+ tests) | -0.1ms | `feat: BLOQUE 12 6 themes + 64-char palette + theme fade` |
| **13** | **Audio: 24 SFX + 4 BGM procedurales** | `src/audio/synth.py` (ADSR configurable, +18 SFX, +4 BGM, 16 channels) | `tests/test_synth.py` (24+4 = 28 tests) | -0.0ms (audio no afecta FPS) | `feat: BLOQUE 13 audio 24 SFX + 4 BGM procedurales` |
| **14** | **GameStateMachine 9 states + 5 scenes** | `src/core/scene_manager.py` (9 states), `src/ui/title_scene.py` (refactor), `src/ui/act_intro_scene.py` (NEW), `src/ui/boss_intro_scene.py` (NEW), `src/ui/act_cleared_scene.py` (NEW), `src/ui/victory_scene.py` (NEW), `src/ui/credits_scene.py` (NEW) | `tests/test_scene_manager.py` (9 states × 3+ tests = 27+ tests) | -0.1ms | `feat: BLOQUE 14 game state machine 9 states + 5 new scenes` |
| **15** | **HUD completo + score popup + juice final** | `src/ui/hud.py` (HP/bombs/multiplier/weapon/level), `src/systems/damage_popup.py` (NEW, pool 32) | `tests/test_hud.py`, `tests/test_damage_popup.py` (10+ tests combined) | -0.2ms | `feat: BLOQUE 15 HUD + damage popup + final juice` |
| **16** | **Stress test + profiling + coverage gate** | `main.py` (--stress, --validate-waves flags), `tests/test_smoke.py` (12 verifications), CI workflow | Ajustar coverage gate a 35% | Verificación final | `chore: BLOQUE 16 stress test + coverage gate 35%` |
| **17** | **Polish + demo run + GDD final review** | README.md (final), CHANGELOG.md (todos los BLOQUE), demo GIF/screenshots | Manual playtest Act 1 + Nemesis P4 | Sign-off | `docs: BLOQUE 17 polish + demo + GDD final` |

### Dependencias entre bloques

```
0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14 → 15 → 16 → 17
     ↓   ↓   ↓   ↓   ↓   ↓   ↓   ↓   ↓    ↓    ↓    ↓    ↓    ↓    ↓    ↓
     └───┴───┴───┴───┴───┴───┴───┴───┴────┴────┴────┴────┴────┴────┴────┘
                              (tests, integration)

Críticos (blocking others):
  0 (settings) → TODO
  1 (pool/particle) → 2 (projectile), 6 (player), 8 (enemies), 9 (bosses)
  5 (event bus) → 6, 7, 8, 9, 10, 11
  6 (player FSM) → 7 (weapon), 8 (enemies), 11 (scoring)
  8 (enemies) → 9 (bosses), 10 (waves)
  14 (scenes) → 15 (HUD integration)
```

### Suite de smoke (12 verificaciones finales)

```bash
# 1. Imports + scene wiring OK
python main.py --check

# 2. FPS ≥ 120 en gameplay normal
python main.py --profile --duration 30

# 3. Stress test ≥ 90 FPS
python main.py --stress 1500particles 400bullets --duration 30

# 4. Act 1 completo sin crash
python main.py --act 1 --debug

# 5. Nemesis final boss enfrentable
python main.py --boss nemesis --debug

# 6. Validar 18 waves JSON
python main.py --validate-waves

# 7. Tests verdes
pytest tests/ -q

# 8. Coverage ≥ 35%
pytest --cov=src/ --cov-fail-under=35

# 9. Mypy strict 0 errores
mypy src/

# 10. No alloc per-frame en sistemas
rg 'pygame\.Surface\(' src/systems/update.py src/systems/draw.py    # 0 matches
rg 'target\.blit\(' src/systems/particle_engine.py | wc -l          # 1 (single)
rg 'target\.blit\(' src/ui/gameplay_scene.py | wc -l                # 1 (single)

# 11. Soberanía
rg 'import motor' src/                                                # 0 matches

# 12. 0 memory leaks en 60s
python main.py --profile --duration 60 --memory-trace
# Expected: < 1 MB delta
```

### Definition of Done (por BLOQUE)

- [ ] Código compila sin warnings (`python -m py_compile`).
- [ ] Tests del BLOQUE pasan (pytest -q).
- [ ] Coverage del módulo ≥ 35% (al cierre del BLOQUE 16).
- [ ] `rg 'pygame\.Surface\(' src/systems/` solo aparece en `init` paths.
- [ ] `rg 'target\.blit\('` cuenta = 1 por sistema de render (single batch).
- [ ] FPS regression < 0.5ms vs BLOQUE anterior.
- [ ] Mypy strict 0 errores en archivos modificados.
- [ ] Commit message sigue convención `feat: BLOQUE N ...`.
- [ ] CHANGELOG.md actualizado.
- [ ] Si BLOQUE introduce asset, pre-bakear en init, NO en update/draw.

### Out of scope (v1.0, placeholders para v2.0)

- [ ] Lunatic difficulty (placeholder en scoring formula).
- [ ] 2-player co-op (soberanía de polaridad en v1.0 single-player).
- [ ] Online leaderboard (v1.0 local JSON only).
- [ ] Localization EN+ES+JP (v1.0 EN only).
- [ ] Color blind mode (paleta base ya contrastante, sufficient v1.0).
- [ ] Replay system (fuera de scope).
- [ ] Mod tools / level editor (fuera de scope).
- [ ] Mobile port (Pygame desktop only).
- [ ] VR / motion controls (desktop only).
- [ ] Live wallpaper / idle demo mode (nice-to-have post-release).

---

## Apéndice A — Constantes de diseño (cheat-sheet)

```python
# Display
INTERNAL_W = 240
INTERNAL_H = 360
DEFAULT_SCALE = 4          # 960x1440
WINDOW_W = 960
WINDOW_H = 1440
FPS_TARGET = 120           # vs 60 seed
FIXED_DT = 1 / 120         # 8.333ms
DT_CLAMP = 1 / 30          # 33.33ms

# Pools
PROJECTILE_POOL = 400
PROJECTILE_POOL_BOSS = 600  # expand during boss
PARTICLE_POOL = 1500
DEBRIS_POOL = 200
DAMAGE_POPUP_POOL = 32
ENEMY_POOL = 64
BOSS_POOL = 4
POWERUP_POOL = 16

# Player
PLAYER_LIVES = 3
PLAYER_CONTINUES = 1
PLAYER_BOMBS = 3
PLAYER_BOMBS_MAX = 4        # con special
PLAYER_SPEED = 130.0
PLAYER_FIRE_COOLDOWN_S = 0.10
PLAYER_DASH_SPEED = 480.0
PLAYER_DASH_DURATION_S = 0.18
PLAYER_DASH_IFRAMES = 22
PLAYER_INVULN_FRAMES = 60
PLAYER_DEATH_DURATION_S = 1.20
PLAYER_RESPAWN_INVULN_S = 1.0

# Bullet FX
BULLET_TRAIL_PARTICLES_PER_FRAME = 1
ION_WAKE_RADIUS = 1

# Camera
TRAUMA_PER_KILL_SCOUT = 0.08
TRAUMA_PER_KILL_CRUISER = 0.10
TRAUMA_PER_KILL_HEAVY = 0.20
TRAUMA_PER_KILL_KAMIKAZE_AIR = 0.15
TRAUMA_PER_KILL_KAMIKAZE_CONTACT = 0.25
TRAUMA_PER_KILL_DRONE = 0.05
TRAUMA_PER_KILL_SNIPER = 0.18
TRAUMA_PER_KILL_TURRET = 0.15
TRAUMA_PER_KILL_CARRIER = 0.30
TRAUMA_PER_HIT = 0.35
TRAUMA_PER_BOSS_PHASE = 0.50
TRAUMA_PER_BOSS_DEATH = 0.60
TRAUMA_PER_BOMB = 0.20
TRAUMA_DECAY = 0.88
SHAKE_MAX_PX = 8.0          # vs 4.0 seed

# Hitstop
HITSTOP_FRAMES_SCOUT = 3
HITSTOP_FRAMES_HEAVY = 6
HITSTOP_FRAMES_BOSS = 2
HITSTOP_FRAMES_BOSS_PHASE = 6
HITSTOP_FRAMES_BOSS_DEATH = 12
HITSTOP_FRAMES_BOMB = 8
HITSTOP_FRAMES_PLAYER_DEATH = 10

# Slow-mo
SLOWMO_CHARGED_FACTOR = 0.95
SLOWMO_CHARGED_FRAMES = 4
SLOWMO_PERFECT_DASH_FACTOR = 0.30
SLOWMO_PERFECT_DASH_FRAMES = 30
SLOWMO_BOMB_FACTOR = 0.50
SLOWMO_BOMB_FRAMES = 8
SLOWMO_BOSS_PHASE_FACTOR = 0.70
SLOWMO_BOSS_PHASE_FRAMES = 12
SLOWMO_BOSS_DEATH_FACTOR = 0.40
SLOWMO_BOSS_DEATH_FRAMES = 24

# Wave
WAVE_KILL_TARGET = 20
WAVE_TIME_LIMIT_S = 30
SUBBOSS_TRIGGER_KILLS = 40
WAVE_GROWTH = 2

# Score
SCORE_PER_SCOUT = 50
SCORE_PER_CRUISER = 150
SCORE_PER_HEAVY = 400
SCORE_PER_KAMIKAZE = 200
SCORE_PER_KAMIKAZE_AIR = 500
SCORE_PER_DRONE = 80
SCORE_PER_MINI_DRONE = 50
SCORE_PER_SNIPER = 300
SCORE_PER_TURRET = 250
SCORE_PER_CARRIER = 800
SCORE_PER_GOLIATH = 5000
SCORE_PER_HYDRA = 8000
SCORE_PER_PHANTOM = 12000
SCORE_PER_NEMESIS = 20000
SCORE_PER_WAVE_CLEAR = 5000
SCORE_PER_ACT_CLEAR = 25000
MULTIPLIER_MAX = 16
MULTIPLIER_DECAY_S = 1.5
ELEMENT_BONUS = 1.5
STREAK_BONUS_CAP = 2.0

# Audio
MIXER_CHANNELS = 16
MIXER_SAMPLE_RATE = 44100
MIXER_BUFFER = 512
MIXER_BITS = 16

# Test gates
COVERAGE_GATE = 0.35
FPS_TARGET_NORMAL = 120
FPS_TARGET_STRESS = 90
```

---

## Apéndice B — Glosario de shmup-speak

| Término | Definición |
| --- | --- |
| **Hitbox** | Rectángulo donde una entidad recibe daño (visual vs hitbox pueden diferir: 70% factor forgiving). |
| **Hurtbox** | Rectángulo donde el player recibe daño (input invuln durante i-frames). |
| **Telegraph** | Frames de aviso visual antes de un ataque letal (≥30 frames en VOID HUNTER). |
| **i-frames** | Invulnerability frames, ventana donde el player no recibe daño (post-hit, durante dash). |
| **Bomb** | Recurso limitado (3 max) que limpia la pantalla. Decisión táctica mayor. |
| **Chain** | Multiplicador que sube con cada kill consecutivo, decae con el tiempo. |
| **Pellet / Spread** | Patrón de N balas en abanico desde un punto. |
| **Ring** | Patrón circular de N balas equi-espaciadas. |
| **Spiral** | Ring que rota con el tiempo, creando rosca visual. |
| **Homing** | Bala que ajusta su trayectoria hacia el player. |
| **Charge** | Disparo retenido que se potencia con el tiempo (L1→L2→L3). |
| **Perfect dash** | Dash ejecutado en el último frame antes de ser golpeado → witch-time slow-mo. |
| **Witch time** | Slow-mo activado por perfect dodge (Bayonetta reference). |
| **Trauma²** | Modelo de screen-shake donde el offset es proporcional al cuadrado del trauma (Eiserloh). |
| **Element bonus** | Multiplicador de daño cuando el path del player es fuerte contra el tipo de enemigo. |
| **Juice** | Game feel acumulado: screen-shake + particles + hitstop + slow-mo + sound coupling (Vlambeer). |
| **Polarity** | Sistema de Ikaruga donde el ship cambia de color y absorbe balas del opuesto. Adaptado a 3 paths. |
| **Bail-out** | Opción de último momento (dash, bomb) cuando el jugador está acorralado. |
| **Rank** | Calificación final de la run (D, C, B, A, S, S+, SSS) estilo DMC. |
| **Continue** | Crédito extra para revivir después de game over (1 en VOID HUNTER). |

---

## Apéndice C — Referencias citadas

1. **Pygame 2.6 release notes** — pygame.org/whatsnew. Surface.blits() con 4-tuplas, BLEND_PREMULTIPLIED, perf +30% en blits grandes.
2. **Squirrel Eiserloh, "Math for Game Programmers: Juicing Your Cameras with Math"** — GDC 2017. Trauma² modelo canónico.
3. **Jan-Marcel van Dijke, "Postmortem: Making a Pygame Shoot 'em Up"** — 2020. Pool, LRU tint cache, single blits batch, FSM, event bus.
4. **Vlambeer, "The Art of Screenshake"** — GDC 2013. 8 principles of juice (game feel).
5. **Bayer dithering matrix 4×4** — Wikipedia. `[[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]]`.
6. **Cave STG design philosophy** — cave-stg.com/devblog. "Always leave an escape route", rule of gaps.
7. **Pygame Mixer Best Practices** — pygame.org/docs/ref/mixer.html. 16 channels, 44100 Hz, pre-load.
8. **Shovel Knight postmortem** — 2014. 54-color global palette, 16 colors max per sprite.
9. **DoDonPachi scoring chain** — arcade manuals. 2×→3×→...→16×, decay 2s.
10. **Touhou difficulty curve** — ZUN interviews. 6 stages × 3 difficulties.
11. **Freesound.org CC0 SFX** — banco de referencia para futura migración a samples reales.
12. **Boss attack pattern catalog** — Cave, Touhou, Ikaruga, G-Darius. 8 patrones canónicos.
13. **Glenn Fiedler, "Fix Your Timestep"** — GDC 2014. Fixed-timestep accumulator pattern.
14. **Hollow Knight (2017)** — phase transitions, VFX full-screen.
15. **Metal Slug (1996)** — multi-stage explosions, juice grade-A.
16. **Ikaruga (2001)** — polarity system, scoring chain.
17. **DoDonPachi / Cave series** — bullet hell design philosophy.
18. **Celeste (2018)** — input lag ≤1 frame, response immediacy.
19. **Dead Cells (2018)** — "every kill matters", score popup feedback.
20. **Bayonetta (2009)** — witch time on perfect dodge.
21. **Cuphead (2017)** — 1930s cartoon aesthetic, 12 FPS animation stutter.
22. **DOOM (2016)** — glory kill finisher mechanic.
23. **DMC Devil May Cry (2013+)** — style ranking system (D, C, B, A, S, S+, SSS).
24. **R-Type (1987)** — charge shot + force pod.
25. **Gradius (1985)** — options system (satélites).
26. **Touhou Project (ZUN)** — 1-frame telegraph rules, pattern memorability.

---

> **Fin del SPEC.** Este documento es ejecutable: cada BLOQUE tiene archivos, tests, FPS delta esperado, y commit message. La duración total estimada: 12–16 semanas para un agente solo, 4–6 semanas para un equipo de 2. La barra de calidad (120 FPS lock, 35% coverage, 0 mypy errors, 0 alloc/frame, single blits/frame) es alta pero alcanzable siguiendo el plan en orden.
