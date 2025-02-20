from flask import Flask, request, render_template, redirect, url_for, session, send_file, jsonify
from steganography import encode_image, decode_image
from cryptography.fernet import Fernet
import os
import threading
import time
import re
import csv

app = Flask(__name__)
app.secret_key = 'your_secret_key'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
input_image_path = os.path.join(BASE_DIR, 'input_image.png')
output_dir = os.path.join(BASE_DIR, 'outputs')
output_image_path = os.path.join(output_dir, 'encoded_image.png')
user_details_file = os.path.join(BASE_DIR, 'user_details.csv')
passwords = {}
decrypted_messages = {}

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

def change_password_and_erase_output(image_path):
    time.sleep(30)  # Sleep for 30 seconds
    new_password = Fernet.generate_key().decode()
    passwords[image_path] = new_password
    decrypted_messages.pop(image_path, None)  # Erase the decrypted message
    print(f"Password for {image_path} changed to {new_password} and output erased")

def is_valid_password(password):
    if (len(password) >= 8 and
        re.search(r'[A-Z]', password) and
        re.search(r'[a-z]', password) and
        re.search(r'[0-9]', password)):
        return True
    return False

def save_user_details(name, user_id):
    with open(user_details_file, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([name, user_id])

def check_user_credentials(name, password):
    if not os.path.exists(user_details_file):
        return False
    with open(user_details_file, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            if row[0] == name and row[1] == password:
                return True
    return False

@app.route('/')
def index():
    return redirect(url_for('user_details'))

@app.route('/user_details', methods=['GET', 'POST'])
def user_details():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        save_user_details(name, password)
        return jsonify({"message": "User registered successfully", "redirect_url": url_for('login')})
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        if check_user_credentials(name, password):
            return jsonify({"message": "Login successful", "redirect_url": url_for('steganography')})
        else:
            return jsonify({"error": "Invalid credentials. Please register first.", "redirect_url": url_for('user_details')}), 401
    return render_template('login.html')

@app.route('/steganography')
def steganography():
    return render_template('index.html')

@app.route('/encrypt', methods=['POST'])
def encrypt():
    try:
        print("Encrypting image...")  # Debug print
        image = request.files['image']
        message = request.form['message']
        password = request.form['password']
        if not is_valid_password(password):
            return jsonify({"error": "Password must contain at least 8 characters, including uppercase, lowercase letters, and numbers."}), 400
        image.save(input_image_path)
        encode_image(input_image_path, message, output_image_path, password)
        passwords[input_image_path] = password
        print(f"Password stored for {input_image_path}: {password}")  # Debug print
        return jsonify({"message": "Image encrypted successfully", "download_url": f"/download/{os.path.basename(output_image_path)}"})
    except Exception as e:
        print(f"Error during encryption: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/download/<filename>')
def download(filename):
    return send_file(os.path.join(output_dir, filename), as_attachment=True)

@app.route('/decrypt', methods=['POST'])
def decrypt():
    try:
        print("Decrypting image...")  # Debug print
        image = request.files['image']
        password = request.form['password']
        image.save(input_image_path)
        stored_password = passwords.get(input_image_path)
        print(f"Stored password for {input_image_path}: {stored_password}")  # Debug print
        print(f"Provided password: {password}")  # Debug print
        if stored_password and stored_password == password:
            message = decode_image(input_image_path, password)
            if message is None:
                return jsonify({"error": "Incorrect password"}), 401
            decrypted_messages[input_image_path] = message
            threading.Thread(target=change_password_and_erase_output, args=(input_image_path,)).start()
            return message
        else:
            return jsonify({"error": "Incorrect password"}), 401
    except Exception as e:
        print(f"Error during decryption: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
