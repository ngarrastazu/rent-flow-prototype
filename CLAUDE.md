# CLAUDE.md — RentFlow

Prototipo funcional de **RentFlow** (proyecto académico de ICAI): web de matching de habitaciones y compañeros de piso en Madrid, hecha con **Streamlit + SQLite**. Es lo que se enseña en la demo de clase, **no es producción**: prioriza que la demo funcione, se entienda y cuente bien la historia.

## Reglas críticas (léelas antes de tocar nada)

1. **El match Mario ↔ Chamberí debe dar 94 % y salir el primero.** Aparece en el pitch. No cambies `WEIGHTS`, los filtros, `seed.py` ni los datos de Mario/Lucía/Tom sin pasar `uv run pytest` (lo comprueba `test_mario_first_match_is_chamberi_94`). En el seed la habitación 1 debe quedar **libre** (sin aceptar ninguna solicitud ni pausarla): Mario la solicita en directo.
2. **Capas:** la interfaz (`app.py`, `src/rentflow/ui/`) no escribe SQL → toda consulta es una función en `db.py`. `matching.py`, `db.py` y `seed.py` no importan Streamlit.
3. **Interfaz en español** (tuteando, frases cortas). Código e identificadores en inglés; comentarios y docstrings en español.
4. **Nada de login real, contraseñas, pagos ni datos sensibles.** Nada de fotos ni datos de personas reales: las fotos de habitaciones solo con licencia libre, **sin personas** y con crédito en `assets/rooms/CREDITS.md`. `data/rentflow.db` no se versiona.
5. **El matching compara hábitos, nunca identidad:** prohibido filtrar o puntuar por origen, etnia, religión, etc. Una opción tipo "solo chicas" requiere revisión legal antes.
6. Si añades una funcionalidad que valida una hipótesis, **registra su evento** con `db.log_event` y muéstralo en Métricas (§7).
7. Es una web para enseñar en ordenador: no la conviertas en app móvil.
8. **Lo visual sigue [docs/DESIGN.md](docs/DESIGN.md):** sin emojis (iconos `:material/…:`), un solo botón violeta (`type="primary"`) por pantalla, logos solo desde `assets/` (nunca redibujados ni escritos como texto), y `unsafe_allow_html` solo en `ui/theme.py`/insignias/puntuación/estrellas.

## Comandos

Entorno gestionado con **uv** (Python 3.12, fijado en `.python-version`; dependencias en `pyproject.toml` + `uv.lock`).

```bash
uv sync                          # crea .venv e instala dependencias (incluye dev: pytest, ruff)
uv run streamlit run app.py      # abre http://localhost:8501
uv run rentflow-seed             # borra data/rentflow.db y vuelve a cargar los datos de ejemplo
uv run pytest                    # tests (BD temporal, nunca toca data/rentflow.db)
uv run ruff check .              # lint  (uv run ruff check --fix . para arreglar lo automático)
uv add <paquete>                 # nueva dependencia (actualiza pyproject.toml y uv.lock)
```

- El código es un paquete instalable (`src/rentflow/`, backend `uv_build`); `uv sync` lo instala en modo editable, así que los imports son siempre `from rentflow import db` / `from rentflow.ui.x import y`, nunca `import db`.
- La primera ejecución de la app crea `data/rentflow.db` y llama a `seed.seed()` si está vacía. La ruta se puede cambiar con la variable de entorno `RENTFLOW_DB_PATH`.
- `requirements.txt` solo existe como alternativa para quien no use uv (`pip install -r requirements.txt`, incluye `-e .`). Si cambias dependencias, mantenlo alineado con `pyproject.toml`.
- Streamlit `>=1.50,<2` (instalada: 1.67). Usamos `st.container(border=True, key=…)`, `vertical_alignment`, `st.toggle`, `st.segmented_control`, `st.chat_message`, `st.chat_input`, `st.pydeck_chart` (con `on_select`), `st.toast` y **`width="stretch"`** (no uses `use_container_width`, está obsoleto).
- **Necesita internet** para el fondo del mapa (Carto) y las fuentes (Google Fonts). Sin conexión la app funciona, pero el mapa sale sin calles y el texto con la fuente del sistema.

