package com.example;

import com.microsoft.playwright.*;
import java.util.Arrays;

public class VerifyAdminLoginOnPartnerPortal {
    public static void main(String[] args) {
        try (Playwright playwright = Playwright.create()) {
            // Launch Chromium headed so the run can be observed visually
            Browser browser = playwright.chromium().launch(new BrowserType.LaunchOptions()
                .setHeadless(false)
                .setSlowMo(500));
            
            BrowserContext context = browser.newContext(new Browser.NewContextOptions()
                .setViewportSize(1280, 800)
                .setIgnoreHTTPSErrors(true));
            
            Page page = context.newPage();
            
            System.out.println("Starting automated Playwright Java test execution...");
            
            // --- Generated Automation Steps ---
            page.navigate("https://dev-tapral.techies.work/Central");
            page.locator("#partner_id").fill("A-0000");
            page.locator("#user_name").fill("admin");
            page.locator("#password").fill("Admin@123");
            page.locator("button:has-text(\"Login\")").click();
            org.testng.Assert.assertTrue(page.title().contains("tapral"));
            
            System.out.println("Automated test execution completed successfully!");
            
            // Cleanup session
            context.close();
            browser.close();
        } catch (Exception e) {
            System.err.println("Test execution failed: " + e.getMessage());
            e.printStackTrace();
        }
    }
}
