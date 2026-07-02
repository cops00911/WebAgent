# WebAgent

An autonomous, AI-driven QA Automation Agent that parses manual test cases (from Text or Excel files), executes them in a browser using Playwright, and compiles them into clean, structured Playwright code (Java/TestNG).

## Features

- **Testcase Ingestion:** Ingest manual steps from text/Excel files.
- **Autonomous Playwright execution:** Matches actions using Heuristics or GPT-4o.
- **Visual Reporting:** Step-by-step screenshots comparing page state before and after each action.
- **MCP Server support:** Exposes test execution to AI clients via the Model Context Protocol.

## Local Usage

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Initialize Playwright:
   ```bash
   playwright install
   ```
3. Run manual test cases:
   ```bash
   python3 web_main.py --url "https://example.com" --testcase standard_testcase.xlsx
   ```
