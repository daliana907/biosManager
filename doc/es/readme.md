# Gestor de BIOS y UEFI para NVDA (BIOS / UEFI Manager)

- Autora: Daliana
- Versión: 1.9
- Compatibilidad: NVDA 2023.1 en adelante
- Licencia: GNU GPL v2

[Read in English](../en/readme.md)

---

## Versión en Español

Este complemento permite consultar y modificar la configuración del firmware UEFI de tu ordenador directamente desde el escritorio de Windows con NVDA, de forma totalmente accesible.

### ¿Para qué sirve?
Normalmente, para cambiar algo en la configuración del firmware (como el orden de arranque para arrancar desde una unidad USB o activar la virtualización) hay que reiniciar la computadora y pulsar teclas a ciegas en una pantalla visual que no tiene sonido ni lector de pantalla.

Con este complemento no necesitas ayuda visual: abres la ventana dentro de Windows, buscas la opción que quieras con el teclado, haces el cambio y al reiniciar el ordenador la placa base ya tiene la nueva configuración aplicada.

### Tipos de BIOS y compatibilidad
Es fundamental distinguir entre la BIOS clásica y el firmware UEFI:

- La BIOS heredada (Legacy BIOS) no se puede controlar ni modificar desde Windows de forma accesible.
- El firmware UEFI moderno permite la comunicación segura con Windows a través de la interfaz WMI de los fabricantes. Este complemento está diseñado específicamente para interactuar con UEFI.

### Compatibilidad de computadoras
Por la forma en que funciona la comunicación con la placa base en Windows:

- Funciona en: Equipos Lenovo de gama profesional (portátiles ThinkPad, computadoras de escritorio ThinkCentre y estaciones de trabajo ThinkStation).
- No funciona en: Equipos armados por piezas (clónicos) o computadoras portátiles domésticas que no traen el sistema de comunicación WMI del fabricante. Si lo abres en un equipo no compatible, te avisará de forma clara y segura.

### Advertencias de seguridad y uso responsable
Modificar los parámetros del firmware del equipo es una operación delicada:

- Orden de arranque: Desactivar o alterar el orden de las unidades de arranque puede impedir que Windows inicie normalmente.
- Seguridad y virtualización: Modificar parámetros como Secure Boot, TPM, contraseñas de arranque o virtualización (VT-x / AMD-V) puede afectar al cifrado de unidad (como BitLocker) o a la integridad del arranque del sistema. Modifica únicamente los parámetros que conozcas.
- Protección en pantallas seguras: Por razones de seguridad, el complemento bloquea automáticamente su carga en pantallas seguras de Windows (como la pantalla de bloqueo o el Control de cuentas de usuario) para evitar accesos no autorizados con privilegios elevados.

### Opciones y atajos de teclado

El complemento no asigna ningún atajo de teclado por defecto para no interferir con las órdenes nativas de NVDA (por ejemplo, el atajo nativo `NVDA + Shift + B` para verbalizar el estado de la batería).

### Opciones desde el menú de NVDA

En el menú de NVDA > Herramientas > Gestor de BIOS y UEFI:

- Configuración de la BIOS / UEFI...: Abre la ventana principal de ajustes.
- Reiniciar en la configuración de UEFI / BIOS...: Reinicia el sistema directamente en la pantalla de configuración del firmware UEFI.
- Comprobar conflictos con otros complementos...: Comprueba si existen atajos coincidentes o complementos duplicados.

### Asignación de atajos personalizados

Puedes asignar tus propios atajos de teclado en el menú de NVDA > Preferencias > Gestos de entrada, dentro de la categoría "Gestor de BIOS y UEFI".

### Teclas útiles dentro de la ventana de ajustes

- Búsqueda: Escribe el término y pulsa Intro o el botón Filtrar para actualizar la lista. Pulsa Limpiar para restablecerla.
- Orden de arranque: Selecciona un dispositivo de la lista y utiliza Alt + Flecha Arriba o Alt + Flecha Abajo (o los botones Subir y Bajar) para cambiar su posición.
- Confirmar y cancelar: Pulsa Aceptar (o Intro fuera de campos de texto) para aplicar los cambios pendientes en la BIOS, o Cancelar (o Escape) para descartar los cambios en memoria y cerrar.

---

## Novedades de la versión 1.9.1 (13 de septiembre de 2026)

- Mayor ligereza del complemento: se eliminaron dependencias internas que ya no se utilizaban, reduciendo el peso y la complejidad del código cargado por NVDA.
- Documentación técnica interna completa de la comunicación con la BIOS y de todos los controles de la ventana de ajustes.

## Novedades de la versión 1.9 (13 de septiembre de 2026)

- Edición de fechas adaptada a cada ordenador: el editor ahora respeta automáticamente si tu placa base usa barras o guiones para las fechas, evitando avisos falsos de que has cambiado algo al moverte por la lista y asegurando que el equipo acepte la fecha al guardarla.
- Mayor seguridad al escribir fechas con el teclado: no te permite escribir días o meses imposibles (como el 30 de febrero o el mes 13) y calcula correctamente los años bisiestos para que la fecha siempre sea válida y segura.
- Opciones numéricas con valores negativos o automáticos: las opciones del equipo que usan números negativos o códigos automáticos especiales ahora se pueden ajustar cómodamente con las casillas numéricas de la ventana.
- Ventanas más estables: se corrigieron errores que podían ocurrir si se cerraba la ventana mientras se realizaban comprobaciones del sistema.
- Protección total al guardar ajustes en la placa base: la ventana no se puede cerrar accidentalmente ni con Escape mientras se están grabando los cambios en el ordenador, protegiendo la placa base de interrupciones peligrosas.
- Reconocimiento de horas mejorado: el editor de hora valida correctamente los formatos habituales de reloj, impidiendo introducir horas o minutos fuera de rango.
- Búsqueda más rápida: al escribir en el cuadro de búsqueda, la lista se filtra al instante tanto por el nombre de la opción como por su valor, cargando de inmediato el control adecuado para cambiarlo.
- Reinicio a la BIOS más fiable: la opción de reiniciar directamente en la configuración de la BIOS o UEFI comprueba los permisos necesarios y te avisa con claridad si tu equipo admite esta función.
- Limpieza automática del sistema: al instalar o desinstalar el complemento, no queda ningún archivo temporal en el ordenador.

### Créditos y Licencia
- Autora: Daliana.
- Licencia: GNU General Public License v2.
