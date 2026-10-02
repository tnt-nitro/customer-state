(function () {
    var group = document.querySelector("[data-choice-group]");
    if (!group) {
        return;
    }

    var buttons = group.querySelectorAll(".choice");

    buttons.forEach(function (button) {
        button.addEventListener("click", function () {
            buttons.forEach(function (other) {
                other.setAttribute("aria-pressed", other === button ? "true" : "false");
            });
        });
    });
})();
