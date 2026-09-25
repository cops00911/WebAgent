#!/usr/bin/env python3
import os
import sys
import argparse
import logging
from dotenv import load_dotenv
import web_driver_utils
from web_agent import WebAgent
from web_reporter import WebHTMLReporter

# Load environment configuration (.env)
load_dotenv()

# Reconfigure stdout/stderr for utf-8 (prevents charmap errors on Windows)
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("web_agent.log", mode="w", encoding="utf-8")
    ]
)
logger = logging.getLogger("WebAgent.main")

def sanitize_class_name(s: str) -> str:
    """Sanitize description strings into valid PascalCase Java class identifiers."""
    import re
    # Remove special characters, split by spaces/dashes/underscores
    words = re.split(r'[^a-zA-Z0-9]+', s)
    capitalized_words = [w.capitalize() for w in words if w]
    name = "".join(capitalized_words)
    if not name:
        return "PlaywrightAutomationCase"
    # Ensure it starts with a letter (prepend 'TC' if it starts with a number)
    if name[0].isdigit():
        name = "TC" + name
    return name

def parse_excel_test_cases(file_path: str) -> list:
    """Parse multiple rows of step-by-step instructions from a standard manual Excel sheet."""
    import openpyxl
    import re
    wb = openpyxl.load_workbook(file_path, data_only=True)
    sheet = wb.active
    
    step_headers = {"test steps", "test step", "steps", "step description", "actions", "action", "step"}
    desc_headers = {"description", "test case description", "name", "test case name", "title", "summary", "test case"}
    precondition_headers = {
        "precondition", "preconditions", "pre-condition", "pre-conditions",
        "prerequisite", "prerequisites", "pre-requisite", "pre-requisites", "setup"
    }
    
    step_col_idx = None
    desc_col_idx = None
    pre_col_idx = None
    header_row_idx = None
    
    # Inspect first 10 rows to find headers
    for row_idx, row in enumerate(sheet.iter_rows(max_row=10, values_only=True), 1):
        found_in_row = {}
        for col_idx, val in enumerate(row, 1):
            if val:
                val_clean = str(val).strip().lower().rstrip(":")
                if val_clean in step_headers or "test step" in val_clean or "test steps" in val_clean:
                    found_in_row['step'] = col_idx
                elif val_clean in desc_headers or "test case name" in val_clean or "test description" in val_clean:
                    found_in_row['desc'] = col_idx
                elif val_clean in precondition_headers or "precondition" in val_clean or "prerequisite" in val_clean or val_clean == "setup":
                    found_in_row['pre'] = col_idx
        if 'step' in found_in_row:
            step_col_idx = found_in_row['step']
            desc_col_idx = found_in_row.get('desc', desc_col_idx)
            pre_col_idx = found_in_row.get('pre', pre_col_idx)
            header_row_idx = row_idx
            break
        else:
            if 'desc' in found_in_row and desc_col_idx is None:
                desc_col_idx = found_in_row['desc']
            if 'pre' in found_in_row and pre_col_idx is None:
                pre_col_idx = found_in_row['pre']
            
    test_cases = []
    
    # Section header regex (to skip labels like 'Preconditions:' or 'Test Steps:' inside step cells)
    section_header_re = re.compile(r'^(?i:preconditions?|prerequisites?|pre-conditions?|pre-requisites?|test\s*steps?|steps?|setup):?\s*$')

    # Helper to clean individual steps
    def clean_step(s: str) -> str:
        s_clean = s.strip()
        if section_header_re.match(s_clean):
            return ""
        s_clean = re.sub(r'^(?i:step\s+\d+[\s\.:\-]*)?[\d\-\*\•\.\)\(]*\s*', '', s_clean).strip()
        if section_header_re.match(s_clean):
            return ""
        return s_clean
        
    def get_steps_from_value(val) -> list:
        if val is None:
            return []
        val_str = str(val).strip()
        if not val_str or val_str.startswith("#"):
            return []
            
        steps = []
        lines = val_str.splitlines()
        for line in lines:
            line_clean = clean_step(line)
            if line_clean and not line_clean.startswith("#"):
                steps.append(line_clean)
        return steps

    # If steps column was identified
    if step_col_idx is not None:
        start_row = header_row_idx + 1
        for r in range(start_row, sheet.max_row + 1):
            steps_val = sheet.cell(row=r, column=step_col_idx).value
            row_steps = get_steps_from_value(steps_val)
            if not row_steps:
                continue
                
            pre_steps = []
            if pre_col_idx is not None:
                pre_val = sheet.cell(row=r, column=pre_col_idx).value
                pre_steps = get_steps_from_value(pre_val)
                
            desc_val = None
            if desc_col_idx is not None:
                desc_val = sheet.cell(row=r, column=desc_col_idx).value
                
            if desc_val:
                desc_str = str(desc_val).strip()
            else:
                desc_str = f"TestCase_{r - start_row + 1}"
                
            test_cases.append({
                "name": sanitize_class_name(desc_str),
                "description": desc_str,
                "preconditions": pre_steps,
                "steps": pre_steps + row_steps,
                "source": f"{os.path.basename(file_path)}: Row {r}"
            })
    else:
        # Fallback: scan first 5 columns to find the first one that has text values in first 10 rows
        fallback_col_idx = 1
        for col_idx in range(1, min(6, sheet.max_column + 1) if sheet.max_column else 6):
            has_text = False
            for row in sheet.iter_rows(max_row=10, min_col=col_idx, max_col=col_idx, values_only=True):
                val = row[0]
                if val and isinstance(val, str) and len(val.strip()) > 3:
                    has_text = True
                    break
            if has_text:
                fallback_col_idx = col_idx
                break
                
        for r in range(1, sheet.max_row + 1):
            val = sheet.cell(row=r, column=fallback_col_idx).value
            if val is not None:
                val_str = str(val).strip()
                if val_str.lower() in step_headers:
                    continue
                row_steps = get_steps_from_value(val)
                if row_steps:
                    test_cases.append({
                        "name": f"TestCase_{r}",
                        "description": f"TestCase_{r}",
                        "preconditions": [],
                        "steps": row_steps,
                        "source": f"{os.path.basename(file_path)}: Row {r}"
                    })
                    
    wb.close()
    return test_cases

