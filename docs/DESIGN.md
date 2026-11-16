# DESIGN.md — Guía visual de RentFlow

Instrucciones para quien programe la interfaz (persona o IA). Define **cómo debe verse** la app: marca, colores, tipografía, componentes y pantallas. Complementa a `CLAUDE.md`, que explica la lógica.

> Antes de tocar la interfaz, abre `el manual de marca (rentflow-manual-de-marca.png, todavía no está en el repositorio)`: es la referencia visual de todo lo que sigue.

## 1. Principios

1. **Clara y confiable.** La app gestiona dónde va a vivir alguien: nada de efectos llamativos. Mucho blanco, una sola acción principal por pantalla, información ordenada.
2. **El match es el protagonista.** El porcentaje de compatibilidad es lo primero que se ve en cada tarjeta y en cada ficha.
3. **La confianza se ve.** Verificación, reseñas y compañeros reales siempre visibles, nunca escondidos tras varios clics.
4. **Violeta para la marca y la acción; azul para el apoyo.** El violeta marca lo importante (botón principal, puntuaciones altas, enlaces activos). El azul acompaña (iconos, barras de progreso, detalles).
5. **Pensada para el ordenador.** Es un prototipo para enseñar en proyector: pantallas anchas (`layout="wide"`), textos legibles a distancia. No hace falta optimizar para móvil.

## 2. Archivos de marca

Todos están en `assets/` (`assets/png/…` y `assets/svg/…`). En el código, las rutas están centralizadas en `src/rentflow/ui/theme.py`. Usa siempre estos archivos: **no redibujes el logo ni lo escribas como texto**.

| Uso en la app | Archivo |
| --- | --- |
| Logo en la barra lateral (fondo claro) | `assets/png/horizontal/rentflow-horizontal-02-color-fondo-claro.png` |
| Logo en la portada / pantalla de entrada | `assets/svg/horizontal/rentflow-horizontal-02-color-fondo-claro.svg` |
| Banner de la portada sobre violeta | `assets/png/horizontal/rentflow-horizontal-01-principal-fondo-violeta.png` |
| Icono de la pestaña del navegador (`page_icon`) | `assets/png/isotipo/rentflow-isotipo-02-color-fondo-claro.png` |
| Barra lateral plegada (`st.logo(icon_image=…)`) | `assets/png/isotipo/rentflow-isotipo-02-color-fondo-claro.png` |
| Avatar de RentFlow en mensajes automáticos | `assets/png/icono-app/rentflow-icono-app-violeta.png` |
| Modo oscuro (si se añade) | variantes `03-color-fondo-oscuro` y `08-blanco-sobre-oscuro` |
| Referencia visual completa | `el manual de marca (rentflow-manual-de-marca.png, todavía no está en el repositorio)` y `.pdf` |

Variantes disponibles (en `svg/` y `png/`, cada una en `horizontal/`, `vertical/` e `isotipo/`):

| Archivo | Cuándo usarlo |
| --- | --- |
| `01-principal-fondo-violeta` | Portada, banners, redes sociales |
| `02-color-fondo-claro` | **Por defecto dentro de la app** (fondo blanco) |
| `03-color-fondo-oscuro` | Fondos oscuros |
| `04-monocromo-violeta` | Elementos de una sola tinta |
| `05-monocromo-azul` | Cuando el violeta compite con otro elemento violeta |
| `06-monocromo-negro` | Impresión en blanco y negro |
| `07-blanco-sobre-violeta` | Logo en negativo sobre una banda violeta |
| `08-blanco-sobre-oscuro` | Logo en negativo sobre fondos oscuros |

Reglas del logo:
- Área de seguridad libre alrededor = altura de la letra «r».
- Ancho mínimo: 120 px. Por debajo, usa el isotipo (solo los cubos).
- Nunca lo estires, gires, recolorees, ni le pongas sombra o borde.
- La palabra se escribe siempre **rentflow**, en minúsculas, cuando aparece como logo. En el texto normal se puede escribir «RentFlow».

## 3. Color

### Tokens

