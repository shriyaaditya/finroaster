// FinRoast Co-Pilot Content Script (Guided Semi-Auto Mode - Option 3)
(function () {
  console.log("[FinRoast Content Script] Injected on page:", window.location.href);

  // Inject Pulsing CSS Styles
  const styleEl = document.createElement("style");
  styleEl.innerHTML = `
    @keyframes finroast-pulse {
      0% {
        box-shadow: 0 0 0 0 rgba(255, 68, 68, 0.8);
        border-color: #ff4444 !important;
      }
      70% {
        box-shadow: 0 0 0 15px rgba(255, 68, 68, 0);
        border-color: #ff0000 !important;
      }
      100% {
        box-shadow: 0 0 0 0 rgba(255, 68, 68, 0);
        border-color: #ff4444 !important;
      }
    }

    .finroast-highlight-btn {
      border: 3px solid #ff4444 !important;
      animation: finroast-pulse 1.5s infinite !important;
      position: relative !important;
      z-index: 999999 !important;
      transform: scale(1.03) !important;
      transition: transform 0.2s ease !important;
    }

    .finroast-toast-banner {
      position: fixed !important;
      bottom: 24px !important;
      right: 24px !important;
      z-index: 9999999 !important;
      background: rgba(15, 23, 42, 0.95) !important;
      border: 1px solid rgba(244, 63, 94, 0.4) !important;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5) !important;
      border-radius: 16px !important;
      padding: 18px 22px !important;
      max-width: 380px !important;
      color: #f8fafc !important;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
      backdrop-filter: blur(12px) !important;
    }

    .finroast-toast-header {
      display: flex !important;
      align-items: center !important;
      gap: 10px !important;
      margin-bottom: 8px !important;
    }

    .finroast-toast-title {
      font-weight: 800 !important;
      font-size: 15px !important;
      color: #fb7185 !important;
      letter-spacing: -0.01em !important;
    }

    .finroast-toast-body {
      font-size: 13px !important;
      line-height: 1.45 !important;
      color: #cbd5e1 !important;
    }
  `;
  document.head.appendChild(styleEl);

  function createToastNotification(vendorName) {
    if (document.getElementById("finroast-toast")) return;

    const toast = document.createElement("div");
    toast.id = "finroast-toast";
    toast.className = "finroast-toast-banner";
    toast.innerHTML = `
      <div class="finroast-toast-header">
        <span style="font-size: 18px;">🔥</span>
        <span class="finroast-toast-title">FinRoast Co-Pilot Active</span>
      </div>
      <div class="finroast-toast-body">
        We've brought you to the cancellation step for <strong>${vendorName || "your subscription"}</strong>! Click the highlighted button below to complete your cancellation safely.
      </div>
    `;
    document.body.appendChild(toast);
  }

  function findDestructiveButton() {
    const candidateTexts = [
      "end membership",
      "cancel subscription",
      "cancel membership",
      "confirm cancellation",
      "cancel auto-renew",
      "cancel plan",
      "finish cancellation",
      "continue to cancel",
      "cancel"
    ];

    const elements = Array.from(document.querySelectorAll("button, a, input[type='submit'], div[role='button']"));
    
    for (const el of elements) {
      const text = (el.innerText || el.textContent || el.value || "").toLowerCase().trim();
      const ariaLabel = (el.getAttribute("aria-label") || "").toLowerCase();
      
      for (const pattern of candidateTexts) {
        if (text.includes(pattern) || ariaLabel.includes(pattern)) {
          return el;
        }
      }
    }

    return null;
  }

  function scanAndHighlight() {
    chrome.storage.local.get(["activeTask"], (result) => {
      const activeTask = result.activeTask;
      const vendorName = activeTask ? activeTask.vendor : "";

      const btn = findDestructiveButton();
      if (btn) {
        console.log("[FinRoast Content Script] Found destructive cancellation button:", btn);
        btn.classList.add("finroast-highlight-btn");
        createToastNotification(vendorName);
        
        // Scroll target button smoothly into view
        btn.scrollIntoView({ behavior: "smooth", block: "center" });

        // Add click listener to mark task complete in backend
        btn.addEventListener("click", () => {
          if (activeTask && activeTask.id) {
            fetch(`http://localhost:8055/api/cancellation-tasks/${activeTask.id}/complete`, {
              method: "POST"
            }).catch(() => {});
          }
        }, { once: true });
      }
    });
  }

  // Scan initially and observe dynamic DOM changes
  scanAndHighlight();
  const observer = new MutationObserver(() => scanAndHighlight());
  observer.observe(document.body, { childList: true, subtree: true });
})();