def load_all_test_cases(tc_paths: list) -> list:
    """Load all test cases from text files or Excel spreadsheets."""
    import re
    test_cases = []
    for path in tc_paths:
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            logger.error(f"Error: Testcase file does not exist at '{abs_path}'")
            sys.exit(1)
            
        basename = os.path.basename(abs_path)
        name_no_ext, ext = os.path.splitext(basename)
        
        if ext.lower() in [".xlsx", ".xls"]:
            sheet_cases = parse_excel_test_cases(abs_path)
            test_cases.extend(sheet_cases)
        else:
            steps = []
            preconditions = []
            current_section = "steps"
            with open(abs_path, "r", encoding="utf-8") as f:
                for line in f:
                    line_clean = line.strip()
                    if not line_clean or line_clean.startswith("#"):
                        continue
                    # Check for section headers (e.g. Preconditions:, Steps:)
                    if re.match(r'^(?i:preconditions?|prerequisites?|pre-conditions?|pre-requisites?|setup):?\s*$', line_clean):
                        current_section = "preconditions"
                        continue
                    if re.match(r'^(?i:test\s*steps?|steps?|actions?):?\s*$', line_clean):
                        current_section = "steps"
                        continue
                        
                    clean_s = re.sub(r'^(?i:step\s+\d+[\s\.:\-]*)?[\d\-\*\•\.\)\(]*\s*', '', line_clean).strip()
                    if clean_s and not clean_s.startswith("#"):
                        if current_section == "preconditions":
                            preconditions.append(clean_s)
                        else:
                            steps.append(clean_s)
                            
            all_steps = preconditions + steps
            if all_steps:
                test_cases.append({
                    "name": sanitize_class_name(name_no_ext),
                    "description": name_no_ext,
                    "preconditions": preconditions,
                    "steps": all_steps,
                    "source": basename
                })
    return test_cases

