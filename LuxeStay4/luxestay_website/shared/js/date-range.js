(function() {
  function dayAfter(value) {
    if (!value) return "";
    const nextDate = new Date(value + "T00:00:00");
    nextDate.setDate(nextDate.getDate() + 1);
    return nextDate.toISOString().slice(0, 10);
  }

  function bindDateRange(form) {
    const checkIn = form.querySelector('input[name="checkIn"]');
    const checkOut = form.querySelector('input[name="checkOut"]');
    if (!checkIn || !checkOut) return;

    function syncCheckOutLimit() {
      const minimumCheckOut = dayAfter(checkIn.value);
      checkOut.min = minimumCheckOut;
      if (minimumCheckOut && checkOut.value && checkOut.value < minimumCheckOut) {
        checkOut.value = "";
      }
    }

    syncCheckOutLimit();
    checkIn.addEventListener("change", syncCheckOutLimit);
  }

  document.addEventListener("DOMContentLoaded", function() {
    document.querySelectorAll("form").forEach(bindDateRange);
  });
}());
