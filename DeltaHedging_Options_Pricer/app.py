"""
app.py
------
Interfaz Streamlit del simulador de Fijación de Precios de Derivados y
Cobertura Dinámica. Tres pestañas:
  1. Pricing & Griegas: compara Black-Scholes cerrado, árbol binomial (americana)
     y Monte Carlo (europea/exótica) para el mismo contrato.
  2. Delta Hedging en vivo: simula una trayectoria y muestra el rebalanceo
     paso a paso (posición en acciones, caja, P&L acumulado).
  3. Estudio de frecuencia: distribución del error de cobertura para
     distintas frecuencias de rebalanceo (efecto de la discretización).
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from black_scholes import OptionParams, bs_price, bs_greeks
from binomial_tree import binomial_price, binomial_greeks
from monte_carlo import MCConfig, mc_price, mc_greeks
from hedging_simulator import HedgeConfig, _simulate_gbm, hedge_single_path, hedge_error_distribution, rebalance_frequency_study

st.set_page_config(page_title="Derivatives Pricing & Dynamic Hedging", layout="wide")
st.title("Modelo de Fijación de Precios de Derivados y Cobertura Dinámica")
st.caption("Black-Scholes · Árbol Binomial (CRR) · Monte Carlo · Delta Hedging dinámico")

with st.sidebar:
    st.header("Parámetros del contrato")
    S0 = st.number_input("Precio spot (S₀)", value=100.0, min_value=0.01)
    K = st.number_input("Strike (K)", value=100.0, min_value=0.01)
    T = st.number_input("Vencimiento (años)", value=0.5, min_value=0.01, max_value=10.0)
    r = st.number_input("Tasa libre de riesgo (r)", value=0.04, format="%.4f")
    q = st.number_input("Dividend yield (q)", value=0.0, format="%.4f")
    sigma = st.number_input("Volatilidad implícita (σ)", value=0.25, min_value=0.01, format="%.4f")
    option_type = st.selectbox("Tipo", ["call", "put"])

    params = OptionParams(S=S0, K=K, T=T, r=r, sigma=sigma, q=q, option_type=option_type)

tab1, tab2, tab3 = st.tabs(["📐 Pricing & Griegas", "⚖️ Delta Hedging en vivo", "📊 Estudio de frecuencia"])

# ---------------------------------------------------------------- TAB 1
with tab1:
    col1, col2, col3 = st.columns(3)

    bs_p = bs_price(params)
    bs_g = bs_greeks(params)
    with col1:
        st.subheader("Black-Scholes (europea)")
        st.metric("Precio", f"{bs_p:.4f}")
        st.write(pd.DataFrame({"Griega": ["Delta", "Gamma", "Vega (1%)", "Theta (1d)", "Rho (1%)"],
                                "Valor": [bs_g["delta"], bs_g["gamma"], bs_g["vega_1pct"], bs_g["theta_1day"], bs_g["rho_1pct"]]})
                 .set_index("Griega").style.format("{:.5f}"))

    with col2:
        st.subheader("Árbol Binomial CRR")
        N = st.slider("Nº pasos del árbol", 50, 2000, 500, step=50)
        american = st.checkbox("Ejercicio americano", value=True)
        bt_p = binomial_price(params, N=N, american=american)
        bt_g = binomial_greeks(params, N=min(N, 500), american=american)
        st.metric("Precio", f"{bt_p:.4f}", delta=f"{bt_p - bs_p:+.4f} vs BS")
        st.write(pd.DataFrame({"Griega": ["Delta", "Gamma", "Vega (1%)", "Theta (1d)"],
                                "Valor": [bt_g["delta"], bt_g["gamma"], bt_g["vega_1pct"], bt_g["theta_1day"]]})
                 .set_index("Griega").style.format("{:.5f}"))
        if american:
            st.caption(f"Prima de ejercicio anticipado: {bt_p - binomial_price(params, N=N, american=False):.4f}")

    with col3:
        st.subheader("Monte Carlo")
        exotic = st.selectbox("Estructura", ["european", "asian", "up_out", "down_out"],
                               format_func=lambda x: {"european": "Europea vanilla", "asian": "Asiática (media aritm.)",
                                                       "up_out": "Barrera Up-and-Out", "down_out": "Barrera Down-and-Out"}[x])
        barrier = None
        if exotic in ("up_out", "down_out"):
            default_b = S0 * 1.3 if exotic == "up_out" else S0 * 0.7
            barrier = st.number_input("Nivel de barrera", value=float(default_b))
        n_paths = st.select_slider("Nº de trayectorias", [10_000, 50_000, 100_000, 200_000], value=100_000)
        cfg = MCConfig(n_paths=n_paths, n_steps=100)
        mc_res = mc_price(params, cfg, exotic, barrier)
        st.metric("Precio", f"{mc_res['price']:.4f}", delta=f"±{1.96*mc_res['stderr']:.4f} (IC 95%)")
        if exotic == "european":
            st.caption(f"Diferencia vs Black-Scholes: {mc_res['price'] - bs_p:+.4f}")

    st.divider()
    st.subheader("Sensibilidad del precio y Delta al spot (BS)")
    S_range = np.linspace(max(S0 * 0.5, 1), S0 * 1.5, 80)
    prices, deltas, gammas = [], [], []
    for s in S_range:
        pp = OptionParams(S=s, K=K, T=T, r=r, sigma=sigma, q=q, option_type=option_type)
        prices.append(bs_price(pp))
        g = bs_greeks(pp)
        deltas.append(g["delta"])
        gammas.append(g["gamma"])

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=S_range, y=prices, name="Precio opción", line=dict(color="#2563eb")), secondary_y=False)
    fig.add_trace(go.Scatter(x=S_range, y=deltas, name="Delta", line=dict(color="#dc2626", dash="dash")), secondary_y=True)
    fig.add_vline(x=S0, line_dash="dot", line_color="gray", annotation_text="S₀ actual")
    fig.update_layout(height=420, legend=dict(orientation="h", y=1.1))
    fig.update_yaxes(title_text="Precio de la opción", secondary_y=False)
    fig.update_yaxes(title_text="Delta", secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------- TAB 2
with tab2:
    st.subheader("Simulación de cobertura Delta en una trayectoria")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        n_rebal = st.slider("Rebalanceos hasta vencimiento", 4, 500, 126)
    with c2:
        vol_mismatch = st.checkbox("Vol realizada ≠ vol implícita")
    with c3:
        realized_vol = st.number_input("Vol realizada", value=float(sigma), disabled=not vol_mismatch, format="%.4f")
    with c4:
        seed = st.number_input("Semilla aleatoria", value=7, step=1)

    cfg_h = HedgeConfig(n_rebalances=n_rebal, n_paths=1,
                         realized_vol=realized_vol if vol_mismatch else None, seed=int(seed))
    S_path = _simulate_gbm(params, cfg_h, n_rebal)[0]
    detail = hedge_single_path(params, cfg_h, n_rebal, S_path)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Prima recibida (t=0)", f"{detail.attrs['premium']:.4f}")
    m2.metric("Payoff pagado (T)", f"{detail.attrs['payoff']:.4f}")
    m3.metric("Valor cartera cobertura (T)", f"{detail.iloc[-1]['portfolio_value']:.4f}")
    m4.metric("P&L de cobertura", f"{detail.attrs['final_pnl']:+.4f}",
              delta=f"{detail.attrs['final_pnl']/detail.attrs['premium']*100:+.2f}% de la prima")

    fig2 = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                          subplot_titles=("Precio del subyacente S(t)", "Delta (posición en acciones por opción)",
                                           "Valor cartera de cobertura vs Payoff intrínseco acumulado"))
    fig2.add_trace(go.Scatter(x=detail["t"], y=detail["S"], name="S(t)", line=dict(color="#2563eb")), row=1, col=1)
    fig2.add_hline(y=K, line_dash="dot", line_color="gray", row=1, col=1, annotation_text="Strike")
    fig2.add_trace(go.Scatter(x=detail["t"], y=detail["delta"], name="Delta", line=dict(color="#16a34a")), row=2, col=1)
    fig2.add_trace(go.Scatter(x=detail["t"], y=detail["portfolio_value"], name="Cartera cobertura", line=dict(color="#dc2626")), row=3, col=1)
    intrinsic_path = np.maximum(detail["S"] - K, 0) if option_type == "call" else np.maximum(K - detail["S"], 0)
    fig2.add_trace(go.Scatter(x=detail["t"], y=intrinsic_path, name="Valor intrínseco actual", line=dict(color="gray", dash="dash")), row=3, col=1)
    fig2.update_layout(height=750, showlegend=True)
    st.plotly_chart(fig2, use_container_width=True)

    st.caption("Con rebalanceo continuo y vol realizada = vol implícita, el P&L de cobertura debería tender a 0. "
               "Actívalo el checkbox de arriba para simular un desajuste de volatilidad y ver cómo el emisor gana o pierde sistemáticamente.")

# ---------------------------------------------------------------- TAB 3
with tab3:
    st.subheader("Efecto de la frecuencia de rebalanceo sobre el error de cobertura")
    st.write("A menor frecuencia de rebalanceo, mayor dispersión del P&L final de la cartera cubierta "
             "(el 'gamma risk' entre rebalanceos no se cubre). Este estudio corre múltiples trayectorias por frecuencia.")

    freqs = st.multiselect("Frecuencias de rebalanceo a comparar (nº de veces hasta T)",
                            [4, 12, 26, 52, 126, 252, 504], default=[12, 26, 52, 126, 252])
    n_paths_study = st.select_slider("Nº de trayectorias por frecuencia", [100, 300, 500, 1000], value=300)

    if st.button("Ejecutar estudio", type="primary"):
        with st.spinner("Simulando..."):
            study = rebalance_frequency_study(params, sorted(freqs), n_paths=n_paths_study)
        st.dataframe(study.style.format({"mean_pnl": "{:.4f}", "std_pnl": "{:.4f}", "pnl_as_pct_premium": "{:.2f}%"}),
                     use_container_width=True)

        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(x=study["n_rebalances"], y=study["std_pnl"], mode="lines+markers",
                                   name="Desv. estándar del P&L de cobertura", line=dict(color="#dc2626")))
        fig3.update_layout(height=420, xaxis_title="Número de rebalanceos hasta vencimiento",
                            yaxis_title="Desv. estándar del P&L final", xaxis_type="log")
        st.plotly_chart(fig3, use_container_width=True)

        # distribución detallada para la frecuencia más baja y más alta
        lo, hi = min(freqs), max(freqs)
        pnl_lo = hedge_error_distribution(params, HedgeConfig(n_rebalances=lo, n_paths=n_paths_study))
        pnl_hi = hedge_error_distribution(params, HedgeConfig(n_rebalances=hi, n_paths=n_paths_study))
        fig4 = go.Figure()
        fig4.add_trace(go.Histogram(x=pnl_lo, name=f"{lo} rebalanceos", opacity=0.6, marker_color="#dc2626"))
        fig4.add_trace(go.Histogram(x=pnl_hi, name=f"{hi} rebalanceos", opacity=0.6, marker_color="#16a34a"))
        fig4.update_layout(barmode="overlay", height=400, xaxis_title="P&L final de cobertura",
                            yaxis_title="Frecuencia", title="Distribución del error de cobertura")
        st.plotly_chart(fig4, use_container_width=True)
