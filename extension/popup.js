const API = "http://127.0.0.1:5000";

const categoriesDiv = document.getElementById("categories");
const noticesDiv = document.getElementById("notices");
const statusMessage = document.getElementById("statusMessage");
const saveButton = document.getElementById("saveButton");
const refreshButton = document.getElementById("refreshButton");

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API}${path}`, options);
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || "Request failed");
  }

  return data;
}

async function loadCategories() {
  try {
    const data = await apiRequest("/categories");
    const saved = await chrome.storage.local.get("selectedSections");
    const selected = saved.selectedSections || data.categories;

    categoriesDiv.replaceChildren();

    data.categories
    .filter(category => category !== "general")
    .forEach(category => {
      const label = document.createElement("label");
      const checkbox = document.createElement("input");

      checkbox.type = "checkbox";
      checkbox.value = category;
      checkbox.checked = selected.includes(category);

      label.append(checkbox, document.createTextNode(
        category.replaceAll("_", " ").replaceAll("-", " ")
      ));

      categoriesDiv.appendChild(label);
    });
  } catch (error) {
    categoriesDiv.textContent = "Could not load categories: " + error.message;
  }
}

saveButton.addEventListener("click", async () => {
  const selectedSections = Array.from(
    categoriesDiv.querySelectorAll('input[type="checkbox"]:checked')
  ).map(checkbox => checkbox.value);

  if (!selectedSections.length) {
    statusMessage.textContent = "Kam se kam ek category select karein.";
    return;
  }

  try {
    await apiRequest("/preferences", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ categories: selectedSections })
    });

    await chrome.storage.local.set({
      selectedSections
    });

    statusMessage.textContent = "Preferences successfully saved!";
    loadNotices();
  } catch (error) {
    statusMessage.textContent = "Error: " + error.message;
  }
});

function createNoticeCard(notice) {
  const card = document.createElement("div");
  card.className = "notice-card";

  const title = document.createElement("h3");
  title.textContent = notice.title;

  const category = document.createElement("p");
  category.textContent = "Category: " + notice.category;

  const explainButton = document.createElement("button");
  explainButton.textContent = "Explain in Hinglish";

  const explanation = document.createElement("div");
  explanation.className = "explanation";

  explainButton.addEventListener("click", async () => {
    explainButton.disabled = true;
    explainButton.textContent = "Generating explanation...";

    try {
      const result = await apiRequest("/explain-notice", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notice_id: notice.id })
      });

      explanation.textContent = result.hinglish_explanation;
      explanation.hidden = false;
    } catch (error) {
      explanation.textContent = "Error: " + error.message;
      explanation.hidden = false;
    } finally {
      explainButton.disabled = false;
      explainButton.textContent = "Explain in Hinglish";
    }
  });

  const officialLink = document.createElement("a");
  officialLink.href = notice.url;
  officialLink.textContent = "View Official Notice";
  officialLink.target = "_blank";
  officialLink.rel = "noopener noreferrer";

  card.append(title, category, explainButton, explanation, officialLink);

  return card;
}

async function loadNotices() {
  noticesDiv.textContent = "Loading notices...";

  try {
    const data = await apiRequest("/my-notices");
    noticesDiv.replaceChildren();

    if (!data.notices.length) {
      noticesDiv.textContent = "No notices found for selected categories.";
      return;
    }

    data.notices.forEach(notice => {
      noticesDiv.appendChild(createNoticeCard(notice));
    });
  } catch (error) {
    noticesDiv.textContent = "Could not load notices: " + error.message;
  }
}

refreshButton.addEventListener("click", loadNotices);

async function initialize() {
  await loadCategories();
  await loadNotices();
}

initialize();