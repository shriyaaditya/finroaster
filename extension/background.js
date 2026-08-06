// FinRoast Co-Pilot Background Service Worker
const BACKEND_URL = "http://localhost:8055";
const processedTaskIds = new Set();

console.log("[FinRoast Extension] Background service worker initialized.");

async function pollPendingTasks() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/cancellation-tasks`);
    if (!res.ok) return;

    const data = await res.json();
    const tasks = data.tasks || [];

    for (const task of tasks) {
      if (!processedTaskIds.has(task.id)) {
        processedTaskIds.add(task.id);
        console.log(`[FinRoast Extension] New task detected:`, task);
        
        // Save active task in chrome.storage for content script access
        await chrome.storage.local.set({ activeTask: task });

        // Open target vendor page in a new foreground tab
        chrome.tabs.create({ url: task.target_url, active: true }, (tab) => {
          console.log(`[FinRoast Extension] Opened tab ${tab.id} for target URL: ${task.target_url}`);
        });
      }
    }
  } catch (err) {
    console.error("[FinRoast Extension] Error polling cancellation tasks:", err);
  }
}

// Poll every 3 seconds
setInterval(pollPendingTasks, 3000);
pollPendingTasks();
