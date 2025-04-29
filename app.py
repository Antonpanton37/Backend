from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import biometeo
import datetime
import numpy as np




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
    sex = 1
    height = 1.66
    if gender == 'Man':
        sex = 2
        height = 1.8
    
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
    ta = Ta
    icl = 0.4

#calculate windspeed at 1.1m height
    v1 = Ws * (4.87 / (4.87 + 67.8 * (1 - 0.1)))  # Wind speed at 1.1 m height (m/s)
    v = v1
    ht = height
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

    tmrt = Tmrt_result['Tmrt']  # Mean radiant temperature (°C)
    vps = 6.107 * (10. ** (7.5 * ta / (238. + ta)))
    vpa = RH * vps / 100  # water vapour presure, kPa

    po = 1013.25  # Pressure
    p = 1013.25  # Pressure
    rob = 1.06
    cb = 3.64 * 1000
    food = 0
    emsk = 0.99
    emcl = 0.95
    evap = 2.42e6
    sigma = 5.67e-8
    cair = 1.01 * 1000

    eta = 0  # No idea what eta is

    c_1 = 0.
    c_2 = 0.
    c_3 = 0.
    c_4 = 0.
    c_5 = 0.
    c_6 = 0.
    c_7 = 0.
    c_8 = 0.
    c_9 = 0.
    c_10 = 0.
    c_11 = 0.

    # INBODY
    metbf = 3.19 * weight ** (3 / 4) * (1 + 0.004 * (30 - age) + 0.018 * ((ht * 100 / (weight ** (1 / 3))) - 42.1))
    metbm = 3.45 * weight ** (3 / 4) * (1 + 0.004 * (30 - age) + 0.010 * ((ht * 100 / (weight ** (1 / 3))) - 43.4))
    if sex == 1:
        met = metbm + work
    else:
        met = metbf + work

    h = met * (1 - eta)
    rtv = 1.44e-6 * met

    # sensible respiration energy
    tex = 0.47 * ta + 21.0
    eres = cair * (ta - tex) * rtv

    # latent respiration energy
    vpex = 6.11 * 10 ** (7.45 * tex / (235 + tex))
    erel = 0.623 * evap / p * (vpa - vpex) * rtv
    # sum of the results
    ere = eres + erel

    # calcul constants
    feff = 0.725
    adu = 0.203 * weight ** 0.425 * ht ** 0.725
    facl = (-2.36 + 173.51 * icl - 100.76 * icl * icl + 19.28 * (icl ** 3)) / 100
    if facl > 1:
        facl = 1
    rcl = (icl / 6.45) / facl
    y = 1

    # should these be else if statements?
    if icl < 2:
        y = (ht-0.2) / ht
    if icl <= 0.6:
        y = 0.5
    if icl <= 0.3:
        y = 0.1

    fcl = 1 + 0.15 * icl
    r2 = adu * (fcl - 1. + facl) / (2 * 3.14 * ht * y)
    r1 = facl * adu / (2 * 3.14 * ht * y)
    di = r2 - r1
    acl = adu * facl + adu * (fcl - 1)

    tcore = [0] * 8

    wetsk = 0
    hc = 2.67 + 6.5 * v ** 0.67
    hc = hc * (p / po) ** 0.55
    c_1 = h + ere
    he = 0.633 * hc / (p * cair)
    fec = 1 / (1 + 0.92 * hc * rcl)
    htcl = 6.28 * ht * y * di / (rcl * np.log(r2 / r1) * acl)
    aeff = adu * feff
    c_2 = adu * rob * cb
    c_5 = 0.0208 * c_2
    c_6 = 0.76075 * c_2
    rdsk = 0.79 * 10 ** 7
    rdcl = 0

    count2 = 0
    j = 1

    while count2 == 0 and j < 7:
        tsk = 34
        count1 = 0
        tcl = (ta + tmrt + tsk) / 3
        count3 = 1
        enbal2 = 0

        while count1 <= 3:
            enbal = 0
            while (enbal*enbal2) >= 0 and count3 < 200:
                enbal2 = enbal
                # 20
                rclo2 = emcl * sigma * ((tcl + 273.15) ** 4 - (tmrt + 273.15) ** 4) * feff
                tsk = 1 / htcl * (hc * (tcl - ta) + rclo2) + tcl

                # radiation balance
                rbare = aeff * (1 - facl) * emsk * sigma * ((tmrt + 273.15) ** 4 - (tsk + 273.15) ** 4)
                rclo = feff * acl * emcl * sigma * ((tmrt + 273.15) ** 4 - (tcl + 273.15) ** 4)
                rsum = rbare + rclo

                # convection
                cbare = hc * (ta - tsk) * adu * (1 - facl)
                cclo = hc * (ta - tcl) * acl
                csum = cbare + cclo

                # core temperature
                c_3 = 18 - 0.5 * tsk
                c_4 = 5.28 * adu * c_3
                c_7 = c_4 - c_6 - tsk * c_5
                c_8 = -c_1 * c_3 - tsk * c_4 + tsk * c_6
                c_9 = c_7 * c_7 - 4. * c_5 * c_8
                c_10 = 5.28 * adu - c_6 - c_5 * tsk
                c_11 = c_10 * c_10 - 4 * c_5 * (c_6 * tsk - c_1 - 5.28 * adu * tsk)
                # tsk[tsk==36]=36.01
                if tsk == 36:
                    tsk = 36.01

                tcore[7] = c_1 / (5.28 * adu + c_2 * 6.3 / 3600) + tsk
                tcore[3] = c_1 / (5.28 * adu + (c_2 * 6.3 / 3600) / (1 + 0.5 * (34 - tsk))) + tsk
                if c_11 >= 0:
                    tcore[6] = (-c_10-c_11 ** 0.5) / (2 * c_5)
                if c_11 >= 0:
                    tcore[1] = (-c_10+c_11 ** 0.5) / (2 * c_5)
                if c_9 >= 0:
                    tcore[2] = (-c_7+abs(c_9) ** 0.5) / (2 * c_5)
                if c_9 >= 0:
                    tcore[5] = (-c_7-abs(c_9) ** 0.5) / (2 * c_5)
                tcore[4] = c_1 / (5.28 * adu + c_2 * 1 / 40) + tsk

                # transpiration
                tbody = 0.1 * tsk + 0.9 * tcore[j]
                sw = 304.94 * (tbody - 36.6) * adu / 3600000
                vpts = 6.11 * 10 ** (7.45 * tsk / (235. + tsk))
                if tbody <= 36.6:
                    sw = 0
                if sex == 2:
                    sw = 0.7 * sw
                eswphy = -sw * evap

                eswpot = he * (vpa - vpts) * adu * evap * fec
                wetsk = eswphy / eswpot
                if wetsk > 1:
                    wetsk = 1
                eswdif = eswphy - eswpot
                if eswdif <= 0:
                    esw = eswpot
                else:
                    esw = eswphy
                if esw > 0:
                    esw = 0

                # diffusion
                ed = evap / (rdsk + rdcl) * adu * (1 - wetsk) * (vpa - vpts)

                # MAX VB
                vb1 = 34 - tsk
                vb2 = tcore[j] - 36.6
                if vb2 < 0:
                    vb2 = 0
                if vb1 < 0:
                    vb1 = 0
                vb = (6.3 + 75 * vb2) / (1 + 0.5 * vb1)

                # energy balance
                enbal = h + ed + ere + esw + csum + rsum + food

                # clothing's temperature
                if count1 == 0:
                    xx = 1
                if count1 == 1:
                    xx = 0.1
                if count1 == 2:
                    xx = 0.01
                if count1 == 3:
                    xx = 0.001
                if enbal > 0:
                    tcl = tcl + xx
                else:
                    tcl = tcl - xx

                count3 = count3 + 1
            count1 = count1 + 1
            enbal2 = 0

        if j == 2 or j == 5:
            if c_9 >= 0:
                if tcore[j] >= 36.6 and tsk <= 34.050:
                    if (j != 4 and vb >= 91) or (j == 4 and vb < 89):
                        pass
                    else:
                        if vb > 90:
                            vb = 90
                        count2 = 1

        if j == 6 or j == 1:
            if c_11 > 0:
                if tcore[j] >= 36.6 and tsk > 33.850:
                    if (j != 4 and vb >= 91) or (j == 4 and vb < 89):
                        pass
                    else:
                        if vb > 90:
                            vb = 90
                        count2 = 1

        if j == 3:
            if tcore[j] < 36.6 and tsk <= 34.000:
                if (j != 4 and vb >= 91) or (j == 4 and vb < 89):
                    pass
                else:
                    if vb > 90:
                        vb = 90
                    count2 = 1

        if j == 7:
            if tcore[j] < 36.6 and tsk > 34.000:
                if (j != 4 and vb >= 91) or (j == 4 and vb < 89):
                    pass
                else:
                    if vb > 90:
                        vb = 90
                    count2 = 1

        if j == 4:
            if (j != 4 and vb >= 91) or (j == 4 and vb < 89):
                pass
            else:
                if vb > 90:
                    vb = 90
                count2 = 1

        j = j + 1

    # PET_cal
    tx = ta
    enbal2 = 0
    count1 = 0
    enbal = 0

    hc = 2.67 + 6.5 * 0.1 ** 0.67
    hc = hc * (p / po) ** 0.55

    while count1 <= 3:
        while (enbal * enbal2) >= 0:
            enbal2 = enbal

            # radiation balance
            rbare = aeff * (1 - facl) * emsk * sigma * ((tx + 273.15) ** 4 - (tsk + 273.15) ** 4)
            rclo = feff * acl * emcl * sigma * ((tx + 273.15) ** 4 - (tcl + 273.15) ** 4)
            rsum = rbare + rclo

            # convection
            cbare = hc * (tx - tsk) * adu * (1 - facl)
            cclo = hc * (tx - tcl) * acl
            csum = cbare + cclo

            # diffusion
            ed = evap / (rdsk + rdcl) * adu * (1 - wetsk) * (12 - vpts)

            # respiration
            tex = 0.47 * tx + 21
            eres = cair * (tx - tex) * rtv
            vpex = 6.11 * 10 ** (7.45 * tex / (235 + tex))
            erel = 0.623 * evap / p * (12 - vpex) * rtv
            ere = eres + erel

            # energy balance
            enbal = h + ed + ere + esw + csum + rsum

            # iteration concerning Tx
            if count1 == 0:
                xx = 1
            if count1 == 1:
                xx = 0.1
            if count1 == 2:
                xx = 0.01
            if count1 == 3:
                xx = 0.001
            if enbal > 0:
                tx = tx - xx
            if enbal < 0:
                tx = tx + xx
        count1 = count1 + 1
        enbal2 = 0
        

    return jsonify({"result": tx})  # Skicka tillbaka ett resultat

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Render bestämmer porten
    app.run(host="0.0.0.0", port=port)
@app.route("/")
def home():
    return jsonify({"message": "Server is running!"})