"""测试共享 Fixtures"""

import pytest
from app.services.assessment import AssessmentService
from app.services.syllabus import SyllabusService


@pytest.fixture
def syllabus_service():
    return SyllabusService


@pytest.fixture
def assessment_service():
    return AssessmentService
