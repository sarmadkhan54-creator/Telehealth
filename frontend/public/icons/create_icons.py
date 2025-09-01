#!/usr/bin/env python3
"""
Simple PWA icon generator for Greenstar Telehealth Platform
Creates basic icons with medical cross symbol
"""

from PIL import Image, ImageDraw, ImageFont
import os

# Color scheme for Greenstar Telehealth
BACKGROUND_COLOR = '#10b981'  # Green theme color
CROSS_COLOR = '#ffffff'       # White cross
BORDER_COLOR = '#059669'      # Darker green border

# Icon sizes needed for PWA
ICON_SIZES = [72, 96, 128, 144, 152, 192, 384, 512]

def create_medical_cross_icon(size):
    """Create a medical cross icon of specified size."""
    # Create image with green background
    img = Image.new('RGBA', (size, size), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(img)
    
    # Add subtle border
    border_width = max(1, size // 64)
    draw.rectangle([0, 0, size-1, size-1], outline=BORDER_COLOR, width=border_width)
    
    # Calculate cross dimensions (30% of icon size)
    cross_thickness = max(size // 8, 4)
    cross_length = size * 0.6
    
    # Center coordinates
    center_x = size // 2
    center_y = size // 2
    
    # Draw vertical bar of cross
    vertical_left = center_x - cross_thickness // 2
    vertical_right = center_x + cross_thickness // 2
    vertical_top = center_y - cross_length // 2
    vertical_bottom = center_y + cross_length // 2
    
    draw.rectangle([vertical_left, vertical_top, vertical_right, vertical_bottom], 
                  fill=CROSS_COLOR)
    
    # Draw horizontal bar of cross
    horizontal_left = center_x - cross_length // 2
    horizontal_right = center_x + cross_length // 2
    horizontal_top = center_y - cross_thickness // 2
    horizontal_bottom = center_y + cross_thickness // 2
    
    draw.rectangle([horizontal_left, horizontal_top, horizontal_right, horizontal_bottom], 
                  fill=CROSS_COLOR)
    
    return img

def main():
    """Generate all required PWA icons."""
    icons_dir = '/app/frontend/public/icons'
    
    print("🏥 Generating Greenstar Telehealth PWA Icons...")
    
    for size in ICON_SIZES:
        icon = create_medical_cross_icon(size)
        filename = f'icon-{size}x{size}.png'
        filepath = os.path.join(icons_dir, filename)
        
        icon.save(filepath, 'PNG')
        print(f"✅ Created {filename} ({size}x{size})")
    
    # Create additional icons for shortcuts
    # Emergency icon (red background)
    emergency_icon = Image.new('RGBA', (192, 192), '#ef4444')
    draw = ImageDraw.Draw(emergency_icon)
    draw.rectangle([0, 0, 191, 191], outline='#dc2626', width=2)
    
    # Emergency cross (white)
    cross_size = 100
    center = 96
    thickness = 16
    
    # Vertical bar
    draw.rectangle([center-thickness//2, center-cross_size//2, 
                   center+thickness//2, center+cross_size//2], fill='white')
    # Horizontal bar  
    draw.rectangle([center-cross_size//2, center-thickness//2, 
                   center+cross_size//2, center+thickness//2], fill='white')
    
    emergency_icon.save(os.path.join(icons_dir, 'emergency-192x192.png'), 'PNG')
    print("✅ Created emergency-192x192.png")
    
    # Call icon (blue background)
    call_icon = Image.new('RGBA', (192, 192), '#3b82f6')
    draw = ImageDraw.Draw(call_icon)
    draw.rectangle([0, 0, 191, 191], outline='#2563eb', width=2)
    
    # Simple phone shape
    draw.ellipse([60, 60, 132, 132], fill='white')
    draw.ellipse([70, 70, 122, 122], fill='#3b82f6')
    
    call_icon.save(os.path.join(icons_dir, 'call-192x192.png'), 'PNG')
    print("✅ Created call-192x192.png")
    
    # Create badge icon (smaller version)
    badge = create_medical_cross_icon(72)
    badge.save(os.path.join(icons_dir, 'badge-72x72.png'), 'PNG')
    print("✅ Created badge-72x72.png")
    
    # Create action icons (simple designs)
    # View action
    view_icon = Image.new('RGBA', (32, 32), '#10b981')
    draw = ImageDraw.Draw(view_icon)
    draw.ellipse([8, 12, 24, 20], fill='white')  # Simple eye shape
    view_icon.save(os.path.join(icons_dir, 'view-action.png'), 'PNG')
    
    # Dismiss action
    dismiss_icon = Image.new('RGBA', (32, 32), '#ef4444')
    draw = ImageDraw.Draw(dismiss_icon)
    draw.line([8, 8, 24, 24], fill='white', width=3)  # X shape
    draw.line([24, 8, 8, 24], fill='white', width=3)
    dismiss_icon.save(os.path.join(icons_dir, 'dismiss-action.png'), 'PNG')
    
    print("✅ Created view-action.png and dismiss-action.png")
    print("🎉 All PWA icons generated successfully!")

if __name__ == '__main__':
    main()