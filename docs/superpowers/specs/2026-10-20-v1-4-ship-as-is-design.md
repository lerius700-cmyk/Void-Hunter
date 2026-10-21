# V1.4 Ship as-is — consolidación + primer push + upload del release v1.4.0 ya construido

**Fecha**: 2026-10-20
**Autor**: Mavis (root session `mvs_48557449a3f04f1dbde3f3e2f698e4b7`)
**Estado del proyecto al inicio**: rama `master`, último commit `954d298` (BLOQUE 66.5), sin remote configurado, ~50 archivos untracked (mezcla de debug scripts, logs viejos, y archivos temporales de la sesión actual).

## Contexto crítico: divergencia source ↔ binary

- **Source en git**: BLOQUE 66.5 + cambios uncommitted de esta sesión (óvalo revertido + test fix) que serían BLOQUE 66.6.
- **Binary existente** (`dist/void-hunter/void-hunter.exe`, 4.3 MB): empaquetado el 2026-09-06, reporta `VOID HUNTER v1.4.0 (BLOQUE 71)` en la barra. Fue compilado desde un source al que no tenemos acceso (probablemente otro working tree / máquina).
- **ZIP ya construido** (`dist/VoidHunter-v1.4.0-win64.zip`, 397 MB, generado 2026-10-09): release candidate acabado.

**Decisión del usuario**: ship v1.4.0 como-esta. NO rebuildeamos. Subimos el `.zip` v1.4.0 ya empaquetado como release, y pusheamos el source actual a GitHub para tracking (con un header/commit message que reconozca que el source está detrás del binario).

## Objetivo

Llevar el repo al estado "primer release público" en GitHub con:
1. Working tree consolidado (sin ruido, `.gitignore` actualizado).
2. Source pusheado a `https://github.com/lerius700-cmyk/Void-Hunter` (con nota de la brecha).
3. `VoidHunter-v1.4.0-win64.zip` (ya construido) subido como primera release.
4. Documentación: `OPERATIONS.md` para git/token, `KNOWN_ISSUES.md` para la brecha source↔binary y los tests pre-existentes.

## Decisiones del brainstorming (confirmadas con el usuario)

| # | Decisión | Elección |
|---|---|---|
| 1 | Cleanup | Conservar `tools/capture/`, borrar el resto, actualizar `.gitignore` |
| 2 | Token | GitHub CLI (`gh auth login`) — token en Windows Credential Manager, Mavis nunca lo ve |
| 3 | Repo | Ya existe: `https://github.com/lerius700-cmyk/Void-Hunter` |
| 4 | Estrategia de ship | Ship v1.4.0 como-esta (zip ya construido, sin rebuildear) |
| 5 | `gh` install | winget (`winget install --id GitHub.cli`) |
| 6 | CHANGELOG / release notes | Usuario redacta la prosa final con draft provisto por Mavis |

## Subsistemas (orden de ejecución)

### A. Consolidación del repo

**Input**: working tree actual con ~50 archivos untracked y 2 archivos modificados.
**Output**: working tree limpio + commit(s) que documenten la brecha source↔binary.

Acciones:
1. Borrar (vía `mavis-trash` para recuperabilidad):
   - `.Trash/`
   - Todos los `*.pytest_*.txt`, `*.smoke_*.txt`, `*.finalverify.txt`, `*.shield_*.txt`, `tests_*.txt`, `tests_dbg.txt`, `tests_full.txt`, `tests_run.txt`, `tests_baseline.txt`
   - `luffy_gear5_logo.png`, `tmp_luffy_gen.json`
   - `game-err.txt`, `game-out.txt`, `run-check-err.txt`, `run-check-out.txt`
   - `output/`, `.diff_runtime.txt`, `.finalverify.txt`, `.main_smoke.txt`
   - `tools/audit_shield_actual_shape.py`, `tools/audit_shield_pixel_position.py`, `tools/build_shield_mask.py`
   - `tools/redesign_bosses/_composite_left_arm_66_4e.py`, `tools/redesign_bosses/_regen_laser_66_4b.py`
   - `Assets/sprites/bosses/goliath/_backplate/` (dir + body.png — el PNG del intento de backplate que revertimos)
2. Conservar: `tools/capture/` (convención ya en repo) + todo lo demás tracked.
3. Actualizar `.gitignore` para añadir:
   ```
   # Session debug logs
   *.pytest_*.txt
   *.smoke_*.txt
   .Trash/
   tmp_*.json
   output/
   # One-off capture artefacts
   luffy_*.png
   *.diff_*.txt
   *.finalverify.txt
   *.main_smoke.txt
   tests_*.txt
   ```
4. Dos commits separados (mejor que uno gigante para preservabilidad):
   - **Commit 1**: `chore: consolidate working tree — drop session debris + refresh .gitignore`
     - Borra archivos listados arriba + actualización de `.gitignore`
   - **Commit 2**: `fix: GOLIATH oval reverted to user-approved values (BLOQUE 66.6)`
     - Incluye los 2 archivos modificados (`src/ui/gameplay_runtime.py` óvalo revertido, `tests/test_gameplay_runtime.py` test fix)
     - El commit message debe mencionar explícitamente: "Source at BLOQUE 66.6 lags behind binary v1.4.0 (BLOQUE 71); see docs/KNOWN_ISSUES.md"

### B. GitHub automation

**Output**: repo sincronizado en `https://github.com/lerius700-cmyk/Void-Hunter.git`, documentación para regeneración de token.

