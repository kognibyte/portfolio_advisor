# Portfolio Advisor
Personalize Portfolio Advisor with What-if Simulation

• Create a goal-based advisory agent where users enter financial goals, risk appetite, and current holdings, and receive a suggested allocation. The agent should stress-test the portfolio against scenarios (rate hike, market downturn, inflation), visualize projected outcomes in charts, and suggest rebalancing steps.<br/>
• Suitability disclaimers must be included. Bonus: multi-agent roles (risk profiler, allocator, simulator).<br/>
• Objective: Deliver personalized, scenario-tested investment guidance with clear risk communication.<br/>
• Learning takeaways: Goal-based financial planning logic, Monte Carlo / scenario simulation, data visualization, risk profiling, and embedding responsible-advice guardrails and disclaimers.<br/>

Data Agent -<br/>
Ingests the portfolio CSV, fetches live prices via yfinance and news headlines per ticker; outputs a clean, structured dataset for everything downstream.

Analysis Agent -<br/>
Computes portfolio metrics — returns, Sharpe ratio, sector allocation, concentration — and produces the analytics report the advisory chain reasons from

Risk Agent -<br/>
Scores the investor's risk profile (conservative / moderate / aggressive) and evaluates whether current holdings match that tolerance

Advisory Agent -<br/>
Generates investment and rebalancing suggestions grounded in the RAG knowledge layer, tailored to the risk profile

QA Agent -<br/>
The compliance and suitability gate — checks every recommendation before it reaches the user, and can send it back for revision
