# BIOS and UEFI Manager for NVDA

- Author: Daliana
- Version: 1.9
- Compatibility: NVDA 2023.1 and later
- License: GNU GPL v2

[Leer en español](../es/readme.md)

---

## English Version

This add-on allows you to view and modify your computer's UEFI firmware settings directly from the Windows desktop with NVDA in a fully accessible way.

### What is it for?
Normally, changing firmware settings (such as the boot order to boot from a USB drive or enabling virtualization) requires restarting the computer and pressing keys blindly on a visual screen with no speech or screen reader support.

With this add-on, you do not need sighted assistance: open the window inside Windows, find the setting you want using the keyboard, make the change, and when you reboot, the motherboard applies the new settings.

### BIOS Types and Compatibility
It is essential to distinguish between legacy BIOS and UEFI firmware:

- Legacy BIOS cannot be managed or modified from Windows accessibly.
- Modern UEFI firmware enables secure communication with Windows through vendor WMI interfaces. This add-on is designed specifically for UEFI.

### Supported Computers
Due to how motherboard communication works in Windows:

- Supported: Lenovo business line computers (ThinkPad laptops, ThinkCentre desktops, and ThinkStation workstations).
- Not supported: Custom-built desktop computers or consumer laptops lacking vendor WMI interfaces. If opened on an unsupported computer, the add-on alerts you safely.

### Safety Warnings and Responsible Use
Modifying firmware settings is a delicate operation:

- Boot order: Changing boot devices or their order can prevent Windows from booting normally.
- Security and virtualization: Modifying settings like Secure Boot, TPM, supervisor passwords, or virtualization (VT-x / AMD-V) can affect drive encryption (such as BitLocker) or system boot integrity. Only modify settings you understand.
- Secure desktop protection: For security reasons, the add-on automatically disables itself on Windows secure screens (such as lock screens or User Account Control prompts) to prevent unauthorized privileged access.

### Options and Keyboard Shortcuts

The add-on assigns no default keyboard shortcuts to avoid conflicting with native NVDA commands (such as `NVDA + Shift + B` for battery status).

### Options from the NVDA Menu

Under NVDA Menu > Tools > BIOS and UEFI Manager:

- BIOS / UEFI Settings...: Opens the main settings dialog.
- Reboot to UEFI / BIOS settings...: Restarts the system directly into UEFI firmware setup.
- Check shortcut conflicts with other add-ons...: Checks for overlapping shortcuts or duplicate add-ons.

### Custom Shortcut Assignment

Assign your preferred keyboard shortcuts under NVDA Menu > Preferences > Input Gestures, in the "BIOS and UEFI Manager" category.

### Keyboard Shortcuts inside the Settings Window

- Search: Type the search term and press Enter or the Filter button. Press Clear to reset.
- Boot Order: Select a device and use Alt + Up Arrow or Alt + Down Arrow (or Move Up / Move Down buttons) to change its position.
- Confirm and Cancel: Press OK (or Enter outside text fields) to apply pending BIOS changes, or Cancel (or Escape) to discard changes and close.

---

## What's new in 1.9.1 (13 September 2026)

- Lighter add-on footprint: removed unused internal dependencies, reducing the amount of code loaded by NVDA.
- Complete internal technical documentation of BIOS communication and all settings window controls.

## What's new in 1.9 (13 September 2026)

- Machine-specific date format support: the date editor now automatically matches whether your motherboard uses slashes or hyphens for dates, preventing false modification warnings when browsing and ensuring the firmware accepts saved dates.
- Safter date entry via keyboard: prevents entering invalid dates (such as February 30 or month 13) and accurately calculates leap years so dates are always valid and safe.
- Numeric settings with negative or automatic values: system options using negative numbers or special automatic codes can now be adjusted easily using the numeric controls in the window.
- Improved window stability: resolved errors that could occur if the window was dismissed while system checks were running.
- Complete protection during firmware saving: the window cannot be closed accidentally or with Escape while changes are being written to the computer, safeguarding the motherboard against dangerous interruptions.
- Enhanced time recognition: the time editor validates standard clock formats, preventing out-of-range hours or minutes.
- Faster search: typing in the search box dynamically filters the list by both setting name and value, instantly loading the right control to edit it.
- More reliable reboot to BIOS: rebooting directly into BIOS/UEFI setup checks for required permissions and announces clearly whether your computer supports this feature.
- Automatic system cleanup: installing or uninstalling the add-on completely removes temporary files without leaving leftover traces.

### Credits and License
- Author: Daliana.
- License: GNU General Public License v2.
