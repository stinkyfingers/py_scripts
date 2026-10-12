import os
from PIL import Image

# ====== CONFIGURATION ======
# Replace these paths with your actual folder paths
IMAGE_FOLDER = "/Users/johnshenk/Desktop/ChadEdwards/Photos"
LOGO_PATH = "/Users/johnshenk/Desktop/ChadEdwards/logo.png"
OUTPUT_FOLDER = "/Users/johnshenk/Desktop/ChadEdwards/Watermarked_Photos"

# Position presets: "top-left", "top-right", "bottom-left", "bottom-right", "center"
POSITION = "bottom-right" 
PADDING = 100 # Gap from the edges in pixels
# ===========================

def watermark_folder():
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    try:
        logo = Image.open(LOGO_PATH).convert("RGBA")
    except Exception as e:
        print(f"Error loading logo: {e}")
        return

    supported_formats = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
    
    for filename in os.listdir(IMAGE_FOLDER):
        if filename.lower().endswith(supported_formats):
            img_path = os.path.join(IMAGE_FOLDER, filename)
            try:
                with Image.open(img_path).convert("RGBA") as img:
                    # Calculate position
                    img_w, img_h = img.size
                    logo_w, logo_h = logo.size

                    ratio = min(img_w / logo_w, img_h / logo_h) * 0.15  # Calculate the scaling ratio - 15% of image
                    logo_resized = logo.resize((int(logo_w * ratio), int(logo_h * ratio)), Image.Resampling.LANCZOS)  # Resize logo maintaining aspect ratio
                    logo_w, logo_h = logo_resized.size  # Update logo dimensions after resizing

                    # Prevent logo from being larger than the image
                    if logo_w > img_w or logo_h > img_h:
                        print(f"Skipping {filename}: Image is smaller than the logo.")
                        continue

                    if POSITION == "top-left":
                        pos = (PADDING, PADDING)
                    elif POSITION == "top-right":
                        pos = (img_w - logo_w - PADDING, PADDING)
                    elif POSITION == "bottom-left":
                        pos = (PADDING, img_h - logo_h - PADDING)
                    elif POSITION == "center":
                        pos = ((img_w - logo_w) // 2, ((img_h - logo_h) // 2))
                    else: # bottom-right default
                        pos = (img_w - logo_w - PADDING, img_h - logo_h - PADDING)

                    # Overlay the logo
                    img.paste(logo_resized, pos, logo_resized)
                    
                    # Convert back to RGB if saving as JPEG
                    output_path = os.path.join(OUTPUT_FOLDER, filename)
                    if filename.lower().endswith(('.jpg', '.jpeg')):
                        img.convert("RGB").save(output_path, "JPEG", quality=95)
                    else:
                        img.save(output_path)
                        
                    print(f"Watermarked: {filename}")
            except Exception as e:
                print(f"Failed to process {filename}: {e}")

if __name__ == "__main__":
    watermark_folder()
