document.addEventListener("DOMContentLoaded", () => {
  const bindRemove = (row) => {
    const btn = row.querySelector(".repeatable__remove");
    btn.addEventListener("click", () => {
      const wrap = row.parentElement;
      if (wrap.children.length > 1) {
        row.remove();
      } else {
        row.querySelectorAll("input").forEach((i) => (i.value = ""));
      }
    });
  };

  document.querySelectorAll(".repeatable__row").forEach(bindRemove);

  const addSizeBtn = document.getElementById("addSizeRow");
  const sizeRows = document.getElementById("sizeRows");
  if (addSizeBtn && sizeRows) {
    addSizeBtn.addEventListener("click", () => {
      const row = document.createElement("div");
      row.className = "repeatable__row";
      row.innerHTML = `
        <input type="text" name="size[]" placeholder="Наприклад, 32" class="repeatable__size">
        <input type="number" name="quantity[]" min="0" placeholder="Кількість" class="repeatable__qty">
        <button type="button" class="icon-btn icon-btn--danger repeatable__remove" aria-label="Прибрати розмір">
          <i class="fa-solid fa-xmark"></i>
        </button>`;
      sizeRows.appendChild(row);
      bindRemove(row);
      row.querySelector("input").focus();
    });
  }

  const addPhotoBtn = document.getElementById("addPhotoRow");
  const photoRows = document.getElementById("photoRows");
  if (addPhotoBtn && photoRows) {
    addPhotoBtn.addEventListener("click", () => {
      const row = document.createElement("div");
      row.className = "repeatable__row repeatable__row--photo";
      row.innerHTML = `
        <input type="file" name="photo_file[]" accept="image/png,image/jpeg,image/webp,image/gif" class="repeatable__file">
        <span class="repeatable__or">або</span>
        <input type="url" name="photo_url[]" placeholder="https://…" class="repeatable__url">
        <button type="button" class="icon-btn icon-btn--danger repeatable__remove" aria-label="Прибрати фото">
          <i class="fa-solid fa-xmark"></i>
        </button>`;
      photoRows.appendChild(row);
      bindRemove(row);
    });
  }

  // Кольори товару: перемикач "плоскі розміри" <-> "кольори + свої розміри"
  const hasColorsToggle = document.getElementById("hasColorsToggle");
  const plainSizesSection = document.getElementById("plainSizesSection");
  const colorsSection = document.getElementById("colorsSection");
  const colorBlocks = document.getElementById("colorBlocks");
  const addColorBtn = document.getElementById("addColorBlock");

  const addColorSizeRow = (rowsWrap, colorIdx, size, qty) => {
    const row = document.createElement("div");
    row.className = "repeatable__row";
    row.innerHTML = `
      <input type="text" name="color_size_${colorIdx}[]" value="${
      size || ""
    }" placeholder="Наприклад, M" class="repeatable__size" list="sizeSuggestions">
      <input type="number" name="color_qty_${colorIdx}[]" value="${
      qty || ""
    }" min="0" placeholder="Кількість" class="repeatable__qty">
      <button type="button" class="icon-btn icon-btn--danger repeatable__remove" aria-label="Прибрати розмір">
        <i class="fa-solid fa-xmark"></i>
      </button>`;
    rowsWrap.appendChild(row);
    bindRemove(row);
    return row;
  };

  const addColorPhotoRow = (rowsWrap, colorIdx) => {
    const row = document.createElement("div");
    row.className = "repeatable__row repeatable__row--photo";
    row.innerHTML = `
      <input type="file" name="color_photo_file_${colorIdx}[]" accept="image/png,image/jpeg,image/webp,image/gif" class="repeatable__file">
      <span class="repeatable__or">або</span>
      <input type="url" name="color_photo_url_${colorIdx}[]" placeholder="https://…" class="repeatable__url">
      <button type="button" class="icon-btn icon-btn--danger repeatable__remove" aria-label="Прибрати фото">
        <i class="fa-solid fa-xmark"></i>
      </button>`;
    rowsWrap.appendChild(row);
    bindRemove(row);
    return row;
  };

  const bindColorBlock = (block) => {
    const idx = block.dataset.colorIndex;
    const rowsWrap = block.querySelector("[data-color-rows]");
    const addSizeBtn = block.querySelector(".color-block__add-size");
    const photoRowsWrap = block.querySelector("[data-color-photo-rows]");
    const addPhotoBtn = block.querySelector(".color-block__add-photo");
    const removeBtn = block.querySelector(".color-block__remove");

    if (addSizeBtn && rowsWrap) {
      addSizeBtn.addEventListener("click", () => {
        const row = addColorSizeRow(rowsWrap, idx);
        row.querySelector("input").focus();
      });
    }
    if (addPhotoBtn && photoRowsWrap) {
      addPhotoBtn.addEventListener("click", () => {
        addColorPhotoRow(photoRowsWrap, idx);
      });
    }
    if (removeBtn) {
      removeBtn.addEventListener("click", () => {
        block.remove();
      });
    }
  };

  if (colorBlocks) {
    colorBlocks.querySelectorAll(".color-block").forEach(bindColorBlock);
  }

  if (addColorBtn && colorBlocks) {
    addColorBtn.addEventListener("click", () => {
      const idx = parseInt(colorBlocks.dataset.nextIndex, 10) || 0;
      colorBlocks.dataset.nextIndex = idx + 1;

      const block = document.createElement("div");
      block.className = "color-block";
      block.dataset.colorIndex = idx;
      block.innerHTML = `
        <div class="color-block__head">
          <input type="text" name="color_name_${idx}" placeholder="Напр. Чорний" class="color-block__name">
          <input type="color" name="color_hex_${idx}" value="#1a1a1a" class="color-block__swatch-input" title="Зразок кольору">
          <button type="button" class="icon-btn icon-btn--danger color-block__remove" aria-label="Прибрати колір">
            <i class="fa-solid fa-trash"></i>
          </button>
        </div>
        <div class="repeatable color-block__sizes" data-color-rows></div>
        <button type="button" class="btn btn--ghost color-block__add-size">
          <i class="fa-solid fa-plus"></i>&nbsp; Додати розмір
        </button>
        <div class="color-block__photos-head">Фото цього кольору <small>(необов'язково)</small></div>
        <div class="repeatable color-block__photo-rows" data-color-photo-rows></div>
        <button type="button" class="btn btn--ghost color-block__add-photo">
          <i class="fa-solid fa-plus"></i>&nbsp; Додати фото кольору
        </button>`;
      colorBlocks.appendChild(block);

      addColorSizeRow(block.querySelector("[data-color-rows]"), idx);
      addColorPhotoRow(block.querySelector("[data-color-photo-rows]"), idx);
      bindColorBlock(block);
      block.querySelector(".color-block__name").focus();
    });
  }

  if (hasColorsToggle && plainSizesSection && colorsSection) {
    hasColorsToggle.addEventListener("change", () => {
      const isColored = hasColorsToggle.checked;
      plainSizesSection.style.display = isColored ? "none" : "";
      colorsSection.style.display = isColored ? "" : "none";
      // Якщо ввімкнули кольори, а блоків ще жодного нема — одразу додаємо перший
      if (
        isColored &&
        colorBlocks &&
        !colorBlocks.querySelector(".color-block") &&
        addColorBtn
      ) {
        addColorBtn.click();
      }
    });
  }
});
