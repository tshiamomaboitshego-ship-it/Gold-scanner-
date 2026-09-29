# V43.3 Auto Control

Adds a persistent server-side AUTO SCANNER ON/OFF control to V43.2.

- OFF: cron returns SCANNER_OFF before XAUS, Twelve Data, discovery, or Telegram trade alerts.
- OFF preserves active WATCH opportunities.
- ON resumes automatic discovery and saved WATCH monitoring.
- Manual SCAN MARKET remains available while AUTO is OFF.
- The browser stores the monitor secret locally after the user enters it; the secret is not embedded in this ZIP.
