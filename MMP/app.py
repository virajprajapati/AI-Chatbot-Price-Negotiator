from flask import Flask, render_template, request
from transformers import pipeline
from pymongo import MongoClient
import re

app = Flask(__name__)


# Your existing chatbot code here...
try:
    client = MongoClient('mongodb+srv://vaghelajigneshcan0205:123Durham@cluster0.liiiog9.mongodb.net/')
    db = client['ProductDB']
    products_collection = db['Products']
    print("MongoDB connection successful.")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")

# NLP pipeline
nlp = pipeline("zero-shot-classification")

import re

def process_user_input(user_input, current_product=None, negotiation_state=None):
    # NLP processing
    result = nlp(user_input, ["greeting", "product_inquiry", "negotiate"])
    predicted_intent = result["labels"][0]

    # Handle different intents
    if predicted_intent == "greeting":
        return "Hello! How can I help you?", current_product, negotiation_state
    elif predicted_intent == "product_inquiry":
        # Extract product name from the input
        product_name = user_input.split(" ")[-1]

        if product_name:
            product_info = products_collection.find_one({"Product Name": {"$regex": f".*{product_name}.*", "$options": "i"}})
            if product_info:
                # If in negotiation state, continue negotiation
                if negotiation_state == "negotiate":
                    return negotiate_price(user_input, current_product)
                else:
                    # Ask if the user wants to buy the product
                    about_product = product_info.get('About Product', 'No additional information available.')
                    return f"Here is information about {product_info['Product Name']}: {about_product}. It costs {product_info['Selling Price']}. Would you like to buy it? (Yes/No)", product_info, negotiation_state
            else:
                return f"Sorry, I couldn't find information about {product_name}.", current_product, negotiation_state
        else:
            return "Sorry, I didn't understand the product name.", current_product, negotiation_state
    elif predicted_intent == "negotiate":
        return initiate_negotiation(current_product)
    else:
        return "I'm sorry, I didn't understand that. How can I assist you?", current_product, negotiation_state

def initiate_negotiation(current_product):
    if current_product:
        return f"Sure, let's negotiate! What price are you looking for?", current_product, "negotiate"
    else:
        return "I'm sorry, but I need more information about the product before we can negotiate.", None, None

def negotiate_price(user_input, current_product):
    # Implement negotiation logic with a maximum discount of 10%
    match = re.search(r'\b\d+(\.\d+)?\b', user_input)
    
    if match:
        proposed_price = float(match.group())
        original_price = float(current_product['Selling Price'].replace('$', ''))  # Remove dollar sign
        max_discounted_price = original_price * 0.9

        if proposed_price >= max_discounted_price:
            return f"Great! We can offer the product at ${proposed_price:.2f}. Would you like to proceed with the purchase? (Yes/No)", current_product, None
        else:
            return f"Sorry, the lowest possible price is 10% off, which is ${max_discounted_price:.2f}. Can you propose a price at least 10% off the original price?", current_product, "negotiate"
    else:
        return "How much lower are you proposing? Please provide a specific amount.", current_product, "negotiate"



# Your existing chatbot code here...
current_product = None
negotiation_state = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.form['user_input']
    global current_product, negotiation_state
    response, current_product, negotiation_state = process_user_input(user_input, current_product, negotiation_state)

    if "Would you like to buy it?" in response:
        # Update negotiation state and current product
        current_product = products_collection.find_one({"Product Name": {"$regex": f".*{user_input.split()[-1]}.*", "$options": "i"}})
        negotiation_state = "buy_inquiry"

    return {'response': response, 'negotiation_state': negotiation_state}

if __name__ == '__main__':
    app.run(debug=True)
