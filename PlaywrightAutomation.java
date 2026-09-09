package com.example;

import com.microsoft.playwright.*;
import org.testng.annotations.*;
import org.testng.Assert;
import java.util.Arrays;

public class PlaywrightAutomation {
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

    @Test(description = "test_steps")
    public void testTestSteps() {
        System.out.println("Executing Test Case: test_steps...");
        page.navigate("https://www.saucedemo.com/");
        page.locator("[data-test=\"username\"]").first().fill("standard_user");
                waitForPageLoad(page);
        page.locator("[data-test=\"password\"]").first().fill("secret_sauce");
                waitForPageLoad(page);
        page.locator("[data-test=\"login-button\"]").first().click();
                waitForPageLoad(page);
        org.testng.Assert.assertTrue(page.title().toLowerCase().contains("swag labs"));
        page.locator("[data-test=\"item-4-title-link\"]").first().click();
                waitForPageLoad(page);
        page.locator("[data-test=\"add-to-cart\"]").first().click();
                waitForPageLoad(page);
        page.locator("[data-test=\"shopping-cart-link\"]").first().click();
                waitForPageLoad(page);
        page.locator("[data-test=\"checkout\"]").first().click();
                waitForPageLoad(page);
        page.locator("[data-test=\"firstName\"]").first().fill("Rachit");
                waitForPageLoad(page);
        page.locator("[data-test=\"lastName\"]").first().fill("Mehta");
                waitForPageLoad(page);
        page.locator("[data-test=\"postalCode\"]").first().fill("390023");
                waitForPageLoad(page);
        page.locator("[data-test=\"continue\"]").first().click();
                waitForPageLoad(page);
        // Step completed.
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
