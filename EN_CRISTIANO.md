# BIOS Manager, explicado en cristiano

Esto es para cualquiera que quiera saber qué hace este complemento antes de
instalarlo, sin necesidad de saber programar.

## ¿Para qué sirve?

La BIOS es la pantalla de configuración que aparece antes de que arranque
Windows, donde se cambian cosas como el orden de arranque, si el teclado
numérico empieza encendido o el comportamiento del lector de huellas. Esa
pantalla **no es accesible con lector de pantalla** en la inmensa mayoría de los
equipos: no habla, y sin ver no hay forma de saber dónde está el cursor.

Este complemento trae esos mismos ajustes a una ventana normal de NVDA, que sí
se puede leer y navegar con el teclado.

## ¿Funciona en cualquier equipo?

No. Solo en equipos **Lenovo** (ThinkPad, ThinkCentre y familias parecidas),
porque Lenovo es el fabricante que publica una forma de hacer esto desde
Windows. En otro equipo el complemento se da cuenta y lo dice; no intenta nada
raro.

## ¿Pide permisos de administrador?

Sí, y es importante entender por qué.

Cambiar la BIOS es una operación delicada en cualquier ordenador del mundo:
Windows exige permisos de administrador para hacerlo, no es un capricho de este
complemento. Leer los ajustes también los pide, porque Lenovo solo entrega la
lista completa a un programa con permisos.

Lo que importa es esto: **el complemento nunca pide permisos por su cuenta**.
El aviso de Windows sale siempre después de algo que tú hiciste — abrir la
ventana de ajustes, o pulsar Aceptar para guardar. Si el aviso aparece sin que
hayas hecho nada, no es este complemento.

Y si no lo aceptas, no pasa nada: espera dos minutos, y si no hay respuesta lo
deja y te lo dice.

## ¿Se conecta a internet?

No. Nunca. Ni una sola vez, ni para nada.

No descarga actualizaciones, no manda estadísticas, no consulta ningún servidor.
Si te quedas sin internet, el complemento funciona exactamente igual.

## ¿Guarda algo en mi equipo?

No guarda ninguna configuración. Los cambios que preparas viven solo en la
memoria mientras la ventana está abierta; si cierras con Cancelar, desaparecen.

Mientras habla con la BIOS crea un par de archivos temporales, y los borra él
mismo al terminar, aunque algo falle por el camino.

## ¿Y si me equivoco y estropeo algo?

Está pensado precisamente para eso.

Los cambios **no se mandan a la BIOS según los vas haciendo**. Se van guardando
en una lista de pendientes que puedes ver, y solo llegan al equipo cuando pulsas
Aceptar. Hasta ese momento, Cancelar lo deshace todo.

Además, el orden de arranque se revisa antes de mandarlo: si falta un
dispositivo o hay alguno repetido, no lo acepta y te dice qué pasa.

Y si escribes un valor pero se te olvida añadirlo a los pendientes, al pulsar
Aceptar te avisa en vez de perderlo en silencio.

## ¿Puedo fiarme de que hace lo que dice?

El código está publicado entero y cualquiera puede leerlo. Además tiene 52
pruebas automáticas que se ejecutan solas cada vez que se sube un cambio: si
algo se rompe, se ve inmediatamente y queda registrado en público.

También escribe en el registro de NVDA todo lo que hace, paso a paso. Si alguna
vez algo va mal, ahí queda la explicación.
