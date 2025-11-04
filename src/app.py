import os
import json



from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "../templates"),
    static_folder=os.path.join(BASE_DIR, "../static")
)

with open(os.path.join(BASE_DIR, "products.json"), "r") as file:
    products = json.load(file)


#memorise last mentioned text
chat_context = {
    "last_category": None,
    "last_product": None
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



def search_products_by_keyword(keyword):
    keyword = keyword.lower()
    results = []

    for product in products:
        #keyword matches category, colouur, or product name
        if (keyword in product["category"].lower() or
                any(keyword in color.lower() for color in product["colors"]) or
                keyword in product["name"].lower()):
            results.append(product)

    return results



def chatbot_reply(user_input):
    user_input = user_input.lower()

    greetings = ["hi", "hello", "hey", "hya", "good morning", "good afternoon", "good evening"]
    for greet in greetings:
        if user_input.strip() == greet or user_input.startswith(greet + " "):
            return "Hi there! 👋 I'm your Customer Support Chatbot. How can I help you today?"


    if "open" in user_input or "hour" in user_input or "time" in user_input:
        return "🕒 Our store is open Monday to Saturday, from 9 AM to 8 PM."

    if "location" in user_input or "where" in user_input:
        return "📍 Our store is located at B15 2TT Fashion Street, Birmingham."

    if "delivery" in user_input or "shipping" in user_input:
        return "🚚 We offer free delivery on orders over £50, and standard shipping takes 3–5 business days."

    if "return" in user_input or "refund" in user_input:
        return "↩️ You can return any item within 14 days of purchase, as long as it's unworn and in original packaging."

    if "thank" in user_input:
        return "You're welcome! 😊 Let me know if you need help with anything else."

    if "bye" in user_input or "goodbye" in user_input or "see you" in user_input:
        return "Goodbye! 👋 Have a great day."

    if "how are you" in user_input:
        return "I'm just a helpful bot 😄 How can I assist you today?"

    keywords = ["jacket", "hoodie", "t-shirt", "shirt", "shoe", "accessory",
                "sock", "pant", "trouser", "jean", "bottom"]
    for word in keywords:
        if word in user_input:
            found = search_products_by_keyword(word)
            if found:
                #remember context instead of replying indivually
                chat_context["last_category"] = word
                chat_context["last_product"] = None
                response = f"<b>Here are our {word}s:</b><br>"
                for product in found:
                    response += f"• {product['name']} (£{product['price']:.2f})<br>"
                return response
            else:
                return f"Sorry, we don't have any {word}s in stock right now."

    if ("color" in user_input or "colors" in user_input or
            "colour" in user_input or "colours" in user_input):

        #user mentioned a specific product in the same message
        for product in products:
            if product["name"].lower() in user_input:
                chat_context["last_product"] = product["name"]
                return get_product_colors(product["name"])

        #user is asking follow-up after a category
        if chat_context["last_category"]:
            found = search_products_by_keyword(chat_context["last_category"])
            colors = set()
            for product in found:
                for color in product["colors"]:
                    colors.add(color.capitalize())
            color_list = ", ".join(colors)
            return f"Our {chat_context['last_category']}s come in these colors: {color_list}."

        return "Which product would you like to know the colours of?"

    if "size" in user_input or "sizes" in user_input:
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

    if "price" in user_input or "cost" in user_input:
        for product in products:
            if product["name"].lower() in user_input:
                return get_product_price(product["name"])
        return "Which product would you like the price for?"

    if "stock" in user_input or "quantity" in user_input or "available" in user_input:
        for product in products:
            if product["name"].lower() in user_input:
                return get_product_stock(product["name"])
        return "Which product would you like to check stock for?"

    return "I'm sorry, I didn't quite understand that. 🤔 I can help with product details, store hours, or returns. What would you like to know?"


@app.route("/")
def index():
    return render_template("index.html")
@app.route("/get", methods=["POST"])
def get_chatbot_response():
    user_input = request.form["message"]
    response = chatbot_reply(user_input)
    return jsonify({"response": response})


if __name__ == "__main__":
    app.run(debug=True)

print("DEBUG:", chat_context)


'''while True:
    user_input = input("You: ")
    if user_input.lower() == "exit":
        break
    reply = chatbot_reply(user_input)
    print("Bot:", reply)'''


