from google.cloud import storage
import os
import subprocess
import glob #tmp

# Procesa archivos .mp3 o .wav

# Initialize the GCS client
client = storage.Client()
bucket_name = os.getenv('BUCKET_NAME', 'default-bucket-name')
input_dir = 'output/' # normally the output of spleeter process
output_dir = 'drums-output/'

print("**** Start ****")
print("PENDING: write processing logs to /logs/")

def list_files(bucket_name, prefix):
    """Lists all the blobs in the bucket and filters drums* files"""
    blobs = client.list_blobs(bucket_name, prefix=prefix)
    return [blob for blob in blobs if blob.name.endswith('drums.mp3') or blob.name.endswith('drums.wav')]

def download_blob(bucket_name, source_blob_name, destination_file_name):
    """Downloads a blob from the bucket."""
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)

def upload_blob(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the bucket."""
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)

def process_files():
    # List files in the bucket
    files = list_files(bucket_name, input_dir)
    print(f"Files to process {files}")
    for blob in files:
        local_input_path = '/tmp/' + os.path.basename(blob.name)
        local_output_path = '/tmp/output/drums'
        os.makedirs(local_output_path, exist_ok=True)

        # Download the file
        print(f"Downloading from bucket {blob.name}")
        download_blob(bucket_name, blob.name, local_input_path)

        #print(f"Final output is in {local_output_path_final}")
        track_name = blob.name[7:-10] # WARNING: hardcododes from paths
        print(f"Track name: {track_name}")
        #drums_input = '/tmp/output/' + os.path.splitext(os.path.basename(local_input_path))[0] + '/drums.wav'
        drums_input = local_input_path
        #drums_output = '/tmp/output/' + os.path.splitext(os.path.basename(local_input_path))[0] + '/'
        drums_output = local_output_path

        print(f"Drum sep process over {drums_input}")
        subprocess.run(['demucs','--repo',"model","-o",drums_output,"-n","49469ca8",drums_input])

        #subprocess.run(['/drumsep/drumsep','/tmp/drums.wav','/tmp/'])

        print(glob.glob("/tmp/*"))
        #print(glob.glob("/drumsep/*"))
        #print(glob.glob("/drumsep/model/*"))
        print(glob.glob(drums_output+"/*"))
        print(glob.glob(drums_output+"/49469ca8/drums/*"))

        # Upload the processed file back to GCS
        drums_output = drums_output +"/49469ca8/drums"
        output_files = os.listdir(drums_output)

        filename = os.path.splitext(os.path.basename(blob.name))[0]

        for output_file in output_files:
            full_output_path = os.path.join(drums_output, output_file)
            gcs_output_path = os.path.join(output_dir,track_name+'-'+filename,os.path.basename(output_file))
            print(f"Uploading {full_output_path} to {gcs_output_path}")
            upload_blob(bucket_name, full_output_path, gcs_output_path)


if __name__ == "__main__":
    process_files()


