from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import biometeo
import datetime




app = Flask(__name__)
CORS(app)

@app.route('/calculate', methods=['POST']) # Din React-app skickar data till denna endpoint för att få tillbaka en beräknad siffra.
def calculate():
    data = request.json  # Få datan från frontend

    # Hämta fälten från requesten
    age = int(data.get("age", 35))
    gender = data.get("gender", "Man")
    weight = float(data.get("weight", 75))
    location = data.get("location", "Stockholm")
    pace = float(data.get("pace", 5))  # Pace i min/km

    if pace <= 4.7:
        work = 800
    elif pace <= 5.3:
        work = 670
    elif pace <= 6.2:
        work = 580
    else:
        work = 500


    # Dummy-beräkning (byt ut detta mot riktig logik)
    sex = 0
    if gender == 'Man':
        sex = 1
    
# Ange plats
    key = '967994137b684f6c886100836252503'
    url = f"https://api.weatherapi.com/v1/forecast.json?key={key}&q={location}&lang=sv&days=1"

# Hämta data från API
    data = requests.get(url).json()

# Plocka ut timmarna
    hours = data['forecast']['forecastday'][0]['hour']

# Initialisera variabler
    max_temp = {}  # dict för att hålla högsta temperaturen
    time1 = 0
    temp1 = 0
    humidity1 = 0
    windspeed1 = 0

# Hämta latitud och longitud
    lat = data['location']['lat']
    long = data['location']['lon']

# Loopa igenom timdata och hitta max-temp
    for hour_data in hours:
        time = hour_data['time']
        temp = hour_data['temp_c']
        humidity = hour_data['humidity']
        windspeed = hour_data['wind_kph'] / 3.6  # omvandlat till m/s

        if not max_temp:
            max_temp['max'] = temp

        if max_temp['max'] <= temp:
            max_temp['max'] = temp
            time1 = time
            temp1 = temp
            humidity1 = humidity
            windspeed1 = windspeed

# Tilldelning av värden
    time = time1
    Ta = temp1
    RH = humidity1
    Ws = windspeed1
    time_format = datetime.datetime.strptime(time, "%Y-%m-%d %H:%M")
    day_of_year = time_format.timetuple().tm_yday
    hour_of_day = time_format.hour

#calculate windspeed at 1.1m height
    v1 = biometeo.v1m_cal(Ws, height=10)

    Tmrt_result = biometeo.Tmrt_calc(
        Ta = Ta,  # Air temperature (°C)
        RH = RH,  # Relative humidity (%)
        v = v1,  # Wind speed at the height of 1.1 m (m/s)
        longitude = long,  # Longitude for location
        latitude = lat,  # Latitude for location
        sea_level_height = 10,  # Height above sea (m)
        day_of_year = day_of_year,  # day of the year (1-365)
        hour_of_day = hour_of_day,  # hour of the day (0-23)
        timezone_offset = 2,  # Summertime (CEST)
        N = 0,  # Cloud cover (0 = clear sky, 1 = completely cloudy)
        G = 900,  # Global radiation (W/m²)
        DGratio = 0.20,  # Ratio of difuse and global radiation (dimensionless)
        #Tob = Tob_VP_result['Tob'],  # Surface temperature (°C)
        ltf = 4.0,  # Linke turbidity (dimensionless)
        alb = 0.1,  # Albedo of the surrounding (dimensionless)
        albhum = 0.3,  # Albedo of the human being (dimensionless)
        RedGChk = False,  # Reduction of G presetting by obstacles in boolean
        foglimit = 90,  # lower limit of RH for full diffuse radiation (%)
        bowen = 1  # Bowen ratio (dimensionless)
    )


    PET_result = biometeo.PET(
        Ta=Ta,  # Air temperature (°C)
        VP=Tmrt_result['VP'],  # Vapor Pressure (hPa)
        v=v1,  # Wind speed at 1.1 m height (m/s)
        Tmrt=Tmrt_result['Tmrt'],  # Mean Radiant Temperature (°C)
        icl=0.9,  # Clothing insulation (clo)
        work=work,  # Workload (W/m²)
        ht=1.75,  # Body height (m)
        mbody=weight,  # Body weight (kg)
        age=age,  # Age (years)
        sex=sex,  # Sex (1 = male, 0 = female)
        pos=1  # Position (1 = standing, 0 = sitting)
    )

    return jsonify({"result": PET_result['PET_v']})  # Skicka tillbaka ett resultat

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Render bestämmer porten
    app.run(host="0.0.0.0", port=port)
@app.route("/")
def home():
    return jsonify({"message": "Server is running!"})