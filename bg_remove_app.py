import os
import tkinter as tk
from tkinter import messagebox, colorchooser
from rembg import remove
from PIL import Image, ImageColor
from io import BytesIO

# Set working directory to script location
os.chdir(os.path.dirname(os.path.abspath(__file__)))

class BGRemoverApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Background Remover")
        self.root.geometry("420x520")

        # Transparent checkbox
        self.transparent_var = tk.BooleanVar(value=True)
        tk.Checkbutton(root, text="Transparent background", variable=self.transparent_var).pack(pady=5)

        # Background color button (only when not transparent)
        self.bg_color = "#ffffff"  # default to white
        self.color_button = tk.Button(root, text="Choose Background Color", command=self.pick_color)
        self.color_button.pack(pady=5)
        self.toggle_color_button()  # Set visibility
        self.transparent_var.trace_add('write', lambda *args: self.toggle_color_button())

        # Target size selector
        tk.Label(root, text="Target Size").pack()
        self.size_options = ["Original", "256x256", "512x512", "1024x1024", "Custom"]
        self.selected_size = tk.StringVar(value=self.size_options[0])
        tk.OptionMenu(root, self.selected_size, *self.size_options, command=self.toggle_custom_fields).pack()

        # Custom size fields
        self.custom_frame = tk.Frame(root)
        tk.Label(self.custom_frame, text="Width:").grid(row=0, column=0)
        self.custom_width = tk.Entry(self.custom_frame, width=6)
        self.custom_width.grid(row=0, column=1, padx=5)
        tk.Label(self.custom_frame, text="Height:").grid(row=0, column=2)
        self.custom_height = tk.Entry(self.custom_frame, width=6)
        self.custom_height.grid(row=0, column=3, padx=5)
        self.custom_frame.pack(pady=5)
        self.custom_frame.pack_forget()

        # Bevel inputs
        tk.Label(root, text="Side Bevel (% of width):").pack()
        self.side_bevel = tk.Entry(root, width=6)
        self.side_bevel.insert(0, "0")
        self.side_bevel.pack()

        tk.Label(root, text="Top/Bottom Bevel (% of height):").pack()
        self.top_bottom_bevel = tk.Entry(root, width=6)
        self.top_bottom_bevel.insert(0, "0")
        self.top_bottom_bevel.pack()

        # Info + Run
        tk.Label(root, text="Input folder: RawPhotos/").pack(pady=5)
        tk.Button(root, text="Start Processing", command=self.process_images).pack(pady=10)
        self.status_label = tk.Label(root, text="")
        self.status_label.pack()

        os.makedirs("RawPhotos", exist_ok=True)

    def toggle_custom_fields(self, value):
        if value == "Custom":
            self.custom_frame.pack(pady=5)
        else:
            self.custom_frame.pack_forget()

    def toggle_color_button(self):
        if self.transparent_var.get():
            self.color_button.pack_forget()
        else:
            self.color_button.pack(pady=5)

    def pick_color(self):
        color = colorchooser.askcolor(initialcolor=self.bg_color)
        if color[1]:
            self.bg_color = color[1]
            self.color_button.config(bg=self.bg_color)

    def process_images(self):
        transparent = self.transparent_var.get()
        size_option = self.selected_size.get()

        try:
            side_pad_percent = float(self.side_bevel.get())
            top_pad_percent = float(self.top_bottom_bevel.get())
        except ValueError:
            messagebox.showerror("Invalid Input", "Bevel values must be numbers.")
            return

        # Size logic
        if size_option == "Original":
            target_size = None
            size_name = "Original"
        elif size_option == "Custom":
            try:
                w = int(self.custom_width.get())
                h = int(self.custom_height.get())
                if w <= 0 or h <= 0:
                    raise ValueError
                target_size = (w, h)
                size_name = f"{w}x{h}"
            except ValueError:
                messagebox.showerror("Invalid Input", "Custom width and height must be positive integers.")
                return
        else:
            w, h = map(int, size_option.split('x'))
            target_size = (w, h)
            size_name = f"{w}x{h}"

        output_folder = f"FinishedPhotos_{'Transparent' if transparent else 'Opaque'}_{size_name}"
        os.makedirs(output_folder, exist_ok=True)

        supported_exts = ('.png', '.jpg', '.jpeg', '.webp')
        files = [f for f in os.listdir("RawPhotos") if f.lower().endswith(supported_exts)]
        if not files:
            messagebox.showinfo("No Images", "No supported images found in RawPhotos.")
            return

        for idx, file in enumerate(files, 1):
            try:
                with open(os.path.join("RawPhotos", file), 'rb') as i:
                    input_data = i.read()
                    output_data = remove(input_data)

                subject_img = Image.open(BytesIO(output_data)).convert("RGBA")
                bbox = subject_img.getbbox()
                if bbox is None:
                    raise ValueError("No subject detected — image is fully transparent.")
                subject_img = subject_img.crop(bbox)

                if target_size:
                    subject_img = self.resize_and_center(subject_img, target_size, transparent, side_pad_percent, top_pad_percent)

                out_name = os.path.splitext(file)[0] + ".png"
                out_path = os.path.join(output_folder, out_name)

                if transparent:
                    subject_img.save(out_path, format="PNG")
                else:
                    bg_rgb = ImageColor.getrgb(self.bg_color)
                    white_bg = Image.new("RGB", subject_img.size, bg_rgb)
                    if subject_img.mode != "RGBA":
                        subject_img = subject_img.convert("RGBA")
                    try:
                        white_bg.paste(subject_img, mask=subject_img.getchannel("A"))
                    except Exception as e:
                        print(f"Warning: failed to apply alpha mask for {file}: {e}")
                        white_bg.paste(subject_img)
                    white_bg.save(out_path, format="PNG")

            except Exception as e:
                print(f"Error processing {file}: {type(e).__name__}: {e}")

            self.status_label.config(text=f"Processed {idx}/{len(files)}")
            self.root.update_idletasks()

        self.status_label.config(text="Done!")
        messagebox.showinfo("Done", f"Processed {len(files)} image(s).")

    def resize_and_center(self, img, target_size, transparent=True, side_pad_percent=0, top_pad_percent=0):
        pad_x = int(img.width * (side_pad_percent / 100))
        pad_y = int(img.height * (top_pad_percent / 100))

        new_w = img.width + pad_x * 2
        new_h = img.height + pad_y * 2
        expanded = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
        expanded.paste(img, (pad_x, pad_y), mask=img.getchannel("A"))
        img = expanded

        original_ratio = img.width / img.height
        target_w, target_h = target_size

        if original_ratio > target_w / target_h:
            resize_w = target_w
            resize_h = int(target_w / original_ratio)
        else:
            resize_h = target_h
            resize_w = int(target_h * original_ratio)

        img = img.resize((resize_w, resize_h), Image.LANCZOS)

        bg_mode = "RGBA" if transparent else "RGB"
        bg_color = (0, 0, 0, 0) if transparent else ImageColor.getrgb(self.bg_color)
        canvas = Image.new(bg_mode, target_size, bg_color)
        offset = ((target_w - resize_w) // 2, (target_h - resize_h) // 2)

        try:
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            canvas.paste(img, offset, mask=img.getchannel("A"))
        except Exception as e:
            print(f"Paste fallback: {e}")
            canvas.paste(img, offset)

        return canvas

# Run app
if __name__ == "__main__":
    root = tk.Tk()
    app = BGRemoverApp(root)
    root.mainloop()
