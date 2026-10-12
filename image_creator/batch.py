import csv
import json
import os
import re
import time
import base64
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
from google import genai
from google.genai import types
import argparse
from pathlib import Path


parser = argparse.ArgumentParser(description="Generate a batch of images from a source image plus prompt file.")
parser.add_argument("--input-file", default="variations.csv", help="Path to a file containing additional prompt text appended to the base instructions.")
parser.add_argument("--source-image-path", default="source.jpg", help="Path to the source image.")
parser.add_argument("--output-dir", default="generated_band_photos", help="Parent directory to save the generated images.")
args = parser.parse_args()

load_dotenv()  # Load environment variables from .env file


def output_dir_for_id(prompt_id):
    """Derive the output directory from a prompt id by stripping the trailing _<number>, e.g. 'chattahoochee_2' -> 'chattahoochee'."""
    return re.sub(r"_\d+$", "", prompt_id)

def run(source_image_path, input_file, output_dir):
    # =====================================================================
    # 1. INITIALIZATION & CONFIGURATION
    # =====================================================================
    # Initialize the client. It will automatically load the GEMINI_API_KEY environment variable.
    client = genai.Client()

    LOCAL_SOURCE_PHOTO = source_image_path
    VARIATIONS_CSV = input_file

    # =====================================================================
    # 2. UPLOAD REFERENCE PHOTO TO GEMINI FILE API
    # =====================================================================
    print(f"Uploading {LOCAL_SOURCE_PHOTO} to Gemini File API...")
    uploaded_photo = client.files.upload(file=LOCAL_SOURCE_PHOTO)
    print(f"Photo uploaded successfully. File ID: {uploaded_photo.name}")

    # Core facial preservation constraints passed as a strict system block
    system_prompt = (
        "[CRITICAL SYSTEM OVERRIDE: ABSOLUTE CHARACTER DEVIATION FORBIDDEN]\n"
        "You are acting as an advanced facial mapping engine. The provided source image contains "
        "exactly four human males who belong to the country music band 'Chad Edwards Band'.\n\n"
        "CORE OBJECTIVE: Generate a realistic variation of this scene according to the user instructions, "
        "locking and matching the physical personas of the four original subjects.\n\n"
        "FACIAL LIKENESS CONSTRAINT CHECKLIST:\n"
        "- Extract bone structure, facial spacing, hair, and symmetry directly from the reference image.\n"
        "- Headwear Alignment: Exactly match any cowboy hats, caps, or headpieces.\n"
        "- Eyewear Integration: Maintain specific glasses/sunglasses present on subjects."
    )

    def load_variations(csv_path):
        with open(csv_path, newline="") as f:
            return [{"id": row["id"], "prompt": row["prompt"]} for row in csv.DictReader(f, delimiter=";")]

    variations = load_variations(VARIATIONS_CSV)

    # =====================================================================
    # 3. BUILD THE LOCAL MANIFEST FILE
    # =====================================================================
    local_jsonl_file = "image_generation_batch.jsonl"
    print(f"Building local manifest file: {local_jsonl_file}...")
    with open(local_jsonl_file, "w") as f:
        for item in variations:
            payload = {
                "key": item["id"],
                "request": {
                    "contents": [
                        {
                            "parts": [
                                # Use the uploaded file's URI directly in the batch call
                                {"fileData": {"fileUri": uploaded_photo.uri, "mimeType": "image/jpeg"}},
                                {"text": item["prompt"]}
                            ]
                        }
                    ],
                    "systemInstruction": {"parts": [{"text": system_prompt}]},
                    "generation_config": {
                        "responseModalities": ["IMAGE"]
                    }
                }
            }
            f.write(json.dumps(payload) + "\n")

    # =====================================================================
    # 4. UPLOAD MANIFEST & DISPATCH THE DISCOUNTED BATCH JOB
    # =====================================================================
    print("Staging the manifest into Gemini File API...")
    # Explicitly use text/plain text mimetype to prevent schema mapping problems during batch submission
    uploaded_manifest = client.files.upload(file=local_jsonl_file, config=types.UploadFileConfig(mime_type="text/plain"))
    print(f"Manifest staged successfully. File ID: {uploaded_manifest.name}")

    print("\nSubmitting batch job to the 50% discounted off-peak pricing pool...")
    batch_job = client.batches.create(
        model="gemini-3.1-flash-image", 
        src=uploaded_manifest.name, # Passing the uploaded file identifier (e.g., 'files/abc123xyz')
        config={
            'display_name': "chad_edwards_band_variations"
        }
    )
    print(f"Batch Job Successfully Dispatched! ID: {batch_job.name}")

    # Polling loop checking completion status
    while True:
        status_check = client.batches.get(name=batch_job.name)
        
        # 1. Use .name to extract the clean text string from the SDK's enum object
        current_state = status_check.state.name if status_check.state else "UNKNOWN"
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Status: {current_state}")
        
        # 2. Check against the full enum string designations
        if current_state in ["JOB_STATE_SUCCEEDED", "JOB_STATE_FAILED", "JOB_STATE_CANCELED"]:
            break
        time.sleep(60)  # Verify status once every 60 seconds


    # 3. Ensure validation logic matches the enum string text
    if status_check.state and status_check.state.name != "JOB_STATE_SUCCEEDED":
        raise Exception(f"Batch job terminated unsuccessfully with state: {status_check.state.name}")

    print("\nBatch execution successful. Downloading results manifest...")

    # =====================================================================
    # 5. RETRIEVE AND PARSE THE GENERATED RESULTS
    # =====================================================================
    # When using the developer API, output metadata paths are included directly in the response metadata
    # or downloadable via the files utilities if provided. 
    # For developer API workflows, we loop over results mapped inside the completed job structure.

    print("\nExtracting and decoding base64 payload strings to PNG...")

    # Fetch results associated with the finished job
    # If results output metadata references an uploaded result file, we stream it directly
    try:
        # If the output generates a direct file path, grab the target content file
        results_file_id = status_check.dest.file_name
        # Use the client to download the text content of the processed JSONL file
        raw_results_text = client.files.download(file=results_file_id)
        
        for line in raw_results_text.decode('utf-8').splitlines():
            if not line.strip():
                continue
            
            row = json.loads(line)
            custom_id = row.get("key")
            response_content = row.get("response", {})
            
            if "error" in response_content:
                print(f"Skipping {custom_id} due to generation error: {response_content['error']}")
                continue
                
            candidates = response_content.get("candidates", [])
            if not candidates:
                continue
                
            parts = candidates[0].get("content", {}).get("parts", [])
            for part in parts:
                if "inlineData" in part:
                    b64_data = part["inlineData"].get("data")
                    
                    image_bytes = base64.b64decode(b64_data)
                    img = Image.open(BytesIO(image_bytes))

                    song_dir = Path(output_dir) / output_dir_for_id(custom_id)
                    os.makedirs(song_dir, exist_ok=True)
                    output_filename = f"{song_dir}/{custom_id}.png"
                    img.save(output_filename, "PNG")
                    print(f" -> Successfully saved image: {output_filename}")

    except Exception as e:
        print(f"Error accessing or parsing batch files: {str(e)}")
        print("If files are processing internally, inspect status output data or your developer console dashboard.")

    print("\nAll tasks finalized!")


def main():
    run(args.source_image_path, args.input_file, args.output_dir)

main()
