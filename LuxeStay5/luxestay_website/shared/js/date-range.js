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
      form.dispatchEvent(new CustomEvent("booking-input-change", { bubbles: true }));
    }

    minus.addEventListener("click", function() {
      render(currentValue() - 1);
    });

    plus.addEventListener("click", function() {
      render(currentValue() + 1);
    });

    render(currentValue());
  }

  function setOrDeleteParam(url, name, value) {
    if (value) {
      url.searchParams.set(name, value);
    } else {
      url.searchParams.delete(name);
    }
  }

  function syncBookingLink(link, form) {
    const hotel = form.querySelector('input[name="hotel"], input[name="hotel_code"]');
    const checkIn = form.querySelector('input[name="checkIn"]');
    const checkOut = form.querySelector('input[name="checkOut"]');
    const guests = form.querySelector('input[name="guests"]');
    const room = form.querySelector('input[name="room_name"]');

    try {
      const url = new URL(link.getAttribute("href"), window.location.href);
      setOrDeleteParam(url, "hotel", hotel ? hotel.value : "");
      setOrDeleteParam(url, "checkIn", checkIn ? checkIn.value : "");
      setOrDeleteParam(url, "checkOut", checkOut ? checkOut.value : "");
      setOrDeleteParam(url, "guests", guests ? guests.value : "");
      setOrDeleteParam(url, "room_name", link.dataset.roomName || (room ? room.value : ""));
      link.href = url.pathname + url.search + url.hash;
    } catch (error) {
      return;
    }
  }

  function formatMoney(value) {
    return "$" + Math.round(value).toLocaleString("en-US");
  }

  function selectedRoomPrice(form) {
    const room = form.querySelector('input[name="room_name"]');
    const deluxePrice = Number(form.dataset.deluxePrice || 0);
    const juniorPrice = Number(form.dataset.juniorPrice || deluxePrice);
    return room && room.value === "Junior Suite" ? juniorPrice : deluxePrice;
  }

  function nightsBetween(checkInValue, checkOutValue) {
    const checkIn = parseDateInput(checkInValue);
    const checkOut = parseDateInput(checkOutValue);
    if (!checkIn || !checkOut) return 0;
    return Math.max(Math.round((checkOut - checkIn) / 86400000), 1);
  }

  function bindBookingWidgetTotals(form) {
    const price = form.querySelector("#w-price");
    const roomName = form.querySelector("#w-room-name");
    const nightsLabel = form.querySelector("#w-nights-label");
    const roomTotal = form.querySelector("#w-room-total");
    const serviceFee = form.querySelector("#w-service-fee");
    const taxes = form.querySelector("#w-taxes");
    const total = form.querySelector("#w-total");
    if (!price || !roomTotal || !serviceFee || !taxes || !total) return;

    const checkIn = form.querySelector('input[name="checkIn"]');
    const checkOut = form.querySelector('input[name="checkOut"]');
    const room = form.querySelector('input[name="room_name"]');

    function renderTotals() {
      const nightlyPrice = selectedRoomPrice(form);
      const nights = nightsBetween(checkIn ? checkIn.value : "", checkOut ? checkOut.value : "");
      price.textContent = formatMoney(nightlyPrice);
      if (roomName && room) roomName.textContent = room.value;

      if (!nights) {
        if (nightsLabel) nightsLabel.textContent = "Room cost";
        roomTotal.textContent = "—";
        serviceFee.textContent = "—";
        taxes.textContent = "—";
        total.textContent = "—";
        return;
      }

      const base = nightlyPrice * nights;
      const service = Math.round(base * 0.08);
      const tax = Math.round(base * 0.12);
      if (nightsLabel) nightsLabel.textContent = nights + " night" + (nights === 1 ? "" : "s") + " room cost";
      roomTotal.textContent = formatMoney(base);
      serviceFee.textContent = formatMoney(service);
      taxes.textContent = formatMoney(tax);
      total.textContent = formatMoney(base + service + tax);
    }

    form.querySelectorAll('input[name="checkIn"], input[name="checkOut"], input[name="room_name"]').forEach(function(input) {
      input.addEventListener("input", renderTotals);
      input.addEventListener("change", renderTotals);
    });
    form.addEventListener("booking-input-change", renderTotals);
    renderTotals();
  }

  function bindBookingLinkSync(form) {
    const links = Array.from(document.querySelectorAll("[data-booking-link]"));
    if (!links.length) return;

    function syncLinks() {
      links.forEach(function(link) {
        syncBookingLink(link, form);
      });
    }

    form.querySelectorAll('input[name="hotel"], input[name="hotel_code"], input[name="checkIn"], input[name="checkOut"], input[name="guests"], input[name="room_name"]').forEach(function(input) {
      input.addEventListener("input", syncLinks);
      input.addEventListener("change", syncLinks);
    });
    form.addEventListener("booking-input-change", syncLinks);
    links.forEach(function(link) {
      link.addEventListener("click", syncLinks);
    });
    syncLinks();
  }

  document.addEventListener("DOMContentLoaded", function() {
    document.querySelectorAll("form").forEach(bindDateRange);
    document.querySelectorAll(".guests-counter").forEach(bindGuestCounter);
    document.querySelectorAll("[data-booking-source]").forEach(bindBookingWidgetTotals);
    document.querySelectorAll("[data-booking-source]").forEach(bindBookingLinkSync);
  });
}());
