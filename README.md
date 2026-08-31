# Derivatives Pricing & Dynamic Hedging Simulator

Simulador de fijación de precios de derivados y cobertura dinámica (Delta Hedging), construido en Python con interfaz Streamlit.

## Estructura

| Archivo | Contenido |
|---|---|
| `black_scholes.py` | Fórmula cerrada BSM + Griegas analíticas (Δ, Γ, Θ, Vega, Rho) |
| `binomial_tree.py` | Árbol CRR para opciones americanas/europeas + Griegas leídas del árbol |
| `monte_carlo.py` | Simulación GBM (solución exacta vía Itô), payoffs europeo/asiático/barrera, Griegas por diferencias finitas con common random numbers |
| `hedging_simulator.py` | Motor de cobertura Delta dinámica: cartera autofinanciada, rebalanceo discreto, distribución del error de cobertura |
| `app.py` | Interfaz Streamlit con 3 pestañas: Pricing & Griegas / Delta Hedging en vivo / Estudio de frecuencia |

## Matemáticas aplicadas

- **Lema de Itô**: base de la dinámica `dS = (r-q)S dt + σS dW` y de la expansión de `dV(S,t)` usada tanto en la derivación de Black-Scholes como en la contabilidad de la cartera de cobertura paso a paso.
- **PDE de Black-Scholes**: `∂V/∂t + (r-q)S ∂V/∂S + ½σ²S² ∂²V/∂S² - rV = 0`, resuelta en forma cerrada para vanillas europeas.
- **Monte Carlo**: integración numérica de `E^Q[e^{-rT} payoff(S_T)]` usando la solución exacta del GBM, con reducción de varianza (antitéticas) y Griegas vía diferencias finitas centradas con semillas comunes.
- **Árbol binomial CRR**: aproximación discreta del proceso continuo que converge a Black-Scholes cuando N→∞; permite ejercicio anticipado (americanas).

## Cómo ejecutar

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Validaciones incluidas

- El árbol binomial europeo converge al precio de Black-Scholes al aumentar N.
- Monte Carlo europeo coincide con Black-Scholes dentro del intervalo de confianza del 95%.
- El error de cobertura (P&L de la cartera replicante vs payoff pagado) decrece al aumentar la frecuencia de rebalanceo, consistente con la teoría de replicación continua.
- Si la volatilidad realizada difiere de la implícita usada para calcular Delta, el emisor de la opción incurre en un sesgo sistemático de P&L (ganancia si vol realizada < implícita para el vendedor, y viceversa) — demostrable activando el toggle de "vol mismatch" en la pestaña de hedging.

## Próximas extensiones sugeridas

- Gamma hedging (cobertura de segundo orden con otra opción)
- Superficie de volatilidad implícita (skew/smile) en lugar de σ constante
- Opciones sobre múltiples activos (cesta, spread) vía Monte Carlo multivariado con correlación