| Token | HEX | Uso |
| --- | --- | --- |
| `violet` | `#4B02F2` | Color de marca. Botón principal, enlaces, puntuaciones altas, elemento activo del menú |
| `violet-dark` | `#3A01BE` | Hover y estado pulsado del violeta |
| `violet-soft` | `#EFEAFE` | Fondos suaves de insignias y elementos seleccionados |
| `blue-light` | `#3D8CF7` | Iconos y detalles |
| `blue` | `#2C78EE` | Barras de progreso del desglose del match, puntuaciones medias |
| `blue-deep` | `#1C4FBA` | Texto secundario de marca, enlaces visitados |
| `night` | `#0D0638` | Fondos oscuros, banda de la portada |
| `ink` | `#14102B` | Texto principal |
| `ink-muted` | `#5A5670` | Texto secundario, pies de tarjeta, `st.caption` |
| `line` | `#E6E3F0` | Bordes de tarjetas y separadores |
| `surface` | `#F7F6FB` | Fondo de la barra lateral y de secciones |
| `white` | `#FFFFFF` | Fondo principal |

Estados (no son colores de marca, úsalos solo para su significado):

| Estado | HEX | Uso |
| --- | --- | --- |
| Éxito / verificado | `#1F9D55` | Insignia «verificado», mensaje de publicado |
| Aviso | `#C77700` | Avisos suaves |
| Error | `#D93025` | Errores de formulario |

### Reglas
- Proporción aproximada en cada pantalla: 80 % blanco/neutros, 15 % violeta, 5 % azul.
- **Un solo botón violeta (`type="primary"`) por pantalla.** El resto, secundarios.
- Texto sobre violeta o `night`: siempre blanco. Texto sobre blanco: `ink` o `ink-muted`. Nunca texto azul claro sobre blanco (poco contraste).
- No uses degradados ni sombras de colores.

### Color de la puntuación de compatibilidad

| Rango | Color | Etiqueta |
| --- | --- | --- |
| ≥ 85 % | `violet` `#4B02F2` | «Match excelente» |
| 70–84 % | `blue` `#2C78EE` | «Buen match» |
| < 70 % | `ink-muted` `#5A5670` | «Match posible» |

## 4. Tipografía

- **Titulares:** Inter Display, peso 700 (la misma familia que la palabra del logo).
- **Texto:** Inter, pesos 400 y 600.
- Carga Inter desde Google Fonts con el CSS de §6. Si no carga, la alternativa es la fuente sans serif del sistema.

| Elemento | Tamaño | Peso | Color |
| --- | --- | --- | --- |
| Título de página (`st.title`) | 36 px | 700 | `ink` |
| Subtítulo (`st.subheader`) | 22 px | 700 | `ink` |
| Título de tarjeta | 18 px | 600 | `ink` |
| Texto normal | 16 px | 400 | `ink` |
| Texto secundario (`st.caption`) | 14 px | 400 | `ink-muted` |
| Porcentaje de match en tarjeta | 32 px | 700 | según §3 |
| Porcentaje de match en ficha | 56 px | 700 | según §3 |

Tono del texto: español, tuteando, frases cortas y concretas («Tus matches», «Contactar con el casero y los compañeros»). Nada de mayúsculas sostenidas.

## 5. Tema de Streamlit

> **Implementado en** `.streamlit/config.toml` (que además carga Inter e Inter Tight desde Google Fonts) y `theme.setup_page()`. Los fragmentos de abajo son la especificación original.

Crea `.streamlit/config.toml`:

```toml
[theme]
primaryColor = "#4B02F2"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F7F6FB"
textColor = "#14102B"
font = "sans serif"
base = "light"
```

En `app.py`:

```python
st.set_page_config(
    page_title="RentFlow",
    page_icon="assets/png/isotipo/rentflow-isotipo-02-color-fondo-claro.png",
    layout="wide",
)
st.logo(
    "assets/png/horizontal/rentflow-horizontal-02-color-fondo-claro.png",
    icon_image="assets/png/isotipo/rentflow-isotipo-02-color-fondo-claro.png",
    size="large",
)
```

Con `st.logo` ya no hace falta el texto «## 🏠 RentFlow» en la barra lateral: sustitúyelo.

## 6. CSS global

> **Implementado en** `theme.inject_css()`. Los selectores de Streamlit 1.67 difieren de los de abajo (p. ej. la barra de progreso es `[data-testid="stProgressBarTrack"] > div`); la versión válida es la del código.

