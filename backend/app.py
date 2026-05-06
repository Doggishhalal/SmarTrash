#!/usr/bin/env python3
"""
SmarTrash - Einfache Desktop-Anwendung
Fokus: Funktioniert zuverlässig & ist leicht zu bedienen
"""

import os
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

import cv2
import numpy as np
from PIL import Image, ImageTk

# ============================================================================
# SETUP & PATHS
# ============================================================================

# Current directory
BACKEND_DIR = Path(__file__).parent.absolute()
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

# Environment
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["YOLOX_DEVICE"] = "cpu"

# Modell - zentraler Fallback: Env -> yolox_l -> yolox_m -> yolox_s
MODEL_PATH = os.environ.get("YOLOX_CKPT", "").strip()
if not MODEL_PATH or not os.path.exists(MODEL_PATH):
    model_candidates = [
        "C:\\models\\yolox_l.pth",
        "C:\\models\\yolox_m.pth",
        "C:\\models\\yolox_s.pth",
    ]
    MODEL_PATH = next((path for path in model_candidates if os.path.exists(path)), model_candidates[-1])

if not os.path.exists(MODEL_PATH):
    print("[-] FEHLER: YOLOX Modell nicht gefunden!")
    print(f"   Erwartet: {MODEL_PATH}")
    sys.exit(1)

# Setze explizit für inference.py
os.environ["YOLOX_CKPT"] = MODEL_PATH

def _infer_yolox_exp_from_path(path: str) -> str:
    name = os.path.basename(str(path or "")).lower()
    for key in ["yolox_x", "yolox_l", "yolox_m", "yolox_s", "yolox_tiny", "yolox_nano"]:
        if key in name:
            return key
    return "yolox_s"

os.environ.setdefault("YOLOX_EXP_NAME", _infer_yolox_exp_from_path(MODEL_PATH))

# ============================================================================
# IMPORTS - Minimal aber funktional
# ============================================================================

try:
    from inference import detect_image
    from quality_controller import get_quality_controller
    from waste_classifier import get_classifier
    print("[OK] Module geladen")
except Exception as e:
    print(f"[!]  Import-Fehler: {e}")
    print("   App startet trotzdem im Basis-Modus...")


# ============================================================================
# CAMERA HELPER - Robuste Kamera-Unterstützung
# ============================================================================

class CameraHandler:
    """Zuverlässiger Kamera-Zugriff mit Fallbacks"""

    def __init__(self):
        self.cap = None
        self.device_id = 0
        self.error_count = 0

    def open(self):
        """Öffne Kamera mit mehreren Versuchen"""
        if self.cap is not None:
            self.release()

        # Versuche verschiedene Geräte-IDs
        for backend in [cv2.CAP_DSHOW, cv2.CAP_ANY]:
            for device_id in [0, 1, 2, -1]:
                try:
                    cap = cv2.VideoCapture(device_id, backend)
                    if cap.isOpened():
                        # Setze beste Einstellungen
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                        cap.set(cv2.CAP_PROP_FPS, 30)
                        cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)

                        # Warmup + Test-Read
                        for _ in range(3):
                            cap.read()
                        ret, _ = cap.read()
                        if ret:
                            self.cap = cap
                            self.device_id = device_id
                            self.error_count = 0
                            print(f"[OK] Kamera geöffnet (Device {device_id}, backend={backend})")
                            return True
                        cap.release()
                except Exception as e:
                    print(f"  Device {device_id} (backend={backend}): {e}")
                    continue

        return False

    def read(self):
        """Lese Frame von Kamera"""
        if self.cap is None:
            return False, None

        try:
            ret, frame = self.cap.read()
            if ret and frame is not None:
                # Spiegele für Mirror-Effekt (wie Spiegel)
                frame = cv2.flip(frame, 1)
                self.error_count = 0
                return ret, frame

            # Error: Try reconnect
            self.error_count += 1
            if self.error_count > 10:
                self.release()
                return False, None

            return False, None
        except Exception as e:
            print(f"Camera read error: {e}")
            self.error_count += 1
            return False, None

    def release(self):
        """Schließe Kamera"""
        if self.cap is not None:
            self.cap.release()
            self.cap = None


# ============================================================================
# MAIN GUI APP
# ============================================================================