### Antes de dar algo por terminado

```bash
uv run ruff check . && uv run pytest
```

Y, si tocaste la interfaz, una pasada por el guion de la demo del `README.md` a 1280 px de ancho, revisando la §12 de `docs/DESIGN.md`.

## Estructura

```
rent-flow-prototype/
├── app.py                  # entrada de Streamlit: solo llama a rentflow.ui.router.main()
├── src/rentflow/
│   ├── db.py               # esquema SQLite, ZONES/SCHEDULES y TODAS las consultas
│   ├── matching.py         # algoritmo de compatibilidad (sin Streamlit)
│   ├── rentals.py          # solicitudes, opiniones de compañeros, aceptar/rechazar, bajas (sin Streamlit)
│   ├── seed.py             # datos de ejemplo deterministas (SEED = 42) → `uv run rentflow-seed`
│   └── ui/                 # interfaz, una pantalla por módulo
│       ├── theme.py        # identidad visual: rutas de logos, colores, CSS global, puntuación, insignias, estrellas
│       ├── maps.py         # mapa de habitaciones con pydeck (puntos con % y color de compatibilidad)
│       ├── router.py       # setup_page(), carga inicial de datos, barra lateral, ROUTES y main()
│       ├── navigation.py   # constantes PAGE_* y PAGE_ICONS, menús por rol, go(), login(), logout(), DEMO_USER
│       ├── components.py   # piezas de personas y pisos: verified_badge, room_facts, room_photo, about_fields…
│       ├── landing.py      # entrada: probar como Mario, entrar, crear cuenta
│       ├── tenant.py       # Mis matches (filtros, lista/mapa, «Ver más»), ficha, Mi perfil y hábitos
│       ├── landlord.py     # Mis habitaciones (solicitudes · más compatibles · chats), Publicar, Mi perfil
│       ├── residents.py    # Mis inquilinos (casero): quién vive en sus pisos, escribirles, darles de baja
│       ├── requests.py     # Mis solicitudes y Mi piso (inquilino): estado, retirar, opinar como compañero
│       ├── messages.py     # chat y valoraciones (ambos roles)
│       └── metrics.py      # métricas del equipo y "Reiniciar datos de la demo"
├── tests/                  # pytest: algoritmo, filtros, datos de la demo y 94 % (test_matching.py);
│                           #   solicitudes, aceptación, bajas, permisos y migración (test_rentals.py);
│                           #   flujo de la UI con AppTest: demo, filtros/mapa, edición de perfil (test_app.py);
│                           #   reglas de diseño: sin emojis, logos, rangos de color, créditos de fotos (test_design.py)
├── assets/                 # logos de marca: png/ y svg/ × horizontal, vertical, isotipo, icono-app
│   └── rooms/              # 12 fotos de ejemplo (Wikimedia Commons, sin personas) + CREDITS.md + placeholder.jpg
├── docs/DESIGN.md          # guía visual (marca, color, tipografía, componentes, pantallas)
├── .streamlit/config.toml  # tema de Streamlit: colores de marca y fuentes Inter / Inter Tight
├── data/                   # rentflow.db (ignorada por git; solo se versiona .gitkeep)
├── pyproject.toml · uv.lock · .python-version
├── requirements.txt        # alternativa sin uv
└── README.md               # instrucciones y guion de la demo para el equipo
```

Dependencias entre módulos (de arriba abajo, nunca al revés): `app.py` → `ui/router` → pantallas (`landing`, `tenant`, `landlord`, `messages`, `metrics`) → `ui/navigation` + `ui/components` + `ui/maps` → `ui/theme` → `rentals` → `matching` → `db`. Las pantallas no se importan entre sí: comparten cosas a través de `navigation`, `components` o `theme`.

