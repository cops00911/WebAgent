---
name: WebAgent QA Runner
description: Run manual web test cases autonomously using Playwright and generate Java/TestNG code or visual HTML reports.
---

# WebAgent QA Runner Skill

This skill allows Antigravity to run manual web test cases autonomously using your project's `WebAgent` engine.

## Instructions

Whenever the user asks to "run a test", "execute a test case spreadsheet", or "automate manual steps":
1. Locate the input test case files (e.g. `*.xlsx`, `*.xls`, or `*.txt`) in the project directory.
2. Execute the test run using the project's main script:
   ```bash
   python3 web_main.py --url "<target_url>" --testcase <path_to_testcase_file>
   ```
3. Locate the generated visual HTML report (`web_report_*.html`) and Java code outputs (`PlaywrightAutomation.java`).
4. Provide the user with direct markdown links to open the report and code in the workspace.
