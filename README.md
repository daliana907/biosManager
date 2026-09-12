# Gestor de BIOS y UEFI para NVDA (BIOS / UEFI Manager)

[![Pruebas](https://github.com/daliana907/biosManager/actions/workflows/pruebas.yml/badge.svg)](https://github.com/daliana907/biosManager/actions/workflows/pruebas.yml)

Autora: Daliana
Versión: 1.8
Compatibilidad: NVDA 2023.1 en adelante
Licencia: GNU GPL v2

[Read in English below](#english-version)

[Descargar última versión / Download latest (.nvda-addon)](https://github.com/daliana907/biosManager/releases/latest/download/biosManager-1.8.nvda-addon) · [Registro de cambios](CHANGELOG.md)

---

## Versión en Español

Este complemento permite consultar y modificar la configuración del firmware UEFI de tu ordenador directamente desde el escritorio de Windows con NVDA, de forma totalmente accesible.

### ¿Para qué sirve?
Normalmente, para cambiar algo en la configuración del firmware (como el orden de arranque para arrancar desde una unidad USB o activar la virtualización) hay que reiniciar la computadora y pulsar teclas a ciegas en una pantalla visual que no tiene sonido ni lector de pantalla.

Con este complemento no necesitas ayuda visual: abres la ventana dentro de Windows, buscas la opción que quieras con el teclado, haces el cambio y al reiniciar el ordenador la placa base ya tendrá tu configuración guardada.

### BIOS heredada frente a UEFI
Es importante distinguir entre la BIOS clásica y el firmware UEFI moderno:
- La BIOS heredada (Legacy BIOS) no se puede controlar ni modificar desde el sistema operativo una vez iniciado.
- El firmware UEFI moderno sí permite la comunicación y lectura/escritura de variables de configuración mediante la interfaz WMI de Windows.
- Por tanto, este complemento funciona exclusivamente en sistemas con firmware UEFI nativo. No funcionará en equipos antiguos con BIOS clásica ni en equipos donde se haya activado el módulo de compatibilidad heredada (CSM).

### Compatibilidad de computadoras
Por la forma en que funciona la comunicación con la placa base en Windows:
- Funciona en: Equipos Lenovo de gama profesional (portátiles ThinkPad, computadoras de escritorio ThinkCentre y estaciones de trabajo ThinkStation).
- No funciona en: Equipos armados por piezas (clónicos) o computadoras portátiles domésticas que no traen el sistema de comunicación WMI del fabricante. Si lo abres en un equipo no compatible, te avisará de forma clara y segura.

### Advertencias de seguridad y uso responsable
Modificar los parámetros del firmware del equipo es una operación delicada:
- **Orden de arranque:** Desactivar o alterar el orden de las unidades de arranque puede impedir que Windows inicie normalmente.
- **Seguridad y virtualización:** Modificar parámetros como Secure Boot, TPM, contraseñas de arranque o virtualización (VT-x / AMD-V) puede afectar al cifrado de unidad (como BitLocker) o a la integridad del arranque del sistema. Modifica únicamente los parámetros que conozcas.
- **Protección en pantallas seguras:** Por razones de seguridad, el complemento bloquea automáticamente su carga en pantallas seguras de Windows (como la pantalla de bloqueo o el Control de cuentas de usuario) para evitar accesos no autorizados con privilegios elevados.

### Opciones y atajos de teclado
El complemento no asigna ningún atajo de teclado por defecto para no interferir con las órdenes nativas de NVDA (por ejemplo, el atajo nativo `NVDA + Shift + B` para verbalizar el estado de la batería).

Todas las acciones se encuentran disponibles desde el menú de NVDA y pueden personalizarse con los atajos que desees:
- **Menú NVDA > Herramientas > Gestor de BIOS y UEFI:**
  - *Configuración de la BIOS / UEFI...:* Abre la ventana principal de ajustes.
  - *Reiniciar en la configuración de UEFI / BIOS...:* Reinicia el sistema directamente en la pantalla de configuración del firmware UEFI.
  - *Comprobar conflictos con otros complementos...:* Comprueba si existen atajos coincidentes o complementos duplicados.
  - *Documentación:* Abre esta guía de ayuda.
- **Asignación de atajos:** Puedes asignar tus propios atajos de teclado en el menú de NVDA > Preferencias > Gestos de entrada, dentro de la categoría "Gestor de BIOS y UEFI".
- **Dentro de la ventana de ajustes:**
  - *Búsqueda:* Escribe el término y pulsa `Intro` o el botón *Filtrar* para actualizar la lista. Pulsa *Limpiar* para restablecerla.
  - *Orden de arranque:* Selecciona un dispositivo de la lista y utiliza `Alt + Flecha Arriba` o `Alt + Flecha Abajo` (o los botones *Subir* y *Bajar*) para cambiar su posición.
  - *Confirmar y cancelar:* Pulsa `Aceptar` (o Intro fuera de campos de texto) para aplicar los cambios pendientes en la BIOS, o `Cancelar` (o Escape) para descartar los cambios en memoria y cerrar.

---

## English Version

This add-on allows blind and visually impaired users to check and change UEFI firmware settings directly from Windows using NVDA.

### Why this add-on exists
Traditional firmware setup screens load before Windows starts. They are purely visual and lack speech support, making them inaccessible without sighted help. This add-on brings those settings into an accessible Windows dialog where NVDA can read and configure them smoothly.

### Legacy BIOS vs. UEFI
Legacy BIOS cannot be configured or controlled from the operating system once booted. Modern UEFI firmware allows communication and configuration through the Windows WMI interface. Therefore, this add-on works exclusively on systems running modern UEFI firmware and will not work on legacy BIOS machines or when Compatibility Support Module (CSM) legacy emulation is enabled.

### Supported Computers
- Supported: Lenovo business line computers (ThinkPad laptops, ThinkCentre desktops, ThinkStation workstations) with Lenovo WMI support.
- Not supported: Custom-built desktop PCs and consumer laptops without vendor WMI firmware support. If run on an unsupported system, the add-on will notify you safely.

### Security and Responsible Use
Firmware configuration controls low-level hardware behavior:
- **Boot order:** Modifying boot devices or their order can prevent Windows from starting.
- **Security & Virtualization:** Altering options such as Secure Boot, TPM, passwords, or CPU virtualization (VT-x / AMD-V) may affect drive encryption (e.g., BitLocker) or virtual machines. Only modify settings you understand.
- **Secure mode enforcement:** The add-on blocks execution on secure screens (e.g. UAC dialogs or lock screen) to prevent unauthorized high-privilege operations.

### Commands and Shortcuts
To prevent conflicts with native NVDA commands (such as `NVDA + Shift + B` for battery status), this add-on does not assign any default keyboard shortcut.

All features are accessible from the NVDA menu and can be assigned custom shortcuts:
- **NVDA Menu > Tools > BIOS and UEFI Manager:**
  - *BIOS / UEFI Settings...:* Opens the configuration dialog.
  - *Reboot to UEFI / BIOS settings...:* Reboots the machine directly into UEFI firmware setup.
  - *Check conflicts with other add-ons...:* Checks for colliding shortcuts or duplicate firmware add-ons.
  - *Documentation:* Opens this help guide.
- **Custom gestures:** Assign your preferred shortcuts in NVDA Menu > Preferences > Input Gestures under the "BIOS and UEFI Manager" category.
- **Inside the settings dialog:**
  - *Search:* Type your search query and press `Enter` or click the *Filter* button.
  - *Boot order:* Select a device and press `Alt + Up Arrow` or `Alt + Down Arrow` (or click *Move up* / *Move down*) to adjust its position.
  - *Apply and Cancel:* Click *OK* (or press Enter) to write pending changes to UEFI, or *Cancel* (or Escape) to dismiss changes and close.