## Modelo de datos (`db.py`)

| Tabla | Campos clave | Notas |
| --- | --- | --- |
| `users` | id, name, age, role (`inquilino` / `casero`), occupation, origin, bio, verified | Un único tipo de usuario con rol |
| `preferences` | user_id, budget_min/max, zones (`"Chamberí\|Malasaña"`), move_in, schedule, cleanliness 1–5, noise 1–5, smokes, pets, own_bathroom | También la tienen los compañeros que ya viven en un piso: se usa para compararles |
| `rooms` | landlord_id, title, zone, price, size_m2, own_bathroom, available_from, smoking_allowed, pets_allowed, description, photo (BLOB), active, tenant_id | `active = 0`: no sale en los matches (alquilada o pausada). `tenant_id`: quien la ocupa tras aceptar su solicitud (NULL = libre) |
| `room_members` | room_id, user_id | Compañeros que ya viven en el piso. Quien vive en un piso **no** aparece como candidato que busca |
| `reviews` | author_id, target_id, rating 1–5, comment | Reseñas de caseros y de compañeros |
| `conversations` | room_id, tenant_id (único por par) | Participan el interesado, el casero y los compañeros |
| `messages` | conversation_id, author_id, text | `author_id` NULL = mensaje automático de RentFlow (`db.send_system_message`) |
| `requests` | room_id, tenant_id, message, move_in, months, status, note, decided_at | Solicitudes. `status`: `pendiente` → `aceptada` / `rechazada` / `retirada` (inquilino) / `cerrada` (sistema). Como mucho una pendiente por inquilino y habitación (índice único parcial) |
| `request_votes` | request_id, user_id, vote (1 / −1) | Opinión de cada compañero del piso sobre un candidato |
| `events` | user_id, kind, room_id | Registro para las métricas (§7) |

Convenciones:
- `db.connect()` es un context manager: abre, hace commit/rollback y **cierra** la conexión (en Windows, una conexión abierta impide borrar la base de datos al reiniciar).
- `db.query()` devuelve `list[dict]` (alias `db.Row`); `db.query_one()` devuelve `dict | None`; `db.get_preferences()` ya convierte `zones` en lista.
- Operaciones de varias sentencias (p. ej. `create_room` + compañeros) van en **una sola** `with connect()` para que sean atómicas.
- Fechas como texto ISO `AAAA-MM-DD`; `created_at` lo pone SQLite (UTC). Booleanos como `INTEGER` 0/1.
- Zonas siempre de `db.ZONES`; horarios siempre de `db.SCHEDULES` (el algoritmo compara cadenas exactas).
- Si cambias el esquema: actualiza `SCHEMA`, ajusta `seed.py` y regenera con `uv run rentflow-seed`. No hay sistema de migraciones; la única excepción es `init_db()`, que añade `rooms.tenant_id` a bases de datos anteriores a las solicitudes (`CREATE TABLE IF NOT EXISTS` no añade columnas). Si añades otra columna a una tabla existente, haz lo mismo o pide regenerar la base de datos.
- **Quién vive dónde:** `room_members` = compañeros que ya viven en el piso; `rooms.tenant_id` = quien ocupa esa habitación. `db.rooms_lived_in()` une ambos (no aparecen en la búsqueda inversa). `db.residents_of_landlord()` los lista para «Mis inquilinos» (`kind` = `ocupante` / `compañero`).
- `db.DB_PATH` se lee en cada conexión: los tests lo parchean con `monkeypatch.setattr(db, "DB_PATH", ...)`.
- **Ubicación:** no hay direcciones. `db.ZONE_COORDS` tiene el centro aproximado de cada zona (debe cubrir todas las de `ZONES`) y `db.room_coords(room)` le suma un desplazamiento fijo según el id (determinista, sin `random`).
- **Fotos:** `rooms.photo` es un BLOB. El seed carga las de `assets/rooms/`; las subidas por caseros se guardan igual. Sin foto, la interfaz muestra `theme.ROOM_PLACEHOLDER`.

