# tinySA Heatmap AR – (Python 3.12)
# exportação CSV + PNG, tracking CSRT, dBm + dBµV
# v10 – correcções:
#   1. HUD mostra o START real configurado no tinySA (não o start após skip)
#   2. SKIP_START_POINTS reduzido de 20 para 8 (spike decai em ~7 pontos)
#   3. E-Export e Q-Quit separados correctamente no canto inferior direito

import cv2
import numpy as np
import time
import csv
import datetime
import os
from tinySA import tinySA
from PIL import Image, ImageDraw, ImageFont

SCAN_INTERVAL_SEC = 0.5
GRID_W = 40
GRID_H = 30

TOP_N         = 10
TABLE_STRIP_H = 260

# Pontos iniciais a saltar para eliminar spike DC/LO do tinySA Ultra+
# O spike decai tipicamente em 7-8 pontos independentemente da frequência de start.
# Aumente para 12-15 se persistir; diminua para 5 se perder sinal perto do start.
SKIP_START_POINTS = 8

# ============================
# Fontes (PIL)
# ============================

FONT_CANDIDATES = [
    "Roboto-Regular.ttf",
    "DejaVuSans.ttf",
    "Arial.ttf",
    "LiberationSans-Regular.ttf"
]

def load_font(size=24):
    for font in FONT_CANDIDATES:
        if os.path.exists(font):
            print(f"[INFO] Fonte carregada: {font}")
            return ImageFont.truetype(font, size)
    raise RuntimeError("Nenhuma fonte TTF encontrada. Coloque Roboto-Regular.ttf na pasta.")

FONT_MAIN  = load_font(28)
FONT_SMALL = load_font(22)
FONT_TABLE = load_font(18)
FONT_THEAD = load_font(18)

# ============================
# Texto HD via PIL
# ============================

def draw_text(img_cv, text, pos, font, color=(255, 255, 255)):
    img_pil = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    r, g, b = color
    draw.text((pos[0]+2, pos[1]+2), text, font=font, fill=(0, 0, 0, 255))
    draw.text(pos, text, font=font, fill=(r, g, b, 255))
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

# ============================
# Tabela Top-N picos
# ============================

def update_top_peaks(top_peaks, dbm, dbuv, freq, gx, gy, ts):
    entry = dict(dbm=dbm, dbuv=dbuv, freq=freq, gx=gx, gy=gy, ts=ts)
    top_peaks.append(entry)
    top_peaks.sort(key=lambda x: x["dbm"], reverse=True)
    del top_peaks[TOP_N:]


def draw_top_table(canvas, top_peaks, strip_y, w):
    row_h    = 20
    header_h = 24
    pad      = 8
    margin_x = 10

    cv2.rectangle(canvas, (0, strip_y), (w, strip_y + TABLE_STRIP_H), (10, 20, 40), -1)
    cv2.line(canvas, (0, strip_y), (w, strip_y), (0, 200, 255), 2)

    if not top_peaks:
        return canvas

    table_x2 = w - margin_x
    table_y2 = strip_y + TABLE_STRIP_H - 4
    cv2.rectangle(canvas, (margin_x, strip_y + 4), (table_x2, table_y2), (0, 210, 255), 1)

    sep_y = strip_y + pad + header_h
    cv2.line(canvas, (margin_x, sep_y), (table_x2, sep_y), (0, 180, 220), 1)

    img_pil = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))
    draw    = ImageDraw.Draw(img_pil)

    YELLOW = (255, 215,   0, 255)
    WHITE  = (255, 255, 255, 255)
    CYAN   = (  0, 230, 255, 255)
    SHADOW = (  0,   0,   0, 255)

    cx = {
        "#"         : margin_x + 4,
        "Hora"      : margin_x + 26,
        "dBm"       : margin_x + 120,
        "dBµV"      : margin_x + 196,
        "Freq(MHz)" : margin_x + 272,
        "Grid(x,y)" : margin_x + 400,
    }

    def txt(text, x, y, font, fill):
        draw.text((x+1, y+1), text, font=font, fill=SHADOW)
        draw.text((x,   y),   text, font=font, fill=fill)

    hy = strip_y + pad
    for label, x in cx.items():
        txt(label, x, hy, FONT_THEAD, CYAN)

    for idx, p in enumerate(top_peaks):
        ry    = sep_y + 4 + idx * row_h
        hora  = p["ts"][11:19]
        color = YELLOW if idx == 0 else WHITE
        txt(f"{idx+1}",               cx["#"],         ry, FONT_TABLE, color)
        txt(hora,                      cx["Hora"],      ry, FONT_TABLE, color)
        txt(f"{p['dbm']:+.2f}",       cx["dBm"],       ry, FONT_TABLE, color)
        txt(f"{p['dbuv']:.2f}",       cx["dBµV"],      ry, FONT_TABLE, color)
        txt(f"{p['freq']/1e6:.6f}",   cx["Freq(MHz)"], ry, FONT_TABLE, color)
        txt(f"({p['gx']},{p['gy']})", cx["Grid(x,y)"], ry, FONT_TABLE, color)

    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)


