---
title: "tinySA AR Field Probe – Augmented Reality RF Mapping"
layout: default
---

<!-- Google Search Console Verification -->
<meta name="google-site-verification" content="Mu0UaeiUzNBmyU8B9NSmJ6elOTVqnPDK_F81MJbXFxY" />

# tinySA AR Field Probe  
### Augmented Reality Tool for RF Field Mapping using tinySA / tinySA-Plus

The **tinySA AR Field Probe** project combines near-field RF measurement with **augmented reality**, allowing real-time visualization of electromagnetic emissions captured by a probe synchronized with a **tinySA** or **tinySA-Plus** spectrum analyzer.

The system generates a live **RF heatmap** while automatically tracking the physical position of the probe via **CSRT visual tracking**.

---

## 🚀 Key Features

### 🔍 RF Measurements with tinySA / tinySA-Plus
- Automatic sweep detection and real sweep range reading  
- Peak detection (dBm and dBµV)  
- Dynamic color scale bar  
- CSV export of all measurements  

### 🎥 Augmented Reality Overlay
- Real-time video capture  
- CSRT probe tracking  
- Full-frame RF heatmap overlay  
- Professional-style measurement HUD  

### 🧪 Applications
- EMI / EMC diagnostics  
- PCB testing  
- Locating RF noise sources  
- Electronics R&D  
- Near-field probing  

---

## 📦 Source Code

GitHub repository:  
https://github.com/pauloonofre/tinySA-AR-field-probe

Included scripts:
- tinysa_ar_fieldProbe.py – Main program (AR + heatmap)
- tinySA.py – Serial interface with tinySA/tinySA-Plus
- Roboto-Regular.ttf – Optional font for better rendering

---

## 🛠 Installation

Install all dependencies:

```bash
pip install opencv-python numpy pillow pyserial
```

Run the tool:

```bash
python tinysa_ar_fieldProbe.py
```

---

## 🔎 SEO Keywords

tinysa, tinysa-plus, rf measurements, spectrum analyzer, augmented reality, heatmap, near field probe, emi testing, python opencv, rf mapping, electromagnetic field, rf visualization, tinySA AR

---

## 📄 License

This project is released under the **MIT License**.

---

## ✨ Contributing

Contributions, suggestions, and pull requests are welcome.

---

## 📬 Contact

Author: **Paulo Onofre**  
GitHub: https://github.com/pauloonofre

---
