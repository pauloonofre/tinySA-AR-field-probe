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

    def data(self, array=2):
        self.send_command(f"data {int(array)}\r")
        data = self.fetch_data()
        x = []
        for line in data.split("\n"):
            line = line.strip()
            if line:
                try:
                    x.append(float(line))
                except ValueError:
                    pass
        return np.array(x, dtype=float)

    def fetch_frequencies(self):
        self.send_command("frequencies\r")
        data = self.fetch_data()
        freqs = []
        for line in data.split("\n"):
            try:
                freqs.append(float(line.strip()))
            except:
                pass
        self._frequencies = np.array(freqs, dtype=float)

    # ==========================================================
    # NOVO → leitura automática do sweep do tinySA Plus
    # ==========================================================
    def get_sweep(self):
        """
        tinySA Plus devolve:  '<start> <stop> <points>'
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
                    stop = float(parts[1])
                    if len(parts) >= 3:
                        points = int(parts[2])
                except:
                    pass

        return start, stop, points
