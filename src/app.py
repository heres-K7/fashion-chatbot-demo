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





def chatbot_reply(user_input):
    user_input = user_input.lower()


    greetings = ["hi", "hello", "hey", "hya", "good morning", "good afternoon", "good evening"]
    if any(greet in user_input for greet in greetings):
        return "Hi there! 👋 I'm your Customer Support Chatbot. How can I help you today?"


    if "open" in user_input or "hour" in user_input or "time" in user_input:
        return "🕒 Our store is open Monday to Saturday, from 9 AM to 8 PM."

    if "location" in user_input or "where" in user_input:
        return "📍 Our store is located at B15 2TT Fashion Street, Birmingham."

    if "delivery" in user_input or "shipping" in user_input:
        return "🚚 We offer free delivery on orders over £50, and standard shipping takes 3–5 business days."

    if "return" in user_input or "refund" in user_input:
        return "↩️ You can return any item within 14 days of purchase, as long as it's the price tag still there and in original packaging quality."

    if "thank" in user_input:
        return "You're welcome! 😊 Let me know if you need help with anything else."

    if "bye" in user_input or "goodbye" in user_input or "see you" in user_input:
        return "Goodbye! 👋 Have a great day."

    if "how are you" in user_input:
        return "I'm just a bunch of code, but I'm feeling helpful today! 😄 How can I assist you?"


    if "price" in user_input:
        # match name of the products, once match the bot replies //look for api. ai free apiin google
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

    elif "colour" in user_input or "colours" in user_input or "color" in user_input or "colors" in user_input:
        for product in products:
            if product["name"].lower() in user_input:
                return get_product_colors(product["name"])
        return "Which product would you like to know the colours of?"

    else:
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



'''while True:
    user_input = input("You: ")
    if user_input.lower() == "exit":
        break
    reply = chatbot_reply(user_input)
    print("Bot:", reply)'''


