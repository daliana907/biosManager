# BIOS Manager

* Autor: Daliana
* Versión: 1.11.0
* Compatibilidad con NVDA: 2023.1 en adelante
* Descarga de la versión estable: https://github.com/daliana907/biosManager

Este complemento te permite ajustar las configuraciones internas de la placa base (BIOS/UEFI) de tu computadora portátil directamente desde Windows usando el lector de pantalla NVDA, sin tener que navegar por menús visuales inaccesibles durante el arranque del equipo.

La configuración de la BIOS históricamente ha sido una de las barreras de accesibilidad más grandes, ya que la pantalla de arranque del equipo no carga ningún sistema de audio o lector de pantalla. Bios Manager derriba esta barrera conectándose a la interfaz de administración interna de Windows.

Con esta herramienta podrás:

*   Modificar opciones de hardware: Cambiar el comportamiento de los puertos USB, las teclas de función, los pitidos de arranque o las opciones de virtualización. Nota: Secure Boot y TPM están bloqueados por diseño (solo lectura) y no se pueden modificar con este complemento.
*   Editar fechas y horas: Ajustar de manera accesible y segura el reloj interno de la placa base, con protecciones para evitar ingresar fechas no válidas.
*   Alterar el orden de arranque: Ver y cambiar en qué orden el equipo intenta arrancar el sistema operativo (muy útil si necesitas arrancar desde un pendrive o lectora de CD/DVD).
*   Supervisión segura: El complemento filtra respuestas deformadas del sistema, realiza verificaciones en segundo plano y te avisa si el equipo soporta o rechaza los comandos, garantizando que tu placa base no sufra daños por interrupciones.

## Novedades en la versión 1.11.0

*   Ajustes delicados bloqueados por diseño, con confirmación previa antes de guardar.
*   Respaldo previo del estado y limpieza de temporales al terminar.
*   Reinicio a UEFI con 30 segundos para guardar o cancelar.
*   Contraseña protegida y ventana sin congelamientos.

## Cómo usarlo

Puedes acceder a sus funciones directamente desde el menú de herramientas de NVDA, buscando la opción BIOS Manager.
Al abrirlo, la ventana cargará todas las configuraciones disponibles en una lista filtrable y buscable. Al pulsar Enter sobre cualquier opción, se abrirá un menú desplegable, un cuadro de texto numérico o una ventana especial (por ejemplo, para el orden de arranque) dependiendo del tipo de ajuste seleccionado.

Cualquier cambio que realices se guardará primero en una lista de "cambios pendientes". Recién cuando estés seguro y presiones el botón de guardar, el complemento requerirá elevación de permisos (permisos de administrador) para inyectar tus modificaciones directamente en la placa base.

## Seguridad al guardar

*   Antes de guardar, el complemento resume los ajustes pendientes y pide una confirmación adicional.
*   Secure Boot, TPM, presencia física y la contraseña de la BIOS están bloqueados por diseño. Se muestran solo para consulta cuando el firmware los expone.
*   El orden de arranque sigue disponible, pero puede impedir que el equipo arranque si se configura mal. Revísalo antes de aceptar.
*   La contraseña de supervisor, si hace falta, solo se usa durante el guardado: no se guarda en NVDA ni se escribe en el registro.
*   Se prepara una copia temporal del estado antes de guardar y se elimina al terminar, incluso si el firmware rechaza el cambio.
*   Reiniciar en UEFI no fuerza el cierre inmediato de los programas: Windows deja un margen de 30 segundos para guardar el trabajo o cancelar el reinicio con `shutdown /a`.
*   Mientras se guardan cambios, la ventana no se cierra para evitar que una operación quede sin seguimiento.

## Compatibilidad de hardware

Debido a que el acceso a la BIOS varía enormemente entre fabricantes, este complemento está diseñado específicamente para computadoras de marca Lenovo (línea ThinkPad y algunos modelos IdeaPad/Legion) que exponen sus métodos WMI (Windows Management Instrumentation) en el espacio de nombres de Windows. Las funciones de reiniciar en UEFI sí son compatibles con todas las marcas.

## Créditos de terceros

*   Documentación de WMI de Lenovo/Microsoft (https://learn.microsoft.com/en-us/windows/win32/wmisdk). Solo equipos Lenovo con interfaces WMI de proveedor.

## Créditos

Autora: Daliana. Desarrollado en base a los estándares de gestión WMI (https://learn.microsoft.com/en-us/windows/win32/wmisdk) proporcionados por Microsoft.

## Licencia y derechos de autor

Este complemento está protegido por derechos de autor y se distribuye bajo los términos de la Licencia Pública General de GNU (GPL), versión 2 o posterior. Eres libre de usar, modificar y distribuir este software bajo dichas condiciones. Puedes consultar el texto completo de la licencia en: https://www.gnu.org/licenses/gpl-2.0.html

Aclaración sobre el uso de Inteligencia Artificial: Para programar partes de la lógica interna de este complemento y para redactar estos manuales me apoyé en herramientas de Inteligencia Artificial, tal como sugieren declarar las reglas de publicación de NVDA. De todos modos, cada línea de código y cada función fueron dirigidas, revisadas y probadas a fondo por mí.
