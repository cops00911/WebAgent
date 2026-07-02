import os
import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger("WebAgent.reporter")

class WebHTMLReporter:
    def __init__(self, target_url: str, testcase_name: str):
        self.target_url = target_url
        self.testcase_name = testcase_name

    def generate_report(self, logs: List[Dict[str, Any]], java_code: str, output_path: str = "web_report.html") -> str:
        """
        Generate a gorgeous, responsive, single-page HTML test report.
        """
        logger.info(f"Generating HTML report at '{output_path}'...")
        
        # Calculate summary metrics
        total_steps = len(logs)
        successful_steps = sum(1 for log in logs if log["status"] == "success")
        failed_steps = total_steps - successful_steps
        status_text = "PASSED" if failed_steps == 0 else "FAILED"
        status_badge_class = "badge-success" if failed_steps == 0 else "badge-danger"
        
        # Generate steps HTML
        steps_html = []
        for log in logs:
            step_idx = log["step_index"]
            step_text = log["step_text"]
            action = log["action"]
            selector = log["selector"] or "N/A"
            val = log["value"] or "N/A"
            reasoning = log["reasoning"] or "No reasoning provided."
            status = log["status"]
            error = log["error"]
            
            # Embed screenshots directly as base64 images
            img_before_src = f"data:image/png;base64,{log['screenshot_before']}" if log['screenshot_before'] else ""
            img_after_src = f"data:image/png;base64,{log['screenshot_after']}" if log['screenshot_after'] else ""
            
            step_status_class = "step-success" if status == "success" else "step-failed"
            status_dot_class = "dot-success" if status == "success" else "dot-danger"
            
            error_html = f'<div class="error-box"><strong>Error:</strong> {error}</div>' if error else ""
            
            # Action badge
            action_badge_class = f"badge-{action}"
            
            # Screenshot comparison HTML
            screenshot_container = ""
            if img_before_src or img_after_src:
                screenshot_container = f"""
                <div class="screenshots-container">
                    <div class="screenshot-block">
                        <span class="screenshot-label">Before Action</span>
                        <div class="screenshot-wrapper">
                            <img src="{img_before_src}" alt="Screenshot Before" onclick="openModal('{img_before_src}')" />
                        </div>
                    </div>
                    <div class="screenshot-block">
                        <span class="screenshot-label">After Action</span>
                        <div class="screenshot-wrapper">
                            <img src="{img_after_src}" alt="Screenshot After" onclick="openModal('{img_after_src}')" />
                        </div>
                    </div>
                </div>
                """

            steps_html.append(f"""
            <div class="step-card {step_status_class}">
                <div class="step-header">
                    <span class="status-dot {status_dot_class}"></span>
                    <span class="step-title">Step {step_idx}: {step_text}</span>
                    <span class="badge {action_badge_class}">{action.upper()}</span>
                </div>
                <div class="step-body">
                    <p class="reasoning"><strong>Reasoning:</strong> {reasoning}</p>
                    <div class="meta-grid">
                        <div><strong>Target Selector:</strong> <code>{selector}</code></div>
                        <div><strong>Input Value:</strong> <code>{val}</code></div>
                    </div>
                    {error_html}
                    {screenshot_container}
                </div>
            </div>
            """)

        steps_rendered = "\n".join(steps_html)
        
        # Escape Java code for HTML output
        escaped_java = (
            java_code.replace("&", "&amp;")
                     .replace("<", "&lt;")
                     .replace(">", "&gt;")
        )

        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WebAgent - Playwright Execution Report</title>
    <!-- Outfit Font & PrismJS for Java code highlight -->
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css" rel="stylesheet" />
    <style>
        :root {{
            --bg-primary: #0b0f19;
            --bg-secondary: #131b2e;
            --bg-tertiary: #1e2942;
            --text-primary: #f3f4f6;
            --text-secondary: #9ca3af;
            --primary: #6366f1;
            --primary-hover: #4f46e5;
            --success: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --border-color: rgba(255, 255, 255, 0.08);
            --card-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            padding: 40px 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        /* Header Card */
        .header-card {{
            background: linear-gradient(135deg, var(--bg-secondary) 0%, rgba(19, 27, 46, 0.8) 100%);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 40px;
            box-shadow: var(--card-shadow);
            backdrop-filter: blur(10px);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 20px;
        }}

        .header-info h1 {{
            font-size: 2.2rem;
            font-weight: 700;
            background: linear-gradient(to right, #a5b4fc, #818cf8, #6366f1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }}

        .header-info p {{
            color: var(--text-secondary);
            font-size: 1.1rem;
        }}

        .header-info a {{
            color: var(--primary);
            text-decoration: none;
        }}

        .header-info a:hover {{
            text-decoration: underline;
        }}

        .header-metrics {{
            display: flex;
            align-items: center;
            gap: 20px;
        }}

        .metric-badge {{
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            padding: 12px 24px;
            border-radius: 12px;
            text-align: center;
        }}

        .metric-badge span {{
            display: block;
            font-size: 0.85rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 4px;
        }}

        .metric-badge strong {{
            font-size: 1.4rem;
            font-weight: 700;
        }}

        .badge {{
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 600;
            letter-spacing: 0.05em;
            display: inline-block;
        }}

        .badge-success {{
            background-color: rgba(16, 185, 129, 0.15);
            color: var(--success);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }}

        .badge-danger {{
            background-color: rgba(239, 68, 68, 0.15);
            color: var(--danger);
            border: 1px solid rgba(239, 68, 68, 0.3);
        }}

        /* Badge action types */
        .badge-navigate {{ background-color: rgba(99, 102, 241, 0.15); color: #818cf8; border: 1px solid rgba(99, 102, 241, 0.3); }}
        .badge-click {{ background-color: rgba(16, 185, 129, 0.15); color: var(--success); border: 1px solid rgba(16, 185, 129, 0.3); }}
        .badge-fill {{ background-color: rgba(245, 158, 11, 0.15); color: var(--warning); border: 1px solid rgba(245, 158, 11, 0.3); }}
        .badge-select {{ background-color: rgba(14, 165, 233, 0.15); color: #38bdf8; border: 1px solid rgba(14, 165, 233, 0.3); }}
        .badge-check {{ background-color: rgba(236, 72, 153, 0.15); color: #f472b6; border: 1px solid rgba(236, 72, 153, 0.3); }}
        .badge-done {{ background-color: rgba(107, 114, 128, 0.15); color: #9ca3af; border: 1px solid rgba(107, 114, 128, 0.3); }}

        /* Main Workspace Grid */
        .workspace-grid {{
            display: grid;
            grid-template-columns: 1.2fr 1fr;
            gap: 40px;
        }}

        @media (max-width: 1100px) {{
            .workspace-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        /* Left side: Step List */
        .steps-section-title {{
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .step-card {{
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: var(--card-shadow);
            transition: transform 0.2s ease, border-color 0.2s ease;
        }}

        .step-card:hover {{
            transform: translateY(-2px);
        }}

        .step-success {{
            border-left: 4px solid var(--success);
        }}

        .step-failed {{
            border-left: 4px solid var(--danger);
        }}

        .step-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 16px;
            position: relative;
        }}

        .status-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }}

        .dot-success {{ background-color: var(--success); box-shadow: 0 0 10px var(--success); }}
        .dot-danger {{ background-color: var(--danger); box-shadow: 0 0 10px var(--danger); }}

        .step-title {{
            font-size: 1.15rem;
            font-weight: 600;
            color: var(--text-primary);
            flex-grow: 1;
        }}

        .step-body {{
            padding-left: 22px;
        }}

        .reasoning {{
            color: var(--text-secondary);
            font-size: 0.95rem;
            margin-bottom: 16px;
        }}

        .meta-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.05);
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 0.9rem;
            margin-bottom: 20px;
        }}

        .meta-grid code {{
            font-family: 'JetBrains Mono', monospace;
            color: #818cf8;
            word-break: break-all;
        }}

        .error-box {{
            background-color: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.2);
            color: #fca5a5;
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 0.9rem;
            margin-bottom: 20px;
            font-family: 'JetBrains Mono', monospace;
        }}

        /* Screenshots */
        .screenshots-container {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }}

        .screenshot-block {{
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}

        .screenshot-label {{
            font-size: 0.8rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .screenshot-wrapper {{
            border: 1px solid var(--border-color);
            border-radius: 8px;
            overflow: hidden;
            background: #000;
            cursor: pointer;
            aspect-ratio: 16/10;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .screenshot-wrapper img {{
            width: 100%;
            height: auto;
            max-height: 100%;
            object-fit: contain;
            transition: transform 0.2s ease;
        }}

        .screenshot-wrapper:hover img {{
            transform: scale(1.03);
        }}

        /* Code Pane Section */
        .code-section {{
            position: sticky;
            top: 40px;
            max-height: calc(100vh - 80px);
            display: flex;
            flex-direction: column;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            box-shadow: var(--card-shadow);
            overflow: hidden;
        }}

        .code-header {{
            padding: 20px 24px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .code-header h2 {{
            font-size: 1.25rem;
            font-weight: 600;
        }}

        .copy-btn {{
            background: var(--primary);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 8px;
            font-family: inherit;
            font-weight: 500;
            font-size: 0.85rem;
            cursor: pointer;
            transition: background 0.2s ease, transform 0.1s ease;
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .copy-btn:hover {{
            background: var(--primary-hover);
        }}

        .copy-btn:active {{
            transform: scale(0.97);
        }}

        .code-body {{
            flex-grow: 1;
            overflow: auto;
            padding: 0;
        }}

        pre[class*="language-"] {{
            margin: 0 !important;
            border-radius: 0 !important;
            background: transparent !important;
            font-size: 0.9rem !important;
            font-family: 'JetBrains Mono', monospace !important;
        }}

        /* Lightbox Modal */
        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(5, 7, 12, 0.95);
            align-items: center;
            justify-content: center;
        }}

        .modal-content-wrapper {{
            position: relative;
            max-width: 90%;
            max-height: 90%;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            overflow: hidden;
        }}

        .modal img {{
            display: block;
            max-width: 100%;
            max-height: 85vh;
            object-fit: contain;
        }}

        .close-modal {{
            position: absolute;
            top: 15px;
            right: 20px;
            color: #fff;
            font-size: 30px;
            font-weight: bold;
            cursor: pointer;
            background: rgba(0,0,0,0.5);
            width: 44px;
            height: 44px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background 0.2s ease;
        }}

        .close-modal:hover {{
            background: rgba(255, 255, 255, 0.1);
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header-card">
            <div class="header-info">
                <h1>WebAgent Automation Report</h1>
                <p>Target Application URL: <a href="{self.target_url}" target="_blank">{self.target_url}</a></p>
                <p style="margin-top: 5px; font-size: 0.9rem; color: var(--text-secondary);">Test Case: <strong>{self.testcase_name}</strong></p>
            </div>
            <div class="header-metrics">
                <div class="metric-badge">
                    <span>Result Status</span>
                    <strong class="badge {status_badge_class}">{status_text}</strong>
                </div>
                <div class="metric-badge">
                    <span>Total Steps</span>
                    <strong>{total_steps}</strong>
                </div>
                <div class="metric-badge">
                    <span>Success Rate</span>
                    <strong>{int((successful_steps/total_steps)*100) if total_steps else 100}%</strong>
                </div>
            </div>
        </div>

        <!-- Main Workspace -->
        <div class="workspace-grid">
            <!-- Left Pane: Step Timeline -->
            <div>
                <h2 class="steps-section-title">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-activity"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                    Execution Timeline
                </h2>
                {steps_rendered}
            </div>

            <!-- Right Pane: Playwright Java Code Output -->
            <div>
                <div class="code-section">
                    <div class="code-header">
                        <h2>Playwright Java Code</h2>
                        <button class="copy-btn" onclick="copyCode()">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-clipboard"><rect width="8" height="4" x="8" y="2" rx="1" ry="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/></svg>
                            <span id="copy-btn-text">Copy Code</span>
                        </button>
                    </div>
                    <div class="code-body">
                        <pre><code class="language-java" id="java-code-block">{escaped_java}</code></pre>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Lightbox Modal -->
    <div id="screenshotModal" class="modal" onclick="closeModal()">
        <span class="close-modal">&times;</span>
        <div class="modal-content-wrapper" onclick="event.stopPropagation()">
            <img id="modalImage" src="" alt="Fullscreen Screenshot">
        </div>
    </div>

    <!-- Highlight Script -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-core.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/plugins/autoloader/prism-autoloader.min.js"></script>
    
    <script>
        function openModal(imgSrc) {{
            const modal = document.getElementById("screenshotModal");
            const modalImg = document.getElementById("modalImage");
            modal.style.display = "flex";
            modalImg.src = imgSrc;
        }}

        function closeModal() {{
            document.getElementById("screenshotModal").style.display = "none";
        }}

        function copyCode() {{
            const codeText = document.getElementById("java-code-block").textContent;
            navigator.clipboard.writeText(codeText).then(() => {{
                const btnText = document.getElementById("copy-btn-text");
                btnText.textContent = "Copied!";
                setTimeout(() => {{
                    btnText.textContent = "Copy Code";
                }}, 2000);
            }}).catch(err => {{
                console.error('Could not copy text: ', err);
            }});
        }}
        
        // Escape close modal with Esc key
        document.addEventListener('keydown', function(event) {{
            if (event.key === "Escape") {{
                closeModal();
            }}
        }});
    </script>
</body>
</html>
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_template)
            
        return os.path.abspath(output_path)