Acciones:
1. Crear `docs/OPERATIONS.md` con 4 secciones:
   - **Instalar `gh`** — comando `winget install --id GitHub.cli`, link al MSI alternativo (`https://github.com/cli/cli/releases/latest` → `gh_*_windows_amd64.msi`).
   - **Crear PAT en GitHub** — paso a paso: Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token con scope `repo` (commits + releases).
   - **Login local** — `gh auth login --with-token < github_token.txt` (token en archivo `.gitignored` con instrucciones de cleanup).
   - **Regenerar token** — qué hacer cuando github avisa "Token expired": regenerar y re-correr paso 3.
2. Crear `docs/KNOWN_ISSUES.md` con:
   - **Source ↔ binary gap**: BLOQUE 66.6 (source commiteado) ↔ BLOQUE 71 (binary v1.4.0). Diferencias exactas a documentar. Resolución: traer el otro source o rebuildear en próxima sesión.
   - **Tests pre-existentes fallando**: lista los 8 archivos de tests que fallan por path hardcodedo `D:\AI\void-hunter\Assets\background\tiles\act1` (no aplica al workspace actual en `F:\AI\MM\void-hunter`):
     - `test_asteroid_sprites.py`
     - `test_bloque_50_1.py`
     - `test_bloque_58_10.py`
     - `test_bloque_58_46.py`
     - `test_bloque_58_57.py`
     - `test_gameplay_runtime.py::test_boss_phase_change_spawns_burst` (ya arreglado en este BLOQUE)
     - `test_parallax_tile_mode.py`
     - `test_paths.py`
     - `test_tile_manager.py`
3. Agregar remote: `git remote add origin https://github.com/lerius700-cmyk/Void-Hunter.git`.
4. Verificar rama (ya está en `master`, OK).
5. `git push -u origin master` desde los commits ya hechos.

### C. Polish (leve — por la brecha documentada)

**Decisión**: skipped en gran parte. El polish NO llegaría al binario v1.4.0 sin rebuildear, que NO hacemos. Pero sí hacemos:

| Acción | Por qué |
|---|---|
| Smoke test del source actual (`python main.py --boss-test --duration 5`) | Confirmar que el working tree commiteable arranca sin errores. Si esto falla, abortar el push. |
| Listar los tests que pasan para boss/goliath/shield/javelin (filtrando los pre-existentes fallando) | Dejar claro qué suite estaba limpia al momento del primer push |
| Documentar en `KNOWN_ISSUES.md` qué se quedó sin cubrir | Transparencia |

**NO hacer en C**: regen AI de frames, fix de `test_asteroid_sprites` (path hardcodedo), cambios visuales no relacionados.

### D. Release del v1.4.0 ya construido

**Output**: `VoidHunter-v1.4.0-win64.zip` (397 MB) subido como primera release oficial en GitHub.

Acciones:
1. Verificar que `dist/VoidHunter-v1.4.0-win64.zip` existe y tiene tamaño > 100 MB (sanity check).
2. Crear `tools/release_notes_draft.md` con bullets que el usuario redacta:
   ```
   # VOID HUNTER v1.4.0 — release notes
   ## Highlights
   - ...
   ## Known limitations
   - Source at https://github.com/lerius700-cmyk/Void-Hunter is at BLOQUE 66.6, lagging behind this binary at BLOQUE 71. See KNOWN_ISSUES.md.
   ```
3. Tag local + push: `git tag v1.4.0 --no-sign` + `git push --tags`.
4. `gh release create v1.4.0 ./dist/VoidHunter-v1.4.0-win64.zip --title "VOID HUNTER v1.4.0 — BLOQUE 71" --notes-file tools/release_notes_draft.md --generate-notes`.
5. Verificar: `gh release list` muestra `v1.4.0` con el zip adjunto.
6. Compartir la URL del release (`https://github.com/lerius700-cmyk/Void-Hunter/releases/tag/v1.4.0`).

## Riesgos conocidos

1. **`gh` CLI no instalado**: usuario debe correr `winget install --id GitHub.cli`. Si falla, fallback MSI link.
2. **Token expirado o con scopes insuficientes**: el PAT necesita `repo` (commits + releases). Documentado en OPERATIONS.md.
3. **Tests pre-existentes fallando**: NO se arreglan en este push. Se documentan en `KNOWN_ISSUES.md`.
4. **Source ↔ binary gap**: el push inicial tendrá un source viejo. NO es bug del primer push (es honest disclosure), pero conviene resolverlo en próxima sesión.
5. **Tag previa `v1.4.0`**: si GitHub ya tiene un tag `v1.4.0` (porque alguna vez se subió un release), `git push --tags` falla con "tag already exists". Verificar antes con `git ls-remote --tags origin` o equivalente `gh`.

## Out of scope (explícito)

- Regen AI de frames GOLIATH.
- Refactor de gameplay/sistemas.
- Cambios visuales no relacionados al GOLIATH polish.
- Actualización de dependencias (requirements.txt).
- Publicar en otros canales (itch.io, Steam, etc.).
- Resolver la brecha source ↔ binary (será próxima sesión).

## Salida final esperada

- Repo `https://github.com/lerius700-cmyk/Void-Hunter` con código al día del BLOQUE 66.6 (óvalo revertido + test fix).
- `git log` reciente muestra los 3 commits: spec doc + cleanup + oval revert.
- Release `https://github.com/lerius700-cmyk/Void-Hunter/releases/tag/v1.4.0` con el `.zip` adjunto (397 MB).
- `docs/OPERATIONS.md` con guía completa de token + `gh`.
- `docs/KNOWN_ISSUES.md` con la brecha source↔binary y los tests pre-existentes listados.
- `tools/release_notes_draft.md` que el usuario redacta en prosa final.
