let lastContextMenuPos = { x: window.innerWidth / 2, y: window.innerHeight / 2 };

document.addEventListener(
  "contextmenu",
  (e) => {
    lastContextMenuPos = { x: e.clientX, y: e.clientY };
  },
  true
);

function removeExistingBox() {
  const existing = document.getElementById("buddy-comment-box");
  if (existing) existing.remove();
}

function showCommentBox(payload) {
  removeExistingBox();

  const box = document.createElement("div");
  box.id = "buddy-comment-box";

  const maxLeft = window.innerWidth - 280;
  const maxTop = window.innerHeight - 140;
  box.style.left = `${Math.min(lastContextMenuPos.x, maxLeft)}px`;
  box.style.top = `${Math.min(lastContextMenuPos.y, maxTop)}px`;

  box.innerHTML = `
    <textarea placeholder="Add a note (optional)..."></textarea>
    <div class="buddy-actions">
      <button class="buddy-cancel" type="button">Cancel</button>
      <button class="buddy-save" type="button">Save</button>
    </div>
  `;

  document.documentElement.appendChild(box);
  const textarea = box.querySelector("textarea");
  textarea.focus();

  box.querySelector(".buddy-cancel").addEventListener("click", removeExistingBox);

  box.querySelector(".buddy-save").addEventListener("click", () => {
    chrome.runtime.sendMessage({
      type: "BUDDY_SUBMIT_COMMENT",
      payload,
      comment: textarea.value.trim() || null,
    });
    removeExistingBox();
  });

  document.addEventListener(
    "keydown",
    function onKey(e) {
      if (e.key === "Escape") {
        removeExistingBox();
        document.removeEventListener("keydown", onKey);
      }
    },
    { once: true }
  );
}

chrome.runtime.onMessage.addListener((message) => {
  if (message.type === "BUDDY_SHOW_COMMENT_INPUT") {
    showCommentBox(message.payload);
  }
});
