#Simple Pythong script to run slideshow of images using WaveShare 7.5in V2 and Waveshare Raspberry Pi Adapter Board
#Requires Waveshare Library: https://github.com/waveshareteam/e-Paper 
#!/usr/bin/env python3
import os
import time
from PIL import Image, ImageOps, ImageEnhance, ImageStat
from waveshare_epd import epd7in5 # Define the display, look in Waveshare's folder for all display models to select a different model. 

# === Settings ===
IMAGE_DIR = "/home/pi/slideshow_images"
DELAY = 30          # seconds per image
INVERT = False      # Set True if blacks/whites appear reversed
THRESHOLD = 128     # Adjust 100–150 to tune darkness

def process_image(img_path):
    """
    Convert an image to clean, high-contrast 1-bit for eInk display.
    """
    image = Image.open(img_path).convert("L")
    image = image.resize((800, 480))

    # --- Contrast and gamma correction ---
    image = ImageEnhance.Contrast(image).enhance(2.0)
    image = ImageEnhance.Brightness(image).enhance(1.1)

    # Apply gamma correction to darken midtones
    gamma = 0.7  # lower = darker
    lut = [pow(x / 255.0, gamma) * 255 for x in range(256)]
    image = image.point(lut)

    # --- Convert to pure black & white with threshold ---
    bw = image.point(lambda x: 0 if x < THRESHOLD else 255, "1")

    # --- Optional inversion ---
    if INVERT:
        bw = ImageOps.invert(bw.convert("L")).convert("1")

    return bw


def main():
    epd = epd7in5.EPD() #Ensure this matches the model selected at top.
    epd.init()
    epd.Clear()  # full clear before starting

    images = sorted([
        os.path.join(IMAGE_DIR, f)
        for f in os.listdir(IMAGE_DIR)
        if f.lower().endswith(('.bmp', '.jpg', '.jpeg', '.png'))
    ])

    if not images:
        print(f"No images found in {IMAGE_DIR}")
        return

    print(f"Loaded {len(images)} images.")
    print("Press Ctrl+C to exit.")

    while True:
        for img_path in images:
            print(f"Displaying: {img_path}")
            image = process_image(img_path)
            epd.display(epd.getbuffer(image))
            time.sleep(DELAY)

            # optional light clear between images to reduce streaks
            epd.init()
            epd.Clear()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting...")
        epd7in5.epdconfig.module_exit()
