# Registro de cambios / Changelog

Todos los cambios importantes de **Gestor de BIOS y UEFI**.
Lo más reciente, arriba. En español primero y en inglés después.

*All notable changes to **BIOS / UEFI Manager**. Newest on top. Spanish first, English below.*

---

## 1.9 — 2026-09-13

### Español

- Preservación estricta de separadores de fecha según el fabricante: el editor respeta si el equipo utiliza barras (`/`) o guiones (`-`), eliminando falsas detecciones de modificaciones no deseadas al navegar por la lista y garantizando que el firmware acepte el formato exacto al guardar.
- Validación cronológica y de calendario completa: cálculo riguroso de años bisiestos según la regla gregoriana completa (`año % 4 == 0 y (año % 100 != 0 o año % 400 == 0)`), verificación de días según el mes (28, 29, 30 o 31 días) y límites estrictos de años válidos al escribir manualmente con el teclado.
- Soporte para parámetros numéricos con signo y valores negativos: configuración de `wx.SpinCtrl` con rango completo de enteros de 32 bits con signo (`-2147483648` a `2147483647`), permitiendo editar parámetros con valores negativos o códigos numéricos automáticos del fabricante.
- Blindaje del ciclo de vida de la interfaz gráfica contra `PyDeadObjectError`: comprobación de validez de controles en callbacks asíncronos y eventos de interfaz antes de manipular elementos visuales tras el cierre del diálogo.
- Protección y veto de cierre de ventana (`wx.EVT_CLOSE`) durante escrituras elevadas sincrónicas: se bloquea el cierre accidental o por escape mientras se ejecutan llamadas WMI (`SetBiosSetting`) para evitar corrupción en el firmware de la placa base o cierres abruptos de la aplicación.
- Reconocimiento y validación de formatos de hora: soporte para horas en formato `HH:MM` y `HH:MM:SS` con verificación estricta de límites (0-23 para horas, 0-59 para minutos y segundos).
- Filtrado dinámico en tiempo real y carga automática de editores: el campo de búsqueda filtra al instante tanto por nombre del ajuste como por su valor actual, instanciando automáticamente el editor correspondiente al enfocar o seleccionar cada elemento en la lista.
- Ejecución robusta del reinicio al firmware UEFI: llamada a `shutdown.exe /r /fw /t 2` con verificación de permisos de administrador y mensaje explícito de error en caso de que la placa base o el sistema no admitan reinicio a UEFI desde el sistema operativo.
- Limpieza de archivos temporales huérfanos: el instalador y desinstalador en `installTasks.py` eliminan cualquier rastro residual de archivos temporales `nvda_bios_*` en el directorio de temporales del sistema.

### English

- Strict preservation of vendor-specific date separators: date editor respects whether the machine utilizes slashes (`/`) or hyphens (`-`), eliminating false dirty flags when navigating the list and ensuring firmware accepts the exact formatted string upon saving.
- Comprehensive calendar and leap year validation: strict leap year calculation adhering to the Gregorian rule (`year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)`), exact month length bounds checking (28, 29, 30, or 31 days), and strict year range clamping when typing manually.
- Signed integer and negative value support: `wx.SpinCtrl` initialized with full 32-bit signed integer boundaries (`-2147483648` to `2147483647`), allowing proper adjustment of settings using negative numbers or vendor-specific negative automatic codes.
- UI lifecycle hardening against `PyDeadObjectError`: defensive checks on wxPython widget handles within asynchronous callbacks and UI events, preventing unhandled exceptions if windows are closed during background operations.
- Vetoed window destruction during synchronous elevated writes: closing via Escape or the close box (`wx.EVT_CLOSE`) is safely vetoed while active WMI `SetBiosSetting` operations write to the motherboard, safeguarding against firmware corruption.
- Time format recognition and boundary validation: robust parsing for `HH:MM` and `HH:MM:SS` time strings with explicit boundary constraints (0-23 for hours, 0-59 for minutes and seconds).
- Dynamic real-time search filtering and automatic editor binding: search input dynamically filters by both setting name and current value, automatically loading and binding the matching editor widget upon focus or selection.
- Robust UEFI reboot execution: invoking `shutdown.exe /r /fw /t 2` with elevated privilege validation and clear explanatory feedback if the hardware does not support OS-initiated UEFI boot.
- Orphaned temporary file cleanup: `installTasks.py` installation and uninstallation hooks clean up any orphaned `nvda_bios_*` temporary files from the system temporary directory.

---

## 1.9.1 — 2026-09-13

### Español

Mantenimiento y documentación interna del código. Sin cambios en el comportamiento del complemento.

Se completó la cobertura de documentación técnica en `wmi_backend.py` y `dialog.py`, añadiendo descripciones a todos los métodos que carecían de ellas para facilitar el mantenimiento futuro. Se eliminó también una importación de `os` en el módulo principal que el código no utilizaba.

### English

Internal code documentation and maintenance. No behavioral changes.

Completed technical docstring coverage across `wmi_backend.py` and `dialog.py`, documenting all previously undescribed methods to aid future maintenance. Also removed an unused `os` import from the main module.

---

## 1.7 — 2026-09-12

### Español

#### Mejorado

- Integración con el sistema oficial de registro de NVDA (`logHandler.log`), permitiendo que cualquier advertencia o fallo técnico quede reflejado limpiamente en el visor de registro de NVDA.
- Al desactivar o recargar complementos, los elementos del menú en Herramientas se destruyen adecuadamente liberando recursos de la interfaz.
- La opción de menú para abrir la documentación detecta automáticamente el idioma de NVDA y abre la versión correspondiente en español o inglés.
- La ventana de ajustes incorpora identificadores estándar de wxWidgets para aceptar y cancelar, permitiendo cerrar con Escape o confirmar con Intro de forma nativa.

### English

#### Improved

- Switched to NVDA's native logging framework (`logHandler.log`) so diagnostic and warning messages integrate seamlessly with NVDA's Log Viewer.
- Clean teardown of Tools menu items on addon termination/reload, preventing orphaned UI handles.
- The documentation menu entry now opens the guide in the user's active NVDA language (Spanish or English).
- The settings dialog now implements standard affirmative and escape IDs (`wx.ID_OK`, `wx.ID_CANCEL`) for native Enter/Escape keyboard navigation.

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
