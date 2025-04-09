from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from PIL import Image, ImageDraw, ImageFont
import io
import random
import os
import re

app = FastAPI()
templates = Jinja2Templates(directory="templates")

def generate_random_color():
    return (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

def is_valid_hex_color(color: str) -> bool:
    if not color:
        return False
    # Check if the color matches the hex format (#RRGGBB or RRGGBB)
    pattern = r'^#?[0-9A-Fa-f]{6}$'
    return bool(re.match(pattern, color))

def hex_to_rgb(hex_color: str) -> tuple:
    # Remove '#' if present
    hex_color = hex_color.lstrip('#')
    # Convert hex to RGB
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def get_font_size(width: int, height: int) -> int:
    # Calculate base font size (more generous proportion)
    base_size = min(width, height) // 6
    
    # Adjust for very small or very large images
    if min(width, height) < 100:
        base_size = min(width, height) // 4  # Even larger proportion for small images
    elif min(width, height) > 1000:
        base_size = min(width, height) // 8  # Smaller proportion for large images
    
    # Ensure minimum and maximum font sizes
    return max(12, min(base_size, 200))

def draw_outlined_text(draw, position, text, font, text_color='white', outline_color='black'):
    x, y = position
    # Draw outline with thicker border for better visibility
    outline_positions = [
        (x-2, y-2), (x+2, y-2), (x-2, y+2), (x+2, y+2),  # Corners
        (x-2, y), (x+2, y), (x, y-2), (x, y+2),  # Edges
        (x-1, y-1), (x+1, y-1), (x-1, y+1), (x+1, y+1),  # Additional points for thicker outline
    ]
    
    # Draw outline
    for pos_x, pos_y in outline_positions:
        draw.text((pos_x, pos_y), text, font=font, fill=outline_color)
    
    # Draw main text
    draw.text((x, y), text, font=font, fill=text_color)

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/{width}/{height}")
async def generate_image(
    width: int,
    height: int,
    text: str = Query(None, description="Optional text to display above the dimensions"),
    color: str = Query(None, description="Background color in hex format (e.g., #FF0000 or FF0000)")
):
    if width <= 0 or height <= 0:
        raise HTTPException(status_code=400, detail="Width and height must be positive numbers")
    
    if width > 3000 or height > 3000:
        raise HTTPException(status_code=400, detail="Maximum dimension is 3000 pixels")

    # Determine background color
    bg_color = hex_to_rgb(color) if color and is_valid_hex_color(color) else generate_random_color()

    # Create image with background color
    image = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(image)

    # Calculate font size
    font_size = get_font_size(width, height)
    
    # Use default font for better multi-language support
    font = ImageFont.load_default()

    # Prepare dimension text
    dim_text = f"{width} x {height}"
    
    # Calculate text positions
    dim_bbox = draw.textbbox((0, 0), dim_text, font=font)
    dim_text_width = dim_bbox[2] - dim_bbox[0]
    dim_text_height = dim_bbox[3] - dim_bbox[1]
    
    # If custom text is provided, adjust positions
    if text and text.strip():  # Check if text is not empty after stripping whitespace
        # For small images, only show the custom text
        if min(width, height) < 100:
            # Draw only custom text centered
            custom_bbox = draw.textbbox((0, 0), text, font=font)
            custom_text_width = custom_bbox[2] - custom_bbox[0]
            custom_text_height = custom_bbox[3] - custom_bbox[1]
            x = (width - custom_text_width) // 2
            y = (height - custom_text_height) // 2
            draw_outlined_text(draw, (x, y), text, font)
        else:
            # Calculate position for both texts
            custom_bbox = draw.textbbox((0, 0), text, font=font)
            custom_text_height = custom_bbox[3] - custom_bbox[1]
            custom_text_width = custom_bbox[2] - custom_bbox[0]
            
            # Center both texts vertically with some padding
            total_height = custom_text_height + dim_text_height + 10  # 10px padding between texts
            start_y = (height - total_height) // 2
            
            # Draw custom text
            custom_x = (width - custom_text_width) // 2
            draw_outlined_text(draw, (custom_x, start_y), text, font)
            
            # Draw dimension text below
            dim_x = (width - dim_text_width) // 2
            draw_outlined_text(draw, (dim_x, start_y + custom_text_height + 10), dim_text, font)
    else:
        # Draw only dimension text centered
        x = (width - dim_text_width) // 2
        y = (height - dim_text_height) // 2
        draw_outlined_text(draw, (x, y), dim_text, font)

    # Save image to bytes buffer
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)

    return StreamingResponse(img_byte_arr, media_type="image/png")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
