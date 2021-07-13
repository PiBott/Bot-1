# Clase con todos los datos y funciones relacionadas con la informacion de la moneda, comprar/vender en binance

# Librerias necesarias
import time

import pandas as pd
import numpy as np
from binance.client import Client
from binance.exceptions import BinanceAPIException
from binance.enums import *
import datetime as dt
import math
import os
import plotly.graph_objects as plot

# Clase con los datos y las funciones
class BinanceClass:

    # Constructor de la clase
    def __init__(self, API_Key, Secret_Key, CoinPair, Frequency, FechaInicio, FechaFinal):

        self.PublicKey = API_Key
        self.PrivateKey = Secret_Key
        self.CoinPair = CoinPair

        self.Crypto = CoinPair[0] + CoinPair[1] + CoinPair[2]
        self.Fiat = CoinPair[3] + CoinPair[4] + CoinPair[5]

        self.Frequency = Frequency

        self.FechaInicio = FechaInicio
        self.FechaFinal = FechaFinal

        #Calcular el numero total de velas a descargar segun el rango de tiempo seleccionado
        FI = dt.datetime(int(FechaInicio[0:4]), int(FechaInicio[5:7]), int(FechaInicio[8:10]), int(FechaInicio[11:13]),
                        int(FechaInicio[14:16]), int(FechaInicio[17:19]))
        FF = FechaFinal
        self.Total_Time = math.floor((FF - FI).total_seconds())

        if "m" in self.Frequency:
            if(len(self.Frequency)) == 2:
                self.CandleSeconds = 60*float(self.Frequency[0])
                self.CandleMinutes = int(self.Frequency[0])
            else:
                self.CandleSeconds = 60*float(self.Frequency[:2])
                self.CandleMinutes = int(self.Frequency[:2])
        elif "h" in self.Frequency:
            if (len(self.Frequency)) == 2:
                self.CandleSeconds = 3600*float(self.Frequency[0])
                self.CandleMinutes = 60*int(self.Frequency[0])
            else:
                self.CandleSeconds = 3600*float(self.Frequency[:2])
                self.CandleMinutes = 60*int(self.Frequency[:2])
        elif "d" in self.Frequency:
            self.CandleSeconds = 86400*float(self.Frequency[0])
            self.CandleMinutes = 24*60*int(self.Frequency[0])
        elif "W" in self.Frequency:
            self.CandleSeconds = 7*86400*float(self.Frequency[0])
            self.CandleMinutes = 7*24*60*int(self.Frequency[0])
        elif "M" in self.Frequency:
            self.CandleSeconds = 30*86400*float(self.Frequency[0])
            self.CandleMinutes = 30*24*60*int(self.Frequency[0])

        self.DataElements = math.floor(self.Total_Time/self.CandleSeconds)

        self.binance_client = Client(API_Key, Secret_Key)

        self.df = pd.DataFrame(columns = ["time", "open", "high", "low", "close", "volume", "trades"])

        self.RUN = True

        #Valores por defecto
        self.SMA_R = 10
        self.SMA_L = 20

        #Booleanos de señales de compra o venta
        self.Buy_Signal = False
        self.Sell_Signal = False

        #Booleanos de estados de las ordenes
        self.order_status = None
        self.Order = None

        self.market_order = False

        #Informacion
        self.info = self.binance_client.get_symbol_info(self.CoinPair) #Informacion sobre el par

        self.min_cantidad = float(self.info["filters"][2].get("minQty")) #Múltiplo minimo de compra de la moneda
        self.max_cantidad = float(self.info["filters"][2].get("maxQty")) #Maxima cantidad de compra de la moneda
        self.min_notional = float(self.info["filters"][3].get("minNotional")) #Cantidad mínima a comprar de la moneda

        #Informacion sobre el balance de la cuenta (libre, no en operaciones)
        self.cantidad_crypto = self.binance_client.get_asset_balance(asset = self.Crypto).get("free")
        self.cantidad_fiat = self.binance_client.get_asset_balance(asset = self.Fiat).get("free")

        self.cantidad_orden = 1.0

    # Display de las keys de Binance
    def display_keys(self):
        return print("Keys de Binance: \nPublic Key: {} \nPrivate Key: {} \n".format(self.PublicKey, self.PrivateKey))

    # Display del par de monedas seleccionado
    def display_pair(self):
        return print("Par de monedas seleccionado: {}\n".format(self.CoinPair))

    # Display de la frecuencia seleccionada
    def display_frequency(self):
        return print("Frecuencia de las velas seleccionada: {}".format(self.Frequency))

    # Display del numero total de elementos
    def display_elements(self):
        return print("Número total de velas: {}".format(self.DataElements))

    #Mostrar por pantalla el grafico de velas con el intervalo de fechas y la frecuencia seleccionados
    def display_candles_chart(self, data):
        fig = plot.Figure(data = [plot.Candlestick(x = data["start"],
                          open = data["open"],
                          high = data["high"],
                          low = data["low"],
                          close = data["close"])])

        fig.update_layout(
            title = "Gráfica {}, Frecuencia {}".format(self.CoinPair,self.Frequency),
            yaxis_title="{}".format(self.CoinPair),
            font_family="Arial",
            font_color="black",
            title_font_family="Arial",
            title_font_color="black",
            legend_title_font_color="black"
        )

        fig.show()

    #Descargar los datos de las velas correspondientes para el rango de tiempo seleccionado
    def get_initial_candle_data(self):
        data = self.binance_client.get_klines(symbol=self.CoinPair, interval=self.Frequency, limit=self.DataElements)
        self.df = self.data_filter(data)

    #Convertir los datos que proporciona la API a un Dataframe
    def data_filter(self, data):
        df = pd.DataFrame(data)
        df = df.drop([6, 7, 9, 10, 11], axis=1)

        columns = ["time", "open", "high", "low", "close", "volume", "trades"]
        df.columns = columns

        for i in columns:
            df[i] = df[i].astype(float)

        df["start"] = pd.to_datetime(df["time"]*1000000) #Pasar los milisegundos a horario UTC
        df["MediaMovil_R"] = np.nan #Media movil rapida (llenar columna)
        df["MediaMovil_L"] = np.nan #Media movil lenta (llenar columna)
        return df

    #Actualizar a los ultimos datos registrados por Binance
    def update_data(self):
        new_candle = self.binance_client.get_klines(symbol=self.CoinPair, interval=self.Frequency, limit=1)
        # limit = 1 -> se descarga los datos de la ultima vela
        # interval -> intervalo de esa vela (frecuencia)
        self.df.drop(index = 0, inplace = True) #Quitamos la primera vela de todas y movemos el resto 1 indice hacia abajo
        self.df = self.df.append(self.data_filter(new_candle), ignore_index=True)
        self.df.index = list(range(self.DataElements))

    #Ejecucion de las ordenes de compra o venta del bot
    def open_order(self, operacion, cantidad):
        try:
            self.opened_order = self.binance_client.create_order(
                symbol = self.CoinPair,
                side = operacion,
                type = "MARKET",
                quantity = cantidad
            )
        except BinanceAPIException as e:
            print(e)

    # Registro de la actividad del bot (para escribir la ordenes en un txt por ejemplo)
    def registro_orden(self, tipo_orden_ejecutada, comision, moneda_comision, PRECIO = "NONE"):
        if os.path.exists("Log_{}_{}_BOT.txt".format(self.CoinPair, self.Frequency)): #Opcion con el txt ya creado
            f1 = open("Log_{}_{}_BOT.txt".format(self.CoinPair, self.Frequency),"a+")
            f1.write("{}\t{}\t{}\t{}\t{}\t{}\n".format(str(dt.datetime.now()), tipo_orden_ejecutada, str(PRECIO), str(self.cantidad_orden), comision, moneda_comision))
            f1.close()
            print("Nueva orden: {}\t{}\t{}\t{}\t{}\t{}\n".format(str(dt.datetime.now()), tipo_orden_ejecutada, str(PRECIO), str(self.cantidad_orden), comision, moneda_comision))
        else:
            f1 = open("Log_{}_{}_BOT.txt".format(self.CoinPair, self.Frequency),"a+")
            f1.write("FECHA \t ORDEN \t PRECIO \t CANTIDAD \t COMISIÓN \t MONEDA COMISIÓN\n")
            f1.write("{}\t{}\t{}\t{}\t{}\t{}\n".format(str(dt.datetime.now()), tipo_orden_ejecutada, str(PRECIO), str(self.cantidad_orden), comision, moneda_comision))
            f1.close()
            print("Nueva orden: {}\t{}\t{}\t{}\t{}\t{}\n".format(str(dt.datetime.now()), tipo_orden_ejecutada, str(PRECIO), str(self.cantidad_orden), comision, moneda_comision))

    # Funcion para notificar que se acaba de fillear una orden
    def notify_order(self):
        if self.order_status == "FILLED":
            mean_prize_operation = 0
            comisiones_pagadas = 0
            for i in self.market_order["fills"]: #Es necesario calcular el mean de la orden
                comisiones_pagadas += float(self.market_order["commission"])
                mean_prize_operation += float(i["price"])*float(i["qty"])
            mean_prize_operation = mean_prize_operation/self.cantidad_orden
            self.registro_orden("FILLED", comisiones_pagadas, self.market_order["commissionAsset"], mean_prize_operation)
        else:
            self.registro_orden(self.order_status)

    #Funcion para descargar los datos iniciales necesarios y preparar el bot para funcionar
    def prepare_bot(self):
        self.get_initial_candle_data()
        print("Preparando bot para operar\n")
        self.display_pair()
        self.display_frequency()

    # Funcion para activar y mantener ejecutándose al bot
    def run_bot(self):

        self.update_data() #Actualizacion de los datos hasta la ultima vela disponible
        start_time = self.df.start.iloc[-1] + dt.timedelta(minutes = self.CandleMinutes) #Se empieza a operar JUSTO cuando acaba una vela y empieza la siguiente

        while dt.datetime.now() < start_time:
            pass
            time.sleep(2) #Esperamos 2 segundos para asegurarnos de que la siguiente vela esta disponible

        while self.RUN:
            #Mientras las variable RUN sea True, el bot se seguirá ejecutando, cuando deje de serlo (False), se parará

            tiempo_inicio = time.time() #Calculamos el tiempo inicial (se empieza a operar en ese tiempo)
            #self.single_operation() #Se hacen las operaciones
            tiempo_operacion = time.time() - tiempo_inicio #Tiempo de las oepraciones ejecutadas en single_operation()
            time.sleep(self.CandleSeconds - tiempo_operacion) #Tiempo hasta seguir con la siguiente vela, de esta forma no se repiten las velas

    # Funcion que ejecuta todas las funcionalidades del bot
    #