## Algoritmo de matching (`matching.py`)

1. **Filtros duros** (`score_room` devuelve `None`):
   - precio > `budget_max × PRICE_TOLERANCE` (1,10);
   - libre más de `MOVE_IN_MARGIN_DAYS` (30) días después de la fecha de entrada;
   - fuma y no se permite · tiene mascota y no se admiten · necesita baño propio y no lo hay.
2. **Puntuación ponderada** (`WEIGHTS`, cada factor de 0 a 1):

   `Compatibilidad = 30 % presupuesto + 20 % zona + 20 % horarios + 15 % limpieza + 15 % estilo de vida`

   - Presupuesto: 1 si está dentro; entre el máximo y +10 % baja linealmente de 1 a 0,4.
   - Zona: 1 si está en sus zonas (o no eligió ninguna), 0,3 si no.
   - Horarios, limpieza y estilo de vida se calculan **contra cada compañero** y se promedian. Escalas 1–5: `1 − |a − b| / 4`. Horario igual 1 / distinto 0,4. Tabaco igual 1 / distinto 0,3. Mascotas igual 1 / distinto 0,6. Estilo de vida = media de ruido, tabaco y mascotas.
   - Piso sin compañeros: `NO_ROOMMATES_SCORE` (0,8) en esos tres factores.
3. API pública:
   - `score_room(prefs, room, mates_prefs)` → `(puntuación_0_100, desglose)` o `None`.
   - `matches_for(tenant_id, limit=10)` → habitaciones ordenadas (`room`, `score`, `breakdown`, `mates`); `limit=None` devuelve todas.
   - `filter_matches(results, max_price, zones, own_bathroom, sort)` → filtra y ordena **sin recalcular** (la puntuación no cambia). Órdenes en `SORTS`.
   - `candidates_for(room_id)` → top 5 inquilinos que buscan piso (búsqueda inversa del casero).
   - `mates_preferences(mates)` → preferencias de los compañeros (omite los que no tienen perfil).
   - `pair_affinity(a, b)` → afinidad de hábitos entre dos personas (0–100), con los pesos relativos de horarios, limpieza y estilo de vida. La ven los compañeros al opinar sobre un candidato.

El desglose se muestra en "Por qué este match". Si añades un factor, añádelo también a `WEIGHTS`: los pesos deben sumar 1 (hay un `assert` al importar el módulo y un test).

## Solicitudes y alquiler (`rentals.py`)

Ciclo: **publicada** → solicitudes (los compañeros opinan) → el casero **acepta** → **alquilada** → el casero da de baja
al ocupante → publicada otra vez. El casero también puede **pausar** un anuncio libre (no sale en los matches).

- Toda la lógica y los permisos están en `rentals.py` (sin Streamlit). La interfaz llama a sus funciones y muestra el
  texto de `RentalError` si algo no se puede hacer. No cambies estados con `db.set_request_status` desde la interfaz.
- `send_request` (solo inquilinos que no viven ya en ese piso; estancia de `MONTHS`), `withdraw_request`,
  `vote` (solo compañeros del piso; cambiar de opinión sustituye la anterior), `accept_request` / `reject_request` /
  `set_paused` / `remove_resident` (solo el casero dueño). `can_request(tenant_id, room)` da el motivo si no se puede.
- **Aceptar** (`db.accept_request_tx`, en una transacción): la habitación pasa a `tenant_id` = inquilino y
  `active = 0`; si ocupaba otra habitación, esa queda libre (mudanza); deja de ser compañero en otros pisos; se cierran
  las demás solicitudes pendientes de la habitación y las del inquilino.
- **Dar de baja**: al ocupante, la habitación se libera y se vuelve a publicar; a un compañero, se quita del piso. Quitar
  compañeros cambia la compatibilidad de esa habitación con todos (cuidado con Lucía/Tom y el 94 %).