class SmarTrashApp:
    def __init__(self, root):
        self.root = root
        self.root.title("[TRASH] SmarTrash - Intelligente Müllsortierung")
        self.root.geometry("1300x850")
        self.root.minsize(1000, 700)

        # Farben
        self.bg_primary = "#1a1a1a"
        self.bg_secondary = "#2d2d2d"
        self.color_success = "#27ae60"
        self.color_warning = "#f39c12"
        self.color_error = "#e74c3c"
        self.color_info = "#3498db"

        self.root.configure(bg=self.bg_primary)

        # State
        self.camera = CameraHandler()
        self.camera_running = False
        self.current_frame = None
        self.last_detections = []
        self.last_detection_frame = None
        self.last_detection_time = 0.0
        self.detect_overlay_hold_sec = 1.6
        self.detection_counter = 0
        self.camera_thread = None
        self.detect_running = False

        # Auto-Detection
        self.auto_detect = False
        self.auto_detect_interval = 3.0  # Sekunden zwischen Auto-Detections
        self.last_auto_detect_time = 0

        # Display transformation (für korrekte Bounding Box Position)
        self.display_scale = 1.0
        self.display_pad_left = 0
        self.display_pad_top = 0

        # Manual focus selection (click-to-select)
        self.manual_focus_box = None
        self.manual_focus_hint = None
        self.manual_focus_label = None
        self.manual_focus_expires_at = 0.0
        self.manual_focus_hold_sec = 6.0
        self.track_memory = []
        self.next_track_id = 1

        # Statistics
        self.stats_today = {'Restmüll': 0, 'Biomüll': 0, 'Papiermüll': 0, 'Gelbe Tonne': 0, 'Glascontainer': 0}
        self.startup_ai_report = None
        self.learning_focus_snapshot = {}
        self.analysis_started_at = 0.0

        # Build UI
        self._build_ui()

        # Run AI warmup + self-optimization in background without blocking the GUI.
        self.root.after(1200, self._start_background_ai_bootstrap)
        self.root.after(2200, self._start_background_auto_retrain)

    # ========================================================================
    # UI BUILD
    # ========================================================================

    def _build_ui(self):
        """Baue komplette UI"""

        # === HEADER ===
        header = tk.Frame(self.root, bg="#1c1c1c", height=70)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        title = tk.Label(
            header,
            text="[TRASH] SmarTrash - KI-Müllsortierung",
            font=("Segoe UI", 20, "bold"),
            bg="#1c1c1c",
            fg="white"
        )
        title.pack(pady=15)

        # === MAIN CONTENT ===
        content = tk.Frame(self.root, bg=self.bg_primary)
        content.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # --- Linke Seite: Kamera & Steuerung ---
        left = tk.Frame(content, bg=self.bg_secondary)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # Kamera-Header
        camera_header = tk.Label(
            left,
            text="[PHOTO] Live Kamera / Bild",
            font=("Segoe UI", 14, "bold"),
            bg=self.bg_secondary,
            fg="white"
        )
        camera_header.pack(pady=10)

        # Kamera Display - mit initialisiertem schwarzem Bild
        self.camera_label = tk.Label(
            left,
            bg="black",
            width=640,
            height=480
        )
        self.camera_label.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.camera_label.bind("<Button-1>", self._on_camera_click)

        # Initiales schwarzes Bild
        try:
            black = Image.new('RGB', (640, 480), color='black')
            photo = ImageTk.PhotoImage(black)
            self.camera_label.config(image=photo)
            self.camera_label.image = photo
            print("[OK] Camera label initialized with black image")
        except Exception as e:
            print(f"[!] Failed to initialize camera label: {e}")

        # Buttons
        button_frame = tk.Frame(left, bg=self.bg_secondary)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        self.camera_btn = tk.Button(
            button_frame,
            text="▶️ Kamera starten",
            font=("Segoe UI", 11, "bold"),
            bg=self.color_success,
            fg="white",
            command=self._toggle_camera,
            relief=tk.FLAT,
            padx=15,
            pady=10
        )
        self.camera_btn.pack(side=tk.LEFT, padx=5)

        self.capture_btn = tk.Button(
            button_frame,
            text="📸 Analysieren",
            font=("Segoe UI", 11, "bold"),
            bg=self.color_info,
            fg="white",
            command=self._capture_and_detect,
            relief=tk.FLAT,
            padx=15,
            pady=10,
            state=tk.DISABLED
        )
        self.capture_btn.pack(side=tk.LEFT, padx=5)

        # Auto-Detect Toggle
        self.auto_btn = tk.Button(
            button_frame,
            text="🤖 Auto: AUS",
            font=("Segoe UI", 11, "bold"),
            bg="#555555",
            fg="white",
            command=self._toggle_auto_detect,
            relief=tk.FLAT,
            padx=15,
            pady=10,
            state=tk.DISABLED
        )
        self.auto_btn.pack(side=tk.LEFT, padx=5)

        load_btn = tk.Button(
            button_frame,
            text="📁 Bild laden",
            font=("Segoe UI", 11, "bold"),
            bg=self.color_warning,
            fg="white",
            command=self._load_image,
            relief=tk.FLAT,
            padx=15,
            pady=10
        )
        load_btn.pack(side=tk.LEFT, padx=5)

        # --- Rechte Seite: Ergebnisse ---
        right = tk.Frame(content, bg=self.bg_secondary)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))

        # === BIN VISUALIZATION ===
        bin_frame = tk.Frame(right, bg=self.bg_secondary)
        bin_frame.pack(pady=10, padx=10, fill=tk.X)

        bin_header = tk.Label(
            bin_frame,
            text="🗑️ Empfohlener Behälter",
            font=("Segoe UI", 12, "bold"),
            bg=self.bg_secondary,
            fg="white"
        )
        bin_header.pack()

        # Bin buttons grid
        bin_grid = tk.Frame(bin_frame, bg=self.bg_secondary)
        bin_grid.pack(pady=5)

        self.bin_buttons = {}
        bins = [
            ('Restmüll', '⚫', '#555555'),
            ('Biomüll', '🟢', '#27ae60'),
            ('Papiermüll', '🔵', '#3498db'),
            ('Gelbe Tonne', '🟡', '#f39c12')
        ]

        for i, (name, emoji, color) in enumerate(bins):
            btn = tk.Button(
                bin_grid,
                text=f"{emoji}\n{name}",
                font=("Segoe UI", 10, "bold"),
                bg=self.bg_primary,
                fg="white",
                width=12,
                height=3,
                relief=tk.FLAT,
                bd=2
            )
            btn.grid(row=i//2, column=i%2, padx=5, pady=5)
            self.bin_buttons[name] = {'button': btn, 'color': color, 'default_bg': self.bg_primary}

        # === STATISTICS PANEL ===
        stats_frame = tk.Frame(right, bg=self.bg_primary)
        stats_frame.pack(pady=5, padx=10, fill=tk.X)

        self.stats_label = tk.Label(
            stats_frame,
            text="📊 Heute: 0 Objekte | Restmüll: 0 | Bio: 0 | Papier: 0 | Gelb: 0",
            font=("Segoe UI", 9),
            bg=self.bg_primary,
            fg="#95a5a6",
            anchor='w'
        )
        self.stats_label.pack(padx=10, pady=5, fill=tk.X)

        # Results Header
        results_header = tk.Label(
            right,
            text="[TARGET] Detaillierte Ergebnisse",
            font=("Segoe UI", 12, "bold"),
            bg=self.bg_secondary,
            fg="white"
        )
        results_header.pack(pady=(10,5))

        # Results Text
        self.results_text = tk.Text(
            right,
            font=("Consolas", 9),
            bg=self.bg_primary,
            fg="white",
            wrap=tk.WORD,
            relief=tk.FLAT,
            padx=10,
            pady=10,
            height=15
        )
        self.results_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.results_text.insert(tk.END, "Warte auf Analyse...\n")

        # === FEEDBACK BUTTONS ===
        feedback_frame = tk.Frame(right, bg=self.bg_secondary)
        feedback_frame.pack(pady=10, padx=10, fill=tk.X)

        self.feedback_correct_btn = tk.Button(
            feedback_frame,
            text="✅ Richtig erkannt",
            font=("Segoe UI", 10, "bold"),
            bg=self.color_success,
            fg="white",
            command=self._feedback_correct,
            relief=tk.FLAT,
            padx=15,
            pady=8,
            state=tk.DISABLED
        )
        self.feedback_correct_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        self.feedback_wrong_btn = tk.Button(
            feedback_frame,
            text="❌ Falsch - Korrigieren",
            font=("Segoe UI", 10, "bold"),
            bg=self.color_error,
            fg="white",
            command=self._feedback_wrong,
            relief=tk.FLAT,
            padx=15,
            pady=8,
            state=tk.DISABLED
        )
        self.feedback_wrong_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        self.manual_draw_btn = tk.Button(
            feedback_frame,
            text="🎨 Manuell Zeichnen",
            font=("Segoe UI", 10, "bold"),
            bg="#9b59b6",
            fg="white",
            command=self._start_manual_draw_mode,
            relief=tk.FLAT,
            padx=15,
            pady=8,
            state=tk.DISABLED
        )
        self.manual_draw_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        # === STATUS BAR ===
        status = tk.Frame(self.root, bg="#1c1c1c", height=40)
        status.pack(fill=tk.X, side=tk.BOTTOM)
        status.pack_propagate(False)

        self.status_label = tk.Label(
            status,
            text="[IDLE] Bereit",
            font=("Segoe UI", 10),
            bg="#1c1c1c",
            fg="white",
            anchor="w",
            padx=15
        )
        self.status_label.pack(fill=tk.BOTH, expand=True)

    # ========================================================================
    # SYSTEM CHECK
    # ========================================================================

    def _check_system(self):
        """Überprüfe System-Status"""

        # Model Check
        if os.path.exists(MODEL_PATH):
            size_mb = os.path.getsize(MODEL_PATH) / (1024 * 1024)
            msg = f"[OK] Model vorhanden: {size_mb:.0f} MB"
            self._set_status(msg, "success")
        else:
            msg = "[-] YOLOX Model nicht gefunden!"
            self._set_status(msg, "error")
            messagebox.showerror(
                "Model fehlt",
                f"YOLOX Model nicht gefunden:\n{MODEL_PATH}\n\n"
                "Bitte lade das Model herunter!"
            )

    def _start_background_ai_bootstrap(self):
        """Startet nicht-blockierendes Selbstlernen beim App-Start."""
        thread = threading.Thread(target=self._startup_ai_bootstrap_worker, daemon=True)
        thread.start()

    def _startup_ai_bootstrap_worker(self):
        """Lädt lokales Wissen vor und führt optional online-validierte Selbstoptimierung aus."""
        try:
            from learning_db import get_db
            from web_knowledge import get_fetcher

            db = get_db()
            fetcher = get_fetcher()
            report = fetcher.auto_self_learn_on_recognition_issue(
                db=db,
                trigger_objects=list(fetcher.ONLINE_SELF_LEARN_PRIORITY_TERMS),
                include_priority_terms=True,
                max_terms=180,
                force=False,
            )
            self.startup_ai_report = report

            try:
                db.add_self_improvement_run(
                    event_type="desktop_startup_auto",
                    status=str(report.get("status", "unknown")),
                    report=report,
                )
            except Exception:
                pass

            local_terms = int(report.get("local_seed_terms", 0) or 0)
            online_terms = int(report.get("live_enriched_terms", 0) or 0)
            msg = f"[AI] Startup-Lernen aktiv (lokal:{local_terms}, online:{online_terms})"
            self.root.after(0, lambda m=msg: self._set_status(m, "info"))
        except Exception as e:
            self.root.after(0, lambda: self._set_status(f"[AI] Startup-Lernen übersprungen: {e}", "warning"))

    def _start_background_auto_retrain(self):
        thread = threading.Thread(target=self._auto_retrain_worker, daemon=True)
        thread.start()

    def _auto_retrain_worker(self):
        """Optionaler woechentlicher Retrain-Check basierend auf Konfiguration."""
        try:
            from auto_retrain import run_if_due
            from learning_db import get_db

            db = get_db()
            result = run_if_due(db=db)
            status = str(result.get("status", "unknown"))
            if status == "started":
                self.root.after(0, lambda: self._set_status("[AI] Retrain gestartet (Hintergrund)", "info"))
            elif status == "not_configured":
                self.root.after(0, lambda: self._set_status("[AI] Retrain nicht konfiguriert", "warning"))
        except Exception as e:
            self.root.after(0, lambda: self._set_status(f"[AI] Retrain-Check fehlgeschlagen: {e}", "warning"))

    def _get_learning_focus_snapshot(self):
        """Liefert aktuelle Lernziele für fokussierte Klassenverbesserung."""
        try:
            from learning_db import get_db

            db = get_db()
            priorities = db.get_priority_feedback_classes(limit=3)
            review_queue = db.get_pending_review_cases(limit=20)
            trend = db.get_recent_feedback_error_rates(window=80)

            top = priorities[0] if priorities else None
            return {
                "top_priority": top,
                "priorities": priorities,
                "review_queue_count": len(review_queue),
                "error_trend": trend.get("trend", "unknown"),
                "recent_error_rate": float(trend.get("recent_error_rate", 0.0)),
            }
        except Exception:
            return {
                "top_priority": None,
                "priorities": [],
                "review_queue_count": 0,
                "error_trend": "unknown",
                "recent_error_rate": 0.0,
            }

    # ========================================================================
    # CAMERA CONTROL
    # ========================================================================

    def _toggle_camera(self):
        """Starte/stoppe Kamera"""
        if not self.camera_running:
            self._start_camera()
        else:
            self._stop_camera()

    def _toggle_auto_detect(self):
        """Toggle Auto-Detection"""
        self.auto_detect = not self.auto_detect

        if self.auto_detect:
            self.auto_btn.config(text="🤖 Auto: EIN", bg=self.color_success)
            self._set_status(f"[AUTO] Erkennung alle {self.auto_detect_interval}s", "success")
            self.last_auto_detect_time = 0  # Trigger sofort beim Aktivieren
            print(f"[AUTO] Auto-detection enabled (interval: {self.auto_detect_interval}s)")
        else:
            self.auto_btn.config(text="🤖 Auto: AUS", bg="#555555")
            self._set_status("[MANUAL] Manuelle Erkennung", "info")
            print("[AUTO] Auto-detection disabled")

    def _start_camera(self):
        """Starte Kamera-Stream"""
        if self.camera_running:
            print("[DEBUG] Camera already running")
            return

        print("[DEBUG] Opening camera...")
        if not self.camera.open():
            self._set_status("[-] Kamera nicht verfügbar", "error")
            messagebox.showerror(
                "Kamera-Fehler",
                "Kamera konnte nicht geöffnet werden!\n\n"
                "Mögliche Lösungen:\n"
                "• Verbinde eine USB-Kamera\n"
                "• Starte die App neu\n"
                "• Wechsle USB-Port\n\n"
                "Nutze stattdessen 'Bild laden'!"
            )
            return

        self.camera_running = True
        self.camera_btn.config(text="[STOP] Kamera stoppen", bg=self.color_error)
        self.capture_btn.config(state=tk.NORMAL)
        self.auto_btn.config(state=tk.NORMAL)
        self._set_status("[ACTIVE] Kamera aktiv", "success")
        print("[DEBUG] Camera opened successfully")

        # Starte Camera Thread
        self.camera_thread = threading.Thread(target=self._camera_loop, daemon=True)
        self.camera_thread.start()
        print("[DEBUG] Camera thread started")

    def _stop_camera(self):
        """Stoppe Kamera sauber"""
        print("[DEBUG] Stopping camera...")
        self.camera_running = False

        # Warte auf Thread-Ende
        if self.camera_thread and self.camera_thread.is_alive():
            print("[DEBUG] Waiting for camera thread to finish...")
            self.camera_thread.join(timeout=1.0)
            if self.camera_thread.is_alive():
                print("[WARN] Camera thread did not stop in time")

        # Release camera hardware
        self.camera.release()
        self.camera_thread = None
        print("[DEBUG] Camera released")

        # Update UI
        self.camera_btn.config(text="▶️ Kamera starten", bg=self.color_success)
        self.capture_btn.config(state=tk.DISABLED)
        self.auto_btn.config(state=tk.DISABLED)

        # Disable auto-detect when camera stops
        if self.auto_detect:
            self.auto_detect = False
            self.auto_btn.config(text="🤖 Auto: AUS", bg="#555555")

        self._set_status("[IDLE] Kamera gestoppt", "info")

        # Zeige schwarzes Bild
        black = Image.new('RGB', (640, 480), color='black')
        photo = ImageTk.PhotoImage(black)
        self.camera_label.config(image=photo)
        self.camera_label.image = photo

    def _camera_loop(self):
        """Kamera-Update Loop mit Error Handling"""
        loop_count = 0
        error_count = 0
        last_error = None

        while self.camera_running:
            try:
                ret, frame = self.camera.read()

                if not ret or frame is None:
                    error_count += 1
                    if error_count % 30 == 0:
                        print(f"[!] Camera read failed #{error_count}")
                    time.sleep(0.1)
                    continue

                # Reset error counter on successful read
                if error_count > 0:
                    print(f"[OK] Camera recovered after {error_count} errors")
                    error_count = 0

                self.current_frame = frame.copy()


                # Auto-Detection Check
                if self.auto_detect and not self.detect_running:
                    current_time = time.time()
                    if current_time - self.last_auto_detect_time >= self.auto_detect_interval:
                        self.last_auto_detect_time = current_time
                        print("[AUTO] Triggering auto-detection...")
                        self.root.after(0, lambda: self._capture_and_detect())

                # Zeige im Label im UI-Thread (ohne Boxen - die werden separat gezeichnet)
                self.root.after(0, lambda f=frame.copy(): self._show_frame(f))
                loop_count += 1

                if loop_count % 100 == 0:
                    print(f"[OK] Camera loop: {loop_count} frames displayed")

                time.sleep(0.033)  # ~30 FPS

            except Exception as e:
                if str(e) != str(last_error):
                    print(f"[!] Camera loop error: {type(e).__name__}: {e}")
                    last_error = e
                error_count += 1
                time.sleep(0.1)

    def _show_frame(self, frame):
        """Zeige Frame im GUI mit korrekter Bounding Box Transformation"""
        try:
            if frame is None or frame.size == 0:
                print("[!] _show_frame: Frame is None or empty")
                return

            # Use detection snapshot briefly so boxes match position/size exactly
            frame_for_display = frame
            if self.last_detections and self.last_detection_frame is not None:
                age = time.time() - self.last_detection_time
                if age <= self.detect_overlay_hold_sec:
                    frame_for_display = self.last_detection_frame

            h, w = frame_for_display.shape[:2]
            if h <= 0 or w <= 0:
                print(f"[!] _show_frame: Invalid frame dimensions {h}x{w}")
                return

            # Berechne Skalierung
            scale = min(640.0/w, 480.0/h)
            if scale <= 0:
                print(f"[!] _show_frame: Invalid scale {scale}")
                return

            new_w = int(w * scale)
            new_h = int(h * scale)

            if new_w <= 0 or new_h <= 0:
                print(f"[!] _show_frame: Invalid new dimensions {new_w}x{new_h}")
                return

            # Resize Frame
            frame_resized = cv2.resize(frame_for_display, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

            # Berechne Padding
            top = (480 - new_h) // 2
            bottom = 480 - new_h - top
            left = (640 - new_w) // 2
            right = 640 - new_w - left

            # Speichere Transformation für Bounding Boxes
            self.display_scale = scale
            self.display_pad_left = left
            self.display_pad_top = top

            # Zeichne Bounding Boxes auf resized Frame (BEVOR padding)
            draw_detections = False
            if self.last_detections and self.last_detection_time:
                age = time.time() - float(self.last_detection_time or 0.0)
                if age <= self.detect_overlay_hold_sec:
                    draw_detections = True

            if draw_detections:
                frame_resized = self._draw_boxes_on_display_frame(frame_resized, self.last_detections, scale)
            else:
                frame_resized = self._draw_preview_box_on_display_frame(frame_resized, scale)

            # Füge Padding hinzu
            frame_padded = cv2.copyMakeBorder(
                frame_resized, top, bottom, left, right,
                cv2.BORDER_CONSTANT, value=(0, 0, 0)
            )

            # Konvertierung
            frame_rgb = cv2.cvtColor(frame_padded, cv2.COLOR_BGR2RGB)
            if frame_rgb is None or frame_rgb.size == 0:
                print("[!] _show_frame: RGB conversion failed")
                return

            # PIL Image erstellen
            img = Image.fromarray(frame_rgb)
            if img is None:
                print("[!] _show_frame: PIL Image creation failed")
                return

            # PhotoImage erstellen
            photo = ImageTk.PhotoImage(img)
            if photo is None:
                print("[!] _show_frame: PhotoImage creation failed")
                return

            # Update Label
            self.camera_label.config(image=photo)
            self.camera_label.image = photo  # WICHTIG: Reference halten!

        except TypeError as e:
            print(f"[!] _show_frame TypeError: {e}")
        except ValueError as e:
            print(f"[!] _show_frame ValueError: {e}")
        except Exception as e:
            print(f"[!] _show_frame Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

    # ========================================================================
    # IMAGE CAPTURE & DETECTION
    # ========================================================================

    def _capture_and_detect(self):
        """Capture von Kamera und Analyse"""
        if self.current_frame is None:
            messagebox.showwarning("Kein Bild", "Bitte starte zuerst die Kamera!")
            return

        self._analyze(self.current_frame.copy())

    def _load_image(self):
        """Lade Bild von Festplatte"""
        try:
            path = filedialog.askopenfilename(
                title="Bild auswählen",
                filetypes=[
                    ("Images", "*.jpg *.jpeg *.png *.bmp"),
                    ("All", "*.*")
                ]
            )

            if not path:
                return

            # Versuche mit OpenCV zu laden
            frame = cv2.imread(path)

            if frame is None or frame.size == 0:
                try:
                    # Fallback: PIL to OpenCV
                    from PIL import Image as PILImage
                    pil_img = PILImage.open(path)
                    frame = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                except Exception as e:
                    messagebox.showerror("Fehler", f"Bild konnte nicht geladen werden: {e}")
                    return

            if frame is None or frame.size == 0:
                messagebox.showerror("Fehler", "Ungültige Image-Datei")
                return

            # Zeige Bild
            self._show_frame(frame)

            # Analysiere
            self._analyze(frame)
        except Exception as e:
            messagebox.showerror("Fehler", f"Image error: {str(e)[:100]}")
            print(f"Load image error: {e}")

    def _analyze(self, frame):
        """Analysiere Bild im separaten Thread"""
        if self.detect_running:
            self._set_status("[INFO] Analyse läuft bereits", "warning")
            return

        self.detect_running = True
        self.analysis_started_at = time.time()
        self._set_status("[LOADING] Analysiere...", "info")
        self.root.after(2500, self._maybe_warn_slow_analysis)

        thread = threading.Thread(
            target=self._detection_worker,
            args=(frame,),
            daemon=True
        )
        thread.start()

    def _maybe_warn_slow_analysis(self):
        """Meldung, wenn die Analyse länger als üblich läuft."""
        if not self.detect_running:
            return

        elapsed = time.time() - float(self.analysis_started_at or 0.0)
        if elapsed >= 2.5:
            self._set_status(
                "[INFO] Analyse dauert noch. Objekt ruhig halten und ggf. näher/weiter weg bewegen.",
                "warning"
            )

    def _detection_worker(self, frame):
        """Detection im Background-Thread mit sauberem State-Management"""
        start_time = time.time()
        try:
            print("[DEBUG] Detection worker started")

            # === FRAME CONVERSION ===
            # CRITICAL FIX: Convert numpy array to JPEG bytes
            try:
                _, img_bytes = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                image_bytes = img_bytes.tobytes()
            except Exception as e:
                self.root.after(0, lambda: self._print_result(f"[-] Frame encoding error: {e}"))
                self.root.after(0, lambda: self._set_status("[-] Image error", "error"))
                return

            # === DETECTION ===
            if detect_image is None:
                self.root.after(0, lambda: self._print_result("[-] Detection not initialized"))
                self.root.after(0, lambda: self._set_status("[-] Module error", "error"))
                return

            print("[DEBUG] Calling detect_image...")
            detections = detect_image(image_bytes)

            if not detections:
                self.last_detections = []
                self.last_detection_frame = None
                self.root.after(0, lambda: self._print_result("[INFO] Keine Objekte erkannt"))
                self.root.after(0, lambda: self._set_status("[IDLE] Keine Objekte", "info"))
                return

            # === PROCESS DETECTIONS ===
            # NOTE: detect_image() already does classification via waste_classifier!
            # We just need to normalize the field names for the UI

            classified = []
            for det in detections:
                try:
                    # Map inference.py field names to app.py expected names
                    waste_info = det.get('waste_sorting', {})

                    # CRITICAL FIX: Handle None waste_sorting
                    if waste_info is None or waste_info == {}:
                        waste_info = {
                            'bin': 'RESTMÜLL',
                            'reasoning': 'Keine klare Zuordnung möglich - bitte manuell prüfen',
                            'confidence': 0.3,
                            'action': 'MANUAL_CHECK_REQUIRED'
                        }

                    # Map waste bin names to standard format
                    bin_key = waste_info.get('bin', 'RESTMÜLL').upper()

                    # Map formal names to display names
                    bin_display_names = {
                        'RESTMÜLL': 'Restmüll',
                        'BIOMÜLL': 'Biomüll',
                        'PAPIERMÜLL': 'Papiermüll',
                        'GELBE TONNE': 'Gelbe Tonne',
                        'GLASCONTAINER': 'Glascontainer',
                    }
                    bin_name = bin_display_names.get(bin_key, 'Restmüll')

                    normalized = {
                        'class_name': det.get('class', 'unknown'),  # 'class' -> 'class_name'
                        'confidence': det.get('calibrated_confidence', det.get('score', 0.0)),  # Use calibrated
                        'bbox': det.get('bbox', []),
                        'bbox_model': det.get('bbox_model', []),
                        'bbox_area_ratio': det.get('bbox_area_ratio', 0.0),
                        'framing_needs_improvement': bool(det.get('framing_needs_improvement', False)),
                        'framing_focus': det.get('framing_focus', {}) or {},
                        'recommended_bin': bin_name,
                        'reasoning': waste_info.get('reasoning', 'Automatische Klassifizierung'),
                        'warnings': waste_info.get('warnings', []) or [],
                        'review_reasons': waste_info.get('review_reasons', []) or [],
                        'data_provenance': det.get('data_provenance', {}) or {},
                        'explainability': waste_info.get('explainability', {}) or {},
                        'learning_target': det.get('learning_target', {}) or {},
                        'action': det.get('user_action', 'MANUAL_CHECK_REQUIRED'),
                        'user_action': det.get('user_action', 'MANUAL_CHECK_REQUIRED'),
                        'detection_id': det.get('detection_id'),
                        'object_condition': det.get('object_condition', 'normal'),
                        'battery_risk': any(
                            ('BATTERIE' in str(w)) or ('Akku' in str(w)) or ('akku' in str(w))
                            or ('könnte Akku/Batterien enthalten' in str(w))
                            for w in (waste_info.get('warnings', []) or [])
                        ),
                        'bin_color': self._get_bin_color(bin_name)
                    }

                    classified.append(normalized)
                except Exception as e:
                    print(f"[ERROR] Processing detection: {e}")
                    import traceback
                    traceback.print_exc()
                    continue

            self.last_detections = classified
            self.detection_counter += 1

            # === INTELLIGENT FILTERING ===
            # Keep only the most important/prominent objects
            filtered_detections = self._filter_and_prioritize_detections(classified)
            filtered_detections = self._assign_track_ids(filtered_detections)
            self.last_detections = filtered_detections  # Update with filtered results
            self.track_memory = [dict(det) for det in filtered_detections]
            if filtered_detections:
                self.last_detection_frame = frame.copy()
                self.last_detection_time = time.time()
            else:
                self.last_detection_frame = None

            # === DISPLAY RESULTS ===
            elapsed_sec = time.time() - start_time
            for det in filtered_detections:
                det['analysis_duration_sec'] = elapsed_sec
                det['distance_hint'] = self._estimate_distance_hint(det)
            self.root.after(0, lambda c=filtered_detections: self._display_results(c))
            if elapsed_sec >= 2.5:
                self.root.after(0, lambda e=elapsed_sec: self._set_status(f"[OK] Analyse fertig in {e:.1f}s", "success"))
            else:
                self.root.after(0, lambda n=len(filtered_detections): self._set_status(f"[OK] {n} Objekt erkannt", "success"))

        except Exception as e:
            error_msg = f"[-] Fehler: {str(e)[:150]}"
            self.root.after(0, lambda: self._print_result(error_msg))
            self.root.after(0, lambda: self._set_status("[-] Fehler bei Analyse", "error"))
            print(f"[ERROR] Detection Error: {e}")
            import traceback
            traceback.print_exc()
            print("[!] Recovery: Detection failed, app remains stable")
        finally:
            # CRITICAL: Always reset detect_running flag
            self.detect_running = False
            print("[DEBUG] Detection worker finished")

    def _display_results(self, detections):
        """Zeige Detektions-Ergebnisse"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        text = f"\n{'='*50}\n"
        text += f"[TIME] {timestamp} | Detection #{self.detection_counter}\n"
        text += f"{'='*50}\n\n"

        # Store for feedback system
        self.last_detections = detections

        if not detections:
            text += "❌ Kein passendes Objekt erkannt (Personen werden ignoriert)\n"
        else:
            det = detections[0]
            conf = det.get('confidence', 0.0) * 100
            class_name = str(det.get('class_name', 'Unbekannt')).replace('_', ' ')
            bin_name = det.get('recommended_bin', 'Unbekannt')
            action = "AUTO" if det.get('user_action') != 'MANUAL_CHECK_REQUIRED' else "PRÜFEN"
            distance_hint = det.get('distance_hint')
            analysis_duration = float(det.get('analysis_duration_sec', 0.0) or 0.0)
            uncertainty = float(det.get('uncertainty_score', 0.0) or 0.0)
            track_id = det.get('track_id')

            text += "🎯 Vorderstes Objekt:\n\n"
            text += f"Objekt: {class_name}\n"
            text += f"Sicherheit: {conf:.0f}%\n"
            text += f"Unsicherheit: {uncertainty * 100:.0f}%\n"
            if track_id is not None:
                text += f"Track-ID: {track_id}\n"
            text += f"Behälter: {bin_name}\n"
            text += f"Modus: {action}\n\n"

            if analysis_duration >= 2.5:
                text += f"Analysezeit: {analysis_duration:.1f}s\n\n"

            if distance_hint:
                text += f"Bildhinweis: {distance_hint}\n\n"

            warnings = det.get('warnings', []) or []
            if warnings:
                text += "Warnungen:\n"
                for warning in warnings[:3]:
                    text += f"- {warning}\n"
                text += "\n"

            if det.get('battery_risk'):
                text += "Sicherheitshinweis: Elektronisches Gerät könnte Akku/Batterien enthalten.\n"
                text += "Bitte vor Entsorgung auf Batterien/Akkus prüfen.\n\n"

            provenance = det.get('data_provenance', {}) or {}
            explainability = det.get('explainability', {}) or {}
            source_parts = []
            source_parts.append("Modell:YOLOX")
            if provenance.get('local_learning', {}).get('used'):
                source_parts.append("Lernen:DB")
            if provenance.get('web_knowledge', {}).get('used'):
                source_parts.append(f"Web:{provenance.get('web_knowledge', {}).get('source', 'unknown')}")

            if source_parts:
                text += f"Datenquellen: {', '.join(source_parts)}\n"

            mapping_source = explainability.get('mapping_source')
            if mapping_source:
                text += f"Entscheidungsweg: {mapping_source}\n\n"

            learning_target = det.get('learning_target', {}) or {}
            if learning_target.get('is_focus_class'):
                rank = learning_target.get('rank', '?')
                acc = float(learning_target.get('accuracy_rate', 0.0)) * 100.0
                urg = float(learning_target.get('urgency', 0.0))
                text += "Lernziel-Priorität aktiv:\n"
                text += f"- Klasse Rang #{rank} für Nachlernen\n"
                text += f"- Aktuelle Genauigkeit: {acc:.1f}%\n"
                text += f"- Dringlichkeit: {urg:.2f}\n\n"

        focus_snapshot = self._get_learning_focus_snapshot()
        self.learning_focus_snapshot = focus_snapshot
        top_priority = focus_snapshot.get('top_priority')
        if top_priority:
            text += "Aktuelles KI-Lernziel:\n"
            text += f"- Klasse: {top_priority.get('class_name')}\n"
            text += f"- Genauigkeit: {float(top_priority.get('accuracy_rate', 0.0))*100.0:.1f}%\n"
            text += f"- Offene Prüf-Fälle: {focus_snapshot.get('review_queue_count', 0)}\n"
            text += f"- Fehlertrend: {focus_snapshot.get('error_trend', 'unknown')}\n\n"

        self._print_result(text)

        # Update bin visualization with first detection's recommendation
        if detections:
            first_bin = detections[0].get('recommended_bin', 'Restmüll')
            self._update_bin_visualization(first_bin)

            # Update statistics (only shown foreground object)
            for det in detections[:1]:
                bin_name = det.get('recommended_bin', 'Restmüll')
                if bin_name in self.stats_today:
                    self.stats_today[bin_name] += 1
            self._update_stats_display()

            # Enable feedback buttons
            self.feedback_correct_btn.config(state=tk.NORMAL)
            self.feedback_wrong_btn.config(state=tk.NORMAL)
            self.manual_draw_btn.config(state=tk.NORMAL)
        else:
            # Disable buttons if nothing detected
            self.feedback_correct_btn.config(state=tk.DISABLED)
            self.feedback_wrong_btn.config(state=tk.DISABLED)
            self.manual_draw_btn.config(state=tk.DISABLED)

    # ========================================================================
    # DRAWING
    # ========================================================================

    def _refine_bbox_on_frame(self, frame, x1, y1, x2, y2):
        """Verfeinere Box robust und konservativ: lieber etwas zu groß als abgeschnitten."""
        try:
            h, w = frame.shape[:2]
            x1 = max(0, min(int(x1), w - 1))
            y1 = max(0, min(int(y1), h - 1))
            x2 = max(1, min(int(x2), w))
            y2 = max(1, min(int(y2), h))

            if x2 - x1 < 8 or y2 - y1 < 8:
                return x1, y1, x2, y2

            orig_w = max(1, x2 - x1)
            orig_h = max(1, y2 - y1)
            orig_area = float(orig_w * orig_h)
            orig_cx = (x1 + x2) / 2.0
            orig_cy = (y1 + y2) / 2.0

            roi = frame[y1:y2, x1:x2]
            if roi.size == 0:
                return x1, y1, x2, y2

            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (5, 5), 0)

            median = float(np.median(gray))
            low = int(max(10, 0.66 * median))
            high = int(min(255, 1.33 * median))
            edges = cv2.Canny(gray, low, high)

            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=1)

            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                # Kein Kontur-Signal: leicht erweitern statt riskant verschieben
                pad_x = max(4, int(round(orig_w * 0.08)))
                pad_y = max(4, int(round(orig_h * 0.08)))
                bx1 = max(0, x1 - pad_x)
                by1 = max(0, y1 - pad_y)
                bx2 = min(w, x2 + pad_x)
                by2 = min(h, y2 + pad_y)
                return bx1, by1, bx2, by2

            roi_area = float((x2 - x1) * (y2 - y1))
            min_area = max(40.0, roi_area * 0.04)
            valid_contours = [c for c in contours if cv2.contourArea(c) >= min_area]
            if not valid_contours:
                return x1, y1, x2, y2

            # Nutze die größten Konturen gemeinsam, damit die Box das ganze Objekt umfasst.
            valid_contours = sorted(valid_contours, key=cv2.contourArea, reverse=True)[:3]
            merged = np.vstack(valid_contours)
            rx, ry, rw, rh = cv2.boundingRect(merged)

            refined_x1 = x1 + int(rx)
            refined_y1 = y1 + int(ry)
            refined_x2 = refined_x1 + int(rw)
            refined_y2 = refined_y1 + int(rh)

            # Schutz gegen falschen Sprung: Kandidat muss nahe beim Originalzentrum liegen.
            cand_cx = (refined_x1 + refined_x2) / 2.0
            cand_cy = (refined_y1 + refined_y2) / 2.0
            center_shift = np.hypot(cand_cx - orig_cx, cand_cy - orig_cy)
            max_shift = max(18.0, 0.32 * np.hypot(orig_w, orig_h))
            cand_area = float(max(1, (refined_x2 - refined_x1) * (refined_y2 - refined_y1)))

            if center_shift > max_shift or cand_area < (orig_area * 0.35):
                refined_x1, refined_y1, refined_x2, refined_y2 = x1, y1, x2, y2

            # Niemals kleiner als Original: union, dann Sicherheits-Padding
            bx1 = min(x1, refined_x1)
            by1 = min(y1, refined_y1)
            bx2 = max(x2, refined_x2)
            by2 = max(y2, refined_y2)

            # Kleine Sicherheitserweiterung, damit Objekt nicht abgeschnitten wirkt
            bw = max(1, bx2 - bx1)
            bh = max(1, by2 - by1)
            pad_x = max(4, int(round(0.08 * bw)))
            pad_y = max(4, int(round(0.08 * bh)))

            bx1 -= pad_x
            by1 -= pad_y
            bx2 += pad_x
            by2 += pad_y

            bx1 = max(0, min(bx1, w - 1))
            by1 = max(0, min(by1, h - 1))
            bx2 = max(1, min(bx2, w))
            by2 = max(1, min(by2, h))

            if bx2 - bx1 < 6 or by2 - by1 < 6:
                return x1, y1, x2, y2

            return bx1, by1, bx2, by2
        except Exception:
            return x1, y1, x2, y2

    def _draw_boxes_on_display_frame(self, frame, detections, scale):
        """Zeichne Bounding Boxes mit großen, lesbaren Labels"""
        try:
            if frame is None or frame.size == 0:
                return frame

            h, w = frame.shape[:2]
            if h <= 0 or w <= 0:
                return frame

            if not detections:
                return frame

            for idx, det in enumerate(detections, 1):
                try:
                    bbox = det.get('bbox', [])
                    if len(bbox) != 4:
                        continue

                    # Transform coordinates from original to display frame
                    x1, y1, x2, y2 = bbox
                    x1_scaled = int(round(x1 * scale))
                    y1_scaled = int(round(y1 * scale))
                    x2_scaled = int(round(x2 * scale))
                    y2_scaled = int(round(y2 * scale))

                    # Clip to frame bounds
                    x1_scaled = max(0, min(x1_scaled, w))
                    y1_scaled = max(0, min(y1_scaled, h))
                    x2_scaled = max(0, min(x2_scaled, w))
                    y2_scaled = max(0, min(y2_scaled, h))

                    if x2_scaled - x1_scaled < 2 or y2_scaled - y1_scaled < 2:
                        continue

                    # Keep UI overlay aligned with model output; no extra contour-based shifts here.
                    if det.get("framing_needs_improvement"):
                        pad_x = max(2, int(round((x2_scaled - x1_scaled) * 0.04)))
                        pad_y = max(2, int(round((y2_scaled - y1_scaled) * 0.04)))
                        x1_scaled = max(0, x1_scaled - pad_x)
                        y1_scaled = max(0, y1_scaled - pad_y)
                        x2_scaled = min(w, x2_scaled + pad_x)
                        y2_scaled = min(h, y2_scaled + pad_y)

                    # Farbe basierend auf empfohlenem Behälter
                    bin_name = det.get('recommended_bin', 'Restmüll')

                    bin_colors = {
                        'Restmüll': (100, 100, 100),      # Grau
                        'Biomüll': (0, 255, 0),           # Grün
                        'Papiermüll': (255, 0, 0),        # Blau (BGR)
                        'Gelbe Tonne': (0, 255, 255),     # Gelb (BGR)
                        'Glascontainer': (200, 50, 200),  # Magenta
                    }
                    if det.get("manual_focus_selected"):
                        color = (0, 200, 255)
                    else:
                        color = bin_colors.get(bin_name, (100, 100, 100))

                    # Zeichne dickere Box (besser sichtbar)
                    cv2.rectangle(frame, (x1_scaled, y1_scaled), (x2_scaled, y2_scaled), color, 3)

                    # GROSSES, LESBARES LABEL
                    class_name = det.get('class_name', 'Unbekannt')
                    confidence = det.get('confidence', 0.0) * 100

                    # Build label text (short + readable)
                    class_display = str(class_name).replace('_', ' ')
                    label_prefix = "AUSWAHL: " if det.get("manual_focus_selected") else ""
                    if det.get("track_id") is not None:
                        label_prefix = f"{label_prefix}#{det.get('track_id')} "
                    label_line1 = f"{label_prefix}{class_display}"
                    short_hint = self._short_distance_hint(det.get('distance_hint'))
                    label_line2 = f"{confidence:.0f}% • {bin_name}"
                    if short_hint:
                        label_line2 = f"{label_line2} • {short_hint}"
                    uncertainty = float(det.get('uncertainty_score', 0.0) or 0.0)
                    label_line2 = f"{label_line2} • u:{uncertainty * 100:.0f}%"

                    font = cv2.FONT_HERSHEY_DUPLEX
                    font_scale = 0.85
                    thickness = 2

                    # Get text size for both lines
                    (text_w1, text_h1), _ = cv2.getTextSize(label_line1, font, font_scale, thickness)
                    (text_w2, text_h2), _ = cv2.getTextSize(label_line2, font, font_scale, thickness)
                    text_w = max(text_w1, text_w2)
                    text_h_total = text_h1 + text_h2 + 10

                    # Label position (above box, clipped in frame)
                    label_x = x1_scaled
                    label_y = max(text_h_total + 8, y1_scaled)
                    if label_x + text_w + 12 > w:
                        label_x = max(0, w - text_w - 12)

                    # Draw label background (solid, opaque)
                    cv2.rectangle(frame,
                                (label_x, label_y - text_h_total - 5),
                                (label_x + text_w + 10, label_y),
                                color, -1)

                    # Add black outline to label background (better contrast)
                    cv2.rectangle(frame,
                                (label_x, label_y - text_h_total - 5),
                                (label_x + text_w + 10, label_y),
                                (0, 0, 0), 2)

                    # Draw text lines
                    cv2.putText(frame, label_line1,
                              (label_x + 5, label_y - text_h2 - 5),
                              font, font_scale, (255, 255, 255), thickness)
                    cv2.putText(frame, label_line2,
                              (label_x + 5, label_y - 2),
                              font, font_scale, (255, 255, 255), thickness)

                except Exception as e:
                    print(f"[!] Draw detection error: {e}")
                    continue
            return frame
        except Exception as e:
            print(f"[!] _draw_boxes error: {e}")
            return frame

    def _draw_boxes(self, frame, detections):
        """Legacy method - zeichne Boxen auf Original-Frame (for export/save)"""
        try:
            if frame is None or frame.size == 0:
                print("[!] _draw_boxes: Frame is None")
                return frame

            h, w = frame.shape[:2]
            if h <= 0 or w <= 0:
                return frame

            if not detections:
                return frame

            for idx, det in enumerate(detections, 1):
                try:
                    bbox = det.get('bbox', [])
                    if len(bbox) != 4:
                        continue

                    x1, y1, x2, y2 = [int(v) for v in bbox]
                    x1, y1 = max(0, min(x1, w)), max(0, min(y1, h))
                    x2, y2 = max(0, min(x2, w)), max(0, min(y2, h))

                    if x2 - x1 < 2 or y2 - y1 < 2:
                        continue

                    color = (0, 165, 255) if det.get('user_action') == 'MANUAL_CHECK_REQUIRED' else (0, 255, 0)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

                    # Safe field access with defaults
                    class_name = det.get('class_name', 'unknown')
                    confidence = det.get('confidence', 0.0)
                    label = f"#{idx} {class_name} {confidence*100:.0f}%"
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    (text_w, text_h), _ = cv2.getTextSize(label, font, 0.5, 1)
                    label_y = max(text_h + 5, y1)
                    cv2.rectangle(frame, (x1, label_y - text_h - 5), (x1 + text_w + 5, label_y), color, -1)
                    cv2.putText(frame, label, (x1 + 2, label_y - 2), font, 0.5, (255, 255, 255), 1)
                except Exception as e:
                    print(f"[!] Draw detection error: {e}")
                    continue
            return frame
        except Exception as e:
            print(f"[!] _draw_boxes error: {e}")
            return frame

    # ========================================================================
    # UI UPDATES
    # ========================================================================

    def _print_result(self, text):
        """Schreibe Text zu Results"""
        try:
            self.results_text.config(state=tk.NORMAL)
            self.results_text.insert(tk.END, str(text))
            self.results_text.see(tk.END)
            self.results_text.update_idletasks()
        except Exception as e:
            print(f"[!] _print_result error: {e}")

    def _set_status(self, message, status_type="info"):
        """Update Status Bar"""
        colors = {
            "success": "#27ae60",
            "error": "#e74c3c",
            "warning": "#f39c12",
            "info": "#3498db"
        }

        self.status_label.config(text=message, fg=colors.get(status_type, "white"))
        self.root.update_idletasks()

    # ========================================================================
    # BIN VISUALIZATION & STATISTICS
    # ========================================================================

    def _get_bin_color(self, bin_name):
        """Get color for bin name"""
        colors = {
            'Restmüll': '#555555',
            'Biomüll': '#27ae60',
            'Papiermüll': '#3498db',
            'Gelbe Tonne': '#f39c12',
            'Glascontainer': '#9b59b6'
        }
        return colors.get(bin_name, '#555555')

    def _filter_and_prioritize_detections(self, detections):
        """
        ULTRA-SMART FOREGROUND-ONLY FILTERING

        Core Logic:
        - Show ONLY main foreground object(s)
        - Completely IGNORE background/far away objects
        - If user shows phone, show ONLY the phone
        - If user shows 2 similar-sized items, show BOTH

        This is trash sorting - we care ONLY about what's being thrown!
        """
        if not detections:
            return []

        if self._manual_focus_active():
            focused = self._apply_manual_focus_filter(detections)
            if focused:
                return focused

        def is_human_detection(det):
            name = str(det.get('class_name', '')).strip().lower()
            if not name:
                return False
            human_tokens = {'person', 'human', 'people', 'man', 'woman', 'boy', 'girl'}
            return name in human_tokens

        def calc_object_size(det):
            bbox = det.get('bbox', [])
            if len(bbox) != 4:
                return 0
            return abs(bbox[2] - bbox[0]) * abs(bbox[3] - bbox[1])

        def calc_iou(box1, box2):
            x1_1, y1_1, x2_1, y2_1 = box1
            x1_2, y1_2, x2_2, y2_2 = box2

            x1_i = max(x1_1, x1_2)
            y1_i = max(y1_1, y1_2)
            x2_i = min(x2_1, x2_2)
            y2_i = min(y2_1, y2_2)

            if x2_i < x1_i or y2_i < y1_i:
                return 0.0

            intersection = (x2_i - x1_i) * (y2_i - y1_i)
            area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
            area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
            union = area1 + area2 - intersection

            return intersection / union if union > 0 else 0.0

        # Step 0: Prefer objects over humans (people should almost never be shown)
        object_only = [d for d in detections if not is_human_detection(d)]
        if not object_only:
            return []

        # Step 1: Filter tiny/low-confidence objects
        min_size = 500
        min_conf = 0.40
        valid = [
            d for d in object_only
            if calc_object_size(d) >= min_size and float(d.get('confidence', 0.0)) >= min_conf
        ]

        if not valid:
            return []

        # Step 2: Sort by weighted foreground score
        # Large + confident objects are preferred.
        def foreground_score(det):
            size = calc_object_size(det)
            conf = float(det.get('confidence', 0.0))
            return size * (0.5 + conf)

        valid.sort(key=foreground_score, reverse=True)

        # Step 3: AGGRESSIVE NMS - merge overlapping boxes
        nms_threshold = 0.35  # Even stricter overlap detection
        filtered = []
        skip = set()

        for i, det1 in enumerate(valid):
            if i in skip:
                continue
            filtered.append(det1)
            bbox1 = det1.get('bbox', [])

            for j in range(i + 1, len(valid)):
                if j in skip:
                    continue
                det2 = valid[j]
                bbox2 = det2.get('bbox', [])

                if len(bbox1) == 4 and len(bbox2) == 4:
                    if calc_iou(bbox1, bbox2) > nms_threshold:
                        skip.add(j)

        if not filtered:
            return []

        # Step 4: CRITICAL - Foreground Only!
        # Get the largest object (main foreground)
        largest = filtered[0]
        largest_size = calc_object_size(largest)

        # ONLY show objects that are AT LEAST 60% of the largest
        # This filters out background completely!
        # Examples:
        #   - Phone (92500) + Person (15000) → 15000/92500 = 16% → ONLY show phone
        #   - Bottle (90000) + Bottle (85000) → 85000/90000 = 94% → show BOTH
        foreground_threshold = 0.60

        result = [largest]  # Always include the largest

        for det in filtered[1:]:
            size = calc_object_size(det)
            ratio = size / largest_size if largest_size > 0 else 0

            # Only add if it's reasonably sized (not background)
            if ratio >= foreground_threshold:
                result.append(det)

        return result[:1]  # Nur vorderstes Objekt für klare UX

    def _apply_manual_focus_filter(self, detections):
        """Bevorzugt das Objekt, das am besten zur manuell gewählten Box passt."""
        if not self.manual_focus_box:
            return []

        best_det = None
        best_iou = 0.0
        focus_box = self.manual_focus_box

        for det in detections:
            bbox = det.get("bbox", [])
            if len(bbox) != 4:
                continue
            iou = self._iou_boxes(focus_box, bbox)
            if iou > best_iou:
                best_iou = iou
                best_det = det

        if best_det and best_iou >= 0.08:
            best_det["manual_focus_selected"] = True
            return [best_det]

        return []

    def _iou_boxes(self, box1, box2):
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = max(0, box1[2] - box1[0]) * max(0, box1[3] - box1[1])
        area2 = max(0, box2[2] - box2[0]) * max(0, box2[3] - box2[1])
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0.0

    def _assign_track_ids(self, detections):
        """Ordnet stabile Track-IDs anhand der vorherigen Boxen zu."""
        if not detections:
            return []

        previous = list(getattr(self, "track_memory", []) or [])
        used_previous = set()
        result = []

        for det in detections:
            bbox = det.get("bbox", [])
            best_prev = None
            best_iou = 0.0

            for idx, prev in enumerate(previous):
                if idx in used_previous:
                    continue
                prev_bbox = prev.get("bbox", [])
                if len(bbox) != 4 or len(prev_bbox) != 4:
                    continue
                iou = self._iou_boxes(bbox, prev_bbox)
                if iou > best_iou:
                    best_iou = iou
                    best_prev = (idx, prev)

            assigned = dict(det)
            if best_prev and best_iou >= 0.18 and best_prev[1].get("track_id") is not None:
                assigned["track_id"] = best_prev[1].get("track_id")
                assigned["track_iou"] = best_iou
                used_previous.add(best_prev[0])
            else:
                assigned["track_id"] = self.next_track_id
                assigned["track_iou"] = best_iou
                self.next_track_id += 1

            result.append(assigned)

        return result

    def _estimate_distance_hint(self, det):
        """Leitet aus Boxgröße ab, ob das Objekt näher oder weiter weg sein sollte."""
        area_ratio = float(det.get('bbox_area_ratio', 0.0) or 0.0)
        conf = float(det.get('confidence', 0.0) or 0.0)
        class_name = str(det.get('class_name', '')).strip().lower()

        if area_ratio <= 0:
            return None

        if area_ratio < 0.004 or (area_ratio < 0.008 and conf < 0.70):
            return "Objekt wirkt klein im Bild. Bitte etwas näher an die Kamera halten."

        if area_ratio > 0.22:
            return "Objekt wirkt sehr groß im Bild. Bitte etwas weiter weg halten."

        if area_ratio > 0.14 and class_name in {'cell phone', 'laptop', 'book', 'bottle', 'cup', 'remote'}:
            return "Objekt füllt das Bild stark. Falls etwas abgeschnitten ist, bitte leicht weiter weg halten."

        if area_ratio < 0.012 and class_name in {'cell phone', 'remote', 'clock', 'watch', 'smartwatch'}:
            return "Kleines Objekt erkannt. Bitte näher heranhalten, damit Details sicherer erkannt werden."

        return None

    def _estimate_distance_hint_for_box(self, area_ratio: float) -> str | None:
        """Leitet Hinweis nur aus Boxfläche ab (vor Analyse)."""
        area_ratio = float(area_ratio or 0.0)
        if area_ratio <= 0:
            return None
        if area_ratio < 0.006:
            return "Bitte näher an die Kamera halten."
        if area_ratio > 0.24:
            return "Bitte etwas weiter weg halten."
        if area_ratio > 0.16:
            return "Objekt füllt das Bild stark. Evtl. etwas weiter weg."
        return None

    def _short_distance_hint(self, hint: str | None) -> str | None:
        """Kurzer Hinweistext für Box-Label."""
        if not hint:
            return None
        hint_lc = str(hint).lower()
        if "näher" in hint_lc or "nahe" in hint_lc:
            return "naeher"
        if "weiter" in hint_lc:
            return "weiter"
        if "abgeschnitten" in hint_lc:
            return "leicht weiter"
        return None

    def _manual_focus_active(self) -> bool:
        return bool(self.manual_focus_box) and time.time() < float(self.manual_focus_expires_at or 0.0)

    def _map_display_to_image(self, x: int, y: int, frame_shape) -> tuple[int, int] | None:
        """Mappt Klick-Koordinaten aus dem Display in das Originalbild."""
        try:
            h, w = frame_shape[:2]
            scale = float(self.display_scale or 1.0)
            x_adj = float(x - self.display_pad_left)
            y_adj = float(y - self.display_pad_top)
            if x_adj < 0 or y_adj < 0:
                return None
            img_x = int(round(x_adj / scale))
            img_y = int(round(y_adj / scale))
            if img_x < 0 or img_y < 0 or img_x > w or img_y > h:
                return None
            return img_x, img_y
        except Exception:
            return None

    def _point_in_box(self, x: int, y: int, bbox) -> bool:
        if not bbox or len(bbox) != 4:
            return False
        x1, y1, x2, y2 = bbox
        return x1 <= x <= x2 and y1 <= y <= y2

    def _select_box_from_click(self, img_x: int, img_y: int):
        """Wählt Box basierend auf Klick: Detection-Box bevorzugt, sonst Preview-Box."""
        if self.last_detections and self.last_detection_time:
            age = time.time() - float(self.last_detection_time or 0.0)
            if age <= self.detect_overlay_hold_sec:
                candidates = []
                for det in self.last_detections:
                    bbox = det.get("bbox", [])
                    if self._point_in_box(img_x, img_y, bbox):
                        candidates.append(det)
                if candidates:
                    candidates.sort(key=lambda d: float(d.get("confidence", 0.0)), reverse=True)
                    return "detection", candidates[0]

        return None, None

    def _on_camera_click(self, event):
        """Klick auf die Kamera: Box fokussieren, damit Analyse auf Objekt zielt."""
        try:
            if self.current_frame is None or self.current_frame.size == 0:
                return

            mapped = self._map_display_to_image(int(event.x), int(event.y), self.current_frame.shape)
            if not mapped:
                return

            img_x, img_y = mapped
            source, det = self._select_box_from_click(img_x, img_y)
            if not det:
                return

            bbox = det.get("bbox", [])
            if len(bbox) != 4:
                return

            self.manual_focus_box = [int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])]
            self.manual_focus_expires_at = time.time() + float(self.manual_focus_hold_sec)
            area_ratio = ((bbox[2] - bbox[0]) * (bbox[3] - bbox[1])) / max(float(self.current_frame.shape[0] * self.current_frame.shape[1]), 1.0)
            self.manual_focus_hint = self._estimate_distance_hint_for_box(area_ratio)

            if source == "detection":
                class_name = str(det.get("class_name", "Objekt")).replace("_", " ")
                conf = float(det.get("confidence", 0.0)) * 100.0
                self.manual_focus_label = f"AUSWAHL: {class_name} ({conf:.0f}%)"
            else:
                self.manual_focus_label = "AUSWAHL"

            self._set_status("[SELECT] Objekt fokussiert. Jetzt analysieren.", "info")
        except Exception:
            return

    def _draw_preview_box_on_display_frame(self, frame, scale):
        """Zeichnet eine Vorschau-Box mit Hinweis vor der Analyse."""
        try:
            if frame is None or frame.size == 0:
                return frame

            if not self._manual_focus_active():
                return frame

            box = self.manual_focus_box
            hint = self.manual_focus_hint
            label_override = self.manual_focus_label or "AUSWAHL"

            h, w = frame.shape[:2]
            x1, y1, x2, y2 = box
            x1_scaled = int(round(x1 * scale))
            y1_scaled = int(round(y1 * scale))
            x2_scaled = int(round(x2 * scale))
            y2_scaled = int(round(y2 * scale))

            x1_scaled = max(0, min(x1_scaled, w))
            y1_scaled = max(0, min(y1_scaled, h))
            x2_scaled = max(0, min(x2_scaled, w))
            y2_scaled = max(0, min(y2_scaled, h))

            if x2_scaled - x1_scaled < 2 or y2_scaled - y1_scaled < 2:
                return frame

            color = (255, 200, 0)
            cv2.rectangle(frame, (x1_scaled, y1_scaled), (x2_scaled, y2_scaled), color, 2)

            label_line1 = label_override
            label_line2 = hint or "Objekt zentrieren und ruhig halten"

            font = cv2.FONT_HERSHEY_DUPLEX
            font_scale = 0.7
            thickness = 2

            (text_w1, text_h1), _ = cv2.getTextSize(label_line1, font, font_scale, thickness)
            (text_w2, text_h2), _ = cv2.getTextSize(label_line2, font, font_scale, thickness)
            text_w = max(text_w1, text_w2)
            text_h_total = text_h1 + text_h2 + 10

            label_x = x1_scaled
            label_y = max(text_h_total + 8, y1_scaled)
            if label_x + text_w + 12 > w:
                label_x = max(0, w - text_w - 12)

            cv2.rectangle(frame,
                          (label_x, label_y - text_h_total - 5),
                          (label_x + text_w + 10, label_y),
                          color, -1)
            cv2.rectangle(frame,
                          (label_x, label_y - text_h_total - 5),
                          (label_x + text_w + 10, label_y),
                          (0, 0, 0), 1)

            cv2.putText(frame, label_line1,
                        (label_x + 5, label_y - text_h2 - 5),
                        font, font_scale, (0, 0, 0), thickness)
            cv2.putText(frame, label_line2,
                        (label_x + 5, label_y - 2),
                        font, font_scale, (0, 0, 0), thickness)

            return frame
        except Exception:
            return frame

    def _update_bin_visualization(self, recommended_bin):
        """Highlight the recommended bin"""
        try:
            # Reset all bins to default
            for name, info in self.bin_buttons.items():
                info['button'].config(
                    bg=info['default_bg'],
                    bd=2,
                    highlightthickness=0
                )

            # Highlight recommended bin
            if recommended_bin in self.bin_buttons:
                self.bin_buttons[recommended_bin]['button'].config(
                    bg=self.bin_buttons[recommended_bin]['color'],
                    bd=4,
                    highlightthickness=2,
                    highlightbackground="white"
                )
        except Exception as e:
            print(f"[!] Bin visualization error: {e}")

    def _update_stats_display(self):
        """Update statistics display"""
        try:
            total = sum(self.stats_today.values())
            stats_text = f"📊 Heute: {total} Objekte | "
            stats_text += f"Restmüll: {self.stats_today['Restmüll']} | "
            stats_text += f"Bio: {self.stats_today['Biomüll']} | "
            stats_text += f"Papier: {self.stats_today['Papiermüll']} | "
            stats_text += f"Gelb: {self.stats_today['Gelbe Tonne']}"

            self.stats_label.config(text=stats_text)
        except Exception as e:
            print(f"[!] Stats update error: {e}")

    # ========================================================================
    # FEEDBACK SYSTEM
    # ========================================================================

    def _feedback_correct(self):
        """User confirms detection was correct"""
        try:
            if not hasattr(self, 'last_detections') or not self.last_detections:
                return

            self._print_result("\n✅ Feedback: Erkennung bestätigt!\n")
            self._set_status("[OK] Danke für dein Feedback!", "success")

            # Store positive feedback in database
            for det in self.last_detections:
                detection_id = det.get('detection_id')
                if detection_id:
                    # Here you could call learning_db to store positive feedback
                    print(f"[FEEDBACK] ✅ Correct: {detection_id}")

            # Disable feedback buttons after use
            self.feedback_correct_btn.config(state=tk.DISABLED)
            self.feedback_wrong_btn.config(state=tk.DISABLED)

        except Exception as e:
            print(f"[!] Feedback correct error: {e}")

    def _feedback_wrong(self):
        """User reports incorrect detection - enter correct object name"""
        try:
            if not hasattr(self, 'last_detections') or not self.last_detections:
                messagebox.showwarning("Fehler", "Keine Erkennung vorhanden für Korrektur")
                return

            original_det = self.last_detections[0]
            original_class = original_det.get('class', '?')
            
            # Dialog for user to enter correct object name
            correction_window = tk.Toplevel(self.root)
            correction_window.title("Korrektur - Was ist es wirklich?")
            correction_window.geometry("500x400")
            correction_window.config(bg=self.bg_secondary)
            
            tk.Label(
                correction_window,
                text=f"Die KI hat '{original_class}' erkannt, aber das stimmt nicht.\nWas ist es wirklich?",
                font=("Segoe UI", 11, "bold"),
                bg=self.bg_secondary,
                fg="white",
                wraplength=450
            ).pack(pady=15)
            
            # Text input for object name
            tk.Label(
                correction_window,
                text="Objektname eingeben:",
                font=("Segoe UI", 10),
                bg=self.bg_secondary,
                fg="white"
            ).pack(pady=5)
            
            name_entry = tk.Entry(
                correction_window,
                font=("Segoe UI", 11),
                width=30
            )
            name_entry.pack(pady=10, padx=20, fill=tk.X)
            name_entry.focus()
            
            # Label for suggested bin
            bin_label = tk.Label(
                correction_window,
                text="",
                font=("Segoe UI", 10, "bold"),
                bg=self.bg_secondary,
                fg="#27ae60",
                wraplength=450
            )
            bin_label.pack(pady=10)
            
            # Update suggestion when text changes (with debounce & error handling)
            suggestion_timer = None
            
            def update_suggestion_safe():
                """Safe version with error handling"""
                nonlocal suggestion_timer
                obj_name = name_entry.get().strip()
                if obj_name and len(obj_name) >= 2:  # Mindestens 2 Zeichen
                    try:
                        from waste_classifier import get_classifier
                        classifier = get_classifier()
                        result = classifier.classify_by_name_only(obj_name)
                        bin_name = result.get('bin_description', 'Unbekannt')
                        bin_label.config(
                            text=f"💡 Vorschlag: {bin_name}",
                            fg="#f39c12"
                        )
                    except Exception as e:
                        # Silently ignore errors during typing
                        bin_label.config(text="", fg="#e74c3c")
                else:
                    bin_label.config(text="")
                suggestion_timer = None
            
            def update_suggestion(*args):
                """Debounced update on every keystroke"""
                nonlocal suggestion_timer
                # Cancel previous timer
                if suggestion_timer is not None:
                    correction_window.after_cancel(suggestion_timer)
                # Schedule new update (300ms debounce)
                suggestion_timer = correction_window.after(300, update_suggestion_safe)
            
            name_entry.bind('<KeyRelease>', update_suggestion)
            
            def submit_correction():
                obj_name = name_entry.get().strip()
                if not obj_name:
                    messagebox.showwarning("Fehler", "Bitte Objektnamen eingeben")
                    return
                
                try:
                    from waste_classifier import get_classifier
                    from learning_db import get_db
                    
                    classifier = get_classifier()
                    db = get_db()
                    
                    # Get bin suggestion
                    result = classifier.classify_by_name_only(obj_name)
                    suggested_bin = result.get('bin_description', 'Restmüll')
                    
                    # WICHTIG: Speichere im dynamischen Mapping damit die KI es lernt!
                    normalized_name = classifier._normalize_class_name(obj_name)
                    if not (normalized_name in classifier.WASTE_MAPPING):
                        # Nur ins dynamische Mapping speichern wenn nicht schon statisch definiert
                        classifier.dynamic_mapping[normalized_name] = {
                            "primary": result.get('bin', 'RESTMÜLL'),
                            "material": result.get('material', 'unknown'),
                            "recyclable": result.get('recyclable', False),
                            "source": "user_feedback",
                            "learned_at": datetime.now().isoformat()
                        }
                    
                    # Store feedback
                    for det in self.last_detections:
                        det_id = det.get('detection_id')
                        if det_id:
                            db.add_feedback(
                                detection_id=det_id,
                                predicted_class=original_class,
                                correct_class=obj_name,
                                user_comment="Manuelle Korrektur"
                            )
                    
                    # Show result
                    self._print_result(f"\n✅ Korrektur gespeichert!\n  War: '{original_class}'\n  Ist: '{obj_name}'\n  → {suggested_bin}\n🧠 KI lernt: '{normalized_name}' = {suggested_bin}\n")
                    self._set_status("[OK] Feedback gespeichert - KI lernt!", "success")
                    
                    correction_window.destroy()
                    self.feedback_correct_btn.config(state=tk.DISABLED)
                    self.feedback_wrong_btn.config(state=tk.DISABLED)
                    
                except Exception as e:
                    messagebox.showerror("Fehler", f"Fehler beim Speichern: {e}")
                    print(f"[!] Feedback error: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Buttons
            button_frame = tk.Frame(correction_window, bg=self.bg_secondary)
            button_frame.pack(pady=20)
            
            submit_btn = tk.Button(
                button_frame,
                text="✅ Bestätigen & Speichern",
                font=("Segoe UI", 11, "bold"),
                bg=self.color_success,
                fg="white",
                command=submit_correction,
                padx=15,
                pady=10,
                relief=tk.FLAT
            )
            submit_btn.pack(side=tk.LEFT, padx=5)
            
            cancel_btn = tk.Button(
                button_frame,
                text="❌ Abbrechen",
                font=("Segoe UI", 11, "bold"),
                bg=self.color_error,
                fg="white",
                command=correction_window.destroy,
                padx=15,
                pady=10,
                relief=tk.FLAT
            )
            cancel_btn.pack(side=tk.LEFT, padx=5)
            
        except Exception as e:
            print(f"[!] Feedback wrong error: {e}")
            messagebox.showerror("Fehler", str(e))

    def _start_manual_draw_mode(self):
        """Öffne Fenster zum manuellen Zeichnen von Objekten"""
        try:
            if self.current_frame is None:
                messagebox.showwarning("Fehler", "Kein Kamerabild vorhanden - erst Kamera starten oder Bild laden")
                return
            
            from learning_db import get_db
            from waste_classifier import get_classifier
            
            db = get_db()
            classifier = get_classifier()
            frame = self.current_frame.copy()
            
            # Zeichnungs-Fenster
            draw_window = tk.Toplevel(self.root)
            draw_window.title("Manuelles Zeichnen - Rechteck ziehen (2x klicken: oben-links, unten-rechts)")
            draw_window.geometry("900x700")
            
            # Canvas für Bild
            canvas = tk.Canvas(draw_window, bg="black")
            canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Konvertiere OpenCV Frame zu PhotoImage
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb_frame)
            photo = ImageTk.PhotoImage(img)
            canvas_img = canvas.create_image(0, 0, image=photo, anchor='nw')
            canvas.image = photo  # Referenz halten
            
            # State für Zeichnen
            draw_state = {
                'points': [],
                'rect': None,
                'frame_h': frame.shape[0],
                'frame_w': frame.shape[1],
                'img_h': img.height,
                'img_w': img.width,
                'scale_x': img.width / frame.shape[1],
                'scale_y': img.height / frame.shape[0]
            }
            
            def canvas_click(event):
                """Click zum Zeichnen"""
                x, y = event.x, event.y
                
                if len(draw_state['points']) == 0:
                    # Erstes Punkt (oben-links)
                    draw_state['points'] = [x, y]
                    canvas.create_oval(x-3, y-3, x+3, y+3, fill='red', width=2)
                    status_label.config(text="✓ Punkt 1 gesetzt. Klick nun auf unten-rechts.", fg="#27ae60")
                elif len(draw_state['points']) == 2:
                    # Zweites Punkt (unten-rechts)
                    draw_state['points'].extend([x, y])
                    
                    # Zeichne Rechteck
                    if draw_state['rect']:
                        canvas.delete(draw_state['rect'])
                    x1, y1, x2, y2 = draw_state['points']
                    draw_state['rect'] = canvas.create_rectangle(
                        min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2),
                        outline='lime', width=2
                    )
                    
                    status_label.config(text="✓ Rechteck gezeichnet. Objektname eingeben.", fg="#27ae60")
                    ask_object_name()
                    
            def ask_object_name():
                """Frage nach Objektname"""
                name_window = tk.Toplevel(draw_window)
                name_window.title("Objektname")
                name_window.geometry("400x250")
                name_window.config(bg=self.bg_secondary)
                
                tk.Label(
                    name_window,
                    text="Was ist das Objekt?",
                    font=("Segoe UI", 12, "bold"),
                    bg=self.bg_secondary,
                    fg="white"
                ).pack(pady=10)
                
                entry = tk.Entry(name_window, font=("Segoe UI", 11), width=25)
                entry.pack(pady=10, padx=20)
                entry.focus()
                
                bin_label = tk.Label(
                    name_window,
                    text="",
                    font=("Segoe UI", 10),
                    bg=self.bg_secondary,
                    fg="#f39c12"
                )
                bin_label.pack(pady=5)
                
                def update_bin(*args):
                    obj_name = entry.get().strip()
                    if obj_name:
                        try:
                            result = classifier.classify_by_name_only(obj_name)
                            bin_desc = result.get('bin_description', 'Unbekannt')
                            bin_label.config(text=f"→ {bin_desc}")
                        except:
                            bin_label.config(text="(Fehler)")
                    else:
                        bin_label.config(text="")
                
                entry.bind('<KeyRelease>', update_bin)
                
                def submit():
                    obj_name = entry.get().strip()
                    if not obj_name:
                        messagebox.showwarning("Fehler", "Bitte Objektnamen eingeben")
                        return
                    
                    # Berechne reale Koordinaten
                    x1, y1, x2, y2 = draw_state['points']
                    bbox = {
                        "x1": int(min(x1, x2) / draw_state['scale_x']),
                        "y1": int(min(y1, y2) / draw_state['scale_y']),
                        "x2": int(max(x1, x2) / draw_state['scale_x']),
                        "y2": int(max(y1, y2) / draw_state['scale_y'])
                    }
                    
                    # KI-Vorschlag
                    result = classifier.classify_by_name_only(obj_name)
                    suggested_bin = result.get('bin', 'RESTMÜLL')
                    suggested_bin_desc = result.get('bin_description', 'Unbekannt')
                    
                    # Speichere manuelle Annotation
                    ann_id = db.save_manual_annotation(
                        bbox=bbox,
                        object_class=obj_name,
                        image_hash=None,
                        frame_path=None,
                        suggested_bin=suggested_bin_desc,
                        comment="Manuell gezeichnet"
                    )
                    
                    # Zeige Ergebnis
                    self._print_result(f"\n🎨 Manuelle Annotation gespeichert!\n  Objekt: '{obj_name}'\n  → {suggested_bin_desc}\n  (ID: {ann_id})\n")
                    self._set_status("[OK] Annotation gespeichert!", "success")
                    
                    name_window.destroy()
                    draw_window.destroy()
                
                submit_btn = tk.Button(
                    name_window,
                    text="✅ Speichern",
                    font=("Segoe UI", 11, "bold"),
                    bg=self.color_success,
                    fg="white",
                    command=submit,
                    padx=15,
                    pady=8,
                    relief=tk.FLAT
                )
                submit_btn.pack(pady=10)
            
            canvas.bind('<Button-1>', canvas_click)
            
            status_label = tk.Label(
                draw_window,
                text="Klick auf oben-links des Objekts",
                font=("Segoe UI", 10),
                bg="#333",
                fg="#f39c12"
            )
            status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
            
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler im Zeichenmodus: {e}")
            print(f"[!] Manual draw error: {e}")
        """Cleanup"""
        if self.camera_running:
            self._stop_camera()
        self.root.destroy()


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point with robust error handling"""
    try:
        print("\n" + "="*60)
        print("[TRASH]  SmarTrash - Desktop-Anwendung")
        print("="*60 + "\n")

        print(f"[PATH] Backend-Verzeichnis: {BACKEND_DIR}")
        print(f"[MODEL] Model: {MODEL_PATH}")
        print(f"[OK] Model vorhanden: {os.path.exists(MODEL_PATH)}\n")

        print("[LAUNCH] Starte GUI...\n")

        root = tk.Tk()
        app = SmarTrashApp(root)
        root.mainloop()

        # Normal exit
        print("\n[OK] App normal beendet")
        sys.exit(0)

    except Exception as e:
        print(f"\n[-] FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
