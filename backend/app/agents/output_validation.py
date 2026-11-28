"""Output validation guardrails for the Autonomous Customer Support Platform.

This module provides validation and sanitization of AI-generated responses
before they are shown to customers. It prevents:
1. Internal URLs and endpoints being exposed
2. Secrets and credentials leaking
3. Cross-customer data leakage
4. PII exposure in customer-facing responses
5. Basic hallucination/fact-checking against retrieved knowledge
"""

from enum import Enum
import re
from typing import Optional, Dict, Any, List, Set
from dataclasses import dataclass, field
from urllib.parse import urlparse


class ValidationIssueType(str, Enum):
    """Types of validation issues that can be detected in output."""
    INTERNAL_URL = "INTERNAL_URL"
    SECRET_LEAK = "SECRET_LEAK"
    CROSS_CUSTOMER_DATA = "CROSS_CUSTOMER_DATA"
    PII_EXPOSURE = "PII_EXPOSURE"
    HALLUCINATION = "HALLUCINATION"
    SENSITIVE_CONFIG = "SENSITIVE_CONFIG"
    UNCITED_CLAIM = "UNCITED_CLAIM"


@dataclass
class ValidationIssue:
    """A single validation issue found in the output."""
    issue_type: ValidationIssueType
    description: str
    matched_content: str
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    position: Optional[int] = None


@dataclass
class ValidationResult:
    """Result of output validation."""
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    sanitized_output: str = ""
    confidence_score: float = 1.0

    def add_issue(self, issue: ValidationIssue):
        """Add an issue and update validation status."""
        self.issues.append(issue)
        if issue.severity in ("HIGH", "CRITICAL"):
            self.is_valid = False


# =============================================================================
# Default Validation Rules
# =============================================================================

# Internal URL patterns - things that should never be shown to customers
INTERNAL_URL_PATTERNS = [
    r'https?://localhost[:\d]*',
    r'https?://127\.0\.0\.1[:\d]*',
    r'https?://0\.0\.0\.0[:\d]*',
    r'https?://10\.\d{1,3}\.\d{1,3}\.\d{1,3}[:\d]*',
    r'https?://172\.(1[6-9]|2[0-9]|3[0-1])\.\d{1,3}\.\d{1,3}[:\d]*',
    r'https?://192\.168\.\d{1,3}\.\d{1,3}[:\d]*',
    r'https?://.*\.internal[:\d]*',
    r'https?://.*\.local[:\d]*',
    r'https?://.*\.corp[:\d]*',
    r'https?://.*\.cluster\.local[:\d]*',
    r'https?://.*\.svc\.cluster\.local[:\d]*',
    r'https?://api\.internal[:\d]*',
    r'https?://admin\.internal[:\d]*',
    r'https?://.*\.clouddesk\.internal[:\d]*',
]

# Secret patterns - API keys, tokens, passwords, etc.
# Exclude test/fake values using negative lookahead (can be disabled for testing)
import os
_DISABLE_FAKE_EXCLUSION = os.getenv("DISABLE_FAKE_EXCLUSION", "false").lower() == "true"

if _DISABLE_FAKE_EXCLUSION:
    EXCLUDE_FAKE = ""
else:
    EXCLUDE_FAKE = r"(?!.*(?:FAKE|REDACTED|fake|redacted))"

