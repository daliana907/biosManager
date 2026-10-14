# -*- coding: utf-8 -*-
"""Pruebas de dialog.py que necesitan instanciar la ventana de verdad.

Para esto se completó tests/nvda_falso.py con un simulador más genérico de wx
(ver el `wx.__getattr__` agregado ahí), porque antes le faltaban varias
constantes de eventos que dialog.py usa al construirse.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nvda_falso                                    # noqa: E402

nvda_falso.instalar()

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "globalPlugins", "biosManager"))

import dialog  # noqa: E402


class CondicionDeCarreraAlCerrarMientrasCarga(unittest.TestCase):
    """Cerrar la ventana (Cancelar/Aceptar) mientras la lectura de ajustes en
    segundo plano todavía no terminó no debe intentar tocar controles ya
    destruidos cuando esa lectura por fin llega.
    """

    def setUp(self):
        nvda_falso.dichos.clear()
        self.dialogo = dialog.BiosManagerDialog(None, backend=object())

    def test_on_settings_loaded_no_hace_nada_si_ya_se_esta_cerrando(self):
        self.dialogo._closing = True
        ajustes = [{"name": "Modo de arranque", "value": "UEFI",
                    "possible_values": ["UEFI", "Legacy"], "editable": True}]

        # No debe lanzar ninguna excepción ni poblar la lista.
        self.dialogo._on_settings_loaded(ajustes)

        self.assertEqual(self.dialogo._all_settings, [])

    def test_on_unsupported_no_hace_nada_si_ya_se_esta_cerrando(self):
        self.dialogo._closing = True

        self.dialogo._on_unsupported()

        # No debe haber anunciado el mensaje de "no se pudieron leer los ajustes".
        self.assertEqual(len(nvda_falso.dichos), 0)


class NoPerderCambiosSiLaBiosRechaza(unittest.TestCase):
    """Si la BIOS rechaza el guardado (por ejemplo, por faltar la contraseña de
    supervisor), la ventana debe quedarse abierta con los cambios pendientes
    intactos, en vez de cerrarse y obligar a rehacerlos desde cero."""

    def setUp(self):
        self.dialogo = dialog.BiosManagerDialog(None, backend=object())
        self.dialogo._pending_changes = {"WakeOnLAN": "Disable"}
        self.dialogo._guardando = True
        self.dialogo.btn_ok.Disable()
        self.dialogo.btn_cancel.Disable()

    def test_si_falla_no_se_cierra_y_los_cambios_pendientes_siguen(self):
        self.dialogo._alTerminarDeGuardar(False, "acceso denegado")

        self.assertEqual(self.dialogo._pending_changes, {"WakeOnLAN": "Disable"})
        self.assertFalse(self.dialogo._closing)

    def test_si_funciona_se_cierra_y_se_limpian_los_cambios_pendientes(self):
        self.dialogo._alTerminarDeGuardar(True, "todo bien")

        self.assertEqual(self.dialogo._pending_changes, {})
        self.assertTrue(self.dialogo._closing)


class ItemActivatedYFoco(unittest.TestCase):
    """Pulsar Enter en un elemento de la lista pasa el foco al editor."""

    def setUp(self):
        self.dialogo = dialog.BiosManagerDialog(None, backend=object())

    def test_on_item_activated_pasa_foco_al_control(self):
        class FalsoControl:
            enfocado = False

            def SetFocus(self):
                self.enfocado = True

        falso = FalsoControl()
        self.dialogo.ctrl = falso
        self.dialogo._on_item_activated()
        self.assertTrue(falso.enfocado)

    def test_on_item_activated_sin_control_no_falla(self):
        self.dialogo.ctrl = None
        self.dialogo.boot_list = None
        self.dialogo.sp_year = None
        self.dialogo.sp_h = None
        self.dialogo._on_item_activated()


if __name__ == "__main__":
    unittest.main(verbosity=2)
