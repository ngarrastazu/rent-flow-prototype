# RentFlow · prototipo

Web de matching de habitaciones y compañeros de piso en Madrid, hecha con **Streamlit** y **SQLite**.

## Cómo arrancarla

Con [uv](https://docs.astral.sh/uv/):

```bash
uv sync
uv run streamlit run app.py
```

Sin uv: `pip install -r requirements.txt` y `streamlit run app.py`.

Se abre en el navegador (http://localhost:8501). La primera vez crea la base de datos `data/rentflow.db`
con datos de ejemplo: 51 inquilinos, 8 caseros y 30 habitaciones en Madrid.

Conviene tener **internet** durante la demo: el fondo del mapa y las fuentes se descargan al momento. Sin conexión
la app funciona, pero el mapa sale sin calles.

## Guion de la demo (historia de Mario)

1. Pulsa **Probar como Mario (demo)**.
2. **Mis matches**: su primer resultado es la habitación de Chamberí con un **94 %** de compatibilidad.
   Prueba los filtros (precio, zona, baño propio) y cambia a **Mapa**: pulsa un punto para ver su resumen.
3. **Ver detalles**: compañeros (Lucía y Tom) con sus hábitos, el casero verificado y el desglose
   "Por qué este match". Activa **Ver reseñas**.
4. **Contactar**: se abre el chat con el casero y los compañeros.
   En **Mi perfil y hábitos** puedes editar a qué te dedicas y tu descripción (el nombre verificado no se cambia).
5. Cierra sesión y entra como **Carmen Ruiz · casero**: en **Mis habitaciones** ve a Mario como interesado
   y la lista de inquilinos más compatibles (búsqueda inversa). Contesta en el chat. En **Mi perfil** edita su
   presentación, que es la que ven los inquilinos.
6. **Métricas (equipo)**: cada acción queda registrada y se compara con las Test Cards (I9, I12, chat) y con
   la exploración de la oferta (I11: filtros, mapa y fichas abiertas).

Para volver al estado inicial: **Métricas → Reiniciar datos de la demo**, o `uv run rentflow-seed`.

Tests: `uv run pytest` (comprueban, entre otras cosas, que el match de Mario sigue dando 94 %).

## Archivos

| Ruta | Qué hay |
| --- | --- |
| `app.py` | Punto de entrada de Streamlit |
| `src/rentflow/ui/` | Interfaz: una pantalla por archivo (entrada, inquilino, casero, mensajes, métricas) |
| `src/rentflow/matching.py` | Algoritmo de compatibilidad (filtros duros + puntuación ponderada) |
| `src/rentflow/db.py` | Esquema SQLite y funciones de acceso a datos |
| `src/rentflow/seed.py` | Datos de ejemplo de Madrid (semilla fija: siempre los mismos) |
| `tests/` | Tests con pytest (algoritmo, datos de la demo e interfaz) |
| `assets/` | Logos de la marca (PNG y SVG) y fotos de ejemplo de habitaciones (`assets/rooms/`) |
| `docs/DESIGN.md` | Guía visual: colores, tipografía, componentes y pantallas |
| `.streamlit/config.toml` | Tema de Streamlit con los colores y fuentes de la marca |
| `data/` | La base de datos local (no se sube a git) |

## El algoritmo

1. **Filtros duros**: se descarta el piso si cuesta más de un 10 % por encima del presupuesto, si queda libre
   más de 30 días después de la fecha de entrada, o si no cumple tabaco, mascotas o baño propio.
2. **Puntuación** (cada factor de 0 a 1):
   `30 % presupuesto + 20 % zona + 20 % horarios + 15 % limpieza + 15 % estilo de vida`.
   Horarios, limpieza y estilo de vida se comparan con cada compañero que ya vive en el piso y se hace la media.

Los pesos están en `WEIGHTS`, al principio de `src/rentflow/matching.py`: cambiadlos para probar otras versiones
(y pasad `uv run pytest` para comprobar que el match de Mario sigue dando 94 %).

## Fotos

Las fotos de las habitaciones son de **Wikimedia Commons**, con licencia libre y sin personas. Son ilustrativas
(pisos de otros países), no oferta real de Madrid. Autor, licencia y enlace de cada una en
[assets/rooms/CREDITS.md](assets/rooms/CREDITS.md). Varias exigen citar al autor: si publicáis la app,
enlazad ese archivo desde un sitio visible.
