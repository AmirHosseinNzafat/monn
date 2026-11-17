from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def main():
    out = Path(__file__).resolve().parents[1] / "assets"
    out.mkdir(parents=True, exist_ok=True)
    size = 256
    image = Image.new("RGBA", (size, size), (9, 13, 24, 255))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((8, 8, 248, 248), radius=54, fill=(17, 31, 52, 255), outline=(65, 215, 232, 255), width=8)
    draw.rounded_rectangle((25, 25, 231, 231), radius=42, outline=(126, 105, 244, 255), width=4)
    # Geometric M mark, drawn as a clean custom monogram.
    draw.line([(55, 192), (55, 65), (128, 143), (201, 65), (201, 192)],
              fill=(83, 225, 235, 255), width=25, joint="curve")
    draw.ellipse((178, 42, 222, 86), fill=(156, 133, 255, 255))
    image.save(out / "monn-studio.png")
    image.save(out / "monn-studio.ico", format="ICO", sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
    print("Created assets/monn-studio.ico")


if __name__ == "__main__":
    main()
