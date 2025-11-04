"""Shared fixtures for E2E tests."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from specflow.models import (
    PRD,
    ComplexityLevel,
    Feature,
    PRDMetadata,
    PriorityLevel,
    Requirement,
    RequirementType,
)


@pytest.fixture
def comprehensive_prd_content() -> str:
    """Real-world comprehensive PRD content for E2E testing."""
    return """# User Authentication System

## Overview
Implement a secure, scalable user authentication system with email/password login,
social authentication, and multi-factor authentication support.

## Business Goals
- Reduce user onboarding friction by 40%
- Improve security posture to meet SOC2 requirements
- Support 100k+ concurrent users

## Features

### Feature 1: Email/Password Authentication
**Description:** Allow users to register and login using email and password credentials.

**User Story:** As a new user, I want to create an account with my email and password
so that I can securely access the platform.

**Requirements:**
- User must provide valid email address
- Password must meet security requirements (12+ chars, uppercase, lowercase, number, special char)
- Email verification required before account activation
- Password reset via email link
- Account lockout after 5 failed login attempts

**Acceptance Criteria:**
- Given valid email and password, when user registers, then account is created and verification email sent
- Given valid credentials, when user logs in, then user is authenticated and redirected to dashboard
- Given invalid credentials, when user attempts login, then error message is displayed
- Given 5 failed attempts, when user tries again, then account is temporarily locked

**Test Stubs:**
- test_user_registration_with_valid_credentials
- test_email_verification_flow
- test_login_with_valid_credentials
- test_login_with_invalid_credentials
- test_account_lockout_after_failed_attempts

### Feature 2: Social Authentication
**Description:** Enable login via Google, GitHub, and LinkedIn OAuth providers.

**User Story:** As a user, I want to log in using my existing social media accounts
so that I don't need to remember another password.

**Requirements:**
- Support Google OAuth 2.0
- Support GitHub OAuth
- Support LinkedIn OAuth
- Link multiple auth providers to single account
- Secure token storage and refresh

**Acceptance Criteria:**
- Given user clicks social login, when OAuth succeeds, then user is authenticated
- Given user has existing account, when linking social auth, then providers are linked
- Given OAuth provider is down, when user tries to login, then fallback error is shown

### Feature 3: Multi-Factor Authentication (MFA)
**Description:** Add optional MFA using TOTP (time-based one-time passwords).

**User Story:** As a security-conscious user, I want to enable two-factor authentication
so that my account is protected even if my password is compromised.

**Requirements:**
- Support TOTP authenticator apps (Google Authenticator, Authy)
- QR code generation for setup
- Backup codes for account recovery
- Optional enforcement for admin users
- Remember device for 30 days

**Acceptance Criteria:**
- Given user enables MFA, when logging in, then TOTP code is required
- Given valid TOTP code, when submitted, then authentication succeeds
- Given invalid TOTP code, when submitted 3 times, then account is locked
- Given user has backup codes, when TOTP unavailable, then backup code works

## Technical Constraints
- Must integrate with existing PostgreSQL database
- Session tokens expire after 24 hours
- API rate limit: 100 requests/minute per user
- GDPR compliant data handling

## Success Metrics
- Registration conversion rate > 60%
- Login success rate > 95%
- Average login time < 2 seconds
- Zero security breaches
"""


@pytest.fixture
def simple_prd_content() -> str:
    """Simple PRD content for basic E2E testing."""
    return """# Task Management Feature

## Overview
Basic task management system for productivity.

## Features

### Feature 1: Create Tasks
Users can create new tasks with titles and descriptions.

**Requirements:**
- Task must have title (required)
- Description is optional
- Auto-save on creation

**Acceptance Criteria:**
- Given user enters title, when saving, then task is created
- Given empty title, when saving, then validation error shown
"""


@pytest.fixture
def malformed_prd_content() -> str:
    """Malformed PRD content for error testing."""
    return """# Broken PRD

This PRD has no proper structure.
Just random text without sections or features.
"""


@pytest.fixture
def empty_prd_content() -> str:
    """Empty PRD content for error testing."""
    return ""


@pytest.fixture
def api_client() -> TestClient:
    """Create FastAPI test client for E2E API tests."""
    from specflow.api.main import app

    return TestClient(app)


@pytest.fixture
def sample_prd_for_pipeline() -> PRD:
    """Create a complete PRD instance for pipeline testing."""
    req1 = Requirement(
        requirement_id=uuid4(),
        description="User can log in with email and password",
        requirement_type=RequirementType.FUNCTIONAL,
        priority=PriorityLevel.HIGH,
        acceptance_criteria=[
            "Given valid credentials, when user submits, then authentication succeeds",
            "Given invalid credentials, when user submits, then error is shown",
        ],
        edge_cases=["Empty fields", "SQL injection", "XSS attempts"],
    )

    feature1 = Feature(
        feature_id=uuid4(),
        name="Email/Password Login",
        description="Allow users to authenticate with email and password",
        user_story="As a user, I want to log in with email so that I can access my account",
        requirements=[req1],
        acceptance_criteria=[
            "User can log in with valid credentials",
            "Invalid credentials show error",
            "Account locks after 5 failed attempts",
        ],
        test_stubs=[
            "test_login_success",
            "test_login_failure",
            "test_account_lockout",
        ],
        priority=PriorityLevel.CRITICAL,
        complexity=ComplexityLevel.MODERATE,
        estimated_days=3.0,
        tags=["auth", "security", "mvp"],
    )

    return PRD(
        prd_id=uuid4(),
        title="Authentication System",
        raw_content="# Authentication System\n\nUser authentication features...",
        parsed_sections=[],
        features=[feature1],
        metadata=PRDMetadata(
            author="E2E Test",
            version="1.0",
            source_format="markdown",
            tags=["test", "e2e"],
        ),
    )
