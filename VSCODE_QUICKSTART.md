# 🚀 SmarTrash - VS Code Quick Start

## ⚡ In 3 Sekunden starten:

### 1. VS Code öffnen
```
Öffne diesen Ordner in VS Code:
C:\Philipp\Schule\SmarTrash\SmarTrash\
```

### 2. Drücke F5
Das wars! 🎉

---

## 📖 Was passiert beim ersten F5?

1. ✅ VS Code installiert empfohlene Extensions (einmalig)
2. ✅ Python Interpreter wird ausgewählt (`backend/venv`)
3. ✅ Server startet mit uvicorn + auto-reload
4. ✅ Umgebungsvariablen werden automatisch gesetzt
5. ✅ Terminal zeigt: "Uvicorn running on http://0.0.0.0:8000"

### Dann öffnen:
```
http://localhost:8000/dashboard
```

---

## 🎯 3 Start-Modi (Dropdown neben Play-Button)

### 🚀 SmarTrash Server (Standard)
- **Bester Modus für Entwicklung**
- Mit `--reload`: Code-Änderungen → Auto-Restart
- F5 drücken → Server läuft

### 🐛 SmarTrash Debug
- **Für Debugging mit Breakpoints**
- Setze Breakpoints (Klick links neben Zeile)
- F5 → Code stoppt bei Breakpoints
- Variables inspizieren, Step-through

### 🧪 Quick Test
- **Schnellster Start**
- Ohne `--reload`
- Für schnelle API-Tests

---

## ⌨️ Wichtigste Shortcuts

| Taste | Aktion |
|-------|--------|
| **F5** | Server starten |
| **Shift+F5** | Server stoppen |
| **Ctrl+Shift+F5** | Server neustarten |
| **F9** | Breakpoint setzen/entfernen |
| **F10** | Step Over (nächste Zeile) |
| **F11** | Step Into (in Funktion) |
| **Ctrl+`** | Terminal öffnen |
| **Ctrl+Shift+P** | Command Palette (Tasks) |

---

## 📋 Nützliche Tasks

**Ctrl+Shift+P** → "Tasks: Run Task" → wähle:

- **📦 Install Dependencies** - pip install alles
- **🔍 Check Compliance** - Compliance Report anzeigen
- **📊 Export Dataset** - Training-Daten exportieren
- **🧹 Cleanup Old Data** - Alte Dateien löschen
- **🌐 Open Dashboard** - Browser öffnen

---

## 🔧 Wenn was nicht funktioniert:

### Python Extension fehlt?
→ VS Code fragt automatisch beim ersten F5
→ Oder: Extensions Tab → "Python" suchen → installieren

### Dependencies fehlen?
→ **Ctrl+Shift+P** → "📦 Install Dependencies"
→ Oder: Terminal: `pip install -r backend/requirements.txt`

### Port 8000 belegt?
→ Server findet automatisch freien Port
→ Oder ändere in `.vscode/launch.json`: `"--port", "8001"`

### Model fehlt?
→ Server startet trotzdem (für API-Tests)
→ Download: https://github.com/Megvii-BaseDetection/YOLOX/releases
→ Speichern: `C:\models\yolox_s.pth`

---

## 💡 Pro-Tipps

### 1. Code ändern während Server läuft
- Server läuft mit `--reload`
- Code ändern → speichern → Auto-Restart
- Keine manuelle Neustarts!

### 2. Debugging nutzen
```
1. Breakpoint setzen (F9 oder Klick links)
2. F5 → "🐛 SmarTrash Debug"
3. API Request machen (Dashboard oder curl)
4. Code stoppt → Variables sehen
5. F10/F11 für Step-through
```

### 3. Terminal nutzen
- **Ctrl+`** öffnet integriertes Terminal
- Automatisch in `backend/` Ordner
- Umgebungsvariablen schon gesetzt
- Nutze für: `pip install`, `python -c ...`, etc.

### 4. Schnell zu Datei
- **Ctrl+P** → Datei-Name tippen
- Fuzzy search: `mainpy` findet `main.py`
- Enter → Datei öffnet sich

### 5. IntelliSense nutzen
- **Ctrl+Space** bei Tippen → Auto-Completion
- Hover über Funktion → Docstring sehen
- **F12** auf Funktion → Go to Definition

---

## 🎓 Workflow-Beispiel

### Normale Entwicklung:
```
1. VS Code öffnen
2. F5 drücken (Server startet)
3. Browser: http://localhost:8000/dashboard
4. Code in main.py ändern
5. Speichern (Ctrl+S)
6. Server reloaded automatisch
7. Browser refreshen (F5)
8. Testen
9. Shift+F5 wenn fertig
```

### Mit Debugging:
```
1. In inference.py Breakpoint setzen (Zeile 150)
2. F5 → "🐛 SmarTrash Debug" wählen
3. Dashboard: Bild hochladen
4. Code stoppt bei Zeile 150
5. Variables: detections inspizieren
6. F10: Step-through
7. Continue (F5) oder Stop (Shift+F5)
```

---

## 📊 Was ist konfiguriert?

### .vscode/launch.json
- 3 Debug-Konfigurationen
- Auto-setzt Umgebungsvariablen
- Working Directory: `backend/`

### .vscode/settings.json
- Python Interpreter: `backend/venv`
- Auto-Import aktiviert
- File-Excludes (cleaner workspace)

### .vscode/tasks.json
- 7 vordefinierte Tasks
- Schnelle Shortcuts für häufige Aktionen

### .vscode/extensions.json
- Empfohlene Extensions
- VS Code schlägt automatisch vor

---

## 🔄 Weitere Konfiguration

### Model-Pfad ändern?
`.vscode/launch.json` → `env` → `YOLOX_CKPT`
```json
"YOLOX_CKPT": "D:\\andere\\pfad\\model.pth"
```

### GPU nutzen?
`.vscode/launch.json` → `env` → `YOLOX_DEVICE`
```json
"YOLOX_DEVICE": "cuda"
```

### Port ändern?
`.vscode/launch.json` → `args`
```json
"--port", "8080"
```

---

## 📚 Mehr lernen?

- **VS Code Docs**: https://code.visualstudio.com/docs
- **Python in VS Code**: https://code.visualstudio.com/docs/python
- **.vscode/README.md**: Detaillierte Infos zur Konfiguration

---

## ✅ Checkliste

- [ ] VS Code geöffnet in SmarTrash Ordner
- [ ] Python Extension installiert (VS Code fragt automatisch)
- [ ] Dependencies installiert (F5 zeigt Fehler wenn nicht)
- [ ] F5 gedrückt
- [ ] Server läuft (Terminal zeigt "Uvicorn running")
- [ ] Dashboard öffnet: http://localhost:8000/dashboard

**Alles grün?** 🎉 **Ready to code!**

---

*Happy Coding mit VS Code! 🚀*