# ============================
# tinySA – init
# ============================

def init_tinysa():
    sa = tinySA()

    print("[INFO] A ler configuração do sweep...")
    s_start, s_stop, s_points = sa.get_sweep()
    print(f"[DEBUG] get_sweep() → start={s_start}, stop={s_stop}, points={s_points}")

    if s_stop is None or s_stop <= 0:
        s_stop = 300_000_000
    if s_points is None or s_points <= 0:
        s_points = 101

    s_start_real = s_start if (s_start is not None and s_start >= 0) else 0

    print(f"[INFO] Sweep real: {s_start_real/1e6:.4f} – {s_stop/1e6:.3f} MHz  ({s_points} pts)")

    sa.set_frequencies(s_start_real, s_stop, s_points)

    step_hz = (s_stop - s_start_real) / max(s_points - 1, 1)
    skip_up_to_mhz = (s_start_real + SKIP_START_POINTS * step_hz) / 1e6
    print(f"[INFO] Spike DC: a saltar primeiros {SKIP_START_POINTS} pontos "
          f"(zona {s_start_real/1e6:.4f}–{skip_up_to_mhz:.4f} MHz excluída da medição)")

    return sa, s_start_real, s_stop, s_points


# ============================
# Medição
# ============================

def medir_pico(sa):
    s = sa.data(0)
    f = sa.frequencies

    if s is None or len(s) == 0 or f is None or len(f) == 0:
        return None, None

    n = min(len(s), len(f))
    s, f = s[:n], f[:n]

    if n <= SKIP_START_POINTS:
        print(f"[WARN] Sweep com apenas {n} pontos.")
        return None, None

    # Saltar primeiros SKIP_START_POINTS para eliminar spike DC/LO
    idx_mask = np.zeros(n, dtype=bool)
    idx_mask[SKIP_START_POINTS:] = True

    s_filtrado = np.where(idx_mask, s, -np.inf)
    i = int(np.argmax(s_filtrado))

    return float(s[i]), float(f[i])


def dbm_to_dbuv(dbm):
    return dbm + 107.0

# ============================
# CSV + PNG
# ============================

def init_csv():
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"tinysa_export_{ts}.csv"
    with open(fname, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "dBm", "dBµV", "freq_Hz", "grid_x", "grid_y"])
    print(f"[INFO] CSV criado: {fname}")
    return fname

def append_csv(fname, dbm, dbuv, freq, gx, gy):
    with open(fname, "a", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            datetime.datetime.now().isoformat(),
            f"{dbm:.2f}", f"{dbuv:.2f}",
            int(freq), gx, gy
        ])

def export_png(img):
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"tinysa_export_{ts}.png"
    cv2.imwrite(fname, img)
    print(f"[PNG] Guardado → {fname}")

# ============================
# Heatmap
# ============================

def update_heatmap(mapdbm, gx, gy, val):
    gx = np.clip(gx, 0, GRID_W - 1)
    gy = np.clip(gy, 0, GRID_H - 1)
    old = mapdbm[gy, gx]
    mapdbm[gy, gx] = max(old, val) if np.isfinite(old) else val

def make_overlay(frame, mapdbm):
    h, w = frame.shape[:2]
    vals = mapdbm[np.isfinite(mapdbm)]
    if vals.size == 0:
        return frame, None, None

    vmin = float(np.min(vals))
    vmax = float(np.max(vals))

    norm = (mapdbm - vmin) / (vmax - vmin + 1e-12)
    norm = np.clip(norm, 0, 1)
    norm[np.isnan(norm)] = 0

    heat       = (norm * 255).astype(np.uint8)
    heat_big   = cv2.resize(heat, (w, h))
    heat_color = cv2.applyColorMap(heat_big, cv2.COLORMAP_JET)
    overlay    = cv2.addWeighted(frame, 0.40, heat_color, 0.60, 0)
    return overlay, vmin, vmax

