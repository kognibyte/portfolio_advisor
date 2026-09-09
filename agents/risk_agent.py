from typing import Any
from dotenv import load_dotenv

from services.llm_service import LLMService
from services.risk_service import RiskService


DISCLAIMER = (
    "This risk assessment is provided for educational and "
    "informational purposes only. It is based on the information "
    "provided by the user and simplified portfolio-risk rules. "
    "It does not constitute investment, financial, legal or tax "
    "advice. Investment values can rise or fall, and projected "
    "outcomes are not guaranteed. Consult a qualified financial "
    "adviser before making investment decisions."
)

load_dotenv()

class RiskAgent:
    def __init__(
        self,
        use_llm: bool = True,
    ) -> None:
        self.risk_service = RiskService()
        self.llm_service = (
            LLMService()
            if use_llm
            else None
        )

    def run(
        self,
        investor: dict[str, Any],
        portfolio_analytics: dict[str, Any],
    ) -> dict[str, Any]:
        risk_result = self.risk_service.assess(
            investor=investor,
            analytics=portfolio_analytics,
        )

        if self.llm_service:
            summary = (
                self.llm_service.generate_risk_summary(
                    risk_result
                )
            )
        else:
            summary = (
                f"The investor is classified as "
                f'{risk_result["risk_profile"]} with a '
                f'risk score of {risk_result["risk_score"]}. '
                f"The portfolio is "
                f'{risk_result["alignment_status"].lower()} '
                f"with this profile."
            )

        risk_result["summary"] = summary
        risk_result["disclaimer"] = DISCLAIMER
        risk_result["agent_name"] = "Risk Agent"
        risk_result["status"] = "success"

        return risk_result