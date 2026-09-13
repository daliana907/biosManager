# BIOS / UEFI Manager for NVDA

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
  *(Add-on documentation is accessible directly from NVDA Add-on Store / Add-ons Manager by pressing the "Add-on help" button).*
- **Custom gestures:** Assign your preferred shortcuts in NVDA Menu > Preferences > Input Gestures under the "BIOS and UEFI Manager" category.
- **Inside the settings dialog:**
  - *Search:* Type your search query and press `Enter` or click the *Filter* button.
  - *Boot order:* Select a device and press `Alt + Up Arrow` or `Alt + Down Arrow` (or click *Move up* / *Move down*) to adjust its position.
  - *Apply and Cancel:* Click *OK* (or press Enter) to write pending changes to UEFI, or *Cancel* (or Escape) to dismiss changes and close.

## What's new in 1.7 (12 September 2026)

### Security and Compatibility

- Prevents loading in NVDA secure mode / secure screens to eliminate privilege escalation risks.
- Removed default keyboard shortcut to avoid overriding NVDA's native battery status command.
- Added a Tools menu option to reboot directly into UEFI firmware setup.
- Uses NVDA's official API (`openDocumentation()`) to open documentation according to the active language.
- Conflict detection regex now uses word boundary matching to eliminate false positives on words like "cambios".
- Dynamic month and leap-year validation for BIOS date settings (1970-2037).
- Signed 32-bit integer range (-2147483648 to 2147483647) for numeric spin controls.
- Settings with available options are correctly treated as dropdowns even when their current value is empty.
- Canceling the dialog no longer triggers unnecessary WMI calls.

## What's new in 1.6 (8 September 2026)

### Fixed

- BIOS changes were never applied: the command sent to Windows was malformed.
- The file with the BIOS answer was left in a folder NVDA could not always read, and the operation appeared to fail for no reason.
- Applying a change was assumed to work without checking. The value is now read back and you are told whether the BIOS accepted or rejected it.
- Saving to the BIOS froze NVDA until it finished. It now runs in the background.
- Closing the window with a typed but unapplied change lost it silently. It now warns you.
- Boot order was edited with one dropdown per position, so a device could be repeated and another omitted with no warning.
- BIOS queries could wait forever if the machine did not answer or nobody responded to the permission prompt.

### Internal changes

- Boot order is now edited in a single list reordered with Alt and the arrow keys, and only what actually moved is summarised on apply.
- The settings editor separates deciding which editor a value needs from building it, and that decision has its own tests.
- Removed about 119 lines of code that were no longer used.
- Fixed two security issues: a temporary file with a predictable name, and values sent to Windows without escaping.
- Added 52 automatic checks that run on their own on GitHub with every change.

The full history of every version is in the CHANGELOG.md file of the
add-on repository.
