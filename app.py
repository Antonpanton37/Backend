from flask import Flask, request, jsonify
from flask_cors import CORS
import os




app = Flask(__name__)
CORS(app)

@app.route('/calculate', methods=['POST']) # Din React-app skickar data till denna endpoint för att få tillbaka en beräknad siffra.
def calculate():
    data = request.json  # Få datan från frontend

    # Hämta fälten från requesten
    age = int(data.get("age", 0))
    gender = data.get("gender", "unknown")
    weight = float(data.get("weight", 0))
    location = data.get("location", "")
    pace = float(data.get("pace", 5))  # Pace i min/km

    # Dummy-beräkning (byt ut detta mot riktig logik)
    result = weight + pace + age 

    return jsonify({"result": result})  # Skicka tillbaka ett resultat

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Render bestämmer porten
    app.run(host="0.0.0.0", port=port)
