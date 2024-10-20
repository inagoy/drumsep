Run drumsep as a container. Useful to run in a cloud context or isolating dependencies

# Setup

## GCP config
	gcloud init

	gcloud auth configure-docker

	gcloud builds submit --tag gcr.io/[]/my-drumsep-image . 

After the build:
You can verify this by checking the list of images in GCR:
	gcloud container images list --repository=[gcr.io/[PROJECT_ID]](http://gcr.io/%5BPROJECT_ID%5D)


	gcloud run deploy my-drumsep-service [params]

Then:
	gcloud builds submit --config cloudbuild.yaml . # enables layer cache, speeds up docker image building

## Instance

Check if with less RAM exits the process

16gb RAM
8 CPU


# Run Job

	Final output will be in [BUCKET]/drums-output/[TRACK]-drums/ as:
		bombo.wav
		platillos.wav
		redoblante.wav
		toms.wav
