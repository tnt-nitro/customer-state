(function () {
    var level2 = document.querySelector("[data-level='2']");
    var level3 = document.querySelector("[data-level='3']");
    var level3Choices = level3 ? level3.querySelector("[data-choice-group]") : null;

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
})();
