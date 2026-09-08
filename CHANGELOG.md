# Registro de cambios / Changelog

Todos los cambios importantes de **Gestor de BIOS y UEFI**.
Lo más reciente, arriba. En español primero y en inglés después.

*All notable changes to **BIOS / UEFI Manager**. Newest on top. Spanish first, English below.*

---

## 1.6 — 2026-09-08

### Español

#### Corregido

- Los cambios en la BIOS no llegaban a aplicarse: la orden que se enviaba a Windows estaba mal formada.
- El archivo con la respuesta de la BIOS quedaba en una carpeta que NVDA no siempre podía leer, y la operación parecía fallar sin motivo.
- Al aplicar un cambio se daba por bueno sin comprobarlo. Ahora se vuelve a leer el valor y se informa de si la BIOS lo aceptó o lo rechazó.
- Guardar en la BIOS bloqueaba NVDA hasta terminar. Ahora se hace en segundo plano.
- Al cerrar la ventana con un cambio escrito pero sin aplicar, ese cambio se perdía en silencio. Ahora avisa.
- El orden de arranque se editaba con un desplegable por posición, y se podía repetir un dispositivo y omitir otro sin que nada lo advirtiera.
- Las consultas a la BIOS podían quedarse esperando indefinidamente si el equipo no respondía o si nadie contestaba al aviso de permisos.

#### Cambios internos

- El orden de arranque se edita ahora en una sola lista que se reordena con Alt y las flechas, y al aplicar se resume solo lo que cambió de sitio.
- El editor de opciones separa decidir qué tipo de editor toca de construirlo, y esa decisión tiene pruebas propias.
- Se eliminaron unas 119 líneas de código que ya no se usaba.
- Se corrigieron dos problemas de seguridad: un archivo temporal con nombre predecible y valores que se enviaban a Windows sin escapar.
- Se añadieron 52 comprobaciones automáticas que se ejecutan solas en GitHub con cada cambio.

### English

#### Fixed

- BIOS changes were never applied: the command sent to Windows was malformed.
- The file with the BIOS answer was left in a folder NVDA could not always read, and the operation appeared to fail for no reason.
- Applying a change was assumed to work without checking. The value is now read back and you are told whether the BIOS accepted or rejected it.
- Saving to the BIOS froze NVDA until it finished. It now runs in the background.
- Closing the window with a typed but unapplied change lost it silently. It now warns you.
- Boot order was edited with one dropdown per position, so a device could be repeated and another omitted with no warning.
- BIOS queries could wait forever if the machine did not answer or nobody responded to the permission prompt.

#### Internal changes

- Boot order is now edited in a single list reordered with Alt and the arrow keys, and only what actually moved is summarised on apply.
- The settings editor separates deciding which editor a value needs from building it, and that decision has its own tests.
- Removed about 119 lines of code that were no longer used.
- Fixed two security issues: a temporary file with a predictable name, and values sent to Windows without escaping.
- Added 52 automatic checks that run on their own on GitHub with every change.

---

## 1.5 y anteriores / 1.5 and earlier

El historial de estas versiones está en los mensajes de guardado del repositorio,
en la pestaña de confirmaciones de GitHub.

*The history of these versions lives in the repository commit messages, on the
GitHub commits tab.*
