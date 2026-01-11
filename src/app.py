from flask import Flask, render_template, request, jsonify, redirect
from symspellpy import SymSpell, Verbosity
from textblob import TextBlob
import os
import json
import re
import random



BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "../templates"),
    static_folder=os.path.join(BASE_DIR, "../static")
)


with open(os.path.join(BASE_DIR, "products.json"), "r") as file:
    products = json.load(file)

sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)

import pkg_resources
dictionary_path = pkg_resources.resource_filename(
    "symspellpy", "frequency_dictionary_en_82_765.txt"
)
sym_spell.load_dictionary(dictionary_path, 0, 1)

custom_store_words = [
    "monalisa", "hoodie", "hoodies", "denim", "tshirt", "t-shirt",
    "jacket", "jackets", "sneaker", "sneakers", "trouser", "trousers",
    "jean", "jeans", "puffer", "zipper", "fashion", "accessory",
    "accessories", "store", "sock", "socks", "shoe", "shoes"
]
custom_greetings = [
    "hi", "hello", "hey", "hiya", "hya",
    "good", "morning", "afternoon", "evening",
    "bye", "goodbye", "thanks", "thank", "thankyou"
]
# adding the products to the dictionary
for p in products:
    sym_spell.create_dictionary_entry(p["name"].lower(), 1)
    sym_spell.create_dictionary_entry(p["category"].lower(), 1)

# adding the extra words to dictionary
for w in custom_store_words:
    sym_spell.create_dictionary_entry(w.lower(), 1)
#....................................
for g in custom_greetings:
    sym_spell.create_dictionary_entry(g.lower(), 1)


category_aliases = {
    "jacket": "jacket",
    "jackets": "jacket",
    "hoodie": "hoodie",
    "hoodies": "hoodie",
    "t-shirt": "t-shirt",
    "tshirts": "t-shirt",
    "t shirt": "t-shirt",
    "shirt": "shirt",
    "shirts": "shirt",
    "shoe": "shoe",
    "shoes": "shoe",
    "accessory": "accessory",
    "accessories": "accessory",
    "sock": "sock",
    "socks": "sock",
    "bottom": "bottom",
    "bottoms": "bottom",
    "jean": "jean",
    "jeans": "jean",
    "trouser": "trouser",
    "trousers": "trouser",
    "pant": "pant",
    "pants": "pant"
}


FRUSTRATION_PHRASES = ["not working", "doesn't work", "doesnt work", "broken", "bug", "error", "useless"
                       "waste of time", "annoying", "mad", "angry", "frustrating", "bad", "sad"
                       "terrible", "stupid", "hate", "worst", "ridiculous", "Pissed off", "pissed"
                       ]
FRUSTRATION_EMOJIS = ["😡", "🤬", "😤", "😠", "😞", "💩", "🤦‍♂️"]
NEGATIVE_PUNCTUATION = ["!!!", "!!", "??", "?!", "!?"]


#memorise last mentioned text
chat_context = {
    "last_category": None,
    "last_product": None,
    "last_intent": None,
    "last_product_list": [],
    "mode": None, #outfit mode or not
    "outfit_step": None, #occasion -> waether -> colour -> budget
    "outfit_prefs": { #user's preferences
        "occasion": None,
        "weather": None,
        "colors": [],
        "budget": None,
        "style": None
    },
    "last_outfit": None, #memorise
    "last_outfit_prefs": None,
    "active_product_id": None,
}


#finding the products functions
def get_product_price(name):
    for product in products:
        if name.lower() in product["name"].lower():
            return f"The price of {product['name']} is £{product['price']:.2f}."
    return "Sorry, I couldn't find that product."

def get_product_stock(name):
    for product in products:
        if name.lower() in product["name"].lower():
            return f"We currently have {product['stock']} of {product['name']} in stock."
    return "Sorry, that product is not available."

def get_product_sizes(name):
    for product in products:
        if name.lower() in product["name"].lower():
            sizes = ", ".join(product["sizes"])
            return f"{product['name']} is available in the following sizes: {sizes}."
    return "Sorry, we don't have that product."

def get_product_colors(name):
    for product in products:
        if name.lower() in product["name"].lower():
            colors = ", ".join(product["colors"])
            return f"{product['name']} comes in the following colors: {colors}."
    return "Sorry, that product is not available."


#search the products by keywords for single product and a whole catogory to list all for the user
def search_products_by_keyword(keyword):
    keyword = keyword.lower()
    results = []

    plural_forms = set()
    if keyword.endswith("y"):
        plural_forms.add(keyword[:-1] + "ies")
    else:
        plural_forms.add(keyword + "s")
    plural_forms.add(keyword)

    for product in products:
        product_category = product["category"].lower()
        product_name = product["name"].lower()
        product_colors = [color.lower() for color in product["colors"]]

        if any(
                form in product_category
                or any(form in color for color in product_colors)
                or form in product_name
                for form in plural_forms
        ):
            results.append(product)

    return results


