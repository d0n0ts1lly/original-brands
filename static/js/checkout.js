document.addEventListener("DOMContentLoaded", () => {
  // ── Маска телефону (UA): +380 XX XXX XX XX ──
  const phoneInput = document.getElementById("checkoutPhoneInput");
  if (phoneInput) {
    const formatUaPhone = (raw) => {
      let digits = raw.replace(/\D/g, "");

      // "0XXXXXXXXX" (локальний формат) → підставляємо код країни 380
      if (digits.startsWith("0")) {
        digits = "380" + digits.slice(1);
      } else if (!digits.startsWith("380")) {
        digits = digits ? "380" + digits : "380";
      }
      digits = digits.slice(0, 12); // 380 + 9 цифр номера

      const rest = digits.slice(3);
      let out = "+380";
      if (rest.length > 0) out += " " + rest.slice(0, 2);
      if (rest.length > 2) out += " " + rest.slice(2, 5);
      if (rest.length > 5) out += " " + rest.slice(5, 7);
      if (rest.length > 7) out += " " + rest.slice(7, 9);
      return out;
    };

    const applyMask = () => {
      const formatted = formatUaPhone(phoneInput.value);
      phoneInput.value = formatted;
    };

    if (phoneInput.value.trim()) applyMask();
    phoneInput.addEventListener("input", applyMask);
    phoneInput.addEventListener("focus", () => {
      if (!phoneInput.value.trim()) phoneInput.value = "+380 ";
    });
  }

  // ── Перевірка email «на льоту» (поле необов'язкове) ──
  const emailInput = document.getElementById("checkoutEmailInput");
  if (emailInput) {
    const emailField = emailInput.closest(".field");
    const validateEmail = () => {
      const value = emailInput.value.trim();
      const isValid = value === "" || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
      if (emailField) emailField.classList.toggle("field--invalid", !isValid);
    };
    emailInput.addEventListener("input", validateEmail);
    emailInput.addEventListener("blur", validateEmail);
  }

  const cityInput = document.getElementById("checkoutCityInput");
  const citySuggest = document.getElementById("checkoutCitySuggestions");
  const branchInput = document.getElementById("checkoutBranchInput");
  const branchSuggest = document.getElementById("checkoutBranchSuggestions");

  // Форми оформлення замовлення немає на цій сторінці — нічого робити
  if (!cityInput || !citySuggest || !branchInput || !branchSuggest) return;

  let cityDebounce = null;
  let branchDebounce = null;

  function openList(el) {
    el.classList.add("is-open");
  }

  function closeList(el) {
    el.classList.remove("is-open");
    el.innerHTML = "";
  }

  function renderEmpty(el, text) {
    el.innerHTML = "";
    const empty = document.createElement("div");
    empty.className = "np-suggestions__empty";
    empty.textContent = text;
    el.appendChild(empty);
    openList(el);
  }

  function renderList(el, items, onPick) {
    el.innerHTML = "";
    if (!items.length) {
      closeList(el);
      return;
    }
    items.forEach((item) => {
      const row = document.createElement("button");
      row.type = "button";
      row.className = "np-suggestions__item";
      row.textContent = item.label;
      row.addEventListener("click", () => onPick(item));
      el.appendChild(row);
    });
    openList(el);
  }

  function fetchJson(url, body) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => r.json());
  }

  // ── Місто ──
  cityInput.addEventListener("input", () => {
    branchInput.value = "";
    branchInput.placeholder = "Спершу оберіть місто";
    closeList(branchSuggest);

    const q = cityInput.value.trim();
    clearTimeout(cityDebounce);

    if (q.length < 2) {
      closeList(citySuggest);
      return;
    }

    cityDebounce = setTimeout(() => {
      fetchJson("/get_cities", { search: q })
        .then((res) => {
          const items = (res.data || []).map((c) => ({
            label: [c.Present || c.Description, c.AreaDescription]
              .filter(Boolean)
              .join(", "),
            value: c.Description || c.Present || "",
          }));
          if (!items.length) {
            renderEmpty(citySuggest, "Нічого не знайдено");
            return;
          }
          renderList(citySuggest, items, (item) => {
            cityInput.value = item.value;
            closeList(citySuggest);
            branchInput.placeholder = "Почніть вводити номер або адресу…";
            branchInput.focus();
          });
        })
        .catch(() => closeList(citySuggest));
    }, 300);
  });

  // ── Відділення / поштомат ──
  branchInput.addEventListener("input", () => {
    const city = cityInput.value.trim();
    const q = branchInput.value.trim();
    clearTimeout(branchDebounce);

    if (!city) {
      closeList(branchSuggest);
      return;
    }

    branchDebounce = setTimeout(() => {
      fetchJson("/get_warehouses", { city: city, search: q })
        .then((res) => {
          const items = (res.data || []).map((w) => ({
            label: w.Description,
            value: w.Description,
          }));
          if (!items.length) {
            renderEmpty(branchSuggest, "Відділень не знайдено");
            return;
          }
          renderList(branchSuggest, items, (item) => {
            branchInput.value = item.value;
            closeList(branchSuggest);
          });
        })
        .catch(() => closeList(branchSuggest));
    }, 300);
  });

  branchInput.addEventListener("focus", () => {
    if (cityInput.value.trim()) {
      branchInput.dispatchEvent(new Event("input"));
    }
  });

  document.addEventListener("click", (e) => {
    if (!citySuggest.contains(e.target) && e.target !== cityInput) {
      closeList(citySuggest);
    }
    if (!branchSuggest.contains(e.target) && e.target !== branchInput) {
      closeList(branchSuggest);
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeList(citySuggest);
      closeList(branchSuggest);
    }
  });
});
