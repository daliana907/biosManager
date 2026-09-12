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
sys.path.insert(0, os.path.join(RAIZ, "globalPlugins"))
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


class TipoDeEditorSegunElValor(unittest.TestCase):
    """El diálogo elige qué editor mostrar mirando cómo es el valor actual.

    Antes esa decisión estaba enredada con la construcción de cada editor, en
    una cascada de sesenta líneas donde no se podía comprobar por separado.
    """

    def tipo(self, nombre, valor, opciones=None):
        # se pasa la clase como 'self': el método solo consulta una constante
        return Ventana._tipoDeEditor(Ventana, nombre, valor, opciones)

    def test_el_orden_de_arranque_usa_la_lista_reordenable(self):
        self.assertEqual(self.tipo("BootOrder", "NVMe0:USBHDD"), "bootorder_list")
        self.assertEqual(self.tipo("BootOrder", ""), "bootorder_list")

    def test_con_varias_opciones_usa_un_desplegable(self):
        self.assertEqual(self.tipo("SecureBoot", "Enable", ["Enable", "Disable"]),
                         "choice")

    def test_con_una_sola_opcion_no_usa_desplegable(self):
        """Un desplegable de un solo elemento no deja elegir nada."""
        self.assertNotEqual(self.tipo("SecureBoot", "Enable", ["Enable"]), "choice")

    def test_reconoce_fechas_y_horas(self):
        for valor in ("2026-09-08", "2026/09/08", "1999/12/31"):
            with self.subTest(valor=valor):
                self.assertEqual(self.tipo("SystemDate", valor), "date")
        for valor in ("10:30:00", "23:59:59", "00:00:00"):
            with self.subTest(valor=valor):
                self.assertEqual(self.tipo("SystemTime", valor), "time")

    def test_lo_que_solo_parece_fecha_u_hora_no_cuenta(self):
        """Una fecha con un dígito de menos no la entiende el editor de fechas."""
        for valor in ("2026-9-8", "10:30", "2026-09", "8/9/2026"):
            with self.subTest(valor=valor):
                self.assertIn(self.tipo("X", valor), ("text", "spin"))

    def test_los_numeros_usan_casilla_numerica(self):
        for valor in ("1234", " 42 ", "0", "007"):
            with self.subTest(valor=valor):
                self.assertEqual(self.tipo("X", valor), "spin")

    def test_lo_demas_es_texto_libre(self):
        for valor in ("texto libre", "", "  ", "abc123", "-5"):
            with self.subTest(valor=valor):
                self.assertEqual(self.tipo("X", valor), "text")

    def test_siempre_devuelve_uno_de_los_seis_tipos(self):
        conocidos = {"bootorder_list", "choice", "date", "time", "spin", "text"}
        for nombre in ("X", "BootOrder", ""):
            for valor in ("", "abc", "12", "2026-01-01", "1:2:3", "a:b:c"):
                for opciones in (None, [], ["uno"], ["uno", "dos"]):
                    with self.subTest(nombre=nombre, valor=valor, opciones=opciones):
                        self.assertIn(self.tipo(nombre, valor, opciones), conocidos)


class ValidacionDeFecha(unittest.TestCase):
    """El cálculo de días por mes debe considerar años bisiestos y meses de 30/31 días."""

    def test_febrero_bisiesto(self):
        self.assertEqual(Ventana._diasEnMes(Ventana, 2024, 2), 29)

    def test_febrero_no_bisiesto(self):
        self.assertEqual(Ventana._diasEnMes(Ventana, 2025, 2), 28)

    def test_meses_de_30_dias(self):
        for mes in (4, 6, 9, 11):
            with self.subTest(mes=mes):
                self.assertEqual(Ventana._diasEnMes(Ventana, 2026, mes), 30)

    def test_meses_de_31_dias(self):
        for mes in (1, 3, 5, 7, 8, 10, 12):
            with self.subTest(mes=mes):
                self.assertEqual(Ventana._diasEnMes(Ventana, 2026, mes), 31)


class AuditoriaDeConflictosRegex(unittest.TestCase):
    """La comprobación de complementos de BIOS no debe dar falsos positivos con 'cambios'."""

    PATRON = r'\b(bios|uefi)\b'

    def test_no_coincide_con_cambios(self):
        import re
        falsos_positivos = [
            "Gestor de cambios del sistema",
            "Notificador de cambios de estado",
            "Herramienta para registrar cambios",
            "Control de cambios y versiones",
        ]
        for texto in falsos_positivos:
            with self.subTest(texto=texto):
                self.assertIsNone(re.search(self.PATRON, texto, re.IGNORECASE))

    def test_coincide_con_bios_y_uefi_reales(self):
        import re
        reales = [
            "Configuración avanzada de BIOS para NVDA",
            "Gestor de firmware UEFI",
            "bios settings utility",
            "Herramienta UEFI y arranque",
        ]
        for texto in reales:
            with self.subTest(texto=texto):
                self.assertIsNotNone(re.search(self.PATRON, texto, re.IGNORECASE))


class SeguridadYAtajos(unittest.TestCase):
    """Comprobaciones de seguridad (modo seguro) y de ausencia de atajo conflictivo por defecto."""

    def test_bloquea_carga_en_modo_seguro(self):
        import globalVars
        import globalPluginHandler
        import biosManager as pluginMod
        globalVars.appArgs.secureMode = True
        try:
            with self.assertRaises(globalPluginHandler.ActionCancelled):
                pluginMod.GlobalPlugin()
        finally:
            globalVars.appArgs.secureMode = False

    def test_sin_atajo_por_defecto_para_no_pisar_bateria(self):
        import biosManager as pluginMod
        # NVDA+Shift+B es el comando nativo de batería en NVDA; script_openBiosManager
        # no debe tener ningún gesto asignado por defecto en el código.
        gesto = getattr(pluginMod.GlobalPlugin.script_openBiosManager, "gesture", None)
        self.assertIsNone(gesto)


if __name__ == "__main__":
    unittest.main(verbosity=2)
