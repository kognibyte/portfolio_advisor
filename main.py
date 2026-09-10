import os
import json
import statistics
from pathlib import Path
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from openai import OpenAI

load_dotenv()

app = FastAPI(title="Portfolio Advisor Analysis Agent", version="1.0.0")

DATA_FILE = Path(__file__).parent / "data" / "portfolio_training_data.json"


class Goal(BaseModel):
    name: str = Field(default="House down payment")
    target_amount: float = Field(default=3000000.0)
    time_horizon_years: int = Field(default=7)
    monthly_contribution: float = Field(default=25000.0)


class RiskResponses(BaseModel):
    loss_tolerance_percent: float = Field(default=15.0)
    income_stability: str = Field(default="stable")
    investment_experience: str = Field(default="intermediate")
    liquidity_need: str = Field(default="medium")


class PortfolioConfig(BaseModel):
    trading_days: int = Field(default=252)
    risk_free_rate: float = Field(default=0.03)
    methodology: str = Field(default="fixed_current_weights")
    observations_used_for_annualization: int = Field(default=252)


class Holding(BaseModel):
    symbol: str
    quantity: float
    current_price: Optional[float] = None
    purchase_price: Optional[float] = None
    history: List[float] = Field(default_factory=list)


class AgentRequest(BaseModel):
    goal: Goal = Field(default_factory=Goal)
    risk_responses: RiskResponses = Field(default_factory=RiskResponses)
    holdings: List[Holding]
    scenario: str = Field(default="base")
    config: PortfolioConfig = Field(default_factory=PortfolioConfig)


class AgentResponse(BaseModel):
    total_market_value: float
    asset_weights: Dict[str, float]
    asset_class_allocation: Dict[str, float]
    sector_allocation: Dict[str, float]
    annualized_return: float
    annualized_volatility: float
    sharpe_ratio: float
    maximum_drawdown: float
    concentration: Dict[str, float]
    data_quality_warnings: List[str]
    analysis: str
    recommendations: List[str]
    analytics_report: Dict[str, Any]


