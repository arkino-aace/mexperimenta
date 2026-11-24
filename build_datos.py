#!/usr/bin/env python3
"""Genera datos.json (estadísticas del catálogo + vistas públicas de Archive.org) para datos.html.
Lee all_pieces.json y conteos.json (ya generados por el flujo). Si Archive.org no responde,
conserva las vistas de la última vez. Uso: python3 build_datos.py"""
import json, os, re, collections, datetime, urllib.request, concurrent.futures as cf

HERE = os.path.dirname(os.path.abspath(__file__))
def P(n): return os.path.join(HERE, n)

def load(n, default):
    try:
        with open(P(n), encoding="utf-8") as f: return json.load(f)
    except Exception: return default

def seconds(d):
    d = (d or "").strip().lower().replace("min", "").strip()
    m = re.fullmatch(r"(\d+):(\d{2}):(\d{2})", d)
    if m: return int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3])
    m = re.fullmatch(r"(\d+):(\d{2})", d)
    if m: return int(m[1]) * 60 + int(m[2])
    return None

def year(y):
    m = re.search(r"\b(1[89]\d\d|20[0-3]\d)\b", str(y or ""))
    return int(m[1]) if m else None

def norm_color(c):
    c = (c or "").lower()
    if "negro" in c or "b&n" in c or "b/n" in c or c == "bn": return "Blanco y negro"
    if "color" in c: return "Color"
    return None

def norm_lang(l):
    l = (l or "").strip()
    if not l: return None
    if l.lower() in ("es", "español", "espanol", "castellano"): return "Español"
    if l.lower() == "silente": return "Silente"
    if l.lower() in ("en", "eng", "inglés", "ingles"): return "Inglés"
    return l.capitalize()

def tally(values, top=None):
    c = collections.Counter(v for v in values if v)
    items = c.most_common(top)
    return [{"k": k, "n": n} for k, n in items]

def ia_views(ids, previo):
    def f(i):
        try:
            req = urllib.request.Request("https://be-api.us.archive.org/views/v1/short/" + i, headers={"User-Agent": "mexperimenta-datos"})
            return i, json.loads(urllib.request.urlopen(req, timeout=25).read())[i]
        except Exception:
            return i, None
    with cf.ThreadPoolExecutor(8) as ex: res = dict(ex.map(f, ids))
    if sum(1 for v in res.values() if v) < len(ids) * 0.5:   # Archive.org no respondió bien: conservar lo anterior
        print("Archive.org: respuesta incompleta, se conservan las vistas anteriores")
        return previo
    return res

def main():
    piezas = load("all_pieces.json", [])
    conteos = load("conteos.json", {})
    previo = load("datos.json", {})
    ids = sorted({p["archiveId"] for p in piezas if p.get("archiveId")})
    vistas = ia_views(ids, previo.get("_vistas_raw", {}))
    seg = [s for s in (seconds(p.get("duration")) for p in piezas) if s]
    anios = [y for y in (year(p.get("year")) for p in piezas) if y]
    decadas = tally(["%ds" % (y // 10 * 10) for y in anios])
    decadas.sort(key=lambda x: x["k"])
    tags = collections.Counter(t for p in piezas for t in (p.get("tags") or []))
    top = []
    tit = {p.get("archiveId"): (p.get("title_es") or p.get("title") or p.get("idn")) + " · " + (p.get("idn") or "") for p in piezas}
    reservado = {p.get("archiveId") for p in piezas if p.get("sensitive")}
    for i, v in vistas.items():
        if v and v.get("all_time") and i not in reservado: top.append({"k": tit.get(i, i), "n": v["all_time"], "id": i})
    top.sort(key=lambda x: -x["n"])
    vv = [v for v in vistas.values() if v]
    out = {
        "generado": datetime.date.today().isoformat(),
        "piezas": len(piezas),
        "videos": len(ids),
        "colecciones": {k: v for k, v in conteos.items() if k != "total"},
        "total_catalogo": conteos.get("total"),
        "horas_contenido": round(sum(seg) / 3600, 1),
        "piezas_con_duracion": len(seg),
        "duracion_media_min": round(sum(seg) / len(seg) / 60, 1) if seg else None,
        "anio_min": min(anios) if anios else None, "anio_max": max(anios) if anios else None,
        "piezas_con_anio": len(anios),
        "formatos": tally([p.get("fmt") for p in piezas]),
        "color": tally([norm_color(p.get("color")) for p in piezas]),
        "idiomas": tally([norm_lang(p.get("lang")) for p in piezas], 8),
        "decadas": decadas,
        "etiquetas": [{"k": k, "n": n} for k, n in tags.most_common(15)],
        "ia": {
            "videos_con_datos": sum(1 for v in vv if v.get("have_data")),
            "vistas_total": sum(v.get("all_time", 0) for v in vv),
            "vistas_30d": sum(v.get("last_30day", 0) for v in vv),
            "vistas_7d": sum(v.get("last_7day", 0) for v in vv),
            "top": top[:10],
        },
        "_vistas_raw": {i: v for i, v in vistas.items() if v},
    }
    with open(P("datos.json"), "w", encoding="utf-8") as f: json.dump(out, f, ensure_ascii=False, indent=1)
    print("datos.json: %d piezas, %.1f h de contenido, %d vistas en Archive.org" % (out["piezas"], out["horas_contenido"], out["ia"]["vistas_total"]))

if __name__ == "__main__":
    main()