def run_crawl_search(args, agent):
    """
    Run crawler search mode:
    1. Setup browser session.
    2. Navigate to start URL.
    3. If --testcase is provided, run those setup/login steps first.
    4. Start recursive crawling search from the current URL.
    5. Output HTML crawl report and update generated TestNG Java code.
    """
    from web_reporter import WebCrawlReporter
    import time
    import re
    
    playwright_instance = None
    browser = None
    page = None
    
    try:
        # 1. Setup browser
        playwright_instance, browser, page = web_driver_utils.setup_browser(headless=args.headless)
        
        # 2. Navigate to starting page
        logger.info(f"Navigating browser to: {args.url}")
        page.goto(args.url)
        
        # 3. Perform pre-crawl setup/login steps if provided
        if args.testcase:
            tc_files = [x.strip() for x in args.testcase.split(",") if x.strip()]
            test_cases = load_all_test_cases(tc_files)
            if test_cases:
                logger.info(f"Executing {len(test_cases)} setup/login test cases before starting crawl...")
                for tc in test_cases:
                    logger.info(f"Running setup: {tc['name']}")
                    success, logs = agent.execute_testcase(page, tc["steps"])
                    if not success:
                        logger.error(f"Setup steps failed for test case '{tc['name']}'. Crawling may run without authentication.")
        
        # 4. Crawl same-domain pages recursively
        from urllib.parse import urlparse
        start_url = page.url
        logger.info(f"Starting site crawl from URL: {start_url}")
        
        visited = set()
        queue = [start_url]
        crawl_results = []
        found_urls = []
        
        while queue and len(visited) < args.crawl_max_pages:
            current_url = queue.pop(0)
            if current_url in visited:
                continue
                
            logger.info(f"Crawling page {len(visited) + 1} of {args.crawl_max_pages}: {current_url}")
            visited.add(current_url)
            
            page_result = {
                "url": current_url,
                "title": "",
                "screenshot": "",
                "found": False,
                "error": None,
                "status": "success"
            }
            
            try:
                page.goto(current_url)
                web_driver_utils.wait_for_page_load(page)
                
                page_result["title"] = page.title()
                page_result["screenshot"] = web_driver_utils.get_screenshot_b64(page)
                
                # Check for word in raw DOM HTML
                html = page.content()
                if args.crawl_search.lower() in html.lower():
                    page_result["found"] = True
                    found_urls.append(current_url)
                    logger.info(f"🎯 FOUND match on page: {current_url}")
                
                # Extract links to queue
                links = web_driver_utils.extract_same_domain_links(page, start_url)
                for link in links:
                    if link not in visited and link not in queue:
                        queue.append(link)
                        
            except Exception as e:
                logger.error(f"Error crawling page '{current_url}': {e}")
                page_result["status"] = "failed"
                page_result["error"] = str(e)
                try:
                    page_result["screenshot"] = web_driver_utils.get_screenshot_b64(page)
                except Exception:
                    pass
            
            crawl_results.append(page_result)
            
        # 5. Generate HTML crawl report
        report_dir = os.path.dirname(os.path.abspath(args.output_report))
        report_filepath = os.path.join(report_dir, "web_crawl_report.html")
        reporter = WebCrawlReporter(target_url=start_url, search_word=args.crawl_search)
        report_file = reporter.generate_report(crawl_results, report_filepath)
        logger.info(f"✓ Crawling report generated at: {report_file}")
        
        # 6. Generate compiled Java TestNG tests matching each found URL
        if found_urls:
            java_statements = []
            for idx, url in enumerate(found_urls, 1):
                java_statements.append(f'        // Check page {idx} containing the target word')
                java_statements.append(f'        page.navigate("{url}");')
                java_statements.append(f'        org.testng.Assert.assertTrue(page.content().toLowerCase().contains("{agent._escape_java(args.crawl_search).lower()}"));')
                java_statements.append('')
            
            # Write a single method for PlaywrightAutomation
            method_template = f"""    @Test(description = "Verify presence of '{agent._escape_java(args.crawl_search)}' on crawled pages")
    public void testCrawlSearchWord() {{
        System.out.println("Executing Crawled URL Verifications...");
{chr(10).join(java_statements)}
    }}"""
            
            java_filename = os.path.basename(args.output_java)
            class_name, _ = os.path.splitext(java_filename)
            class_name = re.sub(r'[^a-zA-Z0-9_]', '', class_name)
            if class_name and class_name[0].isdigit():
                class_name = "TC" + class_name
            if not class_name:
                class_name = "PlaywrightAutomation"
                
            testng_code = f"""package com.example;

import com.microsoft.playwright.*;
import org.testng.annotations.*;
import org.testng.Assert;

public class {class_name} {{
    private Playwright playwright;
    private Browser browser;
    private BrowserContext context;
    private Page page;

    @BeforeClass
    public void setUp() {{
        playwright = Playwright.create();
        browser = playwright.chromium().launch(new BrowserType.LaunchOptions()
            .setHeadless(true)
            .setSlowMo(500));
    }}

    @BeforeMethod
    public void setUpMethod() {{
        context = browser.newContext(new Browser.NewContextOptions()
            .setViewportSize(1280, 800)
            .setIgnoreHTTPSErrors(true));
        page = context.newPage();
    }}

{method_template}

    @AfterMethod
    public void tearDownMethod() {{
        if (context != null) {{
            context.close();
        }}
    }}

    @AfterClass
    public void tearDown() {{
        if (browser != null) {{
            browser.close();
        }}
        if (playwright != null) {{
            playwright.close();
        }}
    }}
}}
"""
            with open(args.output_java, "w", encoding="utf-8") as f:
                f.write(testng_code)
            logger.info(f"✓ Generated crawling verification Java code written to: {args.output_java}")
            
        logger.info(f"\n==================================================")
        logger.info(f"CRAWLER SEARCH SUMMARY")
        logger.info(f"==================================================")
        logger.info(f"  * Total pages crawled: {len(visited)}")
        logger.info(f"  * Matches found:       {len(found_urls)}")
        for url in found_urls:
            logger.info(f"    - {url}")
        logger.info(f"==================================================")
        
    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        if playwright_instance:
            try:
                playwright_instance.stop()
            except Exception:
                pass

