#Codigo main del bot de trading

#Importación de otros archivos del código
import pandas as pd
from DataConfig import BINANCE, COIN, DATE, FREQUENCY
import BinanceClassFile

Bot_1 = BinanceClassFile.BinanceClass(BINANCE["API_Key"], BINANCE["Secret_Key"], COIN[0], FREQUENCY, DATE["StartDate"], DATE["EndDate"])

Bot_1.display_pair()

Bot_1.display_elements()

Bot_1.get_initial_candle_data()

Bot_1.display_candles_chart(Bot_1.df)

# Esta es la prueba 2 para ver si funcion github

# Esta es la prueba para ver si el github es mejor que el git de los cojones