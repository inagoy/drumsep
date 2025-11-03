# drumsep
Drum separation based on a [Hybrid Demucs](https://github.com/facebookresearch/demucs) model. <br />
Code to facilitate access to the model presented in the thesis "Separación de fuentes  en grabaciones de batería mediante aprendizaje automático" (2022).

<p align="left">
<img src="https://euda.unq.edu.ar/wp-content/uploads/2021/05/logos-UNQ-265x65-1.png" alt="Universidad Nacional de Quilmes.">
</p>

The model takes as input an audio file (mp3, wav, flac, or ogg) corresponding to a drum recording and exports 4 audio files classified as:
* Bombo (Kick)
* Redoblante (Snare)
* Platillos (Cymbals)
* Toms


### With Google Colab
To easily use the model online: <br />
[drumsep Notebook](https://colab.research.google.com/drive/1UQSv0wGhGgnwcbqIAYb4ykfWIeoaXaqh?usp=sharing)

### With Linux
Having pip installed. <br />
  1. Clone repo.
  2. Install.
```bash
bash drumsepInstall
```
  3. Separate <br />
  <PATH_IN>  Path to the audio file or directory containing audio files to be separated. <br />
  <PATH_OUT> Path to the directory where the generated audio files will be exported. <br />
```bash
bash drumsep "<PATH_IN>" "<PATH_OUT>"
```

(Efforts are currently underway to advance research and document progress for this project, with the ultimate objective of sharing valuable insights with the wider community).