Inyéctalo una sola vez al principio de `app.py` con una función `inject_css()`:

```python
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Inter+Tight:wght@700&display=swap');
    html, body, [class*="css"], .stMarkdown, button, input, textarea { font-family: 'Inter', sans-serif; }
    h1, h2, h3 { font-family: 'Inter Display', 'Inter Tight', 'Inter', sans-serif; font-weight: 700; letter-spacing: -0.02em; color: #14102B; }

    /* Tarjetas: st.container(border=True) */
    [data-testid="stVerticalBlockBorderWrapper"] { border-radius: 16px; border-color: #E6E3F0; background: #FFFFFF; }

    /* Botones */
    .stButton > button, .stFormSubmitButton > button { border-radius: 10px; font-weight: 600; }
    .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] { background: #4B02F2; border-color: #4B02F2; }
    .stButton > button[kind="primary"]:hover { background: #3A01BE; border-color: #3A01BE; }

    /* Barra lateral */
    [data-testid="stSidebar"] { background: #F7F6FB; border-right: 1px solid #E6E3F0; }

    /* Barras de progreso del desglose del match */
    .stProgress > div > div > div > div { background-color: #2C78EE; }

    /* Métricas */
    [data-testid="stMetricValue"] { font-weight: 700; color: #4B02F2; }

    /* Insignias propias */
    .rf-badge { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 13px; font-weight: 600; }
    .rf-badge.verified { background: #E6F5EC; color: #1F9D55; }
    .rf-badge.brand { background: #EFEAFE; color: #4B02F2; }
    .rf-score { font-family: 'Inter Display', 'Inter Tight', sans-serif; font-weight: 700; line-height: 1; }
    </style>
    """, unsafe_allow_html=True)
```

Los selectores `data-testid` pueden cambiar entre versiones de Streamlit: si algo deja de aplicarse, revísalos con el inspector del navegador en lugar de añadir más CSS.

## 7. Componentes

### Insignias
Escríbelas con un helper `badge(texto, tipo)` que devuelva HTML con `.rf-badge`:
- `✓ Verificado` → tipo `verified` (verde).
- `Baño propio`, `Admite mascotas`, `Se puede fumar` → tipo `brand` (violeta suave).
Máximo 3 insignias por tarjeta.

### Tarjeta de match (lista «Tus matches»)

```
┌──────────────────────────────────────────────────────────────────────┐
│  94 %          Habitación con baño propio en Chamberí    [Ver detalles]│
│  Match         📍 Chamberí · 650 €/mes · 14 m² · entrada 2027-01-01   │
│  excelente     👥 Lucía (26), Tom (28) · 🏠 Carmen Ruiz ✓ Verificado  │
└──────────────────────────────────────────────────────────────────────┘
```

- `st.container(border=True)` con columnas `[1, 4, 1.4]`, alineadas al centro.
- Izquierda: porcentaje grande (`.rf-score`, 32 px, color según §3) y la etiqueta del rango debajo en 13 px.
- Centro: título en negrita; dos líneas de `st.caption` (datos del piso; compañeros y casero).
- Derecha: botón secundario «Ver detalles».
- Separación entre tarjetas: 12 px. Ordenadas de mayor a menor compatibilidad.

### Ficha de la habitación
- Columnas `[3, 2]`.
- **Izquierda:** foto (si existe, con `border-radius: 16px`), descripción, normas, «Tus compañeros» (una tarjeta por compañero con nombre, edad, ocupación, insignia de verificado, hábitos y estrellas) y «Casero».
- **Derecha, fija arriba:** porcentaje grande (56 px), etiqueta del rango, «Por qué este match» con una barra azul por factor y el peso entre paréntesis, y el único botón violeta: «💬 Contactar con el casero y los compañeros».
- Las reseñas se muestran con `st.toggle`; cada reseña: estrellas en violeta, comentario entre comillas en cursiva y autor en `ink-muted`.

### Estrellas
`★★★★☆ 4,2 (5 reseñas)`: estrellas llenas en `violet`, vacías en `line`. Usa coma decimal.