- Cada paso deja un **mensaje automático de RentFlow** en la conversación de esa habitación con ese inquilino.
- Decide siempre el casero: las opiniones de los compañeros informan, no bloquean.

## Interfaz (`src/rentflow/ui/`)

### Navegación
- Nombres de página en constantes `PAGE_*` y menús en `TENANT_PAGES` / `LANDLORD_PAGES` (`navigation.py`); cada página se resuelve con el diccionario `ROUTES` de `router.py` (página → función `page_*(user)`).
- **Para añadir una página:** constante `PAGE_X` + lista del rol en `navigation.py`, función `page_x(user)` en el módulo de su rol (o uno nuevo en `ui/`), y entrada en `ROUTES`.
- El menú es un `st.radio(key="page")` en la barra lateral, con iconos de `PAGE_ICONS` vía `format_func`; el CSS oculta el círculo y lo pinta como menú.
- Para cambiar de página **desde un botón** usa el callback `go(page, **estado)` con `on_click` (corre antes de dibujar el menú).
- **Desde un formulario o código que corre después del menú** no asignes `st.session_state.page` (Streamlit lanza excepción porque el widget ya existe): usa `st.session_state._goto = PAGE_X` y `st.rerun()`; `main()` lo aplica al principio.
- Estado de sesión: `user_id`, `page`, `_goto`, `_flash`, las marcas de diálogo, `selected_room`, `conversation_id`, `logged_matches`, `logged_detail`, `logged_filter`, `logged_map`, `matches_shown`, `rev<room_id>` y los filtros `f_price`, `f_zones`, `f_bath`, `f_sort`, `f_view`. `logout()` lo vacía todo.
- Streamlit **borra el estado de un widget que no se dibuja** (p. ej. los filtros al abrir una ficha). Las claves que deben sobrevivir van en `navigation.PERSISTENT_KEYS`; `keep_widget_state()` las re-asigna al principio de cada ejecución.
- Widgets con `key`: inicializa el valor en `st.session_state` antes de dibujarlos y **no** pases `value=` a la vez (Streamlit avisa del conflicto).
- El usuario de la demo se busca con `db.find_user_by_name(DEMO_USER)`.
- Avisos tras guardar: `navigation.flash("…")` antes de `st.rerun()` (o en un callback); `router.main()` lo muestra como `st.toast`.
- `navigation.open_chat(room_id, tenant_id)` (callback): abre o crea la conversación y va a Mensajes.
- **Diálogos** (`@st.dialog`): se abren con una marca en sesión (`_request_dialog`, `_accept_dialog`, `_remove_dialog`) que se pone en el `on_click` del botón; la marca se borra al confirmar, al cancelar y en `on_dismiss` (cerrar con la X o clic fuera). No la borres al abrir el diálogo: los botones de dentro dejarían de funcionar en los tests y tras una re-ejecución completa.

