import os
import tkinter as tk
from os.path import isfile, join
from PIL import Image, ImageTk
from config import NEG_FOLDER, POS_FOLDER, UNCLASSIFIED_IMAGE_FOLDER


# Ensure all necessary folders and files are created
if not os.path.isdir(UNCLASSIFIED_IMAGE_FOLDER):
    os.makedirs(UNCLASSIFIED_IMAGE_FOLDER)

if not os.path.isdir(POS_FOLDER):
    os.makedirs(POS_FOLDER)

if not os.path.isdir(NEG_FOLDER):
    os.makedirs(NEG_FOLDER)


images = [f for f in os.listdir(UNCLASSIFIED_IMAGE_FOLDER) if isfile(join(UNCLASSIFIED_IMAGE_FOLDER, f))]
unclassified_images = filter(lambda image: True, images)
current = None
prev_filename = ""


def next_img():
    global current, unclassified_images, prev_filename
    try:
        current = next(unclassified_images)
    except StopIteration:
        root.quit()

    try:
        print(current)
    except Exception:
        print("Failed to process filename, skipping to next image.")
        return

    pil_img = Image.open(f'{UNCLASSIFIED_IMAGE_FOLDER}/{current}')
    width, height = pil_img.size
    max_height = 1000

    if height > max_height:
        resize_factor = max_height / height
        pil_img = pil_img.resize((int(width * resize_factor), int(height * resize_factor)), resample=Image.LANCZOS)
    
    img_tk = ImageTk.PhotoImage(pil_img)
    img_label.img = img_tk
    img_label.config(image=img_label.img)

    filename_label.text = current
    filename_label.config(text=filename_label.text)

    prev_filename = current


def positive(arg):
    global current
    print("Positive")
    os.rename(f'{UNCLASSIFIED_IMAGE_FOLDER}/{current}', f'{POS_FOLDER}/{current}')
    next_img()


def negative(arg):
    global current
    print("Negative")
    os.rename(f'{UNCLASSIFIED_IMAGE_FOLDER}/{current}', f'{NEG_FOLDER}/{current}')
    next_img()


def discard(arg):
    global current
    print("Discarded")
    if os.path.isfile(f'{UNCLASSIFIED_IMAGE_FOLDER}/{current}'):
        os.remove(f'{UNCLASSIFIED_IMAGE_FOLDER}/{current}')
    next_img()


if __name__ == "__main__":
    root = tk.Tk()

    img_label = tk.Label(root)
    img_label.pack()

    filename_label = tk.Label(root)
    filename_label.pack()

    btn = tk.Button(root, text='Next Image', command=next_img)
    btn.pack()
    btn.bind("<Key-Right>", positive)
    btn.bind("<Key-Left>", negative)
    btn.bind("<Key-Down>", discard)

    # Load first image
    next_img()

    root.mainloop()
