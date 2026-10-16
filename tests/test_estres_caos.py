# -*- coding: utf-8 -*-
"""Batería de pruebas de estrés, caos y resiliencia extrema para biosManager.

Somete el backend WMI y la interfaz de BIOS/UEFI a:
- Salidas corruptas de PowerShell (JSON truncado, garbage, bytes nulos)
- Ataques de inyección y contraseñas extremas (comillas, miles de caracteres)
- Órdenes de arranque anómalos (cíclicos, duplicados, inexistentes)
- Fechas y horas extremas (años bisiestos/no bisiestos, desbordamientos, segundos 60)
- Concurrencia y hammering en guardado / cancelación de diálogo
"""
import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nvda_falso
nvda_falso.instalar()

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "globalPlugins"))
sys.path.insert(0, os.path.join(RAIZ, "globalPlugins", "biosManager"))

import wmi_backend
import dialog


class TestEstresCaosBiosManager(unittest.TestCase):
    """Pruebas de estrés y situaciones inesperadas en biosManager."""

    def setUp(self):
        self.backend = wmi_backend.WmiBackend()

    # ── 1. Salidas corruptas y truncadas de PowerShell en apply_settings ─────
    def test_apply_settings_con_salidas_corruptas(self):
        """Verifica que apply_settings no lance excepciones ante salidas corruptas de PowerShell."""
        salidas_caoticas = [
            (False, None),  # UAC cancelado o timeout
            (True, ""),     # Salida vacía
            (True, "{json_incompleto:"),  # JSON truncado
            (True, "<html><body>502 Bad Gateway</body></html>"),  # Salida no JSON
            (True, "123456"),  # Entero como JSON
            (True, "null"),    # Null
            (True, "[]"),      # Lista vacía en vez de dict
            (True, '{"SaveResult": null, "Settings": null}'),
            (True, '{"SaveResult": "Success", "Settings": "no_es_lista"}'),
            (True, '{"SaveResult": "Success", "Settings": [{"Name": null, "SetResult": null, "Current": null}]}'),
            (True, '{"SaveResult": "Success", "Settings": [{"Name": "SecureBoot\x00Injected", "SetResult": "Success", "Current": "Enable"}]}'),
        ]
        settings_test = {"SecureBoot": "Enable"}
        for ok_simulado, salida_simulada in salidas_caoticas:
            with self.subTest(salida=salida_simulada):
                with patch.object(self.backend, "_ejecutarPowerShellElevado", return_value=(ok_simulado, salida_simulada)):
                    ok, informe = self.backend.apply_settings(settings_test, password="test")
                    self.assertIsInstance(ok, bool)
                    self.assertIsInstance(informe, str)
                    self.assertNotIn("\x00", informe)

    # ── 2. Inyección de contraseñas extremas y caracteres especiales ────────
    def test_escapado_contrasenas_extremas_y_payloads(self):
        """Verifica que contraseñas con caracteres raros o miles de caracteres se escapen sin romper PowerShell."""
        payloads_riesgosos = [
            "",
            "normal_password",
            "O'Malley's'Password",
            "'; Remove-Item -Path C:\\ -Recurse; '",
            "\"`$((Get-Process).Name)\"",
            "ContraseñaConÑáéíóú123!@#$%^&*()_+",
            "A" * 5000,
            "'; exit 0; #",
            "\t\r\n\x00",
        ]
        for pwd in payloads_riesgosos:
            with self.subTest(pwd=pwd[:30]):
                escaped = self.backend._textoPowerShell(pwd)
                self.assertTrue(escaped.startswith("'"))
                self.assertTrue(escaped.endswith("'"))
                # La cantidad de comillas simples internas sin doblar debe ser cero
                interior = escaped[1:-1]
                # Reemplazamos las comillas dobles '' (escapadas) por vacío
                sin_escapadas = interior.replace("''", "")
                self.assertNotIn("'", sin_escapadas, "No debe haber comillas simples sueltas sin escapar.")

    # ── 3. Fuzzing y validación extrema de orden de arranque ─────────────────
    def test_fuzzing_orden_de_arranque(self):
        """Prueba _problemaEnOrdenDeArranque con entradas anómalas, duplicados y dispositivos vacíos."""
        dlg = dialog.BiosManagerDialog.__new__(dialog.BiosManagerDialog)
        dlg._bootOriginal = ["NVMe", "USB", "PXE", "HDD"]

        casos_arranque = [
            ("NVMe:USB:PXE:HDD", None),  # Idéntico: OK
            ("HDD:PXE:USB:NVMe", None),  # Invertido: OK
            ("USB:NVMe:HDD:PXE", None),  # Reordenado: OK
            ("NVMe:USB:PXE", "faltan: HDD"),  # Falta uno: debe detectar error
            ("NVMe:USB:PXE:HDD:NVMe", "aparecen dos veces: NVMe"),  # Duplicado: error
            ("NVMe:USB:PXE:HDD:Fantasma", "la lista quedó distinta"),  # Dispositivo nuevo no existente
            ("", "faltan:"),  # Vacío: faltan todos
            (None, "faltan:"),  # None: faltan todos
            ("NVMe:NVMe:NVMe:NVMe", "aparecen dos veces: NVMe"),  # Todo duplicado
        ]
        for val, problema_esperado in casos_arranque:
            with self.subTest(val=val):
                res = dlg._problemaEnOrdenDeArranque(val)
                if problema_esperado is None:
                    self.assertIsNone(res)
                else:
                    self.assertIsNotNone(res)
                    self.assertIn(problema_esperado, res)

    # ── 4. Fechas y horas extremas (bisiestos, desbordamientos, segundos 60) ──
    def test_validacion_fechas_bisiestas_y_limites(self):
        """Verifica que el selector de fecha gestione años bisiestos y rangos de meses/días."""
        dlg = dialog.BiosManagerDialog.__new__(dialog.BiosManagerDialog)
        # Febrero en año bisiesto (2024, 2028) vs no bisiesto (2025, 2026)
        self.assertEqual(dlg._diasEnMes(2024, 2), 29)
        self.assertEqual(dlg._diasEnMes(2028, 2), 29)
        self.assertEqual(dlg._diasEnMes(2025, 2), 28)
        self.assertEqual(dlg._diasEnMes(2026, 2), 28)
        self.assertEqual(dlg._diasEnMes(2000, 2), 29)
        self.assertEqual(dlg._diasEnMes(1900, 2), 28)

        # Meses anómalos o tipos erróneos devuelven fallback seguro 31
        self.assertEqual(dlg._diasEnMes("año_invalido", 2), 31)
        self.assertEqual(dlg._diasEnMes(2026, 13), 31)
        self.assertEqual(dlg._diasEnMes(2026, -1), 31)

    # ── 5. Re-entrancia y protección durante guardado concurrente ────────────
    def test_reentrancia_on_save_y_on_cancel(self):
        """Verifica que al estar guardando (_guardando=True), clics repetidos en Guardar o Cancelar sean rechazados."""
        dlg = dialog.BiosManagerDialog.__new__(dialog.BiosManagerDialog)
        dlg._guardando = True
        dlg._pending_changes = {"SecureBoot": "Disable"}

        with patch.object(dialog.ui, "message") as mock_msg:
            # Invocar onSave repetidamente debe ignorarse
            dlg.onSave()
            mock_msg.assert_called_with("Se están aplicando los cambios en la BIOS. Espera a que termine.")

        with patch.object(dialog.ui, "message") as mock_msg:
            # Invocar onCancel debe vetar y no cerrar
            mock_event = MagicMock()
            mock_event.CanVeto.return_value = True
            dlg.onCancel(mock_event)
            mock_event.Veto.assert_called_once()
            mock_msg.assert_called_with("Se están aplicando los cambios en la BIOS. Espera a que termine.")

    # ── 6. Protección ante objeto C++ destruido (PyDeadObjectError) ───────────
    def test_dead_object_protection_en_callbacks_asincronos(self):
        """Verifica que callbacks como _alTerminarDeGuardar y _on_settings_loaded no lancen PyDeadObjectError."""
        class DeadWxDialog(dialog.BiosManagerDialog):
            def __init__(self):
                pass
            def __bool__(self):
                # Simula la comprobación de wxPython cuando el C++ object fue destruido
                raise RuntimeError("wrapped C/C++ object has been deleted")

        dead_dlg = DeadWxDialog.__new__(DeadWxDialog)
        # Ninguno de estos métodos debe propagar RuntimeError o PyDeadObjectError
        try:
            dead_dlg._alTerminarDeGuardar(True, "OK")
            dead_dlg._on_settings_loaded([{"name": "test"}])
            dead_dlg._on_unsupported()
        except RuntimeError as e:
            self.fail(f"Los callbacks asíncronos fallaron ante objeto destruido: {e}")

    # ── 7. Resiliencia en ejecución de PowerShell elevado ────────────────────
    def test_ejecutar_powershell_elevado_resiliencia(self):
        """Verifica que _ejecutarPowerShellElevado maneje fallos de mkstemp y timeout limpiamente."""
        with patch("tempfile.mkstemp", side_effect=OSError("Disco lleno")):
            try:
                ok, salida = self.backend._ejecutarPowerShellElevado("Write-Host 'Test'")
                self.assertFalse(ok)
                self.assertIsNone(salida)
            except OSError:
                pass

    # ── 8. Manejo de tipos heterogéneos y valores None en selectores ──────────
    def test_tipo_de_editor_entradas_heterogeneas(self):
        """Verifica que _tipoDeEditor no falle con None, enteros o datos no estándar."""
        dlg = dialog.BiosManagerDialog.__new__(dialog.BiosManagerDialog)
        dlg.ORDEN_DE_ARRANQUE = "BootOrder"

        # Con None
        self.assertEqual(dlg._tipoDeEditor("NormalSetting", None, []), "text")
        # Con entero
        self.assertEqual(dlg._tipoDeEditor("NormalSetting", 12345, []), "spin")
        # Con fecha
        self.assertEqual(dlg._tipoDeEditor("DateSetting", "2026-05-18", []), "date")
        # Con hora
        self.assertEqual(dlg._tipoDeEditor("TimeSetting", "14:30:00", []), "time")
        # Con opciones y None
        self.assertEqual(dlg._tipoDeEditor("ChoiceSetting", None, ["A", "B"]), "choice")
        # Con BootOrder
        self.assertEqual(dlg._tipoDeEditor("BootOrder", None, []), "bootorder_list")

    # ── 9. Backend get_selections lanzando excepciones durante UI ─────────────
    def test_get_selections_con_fallo_backend_en_dialogo(self):
        """Verifica que fallos de backend.get_selections no provoquen unhandled exceptions en el diálogo."""
        dlg = dialog.BiosManagerDialog.__new__(dialog.BiosManagerDialog)
        mock_backend = MagicMock()
        mock_backend.get_selections.side_effect = RuntimeError("WMI COM disconnect")
        dlg.backend = mock_backend
        dlg._filtered_settings = [{"name": "Setting1", "value": "Val1"}]
        dlg._pending_changes = {}
        dlg._load_generation = 0
        dlg._closing = False
        dlg.list_ctrl = MagicMock()
        dlg.list_ctrl.GetFirstSelected.return_value = 0
        dlg._build_editor = MagicMock()
        dlg._mostrarCargando = MagicMock()

        # _on_item_selected es async (hilo + CallAfter): ejecutar ambos en línea.
        with patch.object(dialog.wx, "CallAfter", side_effect=lambda fn, *a, **k: fn(*a, **k)):
            with patch.object(dialog.threading, "Thread") as mock_thread:
                def _hilo_inline(target=None, args=(), kwargs=None, daemon=None):
                    m = MagicMock()
                    def _start():
                        target(*args, **(kwargs or {}))
                    m.start.side_effect = _start
                    return m
                mock_thread.side_effect = _hilo_inline
                dlg._on_item_selected(None)
        # El fallo se atrapa en _hiloOpciones y llega a _build_editor con opts=[].
        dlg._build_editor.assert_called_with("Setting1", "Val1", [])

    # ── 10. Contraseña con bytes nulos en apply_settings ─────────────────────
    def test_apply_settings_con_bytes_nulos_en_password(self):
        """Verifica que una contraseña con bytes nulos sea desinfectada sin excepciones."""
        mock_json = '{"SaveResult": "Success", "Settings": [{"Name": "Setting1", "SetResult": "Success", "Current": "Val1"}]}'
        with patch.object(self.backend, "_ejecutarPowerShellElevado", return_value=(True, mock_json)):
            ok, msg = self.backend.apply_settings({"Setting1": "Val1"}, password="secret\x00injected")
            self.assertTrue(ok)

    # ── 11. Opciones como lista en get_all_settings y resiliencia en días del mes ─
    def test_get_all_settings_options_lista_y_actualizar_dias_mes(self):
        """Verifica que get_all_settings tolere opciones como lista nativa y _actualizarDiasDelMes no falle ante errores."""
        mock_json = json.dumps([
            {"Name": "SettingList", "Value": "Opt1", "Options": ["Opt1", "Opt2"]},
            {"Name": "SettingStr", "Value": "A", "Options": "A, B"},
            {"Name": "SettingNone", "Value": "X", "Options": None},
        ])
        with patch.object(self.backend, "_ejecutarPowerShellElevado", return_value=(True, mock_json)):
            settings = self.backend.get_all_settings()
            self.assertEqual(len(settings), 3)
            self.assertEqual(settings[0]["options"], ["Opt1", "Opt2"])
            self.assertEqual(settings[1]["options"], ["A", "B"])
            self.assertEqual(settings[2]["options"], [])

        # Resiliencia en _actualizarDiasDelMes
        dlg = dialog.BiosManagerDialog.__new__(dialog.BiosManagerDialog)
        dlg.sp_year = MagicMock()
        dlg.sp_year.GetValue.side_effect = RuntimeError("Dead object")
        try:
            dlg._actualizarDiasDelMes(None)
        except Exception as e:
            self.fail(f"_actualizarDiasDelMes lanzó excepción: {e}")

    # ── 12. Duplicados en orden de arranque y _moverArranque con dead object ─
    def test_resumen_orden_pendiente_duplicados_y_mover_arranque_dead_object(self):
        """Verifica que _resumenOrdenPendiente maneje duplicados sin errores y que _moverArranque sea seguro ante objetos destruidos."""
        # Duplicados en orden de arranque
        antes = "USB:USB:NVMe"
        despues = "NVMe:USB:USB"
        resumen = dialog.BiosManagerDialog._resumenOrdenPendiente(antes, despues)
        self.assertIn("Quedaría primero NVMe.", resumen)
        self.assertIn("2 cambian de puesto.", resumen)

        # _moverArranque sin boot_list o con objeto muerto
        dlg = dialog.BiosManagerDialog.__new__(dialog.BiosManagerDialog)
        dlg.boot_list = None
        try:
            dlg._moverArranque(1)
        except Exception as e:
            self.fail(f"_moverArranque lanzó excepción con boot_list None: {e}")

        # Objeto muerto
        mock_list = MagicMock()
        mock_list.GetSelection.side_effect = RuntimeError("Dead object")
        dlg.boot_list = mock_list
        try:
            dlg._moverArranque(-1)
        except Exception as e:
            self.fail(f"_moverArranque lanzó excepción con mock destruido: {e}")


    # ── 13. Resiliencia de _apply_filter y _populate_list ante elementos malformados ───
    def test_apply_filter_y_populate_list_elementos_malformados(self):
        """Verifica que _apply_filter y _populate_list toleren listas con None, no-dicts o sin clave 'name'."""
        dlg = dialog.BiosManagerDialog.__new__(dialog.BiosManagerDialog)
        dlg._all_settings = [
            None,
            "no_es_un_dict",
            {},
            {"value": "SoloValor"},
            {"name": None, "value": "NombreNone"},
            {"name": "SecureBoot", "value": "Enabled"},
        ]
        dlg.list_ctrl = MagicMock()
        dlg.list_ctrl.GetItemCount.return_value = 0
        dlg._pending_changes = {}
        dlg._clear_editor = MagicMock()

        try:
            dlg._apply_filter("secure")
            self.assertEqual(len(dlg._filtered_settings), 1)
            self.assertEqual(dlg._filtered_settings[0]["name"], "SecureBoot")

            dlg._apply_filter("")
            self.assertEqual(len(dlg._filtered_settings), 4)
        except Exception as e:
            self.fail(f"_apply_filter lanzó excepción ante datos malformados: {e}")


    # ── 14. open_dialog destruye diálogo viejo no visible antes de crear uno nuevo ──
    def test_open_dialog_destruye_dialogo_oculto_previo(self):
        """Verifica que si _dialog existía pero no estaba visible, se destruya limpiamente."""
        from biosManager import GlobalPlugin
        plugin = GlobalPlugin.__new__(GlobalPlugin)
        mock_old_dlg = MagicMock()
        mock_old_dlg.IsShown.return_value = False
        plugin._dialog = mock_old_dlg
        plugin.backend = MagicMock()
        plugin._on_dialog_closed = MagicMock()

        with patch("gui.mainFrame"):
            with patch("biosManager.BiosManagerDialog") as mock_dlg_cls:
                mock_new_dlg = MagicMock()
                mock_dlg_cls.return_value = mock_new_dlg
                plugin.open_dialog()
                mock_old_dlg.Destroy.assert_called_once()
                self.assertEqual(plugin._dialog, mock_new_dlg)

    # ── 15. script_rebootToUefi ante excepción en gui.messageBox ──
    def test_reboot_to_uefi_exception_resilience(self):
        """Verifica que un fallo inesperado en messageBox durante la confirmación no propague excepción."""
        from biosManager import GlobalPlugin
        plugin = GlobalPlugin.__new__(GlobalPlugin)
        plugin.backend = MagicMock()

        with patch("gui.messageBox", side_effect=RuntimeError("Error en mensaje de reinicio")):
            # Ejecutamos prompt_and_reboot
            with patch("wx.CallAfter", side_effect=lambda fn: fn()):
                try:
                    plugin.script_rebootToUefi(None)
                except Exception as e:
                    self.fail(f"script_rebootToUefi lanzó excepción: {e}")


if __name__ == "__main__":
    unittest.main()

