import os
import sys
import logging
import asyncio
from mcp.server.stdio import stdio_server
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.types as types
from web_agent import WebAgent
from web_reporter import WebHTMLReporter
import web_driver_utils

# Configure logging to stderr/file only to prevent stdout pollution (which corrupts standard input/output JSON-RPC communication)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler("web_mcp_server.log", mode="w")
    ]
)
logger = logging.getLogger("WebAgent.mcp_server")

server = Server("web-agent-mcp")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    Exposes autonomous QA WebAgent tools to the client.
    """
    return [
        types.Tool(
            name="run_autonomous_test",
            description=(
                "Runs a set of natural-language test steps on a web page autonomously using an AI/Heuristics agent, "
                "capturing screenshots, verifying actions, and generating visual HTML reports and Playwright automation code."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Starting target URL to navigate to (e.g., login or homepage URL)."
                    },
                    "steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Sequential list of manual test steps to perform (e.g., ['Type \"username\" in username input', 'Click login button'])."
                    },
                    "testcase_name": {
                        "type": "string",
                        "description": "Optional name for the generated TestNG Java class and reports. Defaults to 'PlaywrightMCPCase'.",
                        "default": "PlaywrightMCPCase"
                    },
                    "headless": {
                        "type": "boolean",
                        "description": "Whether to run the browser in headless mode. Defaults to True.",
                        "default": True
                    }
                },
                "required": ["url", "steps"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Execute the tool and return the output status and generated code path to the LLM.
    """
    if name != "run_autonomous_test":
        raise ValueError(f"Tool '{name}' not found.")
        
    url = arguments.get("url")
    steps = arguments.get("steps", [])
    testcase_name = arguments.get("testcase_name", "PlaywrightMCPCase")
    headless = arguments.get("headless", True)
    
    if not url or not steps:
        return [types.TextContent(type="text", text="Error: Both 'url' and 'steps' are required.")]

    logger.info(f"Starting MCP run_autonomous_test for URL: {url} with {len(steps)} steps.")
    
    # Initialize the WebAgent (uses env OPENAI_API_KEY if present, otherwise heuristics)
    agent = WebAgent()
    
    playwright_instance = None
    browser = None
    page = None
    
    try:
        playwright_instance, browser, page = web_driver_utils.setup_browser(headless=headless)
        
        logger.info(f"Navigating browser to: {url}")
        page.goto(url)
        
        logger.info("Executing test steps...")
        success, logs = agent.execute_testcase(page, steps)
        
        logger.info("Generating automation code...")
        java_code = agent.generate_java_code(logs, testcase_name, initial_url=url)
        
        # Prepare HTML report file name
        report_filename = f"web_report_{testcase_name}.html"
        logger.info(f"Generating visual report: {report_filename}")
        reporter = WebHTMLReporter(target_url=url, testcase_name=testcase_name)
        report_file = reporter.generate_report(logs, java_code, report_filename)
        
        status = "PASSED" if success else "FAILED"
        
        result_message = (
            f"🎯 Execution Status: {status}\n"
            f"📊 Visual HTML Report Generated: {report_file}\n"
            f"☕ Generated Playwright Java Code is ready.\n\n"
            f"### Generated Playwright Java Code:\n```java\n{java_code}\n```"
        )
        
        return [types.TextContent(type="text", text=result_message)]
        
    except Exception as e:
        logger.error(f"Error during autonomous run: {e}", exc_info=True)
        return [types.TextContent(type="text", text=f"Error executing autonomous test: {str(e)}")]
        
    finally:
        logger.info("Cleaning up browser resources...")
        if browser:
            try:
                browser.close()
            except Exception as ex:
                logger.error(f"Error closing browser: {ex}")
        if playwright_instance:
            try:
                playwright_instance.stop()
            except Exception as ex:
                logger.error(f"Error stopping Playwright: {ex}")
        logger.info("Browser resources cleaned up.")

async def main():
    logger.info("Initializing WebAgent MCP Stdio Server...")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="web-agent-mcp",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

def run():
    asyncio.run(main())

if __name__ == "__main__":
    run()

