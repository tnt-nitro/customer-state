(function () {
    var form = document.querySelector("[data-auswertung-filter]");
    if (!form) {
        return;
    }

    var customDates = form.querySelectorAll("[data-custom-date]");

    function selectedZeitraum() {
        var checked = form.querySelector("[name='zeitraum']:checked");
        return checked ? checked.value : "";
    }

    function syncCustomDates() {
        var custom = selectedZeitraum() === "custom";
        customDates.forEach(function (field) {
            field.disabled = !custom;
        });
    }

    syncCustomDates();

    form.querySelectorAll("input[name='zeitraum']").forEach(function (field) {
        var label = field.closest("label") || field;
        label.addEventListener("mousedown", function () {
            field.dataset.wasChecked = field.checked ? "1" : "";
        });
        label.addEventListener("click", function (event) {
            if (field.dataset.wasChecked !== "1" || field.value === "gesamt") {
                return;
            }
            event.preventDefault();
            var gesamt = form.querySelector("input[name='zeitraum'][value='gesamt']");
            if (!gesamt) {
                return;
            }
            gesamt.checked = true;
            field.dataset.wasChecked = "";
            var stand = form.querySelector("[data-stand]");
            if (stand) {
                stand.value = "";
            }
            syncCustomDates();
            if (typeof form.requestSubmit === "function") {
                form.requestSubmit();
            } else {
                form.submit();
            }
        });
    });

    form.querySelectorAll("select, input[type='radio'], input[type='checkbox']").forEach(function (field) {
        field.addEventListener("change", function () {
            syncCustomDates();
            if (field.name === "zeitraum") {
                var stand = form.querySelector("[data-stand]");
                if (stand) {
                    stand.value = "";
                }
            }
            if (field.name === "zeitraum" && field.value === "custom") {
                return;
            }
            if (typeof form.requestSubmit === "function") {
                form.requestSubmit();
            } else {
                form.submit();
            }
        });
    });
})();
