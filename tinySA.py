#!/usr/bin/env python3
import serial
import numpy as np
from serial.tools import list_ports

VID = 0x0483
PID = 0x5740


def getport() -> str:
    device_list = list_ports.comports()
    for device in device_list:
        if device.vid == VID and device.pid == PID:
            return device.device
    raise OSError("tinySA device not found")


class tinySA:

    def __init__(self, dev=None):
        self.dev = dev or getport()
        self.serial = None
        self._frequencies = None
        self.points = 101

    def open(self):
        if self.serial is None:
            self.serial = serial.Serial(self.dev, timeout=1.0)

    def close(self):
        if self.serial is not None:
            self.serial.close()
        self.serial = None

    def send_command(self, cmd: str):
        self.open()
        if not cmd.endswith("\r"):
            cmd += "\r"
        self.serial.write(cmd.encode("utf-8"))
        try:
            self.serial.readline()
        except:
            pass

    def cmd(self, text: str) -> str:
        self.open()
        if not text.endswith("\r"):
            text += "\r"
        self.serial.write(text.encode("utf-8"))
        try:
            self.serial.readline()
        except:
            pass
        data = self.fetch_data()
        return data

    def set_sweep(self, start, stop):
        if start is not None:
            self.send_command(f"sweep start {int(start)}\r")
        if stop is not None:
            self.send_command(f"sweep stop {int(stop)}\r")

    def set_frequencies(self, start=1e6, stop=350e6, points=None):
        if points:
            self.points = points
        self._frequencies = np.linspace(start, stop, self.points)

    @property
    def frequencies(self):
        return self._frequencies

    def fetch_data(self) -> str:
        self.open()
        result = ""
        line = ""
        while True:
            c = self.serial.read().decode("utf-8", errors="ignore")
            if not c:
                break
            if c == "\r":
                continue
            line += c
            if c == "\n":
                result += line
                line = ""
                continue
            if line.endswith("ch>"):
                break
        return result

    def _parse_float_lines(self, raw: str) -> np.ndarray:
        """
        Parser robusto: aceita apenas linhas com um único token numérico.
        Rejeita linhas com 'ch>', 'sweep', múltiplos tokens ou não numéricas.
        """
        values = []
        for line in raw.split("\n"):
            line = line.strip()
            if not line:
                continue
            if "ch>" in line or "sweep" in line:
                continue
            parts = line.split()
            if len(parts) != 1:
                continue
            try:
                values.append(float(parts[0]))
            except ValueError:
                pass
        return np.array(values, dtype=float)

    def data(self, array=2):
        """
        array=2  → dados calibrados em dBm  (RECOMENDADO)
        array=0  → dados raw / pré-calibração (pode NÃO ser dBm)
        array=1  → dados armazenados
        """
        self.send_command(f"data {int(array)}\r")
        raw = self.fetch_data()
        return self._parse_float_lines(raw)

    def fetch_frequencies(self):
        self.send_command("frequencies\r")
        raw = self.fetch_data()
        freqs = self._parse_float_lines(raw)
        freqs = freqs[freqs > 0]   # frequências são sempre > 0
        self._frequencies = freqs

    def get_sweep(self):
        """
        tinySA / tinySA-Plus devolve: '<start> <stop> <points>'
        Ex.: '0 300000000 450'
        """
        txt = self.cmd("sweep")
        start = stop = points = None

        for line in txt.split("\n"):
            line = line.strip()
            if not line or line.startswith("ch>"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                try:
                    start = float(parts[0])
                    stop  = float(parts[1])
                    if len(parts) >= 3:
                        points = int(parts[2])
                    break
                except:
                    pass

        return start, stop, points
