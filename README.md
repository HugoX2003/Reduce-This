# Reduce This

App de escritorio para reducir el peso de videos (pensada para grabaciones de
pantalla / tutoriales) apuntando a un tamaño de archivo objetivo (200 MB,
500 MB, o el que quieras), manteniendo el video legible y el audio con buena
calidad.

## Cómo funciona

- Usa `ffmpeg` (incluido en el paquete `imageio-ffmpeg`, no hace falta
  instalarlo aparte) con codificación de **dos pasadas** en
  H.264, calculando el bitrate de video necesario para llegar justo al
  tamaño pedido.
- El audio se codifica en AAC a una tasa fija (128/160/192 kbps a elegir) para
  que la voz se siga escuchando bien.
- Si el video de origen tiene más de 30 fps, se limita a 30 fps (las
  grabaciones de pantalla no necesitan más para verse nítidas), lo que deja
  más bitrate disponible para la nitidez de la imagen/texto en vez de
  gastarlo en fotogramas de más.
- La resolución original **no se toca**, para que el texto siga siendo
  legible.
- Si el tamaño pedido es demasiado chico para la duración del video, se avisa
  en la interfaz porque por debajo de cierto bitrate la calidad se resiente
  mucho.

## Requisitos

- Python 3.10+ **con Tkinter** (la interfaz gráfica lo necesita).
- Windows (probado) o macOS (Intel y Apple Silicon).
- Conexión a internet solo para instalar las dependencias. `ffmpeg` no hay
  que instalarlo aparte: lo trae el paquete `imageio-ffmpeg`.

### Windows

Instalá Python desde https://www.python.org/downloads/ (Tkinter ya viene
incluido). Marcá "Add python.exe to PATH" en el instalador.

### macOS

Lo más simple es instalar Python desde https://www.python.org/downloads/macos/
(Tkinter viene incluido). Si usás Homebrew, hace falta agregar Tk aparte:

```bash
brew install python python-tk
```

## Instalación

Clonar el repo y crear el entorno virtual con las dependencias.

Windows (PowerShell):

```powershell
git clone https://github.com/HugoX2003/Reduce-This.git
cd Reduce-This
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
```

macOS (Terminal):

```bash
git clone https://github.com/HugoX2003/Reduce-This.git
cd Reduce-This
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

## Uso

Windows (PowerShell):

```powershell
cd Reduce-This
.\venv\Scripts\Activate.ps1
cd reduce_this
python main.py
```

macOS (Terminal):

```bash
cd Reduce-This
source venv/bin/activate
cd reduce_this
python main.py
```

Si preferís no activar el venv, llamá al python del venv directo, desde la
carpeta `reduce_this`: `..\venv\Scripts\python main.py` en Windows, o
`../venv/bin/python main.py` en macOS.

Pasos en la app:
1. "Seleccionar..." el video de entrada.
2. Elegir tamaño objetivo (200 MB, 500 MB o personalizado).
3. Elegir calidad de audio (160 kbps es un buen default para voz).
4. Elegir dónde guardar el resultado (por defecto sugiere
   `nombre_reducido.mp4` al lado del original).
5. "Comprimir" y esperar. Se puede cancelar en cualquier momento.

## Empaquetar como app standalone (para no depender de Python instalado)

PyInstaller no compila de un sistema a otro: el `.exe` hay que generarlo en
Windows y el `.app` en un Mac. El binario de ffmpeg viene dentro del paquete
`imageio-ffmpeg` (no se descarga al ejecutar); `--collect-all` asegura que
quede incluido en el build.

Windows (PowerShell):

```powershell
cd reduce_this
..\venv\Scripts\pyinstaller --noconfirm --onefile --windowed --collect-all imageio_ffmpeg --name ReduceThis main.py
```

Queda en `reduce_this\dist\ReduceThis.exe`.

macOS (Terminal):

```bash
cd reduce_this
../venv/bin/pyinstaller --noconfirm --windowed --collect-all imageio_ffmpeg --name ReduceThis main.py
```

Queda en `reduce_this/dist/ReduceThis.app`. Como la app no está firmada por
Apple, la primera vez macOS la bloquea: click derecho sobre la app → Abrir →
Abrir (o Ajustes del Sistema → Privacidad y seguridad → "Abrir de todos
modos").

## Estructura

```
reduce_this/
  main.py           # punto de entrada
  gui.py            # interfaz Tkinter
  compressor.py      # cálculo de bitrate + ejecución de ffmpeg en 2 pasadas
  ffmpeg_utils.py    # localizar ffmpeg y leer duración/resolución/fps
```
