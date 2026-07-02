import logging
import base64
import os
import json
import time
from typing import Dict, Any, List, Tuple
from playwright.sync_api import sync_playwright, Page, Browser, Playwright

logger = logging.getLogger("WebAgent.driver_utils")

def setup_browser(headless: bool = False, timeout: int = 30000) -> Tuple[Playwright, Browser, Page]:
    """
    Initialize Playwright, launch browser, and return instance controls.
    """
    logger.info(f"Launching Playwright browser (headless={headless})...")
    playwright_instance = sync_playwright().start()
    # Use Chromium as standard browser
    browser = playwright_instance.chromium.launch(
        headless=headless,
        args=["--disable-web-security", "--no-sandbox"]
    )
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
        ignore_https_errors=True
    )
    context.set_default_timeout(timeout)
    page = context.new_page()
    logger.info("Browser launched and new page opened successfully.")
    return playwright_instance, browser, page

def get_screenshot_b64(page: Page) -> str:
    """
    Capture a screenshot of the page and return as Base64 encoded string.
    """
    try:
        screenshot_bytes = page.screenshot(type="png")
        return base64.b64encode(screenshot_bytes).decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to capture web screenshot: {e}")
        return ""

def wait_for_page_load(page: Page, timeout: int = 5000):
    """
    Wait for network idle and load state to settle.
    """
    time.sleep(1.0)
    try:
        page.wait_for_load_state("load", timeout=timeout)
        page.wait_for_load_state("domcontentloaded", timeout=timeout)
        page.wait_for_load_state("networkidle", timeout=timeout)
    except Exception as e:
        logger.debug(f"Wait for page load timed out/relaxed: {e}")

