# HANDOFF — Seguridad: la AccessKey de Aliyun que quedó publicada (2026-11-08)

**Rama:** `bloquec-67-goliath-port` · **Alcance:** la exposición de una credencial de Aliyun en el historial de git, y la postura de seguridad del repo tras la revisión `gstack-review` de BLOQUE 75.

---

## 1. El incidente, en una línea

Una **AccessKey ID de Aliyun** quedó escrita dentro de un archivo commiteado, y por lo tanto **publicada** (el repo es público) en el historial de git. La mitad secreta **nunca** estuvo en el repo, y las URLs prefirmadas que la usaban **vencieron hace meses**; lo que queda por hacer es **rotar la clave** para que la exposición sea inerte por completo.

---

## 2. Los hechos, verificados

| Dato | Valor | Cómo se verificó |
|---|---|---|
| Qué se filtró | El **AccessKey ID** (el identificador de la pareja), **no** el Secret | `git grep` de `LTAI5t9d…fiFZ` y de `AccessKeySecret`: 0 hits del secret |
| Dónde | `tools/tiles/ai_gen/_batch_args.json`, en **4 URLs prefirmadas** de OSS | El commit `7d315aa` (2026-10-23, BLOQUE 67) |
| Qué URL | `https://matrix-internal.oss-us-east-1.aliyuncs.com/user_file_upload_tmp%2F…` — bucket `user_file_upload_tmp`, firma `OSS4-HMAC-SHA256` | `git show 7d315aa:tools/tiles/ai_gen/_batch_args.json` |
| firmadas | `x-oss-date=20260909T043400Z`, `x-oss-expires=3600` → vencidas el **2026-09-09T05:34Z** | La propia URL |
| ¿Viven? | **No.** Un `HEAD` a la URL devuelve **HTTP 403 Forbidden** | Verificado contra el endpoint |
| ¿El secret está? | **No.** 0 coincidencias en todo el repo | `git grep` |
| ¿La clave sigue viva en la cuenta? | **No se puede saber desde acá** — eso lo ves vos en la consola de RAM | Sin CLI ni credenciales en esta máquina |

**Por qué igual hay que rotarla**, aunque hoy no sea explotable:

1. El **ID** es la mitad del par y ya es público. Si el *secret* de esa misma clave apareciera alguna vez en otro lado (un log, un `.env` compartido, un backup), el atacante ya no tiene que adivinar a qué clave corresponde: el ID publicado se lo dice.
2. La clave puede seguir **activa** en la cuenta de Aliyun. Publicar su ID es publicar el blanco de un ataque de fuerza bruta sobre el secret — y el secret de una AccessKey de Aliyun tiene permisos de API completos sobre lo que esa cuenta pueda hacer.
3. Las URLs prefirmadas vencen solas; **una AccessKey no**. La URL era la parte disposable de la credencial, y sin embargo era la que se filtró.

---

## 3. Lo que YA se hizo en el repo

- [x] **Las URLs salieron del archivo commiteado** (commit `f4680a1`). El archivo conserva los *prompts* —que son la parte reproducible— y las URLs quedan como un marcador explícito.
- [x] **La regla de `.gitignore`** (`tools/tiles/ai_gen/_batch_args.local.json`): la URL de una corrida nueva va en un archivo local que no se versiona.
- [x] **El ID fue redactado de la documentación** (este handoff y el de la revisión), así que el árbol ya no lleva el literal: un escaneo futuro del árbol no da positivo falso.
- [x] **Verificado que el Secret nunca estuvo en el repo.**

---

## 4. LO QUE FALTA: rotar la clave (acción tuya)

**No puedo hacerlo desde acá.** En esta máquina no hay CLI de Aliyun, ni credenciales en el entorno, ni configuración de RAM (`aliyun` no está en el PATH; `ALIBABA_CLOUD_ACCESS_KEY_ID`, `ALICLOUD_ACCESS_KEY` y compañía están ausentes; no existe `~/.aliyun/config.json`). La rotación es una operación de la **consola de tu cuenta**, y la consola es tuya.

### Runbook (5 pasos, ~2 minutos)

1. **Abrir** la consola de RAM: `https://ram.console.aliyun.com/manage/ak` (o *AccessKey Management*).
2. **Localizar** el AccessKey cuyo ID empieza por `LTAI5t9d` y termina en `fiFZ`. Para recuperar el ID completo desde el repo:
   ```powershell
   git show 7d315aa:tools/tiles/ai_gen/_batch_args.json | Select-String 'LTAI5t9d'
   ```
3. **DESACTIVARLO** (Status → *Disable*). Desactivar alcanza y es reversible; borrar la clave es opcional y no aporta nada extra frente a dejarla desactivada.
4. **Si hace falta una clave**, creá una nueva (*Create AccessKey*) y guardala **sólo** en `tools/tiles/ai_gen/_batch_args.local.json` (ya está en `.gitignore`) o en un gestor de secretos. **Nunca** en un archivo versionado.
5. **Anotar la fecha** en la sección 6 de este handoff, para que el próximo agente sepa que está cerrada.

> **Verificación:** las URLs prefirmadas ya están muertas (403), así que la prueba práctica de que la rotación funcionó es que la consola muestre el estado *Disabled*. No hace falta (ni se puede) probar autenticación con la clave nueva desde el repo: la clave no se usa para nada del juego.

---

## 5. Lo que NO hay que hacer: reescribir el historial

La alternativa "correcta" en apariencia es reescribir el historial con `git filter-repo` para sacar el ID de `7d315aa`. **En este repo no compensa**, y por tres razones concretas:

