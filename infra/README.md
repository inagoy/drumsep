# Infra: bucket + Cloud Run + IAM

Placeholders usados abajo: `PROJECT_ID`, `REGION` (ej. `southamerica-east1`),
`BUCKET_NAME`, `GH_PAGES_ORIGIN` (ej. `https://tu-usuario.github.io`).

## 1. Bucket con borrado automático a los 7 días

```bash
gsutil mb -l $REGION gs://$BUCKET_NAME

# TTL de 7 días sobre TODO el contenido del bucket (uploads/ y stems/)
gsutil lifecycle set infra/bucket-lifecycle.json gs://$BUCKET_NAME

# Habilita que el browser suba (PUT) directo con la signed URL, y que
# pueda hacer preflight de las descargas si en algún momento se piden
# via fetch() en lugar de <a href>.
# Reemplazar el origin en infra/bucket-cors.json antes de aplicar.
gsutil cors set infra/bucket-cors.json gs://$BUCKET_NAME
```

Notar que el TTL de 7 días aplica tanto a `uploads/` (el archivo original)
como a `stems/` (los resultados). Si se quisiera un TTL distinto por
prefijo, hay que usar buckets separados: GCS lifecycle no soporta
condiciones por prefix+distintas acciones en un único bucket de forma
combinable con antigüedad diferente por carpeta de forma nativa más allá
de `matchesPrefix`, así que si esto importa conviene separar
`drumsep-uploads` y `drumsep-stems`.

## 2. Service account del Cloud Run + permisos

```bash
gcloud iam service-accounts create drumsep-api \
  --display-name="drumsep-api runtime"

SA_EMAIL="drumsep-api@${PROJECT_ID}.iam.gserviceaccount.com"

# Leer/escribir objetos del bucket de trabajo
gsutil iam ch serviceAccount:${SA_EMAIL}:roles/storage.objectAdmin gs://$BUCKET_NAME

# Auto-impersonación: necesaria para poder firmar URLs (signBlob) sin usar
# una key file. Ver api/gcs_utils.py.
gcloud iam service-accounts add-iam-policy-binding $SA_EMAIL \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/iam.serviceAccountTokenCreator"
```

## 3. Build & deploy del servicio

```bash
gcloud builds submit --config api/cloudbuild.yaml .

gcloud run deploy drumsep-api \
  --image gcr.io/${PROJECT_ID}/drumsep-api:latest \
  --region $REGION \
  --service-account $SA_EMAIL \
  --set-env-vars BUCKET_NAME=${BUCKET_NAME},ALLOWED_ORIGIN=${GH_PAGES_ORIGIN} \
  --memory 8Gi --cpu 4 \
  --timeout 900 \
  --concurrency 1 \
  --min-instances 0 \
  --allow-unauthenticated
```

Notas de sizing (ver también `dockerapp/GCP-job/README.md`, mismo modelo):
- `--memory 8Gi --cpu 4`: demucs es CPU/RAM-heavy; con menos memoria el
  proceso puede OOM-ear en archivos largos.
- `--timeout 900`: el request queda abierto mientras se procesa (ver
  decisión de diseño "sync" en el README raíz). Ajustar según duración
  típica de los audios que se esperan procesar.
- `--concurrency 1`: cada instancia procesa un archivo a la vez para no
  competir por CPU/RAM entre requests concurrentes en la misma instancia;
  el paralelismo real lo da el autoscaling de Cloud Run (con el costo de
  más cold starts).
- `--min-instances 0` minimiza costo pero implica cold start (descarga de
  modelo ya está horneada en la imagen, pero el arranque de Python/torch
  igual tarda). Subir a `--min-instances 1` si la latencia del primer
  request importa.

## 4. Frontend (GitHub Pages)

1. Editar `docs/config.js` con la URL del servicio de Cloud Run.
2. Publicar el contenido de `docs/` en GitHub Pages (Settings ->
   Pages -> Deploy from a branch -> carpeta `/docs`).
3. Confirmar que `GH_PAGES_ORIGIN` usado en el paso 3 y en
   `infra/bucket-cors.json` sea *exactamente* el origin publicado
   (protocolo + host, sin path), por ejemplo `https://usuario.github.io`
   (no `https://usuario.github.io/repo/`).
