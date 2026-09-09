from typing import Any, Callable, Optional

from agents.risk_agent import RiskAgent


AgentFunction = Callable[..., dict[str, Any]]


class PortfolioOrchestrator:
    def __init__(
        self,
        data_agent: Optional[AgentFunction] = None,
        analysis_agent: Optional[AgentFunction] = None,
        advisory_agent: Optional[AgentFunction] = None,
        qa_agent: Optional[AgentFunction] = None,
        use_llm: bool = True,
    ) -> None:
        self.data_agent = data_agent
        self.analysis_agent = analysis_agent
        self.advisory_agent = advisory_agent
        self.qa_agent = qa_agent

        self.risk_agent = RiskAgent(
            use_llm=use_llm
        )

    def run_risk_workflow(self,
        investor: dict[str, Any],
        portfolio_analytics: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            risk_result = self.risk_agent.run(
                investor=investor,
                portfolio_analytics=portfolio_analytics,
            )

            return {
                "workflow_status": "completed",
                "risk_assessment": risk_result,
                "final_disclaimer": risk_result[
                    "disclaimer"
                ],
                "errors": [],
            }

        except Exception as exc:
            return {
                "workflow_status": "failed",
                "risk_assessment": {},
                "final_disclaimer": "",
                "errors": [str(exc)],
            }

    def run_complete_workflow(self,
        investor: dict[str, Any],
        portfolio_input: Any,
    ) -> dict[str, Any]:
        workflow = {
            "workflow_status": "running",
            "data_result": {},
            "analysis_result": {},
            "risk_result": {},
            "advisory_result": {},
            "qa_result": {},
            "final_report": {},
            "errors": [],
        }

        try:
            if self.data_agent is None:
                raise ValueError(
                    "Data Agent is not configured."
                )

            workflow["data_result"] = self.data_agent(
                portfolio_input=portfolio_input
            )

            if self.analysis_agent is None:
                raise ValueError(
                    "Analysis Agent is not configured."
                )

            workflow["analysis_result"] = (
                self.analysis_agent(
                    structured_portfolio=workflow[
                        "data_result"
                    ]
                )
            )

            workflow["risk_result"] = (
                self.risk_agent.run(
                    investor=investor,
                    portfolio_analytics=workflow[
                        "analysis_result"
                    ],
                )
            )

            if self.advisory_agent is None:
                raise ValueError(
                    "Advisory Agent is not configured."
                )

            advisory_context = {
                "investor": investor,
                "portfolio_data": workflow[
                    "data_result"
                ],
                "portfolio_analytics": workflow[
                    "analysis_result"
                ],
                "risk_assessment": workflow[
                    "risk_result"
                ],
            }

            workflow["advisory_result"] = (
                self.advisory_agent(
                    context=advisory_context
                )
            )

            if self.qa_agent is None:
                raise ValueError(
                    "QA Agent is not configured."
                )

            workflow["qa_result"] = self.qa_agent(
                recommendation=workflow[
                    "advisory_result"
                ],
                risk_assessment=workflow[
                    "risk_result"
                ],
            )

            if (
                workflow["qa_result"].get("status")
                != "Approved"
            ):
                workflow["workflow_status"] = (
                    "revision_required"
                )

                workflow["errors"].append(
                    workflow["qa_result"].get(
                        "reason",
                        "QA Agent requested revision.",
                    )
                )

                return workflow

            workflow["final_report"] = {
                "investor": investor,
                "portfolio_analytics": workflow[
                    "analysis_result"
                ],
                "risk_assessment": workflow[
                    "risk_result"
                ],
                "recommendations": workflow[
                    "advisory_result"
                ],
                "qa_review": workflow[
                    "qa_result"
                ],
                "disclaimer": workflow[
                    "risk_result"
                ]["disclaimer"],
            }

            workflow["workflow_status"] = "completed"

            return workflow

        except Exception as exc:
            workflow["workflow_status"] = "failed"
            workflow["errors"].append(str(exc))

            return workflow