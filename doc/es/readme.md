# Gestor de BIOS y UEFI para NVDA (BIOS / UEFI Manager)

Autora: Daliana
Versión: 1.7
Compatibilidad: NVDA 2023.1 en adelante
Licencia: GNU GPL v2

[Read in English below](#english-version)

---

## Versión en Español

Este complemento permite consultar y modificar la configuración del firmware UEFI de tu ordenador directamente desde el escritorio de Windows con NVDA, de forma totalmente accesible.

### ¿Para qué sirve?
Normalmente, para cambiar algo en la configuración del firmware (como el orden de arranque para arrancar desde una unidad USB o activar la virtualización) hay que reiniciar la computadora y pulsar teclas a ciegas en una pantalla visual que no tiene sonido ni lector de pantalla.

Con este complemento no necesitas ayuda visual: abres la ventana dentro de Windows, buscas la opción que quieras con el teclado, haces el cambio y al reiniciar el ordenador la placa base ya tendrá tu configuración guardada.

### BIOS heredada frente a UEFI
Es fundamental distinguir entre la BIOS clásica y el firmware UEFI moderno:
- La BIOS heredada (Legacy BIOS) no se puede controlar ni modificar desde el sistema operativo una vez iniciado.
- El firmware UEFI moderno sí permite la comunicación y lectura/escritura de variables de configuración mediante la interfaz WMI de Windows.
- Por tanto, este complemento funciona exclusivamente en sistemas con firmware UEFI nativo. No funcionará en equipos antiguos con BIOS clásica ni en equipos donde se haya activado el módulo de compatibilidad heredada (CSM).

### Compatibilidad de computadoras
Por la forma en que funciona la comunicación con la placa base en Windows:
- Funciona en: Equipos Lenovo de gama profesional (portátiles ThinkPad, computadoras de escritorio ThinkCentre y estaciones de trabajo ThinkStation).
- No funciona en: Equipos armados por piezas (clónicos) o computadoras portátiles domésticas que no traen el sistema de comunicación WMI del fabricante. Si lo abres en un equipo no compatible, te avisará de forma clara y segura.

### Advertencias de seguridad y uso responsable
Modificar los parámetros del firmware del equipo es una operación delicada:
- **Orden de arranque:** Desactivar o alterar el orden de las unidades de arranque puede impedir que Windows inicie normalmente.
- **Seguridad y virtualización:** Modificar parámetros como Secure Boot, TPM, contraseñas de arranque o virtualización (VT-x / AMD-V) puede afectar al cifrado de unidad (como BitLocker) o a la integridad del arranque del sistema. Modifica únicamente los parámetros que conozcas.
- **Protección en pantallas seguras:** Por razones de seguridad, el complemento bloquea automáticamente su carga en pantallas seguras de Windows (como la pantalla de bloqueo o el Control de cuentas de usuario) para evitar accesos no autorizados con privilegios elevados.

### Opciones y atajos de teclado
El complemento no asigna ningún atajo de teclado por defecto para no interferir con las órdenes nativas de NVDA (por ejemplo, el atajo nativo `NVDA + Shift + B` para verbalizar el estado de la batería).

Todas las acciones se encuentran disponibles desde el menú de NVDA y pueden personalizarse con los atajos que desees:
- **Menú NVDA > Herramientas > Gestor de BIOS y UEFI:**
  - *Configuración de la BIOS / UEFI...:* Abre la ventana principal de ajustes.
  - *Reiniciar en la configuración de UEFI / BIOS...:* Reinicia el sistema directamente en la pantalla de configuración del firmware UEFI.
  - *Comprobar conflictos con otros complementos...:* Comprueba si existen atajos coincidentes o complementos duplicados.
  - *Documentación:* Abre esta guía de ayuda.
- **Asignación de atajos:** Puedes asignar tus propios atajos de teclado en el menú de NVDA > Preferencias > Gestos de entrada, dentro de la categoría "Gestor de BIOS y UEFI".
- **Dentro de la ventana de ajustes:**
  - *Búsqueda:* Escribe el término y pulsa `Intro` o el botón *Filtrar* para actualizar la lista. Pulsa *Limpiar* para restablecerla.
  - *Orden de arranque:* Selecciona un dispositivo de la lista y utiliza `Alt + Flecha Arriba` o `Alt + Flecha Abajo` (o los botones *Subir* y *Bajar*) para cambiar su posición.
  - *Confirmar y cancelar:* Pulsa `Aceptar` (o Intro fuera de campos de texto) para aplicar los cambios pendientes en la BIOS, o `Cancelar` (o Escape) para descartar los cambios en memoria y cerrar.

---

## Novedades de la versión 1.7 (12 de septiembre de 2026)

### Seguridad y compatibilidad

- Se anula la carga del complemento en escritorios seguros de Windows para evitar riesgos de elevación de privilegios.
- Se elimina el atajo por defecto `NVDA+Shift+B` para no interferir con la función nativa de lectura de batería de NVDA. Las funciones siguen siendo reasignables en Gestos de entrada.
- Se añade al menú Herramientas la opción para reiniciar directamente en la configuración del firmware UEFI.
- Se utiliza la API oficial de NVDA (`openDocumentation()`) para abrir la documentación en el idioma del usuario.
- Expresión regular con límites de palabra en la auditoría de conflictos para evitar falsos positivos con palabras como "cambios".
- Validación dinámica de fechas según el mes y año (considerando bisiestos y rango estándar 1970-2037).
- Controles numéricos con rango completo de 32 bits con signo (-2147483648 a 2147483647).
- Búsqueda filtrada mediante botón Filtrar o tecla Intro.
- Cancelación limpia sin llamadas innecesarias a la BIOS si no se han enviado cambios.

---

## Novedades de la versión 1.6 (8 de septiembre de 2026)

### Corregido

- Los cambios en la BIOS no llegaban a aplicarse: la orden que se enviaba a Windows estaba mal formada.
- El archivo con la respuesta de la BIOS quedaba en una carpeta que NVDA no siempre podía leer, y la operación parecía fallar sin motivo.
- Al aplicar un cambio se daba por bueno sin comprobarlo. Ahora se vuelve a leer el valor y se informa de si la BIOS lo aceptó o lo rechazó.
- Guardar en la BIOS bloqueaba NVDA hasta terminar. Ahora se hace en segundo plano.
- Al cerrar la ventana con un cambio escrito pero sin aplicar, ese cambio se perdía en silencio. Ahora avisa.
- El orden de arranque se editaba con un desplegable por posición, y se podía repetir un dispositivo y omitir otro sin que nada lo advirtiera.
- Las consultas a la BIOS podían quedarse esperando indefinidamente si el equipo no respondía o si nadie contestaba al aviso de permisos.

### Cambios internos

- El orden de arranque se edita ahora en una sola lista que se reordena con Alt y las flechas, y al aplicar se resume solo lo que cambió de sitio.
- El editor de opciones separa decidir qué tipo de editor toca de construirlo, y esa decisión tiene pruebas propias.
- Se eliminaron unas 119 líneas de código que ya no se usaba.
- Se corrigieron dos problemas de seguridad: un archivo temporal con nombre predecible y valores que se enviaban a Windows sin escapar.
- Se añadieron 52 comprobaciones automáticas que se ejecutan solas en GitHub con cada cambio.

El listado completo de todas las versiones está en el archivo CHANGELOG.md
del repositorio del complemento.
