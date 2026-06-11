# Original User Request

## Initial Request — 2026-06-11T19:51:11Z

I want to create a Vite-based chat frontend for the Bank Makmur virtual assistant (implemented via Google ADK in the current workspace). The UI should look and feel like the "Tanya Jago" mobile chat application from the supplied mockup image but styled with an **Aurora gradient style (like Google Gemini)** instead of the Jago yellow theme. The frontend should be deployed on Google Cloud Run. The project needs unit tests and browser automation tests, as well as an adversarial critic subagent to ensure high quality and consistency.

Working directory: /Users/anggar/Code/bank-makmur-conv-agent/frontend
Integrity mode: development

## Requirements

### R1. UI Design and Mobile Chat Mockup Match
- Build a mobile-first, high-fidelity replica of the "Tanya Jago" UI layout.
- Visual aesthetics:
  - Theme colors: Use **Aurora style gradient colors (cool blues, purples, and pinks, similar to Google Gemini)** rather than Jago's yellow theme.
  - Distinct chat header with a back button, title "Tanya Makmur", and green online indicator dot.
  - User message bubbles: grey background, dark text, right-aligned.
  - Agent message bubbles: left-aligned, accompanied by a Bank Makmur logo/avatar (styled with an Aurora gradient square logo).
  - Bottom rounded input text area with a vibrant Aurora gradient border, showing a placeholder or look-up status text "Looking up that information for you..." when waiting for the backend response.
  - Subtle micro-animations for message entry, typing states, and interactions.
  - Modern typography using Google Fonts (e.g. Inter or Outfit).

### R2. Backend Integration
- The frontend must connect to the FastAPI backend of the ADK app (/Users/anggar/Code/bank-makmur-conv-agent/app/app/fast_api_app.py).
- Read the API endpoint URL from the environment variable VITE_API_URL (defaulting to local port 8000 for development).
- Create a .env file (and .env.example) defining VITE_API_URL.
- Support sending messages to the agent, receiving text or streaming responses, and managing the chat history session-by-session.

### R3. Deployment and Infrastructure
- Build and containerize the Vite frontend using a Dockerfile.
- Deploy the frontend container to Google Cloud Run in the user's GCP project (anggar-conv-agent) in the asia-southeast1 region.

### R4. Automated Testing and Verification
- Write unit tests for major frontend components (e.g. using Vitest).
- Write E2E/browser automation tests (e.g. using Playwright or the built-in browser/chrome-devtools tools) that launch the Vite app, send a message, and verify that the response from the backend is displayed in the UI.
- Use an adversarial critic subagent to review the frontend code, layout consistency, and responsiveness, ensuring it strictly matches the premium styling of the mockup.

## Acceptance Criteria

### UI and Styling
- [ ] Header includes back arrow, "Tanya Makmur" title, and green online dot.
- [ ] Bottom input field features a rounded pill shape with a colorful Aurora style gradient border.
- [ ] Agent avatar uses a premium Aurora gradient design matching the new Bank Makmur branding.
- [ ] Message bubbles are styled correctly (user on the right in grey, agent on the left with avatar).

### Functionality & Integration
- [ ] Interface successfully communicates with the ADK FastAPI server.
- [ ] A .env file exists with VITE_API_URL configured.
- [ ] When a request is in progress, the input/status bar displays "Looking up that information for you..." as a loading indicator.

### Quality & Testing
- [ ] Unit tests are implemented and pass.
- [ ] Browser automation E2E tests are implemented and pass, verifying message sending and receiving.
- [ ] The adversarial critic reviews the UI and reports that layout and visuals match the premium standard.