def pluralize(word):

    word = word.lower()
    if word.endswith("y"):
        return word[:-1] + "ies"
    elif word.endswith("s"):
        return word
    else:
        return word + "s"



def _all_known_colors(products_list):
    colors = set()
    for p in products_list:
        for c in p.get("colors", []):
            colors.add(c.lower())

    colors.update({"grey", "gray", "navy", "off white", "off-white", "white", "black", "blue", "red", "green", "brown", "beige"})
    return colors #get colours so when user request item with a specific colour bot list it

KNOWN_COLORS = _all_known_colors(products) # storing place

def parse_product_query(user_input: str): #take the information from sentence and return them to the return structure

    text = user_input.lower()

    category = None
    for user_word, base_category in category_aliases.items():
        if user_word in text:
            category = base_category
            break

    #size
    size = None
    m = re.search(r"\b(xx?s|xs|s|m|l|xl|xxl)\b", text)
    if m:
        size = m.group(1).upper()

    #price: under/below/less than + number, or over/above/more than + number
    max_price = None
    min_price = None

    '''#capture values
    def _extract_number(s):
        s = s.replace("£", "").strip()
        try:
            return float(s)
        except:
            return None'''

    #regex to search and return request with under or above
    under = re.search(r"\b(under|below|less than)\b\s*(?:£\s*)?([0-9]+(?:\.[0-9]{1,2})?)", text)
    if under:
        max_price = float(under.group(2))

    over = re.search(r"\b(over|above|more than)\b\s*(?:£\s*)?([0-9]+(?:\.[0-9]{1,2})?)", text)
    if over:
        min_price = float(over.group(2))


    color = None
    #handle "off white" and "off-white" as special case
    if "off white" in text or "off-white" in text:
        color = "off white"
    else:
        for c in KNOWN_COLORS:
            if re.search(rf"\b{re.escape(c)}\b", text):
                color = c
                break

    return {
        "category": category,
        "color": color.strip() if isinstance(color, str) else None,
        "size": size,
        "max_price": max_price,
        "min_price": min_price
    }

def filter_products(filters: dict): #check matches
    results = []

    for p in products:
        #category
        if filters["category"]:
            if filters["category"] not in p["category"].lower():
                continue

        #color
        if filters["color"]:
            product_colors = [c.lower() for c in p.get("colors", [])]
            wanted = filters["color"].strip().replace("-", " ")

            #products with no colour still shown
            if product_colors:
                if not any(wanted in pc.replace("-", " ") for pc in product_colors):
                    continue


        if filters["size"]:
            sizes = [s.upper() for s in p.get("sizes", [])]
            if filters["size"] not in sizes:
                continue

        price = float(p.get("price", 0))
        if filters["max_price"] is not None and price > filters["max_price"]:
            continue
        if filters["min_price"] is not None and price < filters["min_price"]:
            continue

        results.append(p)

    return results

def format_product_list(items, title="Here’s what I found:"):
    if not items:
        return "Sorry, I couldn’t find anything matching that. Try a different colour/size/price or category."

    msg = f"<b>{title}</b><br>"
    for p in items:
        msg += f"• {p['name']} (£{p['price']:.2f})<br>"
    return msg




def extract_possible_product_keyword(user_input: str):
    text = user_input.lower()

    noise = {
        "show", "me", "all", "everything", "do", "you", "have", "got",
        "any", "a", "an", "the", "in", "under", "below", "less", "than",
        "over", "above", "more", "price", "cost", "size", "sizes",
        "color", "colour", "colors", "colours", "stock", "available",
        "availability", "please", "can", "could", "tell"
    }

    words = [w for w in re.findall(r"[a-zA-Z\-]+", text) if w not in noise]
    return words[0] if words else None





def detect_frustration(text: str) -> bool:
    t = text.lower().strip()

    if any(p in t for p in FRUSTRATION_PHRASES):
        return True
    if any(p in text for p in NEGATIVE_PUNCTUATION):
        return True
    if any(e in text for e in FRUSTRATION_EMOJIS):
        return True

    blob = TextBlob(text)
    polarity = blob.sentiment.polarity

    if polarity < -0.4: #negetive feeling
        return True
    print("DEBUG frustration check:", text, "polarity:", TextBlob(text).sentiment.polarity)

    return False





def _cat(p):
    return p["category"].lower() #get product by category type

