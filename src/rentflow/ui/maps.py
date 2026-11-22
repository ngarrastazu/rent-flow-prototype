"""Mapas de habitaciones con pydeck (incluido con Streamlit). Fondo de Carto: no necesita clave.

Las posiciones son aproximadas (centro del barrio + desplazamiento fijo, ver `db.room_coords`).
"""
from html import escape

import pydeck as pdk

from rentflow import db
from rentflow.ui.theme import VIOLET, hex_to_rgb, score_style

LAYER_ID = "rooms"


def _points(items):
    """items: [{"room": ..., "score": ...}] -> filas serializables para pydeck (sin la foto)."""
    rows = []
    for it in items:
        room, score = it["room"], it.get("score")
        lat, lon = db.room_coords(room)
        color, label = score_style(score) if score is not None else (VIOLET, "")
        rows.append({
            "id": room["id"], "lat": lat, "lon": lon,
            "title": escape(room["title"] or ""), "zone": escape(room["zone"] or ""), "price": room["price"],
            "score": "" if score is None else f"{score} %", "label": label,
            "text": "" if score is None else str(score),
            "color": hex_to_rgb(color),
        })
    return rows


def rooms_deck(items, zoom=14, show_scores=True):
    """Deck con un punto por habitación: color y número según la compatibilidad (DESIGN.md §3).

    Con varios puntos el encuadre se ajusta a todos; `zoom` solo se usa con un único punto.
    """
    rows = _points(items)
    if len(rows) > 1:  # encuadre que incluye todos los puntos, con un poco de margen
        view = pdk.data_utils.compute_view([[r["lon"], r["lat"]] for r in rows], view_proportion=1)
        view.zoom = min(view.zoom - 0.6, 14)
    else:
        lat, lon = (rows[0]["lat"], rows[0]["lon"]) if rows else db.MADRID_CENTER
        view = pdk.ViewState(latitude=lat, longitude=lon, zoom=zoom)
    layers = [
        pdk.Layer(
            "ScatterplotLayer", id=LAYER_ID, data=rows, get_position=["lon", "lat"],
            get_fill_color="color", get_radius=15 if show_scores else 9,
            radius_units="'pixels'",  # literal entre comillas: pydeck trata el texto suelto como expresión
            stroked=True, get_line_color=[255, 255, 255], line_width_min_pixels=2, pickable=True,
        ),
    ]
    if show_scores:
        layers.append(pdk.Layer(
            "TextLayer", id="scores", data=rows, get_position=["lon", "lat"], get_text="text",
            get_size=12, get_color=[255, 255, 255], font_weight=700,
            get_text_anchor="'middle'", get_alignment_baseline="'center'",
        ))
    return pdk.Deck(
        layers=layers,
        initial_view_state=view,
        map_provider="carto", map_style="light",
        tooltip={
            "html": "<b>{title}</b><br/>{zone} · {price} €/mes<br/>{score} {label}",
            "style": {"backgroundColor": "#FFFFFF", "color": "#14102B", "fontSize": "13px",
                      "border": "1px solid #E6E3F0", "borderRadius": "10px", "padding": "8px 10px"},
        },
    )
