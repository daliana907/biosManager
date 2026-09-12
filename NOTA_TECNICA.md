# Nota técnica para revisores — BIOS Manager

*Versión 1.7 · Complemento para NVDA · Autora: Daliana*

Este documento describe qué toca el complemento en el sistema, qué permisos
pide y por qué. Está pensado para quien revisa el código antes de instalarlo o
publicarlo.

---

## Alcance

BIOS Manager permite leer y modificar los ajustes de la BIOS/UEFI desde una
ventana accesible de NVDA, sin tener que entrar a la pantalla de configuración
del firmware, que no es accesible con lector de pantalla en la mayoría de los
equipos.

Funciona **únicamente en equipos Lenovo** (ThinkPad, ThinkCentre y familias
afines), porque usa la interfaz WMI que Lenovo publica para su BIOS. En
cualquier otro equipo el complemento lo detecta y lo dice, sin intentar nada.

## Interfaces del sistema que utiliza

Todo el acceso a la BIOS pasa por el espacio de nombres WMI `root\wmi`,
mediante PowerShell. Las clases utilizadas son las que Lenovo documenta:

| Clase WMI | Para qué |
|---|---|
| `Lenovo_BiosSetting` | Leer todos los ajustes actuales |
| `Lenovo_GetBiosSelections` | Leer los valores válidos de un ajuste |
| `Lenovo_SetBiosSetting` | Escribir un ajuste |
| `Lenovo_SaveBiosSettings` | Confirmar los cambios en el firmware |
| `Lenovo_DiscardBiosSettings` | Descartar los cambios pendientes |

Además usa un único comando estándar de Windows, `shutdown.exe /r /fw /t 2`,
para reiniciar directamente a la pantalla del firmware. Se ejecuta solo tras
una confirmación explícita de sí o no.

No usa ninguna DLL propia ni de terceros. No lee ni escribe en el registro de
Windows.

## Permisos elevados

**Sí, el complemento pide permisos de administrador**, y conviene explicar
exactamente cuándo y por qué.

Escribir en la BIOS es una operación privilegiada en cualquier sistema
operativo: no es una decisión de diseño de este complemento, es un requisito
del firmware. La lectura de los ajustes también se hace elevada porque la
interfaz de Lenovo devuelve la lista completa únicamente a un proceso con
privilegios.

El mecanismo es el siguiente:

1. Se crea una carpeta temporal nueva con `tempfile.mkdtemp(prefix="nvda_bios_")`.
2. Dentro se escribe el script de PowerShell a ejecutar.
3. Se escribe un segundo script, el lanzador, que arranca `powershell.exe` con
   `StartInfo.Verb = "runas"`. **Ese verbo es lo que provoca el aviso de UAC de
   Windows**, que la persona ve y acepta.
4. La salida se escribe en un archivo en la carpeta temporal general de Windows
   con un nombre distinto en cada ejecución.
5. La carpeta temporal se borra en un bloque `finally`, de modo que desaparece
   aunque el proceso falle o se cancele el permiso.

El complemento **nunca eleva por su cuenta**. La elevación ocurre siempre como
consecuencia directa de una acción de la usuaria: abrir la ventana de ajustes,
o pulsar Aceptar para guardar.

## Límites de espera

Desde la versión 1.6 todas las llamadas a procesos externos tienen un límite:

- **120 segundos** cuando hay un aviso de permisos de por medio. Es el tiempo
  que se le concede a la persona para aceptarlo.
- **30 segundos** para las consultas normales.

Antes de la 1.6 no había ninguno, y un aviso de UAC que nadie contestaba dejaba
la consulta esperando indefinidamente, con NVDA aparentemente colgado.

## Red

**Ninguna.** El complemento no abre ninguna conexión de red, no consulta ningún
servicio, no descarga ni envía nada. No hay claves de API, ni telemetría, ni
comprobación de actualizaciones.

## Almacenamiento

No crea ningún archivo de configuración propio. Los cambios pendientes existen
solo en memoria mientras la ventana está abierta; si se cierra con Cancelar,
desaparecen.

Los únicos archivos que escribe son los temporales descritos arriba, que se
borran solos.

## Diseño de seguridad

Los cambios **no se envían a la BIOS a medida que se hacen**. Se acumulan en una
lista de pendientes, se muestran en una columna aparte de la lista de ajustes, y
solo llegan al firmware cuando se pulsa Aceptar. Esto es deliberado: reduce el
riesgo de dejar la BIOS en un estado a medias.

El orden de arranque se valida antes de enviarlo: se rechaza si falta alguna
entrada o si alguna está repetida.

