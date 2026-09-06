# -*- coding: utf-8 -*-

import os
import logging
import wx
import addonHandler
addonHandler.initTranslation()
import globalPluginHandler
import scriptHandler
import inputCore
import gui
import ui

from .dialog import BiosManagerDialog
from .wmi_backend import WmiBackend

log = logging.getLogger(__name__)

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = _("Gestor de BIOS y UEFI")

    def __init__(self):
        super().__init__()
        log.info("BIOS Manager: Inicializando complemento (v1.5)...")
        self.backend = WmiBackend()
        self._dialog = None

        # Agregar submenú organizado en el menú Herramientas de NVDA
        try:
            self._toolsMenu = gui.mainFrame.sysTrayIcon.toolsMenu
            self._subMenu = wx.Menu()
            self._itemConfig = self._subMenu.Append(
                wx.ID_ANY,
                _("&Configuración de la BIOS / UEFI..."),
                _("Abre la ventana accesible para consultar y configurar la BIOS/UEFI")
            )
            self._itemConflicts = self._subMenu.Append(
                wx.ID_ANY,
                _("&Comprobar conflictos con otros complementos..."),
                _("Comprueba si existen conflictos de atajos de teclado o complementos incompatibles con el Gestor de BIOS")
            )
            self._itemDoc = self._subMenu.Append(
                wx.ID_ANY,
                _("&Documentación"),
                _("Abre la ayuda y documentación del Gestor de BIOS")
            )
            gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self._on_menu_open, self._itemConfig)
            gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self._on_menu_conflicts, self._itemConflicts)
            gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self._on_menu_doc, self._itemDoc)
            self._subMenuItem = self._toolsMenu.AppendSubMenu(
                self._subMenu,
                _("&Gestor de BIOS y UEFI"),
                _("Opciones y configuración accesible de la BIOS/UEFI")
            )
            log.info("BIOS Manager: Submenú 'Gestor de BIOS y UEFI' registrado en Herramientas exitosamente.")
        except Exception as e:
            log.error(f"BIOS Manager: No se pudo registrar el submenú en Herramientas: {e}", exc_info=True)
            self._subMenuItem = None

        import threading
        threading.Thread(target=self._startupBackgroundWorker, daemon=True).start()
        log.info("BIOS Manager: Complemento iniciado y listo.")

    def terminate(self):
        log.info("BIOS Manager: Finalizando complemento...")
        if hasattr(self, "_dialog") and self._dialog:
            try:
                self._dialog.Destroy()
            except Exception as e:
                log.debug(f"BIOS Manager: Error destruyendo diálogo en terminate: {e}")
            self._dialog = None

        try:
            if hasattr(self, "_itemConfig") and self._itemConfig:
                gui.mainFrame.sysTrayIcon.Unbind(wx.EVT_MENU, source=self._itemConfig)
            if hasattr(self, "_itemConflicts") and self._itemConflicts:
                gui.mainFrame.sysTrayIcon.Unbind(wx.EVT_MENU, source=self._itemConflicts)
            if hasattr(self, "_itemDoc") and self._itemDoc:
                gui.mainFrame.sysTrayIcon.Unbind(wx.EVT_MENU, source=self._itemDoc)
            if hasattr(self, "_subMenuItem") and self._subMenuItem:
                self._toolsMenu.Remove(self._subMenuItem)
        except Exception as e:
            log.debug(f"BIOS Manager: Error retirando submenú en terminate: {e}")

        super().terminate()
        log.info("BIOS Manager: Complemento finalizado limpiamente.")

    def _on_menu_open(self, event):
        log.info("BIOS Manager: Opción 'Configuración de la BIOS / UEFI' seleccionada en el menú.")
        self.open_dialog()

    def _on_menu_conflicts(self, event):
        log.info("BIOS Manager: Opción 'Comprobar conflictos' seleccionada en el menú.")
        wx.CallAfter(self._checkAddonConflicts, interactive=True)

    def _on_menu_doc(self, event):
        doc = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "doc", "es", "readme.html"))
        log.info(f"BIOS Manager: Abriendo documentación desde: {doc}")
        if os.path.exists(doc):
            os.startfile(doc)
        else:
            log.warning(f"BIOS Manager: Archivo de documentación no encontrado en {doc}")
            ui.message(_("No se encontró el archivo de documentación de BIOS Manager."))

    def _startupBackgroundWorker(self):
        try:
            import time
            time.sleep(3.0)
            self._checkAddonConflicts(interactive=False)
        except Exception as e:
            log.error(f"BIOS Manager: Error durante la comprobación de conflictos: {e}", exc_info=True)

    def auditConflicts(self):
        """
        Audita y registra en nvda.log posibles conflictos con otros complementos instalados o activos,
        incluyendo colisiones directas de atajos de teclado (gestos) y complementos de BIOS duplicados.
        Devuelve una tupla (conflicts, warnings).
        """
        conflicts = []
        warnings = []

        our_gestures_map = {
            "kb:nvda+shift+b": _("Apertura de la ventana del Gestor de BIOS / UEFI"),
        }

        log.info("BIOS Manager: Iniciando auditoría exhaustiva de compatibilidad y conflictos con otros complementos...")

        # 1. Comprobar complementos duplicados de BIOS
        try:
            available_addons = list(addonHandler.getAvailableAddons())
            log.info(f"BIOS Manager: Analizando {len(available_addons)} complementos disponibles en el sistema...")
            for addon in available_addons:
                addon_name = getattr(addon, "name", "").lower()
                if addon_name == "biosmanager":
                    continue

                if getattr(addon, "isDisabled", False):
                    continue

                manifest = getattr(addon, "manifest", {}) or {}
                summary = manifest.get("summary", "")

                if "bios" in summary.lower() or "uefi" in summary.lower():
                    msg = f"Complemento con funciones similares activo: '{addon.name}' ({summary}). Podría colisionar en la gestión de firmware."
                    warnings.append(msg)
                    log.warning(f"BIOS Manager ADVERTENCIA DE COMPATIBILIDAD: {msg}")
        except Exception as e:
            log.error(f"BIOS Manager: No se pudo verificar la lista de complementos instalados: {e}", exc_info=True)

        # 2. Comprobar colisiones directas de atajos con otros plugins globales
        try:
            running = getattr(globalPluginHandler, "runningPlugins", set())
            log.info(f"BIOS Manager: Inspeccionando {len(running)} plugins globales activos en busca de colisiones de atajos...")
            for plugin in running:
                if plugin is self:
                    continue
                plugin_mod = getattr(plugin, "__module__", str(type(plugin)))
                if "biosmanager" in plugin_mod.lower():
                    continue

                g_map = getattr(plugin, "_gestureMap", {}) or {}
                if not g_map:
                    g_map = getattr(plugin, "_ScriptableObject__gestures", {}) or {}

                for g_id, script_ref in g_map.items():
                    norm_g = str(g_id).strip().lower().replace(" ", "")
                    if norm_g in our_gestures_map:
                        script_name = getattr(script_ref, "__name__", str(script_ref))
                        our_feature = our_gestures_map[norm_g]
                        collision_msg = (
                            f"Colisión de atajo: '{norm_g}' está asignado tanto a '{our_feature}' (BIOS Manager) "
                            f"como a '{script_name}' en el plugin '{plugin_mod}'."
                        )
                        conflicts.append(collision_msg)
                        log.warning(f"BIOS Manager CONFLICTO DE ATAJO: {collision_msg}")
        except Exception as e:
            log.error(f"BIOS Manager: Error inspeccionando runningPlugins: {e}", exc_info=True)

        # Resumen final en el log
        total_issues = len(conflicts) + len(warnings)
        if total_issues == 0:
            log.info("BIOS Manager: Auditoría de conflictos finalizada con éxito. No se detectaron colisiones de atajos ni complementos incompatibles activos.")
        else:
            log.warning(
                f"BIOS Manager: Auditoría de conflictos finalizada. Se detectaron {len(conflicts)} colisión(es) directa(s) de atajos "
                f"y {len(warnings)} advertencia(s) de compatibilidad."
            )

        return conflicts, warnings

    def _checkAddonConflicts(self, interactive=False):
        conflicts, warnings = self.auditConflicts()
        if interactive:
            total = len(conflicts) + len(warnings)
            if total == 0:
                gui.messageBox(
                    _("No se han detectado conflictos de atajos de teclado ni complementos incompatibles activos con el Gestor de BIOS."),
                    _("Auditoría de compatibilidad - Gestor de BIOS"),
                    wx.OK | wx.ICON_INFORMATION,
                )
            else:
                lines = []
                if conflicts:
                    lines.append(_("COLISIONES DIRECTAS DE ATAJOS:"))
                    for c in conflicts:
                        lines.append(f"• {c}")
                if warnings:
                    if lines:
                        lines.append("")
                    lines.append(_("ADVERTENCIAS DE COMPATIBILIDAD:"))
                    for w in warnings:
                        lines.append(f"• {w}")
                lines.append("")
                lines.append(_("Nota: Los detalles completos también se han registrado en el archivo de log de NVDA."))
                gui.messageBox(
                    "\n".join(lines),
                    _("Auditoría de compatibilidad - Gestor de BIOS"),
                    wx.OK | wx.ICON_WARNING,
                )

    def open_dialog(self):
        log.info("BIOS Manager: Abriendo diálogo accesible de configuración de BIOS...")
        if self._dialog and bool(self._dialog):
            try:
                log.info("BIOS Manager: El diálogo ya estaba abierto, trayéndolo al frente.")
                self._dialog.Raise()
                self._dialog.SetFocus()
                return
            except Exception as e:
                log.debug(f"BIOS Manager: Diálogo previo no válido, recreando: {e}")
                self._dialog = None

        try:
            log.info("BIOS Manager: Instanciando BiosManagerDialog...")
            self._dialog = BiosManagerDialog(parent=gui.mainFrame, backend=self.backend)
            self._dialog.Show()
            log.info("BIOS Manager: Diálogo mostrado con éxito.")
        except Exception as e:
            log.error(f"BIOS Manager: Error abriendo ventana de BIOS: {e}", exc_info=True)
            ui.message(f"{_('Error al abrir la ventana de BIOS:')} {e}")

    @scriptHandler.script(
        description=_("Abre la ventana de configuración accesible de la BIOS/UEFI."),
        gesture="kb:nvda+shift+b",
        speakOnDemand=True,
        category=scriptCategory,
    )
    def script_openBiosManager(self, gesture: inputCore.InputGesture):
        log.info("BIOS Manager: Atajo de apertura activado por el usuario.")
        self.open_dialog()

    @scriptHandler.script(
        description=_("Comprueba si existen conflictos de atajos de teclado o complementos incompatibles con el Gestor de BIOS."),
        category=scriptCategory,
    )
    def script_checkConflicts(self, gesture: inputCore.InputGesture):
        log.info("BIOS Manager: Script de comprobación de conflictos ejecutado desde atajo de teclado.")
        self._checkAddonConflicts(interactive=True)

    @scriptHandler.script(
        description=_("Reinicia el equipo directamente en la pantalla de configuración del firmware UEFI."),
        category=scriptCategory,
    )
    def script_rebootToUefi(self, gesture: inputCore.InputGesture):
        log.info("BIOS Manager: Script de reinicio a UEFI ejecutado desde atajo de teclado.")
        if gui.messageBox(
            _("¿Seguro que deseas reiniciar el equipo ahora mismo para acceder a la BIOS / UEFI?"),
            _("Reiniciar a UEFI - Gestor de BIOS"),
            wx.YES_NO | wx.ICON_QUESTION
        ) == wx.YES:
            ok, msg = self.backend.reboot_to_uefi()
            if not ok:
                ui.message(msg)
