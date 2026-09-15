# Size Reducer

App de escritorio para reducir el peso de videos (pensada para grabaciones de
pantalla / tutoriales) apuntando a un tamaño de archivo objetivo (200 MB,
500 MB, o el que quieras), manteniendo el video legible y el audio con buena
calidad.

## Cómo funciona

- Usa `ffmpeg` (descargado automáticamente por el paquete `imageio-ffmpeg`,
  no hace falta instalarlo aparte) con codificación de **dos pasadas** en
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

- Python 3.10+
- Windows (probado), aunque el código es portable a otros sistemas.

## Instalación

```powershell
cd d:\Dev\size-reducer
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
```

## Uso

```powershell
cd d:\Dev\size-reducer\size_reducer
..\venv\Scripts\python main.py
```

Pasos en la app:
1. "Seleccionar..." el video de entrada.
2. Elegir tamaño objetivo (200 MB, 500 MB o personalizado).
3. Elegir calidad de audio (160 kbps es un buen default para voz).
4. Elegir dónde guardar el resultado (por defecto sugiere
   `nombre_reducido.mp4` al lado del original).
5. "Comprimir" y esperar. Se puede cancelar en cualquier momento.

## Empaquetar como .exe standalone (para no depender de Python instalado)

```powershell
cd d:\Dev\size-reducer\size_reducer
..\venv\Scripts\pyinstaller --noconfirm --onefile --windowed --name SizeReducer main.py
```

El ejecutable queda en `size_reducer\dist\SizeReducer.exe`. Este build
incluye Python y las dependencias, pero **no** incluye el binario de ffmpeg
(imageio-ffmpeg lo descarga la primera vez que se ejecuta el programa en una
máquina, y lo cachea). Si necesitas un .exe 100% offline que no descargue
nada la primera vez, añade el binario de ffmpeg como dato empaquetado:

```powershell
..\venv\Scripts\pyinstaller --noconfirm --onefile --windowed --name SizeReducer ^
  --add-binary "%LOCALAPPDATA%\imageio_ffmpeg\ffmpeg-win-x86_64-v7.1.exe;imageio_ffmpeg/binaries" ^
  main.py
```

(Ajusta la ruta del binario según lo que imprima
`python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"`.)

## Estructura

```
size_reducer/
  main.py           # punto de entrada
  gui.py            # interfaz Tkinter
  compressor.py      # cálculo de bitrate + ejecución de ffmpeg en 2 pasadas
  ffmpeg_utils.py    # localizar ffmpeg y leer duración/resolución/fps
```
