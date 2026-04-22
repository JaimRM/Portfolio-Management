Risk Quantization: Developed a Monte Carlo engine to simulate 1,000+ market scenarios to determine the Value at Risk (VaR) of a trading strategy.

Stochastic Modeling: Utilized Geometric Brownian Motion principles to model asset price paths and evaluate the probability of portfolio drawdown.

Stress Testing: Conducted simulations to identify "Black Swan" events and tail-risk exposure, aligning with Basel III internal model requirements for market risk.


Stress test:
Furthermore, kurtosis ("fat tails") is accounted for by using the Student-t distribution. A world where "Black Swan" events (extreme losses) happen more frequently is simulated.


While the strategy has a positive drift (μ), the Monte Carlo shows a 21.8% probability of ending the year in a loss.
This Probability of Ruin reaches 26.5% if we take into account real-world market frictions.
With the Student-t distribution, the numbers are 32.1 and 35.8%, much higher due to the presence of more outliers.


Conclusion/The reality gap:
While the theoretical model (Normal Distribution) suggests a ~22% risk of loss, incorporating leptokurtosis and transaction costs reveals a much harsher reality: a 35.8% probability of ending the year in a loss.
This demonstrates that a strategy with a positive expected return can still fail due to the sequence of returns and market friction.

**Assuming a daily drag of 1 basis point (0.01%) to account for commissions, slippage, and bid-ask spreads.*

We can add ES (expected shortfall) as a more coherent measre:

# Assuming 'final_returns' is your array of 1000 simulated outcomes
var_95 = np.percentile(final_returns, 5)

# Expected Shortfall: The average of everything BELOW the VaR
expected_shortfall = final_returns[final_returns <= var_95].mean()

print(f"If things go wrong (worst 5%), we expect to lose {abs(expected_shortfall):.2f} on average.")
