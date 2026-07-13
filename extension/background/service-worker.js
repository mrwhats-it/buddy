importScripts("../lib/backend-client.js");

chrome.sidePanel
  .setPanelBehavior({ openPanelOnActionClick: true })
  .catch((err) => console.error(err));

const MENU_SAVE = "buddy-save";
const MENU_SAVE_WITH_COMMENT = "buddy-save-with-comment";

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: MENU_SAVE,
    title: "Add to Buddy",
    contexts: ["selection", "link"],
  });
  chrome.contextMenus.create({
    id: MENU_SAVE_WITH_COMMENT,
    title: "Add to Buddy with comment",
    contexts: ["selection", "link"],
  });
});

function itemFromClickInfo(info) {
  if (info.linkUrl) {
    return { content: info.linkUrl, is_link: true };
  }
  return { content: info.selectionText || "", is_link: false };
}

async function doSave(payload, tab) {
  try {
    await BuddyBackend.save({ ...payload, page_title: tab?.title });
    chrome.action.setBadgeText({ text: "OK", tabId: tab?.id });
  } catch (err) {
    console.error("Buddy save failed:", err);
    chrome.action.setBadgeText({ text: "ERR", tabId: tab?.id });
  }
  setTimeout(() => chrome.action.setBadgeText({ text: "" }), 2000);
}

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  const base = itemFromClickInfo(info);
  if (!base.content) return;

  if (info.menuItemId === MENU_SAVE) {
    await doSave(base, tab);
    return;
  }

  if (info.menuItemId === MENU_SAVE_WITH_COMMENT) {
    if (!tab?.id) return;
    // Ask the content script to show a floating comment box near the click.
    chrome.tabs.sendMessage(tab.id, {
      type: "BUDDY_SHOW_COMMENT_INPUT",
      payload: base,
    });
  }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "BUDDY_SUBMIT_COMMENT") {
    doSave({ ...message.payload, comment: message.comment }, sender.tab).then(() =>
      sendResponse({ ok: true })
    );
    return true; // async response
  }
});
