import json

#to load product from json
with open("products.json", "r") as file:
    products = json.load(file)

    for product in products:
        print(product["name"])


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




def chatbot_reply(user_input):
    user_input = user_input.lower()

    if "price" in user_input:
        # match name of the products
        for product in products:
            if product["name"].lower() in user_input:
                return get_product_price(product["name"])
        return "Which product would you like the price for?"

    elif "stock" in user_input or "quantity" in user_input:
        for product in products:
            if product["name"].lower() in user_input:
                return get_product_stock(product["name"])
        return "Which product would you like to check stock for?"

    elif "size" in user_input or "sizes" in user_input:
        for product in products:
            if product["name"].lower() in user_input:
                return get_product_sizes(product["name"])
        return "Which product would you like the sizes for?"

    elif "color" in user_input or "colors" in user_input:
        for product in products:
            if product["name"].lower() in user_input:
                return get_product_colors(product["name"])
        return "Which product would you like to know the colors of?"

    else:
        return "Sorry, I can help with price, stock, sizes, and colors. Please ask about one of those."



while True:
    user_input = input("You: ")
    if user_input.lower() == "exit":
        break
    reply = chatbot_reply(user_input)
    print("Bot:", reply)


