"""TestRail integration client — base infrastructure + aggregator.

`TestRailClient` is the protocol-agnostic aggregator: one HTTP session,
one auth setup, one rate limiter, all resource clients attached.

Per ADR-003 this is the public entry point of `testrail-core`. The MCP
package and any external Python consumer instantiate this class.
"""

from testrail_core.api.attachments import AttachmentsClient
from testrail_core.api.case_fields import CaseFieldsClient
from testrail_core.api.cases import CasesClient
from testrail_core.api.configs import ConfigsClient
from testrail_core.api.milestones import MilestonesClient
from testrail_core.api.plans import PlansClient
from testrail_core.api.projects import ProjectsClient
from testrail_core.api.results import ResultsClient
from testrail_core.api.runs import RunsClient
from testrail_core.api.sections import SectionsClient
from testrail_core.api.shared_steps import SharedStepsClient
from testrail_core.api.statuses import StatusesClient
from testrail_core.api.suites import SuitesClient
from testrail_core.api.tests import TestsClient
from testrail_core.api.users import UsersClient
from testrail_core.client.base_client import BaseAPIClient, ClientConfig
from testrail_core.client.exceptions import (
    TestRailAPIError,
    TestRailAuthenticationError,
    TestRailBadRequestError,
    TestRailError,
    TestRailNetworkError,
    TestRailNotFoundError,
    TestRailPermissionError,
    TestRailRateLimitError,
    TestRailServerError,
    TestRailTimeoutError,
)


class TestRailClient(BaseAPIClient):
    """Main TestRail API client with all resource clients attached."""

    def __init__(self, config: ClientConfig, rate_limiter=None):
        super().__init__(config, rate_limiter)
        self.projects = ProjectsClient(self)
        self.suites = SuitesClient(self)
        self.sections = SectionsClient(self)
        self.cases = CasesClient(self)
        self.tests = TestsClient(self)
        self.runs = RunsClient(self)
        self.plans = PlansClient(self)
        self.results = ResultsClient(self)
        self.case_fields = CaseFieldsClient(self)
        self.statuses = StatusesClient(self)
        self.users = UsersClient(self)
        self.milestones = MilestonesClient(self)
        self.configs = ConfigsClient(self)
        self.attachments = AttachmentsClient(self)
        self.shared_steps = SharedStepsClient(self)


__all__ = [
    "TestRailClient",
    "BaseAPIClient",
    "ClientConfig",
    "TestRailError",
    "TestRailAPIError",
    "TestRailTimeoutError",
    "TestRailNetworkError",
    "TestRailAuthenticationError",
    "TestRailPermissionError",
    "TestRailNotFoundError",
    "TestRailBadRequestError",
    "TestRailRateLimitError",
    "TestRailServerError",
]