def extract_interactive_elements(page: Page) -> List[Dict[str, Any]]:
    """
    Inject JS to inspect the DOM and extract detailed metadata of visible interactive elements.
    """
    js_extract = """
    () => {
        const elements = Array.from(document.querySelectorAll(
            'a, button, input, select, textarea, [role="button"], [role="link"], [role="checkbox"], [role="radio"], [role="combobox"], [contenteditable="true"]'
        ));
        
        let indexCount = 0;
        return elements.map((el) => {
            const rect = el.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) return null;
            
            // Basic visibility check
            const style = window.getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return null;

            // Resolve label text
            let labelText = "";
            if (el.id) {
                const label = document.querySelector(`label[for="${el.id}"]`);
                if (label) labelText = label.innerText || label.textContent;
            }
            if (!labelText) {
                const parentLabel = el.closest('label');
                if (parentLabel) labelText = parentLabel.innerText || parentLabel.textContent;
            }
            if (!labelText) {
                // Find closest wrapper that contains a label
                let container = el.parentElement;
                while (container && container.tagName !== 'FORM') {
                    const label = container.querySelector('label');
                    if (label) {
                        labelText = label.innerText || label.textContent;
                        break;
                    }
                    container = container.parentElement;
                }
            }
            if (!labelText) {
                // Preceding text sibling lookup
                let prev = el.previousElementSibling;
                if (prev) {
                    let tempText = (prev.innerText || prev.textContent || "").trim();
                    if (tempText && !tempText.includes('\\n') && tempText.length < 60) {
                        labelText = tempText;
                    }
                }
            }
            labelText = (labelText || "").trim();

            const placeholderAttr = el.getAttribute('placeholder') || '';
            const nameAttr = el.getAttribute('name') || '';
            const typeAttr = el.getAttribute('type') || '';
            const idAttr = el.id || '';
            const roleAttr = el.getAttribute('role') || '';
            const textValue = (el.innerText || el.textContent || '').trim();

            // Determine if it is a mandatory field
            const isRequiredAttr = el.hasAttribute('required') || 
                                   el.getAttribute('aria-required') === 'true' || 
                                   el.hasAttribute('data-required');
            const textHasStar = labelText.includes('*') || 
                                labelText.toLowerCase().includes('required') || 
                                placeholderAttr.includes('*');
            const isMandatory = isRequiredAttr || textHasStar;

            // Detect field data type
            let dataType = "text";
            const combinedStr = `${typeAttr} ${nameAttr} ${idAttr} ${placeholderAttr} ${labelText} ${roleAttr}`.toLowerCase();
            
            if (typeAttr === 'file') {
                dataType = 'file';
            } else if (typeAttr === 'color') {
                dataType = 'color';
            } else if (typeAttr === 'range') {
                dataType = 'range';
            } else if (typeAttr === 'time') {
                dataType = 'time';
            } else if (typeAttr === 'month') {
                dataType = 'month';
            } else if (typeAttr === 'week') {
                dataType = 'week';
            } else if (typeAttr === 'datetime-local') {
                dataType = 'datetime-local';
            } else if (combinedStr.includes('email') || combinedStr.includes('mail')) {
                dataType = 'email';
            } else if (combinedStr.includes('whatsapp')) {
                dataType = 'whatsapp';
            } else if (combinedStr.includes('phone') || combinedStr.includes('mobile') || combinedStr.includes('tel') || combinedStr.includes('contact')) {
                dataType = 'phone';
            } else if (combinedStr.includes('password') || combinedStr.includes('pwd')) {
                dataType = 'password';
            } else if (combinedStr.includes('first name') || combinedStr.includes('firstname')) {
                dataType = 'firstname';
            } else if (combinedStr.includes('last name') || combinedStr.includes('lastname')) {
                dataType = 'lastname';
            } else if (combinedStr.includes('designation') || combinedStr.includes('job title') || combinedStr.includes('role') || combinedStr.includes('position')) {
                dataType = 'designation';
            } else if (combinedStr.includes('company') || combinedStr.includes('business') || combinedStr.includes('partner name') || combinedStr.includes('organization') || combinedStr.includes('vendor') || combinedStr.includes('firm') || combinedStr.includes('employer')) {
                dataType = 'company';
            } else if (combinedStr.includes('domain') || combinedStr.includes('subdomain') || combinedStr.includes('host')) {
                dataType = 'domain';
            } else if (combinedStr.includes('website') || combinedStr.includes('site') || combinedStr.includes('url') || combinedStr.includes('web')) {
                dataType = 'website';
            } else if (combinedStr.includes('tax') || combinedStr.includes('vat') || combinedStr.includes('gst') || combinedStr.includes('tin')) {
                dataType = 'tax';
            } else if (combinedStr.includes('license') || combinedStr.includes('trade license')) {
                dataType = 'license';
            } else if (combinedStr.includes('landmark')) {
                dataType = 'landmark';
            } else if (combinedStr.includes('po box') || combinedStr.includes('pobox') || combinedStr.includes('postbox')) {
                dataType = 'pobox';
            } else if (combinedStr.includes('description') || combinedStr.includes('comment') || combinedStr.includes('note') || combinedStr.includes('feedback')) {
                dataType = 'description';
            } else if (combinedStr.includes('address') || combinedStr.includes('street') || combinedStr.includes('location')) {
                dataType = 'address';
            } else if (combinedStr.includes('city') || combinedStr.includes('town')) {
                dataType = 'city';
            } else if (combinedStr.includes('state') || combinedStr.includes('province') || combinedStr.includes('region')) {
                dataType = 'state';
            } else if (combinedStr.includes('country') || combinedStr.includes('nation')) {
                dataType = 'country';
            } else if (combinedStr.includes('name') || combinedStr.includes('username')) {
                dataType = 'name';
            } else if (combinedStr.includes('amount') || combinedStr.includes('price') || combinedStr.includes('cost') || combinedStr.includes('payment')) {
                dataType = 'price';
            } else if (combinedStr.includes('number') || combinedStr.includes('quantity') || combinedStr.includes('qty') || combinedStr.includes('age')) {
                dataType = 'number';
            } else if (combinedStr.includes('zip') || combinedStr.includes('postal') || combinedStr.includes('pin code')) {
                dataType = 'zipcode';
            } else if (combinedStr.includes('date') || combinedStr.includes('dob') || combinedStr.includes('birth')) {
                dataType = 'date';
            }


            // Clean asterisk and trailing text of labelText to use in selector
            let cleanLabel = labelText.replace(/[*]/g, '').replace(/required/gi, '').trim().split('\\n')[0].trim();

            // Generate clean Playwright selector
            let selector = "";
            let testId = el.getAttribute('data-testid') || el.getAttribute('data-test') || el.getAttribute('data-qa') || el.getAttribute('data-cy');
            if (testId) {
                let attrName = el.getAttribute('data-testid') ? 'data-testid' : 
                               (el.getAttribute('data-test') ? 'data-test' : 
                               (el.getAttribute('data-qa') ? 'data-qa' : 'data-cy'));
                selector = `[${attrName}="${testId}"]`;
            } else if (el.id && !el.id.startsWith('_r_') && !/^\d+$/.test(el.id)) {
                selector = `#${el.id}`;
            } else if (roleAttr === 'combobox' && cleanLabel) {
                selector = `label:has-text("${cleanLabel.replace(/"/g, '\\"')}") >> xpath=ancestor::div[contains(@class, "flex-col")][1] >> [role="combobox"]`;
            } else if (nameAttr && ['INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName)) {
                selector = `${el.tagName.toLowerCase()}[name="${nameAttr}"]`;
            } else if (el.tagName === 'BUTTON' && textValue && !/^\d+$/.test(textValue.trim())) {
                selector = `button:has-text("${textValue.replace(/"/g, '\\"')}")`;
            } else if (el.tagName === 'A' && textValue && !/^\d+$/.test(textValue.trim())) {
                selector = `a:has-text("${textValue.replace(/"/g, '\\"')}")`;
            } else if (placeholderAttr) {
                selector = `${el.tagName.toLowerCase()}[placeholder="${placeholderAttr.replace(/"/g, '\\"')}"]`;
            } else {
                let path = el.tagName.toLowerCase();
                if (el.className) {
                    const cleanClasses = el.className.split(/\s+/).filter(c => c && !c.includes(':') && !c.includes('[')).join('.');
                    if (cleanClasses) path += `.${cleanClasses}`;
                }
                selector = path;
            }

            return {
                id: indexCount++,
                tagName: el.tagName,
                idAttr: idAttr,
                nameAttr: nameAttr,
                typeAttr: typeAttr,
                roleAttr: roleAttr,
                placeholder: placeholderAttr,
                text: textValue,
                labelText: labelText,
                classAttr: el.className || "",
                isMandatory: !!isMandatory,
                dataType: dataType,

                bounds: {
                    x: rect.left,
                    y: rect.top,
                    width: rect.width,
                    height: rect.height
                },
                selector: selector
            };
        }).filter(x => x !== null);
    }
    """
    try:
        return page.evaluate(js_extract)
    except Exception as e:
        logger.error(f"Failed to evaluate DOM extract script: {e}")
        return []