def main():
    parser = argparse.ArgumentParser(description="WebAgent - Autonomous Web Testcase Playwright Agent")
    parser.add_argument("--url", required=True, help="Initial target URL to navigate to")
    parser.add_argument("--testcase", help="Path to text or Excel testcase files (comma-separated list)")
    parser.add_argument("--output-java", default="PlaywrightAutomation.java", help="Path to write the generated Playwright Java class file")
    parser.add_argument("--output-report", default="web_report.html", help="Path to write the visual HTML report")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode (default: False)")
    parser.add_argument("--model", default="gpt-4o", help="OpenAI Model name (default: gpt-4o)")
    parser.add_argument("--crawl-search", help="Target word to recursively search for across the website DOM")
    parser.add_argument("--crawl-max-pages", type=int, default=20, help="Maximum number of pages to crawl (default: 20)")
    
    args = parser.parse_args()

    if not args.testcase and not args.crawl_search:
        parser.error("either --testcase or --crawl-search must be provided")

    # Initialize the WebAgent
    agent = WebAgent(model=args.model)

    if args.crawl_search:
        run_crawl_search(args, agent)
        return

    # Split input comma-separated files
    tc_files = [x.strip() for x in args.testcase.split(",") if x.strip()]
    
    # Load all test cases
    test_cases = load_all_test_cases(tc_files)
    
    if not test_cases:
        logger.error("Error: No valid test cases found.")
        sys.exit(1)
        
    logger.info(f"Loaded {len(test_cases)} test case(s) for execution.")
    
    overall_success = True
    results = []
    test_cases_runs = []
    
    for tc_idx, tc in enumerate(test_cases, 1):
        logger.info(f"\n==================================================")
        logger.info(f"RUNNING TEST CASE {tc_idx} of {len(test_cases)}: {tc['name']}")
        logger.info(f"Source: {tc['source']}")
        if tc.get("preconditions"):
            logger.info(f"Preconditions ({len(tc['preconditions'])}):")
            for idx, s in enumerate(tc["preconditions"], 1):
                logger.info(f"  [Precondition {idx}] {s}")
        logger.info(f"Steps to Execute ({len(tc['steps'])}):")
        for idx, s in enumerate(tc["steps"], 1):
            logger.info(f"  {idx}. {s}")
        logger.info(f"==================================================")
        
        playwright_instance = None
        browser = None
        page = None
        
        try:
            # Initialize browser & context
            playwright_instance, browser, page = web_driver_utils.setup_browser(headless=args.headless)
            
            # Navigate to initial target URL
            logger.info(f"Navigating to initial target URL: {args.url}")
            page.goto(args.url)
            
            # Execute test case
            success, logs = agent.execute_testcase(page, tc["steps"])
            
            test_cases_runs.append({
                "name": tc["name"],
                "description": tc.get("description", tc["name"]),
                "logs": logs
            })
            
            # Generate Playwright Java code (for the HTML report)
            java_code = agent.generate_java_code(logs, tc["name"], initial_url=args.url)
            
            report_dir = os.path.dirname(os.path.abspath(args.output_report))
            report_filepath = os.path.join(report_dir, f"web_report_{tc['name']}.html")
            
            # Generate HTML report
            reporter = WebHTMLReporter(target_url=args.url, testcase_name=tc["name"])
            report_file = reporter.generate_report(logs, java_code, report_filepath)
            logger.info(f"✓ Automated visual HTML report generated at: {report_file}")
            
            if success:
                logger.info(f"🎉 Test Case '{tc['name']}' executed successfully!")
                results.append((tc["name"], "PASSED", None))
            else:
                logger.warning(f"⚠️ Test Case '{tc['name']}' encountered failures.")
                results.append((tc["name"], "FAILED", "Step failures encountered"))
                overall_success = False
                
        except Exception as e:
            logger.error(f"Error running test case '{tc['name']}': {e}", exc_info=True)
            results.append((tc["name"], "ERROR", str(e)))
            overall_success = False
            
        finally:
            # Clean up browser session
            logger.info("Cleaning up browser sessions...")
            if browser:
                try:
                    browser.close()
                except Exception as e:
                    logger.error(f"Error closing browser: {e}")
            if playwright_instance:
                try:
                    playwright_instance.stop()
                except Exception as e:
                    logger.error(f"Error stopping Playwright: {e}")
            logger.info("Playwright session terminated.")
            
    # Generate unified TestNG Java code at the end
    if test_cases_runs:
        java_filename = os.path.basename(args.output_java)
        class_name, _ = os.path.splitext(java_filename)
        import re
        class_name = re.sub(r'[^a-zA-Z0-9_]', '', class_name)
        if class_name and class_name[0].isdigit():
            class_name = "TC" + class_name
        if not class_name:
            class_name = "PlaywrightAutomation"
        
        testng_code = agent.generate_testng_java_code(test_cases_runs, class_name=class_name, initial_url=args.url)
        
        output_dir = os.path.dirname(os.path.abspath(args.output_java))
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
        with open(args.output_java, "w", encoding="utf-8") as f:
            f.write(testng_code)
        logger.info(f"✓ Generated TestNG Playwright Java code written to: {args.output_java}")
        
    # Log overall execution summary
    logger.info(f"\n==================================================")
    logger.info(f"EXECUTION SUMMARY")
    logger.info(f"==================================================")
    for name, status, err in results:
        status_str = f"[{status}]"
        err_str = f" - Error: {err}" if err else ""
        logger.info(f"  * {name:<35} {status_str:<10}{err_str}")
    logger.info(f"==================================================")
    
    if overall_success:
        logger.info("🎉 All test cases completed successfully!")
    else:
        logger.warning("⚠️ Some test cases encountered failures or errors.")
        sys.exit(1)

if __name__ == "__main__":
    main()
