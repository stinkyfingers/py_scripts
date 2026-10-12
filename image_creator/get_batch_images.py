import argparse
import json
import os
import base64
from io import BytesIO
from PIL import Image
from pathlib import Path
from dotenv import load_dotenv
from google import genai


parser = argparse.ArgumentParser(description="Generate a batch of images from a source image plus prompt file.")
parser.add_argument("--output_dir", default="output_images", help="Directory to save the generated image.")
args = parser.parse_args()

load_dotenv()  # Load environment variables from .env file

# 1. Initialize Client
client = genai.Client()

def run(output_dir):
        
    # 2. Paste the exact Batch Job Name string from your previous log output here
    # It looks like: "batches/XXXXXXXXXXXX"
    COMPLETED_BATCH_JOB_NAME = "batches/6n690zia5c1xkm1nd6q73m2p7k483yunagy0"

    print(f"Fetching completed job properties for: {COMPLETED_BATCH_JOB_NAME}")
    status_check = client.batches.get(name=COMPLETED_BATCH_JOB_NAME)

    if status_check.state.name != "JOB_STATE_SUCCEEDED":
        print(f"Warning: This job status is currently {status_check.state.name}, not SUCCEEDED.")

    print("Retrieving generated results manifest from Google's File API...")
    os.makedirs("generated_band_photos", exist_ok=True)
    try:
        # 3. FIX: Use the native SDK property path to locate the filename 
        results_file_id = status_check.dest.file_name
        print(f"Found server output path: {results_file_id}")
        
        # Download the text byte string stream directly from Google's File API
        raw_results_text = client.files.download(file=results_file_id)
        
        # Process the lines contained in the results JSONL manifest
        for line in raw_results_text.decode('utf-8').splitlines():
            if not line.strip():
                continue
            
            row = json.loads(line)
            custom_id = row.get("key")
            response_content = row.get("response", {})
            
            if "error" in response_content:
                print(f"Skipping variant '{custom_id}' due to processing error: {response_content['error']}")
                continue
                
            candidates = response_content.get("candidates", [])
            if not candidates:
                continue
                
            parts = candidates[0].get("content", {}).get("parts", []) if isinstance(candidates, list) else candidates.get("content", {}).get("parts", [])
            
            for part in parts:
                if "inlineData" in part:
                    b64_data = part["inlineData"].get("data")
                    
                    # Convert token bits back to a pristine picture
                    image_bytes = base64.b64decode(b64_data)
                    img = Image.open(BytesIO(image_bytes))
                    
                    output_filename = f"{output_dir}/{custom_id}.png"
                    img.save(output_filename, "PNG")
                    print(f" -> Successfully saved local image: {output_filename}")

        print(f"\nSuccess! All generated images are extracted into '{output_dir}'.")

    except Exception as e:
        print(f"\nFailed to extract batch items cleanly: {str(e)}")
        print("If you continue to hit unexpected typing properties, run 'print(vars(status_check))' to review structural components returned by the server endpoint.")

def main():
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    run(args.output_dir)

main()
    