TOP_CATS = ["t-shirt", "t-shirts", "shirt", "hoodie", "jacket"]
BOTTOM_CATS = ["trouser", "trousers", "jean", "jeans", "jogger", "joggers", "pant", "pants", "bottom", "bottoms"]
SHOE_CATS = ["shoe", "shoes"]
ACC_CATS = ["accessory", "accessories"]
SOCK_CATS = ["sock", "socks"]


def pick_one(items, prefs, avoid_names=None): #filter by rules
    avoid_names = set(avoid_names or [])

    items = [p for p in items if p.get("stock", 0) > 0] or items #prefer in stock items

    if prefs.get("colors"):
        wanted = {c.lower() for c in prefs["colors"]}
        colored = [p for p in items if any(c.lower() in wanted for c in p.get("colors", []))]
        if colored:
            items = colored

    if prefs.get("budget") is not None:
        under = [p for p in items if float(p.get("price", 0)) <= prefs["budget"]]
        if under:
            items = under

    non_repeat = [p for p in items if p["name"] not in avoid_names] #avoid repeat in the build of the outfit
    if non_repeat:
        items = non_repeat

    if not items:
        return None

    items_sorted = sorted(items, key=lambda p: float(p.get("price", 0))) #pick randomly from top few cheapest (gives variety but stays sensible)
    top_k = items_sorted[:min(4, len(items_sorted))]
    return random.choice(top_k)


def cat_key(cat: str) -> str:
    """
    making category to easy and clear key:
    'T-Shirts' --> 'tshirts'
    'Jackets'  --> 'jackets'
    'Accessories' --> 'accessories'
    """
    return re.sub(r"[^a-z]", "", (cat or "").lower())

def build_outfit(prefs):
    occasion = prefs.get("occasion")
    weather = prefs.get("weather")

    def is_cat(p, *keys):
        return cat_key(p.get("category", "")) in set(keys)

    tops_all = [p for p in products if is_cat(p, "tshirt", "hoodie", "shirt", "jacket")] #go thro all product then group them
    bottoms_all = [p for p in products if is_cat(p, "bottoms")]
    shoes_all = [p for p in products if is_cat(p, "shoes")]
    accs_all = [p for p in products if is_cat(p, "accessories")]

    tops = tops_all[:]
    bottoms = bottoms_all[:]
    shoes = shoes_all[:]
    accs = accs_all[:]


    if occasion == "work":
        work_tops = [p for p in tops if is_cat(p, "shirt", "jacket")]
        if work_tops:
            tops = work_tops

        suit_like = [p for p in tops if "suit" in p["name"].lower()]
        if suit_like:
            tops = suit_like

        formal_bottoms = [p for p in bottoms if any(w in p["name"].lower() for w in ["trouser", "formal", "slim", "chino"])]
        if formal_bottoms:
            bottoms = formal_bottoms

        formal_shoes = [p for p in shoes if any(w in p["name"].lower() for w in ["leather", "boot", "oxford", "loafer", "formal"])]
        if formal_shoes:
            shoes = formal_shoes


    if weather == "cold":
        warm = [p for p in tops if is_cat(p, "hoodie", "jacket")]
        if warm:
            tops = warm
    elif weather == "hot":
        light = [p for p in tops if is_cat(p, "tshirt", "shirt")]
        if light:
            tops = light
    elif weather == "rainy":
        rain = [p for p in tops if is_cat(p, "jacket")]
        if rain:
            tops = rain

    #avoid repeat
    avoid = set()
    last = chat_context.get("last_outfit")
    if last:
        for k in ["top", "bottom", "shoes", "accessory"]:
            if last.get(k):
                avoid.add(last[k]["name"])


    top_pick = pick_one(tops, prefs, avoid)
    bottom_pick = pick_one(bottoms, prefs, avoid)
    shoes_pick = pick_one(shoes, prefs, avoid)

    accessory_pick = None
    if occasion in ["party", "work"]:
        if occasion == "work":
            tie_like = [p for p in accs if "tie" in p["name"].lower()]

            if tie_like:
                accessory_pick = pick_one(tie_like, prefs, avoid)
            else:
                accessory_pick = pick_one(accs, prefs, avoid)
        else:
            accessory_pick = pick_one(accs, prefs, avoid)

    return {
        "top": top_pick,
        "bottom": bottom_pick,
        "shoes": shoes_pick,
        "accessory": accessory_pick
    }

