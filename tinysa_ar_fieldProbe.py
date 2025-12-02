# tinySA Heatmap AR – (Python 3.12)
# exportação CSV + PNG, tracking CSRT, dBm + dBµV

import cv2
import numpy as np
import time
import platform
import csv
import datetime
import os
from tinySA import tinySA
from PIL import Image, ImageDraw, ImageFont

SCAN_INTERVAL_SEC = 0.5
GRID_W = 40
GRID_H = 30

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

# ============================
# Texto HD via PIL
# ============================

def draw_text(img_cv, text, pos, font):
    img_pil = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)

    draw.text((pos[0]+2, pos[1]+2), text, font=font, fill=(0,0,0,255))
    draw.text(pos, text, font=font, fill=(255,255,255,255))

    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

# ============================
# tinySA
# ============================

def init_tinysa():
    sa = tinySA()

    print("[INFO] Detectando sweep...")
    s_start, s_stop, s_points = sa.get_sweep()

    if s_start == 0:
        print("[WARN] Sweep 0 Hz → corrigido para 10 MHz.")
        s_start = 10_000_000

    print(f"[INFO] Sweep real: {s_start/1e6:.3f} – {s_stop/1e6:.3f} MHz ({s_points} pts)")
    sa.fetch_frequencies()

    return sa, s_start, s_stop, s_points

def medir_pico(sa):
    s = sa.data(0)
    f = sa.frequencies
    if s is None or len(s) == 0:
        return None, None
    i = int(np.argmax(s[:len(f)]))
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
            f"{dbm:.2f}",
            f"{dbuv:.2f}",
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
    gx = np.clip(gx, 0, GRID_W-1)
    gy = np.clip(gy, 0, GRID_H-1)
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

    heat = (norm * 255).astype(np.uint8)
    heat_big = cv2.resize(heat, (w, h))
    heat_color = cv2.applyColorMap(heat_big, cv2.COLORMAP_JET)

    overlay = cv2.addWeighted(frame, 0.40, heat_color, 0.60, 0)
    return overlay, vmin, vmax



def draw_colorbar(img, vmin, vmax):
    if vmin is None or vmax is None:
        return img

    h, w = img.shape[:2]
    bar_h = int(h * 0.75)
    bar_w = 30
    margin = 25

    gradient = np.linspace(255, 0, bar_h, dtype=np.uint8).reshape(bar_h, 1)
    gradient = np.repeat(gradient, bar_w, axis=1)
    bar_color = cv2.applyColorMap(gradient, cv2.COLORMAP_JET)

    x0 = w - bar_w - margin
    y0 = int((h - bar_h) / 2) + 20

    img[y0:y0+bar_h, x0:x0+bar_w] = bar_color

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
    fh, fw = frame.shape[:2]

    heatmap = np.full((GRID_H,GRID_W), np.nan, dtype=np.float32)

    tracker = None
    last_scan = 0
    last_dbm = None
    last_freq = None

    win = "tinySA AR"
    cv2.namedWindow(win)

    print("[INFO] Clique na sonda para iniciar tracking.")

    def on_mouse(event, x, y, flags, param):
        nonlocal tracker
        if event == cv2.EVENT_LBUTTONDOWN:
            bbox = (x-20, y-20, 40, 40)
            tracker = cv2.TrackerCSRT_create()
            tracker.init(frame, bbox)

    cv2.setMouseCallback(win, on_mouse)

    while True:

        ok, frame = cap.read()
        if not ok: break

        if tracker is not None:
            ok_t, bbox = tracker.update(frame)
            if ok_t:
                x, y, w, h = map(int, bbox)
                cx = x + w//2
                cy = y + h//2
                cv2.rectangle(frame,(x,y),(x+w,y+h),(0,255,255),2)

                if time.time() - last_scan >= SCAN_INTERVAL_SEC:
                    dbm, freq = medir_pico(sa)
                    if dbm is not None:
                        dbuv = dbm_to_dbuv(dbm)
                        last_dbm = dbm
                        last_freq = freq

                        gx = int(cx/fw * GRID_W)
                        gy = int(cy/fh * GRID_H)
                        update_heatmap(heatmap, gx, gy, dbm)
                        append_csv(csv_file, dbm, dbuv, freq, gx, gy)

                    last_scan = time.time()

        overlay, vmin, vmax = make_overlay(frame, heatmap)
        overlay = draw_colorbar(overlay, vmin, vmax)

        # ---------------------------
        # TEXTO SUPERIOR
        # ---------------------------

        if last_dbm is not None:
            dbuv = dbm_to_dbuv(last_dbm)
            txt = f"PEAK: {last_dbm:.2f} dBm   {dbuv:.2f} dBµV   {last_freq/1e6:.6f} MHz"
        else:
            txt = "PEAK: ---"

        overlay = draw_text(overlay, txt, (10, 20), FONT_MAIN)

        sweep_txt = f"START {s_start/1e6:.3f} MHz   STOP {s_stop/1e6:.3f} MHz   {s_points} pts"
        overlay = draw_text(overlay, sweep_txt, (10, 55), FONT_SMALL)

        # ---------------------------
        # HUD INFERIOR (sem caixa)
        # ---------------------------

        overlay = draw_text(overlay, "E - Export", (20, fh - 60), FONT_SMALL)
        overlay = draw_text(overlay, "Q - Quit",   (20, fh - 30), FONT_SMALL)

        cv2.imshow(win, overlay)
        key=cv2.waitKey(1)&0xFF

        if key==ord('e'):
            print("[EXPORT] CSV + PNG")
            export_png(overlay)

        if key in (27,ord('q')):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__=="__main__":
    main()