def draw_colorbar(img, vmin, vmax, fh):
    if vmin is None or vmax is None:
        return img

    h, w   = img.shape[:2]
    bar_h  = int(fh * 0.55)
    bar_w  = 30
    margin = 25

    gradient  = np.linspace(255, 0, bar_h, dtype=np.uint8).reshape(bar_h, 1)
    gradient  = np.repeat(gradient, bar_w, axis=1)
    bar_color = cv2.applyColorMap(gradient, cv2.COLORMAP_JET)

    x0 = w - bar_w - margin
    y0 = 80

    img[y0:y0 + bar_h, x0:x0 + bar_w] = bar_color
    img = draw_text(img, f"{vmax:.1f} dBm", (x0 - 90, y0 + 5), FONT_SMALL)
    img = draw_text(img, f"{vmin:.1f} dBm", (x0 - 90, y0 + bar_h - 30), FONT_SMALL)
    return img

# ============================
# PROGRAMA PRINCIPAL
# ============================

def main():

    sa, s_start, s_stop, s_points = init_tinysa()
    csv_file = init_csv()

    cam_idx = int(input("Índice da câmara: "))

    cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(cam_idx)

    ok, frame = cap.read()
    if not ok:
        print("[ERR] Câmara não disponível.")
        return

    fh, fw   = frame.shape[:2]
    canvas_h = fh + TABLE_STRIP_H

    heatmap   = np.full((GRID_H, GRID_W), np.nan, dtype=np.float32)
    top_peaks = []

    tracker   = None
    last_scan = 0
    last_dbm  = None
    last_freq = None

    win = "tinySA AR"
    cv2.namedWindow(win)

    print("[INFO] Clique na sonda para iniciar tracking.")

    def on_mouse(event, x, y, flags, param):
        nonlocal tracker
        if event == cv2.EVENT_LBUTTONDOWN and y < fh:
            bbox = (x - 20, y - 20, 40, 40)
            tracker = cv2.TrackerCSRT_create()
            tracker.init(frame, bbox)
            print(f"[INFO] Tracker iniciado em ({x}, {y})")

    cv2.setMouseCallback(win, on_mouse)

    while True:

        ok, frame = cap.read()
        if not ok:
            break

        if tracker is not None:
            ok_t, bbox = tracker.update(frame)
            if ok_t:
                x, y, w, h = map(int, bbox)
                cx = x + w // 2
                cy = y + h // 2
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 255), 2)

                if time.time() - last_scan >= SCAN_INTERVAL_SEC:
                    dbm, freq = medir_pico(sa)
                    if dbm is not None:
                        dbuv      = dbm_to_dbuv(dbm)
                        last_dbm  = dbm
                        last_freq = freq
                        ts        = datetime.datetime.now().isoformat()

                        gx = int(cx / fw * GRID_W)
                        gy = int(cy / fh * GRID_H)
                        update_heatmap(heatmap, gx, gy, dbm)
                        append_csv(csv_file, dbm, dbuv, freq, gx, gy)
                        update_top_peaks(top_peaks, dbm, dbuv, freq, gx, gy, ts)

                    last_scan = time.time()

        # ── Overlay do vídeo ─────────────────────────────────────
        overlay, vmin, vmax = make_overlay(frame, heatmap)
        overlay = draw_colorbar(overlay, vmin, vmax, fh)

        # HUD superior – mostra o START real do tinySA (não o start após skip)
        if last_dbm is not None:
            dbuv = dbm_to_dbuv(last_dbm)
            txt  = f"PEAK: {last_dbm:.2f} dBm   {dbuv:.2f} dBµV   {last_freq/1e6:.6f} MHz"
        else:
            txt = "PEAK: a aguardar leitura..."

        overlay = draw_text(overlay, txt, (10, 20), FONT_MAIN)

        # START = frequência real configurada no tinySA
        sweep_txt = (f"START {s_start/1e6:.4f} MHz   "
                     f"STOP {s_stop/1e6:.3f} MHz   {s_points} pts")
        overlay = draw_text(overlay, sweep_txt, (10, 55), FONT_SMALL)

        # ── Botões: canto inferior direito da câmara, bem separados ──
        YELLOW_BTN = (255, 220, 50)
        overlay = draw_text(overlay, "E - Export", (fw - 170, fh - 65), FONT_SMALL, color=YELLOW_BTN)
        overlay = draw_text(overlay, "Q - Quit",   (fw - 170, fh - 35), FONT_SMALL, color=YELLOW_BTN)

        # ── Canvas final ─────────────────────────────────────────
        canvas = np.zeros((canvas_h, fw, 3), dtype=np.uint8)
        canvas[:fh, :] = overlay
        canvas = draw_top_table(canvas, top_peaks, fh, fw)

        cv2.imshow(win, canvas)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('e'):
            export_png(canvas)
        if key in (27, ord('q')):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
