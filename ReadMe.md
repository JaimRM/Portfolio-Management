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

I calculated that a friction of just 1 bps daily, accounting for execution slippage and commissions, reduces the strategy's Sharpe Ratio by approximately 20%. This structural 'drag' shifts the distribution's mean, increasing the Probability of Ruin by nearly 5%. This highlights why Execution Quality must be monitored; a bad broker isn't just a cost, they are a risk factor that can turn a winning strategy into a losing one.

We can add expected shortfall (the average of everything below the VaR) as a more coherent measure, assuming 'final_returns' is our array of 1000 simulated outcomes.

var_95 = np.percentile(final_returns, 5)

expected_shortfall = final_returns[final_returns <= var_95].mean()

print(f"If things go wrong (worst 5%), we expect to lose {abs(expected_shortfall):.2f} on average.")

