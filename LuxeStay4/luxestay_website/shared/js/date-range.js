(function() {
  function pad(value) {
    return String(value).padStart(2, "0");
  }

  function formatDate(date) {
    return date.getFullYear() + "-" + pad(date.getMonth() + 1) + "-" + pad(date.getDate());
  }

  function parseDateInput(value) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value || "")) return null;
    const parts = value.split("-").map(Number);
    return new Date(parts[0], parts[1] - 1, parts[2]);
  }

  function addDays(value, days) {
    const baseDate = parseDateInput(value);
    if (!baseDate) return "";
    baseDate.setDate(baseDate.getDate() + days);
    return formatDate(baseDate);
  }

  function todayValue() {
    return formatDate(new Date());
  }

  function bindDateRange(form) {
    const checkIn = form.querySelector('input[name="checkIn"]');
    const checkOut = form.querySelector('input[name="checkOut"]');
    if (!checkIn || !checkOut) return;

    const today = todayValue();
    checkIn.min = today;

    function syncCheckInLimit() {
      if (checkIn.value && checkIn.value < today) {
        checkIn.value = today;
      }
    }

    function syncCheckOutLimit() {
      syncCheckInLimit();
      const minimumCheckOut = checkIn.value ? addDays(checkIn.value, 1) : addDays(today, 1);
      checkOut.min = minimumCheckOut;
      if (minimumCheckOut && checkOut.value && checkOut.value < minimumCheckOut) {
        checkOut.value = "";
      }
    }

    syncCheckOutLimit();
    checkIn.addEventListener("change", syncCheckOutLimit);
    checkOut.addEventListener("change", syncCheckOutLimit);
  }

  function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

  function bindGuestCounter(counter) {
    const form = counter.closest("form");
    const input = form ? form.querySelector('input[name="guests"]') : null;
    const display = counter.querySelector(".counter-num");
    const minus = counter.querySelector("#guests-minus, [data-guests-action='minus']");
    const plus = counter.querySelector("#guests-plus, [data-guests-action='plus']");
    if (!input || !display || !minus || !plus) return;

    const min = Number(counter.dataset.min || input.min || 1);
    const max = Number(counter.dataset.max || input.max || 10);

    function currentValue() {
      const parsed = Number(input.value || display.textContent || min);
      return Number.isFinite(parsed) ? clamp(parsed, min, max) : min;
    }

    function render(value) {
      const guests = clamp(value, min, max);
      input.value = String(guests);
      display.textContent = String(guests);
      minus.disabled = guests <= min;
      plus.disabled = guests >= max;
    }

    minus.addEventListener("click", function() {
      render(currentValue() - 1);
    });

    plus.addEventListener("click", function() {
      render(currentValue() + 1);
    });

    render(currentValue());
  }

  document.addEventListener("DOMContentLoaded", function() {
    document.querySelectorAll("form").forEach(bindDateRange);
    document.querySelectorAll(".guests-counter").forEach(bindGuestCounter);
  });
}());
