import argparse
from io import BytesIO
from PIL import Image
from google.genai import types
from google import genai
import sys
from pathlib import Path
import time
from dotenv import load_dotenv
import os

parser = argparse.ArgumentParser(description="Generate an image from a source image plus a prompt.")
parser.add_argument("--input", default="", help="Additional prompt text appended to the base instructions.")
parser.add_argument("--input-file", default="", help="Path to a file containing additional prompt text appended to the base instructions.")
parser.add_argument("--source_image_path", default="source.jpg", help="Path to the source image.")
parser.add_argument("--output_dir", default="output_images", help="Directory to save the generated image.")
parser.add_argument("--prefix", default="", help="Prefix for the output filename.")
args = parser.parse_args()

load_dotenv()

# model = "gemini-3.1-flash-lite-image" # bad with facial likeness, but good with image generation
model = "gemini-3.1-flash-image" 


base_input = """
[CRITICAL SYSTEM OVERRIDE: ABSOLUTE CHARACTER DEVIATION FORBIDDEN]
You are acting as an advanced facial mapping engine. The provided source image contains exactly four human males who belong to the country music band "Chad Edwards Band". 

CORE OBJECTIVE:
Generate a realistic variation of this scene according to the trailing user instructions. However, you must lock, isolate, and identical-match the physical personas of the four original subjects. 

FACIAL LIKENESS CONSTRAINT CHECKLIST:
- Extract bone structure, facial spacing, hair, and exact facial symmetry directly from the 4 men in the reference image. Do not use generic fallback faces.
- Headwear Alignment: Exactly match any cowboy hats, caps, or headpieces worn by the respective individuals. Do not remove or swap their original headwear.
- Eyewear Integration: Maintain the specific design and shape of any glasses or sunglasses present on the subjects.
- Subject Integrity: The facial attributes of these 4 specific men must remain unmutated, clearly recognizable, and unaltered by any contextual text modifications appended to this prompt.

USER MODIFICATION INSTRUCTIONS:
{}
"""

client = genai.Client(api_key=os.environ["API_KEY"])

if args.input == "" and args.input_file == "":
    sys.exit("Please provide additional prompt text using the --input or --input-file argument.")


def get_text_inputs():
    with open(args.input_file, "r") as f:
        lines = [line.strip() for line in f]
    return lines

def create_image(gemini_input, source_image, output_dir="output_images", output_filename="output.png"):
    response = client.models.generate_content(
        contents=[gemini_input, source_image],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"]
        ),
        model = model
    )
    image_saved = False
    if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data is not None:
                image = Image.open(BytesIO(part.inline_data.data))
                image.save(f"{args.output_dir}/{output_filename}")
                image_saved = True
                break

    if image_saved:
        print(f"Image successfully generated and saved as {args.output_dir}/{output_filename}")
    else:
        print("No image was generated.")


def main():
    source_image = Image.open(args.source_image_path)
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    if args.input_file:
        text_inputs = get_text_inputs()
    else:
        text_inputs = [args.input]

    for index, text_input in enumerate(text_inputs):
        gemini_input = base_input.format(text_input)
        filename = f"{args.prefix}_{time.time()}"
        create_image(gemini_input, source_image, output_dir=args.output_dir, output_filename=f"{filename}.png")
        time.sleep(1)  # Sleep for 1 second to avoid overwhelming the API


main()

# SETUP
# python -m venv .venv
# source .venv/bin/activate
# pip install -r requirements.txt

# RUN
# python main.py --input "extra prompt text" OR --input-file "path/to/input_file.txt"