# -*- coding: utf-8 -*-
"""Pruebas de la lógica que no necesita NVDA abierto.

Se prueban las funciones que transforman datos: informes, resúmenes del orden de
arranque y escapado de valores. Son las que se pueden romper en silencio.

Ejecutar con:   python -m unittest discover -s tests -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nvda_falso                                    # noqa: E402

nvda_falso.instalar()

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "globalPlugins", "biosManager"))

import wmi_backend                                   # noqa: E402
import dialog                                        # noqa: E402

Motor = wmi_backend.WmiBackend
Ventana = dialog.BiosManagerDialog


class EscapadoParaPowerShell(unittest.TestCase):
    """Un valor con comilla no debe poder partir la orden en dos."""

    def test_texto_normal(self):
        self.assertEqual(Motor._textoPowerShell("Enable"), "'Enable'")

    def test_comilla_simple_se_duplica(self):
        self.assertEqual(Motor._textoPowerShell("O'Brien"), "'O''Brien'")

    def test_varias_comillas(self):
        self.assertEqual(Motor._textoPowerShell("a'b'c"), "'a''b''c'")

    def test_numero(self):
        self.assertEqual(Motor._textoPowerShell(3), "'3'")


class ValorLegible(unittest.TestCase):
    """Los valores que son una lista pegada con dos puntos se resumen."""

    def test_orden_de_arranque_se_resume(self):
        self.assertEqual(Motor._valorLegible("A:B:C:D"), "primero A, de 4 dispositivos")

    def test_valor_normal_no_se_toca(self):
        self.assertEqual(Motor._valorLegible("Enable"), "Enable")

    def test_fecha_no_se_toca(self):
        self.assertEqual(Motor._valorLegible("2026/09/08"), "2026/09/08")

    def test_vacio(self):
        self.assertEqual(Motor._valorLegible(""), "")

    def test_none(self):
        self.assertEqual(Motor._valorLegible(None), "")


class InformeDeCambios(unittest.TestCase):
    """El informe debe distinguir aceptado, pendiente de reinicio y rechazado."""

    def _datos(self, resultado, actual, guardado="Success", pedido="Enable"):
        return {"SaveResult": guardado,
                "Settings": [{"Name": "X", "Requested": pedido,
                              "SetResult": resultado, "Current": actual}]}

    def test_confirmado(self):
        ok, texto = Motor._informeDeCambios(self._datos("Success", "Enable"), {"X": "Enable"})
        self.assertTrue(ok)
        self.assertIn("confirmado", texto)

    def test_aceptado_pero_aun_no_cambia(self):
        ok, texto = Motor._informeDeCambios(self._datos("Success", "Disable"), {"X": "Enable"})
        self.assertTrue(ok)
        self.assertIn("reiniciar", texto)

    def test_rechazado_dice_el_motivo(self):
        ok, texto = Motor._informeDeCambios(self._datos("Access Denied", "Disable"), {"X": "Enable"})
        self.assertFalse(ok)
        self.assertIn("Access Denied", texto)

    def test_fallo_al_grabar(self):
        ok, texto = Motor._informeDeCambios(
            self._datos("Success", "Enable", guardado="Invalid Parameter"), {"X": "Enable"})
        self.assertFalse(ok)
        self.assertIn("Invalid Parameter", texto)

    def test_un_solo_ajuste_llega_como_objeto_suelto(self):
        """PowerShell no devuelve una lista cuando hay un único elemento."""
        datos = {"SaveResult": "Success",
                 "Settings": {"Name": "X", "Requested": "On", "SetResult": "Success",
                              "Current": "On"}}
        ok, texto = Motor._informeDeCambios(datos, {"X": "On"})
        self.assertTrue(ok)
        self.assertIn("X", texto)

    def test_ajuste_del_que_la_bios_no_dice_nada(self):
        ok, texto = Motor._informeDeCambios(self._datos("Success", "Enable"),
                                            {"X": "Enable", "Y": "Off"})
        self.assertFalse(ok)
        self.assertIn("Y", texto)


class PresentacionDelOrdenDeArranque(unittest.TestCase):
    ANTES = "NVMe0:USBHDD:USBCD"
    DESPUES = "USBHDD:NVMe0:USBCD"

    def test_orden_numerado(self):
        self.assertEqual(Ventana._ordenLegible("A:B"), "1, A. 2, B.")

    def test_resumen_corto_para_la_lista(self):
        self.assertEqual(Ventana._resumenOrden("A:B:C"), "Primero A. 3 dispositivos.")

    def test_resumen_con_un_solo_dispositivo(self):
        self.assertEqual(Ventana._resumenOrden("A"), "Solo A.")

    def test_el_resumen_pendiente_se_distingue_del_actual(self):
        pendiente = Ventana._resumenOrdenPendiente(self.ANTES, self.DESPUES)
        actual = Ventana._resumenOrden(self.ANTES)
        self.assertIn("Quedaría", pendiente)
        self.assertNotIn("Quedaría", actual)
        self.assertNotEqual(pendiente, actual)

    def test_marca_de_donde_venia_cada_uno(self):
        texto = Ventana._ordenConCambios(self.ANTES, self.DESPUES)
        self.assertIn("antes", texto)
        self.assertIn("1, USBHDD, antes 2", texto)
        self.assertIn("3, USBCD", texto)          # no se movió: sin marca
        self.assertNotIn("3, USBCD, antes", texto)

    def test_solo_lo_que_se_movio(self):
        texto = Ventana._soloLoQueSeMovio(self.ANTES, self.DESPUES)
        self.assertIn("USBHDD", texto)
        self.assertIn("NVMe0", texto)
        self.assertNotIn("USBCD", texto)

    def test_sin_cambios_no_dice_nada(self):
        self.assertEqual(Ventana._soloLoQueSeMovio(self.ANTES, self.ANTES), "")

    def test_listas_distintas_no_se_comparan(self):
        self.assertEqual(Ventana._soloLoQueSeMovio(self.ANTES, "X:Y"), "")


class ValidacionDelOrdenDeArranque(unittest.TestCase):
    """Última red antes de mandar a la BIOS un orden estropeado."""

    def _ventana(self, original):
        v = Ventana.__new__(Ventana)
        v._bootOriginal = original.split(":")
        return v

    def test_una_reordenacion_valida_pasa(self):
        v = self._ventana("A:B:C")
        self.assertIsNone(v._problemaEnOrdenDeArranque("C:A:B"))

    def test_un_repetido_se_rechaza(self):
        v = self._ventana("A:B:C")
        problema = v._problemaEnOrdenDeArranque("A:A:B")
        self.assertIsNotNone(problema)
        self.assertIn("dos veces", problema)

    def test_un_faltante_se_rechaza(self):
        v = self._ventana("A:B:C")
        problema = v._problemaEnOrdenDeArranque("A:B")
        self.assertIsNotNone(problema)
        self.assertIn("faltan", problema)

    def test_reordenar_al_azar_nunca_produce_un_orden_invalido(self):
        import random
        dispositivos = ["A", "B", "C", "D", "E"]
        v = self._ventana(":".join(dispositivos))
        actual = list(dispositivos)
        for _vuelta in range(500):
            origen = random.randrange(len(actual))
            destino = max(0, min(len(actual) - 1, origen + random.choice([-1, 1])))
            actual.insert(destino, actual.pop(origen))
            self.assertIsNone(v._problemaEnOrdenDeArranque(":".join(actual)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
