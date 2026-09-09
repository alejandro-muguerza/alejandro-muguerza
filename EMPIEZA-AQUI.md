# Versión 4 — conexión neuronal eléctrica

Abre **vista-previa.html** o directamente **assets/contribution-flow.gif**. El resto del perfil conserva el diseño aprobado.

Esta versión reproduce el lenguaje visual de la captura: curvas largas, ramificaciones finas, halos azules y cian, acentos violetas, núcleos luminosos y tres señales que recorren la red dejando estelas. No hay una onda que suba y baje continuamente: la estructura permanece fija mientras la electricidad viaja por ella.

## Cómo se relaciona con tus aportes

La corriente eléctrica es una capa artística siempre visible. Sus puntos no equivalen a días activos. Los **anillos** en la cuadrícula representan los días con contribuciones reales; su tamaño y color dependen de la actividad. El total se obtiene de GitHub. La actividad de cada tramo también modifica suavemente la curvatura del diseño al actualizarse. La leyenda distingue “neural signal” y “real activity”.

Se conserva la consulta de datos y la actualización diaria de la versión anterior. La tarjeta incluida usa el último calendario guardado en data/contributions.json. No se ha modificado tu cuenta ni activado el flujo.

## Subir a GitHub

1. Guarda una copia de tu README actual.
2. En tu repositorio alejandro-muguerza/alejandro-muguerza, sube **README.md**, **assets/**, **scripts/** y **data/** a la raíz.
3. Incluye **.github/workflows/contribution-flow.yml**. En Finder usa ⌘⇧. para mostrar la carpeta oculta. También puedes crear ese archivo desde GitHub y pegar su contenido.
4. Confirma en main y abre **Actions → Update AI Contribution Flow → Run workflow**. Comprueba que la ejecución termine en verde.

El flujo recalcula la tarjeta diariamente a las 08:17 de Lima; GitHub puede retrasar la ejecución o la renovación de la imagen en caché. No requiere un token personal. Si solo estás reemplazando la versión 3, incluye especialmente el nuevo archivo **scripts/electric_render.py** y el workflow actualizado.

## Editar el efecto

**scripts/electric_render.py** controla las curvas, las ramas, los colores, los halos y las señales. **scripts/contribution_flow.py** consulta y valida los datos. No cambies el significado de los anillos por el de los puntos decorativos.

Para actualizar localmente, instala scripts/requirements.txt y ejecuta:

```sh
python scripts/contribution_flow.py --username alejandro-muguerza --public
```

Requiere Python y la fuente Arial en macOS o DejaVu Sans en Linux. El workflow instala sus dependencias. Si la consulta falla, la ejecución se detiene y no publica datos vacíos.