Desde la 1.6, si se cierra la ventana con Aceptar habiendo un valor escrito en
el editor pero sin haberlo añadido a los cambios pendientes, el complemento
avisa y no cierra. Antes ese cambio se descartaba en silencio.

## Hilos

Toda operación que puede tardar (leer la BIOS, guardar, descartar) se ejecuta en
un hilo `daemon` separado, para no bloquear el hilo principal de NVDA. La
interfaz se actualiza siempre desde el hilo principal.

## Pruebas automáticas

El complemento incluye 52 pruebas que se ejecutan en cada envío a GitHub. No
requieren un equipo Lenovo ni acceso real a la BIOS: usan un NVDA simulado.

---

# Technical note for reviewers — BIOS Manager

*Version 1.7 · NVDA add-on · Author: Daliana*

This document describes what the add-on touches on the system, what permissions
it requests and why. It is intended for anyone reviewing the code before
installing or publishing it.

## Scope

BIOS Manager lets the user read and change BIOS/UEFI settings from an accessible
NVDA dialog, without entering the firmware setup screen, which is not accessible
with a screen reader on most machines.

It works **only on Lenovo systems** (ThinkPad, ThinkCentre and related
families), because it uses the WMI BIOS interface Lenovo publishes. On any other
machine the add-on detects this and says so, without attempting anything.

## System interfaces used

All BIOS access goes through the `root\wmi` WMI namespace, via PowerShell. The
classes used are the ones Lenovo documents:

| WMI class | Purpose |
|---|---|
| `Lenovo_BiosSetting` | Read all current settings |
| `Lenovo_GetBiosSelections` | Read the valid values of one setting |
| `Lenovo_SetBiosSetting` | Write one setting |
| `Lenovo_SaveBiosSettings` | Commit changes to firmware |
| `Lenovo_DiscardBiosSettings` | Discard pending changes |

It also uses one standard Windows command, `shutdown.exe /r /fw /t 2`, to reboot
straight into the firmware screen. This runs only after an explicit yes/no
confirmation.

It uses no DLLs of its own or from third parties. It neither reads nor writes
the Windows registry.

## Elevated privileges

**Yes, the add-on requests administrator privileges**, and it is worth stating
exactly when and why.

Writing to the BIOS is a privileged operation on any operating system: this is
not a design decision of this add-on, it is a firmware requirement. Reading the
settings is also done elevated because Lenovo's interface returns the complete
list only to a privileged process.

The mechanism is:

1. A fresh temporary folder is created with `tempfile.mkdtemp(prefix="nvda_bios_")`.
2. The PowerShell script to run is written inside it.
3. A second script, the launcher, is written; it starts `powershell.exe` with
   `StartInfo.Verb = "runas"`. **That verb is what raises the Windows UAC
   prompt**, which the user sees and accepts.
4. Output is written to a file in the general Windows temp folder, under a
   different name on every run.
5. The temporary folder is removed in a `finally` block, so it disappears even
   if the process fails or the prompt is cancelled.

The add-on **never elevates on its own**. Elevation always follows directly from
a user action: opening the settings dialog, or pressing OK to save.

## Timeouts

Since version 1.6 every call to an external process is bounded:

- **120 seconds** when a permission prompt is involved. That is the time allowed
  for the person to accept it.
- **30 seconds** for ordinary queries.

Before 1.6 there were none, and an unanswered UAC prompt left the query waiting
indefinitely, with NVDA appearing to hang.

## Network

**None.** The add-on opens no network connection, queries no service, downloads
and sends nothing. There are no API keys, no telemetry, no update checks.

## Storage

It creates no configuration file of its own. Pending changes exist only in
memory while the dialog is open; closing with Cancel discards them.

The only files it writes are the temporary ones described above, which delete
themselves.

## Safety design

Changes are **not sent to the BIOS as they are made**. They accumulate in a
pending list, are shown in a separate column of the settings list, and reach the
firmware only when OK is pressed. This is deliberate: it reduces the risk of
leaving the BIOS half-configured.

Boot order is validated before being sent: it is rejected if any entry is
missing or duplicated.

Since 1.6, closing the dialog with OK while a value has been typed in the editor
but not added to pending changes produces a warning and does not close. That
change was previously discarded silently.

## Threads

Every operation that can take time (reading the BIOS, saving, discarding) runs
on a separate `daemon` thread, so NVDA's main thread is never blocked. The UI is
always updated from the main thread.

## Automated tests

The add-on ships with 52 tests that run on every push to GitHub. They require
neither a Lenovo machine nor real BIOS access: they use a simulated NVDA.
