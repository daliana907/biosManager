# BIOS / UEFI Manager for NVDA

* **Author:** Daliana
* **Version:** 1.5
* **Compatibility:** NVDA 2023.1 or later
* **License:** GNU General Public License v2.0 (GPLv2)

An advanced accessibility add-on for the NVDA screen reader that enables users to query, search, and configure BIOS and UEFI firmware settings directly from Windows.

## The Problem It Solves
Traditional BIOS/UEFI setup interfaces run before the operating system boots and are purely visual, rendering them inaccessible to blind and visually impaired users. This add-on brings firmware configuration into the accessible Windows desktop environment, allowing full speech and braille interaction.

## Hardware Compatibility
Interacting with firmware from Windows requires hardware vendor instrumentation:

* **Supported:** **Lenovo** enterprise and business line computers (**ThinkPad** laptops, **ThinkCentre** desktops, **ThinkStation** workstations).
* **Architecture:** Modular design allowing future translation drivers for other enterprise vendors (Dell, HP).
* **Unsupported:** Generic custom-built PCs and budget consumer laptops without vendor WMI firmware support.

## Technical Architecture & Safety
1. **WMI (Windows Management Instrumentation):** The add-on queries official vendor WMI namespaces (`root\wmi`).
2. **NVRAM Persistence:** Settings modified via vendor WMI methods are written to motherboard NVRAM, preserving configurations across OS installations and formatting.
3. **Firmware Protection:** All parameters are verified and validated by the motherboard firmware itself; invalid parameters are safely rejected.
4. **Elevation Control:** Administrative privilege elevation via Windows UAC is only requested when applying user-confirmed changes.

## Menu in NVDA Tools
Access all functions via **NVDA Menu > Tools > BIOS and UEFI Manager**:
* **BIOS / UEFI Settings...**: Opens the accessible management dialog.
* **Check conflicts with other add-ons...**: Audits shortcut collisions and duplicate tools.
* **Documentation**: Opens this user guide.

## How to Use the Interface
The dialog features a list of settings on the left and a dynamic context panel on the right:
* **Drop-down options (Enable/Disable):** Standard combo boxes navigated with arrow keys.
* **Boot Device Priority:** Dynamic sequence of combo boxes for each boot slot.
* **Text / Passwords / Dates:** Accessible text fields and numeric spin controls.
* **Staging Changes:** Click **Add to pending changes** to review staged items before writing.
* **Applying Changes:** Click **OK** and accept the Windows UAC elevation prompt. Changes apply on the next system restart.

## Changelog

### Version 1.5
* Dedicated `BIOS and UEFI Manager` submenu under NVDA Tools.
* Conflict audit tool to diagnose duplicate add-ons or conflicting shortcuts.
* Comprehensive diagnostic logging in `nvda.log`.
* Full exception tracebacks (`exc_info=True`) on all background operations.

### Version 1.4
* Formal AI usage statement (Guideline Criterion 4.5).
* Vendor API security and privilege documentation.
* Tested compatibility with NVDA 2026.2.