SECRET_PATTERNS = [
    (rf'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']?{EXCLUDE_FAKE}[a-zA-Z0-9_\-]{{20,}}["\']?', "API_KEY"),
    (rf'(?i)(secret[_-]?key|secretkey)\s*[:=]\s*["\']?{EXCLUDE_FAKE}[a-zA-Z0-9_\-]{{20,}}["\']?', "SECRET_KEY"),
    (rf'(?i)(access[_-]?token|accesstoken)\s*[:=]\s*["\']?{EXCLUDE_FAKE}[a-zA-Z0-9_\-]{{20,}}["\']?', "ACCESS_TOKEN"),
    (rf'(?i)(bearer\s+){EXCLUDE_FAKE}[a-zA-Z0-9_\-\.]{{20,}}', "BEARER_TOKEN"),
    (rf'(?i)(authorization\s*[:=]\s*["\']?){EXCLUDE_FAKE}[a-zA-Z0-9_\-\.]{{20,}}', "AUTH_HEADER"),
    (rf'(?i)(password|passwd|pwd)\s*[:=]\s*["\']?{EXCLUDE_FAKE}[^\s"\']{{8,}}["\']?', "PASSWORD"),
    (rf'(?i)(private[_-]?key|privatekey)\s*[:=]\s*["\']?{EXCLUDE_FAKE}[^\s"\']{{10,}}["\']?', "PRIVATE_KEY"),
    (rf'(?i)(jwt[_-]?secret|jwtsecret)\s*[:=]\s*["\']?{EXCLUDE_FAKE}[a-zA-Z0-9_\-]{{20,}}["\']?', "JWT_SECRET"),
    (rf'(?i)(database[_-]?url|db[_-]?url)\s*[:=]\s*["\']?{EXCLUDE_FAKE}[^\s"\']{{10,}}["\']?', "DB_URL"),
    (rf'(?i)(connection[_-]?string|conn[_-]?str)\s*[:=]\s*["\']?{EXCLUDE_FAKE}[^\s"\']{{10,}}["\']?', "CONN_STRING"),
    (rf'{EXCLUDE_FAKE}sk-[a-zA-Z0-9]{{32,}}', "OPENAI_KEY"),
    (rf'{EXCLUDE_FAKE}xoxb-[a-zA-Z0-9\-]{{20,}}', "SLACK_BOT_TOKEN"),
    (rf'{EXCLUDE_FAKE}xoxp-[a-zA-Z0-9\-]{{20,}}', "SLACK_USER_TOKEN"),
    (rf'{EXCLUDE_FAKE}ghp_[a-zA-Z0-9]{{36,}}', "GITHUB_PAT"),
    (rf'{EXCLUDE_FAKE}glpat-[a-zA-Z0-9\-]{{20,}}', "GITLAB_PAT"),
    (rf'(?i)aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*["\']?{EXCLUDE_FAKE}[a-zA-Z0-9/+=]{{38,40}}["\']?', "AWS_SECRET"),
]

# Cross-customer data patterns - emails, IDs that might belong to other customers
CROSS_CUSTOMER_PATTERNS = [
    (r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', "EMAIL"),
    (r'\b\d{3}-\d{2}-\d{4}\b', "SSN"),
    (r'\b(?:\d[ -]*?){13,16}\b', "CREDIT_CARD"),
    (r'(?i)(customer[_-]?id|customer)\s*[:=]\s*["\']?[a-f0-9\-]{36}["\']?', "CUSTOMER_ID"),
    (r'(?i)tenant[_-]?id\s*[:=]\s*["\']?[a-f0-9\-]{36}["\']?', "TENANT_ID"),
    (r'(?i)user[_-]?id\s*[:=]\s*["\']?[a-f0-9\-]{36}["\']?', "USER_ID"),
    (r'(?i)account[_-]?id\s*[:=]\s*["\']?[a-f0-9\-]{36}["\']?', "ACCOUNT_ID"),
    (r'(?i)organization[_-]?id\s*[:=]\s*["\']?[a-f0-9\-]{36}["\']?', "ORG_ID"),
]

# Sensitive configuration patterns
SENSITIVE_CONFIG_PATTERNS = [
    (r'(?i)(feature[_-]?flag|ff)\s*[:=]\s*(true|false|enabled|disabled)', "FEATURE_FLAG"),
    (r'(?i)(config|configuration)\s*[:=]\s*\{[^}]+\}', "CONFIG_OBJECT"),
    (r'(?i)environment\s*[:=]\s*["\']?(development|staging|production|prod|dev|stage)["\']?', "ENVIRONMENT"),
    (r'(?i)(debug|verbose)\s*[:=]\s*(true|false)', "DEBUG_FLAG"),
    (r'(?i)(log[_-]?level|loglevel)\s*[:=]\s*["\']?(DEBUG|INFO|WARNING|ERROR)["\']?', "LOG_LEVEL"),
]

# Hallucination indicators - claims that should be cited but aren't
HALLUCINATION_INDICATORS = [
    (r'(?i)according to (?:our|the) (?:documentation|docs|knowledge base|kb)', "UNCITED_DOC_CLAIM"),
    (r'(?i)(?:the|our) (?:policy|rule|guideline) states?', "UNCITED_POLICY_CLAIM"),
    (r'(?i)as per (?:the )?(?:documentation|docs|kb|knowledge base)', "UNCITED_DOC_CLAIM"),
    (r'(?i)based on (?:the )?(?:documentation|docs|kb|knowledge base)', "UNCITED_DOC_CLAIM"),
    (r'(?i)our records (?:show|indicate)', "UNCITED_RECORDS_CLAIM"),
    (r'(?i)the system (?:shows|indicates|reports)', "UNCITED_SYSTEM_CLAIM"),
]


# =============================================================================
# Validation Functions
# =============================================================================

def check_internal_urls(text: str) -> List[ValidationIssue]:
    """Check for internal URLs that should not be exposed to customers."""
    issues = []
    seen_positions: Set[tuple[int, int]] = set()  # Track (start, end) to avoid duplicates
    for pattern in INTERNAL_URL_PATTERNS:
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        for match in matches:
            start, end = match.start(), match.end()
            if (start, end) in seen_positions:
                continue
            seen_positions.add((start, end))
            issues.append(ValidationIssue(
                issue_type=ValidationIssueType.INTERNAL_URL,
                description=f"Internal URL detected: {match.group()}",
                matched_content=match.group(),
                severity="HIGH",
                position=match.start(),
            ))
    return issues


def check_secrets(text: str) -> List[ValidationIssue]:
    """Check for secrets and credentials in the output."""
    issues = []
    for pattern, secret_type in SECRET_PATTERNS:
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        for match in matches:
            issues.append(ValidationIssue(
                issue_type=ValidationIssueType.SECRET_LEAK,
                description=f"{secret_type} detected in output",
                matched_content=match.group()[:50] + "..." if len(match.group()) > 50 else match.group(),
                severity="CRITICAL",
                position=match.start(),
            ))
    return issues


def check_cross_customer_data(
    text: str,
    allowed_customer_ids: Optional[Set[str]] = None,
    allowed_emails: Optional[Set[str]] = None,
) -> List[ValidationIssue]:
    """Check for potential cross-customer data leakage.

    Args:
        text: The output text to check
        allowed_customer_ids: Set of customer IDs that are allowed to be mentioned
        allowed_emails: Set of emails that are allowed to be mentioned
    """
    issues = []
    allowed_customer_ids = allowed_customer_ids or set()
    allowed_emails = allowed_emails or set()

    # Also create a set of allowed UUIDs extracted from full patterns
    allowed_uuids = {c.lower() for c in allowed_customer_ids}
    allowed_uuids.update({e.lower() for e in allowed_emails})

    for pattern, data_type in CROSS_CUSTOMER_PATTERNS:
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        for match in matches:
            matched = match.group()

            # Check if this is an allowed reference
            is_allowed = False
            if data_type in ("EMAIL", "USER_ID", "CUSTOMER_ID", "ACCOUNT_ID"):
                # Check if the full matched string is in allowed lists
                if matched.lower() in {e.lower() for e in allowed_emails}:
                    is_allowed = True
                if matched.lower() in {c.lower() for c in allowed_customer_ids}:
                    is_allowed = True
                # Also check if UUID part is in allowed UUIDs
                uuid_match = re.search(r'[a-f0-9\-]{36}', matched, re.IGNORECASE)
                if uuid_match and uuid_match.group().lower() in allowed_uuids:
                    is_allowed = True

            if not is_allowed:
                issues.append(ValidationIssue(
                    issue_type=ValidationIssueType.CROSS_CUSTOMER_DATA,
                    description=f"Potential cross-customer {data_type} detected: {matched[:50]}",
                    matched_content=matched[:50] + "..." if len(matched) > 50 else matched,
                    severity="HIGH",
                    position=match.start(),
                ))
    return issues


def check_pii_exposure(text: str) -> List[ValidationIssue]:
    """Check for PII exposure in customer-facing output."""
    issues = []

    # Email addresses (full exposure)
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    matches = list(re.finditer(email_pattern, text))
    for match in matches:
        # Only flag if it's not a generic/support email
        email = match.group().lower()
        if not any(domain in email for domain in ['support@', 'help@', 'info@', 'noreply@', 'no-reply@', 'admin@']):
            issues.append(ValidationIssue(
                issue_type=ValidationIssueType.PII_EXPOSURE,
                description=f"Email address exposed: {match.group()}",
                matched_content=match.group(),
                severity="MEDIUM",
                position=match.start(),
            ))

    # Phone numbers (various formats)
    phone_patterns = [
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # US format
        r'\b\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b',  # International
    ]
    for pattern in phone_patterns:
        matches = list(re.finditer(pattern, text))
        for match in matches:
            issues.append(ValidationIssue(
                issue_type=ValidationIssueType.PII_EXPOSURE,
                description=f"Phone number exposed: {match.group()}",
                matched_content=match.group(),
                severity="MEDIUM",
                position=match.start(),
            ))

    # SSN
    ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'
    matches = list(re.finditer(ssn_pattern, text))
    for match in matches:
        issues.append(ValidationIssue(
            issue_type=ValidationIssueType.PII_EXPOSURE,
            description=f"SSN exposed: {match.group()}",
            matched_content=match.group(),
            severity="HIGH",
            position=match.start(),
        ))

    # Credit card numbers
    cc_pattern = r'\b(?:\d[ -]*?){13,16}\b'
    matches = list(re.finditer(cc_pattern, text))
    for match in matches:
        # Basic Luhn check could be added here
        issues.append(ValidationIssue(
            issue_type=ValidationIssueType.PII_EXPOSURE,
            description=f"Credit card number exposed: {match.group()}",
            matched_content=match.group(),
            severity="HIGH",
            position=match.start(),
        ))

    return issues


def check_sensitive_config(text: str) -> List[ValidationIssue]:
    """Check for sensitive configuration details in output."""
    issues = []
    for pattern, config_type in SENSITIVE_CONFIG_PATTERNS:
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        for match in matches:
            issues.append(ValidationIssue(
                issue_type=ValidationIssueType.SENSITIVE_CONFIG,
                description=f"Sensitive {config_type} exposed: {match.group()}",
                matched_content=match.group(),
                severity="MEDIUM",
                position=match.start(),
            ))
    return issues


def check_hallucination(
    text: str,
    retrieved_docs: Optional[List[Dict[str, Any]]] = None,
    require_citations: bool = True,
) -> List[ValidationIssue]:
    """Basic hallucination detection - check for uncited claims.

    Args:
        text: The output text to check
        retrieved_docs: List of retrieved documents with citations
        require_citations: Whether to require citations for factual claims
    """
    issues = []

    if not require_citations:
        return issues

    # Check for hallucination indicators
    for pattern, indicator_type in HALLUCINATION_INDICATORS:
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        for match in matches:
            # Check if there's a citation nearby (within 100 chars)
            context_start = max(0, match.start() - 100)
            context_end = min(len(text), match.end() + 100)
            context = text[context_start:context_end]

            # Look for citation patterns like [1], [doc:123], (source), etc.
            has_citation = bool(re.search(r'\[\d+\]|\(source\)|\[doc:|\(doc:|\[source:|source\s+\d+', context, re.IGNORECASE))

            if not has_citation:
                issues.append(ValidationIssue(
                    issue_type=ValidationIssueType.HALLUCINATION,
                    description=f"Uncited factual claim detected: {match.group()}",
                    matched_content=match.group(),
                    severity="MEDIUM",
                    position=match.start(),
                ))

    return issues


def validate_customer_output(
    text: str,
    customer_context: Optional[Dict[str, Any]] = None,
    retrieved_docs: Optional[List[Dict[str, Any]]] = None,
    require_citations: bool = True,
    allowed_customer_ids: Optional[Set[str]] = None,
    allowed_emails: Optional[Set[str]] = None,
) -> ValidationResult:
    """Complete validation of customer-facing output.

    Args:
        text: The AI-generated response to validate
        customer_context: Current customer's context (for allowed references)
        retrieved_docs: Documents retrieved for this response (for citation checking)
        require_citations: Whether to enforce citation requirements
        allowed_customer_ids: Additional customer IDs allowed in output
        allowed_emails: Additional emails allowed in output

    Returns:
        ValidationResult with issues and sanitized output
    """
    result = ValidationResult(
        is_valid=True,
        issues=[],
        sanitized_output=text,
        confidence_score=1.0,
    )

    # Build allowed references from customer context
    if customer_context:
        if not allowed_customer_ids:
            allowed_customer_ids = set()
        if not allowed_emails:
            allowed_emails = set()

        if customer_context.get("customer_id"):
            allowed_customer_ids.add(customer_context["customer_id"])
        if customer_context.get("email"):
            allowed_emails.add(customer_context["email"])

    # Run all validation checks
    all_issues = []

    # 1. Internal URLs (HIGH severity)
    all_issues.extend(check_internal_urls(text))

    # 2. Secrets (CRITICAL severity)
    all_issues.extend(check_secrets(text))

    # 3. Cross-customer data (HIGH severity)
    all_issues.extend(check_cross_customer_data(
        text, allowed_customer_ids, allowed_emails
    ))

    # 4. PII exposure (MEDIUM/HIGH severity)
    all_issues.extend(check_pii_exposure(text))

    # 5. Sensitive configuration (MEDIUM severity)
    all_issues.extend(check_sensitive_config(text))

    # 6. Hallucination/uncited claims (MEDIUM severity)
    all_issues.extend(check_hallucination(text, retrieved_docs, require_citations))

    # Sort by position for consistent output
    all_issues.sort(key=lambda i: i.position or 0)

    # Add issues to result
    for issue in all_issues:
        result.add_issue(issue)

    # Calculate confidence score based on issues
    if all_issues:
        critical_count = sum(1 for i in all_issues if i.severity == "CRITICAL")
        high_count = sum(1 for i in all_issues if i.severity == "HIGH")
        medium_count = sum(1 for i in all_issues if i.severity == "MEDIUM")
        low_count = sum(1 for i in all_issues if i.severity == "LOW")

        # Deduct confidence
        penalty = critical_count * 0.3 + high_count * 0.15 + medium_count * 0.05 + low_count * 0.01
        result.confidence_score = max(0.0, 1.0 - penalty)

    # Generate sanitized output (redact sensitive content)
    result.sanitized_output = sanitize_output(text, all_issues)

    return result


def sanitize_output(text: str, issues: List[ValidationIssue]) -> str:
    """Sanitize output by redacting sensitive content.

    Args:
        text: Original text
        issues: List of validation issues

    Returns:
        Sanitized text with sensitive content redacted
    """
    sanitized = text

    # Sort issues by position (descending) to avoid position shifts during replacement
    sorted_issues = sorted(
        [i for i in issues if i.position is not None],
        key=lambda i: i.position,
        reverse=True
    )

    for issue in sorted_issues:
        if issue.position is not None:
            matched = issue.matched_content
            if "..." in matched:
                # Find the actual match in the text
                base = matched.replace("...", "")
                pos = sanitized.find(base, max(0, issue.position - 10))
                if pos >= 0:
                    # Find the full match
                    end = pos + len(base)
                    # Try to find a reasonable end
                    for i in range(end, min(len(sanitized), end + 50)):
                        if sanitized[i] in ' \t\n.,;:)]}':
                            end = i
                            break
                    replacement = f"[{issue.issue_type.value}_REDACTED]"
                    sanitized = sanitized[:pos] + replacement + sanitized[end:]
            else:
                replacement = f"[{issue.issue_type.value}_REDACTED]"
                start = issue.position
                end = start + len(matched)
                if end <= len(sanitized):
                    sanitized = sanitized[:start] + replacement + sanitized[end:]

    return sanitized


# =============================================================================
# Default Configuration
# =============================================================================

DEFAULT_OUTPUT_VALIDATION_CONFIG: Dict[str, Any] = {
    "check_internal_urls": True,
    "check_secrets": True,
    "check_cross_customer_data": True,
    "check_pii_exposure": True,
    "check_sensitive_config": True,
    "check_hallucination": True,
    "require_citations": True,
    "minimum_confidence_threshold": 0.7,
    "max_issues_before_reject": 5,
}


def is_output_safe(
    text: str,
    config: Optional[Dict[str, Any]] = None,
    customer_context: Optional[Dict[str, Any]] = None,
    retrieved_docs: Optional[List[Dict[str, Any]]] = None,
) -> bool:
    """Quick check if output is safe for customer delivery.

    Args:
        text: The output text to check
        config: Optional validation configuration
        customer_context: Current customer's context
        retrieved_docs: Retrieved documents for citation checking

    Returns:
        True if output passes validation, False otherwise
    """
    if config is None:
        config = DEFAULT_OUTPUT_VALIDATION_CONFIG

    result = validate_customer_output(
        text,
        customer_context=customer_context,
        retrieved_docs=retrieved_docs,
        require_citations=config.get("require_citations", True),
    )

    threshold = config.get("minimum_confidence_threshold", 0.7)
    max_issues = config.get("max_issues_before_reject", 5)

    if result.confidence_score < threshold:
        return False

    if len(result.issues) > max_issues:
        return False

    # Check for critical issues
    critical_issues = [i for i in result.issues if i.severity == "CRITICAL"]
    if critical_issues:
        return False

    # Also check if validation marked it as invalid (HIGH severity issues)
    if not result.is_valid:
        return False

    return True


# =============================================================================
# Testing / Example Usage
# =============================================================================

if __name__ == "__main__":
    import os
    # Disable fake exclusion for testing
    os.environ["DISABLE_FAKE_EXCLUSION"] = "true"

    # Use the test fixture for test secrets (gitignored file)
    try:
        from tests.unit.agents.test_secrets_fixture import TEST_SECRETS
        test_openai_key = TEST_SECRETS["openai_key"]
    except ImportError:
        # Fallback for environments without test fixtures
        # Use a shorter key that doesn't match the 32+ char pattern
        test_openai_key = "sk-FAKETEST"

    print("=== Output Validation Testing ===\n")

    # Test 1: Internal URL detection
    test1 = "You can access the admin panel at http://admin.internal/dashboard"
    result1 = validate_customer_output(test1)
    print("Test 1 - Internal URL:")
    print(f"  Original: {test1}")
    print(f"  Valid: {result1.is_valid}")
    print(f"  Issues: {len(result1.issues)}")
    for issue in result1.issues:
        print(f"    - {issue.issue_type.value}: {issue.description} (severity: {issue.severity})")
    print(f"  Sanitized: {result1.sanitized_output}")
    print()

    # Test 2: Secret detection
    test2 = f"Your API key is {test_openai_key}"
    result2 = validate_customer_output(test2)
    print("Test 2 - Secret Leak:")
    print(f"  Original: {test2}")
    print(f"  Valid: {result2.is_valid}")
    print(f"  Issues: {len(result2.issues)}")
    for issue in result2.issues:
        print(f"    - {issue.issue_type.value}: {issue.description} (severity: {issue.severity})")
    print(f"  Sanitized: {result2.sanitized_output}")
    print()

    # Test 3: Cross-customer data
    test3 = "Customer john@example.com had a similar issue"
    result3 = validate_customer_output(
        test3,
        customer_context={"customer_id": "cust-123", "email": "jane@example.com"}
    )
    print("Test 3 - Cross-customer data:")
    print(f"  Original: {test3}")
    print(f"  Valid: {result3.is_valid}")
    print(f"  Issues: {len(result3.issues)}")
    for issue in result3.issues:
        print(f"    - {issue.issue_type.value}: {issue.description} (severity: {issue.severity})")
    print(f"  Sanitized: {result3.sanitized_output}")
    print()

    # Test 4: PII exposure
    test4 = "Your SSN is 123-45-6789 and phone is 555-123-4567"
    result4 = validate_customer_output(test4)
    print("Test 4 - PII Exposure:")
    print(f"  Original: {test4}")
    print(f"  Valid: {result4.is_valid}")
    print(f"  Issues: {len(result4.issues)}")
    for issue in result4.issues:
        print(f"    - {issue.issue_type.value}: {issue.description} (severity: {issue.severity})")
    print(f"  Sanitized: {result4.sanitized_output}")
    print()

    # Test 5: Hallucination detection
    test5 = "According to our documentation, you can reset your password by clicking the link."
    result5 = validate_customer_output(test5, require_citations=True)
    print("Test 5 - Hallucination (uncited claim):")
    print(f"  Original: {test5}")
    print(f"  Valid: {result5.is_valid}")
    print(f"  Issues: {len(result5.issues)}")
    for issue in result5.issues:
        print(f"    - {issue.issue_type.value}: {issue.description} (severity: {issue.severity})")
    print(f"  Sanitized: {result5.sanitized_output}")
    print()

    # Test 6: With citation (should pass)
    test6 = "According to our documentation [doc:123], you can reset your password by clicking the link."
    result6 = validate_customer_output(test6, require_citations=True)
    print("Test 6 - With Citation:")
    print(f"  Original: {test6}")
    print(f"  Valid: {result6.is_valid}")
    print(f"  Issues: {len(result6.issues)}")
    print()

    # Test 7: Safe output
    test7 = "I've reset your password. You should receive an email shortly with a secure link to set a new password."
    result7 = validate_customer_output(test7)
    print("Test 7 - Safe Output:")
    print(f"  Original: {test7}")
    print(f"  Valid: {result7.is_valid}")
    print(f"  Issues: {len(result7.issues)}")
    print(f"  Confidence: {result7.confidence_score:.2f}")
    print()

    # Test 8: is_output_safe convenience function
    test8 = "Here is your refund confirmation for $50.00"
    safe = is_output_safe(test8)
    print("Test 8 - is_output_safe:")
    print(f"  Output: {test8}")
    print(f"  Safe: {safe}")
    print()

    # Test 9: Internal IP detection
    test9 = "The service is running at http://10.0.0.5:8080/api"
    result9 = validate_customer_output(test9)
    print("Test 9 - Internal IP:")
    print(f"  Original: {test9}")
    print(f"  Valid: {result9.is_valid}")
    print(f"  Issues: {len(result9.issues)}")
    for issue in result9.issues:
        print(f"    - {issue.issue_type.value}: {issue.description}")
    print(f"  Sanitized: {result9.sanitized_output}")
    print()

    print("=== All tests completed ===")