# Project Plan: AI Intelligence Layer Implementation

## Objective
Implement 4 core AI intelligence modules using pydantic.ai to make SpecFlow valuable by extracting features, generating criteria, detecting ambiguities, and scoring quality.

## Context
- ✅ Pydantic data models exist (PRD, Feature, AmbiguityIssue, QualityScore)
- ✅ Markdown parser implemented
- ✅ Configuration and logging infrastructure ready
- ✅ pydantic-ai dependency installed (v0.0.15)

## Todo List

### Phase 1: Test Infrastructure Setup
- [ ] Create test fixtures for PRD/Feature data
- [ ] Set up mock AI responses for testing
- [ ] Verify test discovery and pytest configuration

### Phase 2: Feature Extractor (extractor.py)
- [ ] Write tests for FeatureExtractor (5 tests)
- [ ] Implement FeatureExtractor class
- [ ] Implement _build_extraction_agent helper
- [ ] Run tests and achieve >85% coverage
- [ ] Commit working extractor

### Phase 3: Criteria Generator (generator.py)
- [ ] Write tests for CriteriaGenerator (4 tests)
- [ ] Implement CriteriaGenerator class
- [ ] Implement acceptance criteria generation
- [ ] Implement test stub generation
- [ ] Run tests and achieve >85% coverage
- [ ] Commit working generator

### Phase 4: Ambiguity Analyzer (analyzer.py)
- [ ] Write tests for AmbiguityAnalyzer (5 tests)
- [ ] Implement AmbiguityAnalyzer class
- [ ] Implement _check_for_vague_terms helper
- [ ] Implement AI-powered improvement suggestions
- [ ] Run tests and achieve >85% coverage
- [ ] Commit working analyzer

### Phase 5: Quality Scorer (scorer.py)
- [ ] Write tests for QualityScorer (5 tests)
- [ ] Implement QualityScorer class
- [ ] Implement _check_completeness helper
- [ ] Implement _calculate_overall_score with weights
- [ ] Run tests and achieve >85% coverage
- [ ] Commit working scorer

### Phase 6: Integration & Documentation
- [ ] Update intelligence/__init__.py with exports
- [ ] Run full test suite (>85% coverage)
- [ ] Manual integration test with example PRD
- [ ] Update PROGRESS.md with completion status
- [ ] Final commit

## Success Criteria
- ✅ All 4 modules implemented with pydantic.ai
- ✅ 19+ tests passing (5+4+5+5 tests)
- ✅ >85% test coverage
- ✅ Can extract features from unstructured text
- ✅ Generates valid Given/When/Then criteria
- ✅ Detects at least 5 types of ambiguities
- ✅ Scores features correctly (complete=high, incomplete=low)

## Implementation Approach
1. Follow TDD rigorously: write tests first, then implementation
2. Start with OpenAI provider (most common)
3. Use simple, working code first - optimize later
4. Handle errors gracefully (return empty/default on failure)
5. Use existing models from specflow.models
6. Log with LoggerMixin for debugging

## Review Section
(To be filled after implementation)
