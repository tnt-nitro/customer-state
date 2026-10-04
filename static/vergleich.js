(function () {
    function fitHeatmaps() {
        document.querySelectorAll(".compare-page .heat-slot .cal-scroll").forEach(function (scroll) {
            var cal = scroll.querySelector(".cal");
            if (!cal) {
                return;
            }
            cal.style.transform = "none";
            scroll.style.height = "";
            scroll.style.overflowX = "";
            var grid = cal.querySelector(".cal-grid");
            var names = cal.querySelector(".cal-names");
            var needed = (grid ? grid.offsetWidth : 0) + (names ? names.offsetWidth : 0) + 2;
            var available = scroll.clientWidth;
            if (needed <= available || available <= 0) {
                return;
            }
            var scale = available / needed;
            cal.style.transformOrigin = "top left";
            cal.style.transform = "scale(" + scale + ")";
            scroll.style.height = Math.ceil(cal.getBoundingClientRect().height) + "px";
            scroll.style.overflowX = "hidden";
        });
    }

    fitHeatmaps();
    window.addEventListener("resize", fitHeatmaps);

    document.querySelectorAll("[data-vergleich-filter], [data-vergleich-values]").forEach(function (form) {
        form.querySelectorAll("select, input[type='radio'], input[type='date']").forEach(function (field) {
            field.addEventListener("change", function () {
                if (typeof form.requestSubmit === "function") {
                    form.requestSubmit();
                } else {
                    form.submit();
                }
            });
        });
    });
})();