def outfit_item_html(label, product):
    if not product:
        return ""

    img_html = ""
    if product.get("image"):
        img_html = f"<img class='outfit-img' src='/static/product_images/{product['image']}' alt='{product['name']}'>"

    dots = ""
    if product.get("colors"):
        dots = "<div class='color-dots'>" + "".join(
            f"<span class='color-dot {c}'></span>" for c in product["colors"]
        ) + "</div>"

    return f"""
    <a class="outfit-item" href="/product/{product['id']}">
        {img_html}
        <div class="outfit-text">
            <b>{label}</b><br>
            {product['name']}<br>
            £{float(product['price']):.2f}
            {dots}
        </div>
    </a>
    """



def format_outfit(outfit, prefs):
    if not outfit["top"] or not outfit["bottom"] or not outfit["shoes"]:
        return "I couldn’t build a full outfit from the current stock 😅 Try a different occasion or budget."

    total = 0.0
    for key in ["top", "bottom", "shoes", "accessory"]:
        item = outfit.get(key)
        if item:
            total += float(item["price"])

    parts_html = ""
    parts_html += outfit_item_html("Top", outfit.get("top"))
    parts_html += outfit_item_html("Bottom", outfit.get("bottom"))
    parts_html += outfit_item_html("Shoes", outfit.get("shoes"))
    if outfit.get("accessory"):
        parts_html += outfit_item_html("Accessory", outfit.get("accessory"))

    why = []
    if prefs.get("occasion"):
        why.append(f"Occasion: <b>{prefs['occasion']}</b> — picked items that fit that vibe.")
    if prefs.get("weather"):
        why.append(f"Weather: <b>{prefs['weather']}</b> — chose pieces that suit the conditions.")
    if prefs.get("colors"):
        why.append(f"Colours: <b>{', '.join(prefs['colors'])}</b> — prioritised items in your colours.")
    if prefs.get("budget") is not None:
        why.append(f"Budget: <b>£{prefs['budget']:.0f}</b> — tried to stay within it where possible.")

    response = "<b>Your Outfit:</b><br>"
    response += f"<div class='outfit-preview'>{parts_html}</div>"
    response += f"<br><b>Total:</b> £{total:.2f}"
    response += "<br><br><b>Why this outfit?</b><br>" + "<br>".join("• " + x for x in why)
    response += "<br><br>Want it more <b>minimal</b>, <b>bold</b>, or <b>trendy</b>?"
    return response



