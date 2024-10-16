Run drumsep as a container. Useful to run in a cloud context or isolating dependencies

# Setup

	sudo docker build -t drumsep .
	sudo docker run -v $PWD/data:/data drumsep data/input/drums.wav /data/output/

# Run
	mkdir -p data/input
	mv [ORIGIN-DRUM-TRACK] data/input/drums.wav
	mkdir data/output
	
	sudo docker run -v $PWD/data:/data drumsep /data/input/drums.wav /data/output/

	Final output will be in data/output/49469ca8/drums as:
		bombo.wav
		platillos.wav
		redoblante.wav
		toms.wav
