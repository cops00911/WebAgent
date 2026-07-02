package com.example;

import com.microsoft.playwright.*;
import org.testng.annotations.*;
import org.testng.Assert;
import java.util.Arrays;

public class PlaywrightAutomationTemp {
    private Playwright playwright;
    private Browser browser;
    private BrowserContext context;
    private Page page;

    @BeforeClass
    public void setUp() {
        playwright = Playwright.create();
        // Launch Chromium headed so the run can be observed visually
        browser = playwright.chromium().launch(new BrowserType.LaunchOptions()
            .setHeadless(true)
            .setSlowMo(500));
    }

    @BeforeMethod
    public void setUpMethod() {
        context = browser.newContext(new Browser.NewContextOptions()
            .setViewportSize(1280, 800)
            .setIgnoreHTTPSErrors(true));
        page = context.newPage();
    }

    @Test(description = "temp_steps")
    public void testTempSteps() {
        System.out.println("Executing Test Case: temp_steps...");
        page.navigate("https://www.saucedemo.com/");
        page.locator("[data-test=\"username\"]").first().fill("standard_user");
                waitForPageLoad(page);
        page.locator("[data-test=\"password\"]").first().fill("secret_sauce");
                waitForPageLoad(page);
        page.locator("[data-test=\"login-button\"]").first().click();
                waitForPageLoad(page);
    }

    @AfterMethod
    public void tearDownMethod() {
        if (context != null) {
            context.close();
        }
    }

    @AfterClass
    public void tearDown() {
        if (browser != null) {
            browser.close();
        }
        if (playwright != null) {
            playwright.close();
        }
    }

    private void waitForPageLoad(Page page) {
        try {
            Thread.sleep(1000);
            page.waitForLoadState(com.microsoft.playwright.options.LoadState.LOAD);
        } catch (Exception e) {}
    }
}
