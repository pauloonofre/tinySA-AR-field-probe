# tinySA AR Field Probe – Augmented Reality RF Mapping Tool

This project provides an augmented reality (AR) system for measuring and mapping RF emissions using the tinySA / tinySA-Plus spectrum analyzer.  
The software creates a real-time RF heatmap synchronized with the position of a physical near‑field probe tracked via computer vision (CSRT).

---
![Screenshot](screenshot.png)
## 🚀 Features

### 🔍 Augmented Reality Interface
- Live video overlay with RF heatmap
- Automatic probe tracking using CSRT
- Dynamic color scale based on measured signal levels
- Professional-style HUD display (Head-Up Display)

### 📡 tinySA / tinySA-Plus Integration
- Automatic sweep detection (start, stop, points)
- Real-time peak detection
- dBm → dBµV conversion
- Spatial mapping using a 40×30 grid

### 📤 Export Options
- PNG export with complete AR overlay
- CSV export including:
  - timestamp  
  - dBm  
  - dBµV  
  - frequency (Hz)  
  - grid coordinates (x, y)

---

## 📁 Repository Structure

```
tinysa_ar_fieldProbe.py   # Main AR + heatmap application
tinySA.py                 # USB serial interface for tinySA
Roboto-Regular.ttf        # Font used for high-quality HUD text
```

---

## ▶️ How to Run

```
python tinysa_ar_fieldProbe.py
```

Keyboard shortcuts:
- **E** – Export PNG + CSV  
- **Q / ESC** – Exit  

---

## 🛠️ Dependencies

Install with:

```
pip install opencv-python numpy pillow pyserial
```

---

## 📜 License

This project is released under the **MIT License**.

---

## 🙌 Credits

by **Paulo Onofre**, with support from ChatGPT following the author's specific instructions.  
All processing logic, UI layout, and integration details were designed by the author.

