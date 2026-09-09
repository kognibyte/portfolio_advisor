from typing import Any


class RiskService:
    """
    Deterministic Risk Service.

    It calculates the investor risk score, classifies the investor,
    evaluates portfolio risk and compares the portfolio with the
    investor's risk profile.

    Important:
    These thresholds are simplified assumptions for a demo.
    Production thresholds must be approved by investment and
    compliance specialists.
    """

    PROFILE_ORDER = {
        "Conservative": 1,
        "Moderate": 2,
        "Aggressive": 3,
    }

    LEVEL_SCORES = {
        "Low": 25.0,
        "Medium": 60.0,
        "High": 90.0,
    }

    def assess(self, investor: dict[str, Any], analytics: dict[str, Any]) -> dict[str, Any]:
        self.validate_investor(investor)
        self.validate_analytics(analytics)

        risk_score, score_breakdown = self.calculate_risk_score(investor)

        risk_profile = self.determine_risk_profile(risk_score)

        portfolio_risk = self.determine_portfolio_risk(analytics)

        alignment = self.check_alignment(investor_profile=risk_profile, portfolio_profile=portfolio_risk)

        warnings = self.generate_warnings(analytics=analytics, investor_profile=risk_profile)

        return {
            "risk_score": risk_score,
            "risk_profile": risk_profile,
            "portfolio_risk_level": portfolio_risk,
            "alignment_status": alignment["status"],
            "alignment_reason": alignment["reason"],
            "score_breakdown": score_breakdown,
            "warnings": warnings,
        }

    def calculate_risk_score(self,investor: dict[str, Any]) -> tuple[float, list[dict[str, Any]]]:
        components = []

        horizon_score = self.score_horizon(investor["investment_horizon_years"])

        components.append(
            self.create_component(
                name="Investment horizon",
                score=horizon_score,
                weight=0.25,
                reason=(
                    f'Investment horizon is '
                    f'{investor["investment_horizon_years"]} years.'
                ),
            )
        )

        appetite_score = self.LEVEL_SCORES[investor["risk_appetite"]]

        components.append(
            self.create_component(
                name="Risk appetite",
                score=appetite_score,
                weight=0.25,
                reason=(
                    f'Stated risk appetite is '
                    f'{investor["risk_appetite"]}.'
                ),
            )
        )

        loss_score = self.score_loss_tolerance(investor["loss_tolerance_percent"])

        components.append(
            self.create_component(
                name="Loss tolerance",
                score=loss_score,
                weight=0.20,
                reason=("Maximum acceptable temporary loss is "
                    f'{investor["loss_tolerance_percent"]}%.'
                ),
            )
        )

        financial_capacity_score = (self.score_financial_capacity(
                income_stability=investor["income_stability"],
                liquidity_need=investor["liquidity_need"],
            )
        )

        components.append(
            self.create_component(
                name="Financial capacity",
                score=financial_capacity_score,
                weight=0.20,
                reason=(
                    f'Income stability is '
                    f'{investor["income_stability"]} and '
                    f'liquidity need is '
                    f'{investor["liquidity_need"]}.'
                ),
            )
        )

        experience_score = self.LEVEL_SCORES[investor["investment_experience"]]

        components.append(
            self.create_component(
                name="Investment experience",
                score=experience_score,
                weight=0.10,
                reason=(
                    f'Investment experience is '
                    f'{investor["investment_experience"]}.'
                ),
            )
        )

        total_score = sum(item["weighted_score"]
            for item in components
        )

        return round(total_score, 2), components

    @staticmethod
    def determine_risk_profile(risk_score: float) -> str:
        if risk_score < 40:
            return "Conservative"

        if risk_score < 70:
            return "Moderate"

        return "Aggressive"

    def determine_portfolio_risk(self,analytics: dict[str, Any]) -> str:
        allocation = {
            str(asset).strip().lower(): float(weight)
            for asset, weight in analytics[
                "asset_allocation"
            ].items()
        }

        equity = allocation.get("equity", 0.0)
        alternatives = allocation.get("alternatives", 0.0)
        crypto = allocation.get("crypto", 0.0)

        risky_asset_percentage = (equity + alternatives + crypto)

        if risky_asset_percentage < 40:
            return "Conservative"

        if risky_asset_percentage < 70:
            return "Moderate"

        return "Aggressive"

    def check_alignment(self, investor_profile: str, portfolio_profile: str) -> dict[str, str]:
        difference = abs(self.PROFILE_ORDER[investor_profile] - self.PROFILE_ORDER[portfolio_profile])

        if difference == 0:
            return {
                "status": "Aligned",
                "reason": ("The portfolio risk level matches the investor risk profile."),
            }

        if difference == 1:
            return {
                "status": "Partially Aligned",
                "reason": (
                    f"The investor is classified as "
                    f"{investor_profile}, but the portfolio "
                    f"appears {portfolio_profile}."
                ),
            }

        return {
            "status": "Not Aligned",
            "reason": (
                f"The investor is classified as "
                f"{investor_profile}, but the portfolio "
                f"appears {portfolio_profile}."
            ),
        }

    @staticmethod
    def generate_warnings(analytics: dict[str, Any],investor_profile: str) -> list: 
        warnings = []

        largest_holding = analytics.get("largest_holding_weight")
        largest_sector = analytics.get("largest_sector_weight")
        volatility = analytics.get("annualised_volatility")

        if (largest_holding is not None and float(largest_holding) > 25):
            warnings.append("A single holding represents more than 25% of the portfolio.")

        if (largest_sector is not None and float(largest_sector) > 40):
            warnings.append("A single sector represents more than 40% of the portfolio.")

        if (volatility is not None and float(volatility) > 25):
            warnings.append("The portfolio has elevated historical volatility.")

        if (investor_profile == "Conservative" and float(analytics["asset_allocation"].get("Equity", 0,)) > 40):
            warnings.append("Equity exposure may be high for a conservative investor.")
        return warnings

    @staticmethod
    def score_horizon(years: int) -> float:
        if years < 3:
            return 20.0

        if years < 7:
            return 45.0

        if years < 15:
            return 70.0

        return 90.0

    @staticmethod
    def score_loss_tolerance(loss_percentage: float) -> float:
        if loss_percentage < 10:
            return 20.0

        if loss_percentage < 20:
            return 45.0

        if loss_percentage < 35:
            return 70.0

        return 90.0

    def score_financial_capacity(self, income_stability: str, liquidity_need: str) -> float:
        income_score = self.LEVEL_SCORES[income_stability]

        liquidity_scores = {
            "High": 20.0,
            "Medium": 60.0,
            "Low": 90.0,
        }

        liquidity_score = liquidity_scores[liquidity_need]

        return round(income_score * 0.60 + liquidity_score * 0.40, 2,)

    @staticmethod
    def create_component(name: str, score: float, weight: float, reason: str) -> dict[str, Any]:
        return {
            "component": name,
            "score": score,
            "weight": weight,
            "weighted_score": round(score * weight, 2,),
            "reason": reason,
        }

    @staticmethod
    def validate_investor(investor: dict[str, Any]) -> None:
        required_fields = [
            "financial_goal",
            "target_amount",
            "investment_horizon_years",
            "risk_appetite",
            "loss_tolerance_percent",
            "liquidity_need",
            "investment_experience",
            "income_stability",
        ]

        missing = [field
            for field in required_fields
            if field not in investor
        ]

        if missing:
            raise ValueError("Missing investor fields: " + ", ".join(missing))

        valid_levels = {"Low", "Medium", "High"}

        level_fields = [
            "risk_appetite",
            "liquidity_need",
            "investment_experience",
            "income_stability",
        ]

        for field in level_fields:
            if investor[field] not in valid_levels:
                raise ValueError(f"{field} must be Low, Medium or High.")

        if investor["investment_horizon_years"] < 1:
            raise ValueError("Investment horizon must be at least one year.")

        if not (0 <= investor["loss_tolerance_percent"] <= 100):
            raise ValueError("Loss tolerance must be between 0 and 100.")

    @staticmethod
    def validate_analytics(analytics: dict[str, Any]) -> None:
        if "asset_allocation" not in analytics:
            raise ValueError("Portfolio asset allocation is required.")

        allocation = analytics["asset_allocation"]

        if not isinstance(allocation, dict):
            raise ValueError("Asset allocation must be a dictionary.")

        total = sum(float(value)
            for value in allocation.values()
        )

        if not 99 <= total <= 101:
            raise ValueError("Portfolio allocation percentages must total approximately 100%.")