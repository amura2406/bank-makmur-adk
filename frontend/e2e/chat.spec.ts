import { test, expect } from '@playwright/test';

test.describe('Chat Interface E2E Test', () => {
  test('should launch the application and verify header and input elements render', async ({ page }) => {
    // Navigate to the base URL configured in playwright.config.ts (http://127.0.0.1:5173/)
    await page.goto('/');

    // Verify header title "Tanya Makmur" is visible
    const headerTitle = page.locator('header').getByText('Tanya Makmur');
    await expect(headerTitle).toBeVisible();

    // Verify online dot is visible
    const onlineDot = page.getByLabel('Online');
    await expect(onlineDot).toBeVisible();

    // Verify welcome message is visible in the chat bubbles
    const welcomeBubble = page.getByText(/Halo! Saya Tanya Makmur, asisten virtual Anda/i);
    await expect(welcomeBubble).toBeVisible();

    // Verify input element with placeholder "Tulis pesan..." is visible and enabled
    const input = page.getByPlaceholder('Tulis pesan...');
    await expect(input).toBeVisible();
    await expect(input).toBeEnabled();

    // Verify the send button is rendered and is initially disabled
    const sendBtn = page.getByLabel('Kirim');
    await expect(sendBtn).toBeVisible();
    await expect(sendBtn).toBeDisabled();
  });

  test('should simulate typing and sending "bunga" and receiving mock response', async ({ page }) => {
    await page.goto('/');

    const input = page.getByPlaceholder('Tulis pesan...');
    const sendBtn = page.getByLabel('Kirim');

    // Type a message "bunga"
    await input.fill('bunga');

    // Verify send button is enabled
    await expect(sendBtn).toBeEnabled();

    // Send the message
    await sendBtn.click();

    // Verify the user bubble contains "bunga"
    const userBubble = page.getByText('bunga');
    await expect(userBubble).toBeVisible();

    // Assert the input placeholder changes to loading message
    const loadingInput = page.getByPlaceholder('Looking up that information for you...');
    await expect(loadingInput).toBeVisible();

    // Assert that the loading state ends and the mock agent response is displayed
    const agentResponse = page.getByText(/bunga|interest|rate/i);
    await expect(agentResponse).toBeVisible();

    // Assert input placeholder reverts to normal and is enabled
    const inputAfter = page.getByPlaceholder('Tulis pesan...');
    await expect(inputAfter).toBeVisible({ timeout: 15000 });
    await expect(inputAfter).toBeEnabled({ timeout: 15000 });
  });

  test('should simulate name introduction and pocket balance retrieval for Angga', async ({ page }) => {
    page.on('console', msg => console.log('PAGE LOG:', msg.text()));
    await page.goto('/');

    const input = page.getByPlaceholder('Tulis pesan...');
    const sendBtn = page.getByLabel('Kirim');

    // Introduce name: "Nama saya Angga"
    await input.fill('Nama saya Angga');
    await expect(sendBtn).toBeEnabled();
    await sendBtn.click();

    // Wait for the loading state to finish and input to become enabled again
    const inputAfterName = page.getByPlaceholder('Tulis pesan...');
    await expect(inputAfterName).toBeVisible({ timeout: 15000 });
    await expect(inputAfterName).toBeEnabled({ timeout: 15000 });

    // Query balance for "kantong utama"
    await input.fill('Berapa saldo kantong utama saya?');
    await expect(sendBtn).toBeEnabled();
    await sendBtn.click();

    // Wait for the loading state to finish and input to become enabled again
    const inputAfterBalance = page.getByPlaceholder('Tulis pesan...');
    await expect(inputAfterBalance).toBeVisible({ timeout: 15000 });
    await expect(inputAfterBalance).toBeEnabled({ timeout: 15000 });

    // Assert that the response contains the balance "12.500.000" or similar
    const balanceResponse = page.getByText(/12\.500\.000|12,500,000/);
    await expect(balanceResponse).toBeVisible({ timeout: 15000 });
  });
});