### Estilo (detalle completo en `docs/DESIGN.md`)
- Precios `650 €/mes`, porcentajes `94 %` (con espacio), decimales con coma en las valoraciones (`4,5`), fechas ISO.
- **Todo lo visual pasa por `ui/theme.py`:** `setup_page()` (page_icon, `st.logo`, CSS), tokens de color (`VIOLET`, `BLUE`, `INK_MUTED`…), rutas de logos (`LOGO_*`, `ISOTYPE*`, `APP_ICON`) e iconos (`ICON`). No pongas colores hex ni rutas de `assets/` sueltos en las pantallas.
- Compatibilidad: siempre con `score_block(score, size)` (32 px en tarjeta, 56 px en ficha): color **y** etiqueta según `score_style()` (≥ 85 «Match excelente» violeta, 70–84 «Buen match» azul, < 70 «Match posible» gris).
- Insignias con `badge(texto, "verified" | "brand" | "muted")` y `badges([...])` (máx. 3); verificado = `verified_badge(user)`. Estrellas con `stars_html()` / `rating_line()`; reseñas con `review_html()`.
- Tarjetas con `st.container(border=True)`; estados vacíos con `empty_state(mensaje, acción)`.
- **Un solo `type="primary"` por pantalla**; el resto secundarios o `type="tertiary"` (volver, cerrar sesión, abrir chat).
- Contenedores con estilo propio vía `key` → clase CSS `.st-key-<key>`: `hero` (banda violeta de portada), `narrow` (formularios de ~760 px), `sticky` (columna del match fija), `empty`, `filters` (barra de filtros), `roomphoto` (foto 16:9 de la ficha) y cualquier `thumb…` (miniatura 3:2 recortada). Fotos siempre con `components.room_photo(room, key)`.
- **pydeck:** cualquier texto en los parámetros de una capa se interpreta como expresión. Los literales van entre comillas simples dentro de la cadena (`radius_units="'pixels'"`, `get_text_anchor="'middle'"`). El mapa base es de Carto y necesita internet.
- **Espaciado** (en `theme.inject_css`): 10 px entre elementos de la página y 5 px dentro de las tarjetas. Las tarjetas se marcan con un `key` que empieza por `card` (`st.container(border=True, key="card…")`). Entre párrafos de un mismo bloque hay 0,35rem. Streamlit pone `margin-bottom: -1rem` a los bloques de texto y el CSS lo anula; no lo reintroduzcas o el texto se solapará con el elemento siguiente.
- Varias líneas cortas seguidas (p. ej. una lista de candidatos) van en **un solo** `st.caption` con saltos `"  \n"`, no en un `st.caption` por línea, para que no se separen con el hueco entre elementos.
- El aviso de Streamlit «Press Enter to submit form» está oculto (`InputInstructions`): se solapaba con el texto.
- Los selectores `data-testid` del CSS son de Streamlit 1.67: si al actualizar Streamlit algo deja de aplicarse, revísalos con el inspector del navegador.
- Cualquier HTML con datos de usuario se escapa (`html.escape`).
- Selectores de usuarios u objetos: **ids** como opciones + `format_func` con el nombre (nunca etiquetas como claves de un dict).
- Callbacks con nombre (`log_reviews_opened`) mejor que lambdas con lógica.

### Pantallas
- **Entrada:** banda violeta con el logo en negativo y el lema; "Probar como Mario (demo)" (único botón violeta), entrar como cualquier usuario, crear cuenta (un inquilino nuevo va directo a su perfil).
- **Inquilino:** Mis matches (barra de filtros, contador «N de M», vista Lista con fotos y «Ver más» o vista Mapa con resumen al pulsar un punto) → ficha de la habitación (foto, compañeros, casero, reseñas, desglose, mini mapa; botón violeta **«Solicitar esta habitación»** con diálogo de presentación, entrada y estancia, o el estado de su solicitud; «Contactar» como secundario) · **Mis solicitudes** (estado, opinión de los compañeros, retirar, chat) · **Mi piso** (su habitación y compañeros con afinidad; si es compañero, candidatos para opinar «Me encaja / No me encaja») · Mi perfil y hábitos · Mensajes · Métricas.
- **Casero:** Mis habitaciones (estado Publicada / Pausada / Alquilada, pausar, y pestañas **Solicitudes** con compatibilidad, mensaje y opinión de los compañeros, aceptar con confirmación o rechazar · **Más compatibles** · **Chats**) · **Mis inquilinos** (quién vive en cada piso, escribir, dar de baja con confirmación y motivo) · Publicar habitación · Mensajes · Mi perfil · Métricas.
- **Perfil (ambos roles):** bloque «Sobre ti» (`components.about_fields`, dentro de un `st.form`): edad, ocupación, de dónde eres y descripción (máx. 300 caracteres). El inquilino lo tiene en «Mi perfil y hábitos» junto a sus hábitos; el casero, en «Mi perfil». Se guarda con `db.update_user`, que no toca el rol, la verificación ni los hábitos. **El nombre de un perfil verificado no se puede editar** (anularía la verificación).
- **Mensajes:** selector de conversación, chat, valorar a otro participante.
- **Métricas (equipo):** fila de hipótesis (ven matches, abren reseñas I12, contactan I9, mensajes), fila «Exploración de la oferta · I11» (usan filtros, abren el mapa, abren una ficha), fila «Del match al piso» (envían solicitud, aceptadas, rechazadas, compañeros que opinan), últimas acciones y «Reiniciar datos de la demo».