def chatbot_reply(user_input):
    user_input = user_input.lower()

    tokens = user_input.split()
    corrected = []
    for word in tokens:
        suggestions = sym_spell.lookup(word, Verbosity.CLOSEST, max_edit_distance=2)
        corrected.append(suggestions[0].term if suggestions else word)
    user_input = " ".join(corrected)
    print("Corrected input:", user_input)  # for debugging, to see the corrected input


    if user_input.strip() in ["try another outfit", "another outfit", "new outfit", "regen outfit"]:
        prefs = chat_context.get("last_outfit_prefs")
        if not prefs:
            return "I don’t have your last outfit preferences yet 😅 Type: build me an outfit"

        outfit = build_outfit(prefs)
        chat_context["last_outfit"] = outfit

        html = format_outfit(outfit, prefs)
        return {
            "response": html,
            "buttons": [
                {"label": "Try another outfit", "value": "try another outfit"},
                {"label": "Start new outfit", "value": "build me an outfit"}
            ]
        }



    if user_input.strip() == "/support":
        return {
            "response": (
                "Here’s how you can get help 👇<br>"
                "📧 Email: <a href='mailto:kxa284@student.bham.ac.uk'>kxa284@student.bham.ac.uk</a><br>"
                "🧾 Or visit: <a href='/support' target='_blank'>Customer Support Page</a>"
            )
        }



    greetings = ["hi", "hello", "hey", "hya", "good morning", "good afternoon", "good evening"]

    for greet in greetings:
        if user_input.strip() == greet or user_input.startswith(greet + " "):
            chat_context["last_intent"] = None
            return "Hi there! 👋 I'm your Customer Support Chatbot. How can I help you today? you can ask me to build an outfit, FAQs or whatever you want me to show you. 😊"



    #askin bot about a product
    active_id = chat_context.get("active_product_id")
    active_product = next((p for p in products if p["id"] == active_id), None) if active_id else None

    if active_product and user_input.strip() in ["help", "menu", "product help", "about this"]:
        return {
            "response": f"Sure! Ask me about <b>{active_product['name']}</b> 👇",
            "buttons": [
                {"label": "Fit & sizing", "value": "fit"},
                {"label": "Material & comfort", "value": "material"},
                {"label": "Care instructions", "value": "care"},
                {"label": "What to wear with it", "value": "style"},
                {"label": "Availability (sizes/colours)", "value": "availability"},
            ]
        }

    if active_product:
        # 1) sizing
        if any(k in user_input for k in ["fit", "oversized", "slim", "regular", "size", "sizing"]):
            fit = active_product.get("fit")
            if fit:
                return (
                    f"<b>{active_product['name']}</b> fit: <b>{fit}</b>. "
                    f"Available sizes: {', '.join(active_product.get('sizes', []))}."
                )
            return (
                f"I don’t have fit info stored for <b>{active_product['name']}</b> yet. "
                f"Sizes available: {', '.join(active_product.get('sizes', []))}."
            )

        # 2)Material
        if any(k in user_input for k in ["material", "fabric", "cotton", "wool", "polyester", "comfortable", "comfort"]):
            material = active_product.get("material")
            if material:
                return f"<b>{active_product['name']}</b> material: <b>{material}</b>."
            return f"I don’t have material info stored for <b>{active_product['name']}</b> yet."

        # 3)Care instructions
        if any(k in user_input for k in ["care", "wash", "washing", "machine wash", "dry", "shrink", "iron"]):
            care = active_product.get("care")
            if care:
                return f"<b>Care for {active_product['name']}:</b><br>{care}"
            return f"I don’t have care instructions stored for <b>{active_product['name']}</b> yet."

        # 4) Wwear with
        if any(k in user_input for k in ["wear with", "style", "outfit", "match", "goes with"]):
            tips = active_product.get("style_tips")
            if tips:
                return (
                        f"<b>Styling ideas for {active_product['name']}:</b><br>"
                        + "<br>".join(f"• {t}" for t in tips)
                )
            return f"For <b>{active_product['name']}</b>, a safe match is neutral bottoms (black/blue) + simple shoes."

        # 5) Availability
        if any(k in user_input for k in ["available", "availability", "stock", "colors", "colour", "sizes"]):
            colors = ", ".join(active_product.get("colors", []))
            sizes = ", ".join(active_product.get("sizes", []))
            stock = active_product.get("stock")
            return (
                f"<b>{active_product['name']}</b><br>"
                f"Stock: {stock}<br>"
                f"Colours: {colors}<br>"
                f"Sizes: {sizes}"
            )



    raw_input = user_input.strip()

    quick_actions = {
        "/support": {"response": (
            "Here’s how you can get help 👇<br>"
            "📧 Email: <a href='mailto:kxa284@student.bham.ac.uk'>kxa284@student.bham.ac.uk</a><br>"
            "🧾 Or visit: <a href='/support' target='_blank'>Customer Support Page</a>"
        )},
        "open support page": {"response": "Opening support page: <a href='/support' target='_blank'>Customer Support</a>"},
        "email support": {"response": "Email us here: <a href='mailto:kxa284@student.bham.ac.uk'>kxa284@student.bham.ac.uk</a>"},
    }

    if raw_input in quick_actions:
        return quick_actions[raw_input]



    if user_input.strip() in ["help", "menu", "/help"]:
        return {
            "response": "Here are some quick options 👇",
            "buttons": [
                {"label": "T-Shirts", "value": "show me t-shirts"},
                {"label": "Hoodies", "value": "show me hoodies"},
                {"label": "Jackets", "value": "show me jackets"},
                {"label": "Shoes", "value": "show me shoes"},
                {"label": "Delivery", "value": "delivery"},
                {"label": "Returns", "value": "return policy"},
                {"label": "Customer Support", "value": "support"}
            ]
        }


    #handling support, etc. messages
    if any(word in user_input for word in ["support", "customer support", "helpdesk", "contact", "email", "complaint", "complain", "human"]):
        return {
            "response": "Customer Support options 👇: you can raise your complaint, report a technical issue via support team's email. Stay rested, and the team will sort out your raise.😊",
            "buttons": [
                {"label": "Open Support Page", "value": "open support page"},
                {"label": "Email Support", "value": "email support"}
            ]
        }



    if chat_context.get("mode") != "outfit" and detect_frustration(user_input): #disable detect_frustration while building an outfit #feeling detection
        chat_context["last_intent"] = None
        return {
            "response": (
                "Sorry about that 😅 I can see this is frustrating. "
                "Let’s try one of these options:"
            ),
            "buttons": [
                {"label": "Help Menu", "value": "help"},
                {"label": "Delivery Info", "value": "delivery"},
                {"label": "Return Policy", "value": "return policy"},
                {"label": "Customer Support", "value": "support"}
            ]
        }



    #after building and outfit, if user wants adjustments, rebuild with style preference
    if chat_context.get("last_outfit") and any(s in user_input for s in ["minimal", "bold", "trendy"]):
        prefs = chat_context.get("outfit_prefs", {})
        if "minimal" in user_input: prefs["style"] = "minimal"
        elif "bold" in user_input: prefs["style"] = "bold"
        else: prefs["style"] = "trendy"

        outfit = build_outfit(prefs)
        chat_context["last_outfit"] = outfit
        return format_outfit(outfit, prefs)



    if any(x in user_input for x in ["outfit", "build an outfit", "outfit builder", "outfit idea", "pick an outfit", "make an outfit", "create an outfit"]):
        chat_context["mode"] = "outfit"
        chat_context["outfit_step"] = "occasion"
        chat_context["outfit_prefs"] = {
            "occasion": None,
            "weather": None,
            "colors": [],
            "budget": None,
            "style": None
        }

        chat_context["last_outfit"] = None

        return "Sure 😄 What’s the occasion? (casual / work / party)"



    if chat_context.get("mode") == "outfit":
        step = chat_context.get("outfit_step")
        prefs = chat_context.get("outfit_prefs", {})

        if step == "occasion":
            if any(o in user_input for o in ["casual", "work", "party"]):
                if "work" in user_input: prefs["occasion"] = "work"
                elif "party" in user_input: prefs["occasion"] = "party"
                else: prefs["occasion"] = "casual"

                chat_context["outfit_prefs"] = prefs
                chat_context["outfit_step"] = "weather"
                return "Nice. What’s the weather like? (cold / mild / hot / rainy)"
            return "Pick one please: casual / work / party"



        if step == "weather":
            if any(w in user_input for w in ["cold", "mild", "hot", "rain", "rainy"]):
                if "cold" in user_input: prefs["weather"] = "cold"
                elif "hot" in user_input: prefs["weather"] = "hot"
                elif "rain" in user_input: prefs["weather"] = "rainy"
                else: prefs["weather"] = "mild"

                chat_context["outfit_prefs"] = prefs
                chat_context["outfit_step"] = "colors"
                return "Any preferred colours? (e.g., black, navy, white) or say 'no'"
            return "Choose: cold / mild / hot / rainy"


        if step == "colors":
            if "no" in user_input or "any" in user_input:
                prefs["colors"] = []
            else:
                found = [c for c in KNOWN_COLORS if c in user_input]
                prefs["colors"] = found[:3]

            chat_context["outfit_prefs"] = prefs
            chat_context["outfit_step"] = "budget"
            return "What’s your budget in £? (e.g., 80) or say 'no'"

        if step == "budget":
            if "no" in user_input or "any" in user_input:
                prefs["budget"] = None
            else:
                m = re.search(r"(\d+(\.\d+)?)", user_input)
                prefs["budget"] = float(m.group(1)) if m else None
            chat_context["outfit_prefs"] = prefs

            print("DEBUG OUTFIT PREFS:", chat_context["outfit_prefs"])

            outfit = build_outfit(prefs)
            chat_context["last_outfit"] = outfit
            chat_context["last_outfit_prefs"] = prefs.copy()
            chat_context["mode"] = None
            chat_context["outfit_step"] = None


            html = format_outfit(outfit, prefs)
            return {
                "response": html,
                "buttons": [
                    {"label": "Try another outfit", "value": "try another outfit"},
                    {"label": "Start new outfit", "value": "build me an outfit"}
                ]
            }

    if ("hour" in user_input or "hours" in user_input or "time" in user_input) or ("open" in user_input and "store" in user_input):
        return "🕒 Our store is open Monday to Saturday, from 9 AM to 8 PM."

    elif "location" in user_input or "where" in user_input:
        return "📍 Our store is located at B15 2TT Fashion Street, Birmingham."

    elif "delivery" in user_input or "shipping" in user_input:
        return "🚚 We offer free delivery on orders over £50, £4.99 delivery fees apply if less. Standard shipping takes 3–5 business days."

    elif "return" in user_input or "refund" in user_input:
        return "↩️ You can return any item within 14 days of purchase, as long as it's unworn and in original packaging."

    elif "thank" in user_input:
        chat_context["last_intent"] = None
        return "You're welcome! 😊 Let me know if you need help with anything else."

    elif "bye" in user_input or "goodbye" in user_input or "see you" in user_input:
        chat_context["last_intent"] = None
        return "Goodbye! 👋 Have a great day."

    elif "how are you" in user_input:
        chat_context["last_intent"] = None
        return "I'm just a helpful bot 😄 How can I assist you today?"


    filters = parse_product_query(user_input) #detect when to search based on user's asking
    print("DEBUG filters:", filters)

    product_keywords = [
        "show", "find", "do you have", "have you got",
        "looking for", "need", "want", "buy", "available"
    ]

    asked_for_products = (
            any(k in user_input for k in product_keywords)
            or filters["category"]
            or filters["color"]
            or filters["size"]
            or filters["max_price"] is not None
            or filters["min_price"] is not None
    )




    if asked_for_products:

        all_phrases = ["show me all", "all products", "everything", "show everything", "show me everything"]
        if any(p in user_input for p in all_phrases):
            return "You’ll probably find it easier to browse everything in the Store page (with pictures 😅). Try /store or click Store in the navbar!"

        matched = filter_products(filters)
        print("DEBUG matched names:", [p["name"] for p in matched])

        possible_kw = extract_possible_product_keyword(user_input)

        no_filters = (
            not filters["category"]
            and not filters["color"]
            and not filters["size"]
            and filters["max_price"] is None
            and filters["min_price"] is None
        )

        if no_filters and possible_kw and len(matched) == len(products):
            kw_exists = any(
                possible_kw in p["name"].lower()
                or possible_kw in p["category"].lower()
                for p in products
            )
            if not kw_exists:
                return (
                    f"Sorry, we don’t sell '{possible_kw}' here. "
                    "I can help with clothes like t-shirts, hoodies, jackets, shoes, "
                    "trousers, socks, and accessories.😊"
                )

        if filters["category"]:
            chat_context["last_category"] = filters["category"]
            chat_context["last_product"] = None
            chat_context["last_product_list"] = [p["name"] for p in matched]

        if filters["max_price"] is not None and not filters["category"]:
            title = f"Products under £{filters['max_price']:.0f}:"
        elif filters["category"]:
            title = f"Here are our {filters['category']}s:"
        else:
            title = "Here’s what I found:"

        return format_product_list(matched, title=title)


    elif ("color" in user_input or "colors" in user_input or
          "colour" in user_input or "colours" in user_input):
        if chat_context["last_product"]:
            return get_product_colors(chat_context["last_product"])

        for product in products:
            if product["name"].lower() in user_input:
                chat_context["last_product"] = product["name"]
                return get_product_colors(product["name"])

        if chat_context["last_category"]:
            found = search_products_by_keyword(chat_context["last_category"])
            colors = set()
            for product in found:
                for color in product["colors"]:
                    colors.add(color.capitalize())
            color_list = ", ".join(colors)
            return f"Our {chat_context['last_category']}s come in these colors: {color_list}."

        return "Which product would you like to know the colours of?"

    elif "size" in user_input or "sizes" in user_input:
        if chat_context["last_product"]:
            return get_product_sizes(chat_context["last_product"])

        for product in products:
            if product["name"].lower() in user_input:
                chat_context["last_product"] = product["name"]
                return get_product_sizes(product["name"])

        if chat_context["last_category"]:
            found = search_products_by_keyword(chat_context["last_category"])
            sizes = set()
            for product in found:
                for size in product["sizes"]:
                    sizes.add(size.upper())
            size_list = ", ".join(sorted(sizes))
            return f"Our {chat_context['last_category']}s are available in these sizes: {size_list}."

        return "Which product would you like to know the sizes of?"

    elif "price" in user_input or "cost" in user_input:
        chat_context["last_intent"] = "price"
        if chat_context["last_product"]:
            return get_product_price(chat_context["last_product"])
        cleaned_input = user_input.replace(" ", "").lower()
        for product in products:
            product_name_no_spaces = product["name"].lower().replace(" ", "")    #if some say monalisa instead of mona lisa
            product_name_words = product["name"].lower().split()

            if (product_name_no_spaces in cleaned_input or
                any(word in cleaned_input for word in product_name_words)):
                chat_context["last_product"] = product["name"]
                return get_product_price(product["name"])

        if chat_context["last_product"]:
            return get_product_price(chat_context["last_product"])

        if chat_context["last_category"]:
            return f"Which {chat_context['last_category']} would you like to know its price?"

        return "Which product would you like the price for?"

    elif "stock" in user_input or "quantity" in user_input or "available" in user_input or "availability" in user_input:
        if chat_context["last_product"]:
            return get_product_stock(chat_context["last_product"])

        for product in products:
            if product["name"].lower() in user_input:
                chat_context["last_product"] = product["name"]
                return get_product_stock(product["name"])
        if chat_context["last_category"]:
            return f"Would you like me to check stock for our {chat_context['last_category']}s?"
        else:
            return "Could you tell me which product you'd like me to check stock for?"



    elif any(
        product["name"].lower().replace(" ", "") in user_input.replace(" ", "") or
        user_input.replace(" ", "") in product["name"].lower().replace(" ", "") or
        product["name"].lower() in user_input
        for product in products
    ):


        for product in products:
            product_name_no_spaces = product["name"].lower().replace(" ", "")
            user_no_spaces = user_input.replace(" ", "")

            if (
                product_name_no_spaces in user_no_spaces or
                user_no_spaces in product_name_no_spaces or
                product["name"].lower() in user_input
            ):
                chat_context["last_product"] = product["name"]

                if "last_intent" in chat_context and chat_context["last_intent"] == "price":
                    return get_product_price(product["name"])



                return f"You mentioned {product['name']}. Would you like to know its price, stock, sizes or colours?"


    elif any(word in user_input for word in category_aliases):
        for user_word, base_category in category_aliases.items():
            if user_word in user_input:
                found = search_products_by_keyword(base_category)
                if found:
                    chat_context["last_category"] = base_category
                    chat_context["last_product"] = None
                    chat_context["last_product_list"] = [p["name"] for p in found]

                    display_name = pluralize(base_category)
                    response = f"<b>Here are our {display_name}:</b><br>"

                    for product in found:
                        response += f"• {product['name']} (£{product['price']:.2f})<br>"
                    chat_context["last_intent"] = None
                    return response
                else:
                    plural_name = pluralize(base_category)
                    return f"Sorry, we don't have any {plural_name} in stock right now."

    elif (
            "one" in user_input or
            "that" in user_input or
            any(adj in user_input for adj in [
                "black", "plain", "blue", "red", "white", "green", "orange",
                "purple", "pink", "brown", "gray", "mona", "monalisa"
            ])
    ):
        if chat_context["last_product_list"]:
            user_words = [w.lower() for w in user_input.split() if w.isalpha() or w.isalnum()] #split maeningful words
            possible_matches = []

            for product_name in chat_context["last_product_list"]:
                product_clean = product_name.lower().replace(" ", "")

                for word in user_words:
                    if word in product_clean or word in product_name.lower():
                        possible_matches.append(product_name)
                        break #stop after match

            if possible_matches:
                chosen_product = possible_matches[0]
                chat_context["last_product"] = chosen_product

                #respond directly if word found
                if any(k in user_input for k in ["price", "cost"]):
                    return get_product_price(chosen_product)
                if any(k in user_input for k in ["stock", "quantity", "available"]):
                    return get_product_stock(chosen_product)
                if any(k in user_input for k in ["size", "sizes"]):
                    return get_product_sizes(chosen_product)
                if any(k in user_input for k in ["color", "colour", "colors", "colours"]):
                    return get_product_colors(chosen_product)

                return f"Are you referring to the {chosen_product}? Would you like to know its price, stock, or colours?"

        return "Could you tell me which product you’re referring to?"



    else:
        return "I'm sorry, I didn't quite understand that. 🤔 I can help with product details, store hours, or returns. What would you like to know?"