1. **El tag de la release.** `v1.9.0` apunta a `157af82`, que es descendiente de `7d315aa`. Reescribir la historia reescribe ese commit: el tag hay que recrearlo y repushearlo, y **el tag publicado cambiaría debajo de quien ya descargó la release**.
2. **El repo es compartido.** Hay otro agente trabajando sobre este mismo repo. Un force-push reescribe la historia para todos y rompe cualquier trabajo en vuelo. La regla del proyecto lo dice: nunca push forzado.
3. **El beneficio es ruido, no seguridad.** Una vez rotada la clave, el ID publicado es una cadena inerte. La reescritura sólo reduce el ruido de un escaneo; no agrega nada de seguridad.

Si algún día se decide hacerlo igual, es un BLOQUE aparte, sobre un **espejo**, con el tag recreado y la release re-taggeada. Los comandos (NO ejecutados, y no recomendados en esta línea):

```powershell
git clone --mirror https://github.com/lerius700-cmyk/Void-Hunter.git vh-mirror.git
cd vh-mirror.git
git filter-repo --path tools/tiles/ai_gen/_batch_args.json --invert-paths   # quita el archivo entero
# o, quirúrgico, con --replace-text: un archivo replacements.txt con una línea
#   <AccessKeyID>==>***REMOVED***
# (el ID se recupera del historial, como en §4; este doc no lo lleva escrito)
git filter-repo --replace-text replacements.txt
# después: recrear el tag v1.9.0 sobre el commit reescrito y re-pushear con --force
```

---

## 6. Estado de la rotación

| Fecha | Quién | Qué |
|---|---|---|
| 2026-11-08 | sesión | Expuesta en el árbol y **sacada** (`f4680a1`); runbook escrito; ID redactado de la documentación |
| — | **PENDIENTE** | **Rotar en la consola de RAM** (§4) y anotar acá la fecha |

---

## 7. La postura de seguridad del repo, tras la revisión

Los 8 hallazgos del especialista de seguridad de la revisión `gstack-review` (diff `d70b8da..61c08d9`), con su estado real:

| # | Hallazgo | Severidad | Estado |
|---|---|---|---|
| 1 | El CI corría código de la rama con el `GITHUB_TOKEN` persistido en `.git/config` y sin `permissions:` | INFO | **CORREGIDO** (`f4680a1`): `permissions: contents: read` + `persist-credentials: false` en los dos checkouts |
| 2 | Las actions no están pineadas por SHA (`@v4`, `@v5` se mueven) | INFO | **ABIERTO** → plan, tanda D |
| 3 | Las dependencias no están pineadas (`pillow>=10.0` es la nueva) | INFO | **ABIERTO** → plan, tanda D |
| 4 | AccessKey ID de Aliyun en el historial | INFO | **PARCIAL**: fuera del árbol; falta la rotación (§4) |
| 5 | `clip.dir` del manifest se concatenaba a la ruta sin sanear: un `dir = "../../.."` sacaba la lectura **y la escritura** de los frames fuera del set | INFO | **CORREGIDO** (`f4680a1`): `_validate_clip_dir()` en `src/anim/manifest.py` |
| 6 | `VH_WT` decide dónde escribe `regen_status.py`: un runner con esa variable reescribe el `CLAUDE.md` de otro árbol | INFO | **ABIERTO** (override documentado y explícito) → plan, tanda D |
| 7 | `loc()` y `pyfiles()` interpolaban el folder en el código de Python y en un `-Command` de PowerShell | INFO | **CORREGIDO** (`f4680a1`): ahora viaja como argumento |
| 8 | La cache del lowpass confía en el **nombre** del archivo, sin validar el contenido, y su clave no incluye la identidad del track original: una actualización del juego en la misma carpeta reutiliza un WAV obsoleto | INFO | **ABIERTO** → plan, tanda D |

**Verificado y sin riesgo** (no son hallazgos, pero conviene saberlo): `shell=True` no existe en el repo · `os.system` no existe · no hay `pickle`/`marshal`/`yaml` · los `eval/exec` son `path.eval(t)` del módulo de curvas de Bézier (método propio, no builtin) · los manifest y anchors se parsean con `tomllib` (stdlib, sin ejecución de código) · `sets.py` ya valida el nombre del set (rechaza `..`, `/`, `\`) · el junit XML del gate se escribe fuera del repo (L7) · `_vh_cache` se crea junto al ejecutable y está ignorado.

---

## 8. La regla para que no vuelva a pasar

> **Una credencial no se versiona. Nunca. Ni siquiera "una URL prefirmada que ya venció".**

En la práctica, para este repo:

- El archivo versionado guarda **lo reproducible** (los prompts, la forma del argumento, el nombre del set).
- Lo **irrepetible y sensible** (la URL prefirmada, un token, un ID de clave) va en un archivo local ignorado por git: `_batch_args.local.json` ya tiene la regla en `.gitignore`.
- Un escaneo de **una sola vez** antes de commitear:
  ```powershell
  git grep -nE 'LTAI|x-oss-credential|AccessKeySecret|AKIA|gh[pousr]_[A-Za-z0-9]{20,}' -- . ':!*.md'
  ```
  Si sale algo, eso no se commitea.
- Y antes de cerrar un BLOQUE que haya tocado credenciales: `git log --all -S '<el identificador>'` — el historial es donde se filtran las cosas, no el árbol.

**Secret scanning de GitHub:** en este repo la herramienta `list_secret_scanning_alerts` **falla** (la feature no está habilitada para esta cuenta/repo), así que **no hay ninguna red de seguridad automática**: el control es el escaneo manual de arriba.
