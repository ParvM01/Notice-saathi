const saveButton = document.getElementById("saveButton");
const statusMessage = document.getElementById("statusMessage");

const checkboxes = document.querySelectorAll(
  'input[type="checkbox"]'
);

// Save selected sections
saveButton.addEventListener("click", async () => {
  const selectedSections = [];

  checkboxes.forEach((checkbox) => {
    if (checkbox.checked) {
      selectedSections.push(checkbox.value);
    }
  });

  if (selectedSections.length === 0) {
    statusMessage.textContent =
      "Kam se kam ek section select karein.";

    return;
  }

  await chrome.storage.local.set({
    selectedSections: selectedSections
  });

  statusMessage.textContent =
    "Preferences successfully save ho gayi!";
});

// Load previously saved preferences
chrome.storage.local.get(
  ["selectedSections"],
  (result) => {
    const savedSections = result.selectedSections || [];

    checkboxes.forEach((checkbox) => {
      checkbox.checked = savedSections.includes(
        checkbox.value
      );
    });
  }
);
