# drumsep
Separación de baterías a partir de un modelo de Hybrid Demucs <br />

Código para facilitar el acceso al Modelo Final presentado en la tesis “Separación <br /> de fuentes  en grabaciones de batería mediante aprendizaje automático” (2022).
<p align="left">
<img src="https://euda.unq.edu.ar/wp-content/uploads/2021/05/logos-UNQ-265x65-1.png" alt="Universidad Nacional de Quilmes.">
</p>

### Con Google Colab
Para utilizar el modelo de manera sencilla online. <br />
[Notebook de drumsep](https://colab.research.google.com/drive/14uxUczAYP9EUZLZmA_uWv5I_mDU7iqJS?usp=sharing)

### Con Linux
Teniendo instalado pip. <br />
  1. Clonar el repositorio.
  2. Instalar
```bash
bash drumsepInstall
```
  2. Separar
  <PATH_IN> : Ruta del archivo de audio o directorio contendedor de archivos de audio a separar. <br />
  <PATH_OUT> : Ruta del directorio donde se exportarán los audios generados. <br />
```bash
bash drumsep "<PATH_IN>" "<PATH_OUT>"
```