## Datos de ejemplo (`seed.py`)

- Deterministas: `seed()` llama a `random.seed(SEED)` **al empezar**, así "Reiniciar datos de la demo" genera exactamente lo mismo que la primera carga (lo comprueba `test_seed_is_repeatable`). Si cambias el orden de las llamadas a `random`, cambian todos los datos: pasa los tests.
- Mario es siempre el usuario 1 y su habitación de Chamberí la habitación 1 (con la foto `room-01.jpg`).
- Las fotos se asignan **por orden** (`room_photo(i)`), sin `random`, para no alterar el resto de datos. Si añades fotos a `assets/rooms/`, añade su línea en `CREDITS.md` (lo comprueba `test_room_photos_are_credited`) y usa solo fotos con licencia libre y **sin personas**.
- Volumen: 51 inquilinos (20 buscan, 28 + Lucía y Tom viven en pisos, + Mario), 8 caseros, 30 habitaciones.
- Solicitudes de ejemplo (sin `random`, con `seed_request`, que **no** registra eventos): los dos interesados de la habitación de Lavapiés de Carmen, y un **rival de Mario** en la de Chamberí (el mejor candidato que no es Mario), con Lucía a favor y Tom en contra. Carmen empieza con 3 solicitudes pendientes.
- Precios realistas por zona en `ZONE_PRICE` (€/mes): Usera la más barata, Salamanca la más cara.
- Nombres y orígenes variados (españoles y Erasmus), todos ficticios.
- Las 12 fotos son de Wikimedia Commons y de pisos de **otros países**: son ilustrativas, no se presentan como oferta real de Madrid. Varias son CC BY / CC BY-SA: si la app se publica, hay que enlazar `CREDITS.md` desde un sitio visible.

## Métricas e hipótesis

Cada acción relevante se guarda con `db.log_event(user_id, kind, room_id)` y se resume en "Métricas (equipo)" (`db.users_with_event`, `db.count_events`, `db.recent_events`). Están ligadas a las Test Cards del plan de validación:

| `kind` | Cuándo se registra | Hipótesis / Test Card |
| --- | --- | --- |
| `ver_matches` | Primera vez por sesión que el inquilino ve sus matches | Denominador de los porcentajes |
| `ver_detalle` | Abre la ficha de una habitación | Interés en el match |
| `ver_resenas` | Activa "Ver reseñas" | **I12**: las reseñas dan confianza (objetivo ≥ 60 %) |
| `contactar` | Pulsa "Contactar" (solo la primera vez por habitación) | **I9**: aceptan un compañero sugerido (objetivo ≥ 50 %) |
| `mensaje` | Envía un mensaje en el chat | Chat en la app frente a WhatsApp (objetivo ≥ 60 % de conversaciones dentro) |
| `resena` | Envía una valoración | Base de la confianza y del "data moat" |
| `filtrar` | Primera vez por sesión que aplica un filtro en «Mis matches» | **I11**: ¿exploran la oferta más allá del top? |
| `ver_mapa` | Primera vez por sesión que abre la vista de mapa | **I11** |
| `solicitar` / `retirar_solicitud` | Envía o retira una solicitud | Conversión del match al alquiler |
| `aceptar_solicitud` / `rechazar_solicitud` | El casero decide (lo registra el casero) | Conversión |
| `votar` | Un compañero opina sobre un candidato | **I9**: doble aceptación |
| `quitar_inquilino`, `pausar_anuncio`, `reactivar_anuncio` | Gestión del casero | Solo registro |

