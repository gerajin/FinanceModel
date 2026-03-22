import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from pmdarima import auto_arima
import matplotlib.pyplot as plt
from statsmodels.graphics.tsaplots import plot_acf


df = pd.read_csv("DF prueba.csv")

train=df.iloc[:-10]
test = df.iloc[-10:]
df.set_index('fecha')
df.info()



def wnoise_fun():
    np.random.seed(42)
    anios = 10
    periodos = 12* anios
    wnoise = np.random.normal(loc=0,scale=0.8, size= periodos)
    plt.figure(figsize=(15,4))
    plt.plot(wnoise)
    plt.title("Ruido Blanco")
    acr = plot_acf(wnoise, lags = 50)
    print (acr)

def main():
    while True:
        wnoise_fun()
        text = input("")

#main()

#data= np.random.rand(periodos)*200 #10 años mensual
#meses = pd.date_range("2020-01-01",periods=periodos, freq='ME')
#
#df = pd.DataFrame(data=data,index=meses, columns=['Ventas'])
#
#train = df.iloc[:-10]
#test = df.iloc[-10:]
#
#model_auto = auto_arima(train,None, start_p=0,max_p=2,start_q=0,max_q=2,m=12,start_P=0,start_Q=0,max_P=2,max_Q=2,seasonal=True,d=1,D=1,trace=True,error_action='ignore',suppress_warnings=True,stepwise=True )
#print(model_auto.summary())
#
#
#792475.62