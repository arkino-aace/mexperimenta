# Mexperimenta · motor de actualización (repositorio de Arkino)

Este repositorio NO contiene la web completa: solo lo necesario para que se actualice sola.
La web que ve el público vive en el hosting (mexperimenta.ultracinema.x10.mx).

## Qué hace cada noche (3:00 am CDMX) y al guardar `contenido.json`
1. `sync_arkino.py` lee Airtable (secreto `AIRTABLE_TOKEN`).
2. `build_real_collections.py` regenera las páginas de colecciones, la ficha (`pieza.html`) y `conteos.json`.
3. `build_datos.py` calcula las estadísticas de la página «El archivo en cifras» (`datos.json`, con las vistas públicas de Archive.org).
4. `build_destacados.py` y `build_stills.py` generan los fotogramas de la pieza destacada y de las tarjetas.
5. Guarda los cambios en este repositorio.
6. Si existen los secretos FTP, envía al hosting las páginas y datos regenerados.

## Secretos (Settings > Secrets and variables > Actions)
- `AIRTABLE_TOKEN` (obligatorio)
- `FTP_SERVER`, `FTP_USERNAME`, `FTP_PASSWORD` (para enviar al hosting) y, opcional, `FTP_DIR` (por defecto `/`)

## Qué NO está aquí (está solo en el hosting)
Imágenes (`capturas`, `capturas_min`, `assets/fondo`, `imagenes-locales`...), `index.html`, `guia.html`, `videoteca.html`, `admin.html`, `*.js`.

## Tarea manual ocasional
`build_capturas.py` genera `capturas.json` y `capturas_min/` a partir de la carpeta `capturas/`. Se ejecuta en una computadora cuando se añaden capturas nuevas (no corre en GitHub).
