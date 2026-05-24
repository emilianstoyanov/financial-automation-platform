/**
 * Swagger UI does not clear <input type="file"> on Reset (browser security).
 * Clear file inputs in the active operation block when Reset is clicked.
 */
(function () {
  function clearFileInputs(opblock) {
    if (!opblock) return;
    opblock.querySelectorAll('input[type="file"]').forEach(function (input) {
      input.value = "";
    });
  }

  document.addEventListener(
    "click",
    function (event) {
      var button = event.target.closest("button");
      if (!button) return;

      var label = (button.textContent || "").trim().toLowerCase();
      if (label !== "reset") return;

      var opblock = button.closest(".opblock");
      if (!opblock) return;

      // Run after Swagger UI's own reset handler
      setTimeout(function () {
        clearFileInputs(opblock);
      }, 0);
      setTimeout(function () {
        clearFileInputs(opblock);
      }, 50);
    },
    true
  );
})();
