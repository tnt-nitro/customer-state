(function () {
    var level1 = document.querySelector("[data-level='1']");
    var level2 = document.querySelector("[data-level='2']");
    var level3 = document.querySelector("[data-level='3']");
    var level4 = document.querySelector("[data-level='4']");
    var level3Groups = level3 ? level3.querySelector("[data-level3-groups]") : null;
    var level4Groups = level4 ? level4.querySelector("[data-level4-groups]") : null;
    var level1Next = document.querySelector("[data-level-next='1']");
    var level2Next = document.querySelector("[data-level-next='2']");
    var saveButton = document.querySelector("[data-save-entry]");
    var saveNotice = document.querySelector("[data-save-notice]");
    var heading = document.querySelector("[data-step-heading]");
    var headSub = document.querySelector("[data-head-sub]");
    var busy = false;
    var entryHeld = false;
    var entryHoldTimer = null;
    var summaryTimer = null;
    var startedAt = null;
    var level1CompletedAt = null;
    var level2OpenedAt = null;
    var level2StartedAt = null;
    var level2CompletedAt = null;
    var level3OpenedAt = null;
    var level3StartedAt = null;

    var headings = {
        1: "Wie ist der Kunde auf uns aufmerksam geworden?",
        2: "Für was interessierte sich der Kunde?",
        3: "Wofür interessiert sich der Kunde?",
        4: "Erfasste Auswahl"
    };

    var interestsByBike = {
        "MTB": ["Specialized", "Produkt fehlte", "Leasing", "Kauf", "Reparatur"],
        "E-MTB": ["Specialized", "PIVOT", "AMFLOW", "Produkt fehlte", "Leasing", "Kauf", "Reparatur"],
        "Gravel": ["PIVOT", "Specialized", "Produkt fehlte", "Leasing", "Kauf", "Reparatur"],
        "E-Gravel": ["Specialized", "PIVOT", "Produkt fehlte", "Leasing", "Kauf", "Reparatur"],
        "Rennrad": ["Specialized", "Produkt fehlte"],
        "Triathlon": ["Specialized", "Produkt fehlte"],
        "Kinderrad": ["woom", "Produkt fehlte", "Leasing", "Kauf", "Reparatur"],
        "Lastenrad": ["Riese & Müller", "Produkt fehlte", "Leasing", "Kauf", "Reparatur"],
        "Trekking": ["Riese & Müller", "Specialized", "Produkt fehlte", "Leasing", "Kauf", "Reparatur"],
        "Trekking vollgefedert": ["Riese & Müller", "Specialized", "AMFLOW", "Produkt fehlte", "Leasing", "Kauf", "Reparatur"],
        "Bekleidung": ["Helm", "Trikot", "Radhose", "Handschuhe", "Schuhe", "Regenbekleidung", "Jacke/Weste", "Brille", "Sonstiges"],
        "Zubehör": ["Luftpumpe", "Beleuchtung", "Schutzbleche", "Schlösser", "Griffe", "Pflege und Reinigungsprodukte"]
    };

    function selectedIn(root) {
        if (!root) {
            return [];
        }
        return Array.from(root.querySelectorAll(".choice")).filter(function (button) {
            return button.getAttribute("aria-pressed") === "true";
        }).map(function (button) {
            return button.textContent;
        });
    }

    function hideNotice() {
        if (!saveNotice) {
            return;
        }
        saveNotice.textContent = "";
        saveNotice.removeAttribute("data-state");
    }

    function showNotice(message, state) {
        if (!saveNotice) {
            return;
        }
        saveNotice.textContent = message;
        saveNotice.setAttribute("data-state", state);
    }

    function visibleLevel() {
        if (level4 && !level4.hidden) {
            return 4;
        }
        if (level3 && !level3.hidden) {
            return 3;
        }
        if (level2 && !level2.hidden) {
            return 2;
        }
        return 1;
    }

    function runningSince(level) {
        if (level === 1) {
            return startedAt ? Date.parse(startedAt) : null;
        }
        if (level === 2) {
            if (level2StartedAt) {
                return Date.parse(level2StartedAt);
            }
            return level2OpenedAt ? Date.parse(level2OpenedAt) : null;
        }
        if (level3StartedAt) {
            return Date.parse(level3StartedAt);
        }
        return level3OpenedAt ? Date.parse(level3OpenedAt) : null;
    }

    function elapsedMs(level) {
        var since = runningSince(level);
        if (since === null || Number.isNaN(since)) {
            return 0;
        }
        return Math.max(0, Date.now() - since);
    }

    function paintDots() {
        var level = visibleLevel();
        document.querySelectorAll("[data-dot]").forEach(function (dot) {
            var number = Number(dot.getAttribute("data-dot"));
            var on = number <= Math.min(level, 3);
            dot.classList.toggle("is-on", on);
            dot.disabled = level >= 4 || !on;
            if (level < 4 && number === level) {
                dot.setAttribute("aria-current", "true");
            } else {
                dot.removeAttribute("aria-current");
            }
        });
    }

    function showLevel(level) {
        if (level1) {
            level1.hidden = level !== 1;
        }
        if (level2) {
            level2.hidden = level !== 2;
        }
        if (level3) {
            level3.hidden = level !== 3;
        }
        if (level4) {
            level4.hidden = level !== 4;
        }
        if (level1Next) {
            level1Next.hidden = level !== 1;
        }
        if (level2Next) {
            level2Next.hidden = level !== 2;
        }
        if (saveButton) {
            saveButton.hidden = level !== 3;
        }
        if (heading) {
            heading.textContent = headings[level];
        }
        if (headSub) {
            var names = level === 3 ? selectedIn(level2) : [];
            headSub.textContent = names.length ? names.join(" · ") : "";
        }
        paintDots();
        updateControls();
    }

    function statusPayload() {
        var details = {};
        if (level3Groups) {
            level3Groups.querySelectorAll("[data-interest]").forEach(function (group) {
                details[group.getAttribute("data-interest")] = selectedIn(group);
            });
        }
        return {
            level1: selectedIn(level1),
            level2: selectedIn(level2).map(function (name) {
                return {
                    value: name,
                    level3: details[name] || []
                };
            })
        };
    }

    function currentRecord() {
        var groups = level3Groups ? Array.from(level3Groups.querySelectorAll("[data-interest]")) : [];
        return {
            level1: selectedIn(level1),
            level2: groups.map(function (group) {
                return {
                    value: group.getAttribute("data-interest"),
                    level3: selectedIn(group)
                };
            }),
            started_at: startedAt,
            level1_completed_at: level1CompletedAt,
            level2_opened_at: level2OpenedAt,
            level2_started_at: level2StartedAt,
            level2_completed_at: level2CompletedAt,
            level3_opened_at: level3OpenedAt,
            level3_started_at: level3StartedAt
        };
    }

    function recordComplete(record) {
        if (!record.level1.length || !record.level2.length) {
            return false;
        }
        return record.level2.every(function (block) {
            return block.level3.length > 0;
        });
    }

    function levelHasSelection(level) {
        if (level === 1) {
            return selectedIn(level1).length > 0;
        }
        if (level === 2) {
            return selectedIn(level2).length > 0;
        }
        return statusPayload().level2.some(function (block) {
            return block.level3.length > 0;
        });
    }

    function updateControls() {
        if (level1Next) {
            level1Next.disabled = entryHeld || selectedIn(level1).length === 0;
        }
        if (level2Next) {
            level2Next.disabled = selectedIn(level2).length === 0;
        }
        if (saveButton) {
            saveButton.disabled = visibleLevel() !== 3 || !recordComplete(currentRecord());
        }
    }

    function clearChoices(root) {
        if (!root) {
            return;
        }
        root.querySelectorAll(".choice").forEach(function (button) {
            button.setAttribute("aria-pressed", "false");
        });
    }

    function clearFrom(level) {
        if (level <= 1) {
            clearChoices(level1);
            clearChoices(level2);
            if (level3Groups) {
                level3Groups.replaceChildren();
            }
            startedAt = null;
            level1CompletedAt = null;
            level2OpenedAt = null;
            level2StartedAt = null;
            level2CompletedAt = null;
            level3OpenedAt = null;
            level3StartedAt = null;
            return;
        }
        if (level === 2) {
            clearChoices(level2);
            if (level3Groups) {
                level3Groups.replaceChildren();
            }
            level2StartedAt = null;
            level2CompletedAt = null;
            level3OpenedAt = null;
            level3StartedAt = null;
            level2OpenedAt = new Date().toISOString();
            return;
        }
        if (level3Groups) {
            level3Groups.querySelectorAll(".choice").forEach(function (button) {
                button.setAttribute("aria-pressed", "false");
            });
        }
        level3StartedAt = null;
        level3OpenedAt = new Date().toISOString();
    }

    function setLast(text, kind) {
        var lastCapture = document.querySelector("[data-last-capture]");
        if (!lastCapture) {
            return;
        }
        lastCapture.textContent = text ? "Letzte Erfassung: " + text : "";
        lastCapture.classList.toggle("is-saved", kind === "saved");
        lastCapture.classList.toggle("is-abort", kind === "abort");
    }

    function syncLevel3() {
        if (!level3 || !level3Groups) {
            return;
        }
        var kept = {};
        level3Groups.querySelectorAll("[data-interest]").forEach(function (group) {
            kept[group.getAttribute("data-interest")] = selectedIn(group);
        });
        var names = selectedIn(level2);
        level3Groups.replaceChildren();
        names.forEach(function (name) {
            var labels = interestsByBike[name];
            if (!labels) {
                return;
            }
            var group = document.createElement("div");
            group.className = "detail-group";
            group.setAttribute("data-interest", name);
            var title = document.createElement("h3");
            title.textContent = name;
            group.appendChild(title);
            var choices = document.createElement("div");
            choices.className = "choices";
            labels.forEach(function (label) {
                var button = document.createElement("button");
                button.type = "button";
                button.className = "choice";
                var active = kept[name] && kept[name].indexOf(label) !== -1;
                button.setAttribute("aria-pressed", active ? "true" : "false");
                button.textContent = label;
                button.addEventListener("click", function () {
                    if (!level3StartedAt) {
                        level3StartedAt = new Date().toISOString();
                    }
                    var pressed = button.getAttribute("aria-pressed") === "true";
                    button.setAttribute("aria-pressed", pressed ? "false" : "true");
                    updateControls();
                    hideNotice();
                });
                choices.appendChild(button);
            });
            group.appendChild(choices);
            level3Groups.appendChild(group);
        });
        updateControls();
    }

    function bindToggle(section, onSelect) {
        section.querySelectorAll(".choice").forEach(function (button) {
            button.addEventListener("click", function () {
                if (section === level1 && entryHeld) {
                    return;
                }
                var pressed = button.getAttribute("aria-pressed") === "true";
                button.setAttribute("aria-pressed", pressed ? "false" : "true");
                if (onSelect) {
                    onSelect();
                }
                updateControls();
                hideNotice();
            });
        });
    }

    function goToLevel(target) {
        var from = visibleLevel();
        if (busy || from >= 4 || target > from) {
            return;
        }
        var hadSelection = levelHasSelection(from);
        var elapsed = Math.floor(elapsedMs(from) / 1000);
        if (target === from && !hadSelection && elapsed === 0) {
            return;
        }
        var status = statusPayload();
        var body = {
            from_level: from,
            to_level: target,
            elapsed_seconds: elapsed,
            had_selection: hadSelection,
            level1: status.level1,
            level2: status.level2
        };
        busy = true;
        fetch("/api/korrekturen", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(body)
        }).then(function (response) {
            if (!response.ok) {
                throw new Error("correction failed");
            }
            clearFrom(target);
            if (target === 1) {
                setLast("Abgebrochen", "abort");
            }
            showLevel(target);
            hideNotice();
        }).catch(function () {
            showNotice("Die Korrektur konnte nicht gespeichert werden.", "error");
        }).finally(function () {
            busy = false;
            updateControls();
        });
    }

    if (level1) {
        bindToggle(level1, function () {
            if (!startedAt) {
                startedAt = new Date().toISOString();
            }
        });
    }

    if (level2) {
        bindToggle(level2, function () {
            if (!level2StartedAt) {
                level2StartedAt = new Date().toISOString();
            }
        });
    }

    if (level1Next) {
        level1Next.addEventListener("click", function () {
            if (level1Next.disabled || busy || selectedIn(level1).length === 0) {
                return;
            }
            var now = new Date().toISOString();
            level1CompletedAt = now;
            level2OpenedAt = now;
            level2StartedAt = null;
            showLevel(2);
            hideNotice();
        });
    }

    if (level2Next) {
        level2Next.addEventListener("click", function () {
            if (level2Next.disabled || busy || selectedIn(level2).length === 0) {
                return;
            }
            var now = new Date().toISOString();
            level2CompletedAt = now;
            level3OpenedAt = now;
            level3StartedAt = null;
            syncLevel3();
            showLevel(3);
            hideNotice();
        });
    }

    document.querySelectorAll("[data-dot]").forEach(function (dot) {
        dot.addEventListener("click", function () {
            if (dot.disabled) {
                return;
            }
            goToLevel(Number(dot.getAttribute("data-dot")));
        });
    });

    function releaseNewEntry() {
        entryHeld = false;
        entryHoldTimer = null;
        if (level1) {
            level1.querySelectorAll(".choice").forEach(function (button) {
                button.disabled = false;
            });
        }
        updateControls();
    }

    function holdNewEntry() {
        entryHeld = true;
        if (level1) {
            level1.querySelectorAll(".choice").forEach(function (button) {
                button.disabled = true;
            });
        }
        updateControls();
        if (entryHoldTimer) {
            window.clearTimeout(entryHoldTimer);
        }
        entryHoldTimer = window.setTimeout(releaseNewEntry, 2000);
    }

    function summaryButton(label) {
        var button = document.createElement("button");
        button.type = "button";
        button.className = "choice";
        button.disabled = true;
        button.setAttribute("aria-pressed", "true");
        button.textContent = label;
        return button;
    }

    function showSummary(record) {
        if (!level4Groups) {
            resetForm();
            holdNewEntry();
            return;
        }
        level4Groups.replaceChildren();
        var details = [];
        record.level2.forEach(function (block) {
            block.level3.forEach(function (label) {
                details.push(label);
            });
        });
        [
            record.level1,
            record.level2.map(function (block) {
                return block.value;
            }),
            details
        ].forEach(function (labels) {
            if (!labels.length) {
                return;
            }
            var block = document.createElement("section");
            block.className = "summary-sector";
            var choices = document.createElement("div");
            choices.className = "choices";
            labels.forEach(function (label) {
                choices.appendChild(summaryButton(label));
            });
            block.appendChild(choices);
            level4Groups.appendChild(block);
        });
        showLevel(4);
        if (summaryTimer) {
            window.clearTimeout(summaryTimer);
        }
        summaryTimer = window.setTimeout(function () {
            summaryTimer = null;
            resetForm();
            holdNewEntry();
        }, 3000);
    }

    function resetForm() {
        if (summaryTimer) {
            window.clearTimeout(summaryTimer);
            summaryTimer = null;
        }
        if (level4Groups) {
            level4Groups.replaceChildren();
        }
        clearFrom(1);
        showLevel(1);
    }

    if (saveButton) {
        saveButton.addEventListener("click", function () {
            if (saveButton.disabled || busy) {
                return;
            }
            var record = currentRecord();
            if (!recordComplete(record)) {
                return;
            }
            busy = true;
            fetch("/api/erfassungen", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(record)
            }).then(function (response) {
                if (!response.ok) {
                    throw new Error("save failed");
                }
                return response.json();
            }).then(function (payload) {
                hideNotice();
                showSummary(record);
                if (payload && payload.completed_label) {
                    setLast(payload.completed_label, "saved");
                }
            }).catch(function () {
                showNotice("Die Erfassung konnte nicht gespeichert werden.", "error");
            }).finally(function () {
                busy = false;
                updateControls();
            });
        });
    }

    showLevel(1);
})();
