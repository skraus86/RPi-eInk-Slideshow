#eInk Slideshow Python Webserver - Run below to add prereqs
#sudo apt update
#sudo apt install python3-flask python3-pil
#!/usr/bin/env python3
import os
import time
import threading
from flask import Flask, render_template, request, redirect, send_from_directory, url_for
from PIL import Image, ImageOps, ImageEnhance
from waveshare_epd import epd7in5

# ==== CONFIG ====
IMAGE_DIR = "/home/pi/slideshow_images"
DELAY = 30              # Seconds per image
PORT = 8080
INVERT = False           # Set True if display colors look inverted
THRESHOLD = 128          # 100–150 for darker/lighter
GAMMA = 0.7              # <1 darkens midtones
CONTRAST = 2.0
BRIGHTNESS = 1.1

# ==== INIT ====
app = Flask(__name__)
os.makedirs(IMAGE_DIR, exist_ok=True)
epd = None
stop_thread = False


# ==== IMAGE PROCESSING ====
def process_image(img_path):
    """Convert an image to crisp black/white for eInk."""
    image = Image.open(img_path).convert("L")
    image = image.resize((800, 480))

    # Enhance contrast and brightness
    image = ImageEnhance.Contrast(image).enhance(CONTRAST)
    image = ImageEnhance.Brightness(image).enhance(BRIGHTNESS)

    # Apply gamma correction
    lut = [pow(x / 255.0, GAMMA) * 255 for x in range(256)]
    image = image.point(lut)

    # Convert to pure black/white
    bw = image.point(lambda x: 0 if x < THRESHOLD else 255, "1")

    # Optional inversion (depends on panel variant)
    if INVERT:
        bw = ImageOps.invert(bw.convert("L")).convert("1")

    return bw


# ==== SLIDESHOW THREAD ====
def slideshow_loop():
    global stop_thread, epd
    epd = epd7in5.EPD()
    epd.init()
    epd.Clear()

    last_image_list = []

    while not stop_thread:
        try:
            # Get sorted image list
            images = sorted([
                os.path.join(IMAGE_DIR, f)
                for f in os.listdir(IMAGE_DIR)
                if f.lower().endswith(('.bmp', '.jpg', '.jpeg', '.png'))
            ])

            if not images:
                time.sleep(5)
                continue

            # Only reload if folder content changed
            if images != last_image_list:
                print("Image list updated.")
                last_image_list = images

            for img_path in images:
                if stop_thread:
                    break
                print("Displaying:", img_path)
                image = process_image(img_path)
                epd.display(epd.getbuffer(image))
                time.sleep(DELAY)
                epd.init()   # full refresh between slides
                epd.Clear()

        except Exception as e:
            print("Error in slideshow loop:", e)
            time.sleep(5)


# ==== WEB SERVER ROUTES ====
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'bmp'}


@app.route('/')
def index():
    files = sorted(os.listdir(IMAGE_DIR))
    images = [f for f in files if allowed_file(f)]
    return render_template('index.html', images=images)


@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return redirect(url_for('index'))
    file = request.files['file']
    if file and allowed_file(file.filename):
        save_path = os.path.join(IMAGE_DIR, file.filename)
        file.save(save_path)
    return redirect(url_for('index'))


@app.route('/delete/<filename>', methods=['POST'])
def delete(filename):
    file_path = os.path.join(IMAGE_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    return redirect(url_for('index'))


@app.route('/images/<filename>')
def serve_image(filename):
    return send_from_directory(IMAGE_DIR, filename)


# ==== MAIN START ====
if __name__ == "__main__":
    # Start slideshow in background
    thread = threading.Thread(target=slideshow_loop, daemon=True)
    thread.start()

    try:
        app.run(host="0.0.0.0", port=PORT, debug=False)
    except KeyboardInterrupt:
        print("Shutting down...")
        stop_thread = True
        if epd:
            epd7in5.epdconfig.module_exit()
