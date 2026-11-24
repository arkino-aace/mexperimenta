#!/usr/bin/env python3
"""
build_destacados.py — prepara la "Pieza destacada" de la portada.

Lee los JSON que deja sync_arkino.py y genera destacados.json con dos listas:
  manual: piezas con la casilla `destacado` marcada en Airtable (cualquier colección)
  auto:   piezas publicadas, con video y no reservadas, de AUTO_COLECCIONES

Para cada pieza que entra y todavía no tiene fotograma (assets/destacados/<idn>.jpg)
saca uno del video de Internet Archive con ffmpeg: recorta bordes negros, reloj y
logo, y elige el cuadro más vistoso. Se descartan cuadros con demasiada piel
(filtro conservador, no infalible). Los trailers no entran al azar (solo si se
marcan como destacados a mano).
"""
import os, sys, json, subprocess, urllib.request, urllib.parse
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(HERE, "assets", "destacados")
AUTO_COLECCIONES = ["Gral. Treegan", "ULTRAcinema", "Archivos X"]
MAX_NUEVOS = 12          # fotogramas nuevos por ejecución
FUENTES = ["trailers_final.json", "gral_treegan_final.json", "ultracinema_final.json", "archivos_x_final.json"]
os.makedirs(OUTDIR, exist_ok=True)


def load(name):
    try:
        with open(os.path.join(HERE, name), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def clean(im):
    a = np.asarray(im.convert("L"), dtype=float)
    cols = np.where(a.mean(0) > 22)[0]; rows = np.where(a.mean(1) > 22)[0]
    if len(cols) < 50 or len(rows) < 50:
        return None
    x0, x1, y0, y1 = cols[0], cols[-1], rows[0], rows[-1]
    w, h = x1 - x0, y1 - y0
    if w < im.width * 0.5 or h < im.height * 0.5:
        return None
    x0 += int(w * .02); x1 -= int(w * .02); y0 += int(h * .09); y1 -= int(h * .10)
    return im.crop((x0, y0, x1, y1))


def skin_fraction(im):
    ycc = np.asarray(im.convert("YCbCr").resize((160, 100)), dtype=float)
    cr, cb = ycc[..., 1], ycc[..., 2]
    return float(((cr > 140) & (cr < 175) & (cb > 85) & (cb < 125)).mean())


def score(im):
    a = np.asarray(im.convert("L").resize((160, 100)), dtype=float)
    m, s = a.mean(), a.std()
    if m < 55 or m > 205 or s < 38:
        return 0
    if skin_fraction(im) > 0.35:
        return 0
    sat = np.asarray(im.convert("HSV").resize((160, 100)))[..., 1].mean()
    return s + 0.15 * sat


def video_url(archive_id):
    m = json.load(urllib.request.urlopen("https://archive.org/metadata/" + archive_id, timeout=40))
    fs = [f for f in m.get("files", []) if f["name"].lower().endswith(".mp4")]
    if not fs:
        return None, 0
    f = sorted(fs, key=lambda x: int(x.get("size", 0) or 0))[0]
    url = "https://archive.org/download/%s/%s" % (archive_id, urllib.parse.quote(f["name"]))
    try:
        dur = float(f.get("length") or 0)
    except ValueError:
        dur = 0
    if dur < 5:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", url],
                           capture_output=True, text=True, timeout=60)
        dur = float(r.stdout.strip() or 30)
    return url, dur


def make_frame(piece):
    dest = os.path.join(OUTDIR, piece["idn"] + ".jpg")
    try:
        url, dur = video_url(piece["archiveId"])
        if not url:
            return False
        best = None
        for k, fr in enumerate((0.15, 0.4, 0.65, 0.85)):
            tmp = os.path.join(OUTDIR, "_tmp%d.jpg" % k)
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(dur * fr), "-i", url, "-frames:v", "1",
                            "-vf", "scale=1400:-2", "-q:v", "4", tmp], capture_output=True, timeout=120)
            if os.path.exists(tmp) and os.path.getsize(tmp) > 5000:
                c = clean(Image.open(tmp).convert("RGB"))
                if c is not None:
                    sc = score(c)
                    if sc > 0 and (best is None or sc > best[0]):
                        best = (sc, c)
            if os.path.exists(tmp):
                os.remove(tmp)
        if best:
            c = best[1]; c.thumbnail((900, 900)); c.save(dest, quality=78, optimize=True)
            return True
    except Exception as e:
        print("  sin fotograma para", piece["idn"], "-", str(e)[:80])
    return False


def entry(p, coll_page):
    has_img = os.path.exists(os.path.join(OUTDIR, p["idn"] + ".jpg"))
    link = ("pieza.html?id=" + urllib.parse.quote(p["idn"])) if p["coll"] in ("Avances Cinematográficos", "Gral. Treegan") else coll_page
    return {"idn": p["idn"], "title": p["title"], "year": p.get("year", ""), "coll": p["coll"],
            "desc": p.get("desc", ""), "fmt": p.get("fmt", ""),
            "img": ("assets/destacados/%s.jpg" % p["idn"]) if has_img else "", "link": link}


def main():
    pages = {"Avances Cinematográficos": "avances-cinematograficos.html", "Gral. Treegan": "gral-treegan.html",
             "ULTRAcinema": "ultracinema.html", "Archivos X": "archivos-x.html"}
    todas = [p for n in FUENTES for p in load(n)]
    ok = [p for p in todas if not p.get("sensitive") and p.get("title") and p["title"] != "(sin título)"]
    manual_src = [p for p in ok if p.get("featured")]
    auto_src = [p for p in ok if p.get("archiveId") and p["coll"] in AUTO_COLECCIONES]

    nuevos = 0
    for p in manual_src + auto_src:
        if nuevos >= MAX_NUEVOS:
            break
        if p.get("archiveId") and not os.path.exists(os.path.join(OUTDIR, p["idn"] + ".jpg")):
            if make_frame(p):
                nuevos += 1
                print("  fotograma nuevo:", p["idn"])

    manual = [entry(p, pages[p["coll"]]) for p in manual_src]
    auto = [e for e in (entry(p, pages[p["coll"]]) for p in auto_src) if e["img"]]
    with open(os.path.join(HERE, "destacados.json"), "w", encoding="utf-8") as f:
        json.dump({"manual": manual, "auto": auto}, f, ensure_ascii=False, indent=1)
    print("destacados.json: %d manuales, %d automáticos (%d fotogramas nuevos)" % (len(manual), len(auto), nuevos))


if __name__ == "__main__":
    main()
