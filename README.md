# BIOS / UEFI Manager for NVDA

* **Author:** Daliana
* **Version:** 1.5
* **Compatibility:** NVDA 2023.1 or later
* **License:** GNU General Public License v2.0 (GPLv2)
* **Repository:** [https://github.com/daliana907/biosManager](https://github.com/daliana907/biosManager)

[Versión en español más abajo](#versión-en-español)

---

## English

**BIOS / UEFI Manager** is an advanced accessibility add-on for the NVDA screen reader that enables blind and visually impaired users to inspect, search, and configure BIOS/UEFI firmware settings directly from within Windows.

### The Problem It Solves
Traditional BIOS and UEFI setup menus execute before the operating system boots and are purely visual environments without screen reader or speech output. For screen reader users, this creates a total barrier, forcing them to rely on sighted assistance or attempt blind keystroke sequences to modify essential hardware settings.

This add-on brings firmware configuration into the accessible Windows environment, allowing NVDA to read, search, and change settings with full speech and braille feedback.

### Hardware Compatibility
Querying and modifying firmware from the operating system requires manufacturer-specific WMI instrumentation:

* **Currently Supported:** **Lenovo** enterprise computers (**ThinkPad** laptops, **ThinkCentre** desktops, and **ThinkStation** workstations) equipped with Lenovo's official BIOS WMI provider.
* **Extensible Architecture:** The add-on is designed with a modular architecture. Support for additional enterprise vendors (such as Dell and HP) can be added via provider modules.
* **Unsupported Devices:** Generic consumer laptops or custom assembled desktop motherboards that do not expose WMI BIOS interfaces. On unsupported hardware, the add-on gracefully informs the user that no compatible BIOS provider was detected.

### Safety & Security
* **Hardware Safe:** All configuration changes are handled through official WMI APIs (`root\wmi`). Any invalid values are validated and rejected by the motherboard firmware itself, eliminating the risk of bricking or corrupting firmware.
* **Persistent across OS reinstallations:** Changes are saved directly to motherboard NVRAM (CMOS). Boot order or security preferences remain configured even after disk formatting or Windows reinstallation.
* **Controlled Privilege Elevation:** Reading settings runs seamlessly in the background. Windows User Account Control (UAC) is only invoked when the user explicitly clicks "OK" to apply queued modifications.

### How to Use
1. Open the NVDA Menu (`NVDA + N`) > **Tools** > **BIOS and UEFI Manager** > **BIOS / UEFI Settings...**.
2. A list on the left displays all available BIOS settings (up to 80+ parameters depending on model), with an instant search box to filter by name.
3. The right-hand panel dynamically adapts to the selected setting:
   * **Standard Settings (Enable/Disable):** Native combo box to select choices with arrow keys.
   * **Boot Device Order:** Dynamic cascading combo boxes for each boot slot (Boot Device 1, 2, 3, etc.).
   * **Text / Passwords / Dates:** Accessible text edit fields or numeric spin controls.
4. Click **Add to pending changes** to stage your changes.
5. Click **OK** to apply all staged changes at once. Accept the Windows UAC confirmation. Changes will take effect on next reboot.

### Third-Party APIs and Privacy
* No external internet connection or third-party web services are used.
* All queries run 100% locally via Windows Management Instrumentation (WMI).
* No user data or telemetry is collected.

---

## Versión en Español

**Gestor de BIOS y UEFI** es un complemento avanzado para el lector de pantalla NVDA que permite consultar, buscar y modificar la configuración de la BIOS/UEFI directamente desde Windows.

### El problema que resuelve
Los menús tradicionales de la BIOS y UEFI se ejecutan antes del arranque del sistema operativo y carecen de soporte para lectores de pantalla. Este complemento derriba esa barrera histórica, permitiendo a los usuarios con discapacidad visual gestionar la configuración del firmware de manera autónoma y accesible.

### Compatibilidad de hardware
* **Soporte actual:** Ordenadores **Lenovo** de gama profesional (**ThinkPad**, **ThinkCentre**, **ThinkStation**) que cuentan con el proveedor oficial WMI de Lenovo.
* **Diseño modular:** La arquitectura modular permite incorporar en el futuro soporte para otros fabricantes corporativos (como Dell y HP).
* **Seguridad total:** Las modificaciones se canalizan mediante interfaces oficiales del fabricante. Cualquier valor incorrecto es validado y rechazado por la propia placa base, protegiendo la integridad del firmware.

### Acceso al complemento
Desde el menú **NVDA ➔ Herramientas ➔ Gestor de BIOS y UEFI**:
* **Configuración de la BIOS / UEFI...**: Abre la interfaz para ver y modificar parámetros.
* **Comprobar conflictos con otros complementos...**: Audita posibles colisiones de atajos o complementos duplicados.
* **Documentación**: Abre el manual de usuario.

### Licencia
Publicado bajo la licencia GNU General Public License versión 2.0 (GPLv2).
