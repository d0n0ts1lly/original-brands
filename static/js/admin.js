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
});
