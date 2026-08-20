# Test Workflow

Run the smallest test set that gives meaningful confidence, then expand for risk.

1. unit checks;
2. type/lint/build checks;
3. integration checks;
4. browser/end-to-end tests for user-facing changes;
5. realtime tests for audio/session changes;
6. security/privacy checks for sensitive changes.

Every production bug should produce a regression test or a documented monitoring alternative.
Never claim tests that were not actually run.
