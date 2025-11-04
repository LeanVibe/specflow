"""Demo script showing how to use SpecFlow intelligence modules.

This demonstrates the complete AI intelligence pipeline:
1. Extract features from unstructured text
2. Generate acceptance criteria
3. Detect ambiguities
4. Score quality

Prerequisites:
- Set OPENAI_API_KEY, ANTHROPIC_API_KEY, or GEMINI_API_KEY in .env
- Configure AI_PROVIDER in .env (openai, anthropic, or gemini)
"""

from uuid import uuid4

from specflow.intelligence import (
    AmbiguityAnalyzer,
    CriteriaGenerator,
    FeatureExtractor,
    QualityScorer,
)
from specflow.models import PRD, PRDMetadata


def main() -> None:
    """Run intelligence pipeline demo."""
    # Sample PRD text (unstructured)
    prd_text = """
    User Authentication System

    We need a secure login system for our application. Users should be able to
    log in using their email and password. The system needs to validate credentials
    against the database and create a session for authenticated users.

    Requirements:
    - Support email/password authentication
    - Password must be hashed using bcrypt
    - Session tokens should expire after 24 hours
    - Login attempts should be rate-limited to prevent brute force attacks
    - API response time must be under 200ms
    - Support 1000+ concurrent users

    Dashboard Feature:
    After successful login, users should see a personalized dashboard.
    The dashboard needs to be fast and user-friendly, showing recent activity
    and key metrics.
    """

    print("=" * 80)
    print("SpecFlow Intelligence Demo")
    print("=" * 80)
    print()

    # Step 1: Extract Features
    print("📝 Step 1: Extracting features from PRD text...")
    print("-" * 80)
    extractor = FeatureExtractor()
    features = extractor.extract_features(prd_text)

    print(f"✅ Extracted {len(features)} features:")
    for i, feature in enumerate(features, 1):
        print(f"\n{i}. {feature.name}")
        print(f"   Description: {feature.description[:100]}...")
    print()

    # Step 2: Generate Acceptance Criteria
    print("📋 Step 2: Generating acceptance criteria...")
    print("-" * 80)
    generator = CriteriaGenerator()

    for feature in features:
        criteria = generator.generate_acceptance_criteria(feature)
        feature.acceptance_criteria = criteria

        test_stubs = generator.generate_test_stubs(feature)
        feature.test_stubs = test_stubs

        print(f"\n🎯 Feature: {feature.name}")
        print(f"   Acceptance Criteria ({len(criteria)}):")
        for j, ac in enumerate(criteria, 1):
            print(f"   {j}. {ac}")

        print(f"\n   Test Stubs ({len(test_stubs)}):")
        for j, stub in enumerate(test_stubs, 1):
            print(f"   {j}. {stub}")
    print()

    # Step 3: Create PRD and Analyze for Ambiguities
    print("🔍 Step 3: Analyzing for ambiguities...")
    print("-" * 80)
    prd = PRD(
        prd_id=uuid4(),
        title="User Authentication System PRD",
        raw_content=prd_text,
        features=features,
        metadata=PRDMetadata(author="Demo User", source_format="markdown"),
    )

    analyzer = AmbiguityAnalyzer()
    ambiguity_report = analyzer.detect_ambiguities(prd)

    print(f"📊 Found {ambiguity_report.total_issues} ambiguity issues:")
    print(f"   Critical: {ambiguity_report.critical_count}")
    print(f"   High: {ambiguity_report.high_count}")
    print(f"   Has blocking issues: {ambiguity_report.has_blocking_issues}")
    print()

    if ambiguity_report.issues:
        print("   Top issues:")
        for i, issue in enumerate(ambiguity_report.issues[:3], 1):
            print(f"\n   {i}. {issue.ambiguity_type.value.upper()} - {issue.severity.value}")
            print(f"      Problem: {issue.original_text}")
            print(f"      Explanation: {issue.explanation}")
            print(f"      Suggestion: {issue.suggestion}")
    else:
        print("   ✅ No major ambiguities detected!")
    print()

    # Step 4: Score Quality
    print("⭐ Step 4: Scoring feature quality...")
    print("-" * 80)
    scorer = QualityScorer()

    for feature in features:
        score = scorer.score_readiness(feature, prd.prd_id)

        print(f"\n📈 Feature: {feature.name}")
        print(f"   Overall Score: {score.overall_score:.1f}/100 (Grade: {score.grade})")
        print(f"   Ready for Implementation: {'✅ YES' if score.is_ready else '❌ NO'}")
        print(f"\n   Category Scores:")
        print(f"   - Completeness: {score.completeness_score:.1f}%")
        print(f"   - Clarity: {score.clarity_score:.1f}%")
        print(f"   - Testability: {score.testability_score:.1f}%")
        print(f"   - Feasibility: {score.feasibility_score:.1f}%")

        if score.blocking_issues:
            print(f"\n   ⚠️ Blocking Issues:")
            for issue in score.blocking_issues[:3]:
                print(f"   - {issue}")

        if score.recommendations:
            print(f"\n   💡 Recommendations:")
            for rec in score.recommendations[:3]:
                print(f"   - {rec}")

    print()
    print("=" * 80)
    print("✅ Intelligence Pipeline Complete!")
    print("=" * 80)
    print()
    print("Summary:")
    print(f"- Extracted {len(features)} features")
    print(f"- Generated {sum(len(f.acceptance_criteria) for f in features)} acceptance criteria")
    print(f"- Created {sum(len(f.test_stubs) for f in features)} test stubs")
    print(f"- Detected {ambiguity_report.total_issues} ambiguity issues")
    print(
        f"- Average quality score: {sum(scorer.score_readiness(f, prd.prd_id).overall_score for f in features) / len(features):.1f}/100"
    )


if __name__ == "__main__":
    main()