def get_product_image_path(product_name):

    base = product_name.lower().replace(" ", "-")

    image_dir = os.path.join(app.static_folder, "product_images")

    for ext in [".jpg", ".jpeg", ".png"]:
        filename = base + ext
        full_path = os.path.join(image_dir, filename)
        if os.path.exists(full_path):

            return f"product_images/{filename}"

    return "product_images/placeholder.png"

@app.context_processor
def utility_processor():
    return dict(product_image=get_product_image_path)


@app.route("/")
def home():
    return redirect("/store")

@app.route("/chat")
def chat_page():
    return render_template("index.html")

@app.route("/get", methods=["POST"])
def get_chatbot_response():
    user_input = request.form["message"]
    response = chatbot_reply(user_input)

    if isinstance(response, dict):
        return jsonify(response)

    return jsonify({"response": response})

@app.route("/store")
def store_home():
    categories = sorted(list(set([p["category"] for p in products])))
    return render_template("store_home.html", categories=categories)

@app.route("/category/<category>")
def category_page(category):
    selected = [p for p in products if p["category"].lower() == category.lower()]
    return render_template("category_page.html", category=category, products=selected)

@app.route("/product/<int:product_id>")
def product_page(product_id):
    product = next((p for p in products if p["id"] == product_id), None)
    if not product:
        return "Product not found", 404
    return render_template("product_page.html", product=product)

@app.route("/support")
def support_page():
    return render_template("support.html")

@app.route("/chat/<int:product_id>")
def chat_about_product(product_id):
    product = next((p for p in products if p["id"] == product_id), None)
    if not product:
        return "Product not found", 404

    chat_context["active_product_id"] = product_id
    chat_context["last_product"] = product["name"]
    return render_template("index.html", auto_open_menu=True, active_product_name=product["name"])



if __name__ == "__main__":
    app.run()

print("DEBUG:", chat_context)