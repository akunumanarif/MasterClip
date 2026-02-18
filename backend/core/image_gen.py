
import requests
from PIL import Image, ImageDraw, ImageFont
import textwrap
import io
import random
import os
from deep_translator import GoogleTranslator

# Local fallback/specific category quotes
ISLAMIC_QUOTES = [
    ("The best of you are those who are best to their families.", "Prophet Muhammad (PBUH)"),
    ("Speak good or remain silent.", "Prophet Muhammad (PBUH)"),
    ("Allah does not burden a soul beyond that it can bear.", "Quran 2:286"),
    ("Indeed, with hardship [will be] ease.", "Quran 94:6"),
    ("Do not lose hope, nor be sad.", "Quran 3:139"),
    ("Trust in Allah, but tie your camel.", "Prophet Muhammad (PBUH)"),
    ("The strong man is not the good wrestler; the strong man is the only one who controls himself when he is angry.", "Prophet Muhammad (PBUH)"),
    ("Richness is not having many belongings, but richness is contentment of the soul.", "Prophet Muhammad (PBUH)")
]

FINANCE_QUOTES = [
    ("Investment in knowledge pays the best interest.", "Benjamin Franklin"),
    ("The rich invest in time, the poor invest in money.", "Warren Buffett"),
    ("Do not save what is left after spending, but spend what is left after saving.", "Warren Buffett"),
    ("A budget is telling your money where to go instead of wondering where it went.", "Dave Ramsey"),
    ("Formal education will make you a living; self-education will make you a fortune.", "Jim Rohn")
]

def fetch_quote(category="life"):
    """Fetches a quote based on category."""
    try:
        if category == "islamic":
            return random.choice(ISLAMIC_QUOTES)
        
        elif category == "finance":
            # Try to get from API first with keyword, fallback to local
            try:
                # ZenQuotes doesn't have a strong 'finance' filter in free tier, use local for consistency or fallback
                # But let's try a random generic one and see, or just use local to be safe for 'finance' specific
                return random.choice(FINANCE_QUOTES)
            except:
                return random.choice(FINANCE_QUOTES)
                
        else: # life / others
            response = requests.get("https://zenquotes.io/api/random")
            if response.status_code == 200:
                data = response.json()[0]
                return data['q'], data['a']
            return "Believe you can and you're halfway there.", "Theodore Roosevelt"

    except Exception as e:
        print(f"Error fetching quote: {e}")
        return "Believe you can and you're halfway there.", "Theodore Roosevelt"

def translate_text(text, target_lang):
    """Translates text to target language."""
    if target_lang == "id":
        try:
            return GoogleTranslator(source='auto', target='id').translate(text)
        except Exception as e:
            print(f"Translation error: {e}")
            return text
    return text

def fetch_image(category="life"):
    """Fetches a random image from Lorem Picsum."""
    try:
        # Request a 1080x1080 image (square for Instagram/social)
        # We can't easily filter Lorem Picsum by category without using the ID, so we keep it random scenic
        response = requests.get("https://picsum.photos/1080/1080")
        if response.status_code == 200:
            return Image.open(io.BytesIO(response.content))
        return Image.new('RGB', (1080, 1080), color = 'gray')
    except Exception as e:
        print(f"Error fetching image: {e}")
        return Image.new('RGB', (1080, 1080), color = 'gray')

def create_quote_image(output_path, category="life", language="en"):
    """Generates a quote image and saves it to output_path."""
    
    # 1. Get Quote
    quote, author = fetch_quote(category)
    
    # 2. Translate if needed
    if language == "id":
        quote = translate_text(quote, "id")
        # Keep author name as is usually, or translate if it's a title (like 'Prophet')
        # Simple heuristic: translate author only if it contains 'Prophet' or 'Quran' to keep format correct?
        # For now, keep author name original as it's a proper noun usually.
        # But 'Quran 2:286' might typically stay same.
    
    # 3. Get Image
    img = fetch_image(category)
    
    # Darken image for better text readability
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 120)) # Slightly darker for better contrast
    img.paste(overlay, (0, 0), overlay)
    
    draw = ImageDraw.Draw(img)
    
    # Load Font - try to use a nice system font or fallback to default
    try:
        # Try a few common sans-serif fonts
        font_path = "arial.ttf" 
        font_size = 55
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        font = ImageFont.load_default()
        font_size = 40 # Adjust for default font
    
    # Wrap text
    wrapper = textwrap.TextWrapper(width=30) 
    wrapped_quote = wrapper.wrap(quote)
    
    # Draw Quote
    current_h = (img.height - (len(wrapped_quote) * font_size * 1.5)) / 2
    
    for line in wrapped_quote:
        # Center text horizontally
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        draw.text(((img.width - text_width) / 2, current_h), line, font=font, fill="white")
        current_h += text_height * 1.5
    
    # Draw Author
    current_h += 30
    author_text = f"- {author}"
    bbox = draw.textbbox((0, 0), author_text, font=font)
    text_width = bbox[2] - bbox[0]
    
    draw.text(((img.width - text_width) / 2, current_h), author_text, font=font, fill="#dddddd")

    img.save(output_path)
    return output_path
