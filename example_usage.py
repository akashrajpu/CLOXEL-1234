"""
Example usage of bg_remover module.
"""

from bg_remover import remove_background, remove_background_batch

# 1. Basic Background Removal (Transparent PNG Output)
print("1. Removing background to transparent PNG...")
# remove_background("input.jpg", "output_transparent.png")

# 2. Background Removal with Custom Solid Background Color (e.g. White / Red / Hex)
print("2. Replacing background with solid White color...")
# remove_background("input.jpg", "output_white.jpg", bg_color="#FFFFFF")

# 3. Pro Mode with Alpha Matting (for hair/fur/fine details)
print("3. Removing background with Alpha Matting for high detail edges...")
# remove_background("input.jpg", "output_pro.png", alpha_matting=True)

# 4. Batch Processing Multiple Images
print("4. Batch processing multiple images...")
# images = ["photo1.jpg", "photo2.jpg", "photo3.jpg"]
# remove_background_batch(images, output_dir="output_folder")

print("✨ Examples ready to use!")
