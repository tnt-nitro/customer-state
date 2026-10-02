(function () {
    var level2 = document.querySelector("[data-level='2']");
    var groups = document.querySelectorAll("[data-choice-group]");

    groups.forEach(function (group) {
        var buttons = group.querySelectorAll(".choice");
        var revealsLevel2 = group.closest("[data-level='1']") !== null;

        buttons.forEach(function (button) {
            button.addEventListener("click", function () {
                buttons.forEach(function (other) {
                    other.setAttribute("aria-pressed", other === button ? "true" : "false");
                });

                if (revealsLevel2 && level2) {
                    level2.hidden = false;
                }
            });
        });
    });
})();
