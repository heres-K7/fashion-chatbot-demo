from flask import Flask, render_template, request, jsonify, redirect
from symspellpy import SymSpell, Verbosity
import os
import json
import re


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


#memorise last mentioned text
chat_context = {
    "last_category": None,
    "last_product": None,
    "last_intent": None,
    "last_product_list": []
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

    #regex to return request with under or above
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





def chatbot_reply(user_input):
    user_input = user_input.lower()

    tokens = user_input.split()
    corrected = []
    for word in tokens:
        suggestions = sym_spell.lookup(word, Verbosity.CLOSEST, max_edit_distance=2)
        corrected.append(suggestions[0].term if suggestions else word)
    user_input = " ".join(corrected)
    print("Corrected input:", user_input)  # for debugging, to see the corrected input


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
            return "Hi there! 👋 I'm your Customer Support Chatbot. How can I help you today?"


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
    if any(word in user_input for word in ["support", "customer support", "helpdesk", "contact", "email", "complaint"]):
        return {
            "response": "Customer Support options 👇",
            "buttons": [
                {"label": "Open Support Page", "value": "open support page"},
                {"label": "Email Support", "value": "email support"}
            ]
        }





    if ("hour" in user_input or "hours" in user_input or "time" in user_input) or ("open" in user_input and "store" in user_input):
        return "🕒 Our store is open Monday to Saturday, from 9 AM to 8 PM."

    elif "location" in user_input or "where" in user_input:
        return "📍 Our store is located at B15 2TT Fashion Street, Birmingham."

    elif "delivery" in user_input or "shipping" in user_input:
        return "🚚 We offer free delivery on orders over £50, and standard shipping takes 3–5 business days."

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

@app.route("/support")
def support_page():
    return render_template("support.html")



if __name__ == "__main__":
    app.run(debug=True)

print("DEBUG:", chat_context)


