# -*- coding: utf-8 -*-
# biosManager: Complemento para gestionar parámetros de BIOS/UEFI en NVDA
# Copyright (C) 2026 Daliana
# Este archivo está cubierto por la Licencia Pública General de GNU (GPLv2).
# Consulta el archivo LICENSE para más detalles.

import wx
import addonHandler
addonHandler.initTranslation()
import threading
import re
import calendar
from logHandler import log
import ui

class BiosManagerDialog(wx.Dialog):
	def __init__(self, parent, backend):
		"""Prepara la ventana: memoria de trabajo y botones Aceptar y Cancelar.

		Guarda el puente con la BIOS y crea las tres listas que la ventana usa
		mientras está abierta: todos los ajustes leídos, los que pasan el filtro
		de búsqueda y los cambios que todavía no se han guardado. El contenido
		de la ventana lo monta makeSettings.
		"""
		self.backend = backend
		self._all_settings = []
		self._filtered_settings = []
		self._pending_changes = {}
		# Translators: Título de la ventana principal de configuración de BIOS/UEFI.
		super().__init__(parent, title=_("Configuración de la BIOS / UEFI"), size=(800, 600))
		
		main_sizer = wx.BoxSizer(wx.VERTICAL)
		self.makeSettings(main_sizer)
		
		# Standard Dialog Buttons
		btn_sizer = wx.StdDialogButtonSizer()
		# Translators: Etiqueta del botón Aceptar del diálogo.
		self.btn_ok = wx.Button(self, wx.ID_OK, label=_("&Aceptar"))
		self.btn_ok.Bind(wx.EVT_BUTTON, self.onSave)
		btn_sizer.AddButton(self.btn_ok)
		
		# Translators: Etiqueta del botón Cancelar del diálogo.
		self.btn_cancel = wx.Button(self, wx.ID_CANCEL, label=_("&Cancelar"))
		self.btn_cancel.Bind(wx.EVT_BUTTON, self.onCancel)
		btn_sizer.AddButton(self.btn_cancel)
		
		btn_sizer.Realize()
		self.SetAffirmativeId(wx.ID_OK)
		self.SetEscapeId(wx.ID_CANCEL)
		main_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 10)
		
		self.SetSizer(main_sizer)
		self.CenterOnParent()

	def makeSettings(self, settingsSizer):
		"""Monta el contenido de la ventana, en dos mitades.

		A la izquierda, la casilla de búsqueda, los botones Filtrar y Limpiar,
		y la lista de ajustes con sus tres columnas: nombre, valor actual y
		cambio pendiente. A la derecha, el panel donde aparece el editor del ajuste
		que esté seleccionado. Al final deja el foco en la lista y arranca en
		segundo plano la lectura de la BIOS.
		"""
		# Splitter layout: List on left, Editor on right
		main_hbox = wx.BoxSizer(wx.HORIZONTAL)
		
		# LEFT PANEL (List)
		left_vbox = wx.BoxSizer(wx.VERTICAL)
		
		# Translators: Etiqueta del campo de búsqueda de ajustes.
		lbl_search = wx.StaticText(self, label=_("&Buscar ajuste:"))
		left_vbox.Add(lbl_search, 0, wx.BOTTOM, 4)
		
		search_hbox = wx.BoxSizer(wx.HORIZONTAL)
		self.txt_search = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
		self.txt_search.Bind(wx.EVT_TEXT_ENTER, self._on_search)
		search_hbox.Add(self.txt_search, 1, wx.EXPAND | wx.RIGHT, 5)

		# Translators: Etiqueta del botón para filtrar la lista de ajustes de BIOS.
		self.btn_filter = wx.Button(self, label=_("&Filtrar"))
		self.btn_filter.Bind(wx.EVT_BUTTON, self._on_search)
		search_hbox.Add(self.btn_filter, 0, wx.RIGHT, 5)
		
		# Translators: Etiqueta del botón para limpiar el filtro de búsqueda.
		btn_clear = wx.Button(self, label=_("L&impiar"))
		btn_clear.Bind(wx.EVT_BUTTON, self._on_clear_search)
		search_hbox.Add(btn_clear, 0, wx.EXPAND)
		
		left_vbox.Add(search_hbox, 0, wx.EXPAND | wx.BOTTOM, 10)
		
		# Translators: Etiqueta sobre la lista de ajustes de la BIOS.
		lbl_list = wx.StaticText(self, label=_("&Lista de Ajustes:"))
		left_vbox.Add(lbl_list, 0, wx.BOTTOM, 4)
		
		self.list_ctrl = wx.ListCtrl(
			self,
			style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN
		)
		# Translators: Encabezado de la columna con el nombre del ajuste en la BIOS.
		self.list_ctrl.InsertColumn(0, _("Ajuste"), width=200)
		# Translators: Encabezado de la columna con el valor actual del ajuste.
		self.list_ctrl.InsertColumn(1, _("Valor Actual"), width=150)
		# Translators: Encabezado de la columna con los cambios pendientes de guardar.
		self.list_ctrl.InsertColumn(2, _("Pendiente de guardar"), width=140)
		self.list_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_item_selected)
		
		# Placeholder temporal
		# Translators: Elemento temporal en la lista mientras se leen los ajustes de la BIOS.
		self.list_ctrl.InsertItem(0, _("Cargando opciones de BIOS..."))
		# Translators: Subtexto temporal mientras se leen los ajustes de la BIOS.
		self.list_ctrl.SetItem(0, 1, _("Por favor, espera..."))
		
		left_vbox.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 0)
		main_hbox.Add(left_vbox, 1, wx.EXPAND | wx.RIGHT, 10)
		
		# RIGHT PANEL (Editor)
		self.right_panel = wx.ScrolledWindow(self, style=wx.VSCROLL)
		self.right_panel.SetScrollRate(0, 20)
		self.right_sizer = wx.BoxSizer(wx.VERTICAL)
		self.right_panel.SetSizer(self.right_sizer)
		
		self._clear_editor()
		main_hbox.Add(self.right_panel, 1, wx.EXPAND | wx.ALL, 0)
		
		settingsSizer.Add(main_hbox, 1, wx.EXPAND | wx.ALL, 5)
		
		# Forzar que el foco inicial vaya a la lista
		self.list_ctrl.SetFocus()
		
		# Load data
		threading.Thread(target=self._load_settings_thread, daemon=True).start()

	def _load_settings_thread(self):
		try:
			settings = self.backend.get_all_settings()
		except Exception as e:
			log.error(f"BIOS Manager: Error leyendo los ajustes de la BIOS: {e}", exc_info=True)
			wx.CallAfter(self._on_unsupported)
			return
		wx.CallAfter(self._on_settings_loaded, settings)

	def _on_unsupported(self):
		"""Avisa y cierra el diálogo cuando no se pudo leer ningún ajuste de la BIOS.

		Ocurre sobre todo si se cancela el aviso de permisos de administrador,
		o si el equipo no tiene una BIOS Lenovo accesible por WMI. Antes de esto
		el diálogo se quedaba con la lista vacía y sin decir nada.
		"""
		log.warning("BIOS Manager: No se obtuvo ningún ajuste de la BIOS. Cerrando el diálogo.")
		# Translators: Mensaje cuando no se pueden leer los ajustes de la BIOS del equipo.
		ui.message(_(
			"No se pudieron leer los ajustes de la BIOS. "
			"Puede que hayas cancelado el aviso de permisos de administrador, "
			"o que este equipo no sea compatible."
		))
		self.Destroy()

	def _on_settings_loaded(self, settings):
		if not settings:
			self._on_unsupported()
			return
		self._all_settings = settings
		self._apply_filter("")

	def _apply_filter(self, query):
		q = query.strip().lower()
		if not q:
			self._filtered_settings = list(self._all_settings)
		else:
			self._filtered_settings = [
				s for s in self._all_settings
				if q in s["name"].lower()
			]
		self._populate_list()

	def _populate_list(self):
		"""Vuelve a rellenar la lista de la izquierda con los ajustes filtrados.

		Borra lo que hubiera y escribe una fila por ajuste. El orden de arranque
		se muestra distinto en cada columna para poder distinguirlas: numerado en
		la del valor actual, y solo lo que se movió en la de pendientes. Al
		terminar selecciona la primera fila y vacía el editor.
		"""
		self.list_ctrl.DeleteAllItems()
		for idx, item in enumerate(self._filtered_settings):
			name = item["name"]
			val = item["value"]
			pending = self._pending_changes.get(name, "")

			if name == self.ORDEN_DE_ARRANQUE:
				# El orden de arranque se muestra distinto en cada columna, para poder
				# distinguirlas: a la izquierda el orden actual numerado, y a la
				# derecha solo lo que se movió.
				val = self._resumenOrden(val)
				if pending:
					pending = self._resumenOrdenPendiente(item["value"], pending)

			self.list_ctrl.InsertItem(idx, name)
			self.list_ctrl.SetItem(idx, 1, val)
			self.list_ctrl.SetItem(idx, 2, pending)
			
		if self.list_ctrl.GetItemCount() > 0:
			self.list_ctrl.Select(0)
			self.list_ctrl.Focus(0)
			
		self._clear_editor()

	def _clear_editor(self):
		self.right_sizer.Clear(True)
		# Translators: Texto mostrado en el panel derecho cuando no hay ningún ajuste seleccionado.
		lbl = wx.StaticText(self.right_panel, label=_("Selecciona un ajuste en la lista para editarlo."))
		self.right_sizer.Add(lbl, 0, wx.ALL, 10)
		self.right_panel.Layout()

	def _on_search(self, event):
		self._apply_filter(self.txt_search.GetValue())

	def _on_clear_search(self, event):
		self.txt_search.ChangeValue("")
		self._apply_filter("")
		self.txt_search.SetFocus()

	def _get_focused_setting(self):
		idx = self.list_ctrl.GetFirstSelected()
		if 0 <= idx < len(self._filtered_settings):
			return self._filtered_settings[idx]
		return None

	def _on_item_selected(self, event):
		item = self._get_focused_setting()
		if not item:
			return
		
		name = item["name"]
		val = item["value"]
		
		# Ya tenemos las opciones en caché, así que construimos directamente (sin lag para NVDA)
		opts = self.backend.get_selections(name)
		self._build_editor(name, val, opts)

	def _build_editor(self, name, val, opts):
		"""Dibuja, a la derecha, el editor del ajuste seleccionado.

		Escribe el nombre del ajuste, su valor actual y, si hay un cambio sin
		guardar, también ese cambio. Después pregunta a _tipoDeEditor qué clase de
		control hace falta (lista de arranque, opciones, fecha, hora, número o
		texto) y llama al constructor correspondiente. Abajo pone siempre el botón
		"Añadir a cambios pendientes".
		"""
		self.right_sizer.Clear(True)
		
		pending = self._pending_changes.get(name)
		display_val = pending if pending else val
		
		# Translators: Etiqueta que precede al nombre del ajuste seleccionado.
		lbl_title = wx.StaticText(self.right_panel, label=_("Ajuste: {nombre}").format(nombre=name))
		font = lbl_title.GetFont()
		font.MakeBold()
		lbl_title.SetFont(font)
		self.right_sizer.Add(lbl_title, 0, wx.ALL, 5)
		
		esOrdenDeArranque = (name == self.ORDEN_DE_ARRANQUE)
		textoActual = self._ordenLegible(val) if esOrdenDeArranque else val
		# Translators: Etiqueta que muestra el valor actual del ajuste en la BIOS.
		lbl_val = wx.StaticText(self.right_panel, label=_("Valor actual en sistema: {valor}").format(valor=textoActual))
		self.right_sizer.Add(lbl_val, 0, wx.LEFT | wx.BOTTOM, 5)

		if pending:
			if esOrdenDeArranque:
				movidos = self._soloLoQueSeMovio(val, pending)
				textoPendiente = movidos if movidos else self._ordenLegible(pending)
			else:
				textoPendiente = pending
			# Translators: Etiqueta que muestra el cambio pendiente de guardar.
			lbl_pen = wx.StaticText(self.right_panel, label=_("(Cambio pendiente: {cambio})").format(cambio=textoPendiente))
			lbl_pen.SetForegroundColour(wx.Colour(0, 100, 0))
			self.right_sizer.Add(lbl_pen, 0, wx.LEFT | wx.BOTTOM, 5)
			if esOrdenDeArranque:
				# Translators: Etiqueta que muestra cómo quedaría el orden de arranque.
				lbl_nuevo = wx.StaticText(self.right_panel, label=_("Quedaría así: {orden}").format(orden=self._ordenConCambios(val, pending)))
				self.right_sizer.Add(lbl_nuevo, 0, wx.LEFT | wx.BOTTOM, 5)
		
		self._current_edit_name = name
		self.editor_type = self._tipoDeEditor(name, display_val, opts)

		if self.editor_type == "bootorder_list":
			self._editorDeOrdenDeArranque(display_val)
		elif self.editor_type == "choice":
			self._editorDeOpciones(display_val, opts)
		elif self.editor_type == "date":
			self._editorDeFecha(display_val)
		elif self.editor_type == "time":
			self._editorDeHora(display_val)
		elif self.editor_type == "spin":
			self._editorDeNumero(display_val)
		else:
			self._editorDeTexto(display_val)

		# Translators: Botón para añadir la modificación actual a los cambios pendientes.
		self.btn_apply = wx.Button(self.right_panel, label=_("&Añadir a cambios pendientes"))
		self.btn_apply.Bind(wx.EVT_BUTTON, self._on_apply)
		self.right_sizer.Add(self.btn_apply, 0, wx.ALL | wx.ALIGN_RIGHT, 5)

		self.right_panel.Layout()

	def _tipoDeEditor(self, name, display_val, opts):
		"""Decide qué clase de editor pide un ajuste, mirando cómo es su valor y opciones.

		Devuelve una de estas palabras: bootorder_list, choice, date, time, spin o text.
		Si existen opciones predefinidas y hay más de una, o hay una y el valor actual
		está vacío, se ofrece la lista desplegable.
		"""
		if name == self.ORDEN_DE_ARRANQUE:
			return "bootorder_list"
		if opts:
			if len(opts) > 1:
				return "choice"
			if len(opts) == 1 and display_val.strip() != opts[0]:
				return "choice"
		texto = display_val.strip()
		if re.match(r'^\d{4}[/-]\d{2}[/-]\d{2}$', texto):
			return "date"
		if re.match(r'^\d{2}:\d{2}:\d{2}$', texto):
			return "time"
		if texto.isdigit():
			return "spin"
		return "text"

	def _editorDeOrdenDeArranque(self, display_val):
		"""Lista reordenable con los dispositivos de arranque."""
		self.editor_type = "bootorder_list"
		dispositivos = [d for d in display_val.split(":") if d.strip()]
		self._bootOriginal = list(dispositivos)

		# Translators: Instrucción sobre la lista de dispositivos de arranque.
		lbl = wx.StaticText(self.right_panel, label=_(
			"&Orden de arranque. Usa Alt más flecha arriba o abajo para mover el dispositivo elegido:"
		))
		self.right_sizer.Add(lbl, 0, wx.TOP | wx.LEFT, 5)

		self.boot_list = wx.ListBox(self.right_panel, choices=dispositivos, style=wx.LB_SINGLE)
		if dispositivos:
			self.boot_list.SetSelection(0)
		self.boot_list.Bind(wx.EVT_KEY_DOWN, self._on_boot_key)
		self.right_sizer.Add(self.boot_list, 1, wx.EXPAND | wx.ALL, 5)

		fila = wx.BoxSizer(wx.HORIZONTAL)
		# Translators: Botón para subir un elemento en el orden de arranque.
		self.btn_subir = wx.Button(self.right_panel, label=_("S&ubir"))
		self.btn_subir.Bind(wx.EVT_BUTTON, lambda evt: self._moverArranque(-1))
		fila.Add(self.btn_subir, 0, wx.RIGHT, 5)
		# Translators: Botón para bajar un elemento en el orden de arranque.
		self.btn_bajar = wx.Button(self.right_panel, label=_("Ba&jar"))
		self.btn_bajar.Bind(wx.EVT_BUTTON, lambda evt: self._moverArranque(1))
		fila.Add(self.btn_bajar, 0, 0)
		self.right_sizer.Add(fila, 0, wx.ALL, 5)

	def _editorDeOpciones(self, display_val, opts):
		"""Desplegable con los valores que admite el ajuste."""
		# Translators: Etiqueta para el selector de opciones.
		lbl = wx.StaticText(self.right_panel, label=_("Elige el nuevo valor:"))
		self.right_sizer.Add(lbl, 0, wx.TOP | wx.LEFT, 5)
		opciones = list(opts) if opts else []
		if display_val and display_val not in opciones:
			opciones.insert(0, display_val)
		elif not opciones:
			opciones = [display_val] if display_val else [""]
		self.ctrl = wx.Choice(self.right_panel, choices=opciones)
		if display_val in opciones:
			self.ctrl.SetStringSelection(display_val)
		else:
			self.ctrl.SetSelection(0)
		self.right_sizer.Add(self.ctrl, 0, wx.EXPAND | wx.ALL, 5)

	def _diasEnMes(self, anio, mes):
		"""Calcula los días válidos para un año y mes dados."""
		try:
			return calendar.monthrange(int(anio), int(mes))[1]
		except Exception:
			return 31

	def _actualizarDiasDelMes(self, event=None):
		"""Ajusta el rango del control de días según el año y mes seleccionados."""
		try:
			y = self.sp_year.GetValue()
			m = self.sp_month.GetValue()
			max_dias = self._diasEnMes(y, m)
			self.sp_day.SetRange(1, max_dias)
			if self.sp_day.GetValue() > max_dias:
				self.sp_day.SetValue(max_dias)
		except (AttributeError, RuntimeError):
			pass
		if event:
			event.Skip()

	def _editorDeFecha(self, display_val):
		"""Tres casillas numéricas: año, mes y día."""
		# Translators: Etiqueta para el editor de fecha.
		lbl = wx.StaticText(self.right_panel, label=_("Fecha (Año, Mes, Día):"))
		self.right_sizer.Add(lbl, 0, wx.TOP | wx.LEFT, 5)
		parts = re.split(r'[/-]', display_val.strip())
		anio = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 2026
		mes = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
		dia = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1

		# Rango estándar BIOS/UEFI: 1970 a 2037
		anio = max(1970, min(2037, anio))
		mes = max(1, min(12, mes))
		max_dias = self._diasEnMes(anio, mes)
		dia = max(1, min(max_dias, dia))
		
		row = wx.BoxSizer(wx.HORIZONTAL)
		self.sp_year = wx.SpinCtrl(self.right_panel, value=str(anio), min=1970, max=2037, size=(70, -1))
		self.sp_month = wx.SpinCtrl(self.right_panel, value=str(mes), min=1, max=12, size=(50, -1))
		self.sp_day = wx.SpinCtrl(self.right_panel, value=str(dia), min=1, max=max_dias, size=(50, -1))

		self.sp_year.Bind(wx.EVT_SPINCTRL, self._actualizarDiasDelMes)
		self.sp_year.Bind(wx.EVT_TEXT, self._actualizarDiasDelMes)
		self.sp_month.Bind(wx.EVT_SPINCTRL, self._actualizarDiasDelMes)
		self.sp_month.Bind(wx.EVT_TEXT, self._actualizarDiasDelMes)
		
		row.Add(self.sp_year, 0, wx.RIGHT, 5)
		row.Add(self.sp_month, 0, wx.RIGHT, 5)
		row.Add(self.sp_day, 0, 0)
		self.right_sizer.Add(row, 0, wx.ALL, 5)

	def _editorDeHora(self, display_val):
		"""Tres casillas numéricas: hora, minuto y segundo."""
		# Translators: Etiqueta para el editor de hora.
		lbl = wx.StaticText(self.right_panel, label=_("Hora (Hora, Minuto, Segundo):"))
		self.right_sizer.Add(lbl, 0, wx.TOP | wx.LEFT, 5)
		parts = display_val.strip().split(':')
		
		row = wx.BoxSizer(wx.HORIZONTAL)
		self.sp_h = wx.SpinCtrl(self.right_panel, value=parts[0], min=0, max=23, size=(50, -1))
		self.sp_m = wx.SpinCtrl(self.right_panel, value=parts[1], min=0, max=59, size=(50, -1))
		self.sp_s = wx.SpinCtrl(self.right_panel, value=parts[2], min=0, max=59, size=(50, -1))
		
		row.Add(self.sp_h, 0, wx.RIGHT, 5)
		row.Add(self.sp_m, 0, wx.RIGHT, 5)
		row.Add(self.sp_s, 0, 0)
		self.right_sizer.Add(row, 0, wx.ALL, 5)

	def _editorDeNumero(self, display_val):
		"""Una casilla numérica de 32 bits con signo."""
		# Translators: Etiqueta para el editor de valor numérico.
		lbl = wx.StaticText(self.right_panel, label=_("Valor numérico:"))
		self.right_sizer.Add(lbl, 0, wx.TOP | wx.LEFT, 5)
		try:
			val_int = int(display_val.strip())
		except (ValueError, TypeError):
			val_int = 0
		val_int = max(-2147483648, min(2147483647, val_int))
		self.ctrl = wx.SpinCtrl(self.right_panel, value=str(val_int), min=-2147483648, max=2147483647)
		self.right_sizer.Add(self.ctrl, 0, wx.EXPAND | wx.ALL, 5)

	def _editorDeTexto(self, display_val):
		"""Un campo de texto libre, para cuando no encaja nada más."""
		# Translators: Etiqueta para el editor de texto libre.
		lbl = wx.StaticText(self.right_panel, label=_("Texto libre:"))
		self.right_sizer.Add(lbl, 0, wx.TOP | wx.LEFT, 5)
		self.ctrl = wx.TextCtrl(self.right_panel, value=display_val)
		self.right_sizer.Add(self.ctrl, 0, wx.EXPAND | wx.ALL, 5)


	ORDEN_DE_ARRANQUE = "BootOrder"

	@staticmethod
	def _ordenLegible(valor):
		"""Convierte 'A:B:C' en '1, A. 2, B. 3, C.', que con lector de pantalla se
		sigue sin perder la cuenta, en vez de seis nombres pegados con dos puntos.
		"""
		partes = [d.strip() for d in valor.split(":") if d.strip()]
		if not partes:
			return valor
		return ". ".join(f"{i + 1}, {d}" for i, d in enumerate(partes)) + "."

	@staticmethod
	def _resumenOrden(valor):
		"""Una línea corta para la lista de ajustes: qué arranca primero y cuántos hay.

		El orden completo se lee en el panel de la derecha; en la fila sería un
		chorizo de seis nombres que hay que escuchar entero cada vez que se pasa por
		encima del ajuste.
		"""
		partes = [d.strip() for d in valor.split(":") if d.strip()]
		if not partes:
			return valor
		if len(partes) == 1:
			# Translators: Resumen para la lista cuando solo hay un dispositivo de arranque.
			return _("Solo {dispositivo}.").format(dispositivo=partes[0])
		# Translators: Resumen para la lista de arranque con primer dispositivo y total.
		return _("Primero {dispositivo}. {total} dispositivos.").format(
			dispositivo=partes[0], total=len(partes),
		)

	@staticmethod
	def _resumenOrdenPendiente(antes, despues):
		"""Lo mismo para la columna de lo pendiente, con palabras que la distinguen.

		Dice "Quedaría", que la columna de la BIOS nunca dice, así que las dos no se
		pueden confundir aunque nombren el mismo dispositivo.
		"""
		a = [d.strip() for d in antes.split(":") if d.strip()]
		b = [d.strip() for d in despues.split(":") if d.strip()]
		if not b:
			return despues
		# Translators: Resumen del primer dispositivo en el nuevo orden pendiente.
		texto = _("Quedaría primero {dispositivo}.").format(dispositivo=b[0])
		if sorted(a) == sorted(b):
			movidos = sum(1 for d in b if a.index(d) != b.index(d))
			if movidos:
				# Translators: Detalle de cuántos dispositivos cambiaron de puesto.
				texto += " " + _("{total} cambian de puesto.").format(total=movidos)
		return texto

	@staticmethod
	def _ordenConCambios(antes, despues):
		"""El orden nuevo, numerado, marcando de dónde venía cada uno que se movió.

		Este es el distintivo: la columna de lo que hay hoy en la BIOS nunca lleva
		esas marcas de "antes", así que las dos columnas no se pueden confundir por
		mucho que tengan los mismos nombres.
		"""
		a = [d.strip() for d in antes.split(":") if d.strip()]
		b = [d.strip() for d in despues.split(":") if d.strip()]
		if not b:
			return despues
		partes = []
		for puesto, dispositivo in enumerate(b, start=1):
			if dispositivo in a and a.index(dispositivo) + 1 != puesto:
				# Translators: Detalle de dispositivo con su puesto nuevo y su posición anterior.
				partes.append(_("{puesto}, {dispositivo}, antes {anterior}").format(
					puesto=puesto, dispositivo=dispositivo, anterior=a.index(dispositivo) + 1,
				))
			else:
				partes.append(f"{puesto}, {dispositivo}")
		return ". ".join(partes) + "."

	@staticmethod
	def _soloLoQueSeMovio(antes, despues):
		"""Solo los dispositivos que cambiaron de puesto, para decirlo en voz alta.

		No intenta adivinar qué movimientos hiciste: dice, sin interpretar, cuáles
		quedaron en un puesto distinto y de dónde venían.
		"""
		a = [d.strip() for d in antes.split(":") if d.strip()]
		b = [d.strip() for d in despues.split(":") if d.strip()]
		if not a or sorted(a) != sorted(b):
			return ""
		# Translators: Dispositivo movido con su posición actual y anterior.
		return ". ".join(
			_("{dispositivo}, ahora {puesto}, antes {anterior}").format(
				dispositivo=d, puesto=b.index(d) + 1, anterior=a.index(d) + 1,
			)
			for d in b if a.index(d) != b.index(d)
		)

	def _on_boot_key(self, event):
		"""Alt+flecha arriba y Alt+flecha abajo mueven el dispositivo elegido."""
		if event.AltDown() and event.GetKeyCode() == wx.WXK_UP:
			self._moverArranque(-1)
		elif event.AltDown() and event.GetKeyCode() == wx.WXK_DOWN:
			self._moverArranque(1)
		else:
			event.Skip()

	def _moverArranque(self, desplazamiento):
		"""Sube o baja un puesto el dispositivo elegido y lo dice en voz alta."""
		try:
			lista = self.boot_list
			origen = lista.GetSelection()
			total = lista.GetCount()
		except (AttributeError, RuntimeError):
			return
		if origen == wx.NOT_FOUND:
			# Translators: Mensaje cuando se intenta mover sin haber seleccionado un dispositivo.
			ui.message(_("Elige primero un dispositivo de la lista."))
			return
		destino = origen + desplazamiento
		nombre = lista.GetString(origen)
		if destino < 0 or destino >= total:
			# Translators: Extremo superior de la lista.
			extremoPrincipio = _("al principio")
			# Translators: Extremo inferior de la lista.
			extremoFinal = _("al final")
			# Translators: Mensaje cuando un dispositivo ya está en el límite superior o inferior.
			ui.message(_("{dispositivo} ya está {extremo} de la lista.").format(
				dispositivo=nombre,
				extremo=extremoPrincipio if desplazamiento < 0 else extremoFinal,
			))
			return
		lista.Delete(origen)
		lista.Insert(nombre, destino)
		lista.SetSelection(destino)
		lista.SetFocus()
		# Translators: Notificación hablada con la nueva posición de un dispositivo de arranque.
		ui.message(_("{dispositivo}, posición {puesto} de {total}.").format(
			dispositivo=nombre, puesto=destino + 1, total=total,
		))

	def _problemaEnOrdenDeArranque(self, val):
		"""Última red antes de mandarle a la BIOS un orden de arranque estropeado.

		Con la lista de Subir y Bajar no debería fallar nunca, porque solo se
		reordena lo que ya había. Devuelve el texto del problema, o None si está bien.
		"""
		nuevos = [d for d in val.split(":") if d.strip()]
		originales = list(getattr(self, "_bootOriginal", []))
		if not originales or sorted(nuevos) == sorted(originales):
			return None
		repetidos = sorted({d for d in nuevos if nuevos.count(d) > 1})
		faltantes = sorted(set(originales) - set(nuevos))
		detalles = []
		if repetidos:
			# Translators: Detalle de dispositivos duplicados en el orden de arranque.
			detalles.append(_("aparecen dos veces: {}").format(", ".join(repetidos)))
		if faltantes:
			# Translators: Detalle de dispositivos omitidos en el orden de arranque.
			detalles.append(_("faltan: {}").format(", ".join(faltantes)))
		# Translators: Texto alternativo si la lista de arranque difiere sin especificar.
		sinDetalles = _("la lista quedó distinta")
		# Translators: Mensaje de error si la validación del orden de arranque detecta incoherencias.
		return _(
			"No se puede guardar este orden de arranque porque no coincide con los "
			"dispositivos del equipo ({})."
		).format("; ".join(detalles) or sinDetalles)

	def _valorDelEditor(self):
		"""Devuelve el valor que muestra ahora mismo el editor de la derecha.

		Devuelve None si no hay editor abierto o si sus controles ya se destruyeron
		(pasa cuando se recarga la lista).
		"""
		try:
			if self.editor_type == "choice":
				val = self.ctrl.GetStringSelection()
			elif self.editor_type == "bootorder_list":
				val = ":".join(
					self.boot_list.GetString(i) for i in range(self.boot_list.GetCount())
				)
			elif self.editor_type == "date":
				y = self.sp_year.GetValue()
				m = self.sp_month.GetValue()
				max_dias = self._diasEnMes(y, m)
				d = min(self.sp_day.GetValue(), max_dias)
				val = f"{str(y).zfill(4)}/{str(m).zfill(2)}/{str(d).zfill(2)}"
			elif self.editor_type == "time":
				h = str(self.sp_h.GetValue()).zfill(2)
				m = str(self.sp_m.GetValue()).zfill(2)
				s = str(self.sp_s.GetValue()).zfill(2)
				val = f"{h}:{m}:{s}"
			elif self.editor_type == "spin":
				val = str(self.ctrl.GetValue())
			else:
				val = self.ctrl.GetValue().strip()
		except (AttributeError, RuntimeError):
			return None
		return val

	def _cambioSinAnadir(self):
		"""Devuelve (nombre, valor) si el editor abierto tiene un valor distinto al que
		tiene el sistema y que todavía NO se añadió a los cambios pendientes.

		Sirve para no perder en silencio un cambio que se hizo en el desplegable pero
		sin pulsar el botón de añadir.
		"""
		name = getattr(self, "_current_edit_name", None)
		if not name:
			return None
		val = self._valorDelEditor()
		if not val:
			return None
		if self._pending_changes.get(name) == val:
			return None
		valorDelSistema = next((s["value"] for s in self._all_settings if s["name"] == name), None)
		if valorDelSistema is None or val == valorDelSistema:
			return None
		return name, val

	def _on_apply(self, event):
		"""Apunta el valor del editor como cambio pendiente. Todavía no toca la BIOS.

		Comprueba primero que el valor sirva; en el orden de arranque, que no falte
		ni sobre ninguna entrada. Si el valor es igual al que ya tiene el sistema,
		lo notifica y no lo añade como pendiente (o lo retira si estaba).
		"""
		name = self._current_edit_name
		val = self._valorDelEditor()

		if not val:
			return

		if self.editor_type == "bootorder_list":
			problema = self._problemaEnOrdenDeArranque(val)
			if problema:
				log.warning(f"BIOS Manager: Orden de arranque rechazado: {val}")
				ui.message(problema)
				return

		valorDelSistema = next((s["value"] for s in self._all_settings if s["name"] == name), None)
		if valorDelSistema is not None and val == valorDelSistema:
			if name in self._pending_changes:
				del self._pending_changes[name]
				idx = self.list_ctrl.GetFirstSelected()
				if idx != -1:
					self.list_ctrl.SetItem(idx, 2, "")
			# Translators: Mensaje cuando el valor seleccionado es idéntico al actual en el sistema.
			ui.message(_("El ajuste {ajuste} ya tiene ese valor en el sistema.").format(ajuste=name))
			return

		self._pending_changes[name] = val
		log.info(f"BIOS Manager: Ajuste marcado como pendiente: {name} = '{val}' (Total pendientes: {len(self._pending_changes)})")
		if name == self.ORDEN_DE_ARRANQUE:
			# Leer el orden entero pegado con dos puntos no se entiende. Se dice qué
			# se movió, que es lo que la persona acaba de cambiar.
			actual = next((a["value"] for a in self._all_settings if a["name"] == name), "")
			movidos = self._soloLoQueSeMovio(actual, val)
			# Translators: Mensaje al añadir cambios en el orden de arranque.
			msg = _("Pendiente en el orden de arranque: {cambios}").format(
				cambios=movidos if movidos else self._ordenLegible(val)
			)
		else:
			# Translators: Mensaje cuando se añade un cambio de ajuste a la lista de pendientes.
			msg = _("Pendiente: {ajuste} a {valor}").format(ajuste=name, valor=val)
		log.info(f"BIOS Manager: Anunciando al usuario: '{msg}'")
		ui.message(msg)
		
		# Update list
		idx = self.list_ctrl.GetFirstSelected()
		if idx != -1:
			if name == self.ORDEN_DE_ARRANQUE:
				actualEnBios = next((a["value"] for a in self._all_settings if a["name"] == name), "")
				textoCelda = self._resumenOrdenPendiente(actualEnBios, val)
			else:
				textoCelda = val
			self.list_ctrl.SetItem(idx, 2, textoCelda)
		
		ajuste = next((a for a in self._all_settings if a["name"] == name), None)
		if ajuste is not None:
			self._build_editor(name, ajuste["value"], ajuste.get("options", []))
		self.list_ctrl.SetFocus()

	def onSave(self, event=None):
		"""Botón Aceptar: manda a la BIOS todos los cambios pendientes.

		Antes comprueba dos cosas: que no haya un guardado en marcha, y que no
		quede un valor escrito en el editor sin haber pulsado "Añadir a cambios
		pendientes". Si no hay nada pendiente, lo dice y cierra. Si lo hay,
		desactiva los botones y lanza el guardado en segundo plano con permisos
		de administrador.
		"""
		if getattr(self, "_guardando", False):
			# Translators: Aviso al intentar guardar cuando ya hay un guardado en curso.
			ui.message(_("Se están aplicando los cambios en la BIOS. Espera a que termine."))
			return

		sinAnadir = self._cambioSinAnadir()
		if sinAnadir:
			name, val = sinAnadir
			log.info(f"BIOS Manager: Aceptar pulsado con un cambio sin añadir: {name} = '{val}'. No se cierra el diálogo.")
			# Translators: Aviso cuando hay modificaciones en el editor sin añadir a la lista de cambios.
			ui.message(_(
				"Has cambiado {ajuste} a {valor}, pero todavía no lo has añadido a los cambios pendientes. "
				"Pulsa el botón Añadir a cambios pendientes, o Cancelar para descartarlo."
			).format(ajuste=name, valor=val))
			try:
				self.btn_apply.SetFocus()
			except (AttributeError, RuntimeError):
				pass
			return

		if not self._pending_changes:
			log.info("BIOS Manager: Diálogo cerrado con Aceptar sin cambios pendientes.")
			# Translators: Mensaje cuando no hay cambios que guardar al pulsar Aceptar.
			ui.message(_("No hay cambios que guardar."))
			self.Destroy()
			return
		
		cambios = dict(self._pending_changes)
		log.info(f"BIOS Manager: Guardando {len(cambios)} cambio(s) en BIOS (en segundo plano)...")
		self._guardando = True
		for boton in ("btn_ok", "btn_cancel"):
			try:
				getattr(self, boton).Disable()
			except (AttributeError, RuntimeError):
				pass
		# Translators: Notificación de inicio de aplicación de cambios en la BIOS.
		ui.message(_("Aplicando los cambios en la BIOS. Puede tardar unos segundos; te aviso al terminar."))
		threading.Thread(target=self._guardarEnSegundoPlano, args=(cambios,), daemon=True).start()

	def _guardarEnSegundoPlano(self, cambios):
		"""Aplica los cambios sin bloquear NVDA. Corre en un hilo aparte."""
		try:
			ok, msg = self.backend.apply_settings(cambios)
		except Exception as e:
			log.error(f"BIOS Manager: Error inesperado al aplicar los cambios: {e}", exc_info=True)
			# Translators: Mensaje de error cuando ocurre una excepción inesperada guardando en la BIOS.
			ok, msg = False, _("Hubo un error inesperado al aplicar los cambios. Revisa el registro de NVDA.")
		wx.CallAfter(self._alTerminarDeGuardar, ok, msg)

	def _alTerminarDeGuardar(self, ok, msg):
		"""Muestra el resultado y cierra. Vuelve al hilo de la ventana con CallAfter."""
		self._guardando = False
		log.info(f"BIOS Manager: Informe de la BIOS: {msg}")
		if ok:
			# Translators: Título del diálogo informativo tras aplicar cambios con éxito.
			wx.MessageBox(msg, _("Cambios aplicados"), wx.OK | wx.ICON_INFORMATION)
		else:
			# Translators: Título del diálogo de advertencia cuando la BIOS rechazó cambios.
			wx.MessageBox(msg, _("La BIOS no aceptó todos los cambios"), wx.OK | wx.ICON_WARNING)

		self._pending_changes.clear()
		self.Destroy()

	def onCancel(self, event=None):
		"""Cierra la ventana descartando los cambios pendientes en memoria."""
		if getattr(self, "_guardando", False):
			# Translators: Aviso al intentar cancelar mientras se aplican cambios en la BIOS.
			ui.message(_("Se están aplicando los cambios en la BIOS. Espera a que termine."))
			return
		if self._pending_changes:
			log.info(f"BIOS Manager: Cancelando diálogo y descartando {len(self._pending_changes)} cambio(s) pendientes de la memoria.")
			self._pending_changes.clear()
		else:
			log.info("BIOS Manager: Diálogo cerrado con Cancelar.")
		self.Destroy()