Estado tras las entrevistas: validadas I1–I7, I9, I10, I12, I13, C1, C2, C4, C5; por poco I8; **no validadas I11** (matching frente a Badi: valoran más el volumen de pisos), **I14** (mantenimiento para inquilinos) y **C6** (comisión a caseros). Consecuencias:
- La oferta de pisos importa tanto como el algoritmo: no escondas habitaciones con filtros demasiado estrictos.
- El mantenimiento, si se añade, es **para caseros**, no para inquilinos.
- El cobro al casero está abierto (comisión frente a cuota fija): no lo programes como definitivo.
- El premium para inquilinos está aparcado: no añadas pagos.

## Contexto de negocio

- **Propuesta de valor:** búsqueda inversa ("dinos qué buscas y te lo encontramos") + matching por hábitos con los compañeros que ya viven en el piso + perfiles verificados y reseñas.
- **Lema:** "Dinos qué buscas. Te encontramos habitación y compañeros compatibles."
- **Marca:** `rentflow` (minúsculas en el logo). Violeta `#4B02F2` (principal), azules `#2C78EE` / `#3D8CF7` / `#1C4FBA`. Paleta completa y reglas en `docs/DESIGN.md`.

| Lado | Segmento | Notas |
| --- | --- | --- |
| Demanda | Jóvenes con primer trabajo que se mudan a Madrid (25–35) | Principal: valoran tiempo y confianza |
| Demanda | Estudiantes desplazados y Erasmus (19–25) | Mucho volumen, poca capacidad de pago; picos en septiembre y enero |
| Oferta | Caseros pequeños (1–3 viviendas) | Quieren inquilinos fiables y verificados; la comisión no les convence |
| Oferta | Agencias e inmobiliarias | Secundario |

**La persona: Mario Rossi** — 27 años, de Milán, estudió en Bocconi, trabaja en banca de inversión en Madrid, gimnasio y running. Quiere vivir en **Chamberí** pero no puede pagarlo solo: busca piso compartido **con baño propio**. Su match ideal es la habitación de Chamberí con **Lucía** (fisioterapeuta, corre maratones) y **Tom** (consultor): **94 %**.

## Siguientes pasos (por prioridad)

1. Publicar el prototipo en una URL (Streamlit Community Cloud) para probarlo con usuarios reales. SQLite allí se borra al
   reiniciar: para conservar métricas haría falta una base externa (Supabase/Neon).
2. Alertas de búsqueda inversa: al publicar una habitación, aviso en la app a los inquilinos compatibles (evento nuevo).
3. Agendar la visita desde el chat (proponer hueco y aceptar), entre la solicitud y la aceptación.
4. Panel del casero con el modelo de cobro elegido (comisión frente a cuota fija) para el piloto, sin cobrar de verdad (**C6**).
5. Encuesta de convivencia al mes de entrar (métrica de **I10**: ≥ 70 % puntúa 4/5 o más).
6. Mantenimiento **para caseros** (aviso de averías desde el chat).
7. Aprender los pesos con las reseñas de convivencia tras un mes (sustituir `WEIGHTS` fijos).

**IA: descartada para la demo por ahora** (decisión del equipo, noviembre de 2026). Si se retoma: la IA solo traduce texto
a filtros/preferencias con un esquema fijo de hábitos y explica el match; nunca decide ni cambia la puntuación (el 94 % y la
regla 5 se mantienen). Ollama en el portátil del equipo (i7-8550U, 12 GB, sin GPU útil) solo da para modelos de ~3B y
respuestas de 3–8 s. Las suscripciones de 20 € (Claude Pro, Google AI Pro) **no** incluyen API: haría falta la API de pago
por uso de Anthropic o la de Gemini (con nivel gratuito). Diseño previsto: un `ai.py` sin Streamlit con proveedor
intercambiable y respaldo sin IA.

Deuda técnica conocida (aceptable para el prototipo): `matches_for` hace una consulta por habitación y compañero (N+1); con más de unos cientos de pisos convendría cargar todo en bloque.
