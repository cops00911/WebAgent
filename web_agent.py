import os
import json
import logging
import time
import random
import re
from typing import Dict, Any, List, Tuple
from openai import OpenAI
import web_driver_utils

logger = logging.getLogger("WebAgent.agent")

def generate_mock_data(data_type: str, label_text: str = "") -> str:
    """
    Generate realistic data based on detected data type constraints.
    """
    first_names = ["John", "David", "Sarah", "Emma", "Robert", "Emily", "Michael", "Sophia", "James", "Olivia"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson", "Anderson", "Taylor"]
    companies = ["Tapral Partners", "Vertex Tech", "Apex Group Solutions", "Global Connect Corp", "Quantum Alliance"]
    cities = ["San Francisco", "New York", "Chicago", "Austin", "Seattle"]
    states = ["California", "New York", "Illinois", "Texas", "Washington"]
    countries = ["United States", "Canada", "United Kingdom", "India", "Australia"]
    designations = ["Manager", "Director", "Software Engineer", "Operations Lead", "VP of Sales"]
    
    dt = data_type.lower()
    if dt == "email":
        name = f"{random.choice(first_names).lower()}.{random.choice(last_names).lower()}{random.randint(10, 99)}"
        return f"{name}@example.com"
    elif dt in ["phone", "whatsapp"]:
        return f"9{random.randint(100000000, 999999999)}" # Standard 10-digit number
    elif dt == "password":
        return f"SecurePass{random.randint(100, 999)}!"
    elif dt == "firstname":
        return random.choice(first_names)
    elif dt == "lastname":
        return random.choice(last_names)
    elif dt == "designation":
        return random.choice(designations)
    elif dt == "company":
        return random.choice(companies)
    elif dt == "domain":
        return f"portal-{random.randint(100, 999)}"
    elif dt == "website":
        return f"https://www.{random.choice(companies).lower().replace(' ', '')}.com"
    elif dt == "tax":
        return f"TX-{random.randint(10, 99)}-{random.randint(1000000, 9999999)}"
    elif dt == "license":
        return f"LIC-{random.randint(100000, 999999)}"
    elif dt == "landmark":
        return f"Opposite {random.choice(cities)} Central Park"
    elif dt == "pobox":
        return f"P.O. Box {random.randint(1000, 9999)}"
    elif dt == "description":
        return "This is a sample onboarding partner record generated automatically for test automation purposes."
    elif dt == "address":
        return f"{random.randint(100, 999)} {random.choice(['Tech Boulevard', 'Innovation Way', 'Enterprise Road', 'Business Dr'])}"
    elif dt == "city":
        return random.choice(cities)
    elif dt == "state":
        return random.choice(states)
    elif dt == "country":
        return random.choice(countries)
    elif dt == "name":
        return f"{random.choice(first_names)} {random.choice(last_names)}"
    elif dt == "price":
        return f"{random.randint(10, 150)}.00"
    elif dt in ["number", "range"]:
        return str(random.randint(10, 99))
    elif dt == "zipcode":
        return f"{random.randint(10000, 99999)}"
    elif dt == "date":
        year = random.randint(1980, 2005)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        return f"{year}-{month:02d}-{day:02d}"
    elif dt == "time":
        return f"{random.randint(8, 17):02d}:{random.choice([0, 30]):02d}"
    elif dt == "datetime-local":
        return f"2026-06-{random.randint(10, 28):02d}T12:00"
    elif dt == "month":
        return f"2026-{random.randint(1, 12):02d}"
    elif dt == "week":
        return f"2026-W{random.randint(10, 50):02d}"
    elif dt == "color":
        return "#" + "".join([random.choice("0123456789abcdef") for _ in range(6)])
    else:
        return "Sample Test Input"


class WebAgent:
    """
    Web Automation Agent that processes natural-language steps, executes actions in a live browser,
    detects fields types, and compiles Playwright Java code.
    """
    def __init__(self, model: str = "gpt-4o", api_key: str = None):
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = None
        if self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key)
                logger.info("OpenAI Client successfully initialized for WebAgent.")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI Client: {e}. Falling back to Heuristics.")
        else:
            logger.info("No OpenAI API key found. WebAgent will use Heuristics Engine.")

    def _escape_java(self, s: str) -> str:
        """Escape backslashes and double quotes for Java string literals."""
        if not s:
            return ""
        return s.replace('\\', '\\\\').replace('"', '\\"')

    def decide_action(self, step_text: str, elements: List[Dict[str, Any]], screenshot_b64: str) -> Dict[str, Any]:
        """
        Choose the next action. Calls LLM if key exists, else Heuristics.
        """
        if self.client:
            try:
                return self._call_openai(step_text, elements, screenshot_b64)
            except Exception as e:
                logger.warning(f"OpenAI decision failed: {e}. Using Heuristics fallback.")
        
        return self._heuristic_decision(step_text, elements)

    def _call_openai(self, step_text: str, elements: List[Dict[str, Any]], screenshot_b64: str) -> Dict[str, Any]:
        system_prompt = (
            "You are an expert AI Web Automation Agent controlling a Playwright browser.\n"
            "Given the user's test step, a list of visible interactive elements, and a screenshot, decide the next action.\n"
            "Format your response strictly as a JSON object:\n"
            "{\n"
            '  "action": "click | fill | select | check | navigate | verify | done",\n'
            '  "element_id": <int element id matching the elements list or null if action is done/navigate/verify>,\n'
            '  "value": "text value to type, option value to select, URL to navigate to, or text/title value to verify",\n'
            '  "reasoning": "brief justification for your decision"\n'
            "}\n"
            "Note: If the field is identified as a mandatory input and no specific value is provided in the instruction, generate a realistic value appropriate for its data_type."
        )

        elements_str = json.dumps([{
            "id": el["id"],
            "tag": el["tagName"],
            "text": el["text"],
            "labelText": el["labelText"],
            "placeholder": el["placeholder"],
            "isMandatory": el["isMandatory"],
            "dataType": el["dataType"],
            "selector": el["selector"]
        } for el in elements], indent=2)

        user_content = [
            {"type": "text", "text": f"CURRENT STEP TO PERFORM: {step_text}\n\nVISIBLE INTERACTIVE ELEMENTS:\n{elements_str}"}
        ]

        if screenshot_b64:
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{screenshot_b64}"
                }
            })

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.0,
            max_tokens=300,
            response_format={"type": "json_object"}
        )

        raw_text = response.choices[0].message.content.strip()
        return json.loads(raw_text)

    def _heuristic_decision(self, step_text: str, elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Regex-based matcher matching test case step against element labels, placeholders, texts.
        """
        step_clean = step_text.lower()
        logger.info(f"Parsing step with Heuristics: '{step_text}'")

        # Check for done
        if "done" in step_clean or "finish" in step_clean or "complete" in step_clean and len(step_clean) < 10:
            return {"action": "done", "element_id": None, "value": "", "reasoning": "Goal completed."}

        # Check for verification / assertion
        verify_title_match = re.search(r"(?:verify|assert)\s+(?:page\s+)?title\s+(?:contains|is|equals?)\s+['\"]?([^'\"]+)['\"]?", step_clean)
        if verify_title_match:
            expected_title = verify_title_match.group(1)
            return {"action": "verify", "element_id": None, "value": f"title:{expected_title}", "reasoning": f"Verifying page title contains: {expected_title}"}
            
        verify_text_match = re.search(r"(?:verify|assert)\s+['\"]?([^'\"]+)['\"]?\s+(?:is visible|exists|is present|on page)", step_clean)
        if verify_text_match:
            expected_text = verify_text_match.group(1)
            return {"action": "verify", "element_id": None, "value": f"text:{expected_text}", "reasoning": f"Verifying page contains text: {expected_text}"}

        if "verify" in step_clean or "assert" in step_clean:
            quoted = re.findall(r"['\"]([^'\"]+)['\"]", step_text)
            val = quoted[0] if quoted else ""
            if "title" in step_clean:
                return {"action": "verify", "element_id": None, "value": f"title:{val}", "reasoning": f"Verifying title contains: {val}"}
            else:
                return {"action": "verify", "element_id": None, "value": f"text:{val}", "reasoning": f"Verifying text presence: {val}"}

        # Check for navigation
        nav_match = re.search(r"(?:navigate to|open|go to|visit)\s+['\"]?([https?://\w\.\-]+[^'\"]*)['\"]?", step_clean)
        if nav_match:
            url = nav_match.group(1)
            # Make sure it has protocol
            if not url.startswith("http"):
                url = "https://" + url
            return {"action": "navigate", "element_id": None, "value": url, "reasoning": f"Navigating to {url}"}

        # Try to resolve target action (default to click if not typed/filled/selected)
        action = "click"
        is_type = any(re.search(rf"\b{x}\b", step_clean) for x in ["type", "fill", "enter", "input", "write"])
        is_select = any(re.search(rf"\b{x}\b", step_clean) for x in ["select", "choose", "dropdown"])
        is_check = any(re.search(rf"\b{x}\b", step_clean) for x in ["check", "uncheck", "toggle"])
        is_hover = any(re.search(rf"\b{x}\b", step_clean) for x in ["hover", "hower", "move mouse to", "mouse over"])
        
        if is_type:
            action = "fill"
        elif is_select:
            action = "select"
        elif is_check:
            action = "check"
        elif is_hover:
            action = "hover"

        # Try to extract target text or value in quotes
        quoted_texts = re.findall(r"['\"]([^'\"]+)['\"]", step_text)
        
        target_query = step_clean
        val = ""
        
        if action == "fill":
            if quoted_texts:
                val = quoted_texts[0]
                target_query = step_clean.replace(val.lower(), "").replace('""', '').replace("''", "")
            else:
                val_match_unquoted = re.search(r"(?:type|enter|fill)\s+(\S+)\s+(?:in|into|to)", step_clean)
                if val_match_unquoted:
                    val = val_match_unquoted.group(1)
                    target_query = step_clean.replace(val, "")
        elif action == "select":
            if len(quoted_texts) >= 2:
                val = quoted_texts[0]
                target_query = quoted_texts[1].lower()
            elif len(quoted_texts) == 1:
                val = quoted_texts[0]
                target_query = step_clean.replace(val.lower(), "").replace('""', '').replace("''", "")
        else:
            if quoted_texts:
                target_query = quoted_texts[0].lower()

        # Match target element
        best_element = None
        best_score = -1

        for el in elements:
            score = 0
            label_lower = el["labelText"].lower()
            text_lower = el["text"].lower()
            place_lower = el["placeholder"].lower()
            name_lower = el["nameAttr"].lower()
            id_lower = el["idAttr"].lower()
            tag_lower = el["tagName"].lower()
            selector_lower = el["selector"].lower()
            class_lower = el.get("classAttr", "").lower()

            # Filter targets by action type
            if action == "fill" and tag_lower not in ["input", "textarea"]:
                continue
            if action == "select" and tag_lower != "select":
                continue

            # Boost score if tag type matches keywords in step text
            role_val = el.get("roleAttr", "") or ""
            if "checkbox" in step_clean and (el.get("typeAttr", "") == "checkbox" or "checkbox" in role_val.lower() or tag_lower == "input"):
                score += 20
            if "button" in step_clean and (tag_lower == "button" or el.get("typeAttr", "") in ["submit", "button"]):
                score += 20

            # Direct string matches
            if target_query == label_lower or target_query == text_lower:
                score += 150
            elif target_query in label_lower or target_query in text_lower:
                score += 50
                
            if target_query == place_lower:
                score += 120
            elif target_query in place_lower:
                score += 40

            # Direct string matches with normalized values (removing underscores/dashes/spaces)
            normalized_query = target_query.replace(" ", "").replace("_", "").replace("-", "")
            normalized_class = class_lower.replace(" ", "").replace("_", "").replace("-", "")
            normalized_selector = selector_lower.replace(" ", "").replace("_", "").replace("-", "")
            normalized_id = id_lower.replace(" ", "").replace("_", "").replace("-", "")
            normalized_name = name_lower.replace(" ", "").replace("_", "").replace("-", "")

            if normalized_query and (normalized_query in normalized_class or normalized_query in normalized_selector or normalized_query in normalized_id or normalized_query in normalized_name):
                score += 100

            # Match individual words in target query
            for word in target_query.split():
                word = word.strip(".,;:?!'\"()[]{}")
                if not word:
                    continue
                # Skip common helper words
                if word in ["click", "on", "type", "fill", "enter", "input", "select", "choose", "the", "button", "link", "field", "text", "in", "into", "checkbox", "radio", "option"]:
                    continue

                if word in label_lower: score += 15
                if word in text_lower: score += 12
                if word in place_lower: score += 12
                if word in name_lower: score += 8
                if word in id_lower: score += 6
                if word in selector_lower: score += 4
                if word in class_lower: score += 10

            if score > best_score:
                best_score = score
                best_element = el

        if best_element is not None and best_score > 0:
            # If fill action and no explicit value, generate mock data based on type
            if action == "fill" and not val:
                val = generate_mock_data(best_element["dataType"], best_element["labelText"])
                logger.info(f"Auto-generated mock value '{val}' for field type '{best_element['dataType']}'")
            
            return {
                "action": action,
                "element_id": best_element["id"],
                "value": val,
                "reasoning": f"Heuristics matched element with score {best_score}: {best_element['selector']}"
            }

        # Fallback to first text input if fill had no matches
        if action == "fill":
            for el in elements:
                if el["tagName"] == "INPUT" and el["typeAttr"] not in ["submit", "button", "image"]:
                    val = val or generate_mock_data(el["dataType"], el["labelText"])
                    return {"action": "fill", "element_id": el["id"], "value": val, "reasoning": "Fallback to first text field."}

        # Fallback to first button/link if click had no matches
        for el in elements:
            if el["tagName"] in ["BUTTON", "A"] or el["text"]:
                return {"action": "click", "element_id": el["id"], "value": "", "reasoning": "Fallback to first interactive element."}

        return {"action": "done", "element_id": None, "value": "", "reasoning": "No suitable element found, finishing."}


    def execute_testcase(self, page: Page, steps: List[str]) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Execute list of testcase steps on the page. Captures results and builds Java lines.
        """
        logger.info(f"Starting execution of {len(steps)} web test steps...")
        logs = []
        overall_success = True
        
        # Keep track of initial load screenshot
        web_driver_utils.wait_for_page_load(page)
        
        for i, step_text in enumerate(steps, 1):
            logger.info(f"\n--- STEP {i} of {len(steps)}: '{step_text}' ---")
            
            step_clean = step_text.lower()
            is_autofill_form_step = "fill the details" in step_clean and "by agent" in step_clean
            
            if is_autofill_form_step:
                logger.info("Special Autofill Step detected: Filling all form details automatically...")
                elements = web_driver_utils.extract_interactive_elements(page)
                screenshot_before = web_driver_utils.get_screenshot_b64(page)
                
                step_log = {
                    "step_index": i,
                    "step_text": step_text,
                    "action": "autofill",
                    "selector": "multiple",
                    "value": "auto-generated form details",
                    "reasoning": "Filled all visible form fields with matching data types automatically.",
                    "screenshot_before": screenshot_before,
                    "screenshot_after": "",
                    "java_code": "",
                    "status": "pending",
                    "error": ""
                }
                
                try:
                    java_statements = {}
                    filled_count = 0
                    
                    for attempt in range(1, 4):
                        logger.info(f"--- Form Autofill Validation Attempt {attempt} ---")
                        elements = web_driver_utils.extract_interactive_elements(page)
                        
                        # In subsequent attempts, check for validation errors
                        if attempt > 1:
                            invalid_elements = []
                            for el in elements:
                                sel = el["selector"]
                                if not sel:
                                    continue
                                try:
                                    # If the element has aria-invalid="true", it is invalid
                                    if page.eval_on_selector(sel, "el => el.getAttribute('aria-invalid') === 'true'"):
                                        invalid_elements.append(el)
                                except Exception:
                                    pass
                            
                            if not invalid_elements:
                                logger.info("✓ Validation check passed: No invalid fields detected.")
                                break
                                
                            logger.info(f"Validation failed on {len(invalid_elements)} fields: {[e['selector'] for e in invalid_elements]}. Regenerating corrected values...")
                            fields_to_fill = invalid_elements
                        else:
                            fields_to_fill = elements
                            
                        # Fill the form fields (or correct invalid ones)
                        for el in fields_to_fill:
                            tag = el["tagName"].upper()
                            type_attr = (el.get("typeAttr") or "").lower()
                            role_attr = (el.get("roleAttr") or "").lower()
                            selector = el["selector"]
                            
                            # Skip if selector is empty
                            if not selector:
                                continue
                            
                            # Identify fillable fields: INPUT (excluding buttons/submits/hidden), TEXTAREA, SELECT, or role="combobox"
                            if tag == "INPUT" and type_attr in ["button", "submit", "image", "hidden", "reset"]:
                                continue
                            
                            if tag not in ["INPUT", "TEXTAREA", "SELECT"] and role_attr != "combobox":
                                continue
                            
                            try:
                                # Check if disabled or readonly (via JS execution)
                                is_editable = page.eval_on_selector(selector, "el => !el.disabled && el.getAttribute('aria-disabled') !== 'true' && !el.readOnly")
                                if not is_editable:
                                    continue
                                
                                # Perform the action based on tag/type/role
                                if role_attr == "combobox":
                                    # 1. Click the combobox to expand options
                                    page.click(selector)
                                    time.sleep(0.5)
                                    
                                    # 2. Resolve options listbox if aria-controls exists, else fallback to global
                                    aria_controls = page.eval_on_selector(selector, "el => el.getAttribute('aria-controls') || ''")
                                    if aria_controls:
                                        options_selector = f"#{aria_controls} [role='option']"
                                    else:
                                        options_selector = "[role='option']"
                                        
                                    # Wait a short moment to see if options are already visible without typing
                                    try:
                                        page.wait_for_selector(options_selector, timeout=500)
                                    except Exception:
                                        pass
                                        
                                    # Retrieve options text values
                                    options_text = page.eval_on_selector_all(options_selector, "elements => elements.map(el => (el.innerText || el.textContent || '').trim())")
                                    valid_options = [opt for opt in options_text if opt and "select" not in opt.lower()]
                                    if not valid_options and options_text:
                                        valid_options = options_text
                                        
                                    is_searchable = False
                                    query = ""
                                    
                                    # If no options are visible, try searching/typing if a searchbox is active
                                    if not valid_options:
                                        is_searchable = page.evaluate("""() => {
                                            const active = document.activeElement;
                                            return (active && active.getAttribute('role') === 'searchbox');
                                        }""")
                                        
                                        if is_searchable:
                                            # Resolve a query based on label and country if possible
                                            query = "1"
                                            lbl_text = el.get("labelText") or ""
                                            if "postal" in lbl_text.lower() or "zip" in lbl_text.lower() or "postal" in selector.lower():
                                                try:
                                                    # Find Operating Country value from the combobox text
                                                    country_text = page.locator('label:has-text("Operating Country") >> xpath=ancestor::div[contains(@class, "flex-col")][1] >> [role="combobox"]').first.inner_text().strip()
                                                except Exception:
                                                    country_text = ""
                                                if "united states" in country_text.lower():
                                                    query = "90210"
                                                elif "india" in country_text.lower():
                                                    query = "560001"
                                                else:
                                                    query = "10001"
                                            page.keyboard.type(query)
                                            time.sleep(1.0)
                                            
                                            # Wait for options to render after typing
                                            try:
                                                page.wait_for_selector(options_selector, timeout=2000)
                                            except Exception:
                                                # Try fallback options selector
                                                options_selector = "[role='option']"
                                                page.wait_for_selector(options_selector, timeout=2000)
                                                
                                            options_text = page.eval_on_selector_all(options_selector, "elements => elements.map(el => (el.innerText || el.textContent || '').trim())")
                                            valid_options = [opt for opt in options_text if opt and "select" not in opt.lower()]
                                            if not valid_options and options_text:
                                                valid_options = options_text
                                                
                                    if not valid_options:
                                        raise Exception(f"No option elements found for combobox {selector}")
                                        
                                    # Select preferred options for country and state to ensure valid dependencies
                                    val = None
                                    lbl_clean = (el.get("labelText") or "").lower()
                                    if "country" in lbl_clean or "country" in selector.lower():
                                        for pref in ["united states", "india", "canada"]:
                                            for opt in valid_options:
                                                if pref in opt.lower():
                                                    val = opt
                                                    break
                                            if val:
                                                break
                                    elif "state" in lbl_clean or "province" in lbl_clean or "state" in selector.lower():
                                        for pref in ["california", "karnataka", "ontario"]:
                                            for opt in valid_options:
                                                if pref in opt.lower():
                                                    val = opt
                                                    break
                                            if val:
                                                break
                                                
                                    if not val:
                                        val = valid_options[0]
                                    opt_click_selector = f"[role='option']:has-text(\"{val}\")"
                                    page.locator(opt_click_selector).first.click()
                                    web_driver_utils.wait_for_page_load(page)
                                    
                                    escaped_selector = self._escape_java(selector)
                                    escaped_val = self._escape_java(val)
                                    if is_searchable and query:
                                        escaped_query = self._escape_java(query)
                                        java_statements[selector] = f'page.locator("{escaped_selector}").first().click();\n        page.keyboard().type("{escaped_query}");\n        try {{ Thread.sleep(1000); }} catch(Exception e) {{}}\n        page.locator("[role=\'option\']:has-text(\\"{escaped_val}\\")").first().click();\n        waitForPageLoad(page);'
                                    else:
                                        java_statements[selector] = f'page.locator("{escaped_selector}").first().click();\n        page.locator("[role=\'option\']:has-text(\\"{escaped_val}\\")").first().click();\n        waitForPageLoad(page);'
                                    filled_count += 1
                                    logger.info(f"Selected option '{val}' for combobox '{selector}'")
                                    
                                elif tag == "SELECT":
                                    # Get available options from the select element
                                    options = page.eval_on_selector_all(f"{selector} option", "elements => elements.map(el => el.value || el.textContent)")
                                    valid_options = [opt.strip() for opt in options if opt and opt.strip() and "select" not in opt.lower()]
                                    
                                    val = valid_options[0] if valid_options else "basic"
                                    page.select_option(selector, val)
                                    escaped_selector = self._escape_java(selector)
                                    escaped_val = self._escape_java(val)
                                    java_statements[selector] = f'page.locator("{escaped_selector}").first().selectOption("{escaped_val}");\n        waitForPageLoad(page);'
                                    filled_count += 1
                                    logger.info(f"Selected option '{val}' for select '{selector}'")
                                    
                                elif type_attr == "checkbox":
                                    # Check the checkbox if it is not already checked
                                    is_checked = page.is_checked(selector)
                                    if not is_checked:
                                        page.check(selector)
                                    escaped_selector = self._escape_java(selector)
                                    java_statements[selector] = f'page.locator("{escaped_selector}").first().check();\n        waitForPageLoad(page);'
                                    filled_count += 1
                                    logger.info(f"Checked checkbox '{selector}'")
                                    
                                elif type_attr == "radio":
                                    # Check the radio button
                                    page.click(selector)
                                    escaped_selector = self._escape_java(selector)
                                    java_statements[selector] = f'page.locator("{escaped_selector}").first().click();\n        waitForPageLoad(page);'
                                    filled_count += 1
                                    logger.info(f"Clicked radio '{selector}'")
                                    
                                elif type_attr == "file":
                                    # Handle file uploads
                                    dummy_filename = "dummy_upload.png"
                                    dummy_filepath = os.path.abspath(dummy_filename)
                                    if not os.path.exists(dummy_filepath):
                                        import base64
                                        png_data = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=")
                                        with open(dummy_filepath, "wb") as f:
                                            f.write(png_data)
                                    page.set_input_files(selector, dummy_filepath)
                                    
                                    # Dismiss any crop dialog overlay if triggered
                                    time.sleep(1.0)
                                    try:
                                        if page.locator("button:has-text('Apply')").first.is_visible():
                                            page.locator("button:has-text('Apply')").first.click()
                                            time.sleep(1.0)
                                    except Exception:
                                        pass
                                        
                                    escaped_selector = self._escape_java(selector)
                                    escaped_filename = self._escape_java(dummy_filename)
                                    java_statements[selector] = (
                                        f'page.locator("{escaped_selector}").first().setInputFiles(java.nio.file.Paths.get("{escaped_filename}"));\n'
                                        f'        waitForPageLoad(page);\n'
                                        f'        try {{\n'
                                        f'            if (page.locator("button:has-text(\'Apply\')").first().isVisible()) {{\n'
                                        f'                page.locator("button:has-text(\'Apply\')").first().click();\n'
                                        f'                waitForPageLoad(page);\n'
                                        f'            }}\n'
                                        f'        }} catch (Exception e) {{}}'
                                    )
                                    filled_count += 1
                                    logger.info(f"Uploaded dummy file for input '{selector}'")
                                else:
                                    # Standard text input/textarea/date/number/etc.
                                    val = generate_mock_data(el["dataType"], el["labelText"])
                                    # Clear it first
                                    page.fill(selector, "")
                                    page.type(selector, val)
                                    escaped_selector = self._escape_java(selector)
                                    escaped_val = self._escape_java(val)
                                    java_statements[selector] = f'page.locator("{escaped_selector}").first().fill("{escaped_val}");\n        waitForPageLoad(page);'
                                    filled_count += 1
                                    logger.info(f"Filled value '{val}' in input '{selector}'")
                                    
                                # Add a small delay between inputs for realism
                                time.sleep(0.3)
                            except Exception as el_err:
                                logger.warning(f"Failed to autofill element {selector}: {el_err}")
                                
                        # End of fields_to_fill loop.
                        # Now find and click the submit button to trigger validation/transition
                        submit_selector = None
                        for btn in elements:
                            b_tag = btn["tagName"].upper()
                            b_type = (btn.get("typeAttr") or "").lower()
                            b_text = (btn.get("text") or "").lower()
                            b_sel = btn["selector"]
                            
                            if b_tag == "BUTTON" and b_sel and (b_type == "submit" or "next" in b_text or "submit" in b_text):
                                submit_selector = b_sel
                                break
                                
                        if submit_selector:
                            logger.info(f"Clicking submit/next button: {submit_selector}")
                            page.click(submit_selector)
                            web_driver_utils.wait_for_page_load(page)
                            time.sleep(1.5) # Wait for page/modal/validation animations to settle
                            
                            escaped_submit = self._escape_java(submit_selector)
                            java_statements["_submit_action"] = f'page.locator("{escaped_submit}").first().click();\n        waitForPageLoad(page);'
                        else:
                            logger.warning("No submit/next button found in form viewport.")
                            
                    # Construct java lines from deduplicated dict
                    java_lines = list(java_statements.values())
                    web_driver_utils.wait_for_page_load(page)
                    step_log["java_code"] = "\n        ".join(java_lines)
                    step_log["status"] = "success"
                    logger.info(f"Successfully autofilled {filled_count} form fields across attempts.")
                    
                except Exception as e:
                    step_log["error"] = str(e)
                    step_log["status"] = "failed"
                    overall_success = False
                    logger.error(f"Error during autofill step: {e}", exc_info=True)
                    
                step_log["screenshot_after"] = web_driver_utils.get_screenshot_b64(page)
                logs.append(step_log)
                continue
            
            # Extract elements & screenshot before action
            elements = web_driver_utils.extract_interactive_elements(page)
            screenshot_before = web_driver_utils.get_screenshot_b64(page)
            
            decision = self.decide_action(step_text, elements, screenshot_before)
            action = decision.get("action", "done").lower()
            el_id = decision.get("element_id")
            val = decision.get("value", "")
            reasoning = decision.get("reasoning", "")
            
            target_el = next((el for el in elements if el["id"] == el_id), None) if el_id is not None else None
            selector = target_el["selector"] if target_el else ""
            
            logger.info(f"Action: {action.upper()}, Target: {selector or 'N/A'}, Value: '{val}'")
            logger.info(f"Reasoning: {reasoning}")
            
            step_log = {
                "step_index": i,
                "step_text": step_text,
                "action": action,
                "selector": selector,
                "value": val,
                "reasoning": reasoning,
                "screenshot_before": screenshot_before,
                "screenshot_after": "",
                "java_code": "",
                "status": "pending",
                "error": ""
            }
            
            try:
                if action == "navigate":
                    page.goto(val)
                    web_driver_utils.wait_for_page_load(page)
                    escaped_val = self._escape_java(val)
                    step_log["java_code"] = f'page.navigate("{escaped_val}");\n        waitForPageLoad(page);'
                    step_log["status"] = "success"
                elif action == "click":
                    if not selector:
                        raise Exception("Target element selector missing for Click action.")
                    page.click(selector)
                    web_driver_utils.wait_for_page_load(page)
                    escaped_selector = self._escape_java(selector)
                    step_log["java_code"] = f'page.locator("{escaped_selector}").first().click();\n        waitForPageLoad(page);'
                    step_log["status"] = "success"
                elif action == "fill":
                                    if not selector:
                                        raise Exception("Target element selector missing for Fill action.")
                                    
                                    is_file_input = page.eval_on_selector(selector, "el => el.type === 'file'")
                                    if is_file_input:
                                        dummy_filename = "dummy_upload.png"
                                        dummy_filepath = os.path.abspath(dummy_filename)
                                        if not os.path.exists(dummy_filepath):
                                            import base64
                                            png_data = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=")
                                            with open(dummy_filepath, "wb") as f:
                                                f.write(png_data)
                                        page.set_input_files(selector, dummy_filepath)
                                        
                                        # Dismiss any crop dialog overlay if triggered
                                        time.sleep(1.0)
                                        try:
                                            if page.locator("button:has-text('Apply')").first.is_visible():
                                                page.locator("button:has-text('Apply')").first.click()
                                                time.sleep(1.0)
                                        except Exception:
                                            pass
                                            
                                        escaped_selector = self._escape_java(selector)
                                        escaped_filename = self._escape_java(dummy_filename)
                                        step_log["java_code"] = (
                                            f'page.locator("{escaped_selector}").first().setInputFiles(java.nio.file.Paths.get("{escaped_filename}"));\n'
                                            f'        waitForPageLoad(page);\n'
                                            f'        try {{\n'
                                            f'            if (page.locator("button:has-text(\'Apply\')").first().isVisible()) {{\n'
                                            f'                page.locator("button:has-text(\'Apply\')").first().click();\n'
                                            f'                waitForPageLoad(page);\n'
                                            f'            }}\n'
                                            f'        }} catch (Exception e) {{}}'
                                        )
                                    else:
                                        # Clear it first
                                        page.fill(selector, "")
                                        page.type(selector, val)
                                        escaped_selector = self._escape_java(selector)
                                        escaped_val = self._escape_java(val)
                                        step_log["java_code"] = f'page.locator("{escaped_selector}").first().fill("{escaped_val}");\n        waitForPageLoad(page);'
                                    web_driver_utils.wait_for_page_load(page)
                                    step_log["status"] = "success"
                elif action == "select":
                    if not selector:
                        raise Exception("Target element selector missing for Select action.")
                    page.select_option(selector, val)
                    web_driver_utils.wait_for_page_load(page)
                    escaped_selector = self._escape_java(selector)
                    escaped_val = self._escape_java(val)
                    step_log["java_code"] = f'page.locator("{escaped_selector}").first().selectOption("{escaped_val}");\n        waitForPageLoad(page);'
                    step_log["status"] = "success"
                elif action == "check":
                    if not selector:
                        raise Exception("Target element selector missing for Check action.")
                    page.check(selector)
                    web_driver_utils.wait_for_page_load(page)
                    escaped_selector = self._escape_java(selector)
                    step_log["java_code"] = f'page.locator("{escaped_selector}").first().check();\n        waitForPageLoad(page);'
                    step_log["status"] = "success"
                elif action == "hover":
                    if not selector:
                        raise Exception("Target element selector missing for Hover action.")
                    page.hover(selector)
                    web_driver_utils.wait_for_page_load(page)
                    escaped_selector = self._escape_java(selector)
                    step_log["java_code"] = f'page.locator("{escaped_selector}").first().hover();\n        waitForPageLoad(page);'
                    step_log["status"] = "success"
                elif action == "verify":
                    web_driver_utils.wait_for_page_load(page)
                    if val.startswith("title:"):
                        expected = val[6:]
                        actual = page.title()
                        if expected.lower() not in actual.lower():
                            raise AssertionError(f"Expected page title to contain '{expected}', but got '{actual}'")
                        logger.info(f"✓ Verification success: Page title contains '{expected}'")
                        escaped_expected = self._escape_java(expected)
                        step_log["java_code"] = f'org.testng.Assert.assertTrue(page.title().toLowerCase().contains("{escaped_expected.lower()}"));'
                    elif selector:
                        # Verify the text inside a specific element
                        expected = val[5:] if val.startswith("text:") else val
                        actual = page.locator(selector).text_content() or ""
                        if expected.lower() not in actual.lower():
                            raise AssertionError(f"Expected element '{selector}' to contain text '{expected}', but got '{actual}'")
                        logger.info(f"✓ Verification success: Element '{selector}' contains text '{expected}'.")
                        escaped_selector = self._escape_java(selector)
                        escaped_expected = self._escape_java(expected)
                        step_log["java_code"] = f'org.testng.Assert.assertTrue(page.locator("{escaped_selector}").first().textContent().toLowerCase().contains("{escaped_expected.lower()}"));'
                    else:
                        expected = val[5:] if val.startswith("text:") else val
                        locator_str = f"text={expected}"
                        page.wait_for_selector(locator_str, timeout=5000)
                        logger.info(f"✓ Verification success: Text '{expected}' is present on page.")
                        escaped_text = self._escape_java(expected)
                        step_log["java_code"] = f'org.testng.Assert.assertTrue(page.locator("text={escaped_text}").first().isVisible());'
                    step_log["status"] = "success"
                elif action == "done":
                    logger.info("Agent declared goal successfully met.")
                    step_log["java_code"] = "// Step completed."
                    step_log["status"] = "success"
                    step_log["screenshot_after"] = screenshot_before
                    logs.append(step_log)
                    break
                else:
                    raise Exception(f"Unsupported web action: {action}")
                
                # Check for mandatory fields in the active viewport and pre-fill them
                # if they are currently on screen and were not filled by the step itself.
                # This makes the agent understand all mandatory fields automatically.
                if action != "done":
                    time.sleep(0.5) # Settle slightly before scanning for remaining inputs
                    new_elements = web_driver_utils.extract_interactive_elements(page)
                    for el in new_elements:
                        # If field is mandatory, is an empty input/textarea, and not targeted yet
                        if el["isMandatory"] and el["tagName"] in ["INPUT", "TEXTAREA"] and el["typeAttr"] not in ["submit", "button", "checkbox", "radio"]:
                            # Fetch current value
                            curr_val = page.locator(el["selector"]).input_value()
                            if not curr_val:
                                mock_val = generate_mock_data(el["dataType"], el["labelText"])
                                logger.info(f"Auto-filling mandatory empty field '{el['selector']}' with mock data: '{mock_val}'")
                                page.fill(el["selector"], mock_val)
                                # Log as a sub-action in Java code
                                escaped_el_selector = self._escape_java(el["selector"])
                                escaped_mock_val = self._escape_java(mock_val)
                                step_log["java_code"] += f'\npage.locator("{escaped_el_selector}").first().fill("{escaped_mock_val}"); // Auto-filled mandatory field\n        waitForPageLoad(page);'
                
                # Save screenshot after
                step_log["screenshot_after"] = web_driver_utils.get_screenshot_b64(page)
                
            except Exception as ex:
                logger.error(f"Failed step execution: {ex}")
                step_log["status"] = "failed"
                step_log["error"] = str(ex)
                step_log["screenshot_after"] = web_driver_utils.get_screenshot_b64(page)
                overall_success = False
                logs.append(step_log)
                break
                
            logs.append(step_log)
            
        return overall_success, logs

    def generate_java_code(self, logs: List[Dict[str, Any]], class_name: str = "PlaywrightAutomation", initial_url: str = None) -> str:
        """
        Compile list of step logs into complete Playwright Java class string.
        """
        java_statements = []
        if initial_url:
            escaped_url = self._escape_java(initial_url)
            java_statements.append(f'            page.navigate("{escaped_url}");')

        for log in logs:
            if log["java_code"]:
                # Split multi-line code blocks if any (e.g. from auto-fills)
                lines = log["java_code"].splitlines()
                for line in lines:
                    java_statements.append(f"            {line}")

        code_block = "\n".join(java_statements)
        
        java_template = f"""package com.example;
 
import com.microsoft.playwright.*;
import java.util.Arrays;
 
public class {class_name} {{
    public static void main(String[] args) {{
        try (Playwright playwright = Playwright.create()) {{
            // Launch Chromium headed so the run can be observed visually
            Browser browser = playwright.chromium().launch(new BrowserType.LaunchOptions()
                .setHeadless(true)
                .setSlowMo(500));
            
            BrowserContext context = browser.newContext(new Browser.NewContextOptions()
                .setViewportSize(1280, 800)
                .setIgnoreHTTPSErrors(true));
            
            Page page = context.newPage();
            
            System.out.println("Starting automated Playwright Java test execution...");
            
            // --- Generated Automation Steps ---
{code_block}
            
            System.out.println("Automated test execution completed successfully!");
            
            // Cleanup session
            context.close();
            browser.close();
        }} catch (Exception e) {{
            System.err.println("Test execution failed: " + e.getMessage());
            e.printStackTrace();
        }}
    }}

    private static void waitForPageLoad(Page page) {{
        try {{
            Thread.sleep(1000);
            page.waitForLoadState(com.microsoft.playwright.options.LoadState.LOAD);
            page.waitForLoadState(com.microsoft.playwright.options.LoadState.DOMCONTENTLOADED);
        }} catch (Exception e) {{}}
    }}
}}
"""
        return java_template

    def generate_testng_java_code(self, test_cases_runs: List[Dict[str, Any]], class_name: str = "PlaywrightAutomation", initial_url: str = None) -> str:
        """
        Compile list of test case runs into a single Playwright Java class using TestNG annotations.
        """
        methods_code = []
        for run in test_cases_runs:
            tc_name = run["name"]
            tc_desc = run["description"]
            logs = run["logs"]
            
            # Format method steps
            java_statements = []
            if initial_url:
                escaped_url = self._escape_java(initial_url)
                java_statements.append(f'        page.navigate("{escaped_url}");')
                
            for log in logs:
                if log["java_code"]:
                    # Split multi-line code blocks if any (e.g. from auto-fills)
                    lines = log["java_code"].splitlines()
                    for line in lines:
                        java_statements.append(f"        {line}")
                        
            code_block = "\n".join(java_statements)
            
            # Build TestNG @Test method
            method_template = f"""    @Test(description = "{self._escape_java(tc_desc)}")
    public void test{tc_name}() {{
        System.out.println("Executing Test Case: {self._escape_java(tc_desc)}...");
{code_block}
    }}"""
            methods_code.append(method_template)
            
        all_methods = "\n\n".join(methods_code)
        
        java_template = f"""package com.example;

import com.microsoft.playwright.*;
import org.testng.annotations.*;
import org.testng.Assert;
import java.util.Arrays;

public class {class_name} {{
    private Playwright playwright;
    private Browser browser;
    private BrowserContext context;
    private Page page;

    @BeforeClass
    public void setUp() {{
        playwright = Playwright.create();
        // Launch Chromium headed so the run can be observed visually
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

{all_methods}

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

    private void waitForPageLoad(Page page) {{
        try {{
            Thread.sleep(1000);
            page.waitForLoadState(com.microsoft.playwright.options.LoadState.LOAD);
        }} catch (Exception e) {{}}
    }}
}}
"""
        return java_template
