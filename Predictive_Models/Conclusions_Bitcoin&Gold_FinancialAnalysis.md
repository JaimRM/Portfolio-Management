1. Estadística Descriptiva y Estacionariedad

Los datos cubren más de 8 años de retornos diarios de Bitcoin (BTC_ret) y Oro (Gold_ret).

Riesgo vs. Retorno: El retorno promedio diario de BTC (0.067%) es ligeramente superior al del oro (0.054%), pero su desviación estándar (std) es casi 4 veces mayor (4.07% frente a 1.09%). En la práctica institucional, esto significa que BTC es muchísimo más volátil.

Asimetría y Curtosis: la curtosis en el bloque ARIMA (14.60) confirma que los retornos de BTC presentan colas extremadamente pesadas. Los retornos no son normales; hay eventos de "fat tail risk" brutales (el mínimo de BTC es un zarpazo del −46.47%).

Correlación: Pearson (0.1073) y Spearman (0.1091) muestran una correlación lineal y monótona muy baja. El oro y BTC apenas se mueven juntos en el día a día.

Test ADF (Augmented Dickey-Fuller): Ambos p-valores son 0.0000. Rechazamos la hipótesis nula de raíz unitaria. Los retornos son estacionarios, lo cual es la luz verde obligatoria antes de meterlos en cualquier modelo de series temporales.



2. Modelos Univariantes: ARIMA vs. GARCH
   

ARIMA(1,0,1) en BTC

Intentamos predecir el retorno de BTC usando su propio pasado (AR1) y los errores del pasado (MA1).

El veredicto: El modelo es ruido. Si miramos la columna P>|z| (los p-valores), tanto la constante (0.452) como el componente autorregresivo ar.L1 (0.375) y el de medias móviles ma.L1 (0.456) NO son estadísticamente significativos (están muy por encima de 0.05).

El test de Ljung-Box (Prob(Q) = 0.86) nos dice que los residuos ya no tienen autocorrelación, lo cual es matemáticamente correcto, pero el modelo no tiene poder predictivo real por sí mismo.


GARCH(1,1)

Como los retornos financieros muestran "volatility clustering" (la volatilidad se agrupa), el proceso GARCH modela la varianza.
Análisis de coeficientes: beta[1] es 0.8159 y sumamente significativo (p≈0). Esto demuestra una fuerte persistencia de la volatilidad. Si hoy hay shock en el mercado, el miedo tardará bastantes días en disiparse.

El modelo estima una volatilidad diaria actual del 3.27%, que, anualizada, equivale a un 51.86%. Para un portfolio manager, este es el dato clave para calcular el tamaño de la posición (position sizing).



3. Modelos Multivariantes y Causalidad: ARX y VAR
   

ARX (ARIMA con variable exógena)

Aquí introducimos la rentabilidad del oro (Gold_ret) para explicar la de BTC.

Sorpresa: El coeficiente de Gold_ret es 0.3995 con un p-valor de 0.000. Estadísticamente, parece que el Oro "explica" parte del retorno contemporáneo de BTC.

El truco institucional: Ojo con la ejecución. El forecast asume que el Oro es un Random Walk (Gold=rw). Si la relación es puramente contemporánea (ocurre el mismo día), no sirve para predecir el futuro de BTC a menos que podamos predecir el oro primero.


VAR (Vector Autoregressive) y Granger

El VAR analiza la bidireccionalidad.

Los criterios de selección (AIC, BIC) seleccionan el lag 0. Esto es una bandera roja econométrica: el pasado de una variable no ayuda a predecir la otra. El script fuerza el lag=1 por defecto.

Test de Causalidad de Granger: El p-valor es 0.883. Fallas en rechazar H0.

Conclusión: El oro NO causa económicamente a BTC en el sentido de Granger. Los movimientos pasados del oro no sirven para predecir los movimientos futuros de BTC.


4. El Sistema de Trading y Backtesting
El bloque final es la lógica cuantitativa que junta todo para operar:
=============================================
  SEÑAL HOY        : LONG
  ARIMA forecast   : +0.00218
  VAR   forecast   : +0.00173
  GARCH vol diaria : 0.0327  (umbral 0.04)
=============================================


La Estrategia: El sistema da señal de COMPRA (LONG) porque los retornos esperados (tanto de ARIMA como de VAR) son positivos, y la volatilidad actual de GARCH (3.27%) está por debajo del límite de riesgo que tolera el algoritmo (4.00%). Si la volatilidad fuera >4%, el sistema se apagaría por gestión de riesgo.


Métricas de Backtesting (Walk-Forward)
Simulación móvil con una ventana de 252 días (1 año bursátil). Aquí está la realidad del modelo:

Días en mercado: Solo 147 de 1877 días posibles (aprox. el 7.8% del tiempo). Es un modelo muy selectivo. Solo opera cuando las condiciones de volatilidad y retorno esperado son perfectas.

Hit Rate: 53.7%. Ligera ventaja estadística (gana más de la mitad de las veces), lo cual es normal y saludable en fondos cuantitativos de alta volatilidad.

Max Drawdown: −24.18%. La peor racha de pérdidas desde el pico hasta el valle es de casi la cuarta parte de la cuenta. Para BTC es "bajo", pero para capital institucional requeriría un stop loss estricto.

Sharpe Anualizado: 0.373. Ajustando el retorno por el riesgo, este ratio es mediocre/bajo. Un fondo institucional busca ratios Sharpe combinados superiores a 1.0. Un 0.37 significa que estamos asumiendo demasiada volatilidad para el premio neto.


El Asesino Silencioso (Coste Total Acumulado): 28.60%. Aquí está el problema. Al abrir y cerrar posiciones en BTC (donde los spreads, comisiones de exchanges o deslizamientos pueden ser altos), gastamos casi un 30% del capital simulado solo en costes operativos a lo largo del histórico.

Conclusión: El modelo está bien estructurado matemáticamente (limpia bien la estacionariedad y controla la volatilidad vía GARCH), pero la señal predictiva es débil, no hay causalidad real con el oro, y los costes de transacción devoran la rentabilidad de la estrategia. Necesitaríamos refinar las variables predictoras (los "features").