### Chat
- `st.chat_message` con avatar de icono Material (sin emojis, §9): `sentiment_satisfied` para el usuario actual, `home` para el casero, `person` para compañeros, y el icono de app violeta (`theme.APP_ICON`) para mensajes automáticos de RentFlow.
- Nombre en negrita + hora en `ink-muted` encima del mensaje.
- Encima del chat, una línea con los participantes y sus roles.

### Formularios
- Agrupa por bloques con subtítulos de 18 px («Qué buscas», «Cómo vives»).
- Deslizadores para escalas 1–5 con las etiquetas de los extremos en el texto («1 = relajado, 5 = muy ordenado»).
- Botón de envío principal en violeta, con verbo de acción («Guardar y ver mis matches», «Publicar»).

### Estados vacíos
Siempre con una frase que explique qué pasa y un botón para resolverlo. Ejemplo: «Todavía no has publicado ninguna habitación.» + [Publicar habitación]. Puedes acompañarlos del isotipo en `monocromo-violeta` a 64 px.

## 8. Pantallas

| Pantalla | Estructura | Acción principal (violeta) |
| --- | --- | --- |
| **Entrada** | Banda superior violeta a todo el ancho con `rentflow-horizontal-07-blanco-sobre-violeta` o `01-principal` y el lema «Dinos qué buscas. Te encontramos habitación y compañeros compatibles.» Debajo, dos columnas: Entrar · Crear cuenta | «▶ Probar como Mario (demo)» |
| **Tus matches** | Título + línea de resumen de lo que busca + lista de tarjetas | Ninguna (cada tarjeta tiene su botón secundario) |
| **Ficha de la habitación** | Ver §7 | «Contactar con el casero y los compañeros» |
| **Mi perfil y hábitos** | Formulario en dos bloques, ancho máximo ~720 px centrado | «Guardar y ver mis matches» |
| **Mis habitaciones** (casero) | Una tarjeta por habitación: datos, «Inquilinos más compatibles» y «Interesados» | «Publicar habitación» solo si no tiene ninguna |
| **Publicar habitación** | Formulario con datos, normas, foto y compañeros | «Publicar» |
| **Mensajes** | Selector de conversación, participantes, chat y valoración plegada | Enviar (campo de chat) |
| **Métricas (equipo)** | 4 métricas arriba con el objetivo de cada hipótesis, tabla de acciones debajo | Ninguna |

La banda de la portada usa `night` `#0D0638` o `violet` `#4B02F2` con el logo en negativo; el resto de pantallas va sobre blanco.

## 9. Espaciado y forma

- Escala de espaciado: 4, 8, 12, 16, 24, 32, 48 px.
- Radio de esquinas: 16 px tarjetas y fotos, 10 px botones y campos, 999 px insignias.
- Bordes de 1 px en `line`. Sin sombras, salvo una muy suave en los iconos de app.
- Iconos: NO debe de haber emojis en la aplicación.

## 10. Accesibilidad

- Contraste mínimo 4,5:1 en texto. `ink-muted` sobre blanco cumple; azul claro sobre blanco no: no lo uses para texto.
- El porcentaje nunca depende solo del color: va siempre acompañado de su etiqueta («Match excelente»).
- Todas las imágenes con texto alternativo (`caption` o `alt`).

## 11. Qué NO hacer

- No usar otros colores de marca, degradados, sombras de colores ni fondos con imágenes.
- No poner más de un botón violeta por pantalla.
- No mostrar el logo como texto ni con otra tipografía; usa los archivos de `assets/`.
- No usar `unsafe_allow_html` para nada que no sea el CSS de §6, las insignias y la puntuación.
- No romper la historia de la demo: la tarjeta de Mario en Chamberí (94 %) debe verse la primera y con el color «Match excelente».

## 12. Comprobación final

Antes de dar un cambio visual por terminado:
1. Ejecuta `streamlit run app.py` y recorre el guion de la demo del `README.md`.
2. Compara con `el manual de marca (rentflow-manual-de-marca.png, todavía no está en el repositorio)`: colores, logo y tipografía coinciden.
3. Revisa que cada pantalla tiene como mucho un botón violeta.
4. Comprueba que se lee bien a 1280 px de ancho (resolución típica de un proyector).