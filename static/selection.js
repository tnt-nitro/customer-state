(function () {
    var level2 = document.querySelector("[data-level='2']");
    var level3 = document.querySelector("[data-level='3']");
    var level3Choices = level3 ? level3.querySelector("[data-choice-group]") : null;
    var saveButton = document.querySelector("[data-save-entry]");
    var saveNotice = document.querySelector("[data-save-notice]");
    var saving = false;

    var interestsByBike = {
        "MTB": ["Specialized", "Leasing", "Kauf", "Reparatur"],
        "E-MTB": ["Specialized", "PIVOT", "AMFLOW", "Leasing", "Kauf", "Reparatur"],
        "Gravel": ["PIVOT", "Specialized", "Leasing", "Kauf", "Reparatur"],
        "E-Gravel": ["Specialized", "PIVOT", "Leasing", "Kauf", "Reparatur"],
        "Kinderrad": ["woom", "Leasing", "Kauf", "Reparatur"],
        "Lastenrad": ["Riese & Müller", "Leasing", "Kauf", "Reparatur"],
        "Trekking": ["Riese & Müller", "Specialized", "Leasing", "Kauf", "Reparatur"],
        "Trekking vollgefedert": ["Riese & Müller", "Specialized", "AMFLOW", "Leasing", "Kauf", "Reparatur"],
        "Bekleidung": ["Helm", "Trikot", "Radhose", "Handschuhe", "Schuhe", "Regenbekleidung", "Jacke/Weste", "Brille", "Sonstiges"],
        "Werkstatt": ["Inspektion", "Reparatur", "Reklamation", "Tuning", "Umbau", "Diagnose/Fehlersuche", "Unfall/Schaden", "Beratung", "Sonstiges"]
    };

    function selectSingle(buttons, selected) {
        buttons.forEach(function (other) {
            other.setAttribute("aria-pressed", other === selected ? "true" : "false");
        });
    }

    function showLevel3(bike) {
        var labels = interestsByBike[bike];
        if (!level3 || !level3Choices || !labels) {
            return;
        }

        level3Choices.replaceChildren();
        labels.forEach(function (label) {
            var button = document.createElement("button");
            button.type = "button";
            button.className = "choice";
            button.setAttribute("aria-pressed", "false");
            button.textContent = label;
            button.addEventListener("click", function () {
                var selected = button.getAttribute("aria-pressed") === "true";
                button.setAttribute("aria-pressed", selected ? "false" : "true");
                updateSaveButton();
                hideNotice();
            });
            level3Choices.appendChild(button);
        });
        level3.hidden = false;
    }

    function bindSingle(section, onChange) {
        var group = section.querySelector("[data-choice-group]");
        if (!group) {
            return;
        }

        var buttons = group.querySelectorAll(".choice");
        buttons.forEach(function (button) {
            button.addEventListener("click", function () {
                var alreadySelected = button.getAttribute("aria-pressed") === "true";
                selectSingle(buttons, button);
                if (!alreadySelected && onChange) {
                    onChange(button.textContent);
                }
                updateSaveButton();
                hideNotice();
            });
        });
    }

    var level1 = document.querySelector("[data-level='1']");
    if (level1) {
        bindSingle(level1, function () {
            if (level2) {
                level2.hidden = false;
            }
        });
    }

    if (level2) {
        bindSingle(level2, showLevel3);
    }

    function selectedLabels(section) {
        if (!section) {
            return [];
        }

        return Array.from(section.querySelectorAll(".choice")).filter(function (button) {
            return button.getAttribute("aria-pressed") === "true";
        }).map(function (button) {
            return button.textContent;
        });
    }

    function currentRecord() {
        var level1Labels = selectedLabels(document.querySelector("[data-level='1']"));
        var level2Labels = selectedLabels(level2);

        return {
            level1: level1Labels[0] || null,
            level2: level2Labels[0] || null,
            level3: selectedLabels(level3)
        };
    }

    function updateSaveButton() {
        if (!saveButton) {
            return;
        }

        var record = currentRecord();
        saveButton.disabled = !(record.level1 && record.level2 && record.level3.length > 0);
    }

    function hideNotice() {
        if (!saveNotice) {
            return;
        }
        saveNotice.hidden = true;
        saveNotice.textContent = "";
        saveNotice.removeAttribute("data-state");
    }

    function showNotice(message, state) {
        if (!saveNotice) {
            return;
        }
        saveNotice.textContent = message;
        saveNotice.setAttribute("data-state", state);
        saveNotice.hidden = false;
    }

    function clearPressed(section) {
        if (!section) {
            return;
        }
        section.querySelectorAll(".choice").forEach(function (button) {
            button.setAttribute("aria-pressed", "false");
        });
    }

    function resetForm() {
        clearPressed(level1);
        clearPressed(level2);
        if (level2) {
            level2.hidden = true;
        }
        if (level3Choices) {
            level3Choices.replaceChildren();
        }
        if (level3) {
            level3.hidden = true;
        }
        if (saveButton) {
            saveButton.disabled = true;
        }
    }

    if (saveButton) {
        saveButton.addEventListener("click", function () {
            if (saveButton.disabled || saving) {
                return;
            }

            var record = currentRecord();
            saving = true;
            fetch("/api/erfassungen", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(record)
            }).then(function (response) {
                if (!response.ok) {
                    throw new Error("save failed");
                }
                return response.json();
            }).then(function () {
                resetForm();
                showNotice("Erfassung gespeichert", "ok");
            }).catch(function () {
                showNotice("Die Erfassung konnte nicht gespeichert werden.", "error");
            }).finally(function () {
                saving = false;
                updateSaveButton();
            });
        });
    }

    updateSaveButton();
})();
