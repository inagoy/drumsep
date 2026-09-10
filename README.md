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

# GCP job

check dockerapp/GCP-job/cloudbuild.yaml

# Web app (frontend + API)

Además del batch job original (`dockerapp/GCP-job`, que sigue existiendo
para procesamiento masivo/offline sobre un bucket completo), este repo
incluye una app web de punta a punta para separar stems bajo demanda:

```
frontend/  ->  sitio estático (GitHub Pages): sube el audio y muestra los
               links de descarga.
api/       ->  servicio en Cloud Run (FastAPI): valida el origin, firma
               URLs de GCS y corre ffmpeg + demucs sobre un archivo.
infra/     ->  lifecycle del bucket (TTL 7 días), CORS del bucket, y los
               comandos gcloud/IAM para desplegar todo.
```

Flujo:
1. El browser (GitHub Pages) pide una signed URL de subida a
   `POST /v1/uploads`.
2. El browser sube el archivo **directo a GCS** con esa URL (no pasa por
   Cloud Run).
3. El browser llama a `POST /v1/process`; el servicio descarga el
   archivo, lo normaliza con `ffmpeg`, corre `demucs` (modelo drumsep) y
   sube los 4 stems a `stems/{track_id}/` en el mismo bucket.
4. La respuesta incluye signed URLs de descarga (GET, 24hs) para cada
   stem.
5. Una lifecycle rule del bucket borra todo (`uploads/` y `stems/`) a los
   7 días, sin intervención manual.

Instrucciones de despliegue completas: `infra/README.md`.

## Decisiones de diseño y tradeoffs

- **Upload directo a GCS vía signed URL, no a través del proxy.** Cloud
  Run tiene un límite práctico de tamaño/tiempo de request; subir el
  archivo directo al bucket evita ese cuello de botella y deja al
  servicio de Cloud Run libre para lo que realmente necesita CPU:
  ffmpeg + demucs. El costo es que el bucket necesita su propia config de
  CORS (además de la del servicio).

- **Procesamiento síncrono, no un Job/cola separada.** `POST /v1/process`
  bloquea hasta terminar y devuelve los links de descarga en la misma
  respuesta. Es la opción más simple de operar (no hay estado a
  persistir, no hay que resolver "¿cómo aviso al cliente que terminó?").
  El tradeoff es que ata una conexión/instancia de Cloud Run durante
  todo el procesamiento (por eso `--concurrency 1` y un timeout alto).
  **Mejora natural si el tráfico crece**: pasar a un patrón async (el
  servicio devuelve 202 + `track_id`, un Cloud Run Job o Eventarc
  (trigger en la subida a GCS) hace el trabajo pesado, y el estado se
  guarda en Firestore o en un `status.json` en el propio bucket que el
  frontend poll-ea). Esto también permite escalar el paso de
  separación independiente del paso de "servir HTTP".

- **`ALLOWED_ORIGIN` como control de acceso.** Se valida en dos capas: (a)
  CORS (`Access-Control-Allow-Origin`) para que solo JS corriendo en la
  GitHub Page pueda *leer* la respuesta desde un browser, y (b) un chequeo
  server-side del header `Origin` que devuelve 403 si no matchea, para
  que un script cualquiera no pueda invocar la API directamente ignorando
  CORS. **Importante:** el header `Origin` lo controla el cliente, así
  que esto no es autenticación real, es un allow-list barato pensado para
  "que solo la página lo use de forma normal", no para bloquear un
  atacante decidido. Si el costo de procesamiento (CPU) es una
  preocupación real (abuso/DoS económico), sumar alguno de:
  - un token de invocación simple (header secreto compartido con el
    frontend, aceptable dado que el frontend es público igual),
  - Firebase App Check o un captcha antes de pedir la signed URL,
  - Cloud Armor / un Load Balancer delante de Cloud Run con rate
    limiting por IP.

- **Signed URLs sin key file, via IAM `signBlob` (auto-impersonación).**
  Cloud Run no expone una private key, así que en vez de montar un JSON
  de service account (mal hábito, rotación manual, riesgo si se filtra),
  el servicio se impersona a sí mismo (`roles/iam.serviceAccountTokenCreator`
  sobre su propia SA) y usa la IAM API para firmar. Es la práctica
  recomendada por Google para este escenario (ver `api/gcs_utils.py`).

- **TTL de 7 días a nivel bucket (lifecycle rule), no un cron/limpieza
  manual.** Es la opción más simple y confiable: GCS lo garantiza sin
  código adicional. Tradeoff: aplica por igual a `uploads/` (input) y
  `stems/` (output); si se necesitara un TTL distinto por carpeta habría
  que separar en dos buckets.

- **Paso explícito de `ffmpeg` antes de `demucs`.** El Dockerfile
  original ya traía `ffmpeg` instalado (demucs/torchaudio lo usa
  internamente para decodificar), pero el pipeline no lo invocaba
  explícitamente y dependía del nombre de archivo (`*drums.mp3/wav`)
  producido por un paso previo de spleeter. `api/processing.py` agrega
  una normalización explícita (`ffmpeg -ac 2 -ar 44100 -sample_fmt s16`)
  antes de correr demucs, lo que (a) permite aceptar cualquier formato
  que ffmpeg sepa decodificar (m4a, ogg/opus, etc.), no solo los 4 que
  drumsep documenta, y (b) evita sorpresas de sample rate/canales en
  archivos "raros" subidos por usuarios reales.

- **Un solo Cloud Run para todo (`api/`), en vez de proxy + worker
  separados.** Se evaluó separar "servicio que valida origin y firma
  URLs" de "servicio que hace el procesamiento pesado", pero para el
  alcance de este proyecto agregaba una llamada de servicio a servicio
  (con su propio problema de auth) sin beneficio claro. Si el pipeline
  de separación se usara desde más de un frontend/cliente, separar
  "API pública" de "worker interno" (no invocable directamente, solo vía
  Pub/Sub o llamado autenticado) sí se justificaría.

## Quick wins / mejoras pendientes

- Reemplazar el signed PUT simple por una **signed POST policy** con
  `content-length-range`, para poner un límite real de tamaño de subida
  (hoy `MAX_INPUT_BYTES` en `api/processing.py` solo corta *después* de
  bajar el archivo completo del bucket).
- Agregar **retry/backoff** y manejo explícito de "archivo corrupto o no
  es audio" con un mensaje claro en el frontend (hoy ffmpeg simplemente
  falla y se propaga como 422).
- **Progreso real** en el frontend: hoy es un solo spinner de "subiendo /
  procesando"; con el patrón async (ver arriba) se podría dar feedback
  por etapa (subida, normalización, separación, listo).
- **Tests**: no hay tests automatizados para `api/processing.py` ni para
  el flujo end-to-end; valdría la pena al menos un test que mockee GCS y
  corra ffmpeg+demucs contra un wav corto de fixture.
- Considerar **Cloud CDN / cache** para el frontend estático si el
  tráfico crece (GitHub Pages ya sirve razonablemente bien, pero es un
  quick win si se migra a un dominio propio).

### With Google Colab
To easily use the model online: <br />
[drumsep Notebook](https://colab.research.google.com/drive/14uxUczAYP9EUZLZmA_uWv5I_mDU7iqJS?usp=sharing)

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

# Ref

“Separación de fuentes en grabaciones de batería mediante aprendizaje automático”. Por Iñaki Goyeneche. 
https://drive.google.com/file/d/1pqsujRU_kqjG6ymWDqohg45ShCskZCBQ/view 
