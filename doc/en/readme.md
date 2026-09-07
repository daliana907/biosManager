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