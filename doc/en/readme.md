# BIOS / UEFI Manager for NVDA

This add-on allows blind and visually impaired users to check and change BIOS/UEFI firmware settings directly from Windows using NVDA.

### Why this add-on exists
Traditional BIOS setup screens load before Windows starts. They are purely visual and lack speech support, making them inaccessible without sighted help. This add-on brings those settings into an accessible Windows dialog where NVDA can read and configure them smoothly.

### Supported Computers
- Supported: Lenovo business line computers (ThinkPad laptops, ThinkCentre desktops, ThinkStation workstations) with Lenovo WMI support.
- Not supported: Custom-built desktop PCs and consumer laptops without vendor WMI firmware support. If run on an unsupported system, the add-on will notify you safely.

### Is it safe?
Yes, completely safe:
- It uses Lenovo official WMI interfaces.
- The motherboard validates every change before saving it, preventing firmware corruption.
- Settings are stored in the motherboard NVRAM, surviving operating system reinstallations.
- Administrator elevation (UAC prompt) is only requested when you click OK to write your confirmed changes.

### How to use
1. Open NVDA Menu (NVDA + N) > Tools > BIOS and UEFI Manager > BIOS / UEFI Settings (or press NVDA + Shift + B directly).
2. Browse the list of settings on the left or use the search box to find a setting quickly.
3. On the right panel, change the option using standard combo boxes or edit fields.
4. Click Add to pending changes.
5. Click OK, accept the Windows UAC prompt, and restart your computer when convenient for the changes to take effect.

## What's new in 1.7 (12 September 2026)

### Improved

- Switched to NVDA's native logging framework (`logHandler.log`) so diagnostic and warning messages integrate directly with NVDA's Log Viewer.
- Clean teardown of Tools menu items on addon termination or reload, releasing UI resources cleanly.
- The documentation menu item automatically detects NVDA's active language and opens the Spanish or English guide accordingly.
- The settings dialog now implements standard affirmative and escape IDs (`wx.ID_OK`, `wx.ID_CANCEL`) for native Enter/Escape keyboard navigation.

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