class PortfolioAnalysisAgent:
    def __init__(self, data_file: Path = DATA_FILE):
        self.data = self._load_data(data_file)
        self.training = self.data.get("training_data", [])
        self.rules = self.data.get("rules", {})
        self.scenarios = self.data.get("scenario_defaults", {})
        self.disclaimer = self.rules.get("disclaimer", "This is educational advice and not investment advice.")
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.openai_client = None
        if self.api_key:
            try:
                self.openai_client = OpenAI(api_key=self.api_key)
            except Exception:
                self.openai_client = None

    def _load_data(self, data_file: Path) -> Dict[str, Any]:
        if not data_file.exists():
            return {"training_data": [], "rules": {}, "scenario_defaults": {}}
        with open(data_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def evaluate(self, request: AgentRequest) -> AgentResponse:
        if not request.holdings:
            raise HTTPException(status_code=400, detail="Holdings list cannot be empty.")

        # Convert holdings to market-value tuple per users requested "Quantity × Current Price"
        # and permit a fallback from purchase_price if current_price is absent.
        values = []
        weights = {}
        for h in request.holdings:
            price = h.current_price if h.current_price is not None else h.purchase_price
            if price is None or price <= 0:
                raise HTTPException(status_code=400, detail=f"Missing current_price for holding {h.symbol}.")
            if h.quantity <= 0:
                raise HTTPException(status_code=400, detail=f"Quantity must be positive for holding {h.symbol}.")
            values.append((h.symbol.upper(), h.quantity * price, price))

        total_market_value = sum(v for _, v, _ in values)
        if total_market_value <= 0:
            raise HTTPException(status_code=400, detail="Holdings total market value must be positive.")

        # Asset weights: current market-value divided by portfolio total
        for symbol, value, _ in values:
            weights[symbol] = round(value / total_market_value, 6)

        # training metadata map
        records = {item.get("symbol", "").upper(): item for item in self.training}
        warnings = []
        unknown = [h.symbol.upper() for h in request.holdings if h.symbol.upper() not in records]
        if unknown:
            warnings.append(f"Missing training metadata for symbol(s): {', '.join(unknown)}")

        # asset-class allocation and sector allocation from mapped metadata
        asset_class_allocation = {}
        sector_allocation = {}
        for h in request.holdings:
            item = records.get(h.symbol.upper(), {})
            asset_class = item.get("asset_class", "unknown")
            sector = item.get("sector", "unknown")
            weight = weights.get(h.symbol.upper(), 0.0)
            asset_class_allocation[asset_class] = asset_class_allocation.get(asset_class, 0.0) + weight
            sector_allocation[sector] = sector_allocation.get(sector, 0.0) + weight

        # Historical daily returns, portfolio return series, and annualized metrics
        portfolio_returns = self.compute_historical_metrics(request, values, weights, request.config)
        annualized_return = portfolio_returns["annualized_return"]
        annualized_volatility = portfolio_returns["annualized_volatility"]
        sharpe_ratio = portfolio_returns["sharpe_ratio"]
        maximum_drawdown = portfolio_returns["maximum_drawdown"]
        daily_asset_returns = portfolio_returns["daily_asset_returns"]
        portfolio_return_series = portfolio_returns["portfolio_return_series"]

        # Concentration metrics
        concentration = self.compute_concentration(weights)

        recommendations = self._recommendations(request, annualized_return, annualized_volatility, metrics=portfolio_returns)

        analytics_report = {
            "scenario": request.scenario,
            "goal": request.goal.model_dump(),
            "risk_responses": request.risk_responses.model_dump(),
            "methodology": request.config.methodology,
            "risk_free_rate_assumption": request.config.risk_free_rate,
            "observations_used_for_annualization": request.config.observations_used_for_annualization,
            "portfolio_metrics": {
                "total_market_value": round(total_market_value, 2),
                "asset_weights": weights,
                "asset_class_allocation": asset_class_allocation,
                "sector_allocation": sector_allocation,
                "annualized_return": annualized_return,
                "annualized_volatility": annualized_volatility,
                "sharpe_ratio": sharpe_ratio,
                "maximum_drawdown": maximum_drawdown,
                "concentration": concentration,
                "data_quality_warnings": warnings,
            },
            "daily_asset_returns": daily_asset_returns,
            "portfolio_return_series": portfolio_return_series,
            "disclaimer": self.disclaimer,
            "stress_tests": {
                "rate_hike": self.scenarios.get("rate_hike", {"growth_multiplier": 0.94, "stress_multiplier": 0.88}),
                "market_downturn": self.scenarios.get("market_downturn", {"growth_multiplier": 0.89, "stress_multiplier": 0.79}),
                "inflation": self.scenarios.get("inflation", {"growth_multiplier": 0.96, "stress_multiplier": 0.82}),
            },
        }

        analysis = self._build_local_analysis(request, annualized_return, annualized_volatility, sharpe_ratio)
        analysis = self._generate_ai_analysis_if_possible(request, analytics_report, analysis)

        return AgentResponse(
            total_market_value=round(total_market_value, 2),
            asset_weights=weights,
            asset_class_allocation=asset_class_allocation,
            sector_allocation=sector_allocation,
            annualized_return=annualized_return,
            annualized_volatility=annualized_volatility,
            sharpe_ratio=sharpe_ratio,
            maximum_drawdown=maximum_drawdown,
            concentration=concentration,
            data_quality_warnings=warnings,
            analysis=analysis,
            recommendations=recommendations,
            analytics_report=analytics_report,
        )

    def compute_historical_metrics(self, request: AgentRequest, values: List[tuple], weights: Dict[str, float], config: PortfolioConfig) -> Dict[str, Any]:
        # Build daily return series from provided history lists.
        # If a holding has no history, fall back to a flat return sample of 0.0 to keep project architecture simple.
        daily_asset_returns = {}
        trading_days = max(1, config.trading_days)

        for symbol, _, _ in values:
            hist = []
            for h in request.holdings:
                if h.symbol.upper() == symbol and h.history:
                    hist = h.history
                    break
            if len(hist) >= 2:
                daily_series = []
                for i in range(1, len(hist)):
                    daily_series.append(hist[i] / hist[i-1] - 1)
                daily_asset_returns[symbol] = daily_series
            else:
                # Historical estimate fallback: flat non-volatile data
                daily_asset_returns[symbol] = [0.0] * max(2, config.observations_used_for_annualization)

        # Portfolio return series using fixed current weights.
        # Align series lengths project-safely by truncating to shortest period.
        length = min(len(series) for series in daily_asset_returns.values()) if daily_asset_returns else 1
        if length == 0:
            length = 1
        portfolio_returns = []
        for idx in range(length):
            total = 0.0
            for symbol, _, _ in values:
                total += weights[symbol] * daily_asset_returns[symbol][idx]
            portfolio_returns.append(total)

        if len(portfolio_returns) == 0:
            portfolio_returns = [0.0]

        # The requested formulas from the attachment.
        # Annualized return: (1 + mean daily return)^trading_days - 1
        mean_daily_return = statistics.fmean(portfolio_returns)
        annualized_return = round((1 + mean_daily_return) ** trading_days - 1, 6)

        # Annualized volatility: std(daily returns) * sqrt(trading_days)
        annualized_volatility = round(statistics.pstdev(portfolio_returns) * (trading_days ** 0.5), 6)

        # Sharpe ratio with configured risk-free-rate assumption and historical estimate label in analytics report.
        sharpe_ratio = round((annualized_return - config.risk_free_rate) / max(annualized_volatility, 0.000001), 6)

        # Maximum drawdown: cumulative product, running peak, drawdown, then min drawdown absolute.
        cumulative = 1.0
        peak = 1.0
        drawdowns = []
        for r in portfolio_returns:
            cumulative *= (1 + r)
            if cumulative > peak:
                peak = cumulative
            drawdowns.append(cumulative / peak - 1)
        maximum_drawdown = round(abs(min(drawdowns)) if drawdowns else 0.0, 6)

        # Bound Sharpe in a stable finite range if no genuine history was supplied.
        if all(v == 0.0 for v in portfolio_returns):
            sharpe_ratio = 0.0

        return {
            "daily_asset_returns": daily_asset_returns,
            "portfolio_return_series": portfolio_returns,
            "annualized_return": annualized_return,
            "annualized_volatility": annualized_volatility,
            "sharpe_ratio": sharpe_ratio,
            "maximum_drawdown": maximum_drawdown,
        }

    def compute_concentration(self, weights: Dict[str, float]) -> Dict[str, float]:
        items = list(weights.values())
        largest_holding_weight = round(max(items), 6)
        top_three_weight = round(sum(sorted(items, reverse=True)[:3]), 6)
        herfindahl_index = round(sum(w * w for w in items), 6)
        return {
            "largest_holding_weight": largest_holding_weight,
            "top_three_weight": top_three_weight,
            "herfindahl_index": herfindahl_index,
        }

    def _build_local_analysis(self, request: AgentRequest, annualized_return: float, annualized_volatility: float, sharpe_ratio: float) -> str:
        return (
            f"Goal '{request.goal.name}' evaluated over {request.goal.time_horizon_years} years. "
            f"The portfolio is projected to return {annualized_return:.2%} annually with "
            f"volatility {annualized_volatility:.2%} and Sharpe ratio {sharpe_ratio:.2f}."
        )

    def _generate_ai_analysis_if_possible(self, request: AgentRequest, analytics_report: Dict[str, Any], fallback_text: str) -> str:
        if not self.openai_client:
            return fallback_text + " " + self.disclaimer

        try:
            prompt = {
                "goal": request.goal.model_dump(),
                "risk_responses": request.risk_responses.model_dump(),
                "scenario": request.scenario,
                "summary": analytics_report,
            }
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.2,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a concise portfolio advisory assistant. Produce one short paragraph with scenario-aware financial planning guidance and a clear suitability disclaimer. Do not give regulated investment advice."
                    },
                    {
                        "role": "user",
                        "content": json.dumps(prompt, indent=2)
                    },
                ],
            )
            text = response.choices[0].message.content.strip()
            return text if text else fallback_text
        except Exception:
            return fallback_text + " " + self.disclaimer

    def _recommendations(self, request: AgentRequest, annualized_return: float, annualized_volatility: float, metrics: Dict[str, Any]) -> List[str]:
        recommendations = []
        if annualized_volatility > 0.20:
            recommendations.append("Reduce volatility by adding defensive or fixed-income exposure and review sector concentration.")
        else:
            recommendations.append("Maintain current exposure and monitor risk on a quarterly basis.")

        if request.goal.target_amount and request.goal.target_amount > 0:
            recommendations.append(f"Track progress toward goal '{request.goal.name}' against the annual contribution path.")

        recommendations.append("Stress-test the portfolio against rate hike, market downturn, and inflation scenarios.")
        recommendations.append("Suitability disclaimer: this output is educational and should be reviewed with a qualified advisor.")
        recommendations.append(f"Historical methodology: fixed current weights; risk-free-rate assumption: {request.config.risk_free_rate}; observations: {request.config.observations_used_for_annualization}.")
        return recommendations


agent = PortfolioAnalysisAgent()


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "portfolio-advisor-analysis-agent"}


@app.post("/agent", response_model=AgentResponse)
def run_agent(request: AgentRequest):
    try:
        result = agent.evaluate(request)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
