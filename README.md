# Luffy2

Modello 3D stilizzato di Monkey D. Luffy dopo il timeskip, in posa statica.

- [`model/luffy.blend`](model/luffy.blend): scena modificabile con materiali, luci e camera.
- [`model/luffy.glb`](model/luffy.glb): personaggio esportato in glTF 2.0; non include luci o camera.
- [`model/preview.png`](model/preview.png): render di anteprima.
- [`model/build_luffy.py`](model/build_luffy.py): generatore procedurale del modello e degli esportati.

Il personaggio guarda verso **−Y**, ha Z verso l'alto ed è alto circa 1,78 unità. È composto da mesh separate e non è riggato o animato.

## Rigenerare

Con Blender 4.2 o successivo:

```sh
blender -b -t 4 --python model/build_luffy.py
```

Lo script sovrascrive i tre file generati nella cartella `model`. Per saltare il render usa `LUFFY_RENDER=0 blender -b --python model/build_luffy.py`. È possibile eseguire lo script anche con Python 3.11 e il modulo `bpy` compatibile installato.
