# Privacy

Buddy does not operate any server. Everything the extension does routes through a backend running on your own machine (`http://localhost:8420`), which you start yourself.

- **Saved content** (selected text, link content, comments) is sent from your machine to your own local supermemory instance, wherever you've configured it to run (default: `http://localhost:8787`).
- **Chat messages** are sent from your machine to the LLM provider and API key you configure in the extension's options page. Buddy does not supply or proxy an LLM key on your behalf.
- No saved content, chat history, or credentials are sent to the developer of this extension or any third party by Buddy itself.
- Chat thread history is stored locally in the browser's extension storage (`chrome.storage.local`) and does not sync anywhere unless Chrome's own sync settings do so.

Because the backend and supermemory both run locally, you are responsible for whatever data-handling policy your chosen LLM provider has for requests you send it.
