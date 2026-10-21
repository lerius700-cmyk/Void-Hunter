# OPERATIONS — `gh` CLI, Personal Access Token (PAT) y flujo de release

**BLOQUE:** 67
**Fecha:** 2026-10-21
**Estado:** vivo

Guía operativa para que cualquier persona (o agente) pueda preparar una
máquina Windows nueva, autenticarse contra GitHub vía `gh` CLI, y ejecutar
el ciclo diario de desarrollo + release de Void Hunter.

No es un tutorial de Git. Es un *runbook*: los comandos exactos que se
ejecutan, en el orden correcto, con los paths concretos de este repo.

---

## §1 — Instalar `gh` CLI

`gh` es la CLI oficial de GitHub (https://cli.github.com). No es
obligatoria para contribuir, pero simplifica autenticación y creación de
releases desde PowerShell sin tipear tokens a mano en cada push.

### 1.1 Recomendado: winget

PowerShell normal (no hace falta admin):

```powershell
winget install --id GitHub.cli
```

Requiere **App Installer** (Win11 por defecto, Win10 reciente). Si el
comando no existe, usar el fallback MSI (§1.2).

### 1.2 Fallback: MSI manual

1. Ir a `https://github.com/cli/cli/releases/latest`.
2. Descargar `gh_*_windows_amd64.msi` (asset amd64, **no** arm64).
3. Doble-click → Next → Next → Finish.
4. **Abrir una ventana de PowerShell nueva** (la sesión actual no ve el
   PATH actualizado; `refreshenv` también sirve si usas
   Chocolatey/scoop).

### 1.3 Verificar

```powershell
gh --version
```

Salida esperada:

```
gh version 2.x.x (yyyy-mm-dd)
```

---

## §2 — Crear un Personal Access Token (PAT) en github.com

El token reemplaza la contraseña al autenticarse por HTTPS. Es personal,
secreto, y nunca debe commitearse al repo.

1. Ir a `https://github.com/settings/tokens`.
2. Click **Generate new token** → **Generate new token (classic)**
   (los *fine-grained tokens* también sirven, pero los classic son los
   más simples para este flujo).
3. **Note:** nombre libre, sugerencia
   `Mavis push bot — <nombre-de-tu-PC>`.
4. **Expiration:** 90 días. Es la ventana recomendada por NIST para
   tokens personales. GitHub avisa por email antes del vencimiento.
5. **Scopes:** tildar **solo** `repo` (*Full control of private
   repositories*). Si vas a tocar GitHub Actions desde la CLI, sumar
   `workflow`.
6. Click **Generate token**.
7. **Copiar el token** inmediatamente. Es la **única** vez que se ve
   completo. Si se pierde, hay que regenerarlo.
8. Guardar el token en un cofre personal (1Password / Bitwarden /
   KeePass). **Nunca** pegarlo en chat, en un issue, ni en un archivo
   dentro del repo.

---

## §3 — Login local con `gh`

Patrón: el token vive en un archivo **fuera** del repo y se le pasa a
`gh` por stdin. `gh` lo cachea en su store seguro y el archivo se borra.

```powershell
# Guardar a archivo FUERA del repo (cualquier directorio user-only sirve)
$token | Out-File -FilePath "$env:USERPROFILE\.github_token" -Encoding UTF8 -NoNewline

# Login (el token pasa a gh sin quedar en pantalla ni en historial)
Get-Content "$env:USERPROFILE\.github_token" -Raw | gh auth login --with-token

# Borrar el archivo (el token ya está en el store seguro de gh)
Remove-Item "$env:USERPROFILE\.github_token"
```

Verificar:

```powershell
gh auth status
```

Salida esperada:

```
You are logged in to github.com as <tu-usuario>
Token scopes: repo
```

Si `Token scopes` está vacío o dice algo distinto a `repo`, repetir §2
con los scopes correctos.

---

## §4 — Regenerar el token

GitHub manda un email *Token expired* cuando vence (cada 90 días).
También se puede rotar proactivamente antes del límite.

1. Repetir §2 (generar token nuevo desde el panel).
2. Repetir §3 (re-login local con el token nuevo).
3. **No hace falta tocar nada en el repo.** `gh` reemplaza el token
   cacheado de forma transparente; el remoto (`origin`) sigue siendo la
   misma URL HTTPS.

Si el token viejo se filtró accidentalmente: regenerar **inmediato**
(antes del email de aviso), y revisar el audit log de GitHub por
actividad sospechosa (`Settings → Audit log`).

---

## §5 — Flujo diario

### 5.1 Clonar en otra máquina

```powershell
git clone https://github.com/lerius700-cmyk/Void-Hunter
cd Void-Hunter
pip install -r requirements-dev.txt  # no es obligatorio para runtime
```

### 5.2 Commit + push

```powershell
git add .
git commit -m "descripción del cambio"
git push origin master
```

Convención de mensajes (ver `CLAUDE.md`):

- `feat: BLOQUE N` — feature nueva
- `fix: BLOQUE N` — bugfix
- `chore: BLOQUE N` — housekeeping
- `docs: ...` — solo docs (ej. este commit)

### 5.3 Crear un release

```powershell
# 1. Build del ejecutable
pyinstaller build.spec --clean

# 2. Empaquetar
Compress-Archive -Path dist/void-hunter/* -DestinationPath VoidHunter-vX.Y.Z-win64.zip

# 3. Tag + push
git tag vX.Y.Z
git push --tags

# 4. Release en GitHub (gh toma el zip + notas)
gh release create vX.Y.Z ./VoidHunter-vX.Y.Z-win64.zip `
    --title "Void Hunter vX.Y.Z" `
    --notes-file release-notes.md
```

`release-notes.md` se redacta desde `tools/release_notes_draft.md`
(generado en BLOQUE 67 D2). El `.exe` queda en `dist/void-hunter/`
después del build.

---

## §6 — Troubleshooting

| Síntoma | Causa probable | Fix |
|---|---|---|
| `gh: command not found` justo después de instalar | PATH de la sesión actual no se refrescó | Abrir **nueva** ventana de PowerShell, o correr `refreshenv` |
| `Bad credentials` en `gh auth status` | Token expirado o revocado | Regenerar (§4) y re-login (§3) |
| `Permission denied` al `git push` | PAT sin scope `repo` | Regenerar (§2) tildando `repo` |
| `remote: Repository not found` | Repo privado y el user no es collaborator | Pedir acceso al owner (`lerius700-cmyk`) |
| `git push` pide username/password | Creds viejos en cache | Borrar: `git credential-manager erase https://github.com` (luego `gh` toma el control) |
| `gh auth login --with-token` rechaza el token | Archivo con BOM o CRLF extra | Re-grabar con `-Encoding UTF8 -NoNewline`, sin CRLF de Windows heredado |
| `error: failed to push` con mensaje `403` | Rate limit o scope insuficiente | Esperar unos minutos o regenerar token con `repo` |

Si nada funciona, diagnóstico rápido:

```powershell
gh auth status          # ¿está autenticado?
gh config get -h github.com  # ¿qué protocolo está usando?
git remote -v           # ¿el remote apunta al repo correcto?
```

---

## Referencias internas

- `CLAUDE.md` — identidad del proyecto + reglas globales.
- `docs/CHANGELOG.md` — historial de BLOQUEs.
- `docs/architecture/` — arquitectura + roadmap.
- `build.spec` — spec de PyInstaller para el `.exe`.
